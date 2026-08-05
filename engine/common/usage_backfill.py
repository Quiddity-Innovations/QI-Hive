"""
QI Hive — one-shot historical backfill of the usage ledger (2026-01-01 -> today).

Run once. Idempotent: measured rows are never overwritten by estimates, so
re-running only refreshes the reconstructed segments.

Segment plan (each day is tagged with how it was derived)
---------------------------------------------------------
  2026-01-01 .. 2026-02-17   none       certain   $0 — no account existed.
                                                  Subscription created
                                                  2026-02-17T22:56:38Z;
                                                  Claude Code first launched
                                                  2026-02-18T01:50:57Z.
  2026-02-18 .. 2026-05-20   estimated  low       Modelled: activity index x
                                                  turns-per-unit, priced at the
                                                  blended measured turn rate.
  2026-05-21 .. 2026-06-19   anchored   medium    Known 30-day total from the
                                                  2026-06-19 dashboard
                                                  screenshot, distributed
                                                  across days by activity share.
  2026-06-20 .. 2026-06-25   estimated  low       Gap between the screenshot
                                                  window and surviving logs.
  2026-06-26 .. today        measured   exact     Parsed from real transcripts.
                                                  Holes inside this range (days
                                                  whose transcripts were already
                                                  deleted but which show
                                                  activity) are filled as
                                                  'estimated'.

Unit rates are derived from the two independent measured windows, which agree
to within ~5% -- see print_calibration().
"""
from __future__ import annotations

import sys
from datetime import date

sys.path.insert(0, r"C:\QIH\engine\common")

import usage_stats
import usage_ledger
from usage_reconstruct import (
    ANCHOR, SUBSCRIPTION_START, YEAR_START, build_activity_index, daterange,
)

MEASURED_START = date(2026, 6, 26)   # earliest surviving transcript event
ANCHOR_START = date(2026, 5, 21)     # first bar on the screenshot's 30d chart
ANCHOR_END = ANCHOR["window_end"]    # 2026-06-19

# ── Plausibility constraints (all derived from measured data, not taste) ──
#
# Raw activity proxies are BURSTY in a way token spend is not. April 2026
# carries 348 commits -- the QI Hive folder reorganisation -- which is a great
# many mechanical commits for very little Claude consumption. Left uncorrected
# the index put April above the busiest window ever actually measured, and put
# single days at ~2x the highest turn count ever recorded. Three corrections:
#
#   1. COMPRESS   sub-linear transform on the index, so a day with 10x the
#                 commits is not assumed to have 10x the token spend.
#   2. MAX_TURNS  hard per-day ceiling = the highest daily turn count ever
#                 measured. The plan is Claude MAX 5x with weekly rate limits;
#                 sustained days above the observed peak are not physically
#                 available.
#   3. WINDOW_CAP no rolling 30-day window may exceed the busiest 30-day
#                 window ever recorded (the screenshot anchor). Excess is
#                 scaled back proportionally.
COMPRESS = 0.5
WINDOW_CAP_TURNS = ANCHOR["turns"]   # 23,676 turns in the busiest measured month


def _compress(idx: dict) -> dict:
    return {d: (v ** COMPRESS if v > 0 else 0.0) for d, v in idx.items()}


def _apply_window_cap(turns_by_day: dict[date, float], fixed: set) -> dict:
    """Scale down any rolling 30-day window that exceeds the busiest window
    ever measured.

    `fixed` holds days we must not touch: measured days (real data) and
    anchored days (distributed from a known window total -- shrinking those
    would contradict the screenshot they came from). Only 'estimated' days
    absorb the correction.
    """
    days = sorted(turns_by_day)
    for _ in range(8):  # a few passes converge
        worst, worst_ratio = None, 1.0
        for i in range(len(days)):
            win = days[i:i + 30]
            if len(win) < 30:
                break
            tot = sum(turns_by_day[d] for d in win)
            if tot > WINDOW_CAP_TURNS and tot / WINDOW_CAP_TURNS > worst_ratio:
                worst, worst_ratio = win, tot / WINDOW_CAP_TURNS
        if worst is None:
            break
        flex = [d for d in worst if d not in fixed]
        if not flex:
            break
        fixed_tot = sum(turns_by_day[d] for d in worst if d in fixed)
        flex_tot = sum(turns_by_day[d] for d in flex)
        allowed = max(0.0, WINDOW_CAP_TURNS - fixed_tot)
        if flex_tot > allowed and flex_tot > 0:
            k = allowed / flex_tot
            for d in flex:
                turns_by_day[d] *= k
    return turns_by_day


def calibration(today: date) -> dict:
    """Blend the two measured windows into per-turn unit rates."""
    # Calibrate against the LEDGER's measured rows, not live transcripts.
    # Transcripts are the fragile source this whole ledger exists to outlive;
    # if they are ever moved or pruned, calibrating from them would silently
    # narrow the sample and swing every estimate with no warning. The ledger
    # base only ever grows, so re-running this in December re-derives the
    # Feb-Jun estimates against many more months of real data.
    B = usage_ledger.measured_totals()
    if B["turns"] < 500:                      # ledger not populated yet
        B = usage_stats.range_stats(MEASURED_START, today)
    A = ANCHOR
    turns = A["turns"] + B["turns"]
    cost = A["cost_usd"] + B["cost_usd"]
    tokens = A["tokens"] + B["tokens"]
    idx = _compress(build_activity_index(SUBSCRIPTION_START, today))
    idx_A = sum(idx[d] for d in daterange(ANCHOR_START, ANCHOR_END))
    return {
        "usd_per_turn": cost / turns,
        "tokens_per_turn": tokens / turns,
        # Cache re-reads scale with tokens; take the ratio from real data.
        "cache_ratio": (B["cache_reads"] / B["tokens"]) if B["tokens"] else 0.0,
        # Turns per unit of activity index, taken from the anchor window --
        # the measured window nearest in time to the estimated period. Using
        # the later window instead would under-count by ~30%, because file
        # mtimes and commits under-represent older work that was later
        # overwritten. We deliberately do NOT extrapolate that drift further
        # back, which would compound into fantasy.
        "turns_per_index": A["turns"] / idx_A if idx_A else 0.0,
        "index": idx,
        "B": B,
    }


def print_calibration(cal: dict) -> None:
    A, B = ANCHOR, cal["B"]
    print("=" * 72)
    print("CALIBRATION — two independent measured windows")
    print("=" * 72)
    print(f"  screenshot 30d -> 06-19 : ${A['cost_usd']:>10,.2f}  "
          f"{A['turns']:>6,} turns  ${A['cost_usd']/A['turns']:.4f}/turn  "
          f"{A['tokens']/A['turns']:>7,.0f} tok/turn")
    print(f"  transcripts 06-26..now  : ${B['cost_usd']:>10,.2f}  "
          f"{B['turns']:>6,} turns  ${B['cost_usd']/B['turns']:.4f}/turn  "
          f"{B['tokens']/B['turns']:>7,.0f} tok/turn")
    print(f"  -> blended               : ${cal['usd_per_turn']:.4f}/turn  "
          f"{cal['tokens_per_turn']:,.0f} tok/turn  "
          f"cache x{cal['cache_ratio']:.1f}")
    print(f"  -> {cal['turns_per_index']:,.1f} turns per activity-index unit")
    print()


def run(today: date | None = None, apply: bool = True) -> dict:
    today = today or date.today()
    cal = calibration(today)
    print_calibration(cal)
    idx = cal["index"]
    upt, tpt, cache_r = cal["usd_per_turn"], cal["tokens_per_turn"], cal["cache_ratio"]

    import datetime as _dt

    # ── 1. Measured days are fixed points; everything else flexes ───────
    measured: dict[date, dict] = {}
    for row in usage_stats.daily((today - MEASURED_START).days + 1):
        if row["turns"] > 0:
            measured[date.fromisoformat(row["date"])] = row
    max_turns = max((r["turns"] for r in measured.values()), default=2500)

    # ── 2. Build modelled turns for every non-measured day ──────────────
    tpi = cal["turns_per_index"]
    idx_anchor = sum(idx[d] for d in daterange(ANCHOR_START, ANCHOR_END))
    anchor_fixed = sum(measured[d]["turns"] for d in daterange(ANCHOR_START, ANCHOR_END)
                       if d in measured)
    anchor_budget = max(0.0, ANCHOR["turns"] - anchor_fixed)

    turns_by_day: dict[date, float] = {}
    kind: dict[date, str] = {}
    for d in daterange(SUBSCRIPTION_START, today):
        if d in measured:
            turns_by_day[d] = float(measured[d]["turns"])
            kind[d] = "measured"
        elif ANCHOR_START <= d <= ANCHOR_END:
            share = (idx[d] / idx_anchor) if idx_anchor else 0.0
            turns_by_day[d] = anchor_budget * share
            kind[d] = "anchored"
        else:
            turns_by_day[d] = idx.get(d, 0.0) * tpi
            kind[d] = "estimated"

    # ── 3. Constrain: per-day ceiling, then rolling-window ceiling ──────
    for d in turns_by_day:
        if kind[d] != "measured":
            turns_by_day[d] = min(turns_by_day[d], max_turns)
    fixed = {d for d in turns_by_day if kind[d] in ("measured", "anchored")}
    turns_by_day = _apply_window_cap(turns_by_day, fixed)

    # ── 4. Write ────────────────────────────────────────────────────────
    con = usage_ledger.connect()
    stats = {"none": 0, "estimated": 0, "anchored": 0, "measured": 0}
    totals = {"none": 0.0, "estimated": 0.0, "anchored": 0.0, "measured": 0.0}

    # 4a. Pre-account days: genuinely zero, and provably so.
    for d in daterange(YEAR_START, SUBSCRIPTION_START - _dt.timedelta(days=1)):
        usage_ledger.upsert_day(
            con, d, tokens=0, cache_reads=0, cost_usd=0.0, turns=0, sessions=0,
            source="none", confidence="certain",
            note="no Claude subscription yet (created 2026-02-17T22:56:38Z)",
        )
        stats["none"] += 1

    notes = {
        "measured": "parsed from surviving ~/.claude/projects transcripts",
        "anchored": ("distributed from known 30d total $17,285.62 "
                     "(dashboard screenshot 2026-06-19) by activity share"),
        "estimated": ("modelled from activity proxies (git commits, session "
                      "summaries, Brain rows, file mtimes), compressed and "
                      "capped at measured peaks"),
    }
    for d in daterange(SUBSCRIPTION_START, today):
        k = kind[d]
        if k == "measured":
            row = measured[d]
            tokens, cost = row["tokens"], row["cost_usd"]
            turns, sess = row["turns"], row["sessions"]
            cache = row.get("cache_reads", 0)
        else:
            turns = max(0, int(round(turns_by_day[d])))
            tokens = int(turns * tpt)
            cost = turns * upt
            cache = int(tokens * cache_r)
            sess = max(1, round(turns / 330)) if turns else 0
        usage_ledger.upsert_day(
            con, d, tokens=tokens, cache_reads=cache, cost_usd=cost,
            turns=turns, sessions=sess, source=k,
            confidence={"measured": "exact", "anchored": "medium"}.get(k, "low"),
            note=notes[k],
        )
        stats[k] += 1
        totals[k] += cost

    if apply:
        con.commit()
    con.close()
    return {"days_by_source": stats, "cost_by_source": {k: round(v, 2) for k, v in totals.items()},
            "max_turns_cap": max_turns}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    res = run()
    print("=" * 72)
    print("BACKFILL COMPLETE")
    print("=" * 72)
    print("  days   :", res["days_by_source"])
    print("  cost   :", res["cost_by_source"])
    print()
    for c in usage_ledger.coverage():
        print(f"  {c['source']:<10} {c['confidence']:<8} {c['days']:>3}d  "
              f"{c['first']} .. {c['last']}  ${c['cost_usd']:>11,.2f}")

# -*- coding: utf-8 -*-
"""
QI Hive — one-shot ledger recalibration after the 2026-09-16 usage audit.

What it does (in order, all logged, nothing deleted):
  0. Copies qi_brain.db to shared/backups/db/<date>_pre-recalibrate/ (sqlite backup API).
  1. Adds the token-split columns to usage_daily if missing (additive migration).
  2. Measures the legacy parser's inflation on the surviving transcripts:
        dedup_ratio  = raw usage lines / unique message ids   (per day, and overall)
        price_ratio  = cost at current per-model prices / cost at legacy family prices
     computed on the SAME deduplicated events, so the two effects are separable.
  3. Re-snapshots every day that still has a transcript on disk with the v2
     parser (measured rows are replaced by measured rows).
  4. Scales every remaining legacy row (estimated / anchored, plus measured
     days whose transcripts are gone) by the era-appropriate factors:
        cost   *= price_ratio(era) / dedup_ratio
        tokens /= dedup_ratio ;  turns /= dedup_ratio
     and records the factors in the row's `note`.
  5. Rebuilds usage_daily_project / usage_daily_model in full.
  6. Prints a monthly before/after table and writes it to
     C:\\QIH\\LOGS\\usage_recalibrate_<stamp>.log

Idempotent: rows carry `note LIKE 'recalibrated%'` and are never scaled twice.
Run:  python C:\\QIH\\engine\\common\\usage_recalibrate.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\QIH\engine\common")
sys.path.insert(0, r"C:\QIH")

import usage_stats            # v2 parser
import usage_ledger
import usage_dimensions
from usage_dimensions import MODEL_ERAS, _ANCHOR_MODEL_MIX

BRAIN_DB = Path(r"C:\QIH\data\qi_brain.db")
LOG_DIR = Path(r"C:\QIH\LOGS")
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG = []

# Legacy (v1) family prices that produced every stored figure before today.
LEGACY_FAMILY = {"opus": (15.0, 75.0), "fable": (15.0, 75.0), "sonnet": (3.0, 15.0),
                 "haiku": (0.8, 4.0), "other": (3.0, 15.0)}


def say(msg: str) -> None:
    print(msg)
    LOG.append(msg)


def legacy_cost(e: dict) -> float:
    i, o = LEGACY_FAMILY[e["family"]]
    return (e["input"] * i + e["output"] * o + e["cache_reads"] * i * 0.10
            + e["cw5"] * i * 1.25 + e["cw1"] * i * 2.0) / 1e6


def backup_db() -> Path:
    dest_dir = Path(r"C:\QIH\shared\backups\db") / f"{date.today()}_pre-recalibrate"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "qi_brain.db"
    src = sqlite3.connect(f"file:{BRAIN_DB}?mode=ro", uri=True, timeout=30)
    out = sqlite3.connect(dest)
    src.backup(out); out.close(); src.close()
    say(f"[0] backup -> {dest} ({dest.stat().st_size:,} bytes)")
    return dest


def migrate(con: sqlite3.Connection) -> None:
    cols = {r[1] for r in con.execute("PRAGMA table_info(usage_daily)")}
    for c, t in (("input_tokens", "INTEGER NOT NULL DEFAULT 0"),
                 ("output_tokens", "INTEGER NOT NULL DEFAULT 0"),
                 ("cache_write_5m", "INTEGER NOT NULL DEFAULT 0"),
                 ("cache_write_1h", "INTEGER NOT NULL DEFAULT 0"),
                 ("pricing_version", "TEXT")):
        if c not in cols:
            con.execute(f"ALTER TABLE usage_daily ADD COLUMN {c} {t}")
            say(f"[1] added column usage_daily.{c}")
    con.commit()


def measure_inflation() -> dict:
    """Per-era dedup and price ratios from surviving transcripts."""
    raw_lines: dict[date, int] = defaultdict(int)
    uniq: dict[date, int] = defaultdict(int)
    cost_new: dict[date, float] = defaultdict(float)
    cost_old: dict[date, float] = defaultdict(float)
    for jsonl in usage_stats.PROJECTS_DIR.rglob("*.jsonl"):
        folder = usage_stats._top_folder(jsonl)
        try:
            with jsonl.open("r", encoding="utf-8") as f:
                evs = usage_stats.parse_lines(f, folder)
        except OSError:
            continue
        for e in evs:
            raw_lines[e["ts"].astimezone().date()] += 1
        for e in usage_stats.dedup(evs):
            d = e["ts"].astimezone().date()
            uniq[d] += 1
            cost_new[d] += e["cost"]
            cost_old[d] += legacy_cost(e)
    days = sorted(raw_lines)
    if not days:
        raise SystemExit("no transcripts found — cannot calibrate")
    tot_raw = sum(raw_lines.values()); tot_uniq = sum(uniq.values())
    dedup_ratio = tot_raw / tot_uniq if tot_uniq else 1.0
    # Earliest 4 measured weeks give the ratio closest to the reconstructed eras.
    early = [d for d in days if d <= days[0] + timedelta(days=28)]
    early_raw = sum(raw_lines[d] for d in early); early_uniq = sum(uniq[d] for d in early)
    dedup_early = early_raw / early_uniq if early_uniq else dedup_ratio
    price_ratio_measured = (sum(cost_new.values()) / sum(cost_old.values())) if sum(cost_old.values()) else 1.0
    say(f"[2] transcripts cover {days[0]} .. {days[-1]} ({len(days)} days)")
    say(f"[2] dedup ratio overall {dedup_ratio:.3f}x, first 4 weeks {dedup_early:.3f}x")
    say(f"[2] price ratio (new/legacy) on measured events {price_ratio_measured:.3f}")
    return {"first_day": days[0], "days_with_transcripts": set(days),
            "dedup_ratio": dedup_ratio, "dedup_early": dedup_early,
            "price_ratio_measured": price_ratio_measured}


def era_price_ratio(d: date) -> float:
    """new/legacy cost ratio implied by the era's model mix (cost-share weights)."""
    mix = None
    for start, end, m in MODEL_ERAS:
        if start <= d <= end:
            mix = m; break
    mix = mix or _ANCHOR_MODEL_MIX
    tot = sum(mix.values()) or 1.0
    ratio = 0.0
    for model, share in mix.items():
        fam = usage_stats._model_family(model)
        li, lo = LEGACY_FAMILY[fam]
        ni, no, _ = usage_stats.price_for(model)
        # cost is dominated by cache reads/writes priced off the input rate,
        # so the input ratio is the right single-number proxy per model.
        ratio += (share / tot) * (ni / li)
    return ratio


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    con = usage_ledger.connect()
    before = con.execute("SELECT substr(day,1,7), ROUND(SUM(cost_usd),2), SUM(turns), SUM(tokens) "
                         "FROM usage_daily GROUP BY 1 ORDER BY 1").fetchall()
    con.close()

    if not a.dry_run:
        backup_db()
    con = usage_ledger.connect()
    if not a.dry_run:
        migrate(con)

    m = measure_inflation()
    first = m["first_day"]

    # [3] re-snapshot every day with a surviving transcript
    span_days = (date.today() - first).days + 1
    if a.dry_run:
        say(f"[3] would re-snapshot {span_days} days from {first}")
    else:
        rows = usage_stats.daily(span_days)
        written = 0
        for row in rows:
            d = date.fromisoformat(row["date"])
            if row["turns"] <= 0:
                continue
            con.execute(
                """INSERT INTO usage_daily
                     (day, tokens, cache_reads, cost_usd, turns, sessions, source, confidence,
                      note, updated_at, input_tokens, output_tokens, cache_write_5m, cache_write_1h,
                      pricing_version)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(day) DO UPDATE SET
                     tokens=excluded.tokens, cache_reads=excluded.cache_reads,
                     cost_usd=excluded.cost_usd, turns=excluded.turns, sessions=excluded.sessions,
                     source='measured', confidence='exact', note=excluded.note,
                     updated_at=excluded.updated_at, input_tokens=excluded.input_tokens,
                     output_tokens=excluded.output_tokens, cache_write_5m=excluded.cache_write_5m,
                     cache_write_1h=excluded.cache_write_1h, pricing_version=excluded.pricing_version""",
                (d.isoformat(), row["tokens"], row["cache_reads"], row["cost_usd"], row["turns"],
                 row["sessions"], "measured", "exact",
                 "parsed from ~/.claude/projects transcripts (v2 parser, dedup + per-model pricing)",
                 datetime.now().isoformat(timespec="seconds"),
                 row["input_tokens"], row["output_tokens"], row["cache_write_5m"], row["cache_write_1h"],
                 usage_stats.PRICING_VERSION))
            written += 1
        con.commit()
        say(f"[3] re-snapshotted {written} measured days from {first}")

    # [4] scale legacy rows
    legacy = con.execute(
        "SELECT day, source, cost_usd, tokens, turns, note FROM usage_daily "
        "WHERE cost_usd > 0 AND (pricing_version IS NULL OR pricing_version = '') "
        "AND (note IS NULL OR note NOT LIKE 'recalibrated%') ORDER BY day").fetchall()
    scaled = 0; delta = 0.0
    for ds, source, cost, tokens, turns, note in legacy:
        d = date.fromisoformat(ds)
        if source == "measured" and d in m["days_with_transcripts"]:
            continue   # just re-snapshotted above
        dd = m["dedup_early"] if d < first else m["dedup_ratio"]
        pr = era_price_ratio(d) if d < first else m["price_ratio_measured"]
        new_cost = cost * pr / dd
        new_tokens = int(tokens / dd)
        new_turns = int(round(turns / dd))
        new_note = (f"recalibrated {date.today()}: legacy parser x{dd:.2f} dedup, "
                    f"price ratio {pr:.3f}; was ${cost:,.2f}/{turns} turns"
                    + (f" | {note}" if note else ""))
        delta += cost - new_cost
        if not a.dry_run:
            con.execute("UPDATE usage_daily SET cost_usd=?, tokens=?, turns=?, note=?, "
                        "pricing_version=?, updated_at=? WHERE day=?",
                        (round(new_cost, 2), new_tokens, new_turns, new_note,
                         usage_stats.PRICING_VERSION + "-scaled",
                         datetime.now().isoformat(timespec="seconds"), ds))
        scaled += 1
    if not a.dry_run:
        con.commit()
    say(f"[4] scaled {scaled} legacy rows; removed ${delta:,.2f} of phantom cost")
    con.close()

    # [5] rebuild dimensions
    if not a.dry_run:
        r = usage_dimensions.backfill(verbose=False)
        say(f"[5] dimensions rebuilt: {r['project_rows']} project rows, {r['model_rows']} model rows, "
            f"unreconciled p={r['unreconciled_projects']} m={r['unreconciled_models']}")

    # [6] before/after
    con = usage_ledger.connect()
    after = con.execute("SELECT substr(day,1,7), ROUND(SUM(cost_usd),2), SUM(turns), SUM(tokens) "
                        "FROM usage_daily GROUP BY 1 ORDER BY 1").fetchall()
    ytd = usage_ledger.totals_since(date(date.today().year, 1, 1))
    con.close()
    bmap = {r[0]: r for r in before}
    say(f"\n{'month':8} {'cost before':>13} {'cost after':>12} {'turns before':>13} {'turns after':>12}")
    for mo, c, t, _tok in after:
        b = bmap.get(mo, (mo, 0, 0, 0))
        say(f"{mo:8} {b[1]:13,.2f} {c:12,.2f} {b[2]:13,} {t:12,}")
    say(f"YTD now ${ytd['cost_usd']:,.2f} ({ytd['measured_pct']}% measured)")
    (LOG_DIR / f"usage_recalibrate_{STAMP}.log").write_text("\n".join(LOG), encoding="utf-8")
    say(f"log -> {LOG_DIR / f'usage_recalibrate_{STAMP}.log'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

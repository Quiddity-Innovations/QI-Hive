"""
QI Hive — persistent daily usage ledger.

The problem this solves
-----------------------
`usage_stats.py` is stateless: it re-parses ~/.claude/projects/**/*.jsonl on
every call. Claude Code deletes those transcripts on a retention timer, so
every historical figure silently decayed. This module gives the Hive a
durable per-day store that survives transcript deletion.

Two entry points:

    snapshot()   — read today's (and recent) MEASURED days out of usage_stats
                   and upsert them into qi_brain.db. Safe to run repeatedly;
                   intended for the nightly sync task.

    totals_since(d) / daily(n) — read back from the ledger, preferring
                   measured rows and falling back to reconstructed ones.

Provenance is first-class. Every row records:

    source      measured  — parsed from a real transcript
                anchored  — distributed from a known window total
                            (the 2026-06-19 dashboard screenshot)
                estimated — modelled from activity proxies
                none      — no account existed; genuinely zero

    confidence  exact | medium | low | certain

`snapshot()` will NEVER overwrite a measured row with an estimate, and will
always upgrade an estimated row to measured if real data reappears.
"""
from __future__ import annotations

import os as _os
import sqlite3
import sys as _sys
from datetime import date, datetime, timedelta
from pathlib import Path

# This module is imported two ways: as `engine.common.usage_ledger` by the
# dashboard, and as a bare `usage_ledger` by the CLI tools in this folder.
# Sibling imports below (usage_stats, usage_dimensions) are written bare, so
# make this directory importable under either entry point. Without this the
# dashboard silently falls back to live transcript parsing and the ledger's
# reconstructed history disappears from every tile.
_HERE = _os.path.dirname(_os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)

BRAIN_DB = Path(r"C:\QIH\data\qi_brain.db")

# Rank used to decide whether an incoming row may replace an existing one.
_SOURCE_RANK = {"none": 0, "estimated": 1, "anchored": 2, "measured": 3}

DDL = """
CREATE TABLE IF NOT EXISTS usage_daily (
    day          TEXT PRIMARY KEY,
    tokens       INTEGER NOT NULL DEFAULT 0,
    cache_reads  INTEGER NOT NULL DEFAULT 0,
    cost_usd     REAL    NOT NULL DEFAULT 0.0,
    turns        INTEGER NOT NULL DEFAULT 0,
    sessions     INTEGER NOT NULL DEFAULT 0,
    source       TEXT    NOT NULL DEFAULT 'estimated',
    confidence   TEXT    NOT NULL DEFAULT 'low',
    note         TEXT,
    updated_at   TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_usage_daily_source ON usage_daily(source);
"""


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(BRAIN_DB, timeout=30)
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(DDL)
    return con


def upsert_day(con: sqlite3.Connection, day: date, *, tokens: int, cache_reads: int,
               cost_usd: float, turns: int, sessions: int, source: str,
               confidence: str, note: str = "", force: bool = False) -> bool:
    """Insert or update one day. Returns True if written.

    A row is only replaced when the incoming `source` ranks >= the stored one,
    so a reconstruction pass can never clobber real measured data.
    """
    ds = day.isoformat()
    cur = con.execute("SELECT source FROM usage_daily WHERE day=?", (ds,))
    row = cur.fetchone()
    if row and not force:
        if _SOURCE_RANK.get(source, 0) < _SOURCE_RANK.get(row[0], 0):
            return False
    con.execute(
        """INSERT INTO usage_daily
             (day, tokens, cache_reads, cost_usd, turns, sessions,
              source, confidence, note, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(day) DO UPDATE SET
             tokens=excluded.tokens, cache_reads=excluded.cache_reads,
             cost_usd=excluded.cost_usd, turns=excluded.turns,
             sessions=excluded.sessions, source=excluded.source,
             confidence=excluded.confidence, note=excluded.note,
             updated_at=excluded.updated_at""",
        (ds, int(tokens), int(cache_reads), float(cost_usd), int(turns),
         int(sessions), source, confidence, note,
         datetime.now().isoformat(timespec="seconds")),
    )
    return True


def max_day() -> date | None:
    """Newest day present in the ledger, or None when it is empty.

    Read paths use this as a staleness probe: every window helper prefers the
    ledger whenever it holds ANY row for the window, so a ledger that has
    stopped being snapshotted silently truncates 30d/QTD/YTD at this date
    instead of falling back to live parsing. See `ensure_fresh` in
    usage_snapshot_task.
    """
    con = connect()
    try:
        r = con.execute("SELECT MAX(day) FROM usage_daily").fetchone()[0]
    finally:
        con.close()
    return date.fromisoformat(r) if r else None


def snapshot(days: int = 45, verbose: bool = False) -> dict:
    """Persist the last `days` of MEASURED data from usage_stats into the
    ledger. This is the call that makes history durable — once a day has been
    snapshotted, deleting its transcript no longer loses it.

    Only days with real activity are written as 'measured'; a zero day inside
    the transcript window is left alone, because it may simply mean the
    transcript was already deleted rather than that nothing happened.
    """
    import usage_stats

    con = connect()
    written = skipped = 0
    for row in usage_stats.daily(days):
        d = date.fromisoformat(row["date"])
        if row["turns"] <= 0:
            skipped += 1
            continue
        ok = upsert_day(
            con, d,
            tokens=row["tokens"], cache_reads=row.get("cache_reads", 0),
            cost_usd=row["cost_usd"],
            turns=row["turns"], sessions=row["sessions"],
            source="measured", confidence="exact",
            note="parsed from ~/.claude/projects transcripts",
        )
        written += 1 if ok else 0
        if verbose:
            print(f"  {d} ${row['cost_usd']:>9,.2f} measured")
    con.commit()
    con.close()
    return {"written": written, "skipped_zero": skipped, "window_days": days}


# ── Read-back API (drop-in shapes matching usage_stats) ──────────────────
def totals_since(start: date, end: date | None = None) -> dict:
    end = end or date.today()
    con = connect()
    r = con.execute(
        """SELECT COALESCE(SUM(tokens),0), COALESCE(SUM(cache_reads),0),
                  COALESCE(SUM(cost_usd),0), COALESCE(SUM(turns),0),
                  COALESCE(SUM(sessions),0)
             FROM usage_daily WHERE day>=? AND day<=?""",
        (start.isoformat(), end.isoformat()),
    ).fetchone()
    breakdown = dict(con.execute(
        """SELECT source, ROUND(SUM(cost_usd),2) FROM usage_daily
             WHERE day>=? AND day<=? GROUP BY source""",
        (start.isoformat(), end.isoformat()),
    ).fetchall())
    con.close()
    return {
        "since": start.isoformat(), "until": end.isoformat(),
        "tokens": r[0], "cache_reads": r[1], "cost_usd": round(r[2], 2),
        "turns": r[3], "sessions": r[4],
        "cost_by_source": breakdown,
        "measured_pct": round(100 * breakdown.get("measured", 0) / r[2], 1) if r[2] else 0.0,
    }


def daily(days: int = 30) -> list[dict]:
    start = date.today() - timedelta(days=days - 1)
    con = connect()
    rows = con.execute(
        """SELECT day, tokens, cache_reads, cost_usd, turns, sessions,
                  source, confidence FROM usage_daily
             WHERE day>=? ORDER BY day""", (start.isoformat(),)
    ).fetchall()
    con.close()
    return [
        {"date": r[0], "tokens": r[1], "cache_reads": r[2], "cost_usd": r[3],
         "turns": r[4], "sessions": r[5], "source": r[6], "confidence": r[7]}
        for r in rows
    ]


def daily_range(start: date, end: date) -> list[dict]:
    """Per-day rows for an inclusive window, zero-filled so the chart has a
    continuous x-axis even across days with no activity.

    Includes the three what-if series the daily chart plots (actual / with
    local offload / combined). Local offload is computed from that day's own
    model-family mix, so an Opus-heavy day correctly shows ~no offloadable
    work while a Haiku-heavy one shows nearly all of it.
    """
    import usage_stats

    con = connect()
    got = {r[0]: r for r in con.execute(
        """SELECT day, tokens, cache_reads, cost_usd, turns, sessions, source, confidence
             FROM usage_daily WHERE day>=? AND day<=?""",
        (start.isoformat(), end.isoformat()))}
    fam: dict[str, dict[str, float]] = {}
    for ds, f, c in con.execute(
        """SELECT day, family, SUM(cost_usd) FROM usage_daily_model
             WHERE day>=? AND day<=? GROUP BY day, family""",
        (start.isoformat(), end.isoformat())):
        fam.setdefault(ds, {})[f] = c or 0.0
    con.close()

    out, d = [], start
    while d <= end:
        ds = d.isoformat()
        r = got.get(ds)
        cost = float(r[3]) if r else 0.0
        offload = sum(c * usage_stats.LOCAL_OFFLOAD_BY_FAMILY.get(f, 0.0)
                      for f, c in fam.get(ds, {}).items())
        local_cost = max(0.0, cost - offload)
        batch_cost = cost * (1 - usage_stats.BATCH_DISCOUNT * _BATCHABLE_FRACTION)
        combined = local_cost * (1 - usage_stats.BATCH_DISCOUNT * _BATCHABLE_FRACTION)
        out.append({
            "date": ds,
            "tokens": r[1] if r else 0, "cache_reads": r[2] if r else 0,
            "cost_usd": round(cost, 2),
            "local_cost_usd": round(local_cost, 2),
            "batch_cost_usd": round(batch_cost, 2),
            "combined_cost_usd": round(combined, 2),
            "turns": r[4] if r else 0, "sessions": r[5] if r else 0,
            "source": r[6] if r else "none", "confidence": r[7] if r else "certain",
        })
        d += timedelta(days=1)
    return out


# Fraction of spend that fell OUTSIDE the 00:00-06:00 batch window, measured
# from real transcripts. Reconstructed days carry no hour-of-day, so the
# measured ratio is applied to them rather than inventing a distribution.
_BATCHABLE_FRACTION = 0.99


def range_stats(start: date, end: date) -> dict:
    """Ledger-backed equivalent of usage_stats.range_stats — same keys, so the
    LLM Usage tab's range picker and drilldown work over reconstructed history
    exactly as they do over measured days.

    Local-offload savings are computed per model family from
    usage_daily_model, so a window dominated by Opus reports ~0% offloadable
    while a Haiku-heavy one reports ~100% -- the same rule usage_stats applies.
    """
    if end < start:
        start, end = end, start
    import usage_stats

    base = totals_since(start, end)
    con = connect()
    fam_rows = con.execute(
        """SELECT family, SUM(cost_usd) FROM usage_daily_model
             WHERE day>=? AND day<=? GROUP BY family""",
        (start.isoformat(), end.isoformat())).fetchall()
    con.close()

    actual = base["cost_usd"]
    local_savings = 0.0
    for fam, c in fam_rows:
        local_savings += (c or 0.0) * usage_stats.LOCAL_OFFLOAD_BY_FAMILY.get(fam, 0.0)
    # If the dimension table is empty for this window, fall back to no offload
    # rather than silently reporting a fabricated saving.
    batchable = actual * _BATCHABLE_FRACTION
    batch_savings = batchable * usage_stats.BATCH_DISCOUNT
    combined = (actual - local_savings)
    combined -= (combined * _BATCHABLE_FRACTION) * usage_stats.BATCH_DISCOUNT

    def pct(p, w):
        return round((p / w) * 100, 1) if w > 0 else 0.0

    return {
        "start": start.isoformat(), "end": end.isoformat(),
        "days": (end - start).days + 1,
        "tokens": base["tokens"], "cache_reads": base["cache_reads"],
        "cost_usd": actual, "turns": base["turns"], "sessions": base["sessions"],
        # Aliases so this is a drop-in for both usage_stats.totals() and
        # usage_stats.savings(), which name the same quantities differently.
        "actual_cost_usd": actual, "actual_tokens": base["tokens"],
        "measured_pct": base["measured_pct"], "cost_by_source": base["cost_by_source"],
        "local_savings_usd": round(local_savings, 2),
        "local_savings_pct": pct(local_savings, actual),
        "local_optimized_cost_usd": round(actual - local_savings, 2),
        "offloaded_turns": int(base["turns"] * (local_savings / actual)) if actual else 0,
        "offloaded_tokens": int(base["tokens"] * (local_savings / actual)) if actual else 0,
        "batch_savings_usd": round(batch_savings, 2),
        "batch_savings_pct": pct(batch_savings, actual),
        "batch_optimized_cost_usd": round(actual - batch_savings, 2),
        "batchable_turns": int(base["turns"] * _BATCHABLE_FRACTION),
        "combined_cost_usd": round(combined, 2),
        "combined_savings_usd": round(actual - combined, 2),
        "combined_savings_pct": pct(actual - combined, actual),
    }


def measured_span() -> tuple[date, date] | None:
    """First and last day for which we hold real measured data."""
    con = connect()
    r = con.execute(
        "SELECT MIN(day), MAX(day) FROM usage_daily WHERE source='measured'").fetchone()
    con.close()
    if not r or not r[0]:
        return None
    return date.fromisoformat(r[0]), date.fromisoformat(r[1])


def measured_totals(start: date | None = None, end: date | None = None) -> dict:
    """Totals over MEASURED days only — the durable calibration base.

    Reconstruction calibrates unit rates ($/turn, tokens/turn) against real
    data. Reading that base from live transcripts would make it depend on the
    very files that get deleted; the whole point of the ledger is that it
    doesn't. As measured history accumulates, this widens automatically and
    a re-run of the backfill re-derives every estimate against a larger,
    better sample.
    """
    con = connect()
    q = ("SELECT COALESCE(SUM(tokens),0), COALESCE(SUM(cache_reads),0), "
         "COALESCE(SUM(cost_usd),0), COALESCE(SUM(turns),0), COUNT(*) "
         "FROM usage_daily WHERE source='measured'")
    args: list = []
    if start:
        q += " AND day>=?"; args.append(start.isoformat())
    if end:
        q += " AND day<=?"; args.append(end.isoformat())
    r = con.execute(q, args).fetchone()
    con.close()
    return {"tokens": r[0], "cache_reads": r[1], "cost_usd": round(r[2], 2),
            "turns": r[3], "days": r[4]}


def coverage() -> list[dict]:
    """Per-source rollup — how much of the ledger is real vs reconstructed."""
    con = connect()
    rows = con.execute(
        """SELECT source, confidence, COUNT(*), MIN(day), MAX(day),
                  ROUND(SUM(cost_usd),2), SUM(tokens), SUM(turns)
             FROM usage_daily GROUP BY source, confidence
             ORDER BY MIN(day)"""
    ).fetchall()
    con.close()
    return [
        {"source": r[0], "confidence": r[1], "days": r[2], "first": r[3],
         "last": r[4], "cost_usd": r[5], "tokens": r[6], "turns": r[7]}
        for r in rows
    ]


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    print(snapshot(verbose=False))
    for c in coverage():
        print(c)

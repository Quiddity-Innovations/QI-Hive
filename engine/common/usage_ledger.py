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

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

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

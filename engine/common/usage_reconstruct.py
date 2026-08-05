"""
QI Hive — historical usage reconstruction (Feb 18 2026 -> present).

Why this exists
---------------
`usage_stats.py` has no persistent store: every figure is recomputed by
parsing ~/.claude/projects/**/*.jsonl. Claude Code deletes those transcripts
on a retention timer (`cleanupPeriodDays`, default 30), so the "Year to date"
tile silently lost history every time cleanup ran. On 2026-08-05T04:31:23Z a
cleanup pass left only 2026-06-26 onward on disk.

This module rebuilds a per-day activity timeline from artefacts that were NOT
deleted (git commits, session summary .docx filenames, qi_brain.db rows, file
mtimes), calibrates that activity against the windows we can still measure,
and emits a per-day estimate for the days whose transcripts are gone.

Every emitted row carries a `source` and `confidence` so an estimate can
never be mistaken for a measurement. Nothing here overwrites measured data.

Hard boundaries (evidence, not assumption)
------------------------------------------
  2026-01-01 .. 2026-02-17  -> ZERO. The Claude subscription was created
                               2026-02-17T22:56:38Z and Claude Code first ran
                               2026-02-18T01:50:57Z (~/.claude.json). There was
                               no account to spend on.
  2026-02-18 .. 2026-06-25  -> ESTIMATED from activity proxies.
  2026-06-26 .. present     -> MEASURED from surviving JSONL.

Calibration anchor
------------------
A dashboard screenshot saved 2026-06-19 20:30
(docs/assets/hive_screens/11_usage.png) preserves real figures for the 30-day
window ending 2026-06-19: $17,285.62 actual, 23,676 turns, ~261.6M tokens,
and full per-project / per-model tables. That window is otherwise deleted.
"""
from __future__ import annotations

import json
import re
import sqlite3
import subprocess
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

BRAIN_DB = Path(r"C:\QIH\data\qi_brain.db")
SUMMARIES = Path(r"C:\QIH\shared\documentation\session_summaries")
ARCHIVE = Path(r"C:\QIH\data\usage_archive")

# Repos that carry dated commit history for QI work.
REPOS = [
    r"C:\QI", r"C:\QIH", r"C:\NAYA", r"C:\NEXUS",
    r"C:\OC", r"C:\EasyFlow", r"C:\MQ", r"C:\Claude",
]

# Project trees whose file mtimes act as an activity proxy before git existed.
MTIME_TREES = [r"C:\QI", r"C:\NAYA", r"C:\NEXUS", r"C:\OC"]

# ── Evidence-backed boundaries ──────────────────────────────────────────
SUBSCRIPTION_START = date(2026, 2, 18)   # ~/.claude.json firstStartTime
YEAR_START = date(2026, 1, 1)

# ── Calibration anchor from the 2026-06-19 dashboard screenshot ─────────
# 30-day window ending 2026-06-19 (inclusive) — the only surviving record of
# that period. Values read directly off the saved PNG.
ANCHOR = {
    "window_end": date(2026, 6, 19),
    "window_days": 30,
    "cost_usd": 17285.62,
    "turns": 23676,          # 19673 + 759 + 459 + 1799 + 986
    "tokens": 261_600_000,   # 233.1M + 10.9M + 5.5M + 7.8M + 4.3M
    "ytd_cost_usd": 19554.0,  # YTD tile on the same screenshot
    "by_project": {
        "claude_manager": 4087.65, "mapsnap": 3834.88, "lotterywiz": 2920.87,
        "unknown": 2446.07, "digitization": 1500.90, "personalsong": 811.78,
        "nexus": 605.45, "autopdf": 492.74, "openclaw": 293.88,
        "tubescout": 203.33, "fidelityanalyzer": 74.75, "qi_hive": 9.88,
        "easyflow": 3.45,
    },
    "by_model": {
        "opus-4-8": 16264.13, "fable-5": 518.08, "opus-4-7": 389.91,
        "sonnet-4-6": 105.10, "haiku-4-5": 8.39,
    },
}


def _run(args: list[str], cwd: str | None = None) -> str:
    try:
        return subprocess.run(
            args, cwd=cwd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=120,
        ).stdout
    except Exception:
        return ""


# ── Proxy 1: git commits per day ────────────────────────────────────────
def commits_per_day() -> dict[date, int]:
    out: dict[date, int] = defaultdict(int)
    for repo in REPOS:
        if not Path(repo, ".git").exists():
            continue
        txt = _run(["git", "log", "--all", "--format=%ad", "--date=short"], cwd=repo)
        for line in txt.splitlines():
            line = line.strip()
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", line):
                out[date.fromisoformat(line)] += 1
    return dict(out)


# ── Proxy 2: session summary documents per day ──────────────────────────
def summaries_per_day() -> dict[date, int]:
    out: dict[date, int] = defaultdict(int)
    if not SUMMARIES.is_dir():
        return {}
    for f in SUMMARIES.iterdir():
        m = re.search(r"(20\d{2}-\d{2}-\d{2})", f.name)
        if m:
            try:
                out[date.fromisoformat(m.group(1))] += 1
            except ValueError:
                continue
    return dict(out)


# ── Proxy 3: qi_brain.db session_log / heartbeats per day ───────────────
def brain_rows_per_day() -> dict[date, int]:
    out: dict[date, int] = defaultdict(int)
    if not BRAIN_DB.exists():
        return {}
    con = sqlite3.connect(f"file:{BRAIN_DB}?mode=ro", uri=True)
    for sql in (
        "SELECT substr(started_at,1,10), COUNT(*) FROM session_log "
        "WHERE started_at IS NOT NULL GROUP BY 1",
        "SELECT substr(ts,1,10), COUNT(*) FROM agent_heartbeats "
        "WHERE ts IS NOT NULL GROUP BY 1",
    ):
        try:
            for ds, n in con.execute(sql):
                if ds and re.fullmatch(r"\d{4}-\d{2}-\d{2}", ds):
                    # Heartbeats are far noisier than sessions; damp them so
                    # they inform shape without dominating the index.
                    out[date.fromisoformat(ds)] += n if "session_log" in sql else max(1, n // 20)
        except sqlite3.Error:
            continue
    con.close()
    return dict(out)


# ── Proxy 4: files modified per day (reaches back before git existed) ───
def mtimes_per_day(since: date) -> dict[date, int]:
    out: dict[date, int] = defaultdict(int)
    exts = {".py", ".md", ".json", ".bat", ".ps1", ".html", ".js", ".css", ".sql", ".yaml", ".yml"}
    skip = {"node_modules", ".venv", "venv", "__pycache__", ".git", "site-packages", "_archive", "archive"}
    for tree in MTIME_TREES:
        root = Path(tree)
        if not root.is_dir():
            continue
        for p in root.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in exts:
                continue
            if any(s in p.parts for s in skip):
                continue
            try:
                d = date.fromtimestamp(p.stat().st_mtime)
            except OSError:
                continue
            if d >= since:
                out[d] += 1
    return dict(out)


def build_activity_index(start: date, end: date) -> dict[date, float]:
    """Composite per-day activity score, normalised so each proxy contributes
    comparable weight regardless of its raw scale."""
    proxies = {
        "commits":   (commits_per_day(),   3.0),
        "summaries": (summaries_per_day(), 4.0),
        "brain":     (brain_rows_per_day(), 2.0),
        "mtimes":    (mtimes_per_day(start), 1.0),
    }
    # Normalise each proxy by its own mean over active days, then weight.
    norm: dict[str, dict[date, float]] = {}
    for name, (raw, _w) in proxies.items():
        vals = [v for d, v in raw.items() if start <= d <= end and v > 0]
        mean = (sum(vals) / len(vals)) if vals else 0.0
        norm[name] = {d: (v / mean if mean else 0.0) for d, v in raw.items()}

    index: dict[date, float] = {}
    d = start
    while d <= end:
        score = 0.0
        for name, (_raw, w) in proxies.items():
            score += w * norm[name].get(d, 0.0)
        index[d] = score
        d += timedelta(days=1)
    return index


def daterange(a: date, b: date):
    d = a
    while d <= b:
        yield d
        d += timedelta(days=1)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    idx = build_activity_index(SUBSCRIPTION_START, date.today())
    active = {d: v for d, v in idx.items() if v > 0.01}
    print(f"activity index days: {len(idx)}  active: {len(active)}")
    for d in sorted(idx):
        if idx[d] > 0.01:
            print(f"  {d}  {idx[d]:7.3f}")

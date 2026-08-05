"""
QI Hive — per-project and per-model dimensions for the usage ledger.

`usage_daily` answers "what did a day cost". This module answers "cost by
which project, on which model" for every day back to 2026-01-01, so the LLM
Usage tab's By-Project / By-Model tables and its date-range picker return
coherent data for ANY window -- not just the ~40 days of surviving transcripts.

Two tables, same provenance discipline as usage_daily:

    usage_daily_project(day, project, ...)
    usage_daily_model(day, model, family, ...)

Both always reconcile: for any given day, SUM(cost_usd) across each dimension
equals that day's usage_daily.cost_usd. That invariant is what makes an
arbitrary date range add up in the UI.

How each segment is derived
---------------------------
measured days   Grouped straight from the surviving transcript events. Real.

anchored /      Split by weights:
estimated days    projects — per-day activity proxies (git commits per repo,
                             session-summary filenames, Brain session_log
                             project_id), falling back to the 2026-06-19
                             screenshot's project mix when a day has no signal.
                  models   — era mix. Model availability is datable, so we do
                             NOT smear today's model lineup across February.
                             Evidence for first-appearance:
                               sonnet-4-6  seen 2026-04-18 (Brain session_log)
                               opus-4-7    seen 2026-05-13
                               fable-5     seen 2026-06-10
                               opus-4-8    seen 2026-06-12
                               sonnet-5    seen 2026-07-01 (transcripts)
                               opus-5      seen 2026-07-29 (transcripts)
"""
from __future__ import annotations

import collections
import os as _os
import re
import sqlite3
import subprocess
import sys as _sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Importable both as `engine.common.usage_dimensions` (dashboard) and as a
# bare module (CLI). See the same note in usage_ledger.py.
_HERE = _os.path.dirname(_os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)

import usage_ledger
from usage_reconstruct import ANCHOR, REPOS, SUMMARIES, BRAIN_DB, SUBSCRIPTION_START

DDL = """
CREATE TABLE IF NOT EXISTS usage_daily_project (
    day TEXT NOT NULL, project TEXT NOT NULL,
    tokens INTEGER NOT NULL DEFAULT 0, cache_reads INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0.0, turns INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL, confidence TEXT NOT NULL, updated_at TEXT NOT NULL,
    PRIMARY KEY (day, project)
);
CREATE TABLE IF NOT EXISTS usage_daily_model (
    day TEXT NOT NULL, model TEXT NOT NULL, family TEXT NOT NULL,
    tokens INTEGER NOT NULL DEFAULT 0, cache_reads INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0.0, turns INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL, confidence TEXT NOT NULL, updated_at TEXT NOT NULL,
    PRIMARY KEY (day, model)
);
CREATE INDEX IF NOT EXISTS idx_udp_day ON usage_daily_project(day);
CREATE INDEX IF NOT EXISTS idx_udm_day ON usage_daily_model(day);
"""

# ── Model eras ──────────────────────────────────────────────────────────
# Cost-weighted mix used for days we could not measure. Bounded by observed
# first-appearance dates so a model never shows up before it existed.
_ANCHOR_MODEL_MIX = {
    "claude-opus-4-8": 0.9409, "claude-fable-5": 0.0300,
    "claude-opus-4-7": 0.0226, "claude-sonnet-4-6": 0.0061,
    "claude-haiku-4-5": 0.0005,
}
MODEL_ERAS: list[tuple[date, date, dict[str, float]]] = [
    # Pre-Claude-5. Opus 4.7 era; Brain first records sonnet-4-6 on 2026-04-18
    # and opus-4-7 on 2026-05-13, and nothing newer appears before June.
    (date(2026, 2, 18), date(2026, 6, 9),
     {"claude-opus-4-7": 0.88, "claude-sonnet-4-6": 0.10, "claude-haiku-4-5": 0.02}),
    # Fable 5 appears 2026-06-10, before Opus 4.8.
    (date(2026, 6, 10), date(2026, 6, 11),
     {"claude-opus-4-7": 0.80, "claude-fable-5": 0.08,
      "claude-sonnet-4-6": 0.10, "claude-haiku-4-5": 0.02}),
    # Opus 4.8 lands 2026-06-12 and immediately dominates — this is the mix
    # the 2026-06-19 screenshot actually recorded.
    (date(2026, 6, 12), date(2026, 6, 30), _ANCHOR_MODEL_MIX),
    # July: Sonnet 5 in the mix, Opus 5 not yet.
    (date(2026, 7, 1), date(2026, 7, 28),
     {"claude-fable-5": 0.55, "claude-opus-4-8": 0.35,
      "claude-sonnet-5": 0.07, "claude-haiku-4-5-20251001": 0.03}),
    # Opus 5 first seen in transcripts 2026-07-29.
    (date(2026, 7, 29), date(2099, 1, 1),
     {"claude-opus-5": 0.55, "claude-fable-5": 0.35,
      "claude-sonnet-5": 0.07, "claude-haiku-4-5-20251001": 0.03}),
]


def _family(name: str) -> str:
    n = (name or "").lower()
    for f in ("opus", "fable", "sonnet", "haiku"):
        if f in n:
            return f
    return "other"


def model_mix(d: date) -> dict[str, float]:
    for start, end, mix in MODEL_ERAS:
        if start <= d <= end:
            return mix
    return _ANCHOR_MODEL_MIX


# ── Project weights from activity proxies ───────────────────────────────
_REPO_TO_PROJECT = {
    "QI": "maia", "QIH": "qi_hive", "NAYA": "naya", "NEXUS": "nexus",
    "OC": "openclaw", "EASYFLOW": "easyflow", "MQ": "mq", "CLAUDE": "claude_manager",
}
_SUMMARY_PREFIX = {
    "autopdf": "autopdf", "claude": "claude_manager", "claudemanager": "claude_manager",
    "claudehive": "qi_hive", "clauddevoice": "claude_voice", "claudevoice": "claude_voice",
    "cognibase": "cognibase", "mapsnap": "mapsnap", "nexus": "nexus", "naya": "naya",
    "maia": "maia", "qihive": "qi_hive", "easyflow": "easyflow", "aws": "maia",
    "digitizationcosts": "digitization", "cypherminer": "cypherminer",
    "akiyascout": "akiyascout", "personalsong": "personalsong",
    "lotterywiz": "lotterywiz", "tubescout": "tubescout", "gamez": "gamez",
    "retirementanalyzer": "retirementanalyzer", "avatarstudio": "avatarstudio",
    "fidelityanalyzer": "fidelityanalyzer", "bakeoff": "bakeoff",
    "connector": "qi_hive", "dashboard": "qi_hive", "playdeck": "playdeck",
}


def project_weights() -> dict[date, collections.Counter]:
    """Per-day project activity weights from proxies that survived deletion."""
    w: dict[date, collections.Counter] = collections.defaultdict(collections.Counter)

    # git commits per repo
    for repo in REPOS:
        if not Path(repo, ".git").exists():
            continue
        pid = _REPO_TO_PROJECT.get(Path(repo).name.upper(), Path(repo).name.lower())
        try:
            out = subprocess.run(
                ["git", "log", "--all", "--format=%ad", "--date=short"], cwd=repo,
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=120).stdout
        except Exception:
            continue
        for line in out.splitlines():
            line = line.strip()
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", line):
                w[date.fromisoformat(line)][pid] += 3

    # session summary documents (filename carries project + date)
    if SUMMARIES.is_dir():
        for f in SUMMARIES.iterdir():
            m = re.match(r"([A-Za-z_]+?)_(?:Summary|ProjectStatus|Nightly)", f.name)
            dm = re.search(r"(20\d{2}-\d{2}-\d{2})", f.name)
            if not dm:
                continue
            key = (m.group(1).replace("_", "").lower() if m else "")
            pid = _SUMMARY_PREFIX.get(key)
            if pid:
                try:
                    w[date.fromisoformat(dm.group(1))][pid] += 6
                except ValueError:
                    pass

    # Brain session_log project_id
    if BRAIN_DB.exists():
        con = sqlite3.connect(f"file:{BRAIN_DB}?mode=ro", uri=True)
        try:
            for ds, pid, n in con.execute(
                "SELECT substr(started_at,1,10), project_id, COUNT(*) FROM session_log "
                "WHERE started_at IS NOT NULL AND project_id IS NOT NULL GROUP BY 1,2"
            ):
                if ds and re.fullmatch(r"\d{4}-\d{2}-\d{2}", ds):
                    w[date.fromisoformat(ds)][str(pid).lower()] += 2 * n
        except sqlite3.Error:
            pass
        con.close()
    return w


def _anchor_project_mix() -> dict[str, float]:
    tot = sum(ANCHOR["by_project"].values())
    return {k: v / tot for k, v in ANCHOR["by_project"].items()}


def backfill(verbose: bool = True) -> dict:
    """Rebuild both dimension tables from the day-level ledger.

    Measured days come from real transcript events; everything else is split
    by weights. Every day reconciles exactly to usage_daily.cost_usd.
    """
    import usage_stats

    con = usage_ledger.connect()
    con.executescript(DDL)
    con.execute("DELETE FROM usage_daily_project")
    con.execute("DELETE FROM usage_daily_model")

    # Real per-day/per-project and per-day/per-model splits where we have logs.
    meas_p: dict[date, collections.Counter] = collections.defaultdict(collections.Counter)
    meas_m: dict[date, collections.Counter] = collections.defaultdict(collections.Counter)
    meas_tok_p: dict[date, collections.Counter] = collections.defaultdict(collections.Counter)
    meas_tok_m: dict[date, collections.Counter] = collections.defaultdict(collections.Counter)
    meas_turns_p: dict[date, collections.Counter] = collections.defaultdict(collections.Counter)
    meas_turns_m: dict[date, collections.Counter] = collections.defaultdict(collections.Counter)
    for e in usage_stats._iter_events():
        d = e["ts"].astimezone().date()
        meas_p[d][e["project"]] += e["cost"]
        meas_m[d][e["model"]] += e["cost"]
        meas_tok_p[d][e["project"]] += e["tokens"]
        meas_tok_m[d][e["model"]] += e["tokens"]
        meas_turns_p[d][e["project"]] += 1
        meas_turns_m[d][e["model"]] += 1

    pw = project_weights()
    amix = _anchor_project_mix()
    now = datetime.now().isoformat(timespec="seconds")

    rows = con.execute(
        "SELECT day, tokens, cache_reads, cost_usd, turns, source, confidence "
        "FROM usage_daily WHERE cost_usd > 0 ORDER BY day"
    ).fetchall()

    n_p = n_m = 0
    for ds, tokens, cache, cost, turns, source, conf in rows:
        d = date.fromisoformat(ds)

        # ---- projects ----
        if source == "measured" and meas_p.get(d):
            shares = {k: v / sum(meas_p[d].values()) for k, v in meas_p[d].items()}
        else:
            wd = pw.get(d)
            shares = ({k: v / sum(wd.values()) for k, v in wd.items()} if wd else dict(amix))
        for proj, sh in shares.items():
            if sh <= 0:
                continue
            con.execute(
                "INSERT OR REPLACE INTO usage_daily_project VALUES (?,?,?,?,?,?,?,?,?)",
                (ds, proj, int(tokens * sh), int(cache * sh), cost * sh,
                 int(round(turns * sh)), source, conf, now))
            n_p += 1

        # ---- models ----
        if source == "measured" and meas_m.get(d):
            shares = {k: v / sum(meas_m[d].values()) for k, v in meas_m[d].items()}
        else:
            mm = model_mix(d)
            tot = sum(mm.values())
            shares = {k: v / tot for k, v in mm.items()}
        for mdl, sh in shares.items():
            if sh <= 0:
                continue
            con.execute(
                "INSERT OR REPLACE INTO usage_daily_model VALUES (?,?,?,?,?,?,?,?,?,?)",
                (ds, mdl, _family(mdl), int(tokens * sh), int(cache * sh), cost * sh,
                 int(round(turns * sh)), source, conf, now))
            n_m += 1

    con.commit()

    # Reconciliation check — this is the invariant the UI depends on.
    bad = con.execute("""
        SELECT COUNT(*) FROM (
          SELECT d.day, d.cost_usd c, IFNULL(SUM(p.cost_usd),0) pc
          FROM usage_daily d LEFT JOIN usage_daily_project p ON p.day=d.day
          WHERE d.cost_usd>0 GROUP BY d.day
          HAVING ABS(c-pc) > 0.02)""").fetchone()[0]
    bad_m = con.execute("""
        SELECT COUNT(*) FROM (
          SELECT d.day, d.cost_usd c, IFNULL(SUM(m.cost_usd),0) mc
          FROM usage_daily d LEFT JOIN usage_daily_model m ON m.day=d.day
          WHERE d.cost_usd>0 GROUP BY d.day
          HAVING ABS(c-mc) > 0.02)""").fetchone()[0]
    con.close()
    if verbose:
        print(f"project rows: {n_p:,}   model rows: {n_m:,}")
        print(f"reconciliation mismatches — projects: {bad}  models: {bad_m}")
    return {"project_rows": n_p, "model_rows": n_m,
            "unreconciled_projects": bad, "unreconciled_models": bad_m}


# ── Read-back API (mirrors usage_stats shapes) ──────────────────────────
def by_project(start: date, end: date) -> list[dict]:
    con = usage_ledger.connect()
    rows = con.execute(
        """SELECT project, SUM(tokens), SUM(cost_usd), SUM(turns),
                  ROUND(100.0*SUM(CASE WHEN source='measured' THEN cost_usd ELSE 0 END)
                        /NULLIF(SUM(cost_usd),0),0)
             FROM usage_daily_project WHERE day>=? AND day<=?
             GROUP BY project ORDER BY SUM(cost_usd) DESC""",
        (start.isoformat(), end.isoformat())).fetchall()
    con.close()
    return [{"project": r[0], "tokens": r[1], "cost_usd": round(r[2], 2),
             "turns": r[3], "measured_pct": r[4] or 0} for r in rows]


def by_model(start: date, end: date) -> list[dict]:
    con = usage_ledger.connect()
    rows = con.execute(
        """SELECT model, family, SUM(tokens), SUM(cost_usd), SUM(turns),
                  ROUND(100.0*SUM(CASE WHEN source='measured' THEN cost_usd ELSE 0 END)
                        /NULLIF(SUM(cost_usd),0),0)
             FROM usage_daily_model WHERE day>=? AND day<=?
             GROUP BY model ORDER BY SUM(cost_usd) DESC""",
        (start.isoformat(), end.isoformat())).fetchall()
    con.close()
    return [{"model": r[0], "family": r[1], "tokens": r[2], "cost_usd": round(r[3], 2),
             "turns": r[4], "measured_pct": r[5] or 0} for r in rows]


def _savings_rows(rows: list[dict], key: str) -> list[dict]:
    """Shape a dimension breakdown into the what-if columns the UI renders.

    Local offload is applied per model family (Opus/Fable stay on Claude);
    for projects the family split isn't known per row, so the window's blended
    offload rate is used. Batch discount uses the measured batchable fraction,
    since reconstructed days carry no hour-of-day.
    """
    import usage_stats
    from usage_ledger import _BATCHABLE_FRACTION

    out = []
    for r in rows:
        actual = r["cost_usd"]
        fam = r.get("family")
        frac = (usage_stats.LOCAL_OFFLOAD_BY_FAMILY.get(fam, 0.0) if fam
                else r.get("_blend", 0.0))
        local_opt = actual * (1 - frac)
        batch_opt = actual * (1 - usage_stats.BATCH_DISCOUNT * _BATCHABLE_FRACTION)
        combined = local_opt * (1 - usage_stats.BATCH_DISCOUNT * _BATCHABLE_FRACTION)
        out.append({
            key: r[key], "family": fam, "tokens": r["tokens"], "turns": r["turns"],
            "measured_pct": r.get("measured_pct", 0),
            "actual_usd": round(actual, 2), "local_opt_usd": round(local_opt, 2),
            "batch_opt_usd": round(batch_opt, 2), "combined_usd": round(combined, 2),
            "total_savings_usd": round(actual - combined, 2),
            "total_savings_pct": round(((actual - combined) / actual) * 100, 1) if actual else 0.0,
        })
    return out


def savings_by_model(start: date, end: date) -> list[dict]:
    return _savings_rows(by_model(start, end), "model")


def savings_by_project(start: date, end: date) -> list[dict]:
    rows = by_project(start, end)
    # Blend the window's local-offload rate from the model mix, then apply it
    # uniformly across projects — per-project family splits aren't tracked.
    import usage_stats
    mrows = by_model(start, end)
    tot = sum(m["cost_usd"] for m in mrows) or 1.0
    blend = sum(m["cost_usd"] * usage_stats.LOCAL_OFFLOAD_BY_FAMILY.get(m["family"], 0.0)
                for m in mrows) / tot
    for r in rows:
        r["_blend"] = blend
    return _savings_rows(rows, "project")


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    print(backfill())
    print("\ntop projects YTD:")
    for r in by_project(date(2026, 1, 1), date.today())[:10]:
        print(f"  {r['project']:<20} ${r['cost_usd']:>10,.2f}  {r['measured_pct']:>3.0f}% measured")
    print("\nby model YTD:")
    for r in by_model(date(2026, 1, 1), date.today()):
        print(f"  {r['model']:<28} ${r['cost_usd']:>10,.2f}  {r['measured_pct']:>3.0f}% measured")

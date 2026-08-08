# -*- coding: utf-8 -*-
"""
Live status refresh — the "real-time" half of the Hive pipeline.

The nightly reconciler (C:\\QIH\\tools\\nightly_reconcile.py) rebuilds the
dashboard's project tiles + git activity ONCE a day at 02:30. That meant a full
day's work was invisible on the dashboard until the next morning.

This module performs the *light* part of that job — git-commit backfill into
session_log + merge of Brain project_state into status.json — cheaply enough to
run on a short interval from the QI_HiveIngest service loop. It deliberately
does NOT run the heavy nightly steps (compliance deep-scan, doc harvest with
embeddings); those stay nightly.

It reuses `regenerate_views` from nightly_reconcile so the status.json merge
logic lives in exactly one place.
"""
from __future__ import annotations
import sqlite3
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import sys

# nightly_reconcile holds the canonical DB path, project list, and the
# status.json merge logic. Import it as the single source of truth.
_TOOLS = r"C:\QIH\tools"
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)
import nightly_reconcile as nr  # noqa: E402


def light_refresh(window_days: int = 2) -> dict:
    """Backfill recent git commits into session_log and merge Brain status into
    status.json (incl. recent_sessions dedupe). Returns a small stats dict.

    Cheap by design: a few `git log` calls + two small SQLite reads + one JSON
    write. Safe to call every minute or two.
    """
    cutoff = (datetime.now() - timedelta(days=window_days)).strftime("%Y-%m-%d")
    con = sqlite3.connect(nr.DB, timeout=10.0)
    try:
        cur = con.cursor()

        # Build the set of session titles we already have in the window so we
        # never insert a commit twice.
        existing = set()
        for r in cur.execute(
            "SELECT project_id, session_title FROM session_log WHERE started_at >= ?",
            (cutoff,),
        ):
            existing.add((r[0], (r[1] or "")[:80]))

        git_added = 0
        for pid, path in nr.GIT_PROJECTS.items():
            if not Path(path, ".git").exists():
                continue
            try:
                out = subprocess.run(
                    ["git", "-C", path, "log", f"--since={cutoff}", "--format=%ai|%s"],
                    capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=15,
                )
            except Exception:
                continue
            if out.returncode != 0:
                continue
            for line in out.stdout.splitlines():
                if "|" not in line:
                    continue
                when, msg = line.split("|", 1)
                when = when.strip()[:19]
                msg = msg.strip()
                title = f"commit: {msg[:100]}"
                key = (pid, title[:80])
                if key in existing:
                    continue
                cur.execute(
                    "INSERT INTO session_log (project_id, agent_id, session_title, "
                    "summary, decisions_made, features_logged, files_changed, "
                    "next_steps, model_used, started_at, ended_at) "
                    "VALUES (?,'git-live',?,?,0,0,'[]','','git-only',?,?)",
                    (pid, title, f"Git commit: {msg}", when, when),
                )
                existing.add(key)
                git_added += 1

        con.commit()

        # Merge Brain project_state -> status.json (also dedupes recent_sessions).
        refreshed = nr.regenerate_views(cur, source="hive_ingest live refresh")
    finally:
        con.close()

    return {"git_added": git_added, "projects_refreshed": refreshed}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(light_refresh())

# -*- coding: utf-8 -*-
"""
inspector_export_snapshot.py — export QI Hive Inspector compliance snapshots
from qi_brain.db into the per-day JSON files that Sentry's weekly drift report
expects.

WHY THIS EXISTS
---------------
`sentry-weekly-drift.sh` reads:
    C:\\QIH\\engine\\hive\\inspector\\reports\\compliance-YYYY-MM-DD.json
and diffs the two most recent ones via the LLM router.

That directory has NEVER existed. The Inspector persists its results to the
`compliance_log` table in qi_brain.db, not to JSON files. So Sentry has been
hitting its own guard clause —

    log "Inspector reports dir not found: $REPORTS_DIR — skipping (no error)"
    exit 0

— every single Sunday since the task was created, exiting 0 and reporting
success while never once producing a drift report. Found by the 2026-08-27 QI
scheduled-task health audit. It is the "born dead, reports healthy" class: no
regression ever happened, it simply never worked.

This exporter is the bridge. It reads the real data and writes the artifact
Sentry already knows how to consume, so neither side needs restructuring.

USAGE
-----
    python inspector_export_snapshot.py              # export today's snapshot
    python inspector_export_snapshot.py --backfill 60  # also rebuild last 60 days
    python inspector_export_snapshot.py --list       # show what exists

One file per DAY, built from that day's LAST inspector run (a day can hold
several runs — QI_ComplianceFast fires every 4h). Idempotent: re-running
overwrites the same day's file with the same content.
"""
import argparse
import json
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

DB = r"C:\QIH\data\qi_brain.db"
REPORTS_DIR = r"C:\QIH\engine\hive\inspector\reports"


def connect():
    # read-only: this tool must never be able to damage the brain DB
    return sqlite3.connect("file:" + DB.replace("\\", "/") + "?mode=ro", uri=True)


def day_runs(con, days):
    """Return {day: last_run_id} for the most recent `days` distinct days."""
    rows = con.execute(
        "SELECT DATE(recorded_at) AS d, run_id, MAX(recorded_at) AS ts "
        "FROM compliance_log "
        "WHERE recorded_at IS NOT NULL "
        "GROUP BY d, run_id "
        "ORDER BY d DESC, ts DESC"
    ).fetchall()

    best = {}
    for d, run_id, ts in rows:
        if d and d not in best:          # first seen per day == latest run that day
            best[d] = run_id
    ordered = sorted(best.items(), reverse=True)[:days]
    return dict(ordered)


def build_snapshot(con, day, run_id):
    rows = con.execute(
        "SELECT project_id, check_id, status, severity, auto_fixable, "
        "       action_taken, message, fix_action "
        "FROM compliance_log WHERE run_id = ? ORDER BY project_id, check_id",
        (run_id,),
    ).fetchall()

    projects = defaultdict(list)
    counts = defaultdict(int)
    for pid, check, status, sev, autofix, action, msg, fix in rows:
        counts[status] = counts[status] + 1
        # a snapshot is for diffing — carry only what distinguishes one week
        # from the next, not the full prose
        if status in ("warn", "fail", "error"):
            projects[pid].append(
                {
                    "check_id": check,
                    "status": status,
                    "severity": sev,
                    "auto_fixable": bool(autofix),
                    "action_taken": action,
                    "message": (msg or "")[:400],
                    "fix_action": (fix or "")[:200],
                }
            )

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "generated_by": "inspector_export_snapshot.py",
        "day": day,
        "run_id": run_id,
        "totals": dict(counts),
        "issue_count": sum(len(v) for v in projects.values()),
        "project_count": len(projects),
        "projects": {k: v for k, v in sorted(projects.items())},
    }


def write_snapshot(snap):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    path = os.path.join(REPORTS_DIR, "compliance-%s.json" % snap["day"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snap, f, indent=2, ensure_ascii=False)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill", type=int, default=1,
                    help="how many recent days to export (default 1 = today's latest run)")
    ap.add_argument("--list", action="store_true", help="list existing snapshots and exit")
    args = ap.parse_args()

    if args.list:
        if not os.path.isdir(REPORTS_DIR):
            print("No reports dir yet:", REPORTS_DIR)
            return 0
        files = sorted(os.listdir(REPORTS_DIR), reverse=True)
        print("%d snapshot(s) in %s" % (len(files), REPORTS_DIR))
        for f in files[:20]:
            print("  ", f)
        return 0

    if not os.path.exists(DB):
        print("FATAL: brain DB not found:", DB)
        return 1

    con = connect()
    try:
        runs = day_runs(con, args.backfill)
        if not runs:
            print("No compliance_log rows found — nothing to export.")
            return 1
        for day, run_id in sorted(runs.items()):
            snap = build_snapshot(con, day, run_id)
            path = write_snapshot(snap)
            print("wrote %s  (%d issues across %d projects, run %s)"
                  % (os.path.basename(path), snap["issue_count"],
                     snap["project_count"], run_id[:8]))
    finally:
        con.close()

    print("OK ->", REPORTS_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())

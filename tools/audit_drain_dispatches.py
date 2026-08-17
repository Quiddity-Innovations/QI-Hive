# -*- coding: utf-8 -*-
"""
One-shot repair: drain the stale dispatch queue in qi_brain.db.

Background (2026-08-17 audit)
----------------------------
The compliance Inspector files dispatches faithfully but nothing consumes them,
so the queue had grown to 27 pending (oldest 2026-06-18, 60 days) plus 9
'approved' rows that were never anything but May e2e test fixtures.

Three categories are closed here:

  1. TEST FIXTURES  — dispatch ids matching the May 13-14 auto-apply e2e run
     (test-auto-apply-*, e2e-*, sanity-*) against synthetic projects. Never
     represented real work.

  2. SUPERSEDED     — an older pending dispatch for the same (project, check_id)
     where a newer one exists. Only the newest is actionable; the rest are the
     same finding re-filed on each nightly run.

  3. ID-ARTEFACT    — session_freshness / brain_drift raised while the project's
     activity was being logged under a non-canonical id (see
     audit_fix_brain_ids.py). The premise was wrong, not the project.

Rows are marked resolved with an explanatory note rather than deleted, so the
audit trail survives. Safe to re-run: idempotent.
"""
from __future__ import annotations
import json, sqlite3, sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DB = Path(r"C:\QIH\data\qi_brain.db")
STAMP = datetime.now().strftime("%Y-%m-%d")

FIXTURE_PREFIXES = ("test-auto-apply", "e2e-", "sanity-")
FIXTURE_PROJECTS = {"qi_e2e_test", "qi_e2e_sanity"}

# Projects whose activity was logged under a wrong id until the 2026-08-17 fix.
ID_ARTEFACT_PROJECTS = {"qi_hive", "nexus", "openclaw", "maia", "claude_voice"}
ID_ARTEFACT_CHECKS = {"session_freshness", "brain_drift"}


def main(apply: bool) -> int:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "select dispatch_id, project_id, status, created_at, payload "
        "from dispatches where status in ('pending','approved') order by created_at"
    ).fetchall()

    def check_of(r):
        try:
            return json.loads(r["payload"] or "{}").get("check_id", "")
        except Exception:
            return ""

    # Newest pending dispatch per (project, check) — everything older is superseded.
    newest: dict[tuple, str] = {}
    for r in rows:
        if r["status"] != "pending":
            continue
        newest[(r["project_id"], check_of(r))] = r["dispatch_id"]

    # Which (project, check) pairs are PASS or SKIP in the most recent run? A
    # dispatch describing a problem that no longer exists is noise, and leaving it
    # open is how the queue silently refilled after the underlying issues were
    # actually fixed. This is the rule that makes the queue self-healing.
    latest_run = con.execute(
        "SELECT run_id FROM compliance_log ORDER BY log_id DESC LIMIT 1"
    ).fetchone()
    now_passing: set[tuple] = set()
    if latest_run:
        for row in con.execute(
            "SELECT project_id, check_id FROM compliance_log "
            "WHERE run_id=? AND status IN ('pass','skip')", (latest_run["run_id"],)
        ):
            now_passing.add((row["project_id"], row["check_id"]))

    actions: list[tuple[str, str, str]] = []   # (dispatch_id, reason, note)
    for r in rows:
        did, pid, chk = r["dispatch_id"], r["project_id"], check_of(r)

        if r["status"] == "pending" and (pid, chk) in now_passing:
            actions.append((did, "now_passing",
                            f"[{STAMP} audit] Closed: check '{chk}' no longer reports a problem for "
                            f"{pid} in the latest compliance run (pass or intentionally skipped)."))
            continue

        if did.startswith(FIXTURE_PREFIXES) or pid in FIXTURE_PROJECTS:
            actions.append((did, "test_fixture",
                            f"[{STAMP} audit] Closed: May 13-14 auto-apply e2e test fixture, "
                            f"never real work."))
            continue

        if r["status"] == "pending" and newest.get((pid, chk)) != did:
            actions.append((did, "superseded",
                            f"[{STAMP} audit] Closed: superseded by a newer '{chk}' "
                            f"dispatch for {pid}."))
            continue

        if (r["status"] == "pending" and chk in ID_ARTEFACT_CHECKS
                and pid in ID_ARTEFACT_PROJECTS):
            actions.append((did, "id_artefact",
                            f"[{STAMP} audit] Closed: raised while {pid} activity was logged "
                            f"under a non-canonical project_id; premise invalid. "
                            f"See tools/audit_fix_brain_ids.py."))
            continue

    by_reason: dict[str, int] = {}
    for _, reason, _ in actions:
        by_reason[reason] = by_reason.get(reason, 0) + 1

    print(f"queue before : {len(rows)} open ({sum(1 for r in rows if r['status']=='pending')} pending, "
          f"{sum(1 for r in rows if r['status']=='approved')} approved)")
    print(f"closing      : {len(actions)}")
    for k, v in sorted(by_reason.items()):
        print(f"    {k:14} {v}")
    print(f"left open    : {len(rows) - len(actions)}")

    if not apply:
        print("\nDRY RUN — pass --apply to write.")
        for did, reason, _ in actions:
            print(f"    {reason:14} {did}")
        return 0

    with con:
        for did, reason, note in actions:
            con.execute(
                "update dispatches set status='resolved', reviewed_by='audit_2026-08-17', "
                "reviewed_at=?, notes=coalesce(notes,'') || ? where dispatch_id=?",
                (datetime.now().isoformat(timespec="seconds"), " " + note, did),
            )
    print(f"\nclosed {len(actions)} dispatch(es)")

    remaining = con.execute(
        "select project_id, payload from dispatches where status in ('pending','approved') "
        "order by created_at"
    ).fetchall()
    print(f"\nstill open ({len(remaining)}) — these are genuinely actionable:")
    for r in remaining:
        try:
            p = json.loads(r["payload"] or "{}")
        except Exception:
            p = {}
        print(f"    {str(r['project_id']):14} {p.get('check_id','?'):20} {str(p.get('message',''))[:60]}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main("--apply" in sys.argv))

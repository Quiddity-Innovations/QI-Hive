# -*- coding: utf-8 -*-
"""
backfill_unknown_runs.py — one-off re-attribution of the 409 agent='unknown_subagent'
rows found in the 2026-09-16 QI Hive audit (agent_hr.db).

These rows were written by agent_hr.py's cmd_ingest_hook() before the
2026-09-16 fix: the real SubagentStop hook payload almost never carries a
subagent_type, and most of these particular runs have no matching Task
tool_use anywhere in their transcript at all (verified against several
sessions, e.g. Godseye 0e348b9a-...) — they are Claude Code's own internal
subagent-style events (e.g. auto-compaction), not user-dispatched sub-agents.
So `agent` genuinely cannot be recovered for these and MUST stay
'unknown_subagent' per the audit's own instruction.

What CAN be recovered: `project` was stored as the raw cwd path instead of a
canonical registry id. This script re-resolves it with the same
longest-registry-path logic every other QI usage stat uses
(engine/common/usage_stats._project_from_cwd), imported, not copied.

Never deletes or reassigns agent/model/task_desc — only updates `project`
where resolution changes it, and only for rows with agent='unknown_subagent'.
Safe to re-run: rows already holding a canonical id resolve to themselves.
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = r"C:\QIH\engine\hive\agents\agent_hr.db"
COMMON_DIR = r"C:\QIH\engine\common"

sys.path.insert(0, COMMON_DIR)
from usage_stats import _project_from_cwd  # noqa: E402


def main():
    conn = sqlite3.connect(DB_PATH)

    before_unknown_agent = conn.execute(
        "SELECT COUNT(*) FROM runs WHERE agent = 'unknown_subagent'"
    ).fetchone()[0]
    before_raw_project = conn.execute(
        "SELECT COUNT(*) FROM runs WHERE agent = 'unknown_subagent' AND project LIKE '%:\\%'"
    ).fetchone()[0]

    rows = conn.execute(
        "SELECT id, project FROM runs WHERE agent = 'unknown_subagent'"
    ).fetchall()

    updated = 0
    unresolved = []
    for rid, project in rows:
        canonical = _project_from_cwd(project, "")
        if canonical != project:
            conn.execute("UPDATE runs SET project = ? WHERE id = ?", (canonical, rid))
            updated += 1
            if canonical == "unknown":
                unresolved.append((rid, project))

    conn.commit()

    after_unknown_agent = conn.execute(
        "SELECT COUNT(*) FROM runs WHERE agent = 'unknown_subagent'"
    ).fetchone()[0]
    after_raw_project = conn.execute(
        "SELECT COUNT(*) FROM runs WHERE agent = 'unknown_subagent' AND project LIKE '%:\\%'"
    ).fetchone()[0]

    print(f"rows examined:               {len(rows)}")
    print(f"rows with project updated:   {updated}")
    print(f"agent='unknown_subagent'     before={before_unknown_agent}  after={after_unknown_agent}  (agent is never changed by this script)")
    print(f"project still a raw path     before={before_raw_project}  after={after_raw_project}")
    if unresolved:
        print(f"{len(unresolved)} row(s) had no registry match, project set to 'unknown':")
        for rid, project in unresolved[:20]:
            print(f"  id={rid} raw_project={project!r}")

    conn.close()


if __name__ == "__main__":
    main()

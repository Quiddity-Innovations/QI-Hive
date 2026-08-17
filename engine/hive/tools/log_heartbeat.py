#!/usr/bin/env python
"""Write one row to agent_heartbeats. Called from Claude Code hooks."""
import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

DB = Path(r"C:\QIH\data\qi_brain.db")
REGISTRY = Path(r"C:\QIH\ecosystem\qi_registry.json")


def canonical_project_id(pid: str | None) -> str | None:
    """Map a caller-supplied project id onto the canonical registry id.

    This writer goes straight to SQLite, bypassing the Brain API — so the
    API's _resolve_pid() never sees these rows. The Claude Code hooks passed
    '--project qihive' for months, and 5231 of 5375 heartbeats (97%) landed
    under 'qihive' instead of 'qi_hive'. Every session-freshness query then saw
    a near-idle project and the Inspector filed false alerts for months.

    Normalising here means the hooks can be sloppy without corrupting the data.
    Unknown ids are returned unchanged — a heartbeat is telemetry and must never
    fail the hook. (2026-08-17 audit.)
    """
    if not pid:
        return pid
    try:
        ids = {p["id"] for p in json.loads(REGISTRY.read_text(encoding="utf-8"))["projects"]}
    except Exception:
        return pid
    if pid in ids:
        return pid
    flat = {re.sub(r"[^a-z0-9]", "", i.lower()): i for i in ids}
    return flat.get(re.sub(r"[^a-z0-9]", "", pid.lower()), pid)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--agent", required=True, help="agent_id (e.g. hive-builder, claude_code, cowork)")
    p.add_argument("--kind", default="subagent", choices=["interactive", "subagent", "service"])
    p.add_argument("--event", default="stop", choices=["start", "tool_call", "stop", "heartbeat"])
    p.add_argument("--project", default=None, help="project_id (qihive, maia, naya, ...)")
    p.add_argument("--session", default=None, help="session_ref")
    p.add_argument("--model", default=None)
    p.add_argument("--meta", default=None, help="optional JSON string")
    args = p.parse_args()

    if not DB.exists():
        print(f"DB missing: {DB}", file=sys.stderr)
        sys.exit(2)

    try:
        conn = sqlite3.connect(str(DB), timeout=2.0)
        conn.execute(
            "INSERT INTO agent_heartbeats (agent_id, agent_kind, event, project_id, session_ref, model, meta_json) "
            "VALUES (?,?,?,?,?,?,?)",
            (args.agent, args.kind, args.event, canonical_project_id(args.project),
             args.session, args.model, args.meta),
        )
        conn.commit()
        conn.close()
    except sqlite3.OperationalError as e:
        # DB locked — drop the heartbeat rather than block the hook
        print(f"heartbeat write skipped (locked): {e}", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"heartbeat error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

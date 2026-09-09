# -*- coding: utf-8 -*-
# AI-GENERATED BEGIN (Claude Code, 2026-09-08)
"""Record a Trinity assistant run in Agent HR from the command line.

Usage:
  python C:\\QIH\\engine\\tools\\qi_trinity_hr_log.py --agent codex --model gpt-5.6-luna \
      --task "what was asked and how it was verified" --outcome pass [--tool-uses N] [--duration-ms N] [--session ID]

Rows land in project 'trinity' (same as qi_trinity_check.py) so :8600/agents shows every
assistant call. Never pass prompt text or secrets in --task; describe, don't quote.
"""
import argparse
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\QIH\engine\hive\agents")
import agent_hr  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True, choices=["codex", "gemini"])
    ap.add_argument("--model", required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--outcome", required=True, choices=["pass", "fail", "partial", "error"])
    ap.add_argument("--tool-uses", type=int, default=0)
    ap.add_argument("--duration-ms", type=int, default=None)
    ap.add_argument("--session", default="claude_manager")
    a = ap.parse_args()
    conn = agent_hr.get_conn()
    agent_hr.ensure_schema(conn)
    run = {
        "agent": a.agent, "project": "trinity", "task_desc": a.task[:400],
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "duration_ms": a.duration_ms, "tokens": None, "tool_uses": a.tool_uses,
        "outcome": a.outcome, "session_id": a.session, "model": a.model,
    }
    added, agent_added = agent_hr.record_run(conn, run, "qi_trinity_hr_log")
    conn.commit()
    print(f"agent={a.agent} model={a.model} outcome={a.outcome} run_added={added}")
    return 0 if added else 1


if __name__ == "__main__":
    sys.exit(main())
# AI-GENERATED END

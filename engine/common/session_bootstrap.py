# -*- coding: utf-8 -*-
"""SessionStart hook helper.

Emits JSON to stdout per Claude Code hook protocol:
  {"hookSpecificOutput": {"hookEventName": "SessionStart",
                          "additionalContext": "<text>"}}

Combines:
  1. QI Brain context (qi.get_context) if Brain API is up at :9010
  2. C:\\QIH\\docs\\LATEST.md (cross-session broadcast board)
  3. Also emits hive_report session_start (fire-and-forget)

Silent-on-failure: any error -> empty additionalContext, exit 0, so
it never blocks the session from starting.

Usage (from .claude/settings.json):
    python C:\\QIH\\engine\\common\\session_bootstrap.py --project Maia
"""
from __future__ import annotations
import argparse, json, sys, subprocess, urllib.request, urllib.error
from pathlib import Path

BRAIN_URL = "http://127.0.0.1:9010"
LATEST_MD = Path(r"C:\QIH\docs\LATEST.md")
HIVE_REPORT = Path(r"C:\QIH\engine\common\hive_report.py")


def fetch_brain_context(project_id: str, timeout: float = 2.5) -> str:
    try:
        req = urllib.request.Request(
            f"{BRAIN_URL}/api/context",
            data=json.dumps({"project_id": project_id}).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", errors="replace"))
        lines = [f"### QI Brain context for `{project_id}`"]
        cs = data.get("current_state") or {}
        if cs:
            lines.append(f"- **Phase:** {cs.get('phase','?')} | **Status:** {cs.get('status','?')}")
            if cs.get("summary"):
                lines.append(f"- **Summary:** {cs['summary']}")
            if cs.get("next_steps"):
                lines.append(f"- **Next steps:** {cs['next_steps']}")
        decs = data.get("recent_decisions") or []
        if decs:
            lines.append("\n**Recent decisions:**")
            for d in decs[:5]:
                lines.append(f"  - {d.get('title','?')} \u2014 {(d.get('rationale') or '')[:140]}")
        sess = data.get("recent_sessions") or []
        if sess:
            lines.append("\n**Recent sessions:**")
            for s in sess[:3]:
                lines.append(f"  - {s.get('session_title','?')} ({(s.get('started_at') or '')[:10]})")
        return "\n".join(lines)
    except (urllib.error.URLError, TimeoutError, ConnectionError, ValueError):
        return ""
    except Exception:
        return ""


def read_latest() -> str:
    try:
        if LATEST_MD.exists():
            txt = LATEST_MD.read_text(encoding="utf-8", errors="replace")
            if len(txt) > 8000:
                txt = txt[:8000] + "\n\n... [truncated]"
            return f"### Cross-session broadcast ({LATEST_MD})\n\n{txt}"
    except Exception:
        pass
    return ""


def fire_hive_report(project: str) -> None:
    try:
        subprocess.Popen(
            ["python", str(HIVE_REPORT), "session_start", "--project", project,
             "--summary", "session opened"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=0x08000000 if sys.platform == "win32" else 0,
        )
    except Exception:
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, help="Display name (Maia, Naya, NEXUS, EasyFlow, QI Hive)")
    ap.add_argument("--project-id", default=None, help="Brain project_id (defaults to lower(project))")
    args = ap.parse_args()

    pid = args.project_id or args.project.lower().replace(" ", "_")

    fire_hive_report(args.project)

    parts = []
    brain = fetch_brain_context(pid)
    if brain:
        parts.append(brain)
    latest = read_latest()
    if latest:
        parts.append(latest)

    additional = "\n\n---\n\n".join(parts) if parts else ""

    out = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": additional,
        }
    }
    sys.stdout.write(json.dumps(out))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.stdout.write('{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":""}}')
        sys.exit(0)

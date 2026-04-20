# -*- coding: utf-8 -*-
"""Stop hook helper.

Reads the Claude Code hook payload from stdin (per hook protocol):
  { "session_id": "...", "transcript_path": "...", ... }

Parses the transcript (JSONL) to extract:
  - session title (first user message, truncated)
  - summary (last assistant message, truncated)
  - files touched (Edit/Write tool calls)
  - decisions (look for "decision:" / "decided:" / "chose " markers)

Posts qi.log_session to the Brain API at :9010.
Also fires the existing hive_report session_end (fire-and-forget).

Silent-on-failure. Exit 0 always so it never blocks session close.

Usage (from .claude/settings.json Stop hook):
    python C:\\QIH\\engine\\common\\session_stop.py --project Maia --project-id maia
"""
from __future__ import annotations
import argparse, json, sys, subprocess, urllib.request, urllib.error, re
from datetime import datetime
from pathlib import Path

BRAIN_URL = "http://127.0.0.1:9010"
HIVE_REPORT = Path(r"C:\QIH\engine\common\hive_report.py")

DECISION_PATTERNS = [
    r"(?:^|\n)\s*[-*]\s*(?:decision|decided|chose|choosing)\s*[:\-]\s*(.+)",
    r"(?:^|\n)\s*(?:decision|decided)\s*[:\-]\s*(.+)",
]


def read_payload() -> dict:
    try:
        data = sys.stdin.read()
        return json.loads(data) if data else {}
    except Exception:
        return {}


def parse_transcript(path: str) -> dict:
    info = {"title": "", "summary": "", "files": [], "decisions": []}
    if not path:
        return info
    p = Path(path)
    if not p.exists():
        return info
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return info

    first_user, last_assistant = None, None
    for line in lines:
        try:
            evt = json.loads(line)
        except Exception:
            continue
        etype = evt.get("type")
        msg = evt.get("message") or {}
        role = msg.get("role") or evt.get("role")
        content = msg.get("content") or evt.get("content") or ""

        if isinstance(content, list):
            text_parts, tool_uses = [], []
            for c in content:
                if not isinstance(c, dict):
                    continue
                if c.get("type") == "text":
                    text_parts.append(c.get("text", ""))
                elif c.get("type") == "tool_use":
                    tool_uses.append(c)
            content_text = "\n".join(text_parts)
            for tu in tool_uses:
                name = tu.get("name", "")
                inp = tu.get("input") or {}
                if name in ("Edit", "Write", "NotebookEdit") and inp.get("file_path"):
                    fp = inp["file_path"]
                    if fp not in info["files"]:
                        info["files"].append(fp)
        else:
            content_text = str(content)

        if role == "user" and first_user is None and content_text.strip():
            first_user = content_text.strip()
        if role == "assistant" and content_text.strip():
            last_assistant = content_text.strip()

        for pat in DECISION_PATTERNS:
            for m in re.finditer(pat, content_text, re.IGNORECASE):
                d = m.group(1).strip().rstrip(".")
                if 10 < len(d) < 250 and d not in info["decisions"]:
                    info["decisions"].append(d)

    if first_user:
        info["title"] = first_user.splitlines()[0][:120]
    if last_assistant:
        info["summary"] = last_assistant[:1500]
    info["files"] = info["files"][:50]
    info["decisions"] = info["decisions"][:20]
    return info


def post_brain(endpoint: str, body: dict, timeout: float = 3.0) -> bool:
    try:
        req = urllib.request.Request(
            f"{BRAIN_URL}{endpoint}",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= r.status < 300
    except Exception:
        return False


def fire_hive_report(project: str, summary: str) -> None:
    try:
        subprocess.Popen(
            ["python", str(HIVE_REPORT), "session_end", "--project", project,
             "--summary", summary or "session closed"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=0x08000000 if sys.platform == "win32" else 0,
        )
    except Exception:
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--project-id", default=None)
    args = ap.parse_args()

    pid = args.project_id or args.project.lower().replace(" ", "_")
    payload = read_payload()
    tpath = payload.get("transcript_path") or ""
    info = parse_transcript(tpath)

    title = info["title"] or f"{args.project} session {datetime.now():%Y-%m-%d %H:%M}"
    summary = info["summary"] or "session closed"

    fire_hive_report(args.project, summary[:200])

    post_brain("/api/log_session", {
        "project_id": pid,
        "session_title": title,
        "summary": summary,
        "files_changed": info["files"],
        "decisions_made": info["decisions"],
        "features_logged": [],
        "next_steps": "",
        "model_used": payload.get("model", ""),
    })

    for d in info["decisions"][:10]:
        post_brain("/api/log_decision", {
            "project_id": pid,
            "title": d[:120],
            "rationale": d,
            "impact_scope": "project",
            "tags": ["auto-extracted"],
        })

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)

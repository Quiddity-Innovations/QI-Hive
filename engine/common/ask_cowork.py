# -*- coding: utf-8 -*-
"""
ask_cowork.py — Claude Code's outbound channel to Claude Work.

Usage (from any Claude Code session):
    from engine.common.ask_cowork import ask_cowork

    ask_cowork(
        type="request",
        payload={
            "task": "Generate a session summary .docx for the Maia project",
            "context": "Files changed: maia_server.py, config.py. Decisions: switched to FastAPI.",
            "output_path": "C:/QIH/shared/documentation/session_summaries/Maia_Summary_2026-04-20_1800.docx",
            "format": "docx",
        },
        priority="normal",
        project_id="maia",
    )

CoWork reads dispatch files from C:/QIH/cowork-dispatch/ at session start.
Each file is also logged to QI Brain via /api/dispatch for dashboard visibility.

Types Claude Code typically sends to CoWork:
    request   — ask CoWork to produce a document, report, brief, or analysis
    brief     — pre-brief CoWork before a session so it has context
    review    — ask CoWork to review a decision before it's logged
    flag      — flag something for CoWork's strategic attention
"""
from __future__ import annotations
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
_THIS   = Path(__file__).parent                     # engine/common/
_QIH    = _THIS.parent.parent                       # C:\QIH
DISPATCH_DIR = _QIH / "cowork-dispatch"
BRAIN_URL    = "http://localhost:9010"

sys.path.insert(0, str(_QIH / "engine" / "brain"))


def ask_cowork(
    type: str,
    payload: dict,
    priority: str = "normal",
    project_id: str | None = None,
    source: str = "claude_code",
) -> str:
    """
    Write a dispatch file for CoWork AND log it to QI Brain.

    Returns the dispatch_id.

    type:       request | brief | review | flag | task | decision
    payload:    free-form dict — describe what you need CoWork to do
    priority:   high | normal | low
    project_id: lowercase project id (maia | naya | nexus | qi_hive | ...)
    source:     who is sending (default: claude_code)
    """
    did = str(uuid.uuid4())
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")

    dispatch = {
        "dispatch_id": did,
        "source":      source,
        "type":        type,
        "priority":    priority,
        "project":     project_id,
        "payload":     payload,
        "created_at":  datetime.now().isoformat(),
        "reply_path":  str(_QIH / "shared" / "reports" / "inbox" / f"reply_{did}.json"),
    }

    # 1. Write to cowork-dispatch folder (CoWork reads these at session start)
    DISPATCH_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"dispatch_{ts}_{type}_{did[:8]}.json"
    out   = DISPATCH_DIR / fname
    out.write_text(json.dumps(dispatch, indent=2, ensure_ascii=False), encoding="utf-8")

    # 2. Also log to QI Brain (appears on dashboard, survives folder cleanup)
    try:
        import urllib.request
        body = json.dumps({
            "dispatch_id": did,
            "source":      source,
            "type":        type,
            "priority":    priority,
            "project_id":  project_id,
            "payload":     payload,
            "reply_path":  dispatch["reply_path"],
        }).encode()
        req = urllib.request.Request(
            f"{BRAIN_URL}/api/dispatch", data=body,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        urllib.request.urlopen(req, timeout=3)
    except Exception:
        pass  # Brain offline — file dispatch is sufficient

    print(f"[ask_cowork] Dispatch written: {fname} (id={did[:8]})", flush=True)
    return did


# ── Convenience wrappers ───────────────────────────────────────────────────────

def request_document(task: str, output_path: str, format: str = "docx",
                     context: str = "", project_id: str | None = None,
                     priority: str = "normal") -> str:
    """Ask CoWork to produce a document."""
    return ask_cowork(
        type="request",
        payload={"task": task, "output_path": output_path, "format": format, "context": context},
        priority=priority,
        project_id=project_id,
    )


def send_brief(session_title: str, context: str, project_id: str,
               next_steps: list[str] | None = None) -> str:
    """Brief CoWork before a session so it has full context."""
    return ask_cowork(
        type="brief",
        payload={"session_title": session_title, "context": context,
                 "project_id": project_id, "next_steps": next_steps or []},
        priority="normal",
        project_id=project_id,
    )


def flag_for_cowork(issue: str, project_id: str | None = None, priority: str = "normal") -> str:
    """Flag something strategic for CoWork's attention."""
    return ask_cowork(
        type="flag",
        payload={"issue": issue},
        priority=priority,
        project_id=project_id,
    )


if __name__ == "__main__":
    # Quick test — sends a sample request
    sys.stdout.reconfigure(encoding="utf-8")
    did = ask_cowork(
        type="request",
        payload={
            "task": "Confirm receipt of dispatch system. Reply to reply_path with a brief hello.",
            "context": "This is the first test of the Claude Code → CoWork dispatch channel.",
        },
        priority="low",
        project_id="qi_hive",
    )
    print(f"[TEST] Dispatch sent. ID: {did}")

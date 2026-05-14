# -*- coding: utf-8 -*-
"""
Thin client for QI Brain API (port 9011).
Dashboard uses this to pull live hive state — agents, sessions, decisions.
Falls back gracefully if Brain is offline.
"""
import json
import urllib.request
import urllib.error
from typing import Any

BRAIN_URL = "http://localhost:9011"
TIMEOUT   = 3  # seconds — dashboard must stay fast


def _get(path: str) -> dict | None:
    try:
        with urllib.request.urlopen(f"{BRAIN_URL}{path}", timeout=TIMEOUT) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def _post(path: str, payload: dict) -> dict | None:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            f"{BRAIN_URL}{path}", data=data,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def brain_online() -> bool:
    r = _get("/health")
    return bool(r and r.get("status") == "ok")


def get_agents() -> list[dict]:
    r = _get("/api/agents?active_only=true")
    return r.get("agents", []) if r else []


def get_ecosystem_snapshot() -> dict:
    r = _get("/api/ecosystem_snapshot")
    return r or {}


def get_recent_sessions(limit: int = 5) -> list[dict]:
    snap = get_ecosystem_snapshot()
    return snap.get("recent_sessions", [])[:limit]


def get_agent_profile(agent_id: str) -> dict | None:
    return _get(f"/api/agent/{agent_id}/profile")


def log_growth(agent_id: str, session_ref: str, task_summary: str,
               what_worked: str = None, what_to_improve: str = None,
               pattern_learned: str = None, project_id: str = None) -> dict | None:
    return _post("/api/agent/growth", {
        "agent_id": agent_id,
        "session_ref": session_ref,
        "task_summary": task_summary,
        "what_worked": what_worked,
        "what_to_improve": what_to_improve,
        "pattern_learned": pattern_learned,
        "project_id": project_id,
    })


def get_brain_status() -> dict:
    r = _get("/api/status")
    return r or {"error": "offline"}

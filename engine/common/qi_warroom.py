# -*- coding: utf-8 -*-
"""
QI War Room — shared poster for the multi-agent chat (Phase N Stage 0).

Any QI agent (Claude Code, Claude Work, CoWork, the 7 Hive agents) posts to the
War Room with one call. Prefers the Brain HTTP endpoint; if Brain hasn't been
restarted with the new route yet, falls back to a direct (WAL-safe) write to
qi_brain.db so the room is always writable.

Usage:
    from engine.common.qi_warroom import post, recent
    post("claude_code", "Build finished — tests green.")
    for m in recent(20):
        print(m["agent_label"], ":", m["body"])

See: C:\\QIH\\shared\\documentation\\Phase_N_War_Room_Spec_2026-06-18.md
"""
import json
import sqlite3
import urllib.request
from pathlib import Path
from typing import Optional

BRAIN_URL = "http://127.0.0.1:9011"
BRAIN_DB  = Path(r"C:\QIH\data\qi_brain.db")

_LABELS = {
    "renne": "Renne", "claude_code": "Claude Code", "claude": "Claude (Interactive)",
    "claude_work": "Claude Work", "cowork": "CoWork", "architect": "Architect",
    "builder": "Builder", "inspector": "Inspector", "ops": "Ops", "scout": "Scout",
    "scribe": "Scribe", "tester": "Tester",
}


def _label(agent_id: str) -> str:
    return _LABELS.get(agent_id, agent_id)


def _post_http(agent_id: str, body: str, project_id: Optional[str]) -> Optional[int]:
    try:
        data = json.dumps({"agent_id": agent_id, "body": body,
                           "project_id": project_id}).encode()
        req = urllib.request.Request(
            f"{BRAIN_URL}/api/warroom/message", data=data,
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=3) as r:
            return json.loads(r.read().decode()).get("id")
    except Exception:
        return None


def _post_db(agent_id: str, body: str, project_id: Optional[str]) -> Optional[int]:
    if not BRAIN_DB.exists():
        return None
    try:
        conn = sqlite3.connect(str(BRAIN_DB), timeout=5.0)
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA busy_timeout = 5000")
            cur = conn.execute(
                """INSERT INTO warroom_messages (agent_id, agent_label, body, project_id)
                   VALUES (?, ?, ?, ?)""",
                (agent_id, _label(agent_id), body, project_id))
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()
    except Exception:
        return None


def post(agent_id: str, body: str, project_id: Optional[str] = None) -> Optional[int]:
    """Post a message to the War Room. Returns the new row id, or None on failure.

    Tries the Brain HTTP endpoint first; falls back to a direct DB write so the
    room works even before Brain has reloaded the new route.
    """
    body = (body or "").strip()
    if not body:
        return None
    return _post_http(agent_id, body, project_id) or _post_db(agent_id, body, project_id)


def recent(limit: int = 50) -> list[dict]:
    """Return the most recent `limit` messages in chronological order."""
    if not BRAIN_DB.exists():
        return []
    try:
        conn = sqlite3.connect(f"file:{BRAIN_DB}?mode=ro", uri=True, timeout=3.0)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """SELECT id, agent_id, agent_label, body, project_id, ts
                   FROM warroom_messages ORDER BY id DESC LIMIT ?""",
                (max(1, min(limit, 500)),)).fetchall()
            return [dict(r) for r in rows][::-1]
        finally:
            conn.close()
    except Exception:
        return []


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) >= 3:
        rid = post(sys.argv[1], " ".join(sys.argv[2:]))
        print(f"posted id={rid}")
    else:
        for m in recent(20):
            print(f"[{m['ts'][:16]}] {m['agent_label']}: {m['body']}")

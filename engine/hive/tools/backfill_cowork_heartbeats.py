#!/usr/bin/env python
"""Backfill cowork heartbeats from existing approved dispatches.

Run once. Safe to re-run — skips any dispatch_id already in agent_heartbeats.
"""
import sqlite3
from pathlib import Path

DB = Path(r"C:\QIH\data\qi_brain.db")

conn = sqlite3.connect(str(DB))

existing = {
    r[0]
    for r in conn.execute(
        "SELECT meta_json FROM agent_heartbeats WHERE agent_id='cowork' AND meta_json IS NOT NULL"
    ).fetchall()
    if r[0]
}

rows = conn.execute(
    "SELECT dispatch_id, project_id, COALESCE(reviewed_at, created_at) "
    "FROM dispatches "
    "WHERE reviewed_at IS NOT NULL OR apply_state IS NOT NULL"
).fetchall()

inserted = 0
for did, pid, ts in rows:
    did_str = str(did)
    if any(did_str in (e or "") for e in existing):
        continue
    conn.execute(
        "INSERT INTO agent_heartbeats (agent_id, agent_kind, event, project_id, ts, meta_json) "
        "VALUES ('cowork','service','stop',?,?,?)",
        (pid or "qihive", ts, '{"dispatch_id":"' + did_str + '"}'),
    )
    inserted += 1

conn.commit()
conn.close()
print(f"inserted {inserted} cowork heartbeats")

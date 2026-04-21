# -*- coding: utf-8 -*-
"""
Migration: add dispatches table + cowork agent to qi_brain.db
Run once: python C:\QIH\tools\migrate_add_dispatches.py
"""
import sys
sys.path.insert(0, r"C:\QIH\engine\brain")
from core.db import open_brain_db

SQL = """
CREATE TABLE IF NOT EXISTS dispatches (
    dispatch_id   TEXT    PRIMARY KEY,
    source        TEXT    NOT NULL,   -- cowork | claude_code | renne | maia | naya
    type          TEXT    NOT NULL,   -- report|brief|decision|task|review|proposal|request
    priority      TEXT    NOT NULL DEFAULT 'normal',  -- high|normal|low
    project_id    TEXT    REFERENCES projects(project_id),
    payload       TEXT    NOT NULL,   -- JSON blob
    status        TEXT    NOT NULL DEFAULT 'pending',  -- pending|approved|declined|discussing|executed
    reply_path    TEXT,
    notes         TEXT,               -- JSON array of discussion notes
    reviewed_by   TEXT,
    reviewed_at   TEXT,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

SEED_AGENT = """
INSERT OR IGNORE INTO agents (agent_id, display_name, agent_type)
VALUES ('cowork', 'Claude Work', 'claude');
"""

with open_brain_db() as conn:
    conn.execute(SQL)
    conn.execute(SEED_AGENT)
    conn.commit()
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    agents = [r[0] for r in conn.execute("SELECT agent_id FROM agents").fetchall()]

print(f"[OK] dispatches table ready. Tables: {tables}")
print(f"[OK] agents: {agents}")

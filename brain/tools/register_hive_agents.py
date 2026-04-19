# -*- coding: utf-8 -*-
"""
Register the 7 QI Hive agents in QI Brain's agents table.
Also adds agent_growth_log table for the learning loop.
Run once: python register_hive_agents.py
"""
import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).parent.parent / "qi_brain.db"

HIVE_AGENTS = [
    ("hive_architect",  "Architect",  "hive", "Designs systems and features before anyone builds. Produces blueprints, ADRs, implementation plans."),
    ("hive_builder",    "Builder",    "hive", "Executes Architect plans. Writes Python, SQL, config. Gets things done."),
    ("hive_scout",      "Scout",      "hive", "Researches tools, APIs, AI news. Fast and cheap. First responder for unknowns."),
    ("hive_scribe",     "Scribe",     "hive", "Writes all documentation, session summaries, meeting minutes."),
    ("hive_ops",        "Ops",        "hive", "Monitors services, restarts things, checks logs. Ecosystem custodian."),
    ("hive_inspector",  "Inspector",  "hive", "Reviews code and config for quality, security, QI standards compliance."),
    ("hive_tester",     "Tester",     "hive", "Runs API, UI, and load tests across all QI projects. Cross-project quality guardian."),
]

GROWTH_LOG_DDL = """
CREATE TABLE IF NOT EXISTS agent_growth_log (
    growth_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id        TEXT NOT NULL REFERENCES agents(agent_id),
    session_ref     TEXT,
    project_id      TEXT REFERENCES projects(project_id),
    task_summary    TEXT NOT NULL,
    what_worked     TEXT,
    what_to_improve TEXT,
    pattern_learned TEXT,
    tags            TEXT,
    recorded_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_growth_agent   ON agent_growth_log(agent_id);
CREATE INDEX IF NOT EXISTS idx_growth_project ON agent_growth_log(project_id);
CREATE INDEX IF NOT EXISTS idx_growth_pattern ON agent_growth_log(pattern_learned) WHERE pattern_learned IS NOT NULL;
"""

AGENT_TYPE_PATCH = """
-- Widen agent_type CHECK to include 'hive' variants
-- SQLite doesn't support ALTER COLUMN — handled by INSERT OR IGNORE logic
"""

def run():
    print(f"Connecting to {DB}")
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    # 1. Patch agents table to accept 'hive' type
    #    SQLite can't ALTER a CHECK constraint — we recreate only if needed.
    cur = con.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='agents'")
    row = cur.fetchone()
    if row and "'hive'" not in row[0]:
        print("Patching agents table to allow agent_type='hive'...")
        con.executescript("""
            BEGIN;
            ALTER TABLE agents RENAME TO agents_old;
            CREATE TABLE agents (
                agent_id     TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                agent_type   TEXT NOT NULL CHECK(agent_type IN (
                                  'claude','maia','nexus','naya','system','hive')),
                active       INTEGER NOT NULL DEFAULT 1,
                description  TEXT,
                created_at   TEXT NOT NULL DEFAULT (datetime('now'))
            );
            INSERT INTO agents (agent_id, display_name, agent_type, active, created_at)
                SELECT agent_id, display_name, agent_type, active, created_at FROM agents_old;
            DROP TABLE agents_old;
            COMMIT;
        """)
        print("  agents table patched.")
    else:
        # Add description column if missing
        cols = [r[1] for r in con.execute("PRAGMA table_info(agents)")]
        if "description" not in cols:
            con.execute("ALTER TABLE agents ADD COLUMN description TEXT")
            con.commit()
            print("  Added description column to agents.")

    # 2. Register hive agents
    print("Registering hive agents...")
    for agent_id, display_name, agent_type, description in HIVE_AGENTS:
        con.execute(
            "INSERT OR IGNORE INTO agents (agent_id, display_name, agent_type, description) VALUES (?,?,?,?)",
            (agent_id, display_name, agent_type, description)
        )
        print(f"  {agent_id} -> {display_name}")
    con.commit()

    # 3. Add agent_growth_log table
    print("Creating agent_growth_log table...")
    con.executescript(GROWTH_LOG_DDL)
    con.commit()
    print("  agent_growth_log ready.")

    # 4. Verify
    agents = con.execute("SELECT agent_id, display_name, agent_type FROM agents ORDER BY agent_type, agent_id").fetchall()
    print(f"\nAll agents in QI Brain ({len(agents)}):")
    for a in agents:
        print(f"  [{a['agent_type']:8}] {a['agent_id']:20} — {a['display_name']}")

    con.close()
    print("\nDone.")

if __name__ == "__main__":
    run()

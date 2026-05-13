"""Revert project_id QI_Hive -> qi_hive in qi_brain.db."""
import sqlite3
import sys

DB = r"C:\QIH\data\qi_brain.db"
OLD = "QI_Hive"
NEW = "qi_hive"

TARGETS = [
    ("projects", "project_id"),
    ("project_state", "project_id"),
    ("decisions", "project_id"),
    ("session_log", "project_id"),
    ("dispatches", "project_id"),
    ("agent_growth_log", "project_id"),
    ("archived_decisions", "project_id"),
    ("scope_drops", "project_id"),
    ("brain_inbox_log", "project_id"),
    ("features", "source_project"),
    ("feature_evaluations", "target_project"),
    ("archived_features", "source_project"),
]

db = sqlite3.connect(DB, timeout=10)
db.execute("PRAGMA foreign_keys = OFF")

try:
    with db:
        for table, col in TARGETS:
            cur = db.execute(
                f"UPDATE {table} SET {col}=? WHERE {col}=?", (NEW, OLD)
            )
            if cur.rowcount:
                print(f"  {table}.{col}: {cur.rowcount} row(s) reverted")
    print(f"\nDone. '{OLD}' -> '{NEW}' committed.")
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
finally:
    db.execute("PRAGMA foreign_keys = ON")
    db.close()

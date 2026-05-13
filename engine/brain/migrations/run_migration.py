# -*- coding: utf-8 -*-
"""
Run a named migration SQL file against qi_brain.db.

Usage:
    python run_migration.py 2026_05_13_auto_apply

ALTER TABLE statements will fail if the column already exists; this is caught
and logged as a no-op so the script is safe to re-run.
"""
import sys
import sqlite3
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

_HERE = Path(__file__).parent
_DB   = Path(r"C:\QIH\data\qi_brain.db")


def run(migration_name: str) -> None:
    sql_path = _HERE / f"{migration_name}.sql"
    if not sql_path.exists():
        print(f"[ERROR] Migration file not found: {sql_path}")
        sys.exit(1)

    sql = sql_path.read_text(encoding="utf-8")
    conn = sqlite3.connect(str(_DB), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")

    # Strip line comments, then split on ';'
    clean_lines = [ln for ln in sql.splitlines() if not ln.strip().startswith("--")]
    clean_sql = "\n".join(clean_lines)
    statements = [s.strip() for s in clean_sql.split(";") if s.strip()]
    applied = 0
    for stmt in statements:
        try:
            conn.execute(stmt)
            conn.commit()
            print(f"[OK]   {stmt[:80]}")
            applied += 1
        except sqlite3.OperationalError as exc:
            msg = str(exc)
            if "duplicate column" in msg.lower() or "already exists" in msg.lower():
                print(f"[SKIP] Already applied: {stmt[:80]}")
            else:
                print(f"[FAIL] {msg}  |  stmt: {stmt[:80]}")
                conn.close()
                sys.exit(1)

    conn.close()
    print(f"\n[DONE] {migration_name}: {applied} statements applied against {_DB}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_migration.py <migration_name>")
        sys.exit(1)
    run(sys.argv[1])

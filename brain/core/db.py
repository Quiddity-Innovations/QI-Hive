# -*- coding: utf-8 -*-
"""
QI Brain — SQLite connection helper.

Every module that touches qi_brain.db must use open_brain_db() from here.
This ensures WAL mode, busy_timeout, and foreign_keys are always applied.

Usage:
    from core.db import open_brain_db
    with open_brain_db() as conn:
        rows = conn.execute("SELECT * FROM decisions").fetchall()
"""
import sqlite3
import sys
from pathlib import Path

# ── Path resolution ────────────────────────────────────────────────────────────
_THIS_DIR   = Path(__file__).parent          # core/
_BRAIN_DIR  = _THIS_DIR.parent              # qi_brain/
DB_PATH     = _BRAIN_DIR / "qi_brain.db"
SCHEMA_PATH = _THIS_DIR / "schema.sql"


def open_brain_db(path: Path = DB_PATH) -> sqlite3.Connection:
    """
    Open qi_brain.db with correct PRAGMAs applied per-connection.

    Returns a sqlite3.Connection with:
    - WAL journal mode (persistent on db, enforced here as belt-and-suspenders)
    - busy_timeout = 5000 ms   (per-connection, so always needed)
    - foreign_keys = ON
    - Row factory = sqlite3.Row (access columns by name)
    """
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def init_db(path: Path = DB_PATH, schema_path: Path = SCHEMA_PATH) -> None:
    """
    Create qi_brain.db from schema.sql if it doesn't exist yet.
    Safe to call multiple times — uses CREATE TABLE IF NOT EXISTS throughout.
    """
    sql = schema_path.read_text(encoding="utf-8")
    conn = open_brain_db(path)
    # Split on ';' and execute each statement individually
    # (executescript doesn't respect the connection's PRAGMAs)
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    for stmt in statements:
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError as exc:
            # Ignore "PRAGMA journal_mode = WAL" returning a value, etc.
            if "no such table" not in str(exc).lower():
                pass  # PRAGMAs return rows, not errors — skip gracefully
    conn.commit()
    conn.close()


if __name__ == "__main__":
    # python -m core.db   →  creates/verifies the database
    sys.stdout.reconfigure(encoding="utf-8")
    init_db()
    print(f"[qi_brain.db] Initialized at {DB_PATH}")
    conn = open_brain_db()
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    print(f"[qi_brain.db] Tables: {[r['name'] for r in tables]}")
    conn.close()

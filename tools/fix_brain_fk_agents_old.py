# -*- coding: utf-8 -*-
"""
fix_brain_fk_agents_old.py — one-shot migration.

The brain schema was partially migrated from `agents_old` -> `agents`, but FK
references in several tables still point to the dropped `agents_old` table.
With foreign_keys=ON, INSERTs fail with:
    sqlite3.OperationalError: no such table: main.agents_old

Fix: for each affected table, read its CURRENT CREATE TABLE sql from
sqlite_master, rewrite `"agents_old"` -> `agents`, rebuild with SQLite's
standard table-swap. Preserves all columns & rows exactly as-is.

Safe to re-run — any table without "agents_old" in its DDL is left alone.
"""
from __future__ import annotations
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

DB = Path(r"C:\QIH\data\qi_brain.db")

AFFECTED = ["project_state", "decisions", "features",
            "feature_evaluations", "session_log"]


def table_ddl(conn: sqlite3.Connection, name: str) -> str | None:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row[0] if row else None


def table_cols(conn: sqlite3.Connection, name: str) -> list[str]:
    return [r[1] for r in conn.execute(f"PRAGMA table_info({name})").fetchall()]


def main() -> None:
    backup = DB.with_suffix(f".db.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(DB, backup)
    print(f"Backup: {backup}")

    conn = sqlite3.connect(str(DB))
    conn.execute("PRAGMA foreign_keys=OFF")

    for table in AFFECTED:
        ddl = table_ddl(conn, table)
        if not ddl:
            print(f"  skip {table} (not in db)")
            continue
        if '"agents_old"' not in ddl:
            print(f"  ok   {table} (already clean)")
            continue

        new_name = f"{table}__newfk"
        new_ddl = ddl.replace(f"CREATE TABLE {table}", f"CREATE TABLE {new_name}")
        new_ddl = new_ddl.replace('"agents_old"', "agents")
        cols = ", ".join(table_cols(conn, table))

        print(f"  fix  {table}: rebuilding with FK -> agents")
        conn.executescript(
            f"BEGIN;\n{new_ddl};\n"
            f"INSERT INTO {new_name} ({cols}) SELECT {cols} FROM {table};\n"
            f"DROP TABLE {table};\n"
            f"ALTER TABLE {new_name} RENAME TO {table};\n"
            f"COMMIT;"
        )

    conn.execute("PRAGMA foreign_keys=ON")
    errs = conn.execute("PRAGMA foreign_key_check").fetchall()
    print("FK check:", "clean" if not errs else errs)
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()

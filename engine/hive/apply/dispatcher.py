# -*- coding: utf-8 -*-
"""
QI_HiveApply — dispatcher.

Every 10 seconds main.py calls run_once(). We SELECT the oldest queued run,
hand it to runner.py, then return. Only one run is processed per cycle to
enforce the global-mutex-of-one rule from the design doc.
"""
import logging
import sqlite3
from pathlib import Path

from runner import handle_run

_DB_PATH  = Path(r"C:\QIH\data\qi_brain.db")
_HALT     = Path(r"C:\QIH\engine\hive\apply\HALT")

log = logging.getLogger("hive_apply.dispatcher")


def _open_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def run_once() -> None:
    """Pick up one queued dispatch_run (if any) and process it."""
    if _HALT.exists():
        _drain_queued_under_kill_switch()
        return

    with _open_db() as conn:
        existing = conn.execute(
            "SELECT 1 FROM dispatch_runs WHERE state='in_progress' LIMIT 1"
        ).fetchone()
        if existing:
            log.debug("Concurrency mutex: run already in_progress — skipping cycle")
            return

        row = conn.execute(
            "SELECT id, dispatch_id FROM dispatch_runs WHERE state='queued' ORDER BY id ASC LIMIT 1"
        ).fetchone()

    if row is None:
        return

    run_id     = row["id"]
    dispatch_id = row["dispatch_id"]
    log.info("Dispatcher picked up run_id=%d dispatch_id=%s", run_id, dispatch_id)
    handle_run(run_id, dispatch_id)


def _drain_queued_under_kill_switch() -> None:
    """HALT file present — reject all queued runs without processing them."""
    with _open_db() as conn:
        queued = conn.execute(
            "SELECT id, dispatch_id FROM dispatch_runs WHERE state='queued'"
        ).fetchall()
        if not queued:
            return

        log.warning("Kill switch active — rejecting %d queued run(s)", len(queued))
        now = _now()
        for row in queued:
            conn.execute(
                """UPDATE dispatch_runs
                   SET state='rejected_auto', finished_at=?, error='kill switch active'
                   WHERE id=?""",
                (now, row["id"])
            )
            conn.execute(
                """UPDATE dispatches SET apply_state='rejected_auto' WHERE dispatch_id=?""",
                (row["dispatch_id"],)
            )
            _write_compliance_log(conn, row["dispatch_id"], "dispatch.rejected_auto")
        conn.commit()


def _now() -> str:
    from datetime import datetime
    return datetime.utcnow().isoformat()


def _write_compliance_log(conn: sqlite3.Connection, dispatch_id: str, event: str) -> None:
    conn.execute(
        """INSERT INTO compliance_log
               (run_id, project_id, check_id, status, severity, action_taken, message, dispatch_id, mode)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            f"hive_apply_{dispatch_id}",
            "qi_hive",
            "auto_apply",
            "info",
            "low",
            "QI_HiveApply",
            f"actor=QI_HiveApply event={event} ref={dispatch_id}",
            None,   # compliance_log.dispatch_id is INTEGER; NULL here (we use message for ref)
            "fast",
        ),
    )

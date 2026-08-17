# -*- coding: utf-8 -*-
"""
QI_HiveApply — dispatcher.

Every 10 seconds main.py calls run_once(). We SELECT the oldest queued run,
hand it to runner.py, then return. Only one run is processed per cycle to
enforce the global-mutex-of-one rule from the design doc.
"""
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from runner import handle_run, _resolve_pending_reviews

# How long a run may sit 'in_progress' before the concurrency guard treats it as
# dead. Generous relative to a real run (which completes in seconds) but short
# enough that a crash cannot wedge the loop for months. (2026-08-17 audit.)
_STALE_RUN_MINUTES = 15


def _is_stale(started_at: str | None) -> bool:
    """True if `started_at` is missing or older than _STALE_RUN_MINUTES.

    A missing/unparseable timestamp counts as stale: a run we cannot date is a
    run we cannot trust to still be alive, and refusing to expire it is what
    wedges the dispatcher.
    """
    if not started_at:
        return True
    text = str(started_at).strip().replace("T", " ").split(".")[0]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.now() - datetime.strptime(text, fmt) > timedelta(minutes=_STALE_RUN_MINUTES)
        except ValueError:
            continue
    return True

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
        # Step 1: Resolve any pending_review runs that have received a verdict.
        # Runs in the same connection so _resolve_pending_reviews can commit inside.
        _resolve_pending_reviews(conn)

        # Step 2: Concurrency guard — only one active run at a time.
        #
        # The guard MUST expire. If a run dies mid-flight (process killed, git
        # hung on a credential prompt, machine rebooted) its row stays
        # 'in_progress' forever, and this mutex then skips every cycle for all
        # eternity — at debug level, so the service looks healthy while doing
        # nothing at all. That is precisely what happened: the May 2026 run
        # test-auto-apply-003 still carries error='stale_lock_cleared_2026-05-14'
        # from someone clearing this by hand, and the underlying bug was never
        # fixed. It is the reason the pipeline appeared idle rather than broken.
        # (2026-08-17 audit.)
        existing = conn.execute(
            "SELECT id, dispatch_id, started_at FROM dispatch_runs "
            "WHERE state='in_progress' ORDER BY id ASC LIMIT 1"
        ).fetchone()
        if existing:
            if _is_stale(existing["started_at"]):
                log.warning(
                    "Stale lock: run_id=%s dispatch_id=%s has been in_progress since %s "
                    "(> %d min) — marking failed and continuing.",
                    existing["id"], existing["dispatch_id"],
                    existing["started_at"], _STALE_RUN_MINUTES,
                )
                conn.execute(
                    "UPDATE dispatch_runs SET state='failed', finished_at=datetime('now'), "
                    "error=? WHERE id=?",
                    (f"stale_lock_expired_after_{_STALE_RUN_MINUTES}min", existing["id"]),
                )
                conn.execute(
                    "UPDATE dispatches SET apply_state='failed' WHERE dispatch_id=?",
                    (existing["dispatch_id"],),
                )
                conn.commit()
                # Fall through: this cycle may now pick up the next queued run.
            else:
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

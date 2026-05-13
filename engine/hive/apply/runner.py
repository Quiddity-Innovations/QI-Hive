# -*- coding: utf-8 -*-
"""
QI_HiveApply — runner (Phase 1: inbox-fallback mode).

For each queued dispatch_run:
  1. Load the dispatch from qi_brain.db.
  2. Check allowlist categories — reject_auto if not in Phase 1 list.
  3. Persist guardrail limits as JSON in dispatch_runs.meta.
  4. Write prompt envelope to C:\\QIH\\inbox\\hive_builder\\<dispatch_id>.json.
  5. Transition state: queued -> in_progress, record started_at + worktree placeholder.
  6. Log every state change to compliance_log.

Phase 2 will replace step 4/5 with a headless Claude Code subprocess.
The HALT check lives in dispatcher.py before handle_run() is called.
"""
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

_DB_PATH   = Path(r"C:\QIH\data\qi_brain.db")
_INBOX_DIR = Path(r"C:\QIH\inbox\hive_builder")
_WORKTREE_ROOT = Path(r"C:\QIH\worktrees\apply")

# Phase 1 allowlist (Decision D)
_ALLOWED_CATEGORIES = {"typo_fix", "doc_link_correction", "gitignore_addition"}

# Phase 1 guardrail defaults
_MAX_FILES = 1
_MAX_LINES = 40
_FORBIDDEN_PATHS = [
    ".env",
    "*.db",
    "qi_registry.json",
    "QI_Standards.md",
    "QI_Architecture_Principles.md",
    "QI_Service_Registry.md",
    r"C:\Windows",
    r"C:\Program Files",
]

log = logging.getLogger("hive_apply.runner")


def _open_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _now() -> str:
    return datetime.utcnow().isoformat()


def _log_compliance(conn: sqlite3.Connection, dispatch_id: str, event: str, message: str = "") -> None:
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
            f"actor=QI_HiveApply event={event} ref={dispatch_id}" + (f" | {message}" if message else ""),
            None,
            "fast",
        ),
    )


def handle_run(run_id: int, dispatch_id: str) -> None:
    """Process one queued dispatch_run. All state transitions happen here."""
    _INBOX_DIR.mkdir(parents=True, exist_ok=True)
    _WORKTREE_ROOT.mkdir(parents=True, exist_ok=True)

    with _open_db() as conn:
        dispatch = conn.execute(
            "SELECT * FROM dispatches WHERE dispatch_id=?", (dispatch_id,)
        ).fetchone()

    if dispatch is None:
        log.error("run_id=%d: dispatch_id=%s not found in DB — rejecting", run_id, dispatch_id)
        _reject(run_id, dispatch_id, "dispatch not found in DB")
        return

    try:
        payload = json.loads(dispatch["payload"]) if isinstance(dispatch["payload"], str) else dispatch["payload"]
    except Exception:
        payload = {}

    fix_category = payload.get("fix_category") or payload.get("check_id") or ""

    # ── Step 1: Allowlist check ────────────────────────────────────────────────
    if fix_category not in _ALLOWED_CATEGORIES:
        log.info(
            "run_id=%d dispatch_id=%s: fix_category=%r not in allowlist — rejecting",
            run_id, dispatch_id, fix_category
        )
        _reject(
            run_id, dispatch_id,
            f"fix_category '{fix_category}' not in Phase 1 allowlist {sorted(_ALLOWED_CATEGORIES)}"
        )
        return

    # ── Step 2: Persist guardrail limits in dispatch_runs.meta ───────────────
    meta = {
        "guardrails": {
            "max_files": _MAX_FILES,
            "max_lines": _MAX_LINES,
            "forbidden_paths": _FORBIDDEN_PATHS,
        },
        "fix_category": fix_category,
        "phase": 1,
        "mode": "inbox_fallback",
    }

    worktree_placeholder = str(_WORKTREE_ROOT / dispatch_id)

    with _open_db() as conn:
        conn.execute(
            """UPDATE dispatch_runs
               SET state='in_progress', started_at=?, worktree_path=?, meta=?
               WHERE id=?""",
            (_now(), worktree_placeholder, json.dumps(meta), run_id)
        )
        conn.execute(
            "UPDATE dispatches SET apply_state='in_progress', apply_run_id=? WHERE dispatch_id=?",
            (run_id, dispatch_id)
        )
        _log_compliance(conn, dispatch_id, "dispatch.in_progress")
        conn.commit()

    log.info("run_id=%d dispatch_id=%s: state -> in_progress", run_id, dispatch_id)

    # === Phase 2 enforcement gate (NOT YET ACTIVE) ===
    # Before the headless builder runs in Phase 2, this point MUST enforce:
    #   - forbidden_paths: .env*, *.db, qi_registry.json, QI_Standards.md,
    #     QI_Architecture_Principles.md, QI_Service_Registry.md, C:\Windows, C:\Program Files*
    #   - forbidden_ops: deletes, renames, mode changes, binary writes, NSSM/service config edits
    #   - max_files_changed = 1, max_lines (added+removed) = 40
    # These are documented in dispatch_runs.meta for human reviewers in Phase 1.
    # Phase 2 builder: DO NOT bypass this gate — it is the only thing between an approved
    # dispatch and a destructive write to the live tree.

    # ── Step 3: Write prompt envelope to inbox ────────────────────────────────
    envelope = {
        "dispatch_id":    dispatch_id,
        "project_id":     dispatch["project_id"] or "",
        "suggested_fix":  payload.get("suggested_fix", ""),
        "rationale":      payload.get("message", ""),
        "allowed_paths":  [],                      # Phase 2 will populate from project config
        "max_diff_lines": _MAX_LINES,
        "fix_category":   fix_category,
        "worktree_path":  worktree_placeholder,
    }

    inbox_path = _INBOX_DIR / f"{dispatch_id}.json"
    inbox_path.write_text(json.dumps(envelope, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("run_id=%d dispatch_id=%s: prompt envelope written to %s", run_id, dispatch_id, inbox_path)

    # ── Step 4: Final state — in_progress, inbox written, operator picks up ──
    # Phase 1 stops here. The run stays in_progress until an operator (interactive
    # Claude Code session) acts on the inbox file and manually transitions state.
    with _open_db() as conn:
        _log_compliance(conn, dispatch_id, "dispatch.inbox_written", str(inbox_path))
        conn.commit()

    log.info(
        "run_id=%d dispatch_id=%s: Phase 1 complete — awaiting operator pickup at %s",
        run_id, dispatch_id, inbox_path
    )

    # === Phase 2 commit/push gate (NOT YET ACTIVE) ===
    # Before any git commit/push in Phase 2:
    #   1. Read C:\QIH\ecosystem\qi_registry.json
    #   2. Check projects[<project_id>].auto_merge_approved_fixes (default: false)
    #   3. If false → open PR via gh; do NOT push to default branch
    #   4. If true → commit on isolated worktree; fast-forward only if hive-inspector verdict=pass
    # This implements Decision C from Auto_Apply_Pipeline_Design_2026-05-13.md.


def _reject(run_id: int, dispatch_id: str, reason: str) -> None:
    with _open_db() as conn:
        conn.execute(
            """UPDATE dispatch_runs
               SET state='rejected_auto', finished_at=?, error=?
               WHERE id=?""",
            (_now(), reason, run_id)
        )
        conn.execute(
            "UPDATE dispatches SET apply_state='rejected_auto' WHERE dispatch_id=?",
            (dispatch_id,)
        )
        _log_compliance(conn, dispatch_id, "dispatch.rejected_auto", reason)
        conn.commit()
    log.info("run_id=%d dispatch_id=%s: rejected_auto — %s", run_id, dispatch_id, reason)

# -*- coding: utf-8 -*-
"""
QI_HiveApply — runner (Phase 2: deterministic transform worker).

For each queued dispatch_run:
  Phase 2 path (allowlisted categories):
    1. Validate spec via transform module.
    2. Create git worktree at C:\\QIH\\worktrees\\apply\\<dispatch_id>.
    3. Apply transform inside worktree.
    4. Run mechanical inspector (ast, md-links, git diff --check, size limits).
    5. Transition state: pending_review. Write inbox file for hive-inspector.
       (Steps 5-6: inspector-gated commit vs fast-commit decided by Renne — not yet active.)

  Phase 1 fallback (unknown category):
    Writes prompt envelope to C:\\QIH\\inbox\\hive_builder\\<dispatch_id>.json.
    State stays in_progress; operator picks up manually.

The HALT check lives in dispatcher.py before handle_run() is called.
"""
import json
import logging
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Allow sibling-directory imports when running from the apply/ folder.
sys.path.insert(0, str(Path(__file__).parent))

from transforms import typo_fix, doc_link_correction, gitignore_addition
from mechanical_inspector import run_all as mech_run

_DB_PATH        = Path(r"C:\QIH\data\qi_brain.db")
_INBOX_BUILDER  = Path(r"C:\QIH\inbox\hive_builder")
_INBOX_INSPECTOR = Path(r"C:\QIH\inbox\hive_inspector")
_WORKTREE_ROOT  = Path(r"C:\QIH\worktrees\apply")

# Transform registry — Phase 2 allowlist
TRANSFORMS = {
    "typo_fix":             typo_fix,
    "doc_link_correction":  doc_link_correction,
    "gitignore_addition":   gitignore_addition,
}

# Phase 1 guardrail defaults (retained for Phase 1 fallback meta)
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


# ── DB helpers ────────────────────────────────────────────────────────────────

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


# ── Transform dispatch ────────────────────────────────────────────────────────

def dispatch_to_transform(category: str):
    """Return the transform module for a category, or None if not in allowlist."""
    return TRANSFORMS.get(category)


# ── Project root resolution ───────────────────────────────────────────────────

def _resolve_project_root(project_id: str) -> Path | None:
    """Look up project path from qi_registry.json. Returns None if not found."""
    registry_path = Path(r"C:\QIH\ecosystem\qi_registry.json")
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except Exception as e:
        log.error("Failed to read qi_registry.json: %s", e)
        return None
    for proj in data.get("projects", []):
        if proj.get("id") == project_id:
            p = proj.get("path")
            return Path(p) if p else None
    return None


# ── State transition helpers ──────────────────────────────────────────────────

def _mark_rejected(run_id: int, dispatch_id: str, reason: str) -> None:
    with _open_db() as conn:
        conn.execute(
            """UPDATE dispatch_runs
               SET state='rejected_auto', finished_at=?, error=?
               WHERE id=?""",
            (_now(), reason, run_id),
        )
        conn.execute(
            "UPDATE dispatches SET apply_state='rejected_auto' WHERE dispatch_id=?",
            (dispatch_id,),
        )
        _log_compliance(conn, dispatch_id, "dispatch.rejected_auto", reason)
        conn.commit()
    log.info("run_id=%d dispatch_id=%s: rejected_auto — %s", run_id, dispatch_id, reason)


def _mark_failed(run_id: int, dispatch_id: str, reason: str) -> None:
    with _open_db() as conn:
        conn.execute(
            """UPDATE dispatch_runs
               SET state='failed', finished_at=?, error=?
               WHERE id=?""",
            (_now(), reason, run_id),
        )
        conn.execute(
            "UPDATE dispatches SET apply_state='failed' WHERE dispatch_id=?",
            (dispatch_id,),
        )
        _log_compliance(conn, dispatch_id, "dispatch.failed", reason)
        conn.commit()
    log.error("run_id=%d dispatch_id=%s: failed — %s", run_id, dispatch_id, reason)


def _mark_pending_review(
    run_id: int,
    dispatch_id: str,
    worktree: Path,
    diff: str,
    mech_result: dict,
    mech_label: str,
) -> None:
    """Write dispatch_runs + inbox file for hive-inspector. State -> pending_review."""
    _INBOX_INSPECTOR.mkdir(parents=True, exist_ok=True)

    inbox_payload = {
        "dispatch_id": dispatch_id,
        "worktree_path": str(worktree),
        "diff_text": diff,
        "mechanical_pass": mech_result["pass"],
        "mechanical_checks": mech_result["checks"],
        "mechanical_errors": mech_result["errors"],
        "label": mech_label,
    }
    inbox_file = _INBOX_INSPECTOR / f"{dispatch_id}.json"
    inbox_file.write_text(json.dumps(inbox_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    with _open_db() as conn:
        conn.execute(
            """UPDATE dispatch_runs
               SET state='pending_review', worktree_path=?, diff_path=?,
                   inspector_verdict=NULL, finished_at=NULL, error=NULL
               WHERE id=?""",
            (str(worktree), str(inbox_file), run_id),
        )
        conn.execute(
            "UPDATE dispatches SET apply_state='pending_review' WHERE dispatch_id=?",
            (dispatch_id,),
        )
        _log_compliance(
            conn, dispatch_id, "dispatch.pending_review",
            f"mechanical_pass={mech_result['pass']} inbox={inbox_file}",
        )
        conn.commit()
    log.info(
        "run_id=%d dispatch_id=%s: state -> pending_review  worktree=%s  mech_pass=%s",
        run_id, dispatch_id, worktree, mech_result["pass"],
    )


# ── Project flag helper ───────────────────────────────────────────────────────

def _project_flag(project_id: str, flag_name: str, default=False):
    """Read a flag from qi_registry.json for a given project. Returns default if absent."""
    registry_path = Path(r"C:\QIH\ecosystem\qi_registry.json")
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except Exception:
        return default
    for proj in data.get("projects", []):
        if proj.get("id") == project_id:
            return proj.get(flag_name, default)
    return default


# ── Inspector-verdict resolution ──────────────────────────────────────────────

def _resolve_pending_reviews(conn: sqlite3.Connection) -> None:
    """For each pending_review run with an inspector verdict, advance state to applied or review.

    Called by dispatcher each tick — runs inside the dispatcher's existing connection
    so no separate open_db() needed here. Caller is responsible for commit.
    """
    rows = conn.execute(
        """SELECT id, dispatch_id, worktree_path, inspector_verdict, inspector_reasons
           FROM dispatch_runs
           WHERE state='pending_review' AND inspector_verdict IS NOT NULL
           LIMIT 5"""
    ).fetchall()

    for run in rows:
        if run["inspector_verdict"] == "pass":
            _commit_and_advance(conn, run)
        else:
            _hold_for_review(conn, run)


def _commit_and_advance(conn: sqlite3.Connection, run: sqlite3.Row) -> None:
    """Inspector passed: commit worktree diff, then open a PR (default) or push direct (opt-in)."""
    worktree = Path(run["worktree_path"]) if run["worktree_path"] else None
    if not worktree or not worktree.exists():
        _mark_failed(run["id"], run["dispatch_id"], "worktree_missing_at_commit_time")
        return

    dispatch = conn.execute(
        "SELECT project_id, payload FROM dispatches WHERE dispatch_id=?",
        (run["dispatch_id"],),
    ).fetchone()
    if not dispatch:
        _mark_failed(run["id"], run["dispatch_id"], "dispatch_row_missing_at_commit_time")
        return

    project_id = dispatch["project_id"] or ""
    try:
        payload = json.loads(dispatch["payload"]) if dispatch["payload"] else {}
    except Exception:
        payload = {}
    fix_category = payload.get("fix_category") or payload.get("check_id") or "unknown"

    project_root = _resolve_project_root(project_id)
    if not project_root:
        _mark_failed(run["id"], run["dispatch_id"], "project_root_not_in_registry")
        return

    # Commit inside the worktree
    msg = (
        f"qi-apply: {fix_category} {run['dispatch_id']}\n\n"
        "Co-Authored-By: hive-inspector <noreply@quiddity.ai>"
    )
    r = subprocess.run(["git", "add", "-A"], cwd=worktree, capture_output=True, text=True)
    if r.returncode != 0:
        _mark_failed(run["id"], run["dispatch_id"], f"git_add: {r.stderr.strip()}")
        return

    r = subprocess.run(["git", "commit", "-m", msg], cwd=worktree, capture_output=True, text=True)
    if r.returncode != 0:
        # Nothing staged = transform already committed or no diff — treat as success
        if "nothing to commit" in r.stdout + r.stderr:
            log.warning(
                "run_id=%d dispatch_id=%s: nothing to commit in worktree — treating as applied",
                run["id"], run["dispatch_id"],
            )
        else:
            _mark_failed(run["id"], run["dispatch_id"], f"git_commit: {r.stderr.strip()}")
            return

    commit_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=worktree, capture_output=True, text=True
    ).stdout.strip()

    auto_merge = _project_flag(project_id, "auto_merge_approved_fixes", default=False)

    if auto_merge:
        r = subprocess.run(["git", "push"], cwd=worktree, capture_output=True, text=True)
        if r.returncode != 0:
            _mark_failed(run["id"], run["dispatch_id"], f"git_push: {r.stderr.strip()}")
            return
        conn.execute(
            "UPDATE dispatch_runs SET state='applied', commit_sha=?, finished_at=datetime('now') WHERE id=?",
            (commit_sha, run["id"]),
        )
        conn.execute(
            "UPDATE dispatches SET apply_state='applied', applied_at=datetime('now'), applied_commit=? WHERE dispatch_id=?",
            (commit_sha, run["dispatch_id"]),
        )
    else:
        # PR path: push a branch then open a PR via gh CLI
        branch = f"qi-apply/{run['dispatch_id'][:8]}"
        subprocess.run(
            ["git", "checkout", "-b", branch], cwd=worktree, capture_output=True, text=True
        )
        r = subprocess.run(
            ["git", "push", "-u", "origin", branch], cwd=worktree, capture_output=True, text=True
        )
        if r.returncode != 0:
            _mark_failed(run["id"], run["dispatch_id"], f"git_push_branch: {r.stderr.strip()}")
            return

        pr_title = f"qi-apply: {fix_category} ({run['dispatch_id'][:8]})"
        pr_body = "\n".join([
            "Auto-applied by QI_HiveApply worker.",
            f"- Category: {fix_category}",
            f"- Dispatch: {run['dispatch_id']}",
            "- Inspector verdict: pass",
            "",
            "Mechanical inspector checks all passed; hive-inspector verdict recorded in dispatch_runs.",
        ])
        r = subprocess.run(
            ["gh", "pr", "create", "--title", pr_title, "--body", pr_body],
            cwd=worktree, capture_output=True, text=True,
        )
        if r.returncode != 0:
            # gh failure is non-fatal — the branch is pushed; PR can be opened manually.
            log.warning(
                "run_id=%d dispatch_id=%s: gh pr create failed: %s",
                run["id"], run["dispatch_id"], r.stderr.strip(),
            )

        conn.execute(
            "UPDATE dispatch_runs SET state='applied', commit_sha=?, finished_at=datetime('now') WHERE id=?",
            (commit_sha, run["id"]),
        )
        conn.execute(
            "UPDATE dispatches SET apply_state='applied', applied_at=datetime('now'), applied_commit=? WHERE dispatch_id=?",
            (commit_sha, run["dispatch_id"]),
        )

    conn.commit()

    # Clean up worktree after successful commit+push
    subprocess.run(
        ["git", "worktree", "remove", str(worktree), "--force"],
        cwd=project_root, capture_output=True, text=True,
    )
    _log_compliance(conn, run["dispatch_id"], "dispatch.applied", f"commit={commit_sha}")
    conn.commit()

    log.info(
        "run_id=%d dispatch_id=%s: applied — commit=%s auto_merge=%s",
        run["id"], run["dispatch_id"], commit_sha, auto_merge,
    )


def _hold_for_review(conn: sqlite3.Connection, run: sqlite3.Row) -> None:
    """Inspector failed: worktree retained. state -> review."""
    conn.execute(
        "UPDATE dispatch_runs SET state='review', finished_at=datetime('now') WHERE id=?",
        (run["id"],),
    )
    conn.execute(
        "UPDATE dispatches SET apply_state='review' WHERE dispatch_id=?",
        (run["dispatch_id"],),
    )
    conn.commit()
    _log_compliance(conn, run["dispatch_id"], "dispatch.review", "inspector_verdict=fail")
    conn.commit()

    log.info(
        "run_id=%d dispatch_id=%s: held for review — inspector verdict=fail",
        run["id"], run["dispatch_id"],
    )


# ── Phase 2 deterministic path ────────────────────────────────────────────────

def _run_deterministic_transform(
    mod,
    run_id: int,
    dispatch_id: str,
    spec: dict,
    project_id: str,
) -> None:
    """Worktree + transform + mechanical inspector. State ends at pending_review.

    Steps 5-6 (inspector-gated or fast-commit) are deferred until Renne resolves
    the strict-vs-fast fork (see Auto_Apply_Phase2_Deterministic_2026-05-14.md §5).
    """
    # Mark in_progress
    with _open_db() as conn:
        conn.execute(
            """UPDATE dispatch_runs SET state='in_progress', started_at=? WHERE id=?""",
            (_now(), run_id),
        )
        conn.execute(
            "UPDATE dispatches SET apply_state='in_progress', apply_run_id=? WHERE dispatch_id=?",
            (run_id, dispatch_id),
        )
        _log_compliance(conn, dispatch_id, "dispatch.in_progress", "phase=2 deterministic")
        conn.commit()

    # Validate spec
    errs = mod.validate(spec)
    if errs:
        _mark_rejected(run_id, dispatch_id, f"spec_invalid: {errs}")
        return

    # Resolve project root
    project_root = _resolve_project_root(project_id)
    if project_root is None:
        _mark_failed(run_id, dispatch_id, f"project_root_not_found for project_id={project_id!r}")
        return
    if not project_root.exists():
        _mark_failed(run_id, dispatch_id, f"project_root does not exist: {project_root}")
        return

    # Create worktree
    worktree = _WORKTREE_ROOT / dispatch_id
    _WORKTREE_ROOT.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["git", "worktree", "add", str(worktree), "HEAD"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        _mark_failed(run_id, dispatch_id, f"worktree_create: {r.stderr.strip()}")
        return
    log.info("run_id=%d dispatch_id=%s: worktree created at %s", run_id, dispatch_id, worktree)

    # Apply transform inside worktree
    try:
        result = mod.apply(worktree, spec)
    except Exception as e:
        _mark_failed(run_id, dispatch_id, f"transform_exception: {e}")
        return

    if not result.get("applied"):
        _mark_rejected(run_id, dispatch_id, f"transform_failed: {result.get('error')}")
        return

    log.info("run_id=%d dispatch_id=%s: transform applied — %s", run_id, dispatch_id, result)

    # Capture diff + changed files
    diff = subprocess.run(
        ["git", "diff"], cwd=worktree, capture_output=True, text=True
    ).stdout
    changed_raw = subprocess.run(
        ["git", "diff", "--name-only"], cwd=worktree, capture_output=True, text=True
    ).stdout
    changed_files = [worktree / f.strip() for f in changed_raw.splitlines() if f.strip()]

    # Mechanical inspector
    mech_result = mech_run(worktree, changed_files, project_root)
    log.info(
        "run_id=%d dispatch_id=%s: mechanical_inspector pass=%s errors=%s",
        run_id, dispatch_id, mech_result["pass"], mech_result["errors"],
    )

    # Mechanical fail: still pending_review; inspector inbox carries the errors.
    # The worktree is retained for human/inspector review in either case.
    label = "mechanical_pass" if mech_result["pass"] else "mechanical_fail"
    _mark_pending_review(run_id, dispatch_id, worktree, diff, mech_result, label)


# ── Main entry point ──────────────────────────────────────────────────────────

def handle_run(run_id: int, dispatch_id: str) -> None:
    """Process one queued dispatch_run. All state transitions happen here."""
    _INBOX_BUILDER.mkdir(parents=True, exist_ok=True)
    _WORKTREE_ROOT.mkdir(parents=True, exist_ok=True)

    with _open_db() as conn:
        dispatch = conn.execute(
            "SELECT * FROM dispatches WHERE dispatch_id=?", (dispatch_id,)
        ).fetchone()

    if dispatch is None:
        log.error("run_id=%d: dispatch_id=%s not found in DB — rejecting", run_id, dispatch_id)
        _reject_legacy(run_id, dispatch_id, "dispatch not found in DB")
        return

    try:
        payload = json.loads(dispatch["payload"]) if isinstance(dispatch["payload"], str) else dispatch["payload"]
    except Exception:
        payload = {}

    fix_category = payload.get("fix_category") or payload.get("check_id") or ""
    spec = payload.get("suggested_fix") if isinstance(payload.get("suggested_fix"), dict) else {}
    project_id = dispatch["project_id"] or ""

    # ── Phase 2 deterministic path ────────────────────────────────────────────
    mod = dispatch_to_transform(fix_category)
    if mod is not None:
        _run_deterministic_transform(mod, run_id, dispatch_id, spec, project_id)
        return

    # ── Phase 1 fallback: unknown category → inbox for operator pickup ────────
    # Unknown category: reject_auto with reason rather than silently queuing.
    # The original Phase 1 code would write an inbox file; we keep that path for
    # any categories that were previously queued under Phase 1 operation.
    log.info(
        "run_id=%d dispatch_id=%s: fix_category=%r not in allowlist — Phase 1 fallback",
        run_id, dispatch_id, fix_category,
    )

    # Allowlist check — reject_auto for unrecognised categories
    if fix_category not in TRANSFORMS:
        _reject_legacy(
            run_id, dispatch_id,
            f"fix_category '{fix_category}' not in allowlist {sorted(TRANSFORMS.keys())}",
        )
        return

    # (Unreachable if allowlist == TRANSFORMS keys, but retained as belt-and-braces)
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
            (_now(), worktree_placeholder, json.dumps(meta), run_id),
        )
        conn.execute(
            "UPDATE dispatches SET apply_state='in_progress', apply_run_id=? WHERE dispatch_id=?",
            (run_id, dispatch_id),
        )
        _log_compliance(conn, dispatch_id, "dispatch.in_progress")
        conn.commit()

    envelope = {
        "dispatch_id":    dispatch_id,
        "project_id":     project_id,
        "suggested_fix":  payload.get("suggested_fix", ""),
        "rationale":      payload.get("message", ""),
        "allowed_paths":  [],
        "max_diff_lines": _MAX_LINES,
        "fix_category":   fix_category,
        "worktree_path":  worktree_placeholder,
    }
    inbox_path = _INBOX_BUILDER / f"{dispatch_id}.json"
    inbox_path.write_text(json.dumps(envelope, indent=2, ensure_ascii=False), encoding="utf-8")

    with _open_db() as conn:
        _log_compliance(conn, dispatch_id, "dispatch.inbox_written", str(inbox_path))
        conn.commit()

    log.info(
        "run_id=%d dispatch_id=%s: Phase 1 fallback complete — awaiting operator pickup at %s",
        run_id, dispatch_id, inbox_path,
    )


def _reject_legacy(run_id: int, dispatch_id: str, reason: str) -> None:
    """Reject helper that matches the original Phase 1 signature."""
    _mark_rejected(run_id, dispatch_id, reason)


# Keep the old _reject name for any external callers (dispatcher.py doesn't call it directly).
_reject = _reject_legacy

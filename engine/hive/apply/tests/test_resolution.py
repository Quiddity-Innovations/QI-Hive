# -*- coding: utf-8 -*-
"""
Tests for Phase 2 steps 5-6: inspector verdict resolution.

Covers:
  - _resolve_pending_reviews: pass branch -> state applied
  - _resolve_pending_reviews: fail branch -> state review
  - Endpoint model validation (InspectorVerdictIn)
"""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

_APPLY_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(_APPLY_DIR))

# ── Shared DB fixture ─────────────────────────────────────────────────────────

def _make_in_memory_db() -> sqlite3.Connection:
    """Minimal in-memory DB with the tables used by the resolution loop."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE dispatches (
            dispatch_id TEXT PRIMARY KEY,
            source      TEXT NOT NULL DEFAULT 'test',
            type        TEXT NOT NULL DEFAULT 'task',
            priority    TEXT NOT NULL DEFAULT 'normal',
            project_id  TEXT,
            payload     TEXT NOT NULL DEFAULT '{}',
            status      TEXT NOT NULL DEFAULT 'approved',
            apply_state TEXT,
            applied_at  TEXT,
            applied_commit TEXT,
            apply_run_id INTEGER,
            notes       TEXT,
            reviewed_by TEXT,
            reviewed_at TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE dispatch_runs (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            dispatch_id       TEXT NOT NULL,
            state             TEXT NOT NULL,
            worktree_path     TEXT,
            inspector_verdict TEXT,
            inspector_reasons TEXT,
            commit_sha        TEXT,
            started_at        TEXT DEFAULT (datetime('now')),
            finished_at       TEXT,
            error             TEXT,
            diff_path         TEXT,
            builder_log       TEXT,
            meta              TEXT
        );
        CREATE TABLE compliance_log (
            log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id      TEXT,
            project_id  TEXT,
            check_id    TEXT,
            status      TEXT,
            severity    TEXT,
            action_taken TEXT,
            message     TEXT,
            dispatch_id INTEGER,
            mode        TEXT,
            recorded_at TEXT DEFAULT (datetime('now'))
        );
    """)
    return conn


def _insert_dispatch(conn, dispatch_id, project_id="test_proj", fix_category="typo_fix"):
    payload = json.dumps({"fix_category": fix_category})
    conn.execute(
        "INSERT INTO dispatches (dispatch_id, project_id, payload, apply_state) VALUES (?,?,?,'pending_review')",
        (dispatch_id, project_id, payload),
    )


def _insert_run(conn, dispatch_id, worktree_path=None, verdict=None, reasons=None):
    conn.execute(
        """INSERT INTO dispatch_runs (dispatch_id, state, worktree_path, inspector_verdict, inspector_reasons)
           VALUES (?, 'pending_review', ?, ?, ?)""",
        (dispatch_id, worktree_path, verdict, json.dumps(reasons or [])),
    )
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


# ── Helpers that patch away git/fs side-effects ───────────────────────────────

class _FakeWorktree:
    """Creates a real git worktree in tmp so git commands inside succeed."""

    def __init__(self, tmp_path: Path):
        self.root = tmp_path / "repo"
        self.root.mkdir()
        subprocess.run(["git", "init", str(self.root)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.email", "t@qi"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.name", "Test"], check=True, capture_output=True)
        (self.root / "file.txt").write_text("hello\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-m", "init"], check=True, capture_output=True)
        # Make an unstaged change so git commit has something to do
        (self.root / "file.txt").write_text("hello world\n", encoding="utf-8")


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestResolveVerdictPass:
    """Inspector verdict=pass path advances state to 'applied' and commits."""

    def test_state_becomes_applied(self, tmp_path, monkeypatch):
        from runner import _resolve_pending_reviews, _resolve_project_root

        worktree = _FakeWorktree(tmp_path)
        conn = _make_in_memory_db()
        did = "test-pass-001"
        _insert_dispatch(conn, did, project_id="test_proj")
        run_id = _insert_run(conn, did, worktree_path=str(worktree.root), verdict="pass")

        # Patch _resolve_project_root to return the worktree root (acts as project_root for cleanup)
        monkeypatch.setattr("runner._resolve_project_root", lambda pid: worktree.root)
        # Patch git push so no remote is needed
        original_run = subprocess.run
        def _fake_run(args, **kwargs):
            if args and args[0] == "git" and "push" in args:
                import subprocess as sp
                class _R:
                    returncode = 0
                    stdout = ""
                    stderr = ""
                return _R()
            if args and args[0] == "gh":
                class _R:
                    returncode = 1
                    stdout = ""
                    stderr = "gh not available in test"
                return _R()
            if args and args[0] == "git" and "worktree" in args:
                # worktree remove — skip silently
                class _R:
                    returncode = 0
                    stdout = ""
                    stderr = ""
                return _R()
            return original_run(args, **kwargs)

        monkeypatch.setattr(subprocess, "run", _fake_run)

        _resolve_pending_reviews(conn)

        run_row = conn.execute("SELECT state, commit_sha FROM dispatch_runs WHERE id=?", (run_id,)).fetchone()
        assert run_row["state"] == "applied", f"Expected applied, got {run_row['state']}"
        assert run_row["commit_sha"], "commit_sha should be set after applying"

        dispatch_row = conn.execute("SELECT apply_state FROM dispatches WHERE dispatch_id=?", (did,)).fetchone()
        assert dispatch_row["apply_state"] == "applied"

    def test_compliance_log_written(self, tmp_path, monkeypatch):
        from runner import _resolve_pending_reviews

        worktree = _FakeWorktree(tmp_path)
        conn = _make_in_memory_db()
        did = "test-pass-002"
        _insert_dispatch(conn, did, project_id="test_proj")
        _insert_run(conn, did, worktree_path=str(worktree.root), verdict="pass")

        monkeypatch.setattr("runner._resolve_project_root", lambda pid: worktree.root)
        original_run = subprocess.run
        def _fake_run(args, **kwargs):
            if args and args[0] == "git" and ("push" in args or ("worktree" in args)):
                class _R:
                    returncode = 0; stdout = ""; stderr = ""
                return _R()
            if args and args[0] == "gh":
                class _R:
                    returncode = 1; stdout = ""; stderr = "not available"
                return _R()
            return original_run(args, **kwargs)
        monkeypatch.setattr(subprocess, "run", _fake_run)

        _resolve_pending_reviews(conn)

        log_rows = conn.execute(
            "SELECT message FROM compliance_log WHERE message LIKE '%dispatch.applied%'"
        ).fetchall()
        assert log_rows, "compliance_log entry for dispatch.applied not found"


class TestResolveVerdictFail:
    """Inspector verdict=fail path transitions state to 'review', worktree retained."""

    def test_state_becomes_review(self):
        conn = _make_in_memory_db()
        did = "test-fail-001"
        _insert_dispatch(conn, did, project_id="test_proj")
        run_id = _insert_run(conn, did, worktree_path="/some/path", verdict="fail",
                              reasons=["missing_docstring", "encoding_issue"])

        from runner import _resolve_pending_reviews
        _resolve_pending_reviews(conn)

        run_row = conn.execute("SELECT state FROM dispatch_runs WHERE id=?", (run_id,)).fetchone()
        assert run_row["state"] == "review", f"Expected review, got {run_row['state']}"

        dispatch_row = conn.execute("SELECT apply_state FROM dispatches WHERE dispatch_id=?", (did,)).fetchone()
        assert dispatch_row["apply_state"] == "review"

    def test_no_commit_on_fail(self, tmp_path):
        """Worktree must not be touched when verdict is fail."""
        conn = _make_in_memory_db()
        did = "test-fail-002"
        _insert_dispatch(conn, did)
        run_id = _insert_run(conn, did, worktree_path=str(tmp_path), verdict="fail")

        from runner import _resolve_pending_reviews
        _resolve_pending_reviews(conn)

        run_row = conn.execute("SELECT commit_sha FROM dispatch_runs WHERE id=?", (run_id,)).fetchone()
        assert run_row["commit_sha"] is None, "commit_sha must be NULL when inspector fails"

    def test_compliance_log_written_for_fail(self):
        conn = _make_in_memory_db()
        did = "test-fail-003"
        _insert_dispatch(conn, did)
        _insert_run(conn, did, worktree_path="/noop", verdict="fail")

        from runner import _resolve_pending_reviews
        _resolve_pending_reviews(conn)

        log_rows = conn.execute(
            "SELECT message FROM compliance_log WHERE message LIKE '%dispatch.review%'"
        ).fetchall()
        assert log_rows, "compliance_log entry for dispatch.review not found"


class TestNoVerdictYet:
    """Rows with NULL inspector_verdict must not be touched."""

    def test_no_transition_without_verdict(self):
        conn = _make_in_memory_db()
        did = "test-no-verdict-001"
        _insert_dispatch(conn, did)
        run_id = _insert_run(conn, did, worktree_path="/noop", verdict=None)

        from runner import _resolve_pending_reviews
        _resolve_pending_reviews(conn)

        run_row = conn.execute("SELECT state FROM dispatch_runs WHERE id=?", (run_id,)).fetchone()
        assert run_row["state"] == "pending_review", "State must remain pending_review when no verdict"


class TestInspectorVerdictModel:
    """Pydantic validation for InspectorVerdictIn (no HTTP layer needed)."""

    def test_valid_pass(self):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "brain"))
        from pydantic import ValidationError
        # Import model directly from api module path
        _BRAIN = Path(r"C:\QIH\engine\brain")
        sys.path.insert(0, str(_BRAIN))
        try:
            from api import InspectorVerdictIn
            m = InspectorVerdictIn(verdict="pass", reviewer="hive_inspector")
            assert m.verdict == "pass"
            assert m.reasons == []
        except ImportError:
            pytest.skip("Brain API not importable in this environment")

    def test_invalid_verdict(self):
        _BRAIN = Path(r"C:\QIH\engine\brain")
        sys.path.insert(0, str(_BRAIN))
        try:
            from api import InspectorVerdictIn
            from pydantic import ValidationError
            with pytest.raises(ValidationError):
                InspectorVerdictIn(verdict="maybe", reviewer="hive_inspector")
        except ImportError:
            pytest.skip("Brain API not importable in this environment")

    def test_invalid_reviewer_chars(self):
        _BRAIN = Path(r"C:\QIH\engine\brain")
        sys.path.insert(0, str(_BRAIN))
        try:
            from api import InspectorVerdictIn
            from pydantic import ValidationError
            with pytest.raises(ValidationError):
                InspectorVerdictIn(verdict="pass", reviewer="bad reviewer!")
        except ImportError:
            pytest.skip("Brain API not importable in this environment")

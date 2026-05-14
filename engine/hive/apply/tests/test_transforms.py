# -*- coding: utf-8 -*-
"""Tests for Phase 2 transform modules and mechanical_inspector."""
import json
import sqlite3
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

# Allow importing from the apply/ folder regardless of cwd.
_APPLY_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(_APPLY_DIR))

from transforms import typo_fix, doc_link_correction, gitignore_addition
from mechanical_inspector import (
    check_python_syntax,
    check_markdown_links,
    check_size_limits,
    run_all,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_project(tmp_path: Path) -> Path:
    """Initialise a minimal git repo under tmp_path and return its path."""
    root = tmp_path / "proj"
    root.mkdir()
    subprocess.run(["git", "init", str(root)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "test@qi"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True, capture_output=True)
    # Initial commit so worktrees work
    readme = root / "README.md"
    readme.write_text("# test\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "commit", "-m", "init"], check=True, capture_output=True)
    return root


# ── typo_fix ──────────────────────────────────────────────────────────────────

class TestTypoFix:
    def test_validate_happy(self):
        errs = typo_fix.validate({"file": "README.md", "find": "teh", "replace": "the"})
        assert errs == []

    def test_validate_missing_field(self):
        errs = typo_fix.validate({"file": "README.md", "find": "teh"})
        assert any("replace" in e for e in errs)

    def test_validate_identical(self):
        errs = typo_fix.validate({"file": "f.py", "find": "x", "replace": "x"})
        assert any("identical" in e for e in errs)

    def test_apply_happy(self, tmp_path):
        root = tmp_path / "proj"
        root.mkdir()
        f = root / "README.md"
        f.write_text("Hello teh world\n", encoding="utf-8")
        result = typo_fix.apply(root, {"file": "README.md", "find": "teh", "replace": "the"})
        assert result["applied"] is True
        assert result["count"] == 1
        assert f.read_text(encoding="utf-8") == "Hello the world\n"

    def test_apply_missing_file(self, tmp_path):
        root = tmp_path / "proj"
        root.mkdir()
        result = typo_fix.apply(root, {"file": "no_such.md", "find": "x", "replace": "y"})
        assert result["applied"] is False
        assert "missing" in result["error"]

    def test_apply_find_not_present(self, tmp_path):
        root = tmp_path / "proj"
        root.mkdir()
        (root / "f.md").write_text("hello world\n", encoding="utf-8")
        result = typo_fix.apply(root, {"file": "f.md", "find": "NOTHERE", "replace": "x"})
        assert result["applied"] is False
        assert "not found" in result["error"]

    def test_apply_wrong_occurrence_count(self, tmp_path):
        root = tmp_path / "proj"
        root.mkdir()
        (root / "f.md").write_text("teh teh\n", encoding="utf-8")
        result = typo_fix.apply(root, {"file": "f.md", "find": "teh", "replace": "the", "occurrences": 1})
        assert result["applied"] is False
        assert "expected 1" in result["error"]


# ── doc_link_correction ───────────────────────────────────────────────────────

class TestDocLinkCorrection:
    def test_validate_happy(self):
        errs = doc_link_correction.validate({
            "file": "docs/guide.md",
            "broken_link": "old.md",
            "corrected_link": "new.md",
        })
        assert errs == []

    def test_validate_not_md(self):
        errs = doc_link_correction.validate({
            "file": "docs/guide.txt",
            "broken_link": "old.md",
            "corrected_link": "new.md",
        })
        assert any(".md" in e for e in errs)

    def test_validate_identical_links(self):
        errs = doc_link_correction.validate({
            "file": "docs/guide.md",
            "broken_link": "same.md",
            "corrected_link": "same.md",
        })
        assert any("identical" in e for e in errs)

    def test_apply_happy(self, tmp_path):
        root = tmp_path / "proj"
        (root / "docs").mkdir(parents=True)
        f = root / "docs" / "guide.md"
        f.write_text("[See](old/path.md)\n", encoding="utf-8")
        result = doc_link_correction.apply(root, {
            "file": "docs/guide.md",
            "broken_link": "old/path.md",
            "corrected_link": "new/path.md",
        })
        assert result["applied"] is True
        assert "new/path.md" in f.read_text(encoding="utf-8")

    def test_apply_not_under_docs(self, tmp_path):
        root = tmp_path / "proj"
        (root / "src").mkdir(parents=True)
        f = root / "src" / "readme.md"
        f.write_text("[See](old.md)\n", encoding="utf-8")
        result = doc_link_correction.apply(root, {
            "file": "src/readme.md",
            "broken_link": "old.md",
            "corrected_link": "new.md",
        })
        assert result["applied"] is False
        assert "docs folder" in result["error"]

    def test_apply_missing_file(self, tmp_path):
        root = tmp_path / "proj"
        root.mkdir()
        result = doc_link_correction.apply(root, {
            "file": "docs/no_such.md",
            "broken_link": "x",
            "corrected_link": "y",
        })
        assert result["applied"] is False

    def test_apply_link_not_present(self, tmp_path):
        root = tmp_path / "proj"
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "g.md").write_text("nothing here\n", encoding="utf-8")
        result = doc_link_correction.apply(root, {
            "file": "docs/g.md",
            "broken_link": "ghost.md",
            "corrected_link": "real.md",
        })
        assert result["applied"] is False
        assert "not found" in result["error"]


# ── gitignore_addition ────────────────────────────────────────────────────────

class TestGitignoreAddition:
    def test_validate_happy(self):
        errs = gitignore_addition.validate({"file": ".gitignore", "line": "__pycache__/"})
        assert errs == []

    def test_validate_not_gitignore(self):
        errs = gitignore_addition.validate({"file": "notes.txt", "line": "x"})
        assert errs

    def test_validate_blank_line(self):
        errs = gitignore_addition.validate({"file": ".gitignore", "line": "   "})
        assert errs

    def test_apply_appends_new_line(self, tmp_path):
        root = tmp_path / "proj"
        root.mkdir()
        gi = root / ".gitignore"
        gi.write_text("*.pyc\n", encoding="utf-8")
        result = gitignore_addition.apply(root, {"file": ".gitignore", "line": "__pycache__/"})
        assert result["applied"] is True
        assert "__pycache__/" in gi.read_text(encoding="utf-8")

    def test_apply_dedup(self, tmp_path):
        root = tmp_path / "proj"
        root.mkdir()
        gi = root / ".gitignore"
        gi.write_text("__pycache__/\n", encoding="utf-8")
        result = gitignore_addition.apply(root, {"file": ".gitignore", "line": "__pycache__/"})
        assert result["applied"] is False
        assert "already present" in result["error"]

    def test_apply_creates_file_if_absent(self, tmp_path):
        root = tmp_path / "proj"
        root.mkdir()
        result = gitignore_addition.apply(root, {"file": ".gitignore", "line": "*.db"})
        assert result["applied"] is True
        assert "*.db" in (root / ".gitignore").read_text(encoding="utf-8")

    def test_apply_ignores_comments_for_dedup(self, tmp_path):
        root = tmp_path / "proj"
        root.mkdir()
        gi = root / ".gitignore"
        gi.write_text("# *.db is excluded\n*.pyc\n", encoding="utf-8")
        # "# *.db is excluded" is a comment; "*.db" is NOT in the file as a pattern
        result = gitignore_addition.apply(root, {"file": ".gitignore", "line": "*.db"})
        assert result["applied"] is True


# ── mechanical_inspector ──────────────────────────────────────────────────────

class TestMechanicalInspector:
    def test_py_syntax_good(self, tmp_path):
        f = tmp_path / "ok.py"
        f.write_text("def foo():\n    return 1\n", encoding="utf-8")
        ok, err = check_python_syntax(f)
        assert ok is True
        assert err is None

    def test_py_syntax_bad(self, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text("def foo(\n", encoding="utf-8")
        ok, err = check_python_syntax(f)
        assert ok is False
        assert "SyntaxError" in err

    def test_md_links_good(self, tmp_path):
        root = tmp_path / "proj"
        root.mkdir()
        f = root / "doc.md"
        target = root / "other.md"
        target.write_text("x\n", encoding="utf-8")
        f.write_text("[See](other.md)\n", encoding="utf-8")
        ok, broken = check_markdown_links(f, root)
        assert ok is True
        assert broken == []

    def test_md_links_broken(self, tmp_path):
        root = tmp_path / "proj"
        root.mkdir()
        f = root / "doc.md"
        f.write_text("[See](ghost.md)\n", encoding="utf-8")
        ok, broken = check_markdown_links(f, root)
        assert ok is False
        assert any("ghost.md" in b for b in broken)

    def test_md_links_http_skipped(self, tmp_path):
        root = tmp_path / "proj"
        root.mkdir()
        f = root / "doc.md"
        f.write_text("[See](https://example.com)\n", encoding="utf-8")
        ok, broken = check_markdown_links(f, root)
        assert ok is True

    def test_size_limits_pass(self, tmp_path):
        root = _make_project(tmp_path)
        (root / "README.md").write_text("# updated\n", encoding="utf-8")
        ok, err = check_size_limits(root, max_files=1, max_lines=40)
        assert ok is True

    def test_size_limits_too_many_files(self, tmp_path):
        root = _make_project(tmp_path)
        # Commit both files so they exist at HEAD in the worktree
        (root / "a.md").write_text("a\n", encoding="utf-8")
        (root / "b.md").write_text("b\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(root), "commit", "-m", "add files"], check=True, capture_output=True)
        # Modify both files so they show in `git diff` (unstaged)
        (root / "a.md").write_text("a-changed\n", encoding="utf-8")
        (root / "b.md").write_text("b-changed\n", encoding="utf-8")
        ok, err = check_size_limits(root, max_files=1, max_lines=40)
        assert ok is False
        assert "files" in err


# ── End-to-end fixture ─────────────────────────────────────────────────────────

class TestEndToEnd:
    """
    Creates a synthetic dispatch row with category=typo_fix, runs handle_run(),
    and confirms: worktree created, transform applied, mechanical pass,
    dispatch_runs.state=pending_review.
    """

    def _make_db(self, tmp_path: Path) -> Path:
        db_path = tmp_path / "qi_brain.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE dispatches (
                dispatch_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                type TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'normal',
                project_id TEXT,
                payload TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                reply_path TEXT,
                notes TEXT,
                reviewed_by TEXT,
                reviewed_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                apply_state TEXT,
                apply_run_id INTEGER,
                applied_at TEXT,
                applied_commit TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE dispatch_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dispatch_id TEXT NOT NULL,
                state TEXT NOT NULL,
                builder_log TEXT,
                inspector_verdict TEXT,
                inspector_reasons TEXT,
                diff_path TEXT,
                worktree_path TEXT,
                commit_sha TEXT,
                started_at TEXT DEFAULT (datetime('now')),
                finished_at TEXT,
                error TEXT,
                meta TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE compliance_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                check_id TEXT NOT NULL,
                status TEXT NOT NULL,
                severity TEXT NOT NULL,
                auto_fixable INTEGER NOT NULL DEFAULT 0,
                action_taken TEXT NOT NULL DEFAULT 'none',
                message TEXT,
                fix_action TEXT,
                dispatch_id INTEGER,
                mode TEXT NOT NULL DEFAULT 'fast',
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        return db_path

    def test_handle_run_typo_fix(self, tmp_path, monkeypatch):
        # Build a fake project with the typo committed so the worktree (HEAD) has it.
        proj_root = _make_project(tmp_path)
        target_file = proj_root / "README.md"
        # _make_project already committed README.md as "# test\n"; overwrite and recommit.
        target_file.write_text("This is teh problem.\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(proj_root), "add", "README.md"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(proj_root), "commit", "-m", "add typo"], check=True, capture_output=True)

        # Patch the DB path and inbox/worktree dirs in runner
        db_path = self._make_db(tmp_path)
        worktree_root = tmp_path / "worktrees"
        inbox_inspector = tmp_path / "inbox_inspector"
        inbox_builder = tmp_path / "inbox_builder"

        # Insert a dispatch row
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        dispatch_id = "test-e2e-001"
        payload = json.dumps({
            "fix_category": "typo_fix",
            "suggested_fix": {
                "file": "README.md",
                "find": "teh",
                "replace": "the",
            },
        })
        conn.execute(
            "INSERT INTO dispatches (dispatch_id, source, type, payload, project_id) VALUES (?,?,?,?,?)",
            (dispatch_id, "test", "task", payload, "test_proj"),
        )
        conn.execute(
            "INSERT INTO dispatch_runs (dispatch_id, state) VALUES (?,?)",
            (dispatch_id, "queued"),
        )
        conn.commit()
        run_id = conn.execute(
            "SELECT id FROM dispatch_runs WHERE dispatch_id=?", (dispatch_id,)
        ).fetchone()[0]
        conn.close()

        # Patch runner module globals
        import runner as runner_mod
        monkeypatch.setattr(runner_mod, "_DB_PATH", db_path)
        monkeypatch.setattr(runner_mod, "_WORKTREE_ROOT", worktree_root)
        monkeypatch.setattr(runner_mod, "_INBOX_BUILDER", inbox_builder)
        monkeypatch.setattr(runner_mod, "_INBOX_INSPECTOR", inbox_inspector)

        # Patch _resolve_project_root to return our fake project
        monkeypatch.setattr(runner_mod, "_resolve_project_root", lambda pid: proj_root)

        runner_mod.handle_run(run_id, dispatch_id)

        # Verify worktree was created
        wt = worktree_root / dispatch_id
        assert wt.exists(), "worktree directory should exist"

        # Verify transform was applied in the worktree
        wt_readme = wt / "README.md"
        assert wt_readme.exists()
        content = wt_readme.read_text(encoding="utf-8")
        assert "the problem" in content, f"expected 'the problem' in {content!r}"
        assert "teh" not in content

        # Verify dispatch_runs state = pending_review
        conn2 = sqlite3.connect(str(db_path))
        conn2.row_factory = sqlite3.Row
        row = conn2.execute(
            "SELECT state, worktree_path FROM dispatch_runs WHERE id=?", (run_id,)
        ).fetchone()
        assert row["state"] == "pending_review", f"state was {row['state']}"

        # Verify inspector inbox file was written
        inbox_file = inbox_inspector / f"{dispatch_id}.json"
        assert inbox_file.exists(), "inspector inbox file should be written"
        payload_out = json.loads(inbox_file.read_text(encoding="utf-8"))
        assert payload_out["dispatch_id"] == dispatch_id
        assert payload_out["mechanical_pass"] is True

        conn2.close()

        # Clean up worktree
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt)],
            cwd=proj_root, capture_output=True
        )

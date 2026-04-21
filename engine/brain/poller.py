# -*- coding: utf-8 -*-
"""
QI Brain Poller
===============
Background thread started at Brain API startup. Pulls state from every
registered QI project on a configurable schedule instead of waiting for
Claude to push at session end.

Poll sources per project:
  • <project_path>/data/state.json or status.json  — project state file
  • <project_path>/data/tasks.json                  — task board (QI Hive only)
  • git log --since=<last_check>                    — recent commits

Brain inbox (file-based, for any sender):
  C:\\QIH\\brain\\inbox\\*.json  — drop a message here, poller picks it up

Configuration (brain_config table):
  poll_interval_s      — seconds between cycles (default 300)
  poll_min_file_age_s  — only process files older than this (default 60)
  poll_enabled         — '1' to run, '0' to pause (default 1)
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
import time
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from core.db import open_brain_db

log = logging.getLogger("qi.brain.poller")

INBOX_DIR     = Path(r"C:\QIH\brain\inbox")
PROCESSED_DIR = INBOX_DIR / "processed"
ERROR_DIR     = INBOX_DIR / "errors"

# Projects whose state files Brain actively watches
# Keyed by project_id → list of candidate state file subpaths (first found wins)
STATE_FILE_CANDIDATES: dict[str, list[str]] = {
    "qi_hive":   ["data/status.json", "data/state.json"],
    "easyflow":  ["data/state.json", "data/status.json"],
    "maia":      ["data/state.json", "config/state.json"],
    "naya":      ["data/state.json", "config/state.json"],
    "nexus":     ["data/state.json"],
    "openclaw":  ["data/state.json"],
    "filehq":    ["data/state.json"],
}

# Hive tasks file (special — drives board sync)
HIVE_TASKS_FILE = Path(r"C:\QIH\data\tasks.json")


# ─────────────────────────────────────────────────────────────────────────────
# Config helpers (re-read each cycle so hot-edit works without restart)
# ─────────────────────────────────────────────────────────────────────────────

def _cfg(key: str, default: str) -> str:
    try:
        with open_brain_db() as conn:
            row = conn.execute(
                "SELECT value FROM brain_config WHERE key=?", (key,)
            ).fetchone()
        return row["value"] if row else default
    except Exception:
        return default


# ─────────────────────────────────────────────────────────────────────────────
# Git helpers
# ─────────────────────────────────────────────────────────────────────────────

def _git_recent_commits(repo_path: Path, since_iso: str) -> list[dict]:
    """Return commits to repo since since_iso (ISO-8601 string)."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "log",
             f"--since={since_iso}",
             "--pretty=format:%H|%s|%an|%ai",
             "--no-merges"],
            capture_output=True, text=True, timeout=10
        )
        commits = []
        for line in result.stdout.strip().splitlines():
            if "|" not in line:
                continue
            parts = line.split("|", 3)
            if len(parts) == 4:
                commits.append({
                    "hash": parts[0][:12],
                    "subject": parts[1],
                    "author": parts[2],
                    "date": parts[3],
                })
        return commits
    except Exception:
        return []


def _detect_version_bump(commits: list[dict]) -> str | None:
    """Return version string if any commit subject looks like a version bump."""
    for c in commits:
        s = c.get("subject", "").lower()
        for kw in ["bump", "release", "v1.", "v2.", "v0.", "version", "tag"]:
            if kw in s:
                return c["subject"]
    return None


# ─────────────────────────────────────────────────────────────────────────────
# State file reader
# ─────────────────────────────────────────────────────────────────────────────

def _read_state_file(project_path: Path, candidates: list[str]) -> tuple[Path | None, dict]:
    for rel in candidates:
        p = project_path / rel
        if p.exists():
            try:
                return p, json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
    return None, {}


def _extract_phase_status(data: dict, project_id: str) -> tuple[str, str, str]:
    """Best-effort extraction of (phase, status, summary) from heterogeneous state files."""
    # QI Hive status.json has a top-level 'projects' dict
    if "projects" in data and project_id in data.get("projects", {}):
        proj = data["projects"][project_id]
        phase  = str(proj.get("phase", proj.get("stage", "active")))
        status = str(proj.get("status", "active")).lower()
        summary = str(proj.get("summary", proj.get("description", "")))[:300]
        return phase, status, summary

    # Generic state.json
    phase   = str(data.get("phase",  data.get("stage",  "active")))
    status  = str(data.get("status", "active")).lower()
    summary = str(data.get("summary", data.get("description", "")))[:300]
    return phase, status, summary


# ─────────────────────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────────────────────

def _last_poll_time() -> str:
    """Return ISO timestamp of last successful poll, or 24h ago as fallback."""
    try:
        with open_brain_db() as conn:
            row = conn.execute(
                "SELECT started_at FROM poll_log ORDER BY poll_id DESC LIMIT 1"
            ).fetchone()
        if row:
            return row["started_at"]
    except Exception:
        pass
    # Fallback: 24 hours ago
    from datetime import timedelta
    return (datetime.now() - timedelta(hours=24)).isoformat()


def _last_project_state(project_id: str) -> dict:
    try:
        with open_brain_db() as conn:
            row = conn.execute(
                "SELECT phase, status, summary FROM project_state "
                "WHERE project_id=? ORDER BY recorded_at DESC LIMIT 1",
                (project_id,)
            ).fetchone()
        return dict(row) if row else {}
    except Exception:
        return {}


def _write_project_state(project_id: str, phase: str, status: str, summary: str,
                          source: str = "poller") -> None:
    with open_brain_db() as conn:
        conn.execute(
            """INSERT INTO project_state
                   (project_id, agent_id, phase, status, summary)
               VALUES (?, 'system', ?, ?, ?)""",
            (project_id, phase, status, f"[auto:{source}] {summary}")
        )
        conn.commit()


def _write_poll_log(started: datetime, finished: datetime,
                    projects_checked: int, files_checked: int,
                    changes_found: int, inbox_processed: int,
                    errors: list[str], summary: str) -> None:
    duration_ms = int((finished - started).total_seconds() * 1000)
    with open_brain_db() as conn:
        conn.execute(
            """INSERT INTO poll_log
                   (started_at, finished_at, duration_ms, projects_checked,
                    files_checked, changes_found, inbox_processed, errors, summary)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (started.isoformat(), finished.isoformat(), duration_ms,
             projects_checked, files_checked, changes_found, inbox_processed,
             json.dumps(errors), summary)
        )
        conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Inbox processor
# ─────────────────────────────────────────────────────────────────────────────

def _process_inbox_file(f: Path, min_age_s: float) -> tuple[bool, str]:
    """
    Process one inbox JSON file. Returns (success, error_msg).
    Message types:
      state_update  → insert project_state row
      decision      → insert decisions row
      session       → insert session_log row
      scope_drop    → call distiller
      note          → log only (brain_inbox_log)
    """
    try:
        age = time.time() - f.stat().st_mtime
        if age < min_age_s:
            return False, f"too_young ({age:.0f}s < {min_age_s}s)"

        payload = json.loads(f.read_text(encoding="utf-8"))
        msg_type   = payload.get("type", "note")
        project_id = payload.get("project_id", "unknown")
        source     = payload.get("source", "file")

        with open_brain_db() as conn:
            if msg_type == "state_update":
                conn.execute(
                    """INSERT INTO project_state
                           (project_id, agent_id, phase, status, summary, next_steps)
                       VALUES (?, 'system', ?, ?, ?, ?)""",
                    (project_id,
                     payload.get("phase", "active"),
                     payload.get("status", "active"),
                     payload.get("summary", ""),
                     payload.get("next_steps"))
                )

            elif msg_type == "decision":
                conn.execute(
                    """INSERT INTO decisions
                           (project_id, agent_id, title, rationale, impact_scope, tags)
                       VALUES (?, 'system', ?, ?, ?, ?)""",
                    (project_id,
                     payload.get("title", "(untitled)"),
                     payload.get("rationale", ""),
                     payload.get("impact_scope", "project"),
                     json.dumps(payload.get("tags", [])))
                )

            elif msg_type == "session":
                conn.execute(
                    """INSERT INTO session_log
                           (project_id, agent_id, session_title, summary,
                            decisions_made, features_logged, model_used)
                       VALUES (?, 'system', ?, ?, ?, ?, ?)""",
                    (project_id,
                     payload.get("title", "Session"),
                     payload.get("summary", ""),
                     payload.get("decisions_made", 0),
                     payload.get("features_logged", 0),
                     payload.get("model_used"))
                )

            elif msg_type == "scope_drop":
                # Import here to avoid circular at module load
                from distiller import distill
                distill(
                    project_id=project_id,
                    reason="scope_dropped",
                    scope_label=payload.get("scope_label", ""),
                    drop_reason=payload.get("reason", ""),
                    dropped_by=payload.get("dropped_by", source),
                )

            # Always log to brain_inbox_log
            conn.execute(
                """INSERT INTO brain_inbox_log
                       (message_type, project_id, source, source_file, payload, status)
                   VALUES (?, ?, ?, ?, ?, 'ok')""",
                (msg_type, project_id, source, f.name, json.dumps(payload))
            )
            conn.commit()

        # Archive
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        shutil.move(str(f), str(PROCESSED_DIR / f.name))
        return True, ""

    except Exception as e:
        err = str(e)
        try:
            ERROR_DIR.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), str(ERROR_DIR / f.name))
            with open_brain_db() as conn:
                conn.execute(
                    """INSERT INTO brain_inbox_log
                           (message_type, project_id, source, source_file, payload, status, error)
                       VALUES ('unknown', 'unknown', 'file', ?, ?, 'error', ?)""",
                    (f.name, f.read_text(encoding="utf-8") if f.exists() else "", err)
                )
                conn.commit()
        except Exception:
            pass
        return False, err


# ─────────────────────────────────────────────────────────────────────────────
# Core poll cycle
# ─────────────────────────────────────────────────────────────────────────────

def run_poll_cycle() -> dict:
    """
    Execute one full poll cycle. Returns a summary dict.
    Safe to call from the background thread or manually via API.
    """
    started        = datetime.now()
    errors: list[str] = []
    projects_checked  = 0
    files_checked     = 0
    changes_found     = 0
    inbox_processed   = 0
    change_notes: list[str] = []

    min_age_s = float(_cfg("poll_min_file_age_s", "60"))

    # ── 1. Load registered projects ──────────────────────────────────────────
    try:
        with open_brain_db() as conn:
            rows = conn.execute(
                "SELECT project_id, path FROM projects WHERE active=1 AND path IS NOT NULL"
            ).fetchall()
        registered = {r["project_id"]: r["path"] for r in rows}
    except Exception as e:
        errors.append(f"db_read: {e}")
        registered = {}

    last_poll_iso = _last_poll_time()

    # ── 2. Poll each project ─────────────────────────────────────────────────
    for project_id, project_path_str in registered.items():
        if not project_path_str:
            continue
        project_path = Path(project_path_str)
        if not project_path.exists():
            continue

        projects_checked += 1
        candidates = STATE_FILE_CANDIDATES.get(project_id, ["data/state.json", "data/status.json"])

        try:
            # ── 2a. State file ────────────────────────────────────────────────
            state_file, state_data = _read_state_file(project_path, candidates)
            if state_file:
                files_checked += 1
                age = time.time() - state_file.stat().st_mtime
                if age >= min_age_s and state_data:
                    phase, status, summary = _extract_phase_status(state_data, project_id)
                    last = _last_project_state(project_id)
                    changed = (
                        last.get("phase")   != phase  or
                        last.get("status")  != status or
                        last.get("summary") != summary
                    )
                    if changed and summary:
                        _write_project_state(project_id, phase, status, summary, "state_file")
                        changes_found += 1
                        change_notes.append(f"{project_id}: state→{status}/{phase}")

            # ── 2b. Git log ───────────────────────────────────────────────────
            if (project_path / ".git").exists():
                commits = _git_recent_commits(project_path, last_poll_iso)
                if commits:
                    files_checked += 1
                    ver = _detect_version_bump(commits)
                    summary = f"{len(commits)} new commit(s). Latest: {commits[0]['subject'][:80]}"
                    if ver:
                        summary += f" | Version bump detected: {ver}"
                    last = _last_project_state(project_id)
                    # Only write if git activity is newer than any known state update
                    if not last or commits[0]["date"] > last.get("summary", ""):
                        phase  = last.get("phase", "active")
                        status = last.get("status", "active")
                        _write_project_state(project_id, phase, status, summary, "git")
                        changes_found += 1
                        change_notes.append(f"{project_id}: git→{len(commits)} commits")

        except Exception as e:
            errors.append(f"{project_id}: {e}")

    # ── 3. Process inbox ─────────────────────────────────────────────────────
    try:
        INBOX_DIR.mkdir(parents=True, exist_ok=True)
        inbox_files = sorted(INBOX_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)
        for f in inbox_files:
            ok, err = _process_inbox_file(f, min_age_s)
            if ok:
                inbox_processed += 1
                changes_found += 1
            elif err and not err.startswith("too_young"):
                errors.append(f"inbox/{f.name}: {err}")
    except Exception as e:
        errors.append(f"inbox: {e}")

    # ── 4. Write poll log ────────────────────────────────────────────────────
    finished = datetime.now()
    summary_line = (
        f"Checked {projects_checked} projects, {files_checked} files — "
        f"{changes_found} change(s), {inbox_processed} inbox msg(s)"
    )
    if change_notes:
        summary_line += " | " + "; ".join(change_notes[:5])

    try:
        _write_poll_log(
            started=started, finished=finished,
            projects_checked=projects_checked, files_checked=files_checked,
            changes_found=changes_found, inbox_processed=inbox_processed,
            errors=errors, summary=summary_line,
        )
    except Exception as e:
        log.error(f"poll_log write failed: {e}")

    if errors:
        log.warning(f"Poll cycle completed with {len(errors)} error(s): {errors[:3]}")
    else:
        log.info(summary_line)

    return {
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "duration_ms": int((finished - started).total_seconds() * 1000),
        "projects_checked": projects_checked,
        "files_checked": files_checked,
        "changes_found": changes_found,
        "inbox_processed": inbox_processed,
        "errors": errors,
        "summary": summary_line,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Background thread
# ─────────────────────────────────────────────────────────────────────────────

class BrainPoller(threading.Thread):
    """
    Daemon thread that runs poll cycles on a configurable schedule.
    Started once at Brain API startup. Stopped cleanly on shutdown.
    """

    def __init__(self) -> None:
        super().__init__(name="BrainPoller", daemon=True)
        self._stop_event = threading.Event()
        self.last_result: dict = {}
        self.is_running   = False

    def stop(self) -> None:
        self._stop_event.set()

    def trigger(self) -> dict:
        """Force an immediate poll cycle (called from API endpoint)."""
        return run_poll_cycle()

    def run(self) -> None:
        log.info("BrainPoller started")
        # Small initial delay so Brain API is fully up before first poll
        time.sleep(10)

        while not self._stop_event.is_set():
            interval_s = int(_cfg("poll_interval_s", "300"))
            enabled    = _cfg("poll_enabled", "1") == "1"

            if enabled:
                self.is_running = True
                try:
                    self.last_result = run_poll_cycle()
                except Exception as e:
                    log.exception(f"Unhandled error in poll cycle: {e}")
                    self.last_result = {"error": str(e)}
                finally:
                    self.is_running = False
            else:
                log.debug("Polling disabled via brain_config poll_enabled=0")

            # Sleep in small increments so stop() is responsive
            for _ in range(interval_s):
                if self._stop_event.is_set():
                    break
                time.sleep(1)

        log.info("BrainPoller stopped")


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton (created at Brain API startup)
# ─────────────────────────────────────────────────────────────────────────────

_poller: BrainPoller | None = None


def start_poller() -> BrainPoller:
    global _poller
    if _poller is None or not _poller.is_alive():
        _poller = BrainPoller()
        _poller.start()
    return _poller


def get_poller() -> BrainPoller | None:
    return _poller


def stop_poller() -> None:
    global _poller
    if _poller and _poller.is_alive():
        _poller.stop()

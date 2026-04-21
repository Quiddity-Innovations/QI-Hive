# -*- coding: utf-8 -*-
"""
QI Brain Distiller
==================
Cleans up Brain's active memory when a project completes, a scope is dropped,
or stale artefacts are detected (worktree paths, dead references, etc.).

Three trigger types:
  completed      — project reached a completion milestone; squash to final state
  scope_dropped  — deliberate scope change; archive everything related to the drop
  stale_cleanup  — remove dead artefacts (worktree paths, old session refs, etc.)

Distillation NEVER hard-deletes. Everything moves to:
  archived_decisions   — active decisions → archive
  archived_features    — active features  → archive
  scope_drops          — record of what was dropped and why

The "why" always stays in the live layer as a single clean entry.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.db import open_brain_db

log = logging.getLogger("qi.brain.distiller")

VALID_REASONS = {"completed", "scope_dropped", "stale_cleanup"}


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def distill(
    project_id: str,
    reason: str,
    scope_label: str = "",
    drop_reason: str = "",
    dropped_by: str = "claude",
    stale_patterns: Optional[list[str]] = None,
) -> dict:
    """
    Distill Brain records for a project.

    Args:
        project_id:      QI project identifier (e.g. 'easyflow', 'naya')
        reason:          'completed' | 'scope_dropped' | 'stale_cleanup'
        scope_label:     Human label for what was dropped ("Naya chat", "NEXUS v1")
        drop_reason:     Why it was dropped (kept in live layer)
        dropped_by:      Who triggered (default 'claude')
        stale_patterns:  For stale_cleanup — list of regex patterns to match
                         against decision/feature text (e.g. ['worktree', 'gifted-visvesvaraya'])

    Returns dict with counts of what was archived.
    """
    if reason not in VALID_REASONS:
        raise ValueError(f"reason must be one of {VALID_REASONS}, got '{reason}'")

    now = datetime.now().isoformat()
    decisions_archived = 0
    features_archived  = 0
    state_written      = False

    with open_brain_db() as conn:

        # ── Verify project exists ────────────────────────────────────────────
        proj = conn.execute(
            "SELECT project_id, display_name FROM projects WHERE project_id=?",
            (project_id,)
        ).fetchone()
        if not proj:
            raise ValueError(f"Unknown project_id: '{project_id}'")

        # ── Archive decisions ────────────────────────────────────────────────
        decisions_to_archive = _select_decisions(
            conn, project_id, reason, scope_label, stale_patterns
        )

        for d in decisions_to_archive:
            conn.execute(
                """INSERT INTO archived_decisions
                       (decision_id, project_id, title, rationale, impact_scope,
                        tags, recorded_at, archived_at, archive_reason, scope_label)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (d["decision_id"], d["project_id"], d["title"], d["rationale"],
                 d["impact_scope"], d["tags"], d["recorded_at"],
                 now, reason, scope_label)
            )
            # Mark superseded in live table so context queries exclude it
            conn.execute(
                """UPDATE decisions
                   SET superseded_by = decision_id,
                       superseded_at = ?,
                       superseded_reason = ?
                   WHERE decision_id = ? AND superseded_by IS NULL""",
                (now, f"distilled: {reason} — {scope_label or drop_reason}", d["decision_id"])
            )
            decisions_archived += 1

        # ── Archive features ─────────────────────────────────────────────────
        features_to_archive = _select_features(
            conn, project_id, reason, scope_label, stale_patterns
        )

        for f in features_to_archive:
            conn.execute(
                """INSERT INTO archived_features
                       (feature_id, source_project, name, description, domain,
                        recorded_at, archived_at, archive_reason, scope_label)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (f["feature_id"], f["source_project"], f["name"], f["description"],
                 f["domain"], f["recorded_at"], now, reason, scope_label)
            )
            features_archived += 1

        # ── Record scope_drop event ──────────────────────────────────────────
        if reason in ("scope_dropped", "completed") and (
            decisions_archived > 0 or features_archived > 0 or scope_label
        ):
            conn.execute(
                """INSERT INTO scope_drops
                       (project_id, scope_label, reason, dropped_by,
                        decisions_archived, features_archived)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (project_id, scope_label or reason,
                 drop_reason or f"distillation trigger: {reason}",
                 dropped_by, decisions_archived, features_archived)
            )

        # ── Write a clean "why" state entry for scope drops ──────────────────
        if reason == "scope_dropped" and drop_reason:
            conn.execute(
                """INSERT INTO project_state
                       (project_id, agent_id, phase, status, summary)
                   VALUES (?, 'system', 'active', 'active', ?)""",
                (project_id,
                 f"Scope dropped: {scope_label or '(unnamed)'}. Reason: {drop_reason}")
            )
            state_written = True

        elif reason == "completed":
            conn.execute(
                """INSERT INTO project_state
                       (project_id, agent_id, phase, status, summary)
                   VALUES (?, 'system', 'complete', 'complete', ?)""",
                (project_id,
                 f"Project distilled at completion. {decisions_archived} decisions archived, "
                 f"{features_archived} features archived. {drop_reason}")
            )
            state_written = True

        conn.commit()

    result = {
        "ok": True,
        "project_id": project_id,
        "reason": reason,
        "scope_label": scope_label,
        "decisions_archived": decisions_archived,
        "features_archived": features_archived,
        "state_written": state_written,
        "distilled_at": now,
    }

    log.info(
        f"Distilled {project_id} ({reason}): "
        f"{decisions_archived}d / {features_archived}f archived"
    )
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Selection helpers
# ─────────────────────────────────────────────────────────────────────────────

def _select_decisions(
    conn, project_id: str, reason: str,
    scope_label: str, stale_patterns: Optional[list[str]]
) -> list[dict]:
    """Return active decisions that should be archived for this distillation."""

    if reason == "completed":
        # Archive ALL active decisions for this project (squash to clean state)
        rows = conn.execute(
            """SELECT decision_id, project_id, title, rationale, impact_scope,
                      tags, recorded_at
               FROM decisions
               WHERE project_id = ? AND superseded_by IS NULL""",
            (project_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    elif reason == "scope_dropped" and scope_label:
        # Archive decisions whose title/rationale/tags mention the dropped scope
        rows = conn.execute(
            """SELECT decision_id, project_id, title, rationale, impact_scope,
                      tags, recorded_at
               FROM decisions
               WHERE project_id = ? AND superseded_by IS NULL""",
            (project_id,)
        ).fetchall()
        return [dict(r) for r in rows if _matches_scope(dict(r), scope_label)]

    elif reason == "stale_cleanup" and stale_patterns:
        rows = conn.execute(
            """SELECT decision_id, project_id, title, rationale, impact_scope,
                      tags, recorded_at
               FROM decisions
               WHERE project_id = ? AND superseded_by IS NULL""",
            (project_id,)
        ).fetchall()
        return [
            dict(r) for r in rows
            if _matches_patterns(dict(r), stale_patterns)
        ]

    return []


def _select_features(
    conn, project_id: str, reason: str,
    scope_label: str, stale_patterns: Optional[list[str]]
) -> list[dict]:
    """Return features that should be archived for this distillation."""

    if reason == "completed":
        rows = conn.execute(
            """SELECT feature_id, source_project, name, description, domain, recorded_at
               FROM features WHERE source_project = ?""",
            (project_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    elif reason == "scope_dropped" and scope_label:
        rows = conn.execute(
            """SELECT feature_id, source_project, name, description, domain, recorded_at
               FROM features WHERE source_project = ?""",
            (project_id,)
        ).fetchall()
        return [dict(r) for r in rows if _matches_scope(dict(r), scope_label)]

    elif reason == "stale_cleanup" and stale_patterns:
        rows = conn.execute(
            """SELECT feature_id, source_project, name, description, domain, recorded_at
               FROM features WHERE source_project = ?""",
            (project_id,)
        ).fetchall()
        return [
            dict(r) for r in rows
            if _matches_patterns(dict(r), stale_patterns)
        ]

    return []


def _matches_scope(record: dict, scope_label: str) -> bool:
    """Check if a record's text fields mention the scope label."""
    needle = scope_label.lower()
    haystack = " ".join([
        str(record.get("title", "")),
        str(record.get("rationale", "")),
        str(record.get("description", "")),
        str(record.get("name", "")),
        str(record.get("tags", "")),
    ]).lower()
    return needle in haystack


def _matches_patterns(record: dict, patterns: list[str]) -> bool:
    """Check if a record matches any of the stale regex patterns."""
    haystack = " ".join([
        str(record.get("title", "")),
        str(record.get("rationale", "")),
        str(record.get("description", "")),
        str(record.get("name", "")),
        str(record.get("tags", "")),
    ])
    for pat in patterns:
        try:
            if re.search(pat, haystack, re.IGNORECASE):
                return True
        except re.error:
            if pat.lower() in haystack.lower():
                return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Auto-distill helpers (called by poller on milestone detection)
# ─────────────────────────────────────────────────────────────────────────────

def auto_stale_cleanup(project_id: str, stale_patterns: list[str]) -> dict:
    """Convenience wrapper for stale-artefact cleanup triggered by the poller."""
    return distill(
        project_id=project_id,
        reason="stale_cleanup",
        scope_label="stale_artefacts",
        drop_reason=f"Auto-detected stale patterns: {stale_patterns}",
        stale_patterns=stale_patterns,
    )

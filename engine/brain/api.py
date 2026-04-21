# -*- coding: utf-8 -*-
"""
QI Brain — FastAPI server at port 9010.

All brain logic lives here. The MCP server (qi_brain_mcp.py) is a thin
stdio client that forwards every tool call to these endpoints.

Endpoints (12 MCP tools + status/dashboard endpoints):
    GET  /health
    GET  /api/status
    POST /api/context              → qi.get_context()
    POST /api/log_decision         → qi.log_decision()
    POST /api/log_feature          → qi.log_feature()
    GET  /api/pending_features     → qi.get_pending_features()
    POST /api/decide_feature       → qi.decide_on_feature()
    POST /api/update_project_state → qi.update_project_state()
    POST /api/search_memory        → qi.search_memory()
    POST /api/log_session          → qi.log_session()
    GET  /api/ecosystem_snapshot   → qi.get_ecosystem_snapshot()
    POST /api/supersede_decision   → qi.supersede_decision()
    POST /api/explain              → qi.explain()
    POST /api/override_evaluation  → qi.override_evaluation()
    GET  /api/providers            → dashboard: list active providers
    GET  /api/config               → dashboard: list brain config

Hive agent growth loop:
    POST /api/agent/growth         → log what an agent learned after a task
    GET  /api/agent/{id}/profile   → full agent profile + growth history + patterns
    GET  /api/agent/{id}/growth    → recent growth entries
    GET  /api/agents               → list all registered hive agents

Run:
    python qi_brain_api.py
    uvicorn qi_brain_api:app --host 0.0.0.0 --port 9010 --reload
"""
from __future__ import annotations
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator


def _norm_pid(pid: str) -> str:
    """Normalize a project_id — lowercase, trimmed, no whitespace.
    Enforces the QI standard: project_ids are always lowercase_snake_case."""
    if not isinstance(pid, str):
        return pid
    return pid.strip().lower().replace(" ", "_").replace("-", "_")

from core.db import open_brain_db
from core.memory_store import MemoryStore, COL_DECISIONS, COL_FEATURES, COL_SESSIONS, COL_DOCS
from core.providers.factory import ProviderFactory
from poller import start_poller, stop_poller, get_poller, run_poll_cycle, INBOX_DIR
from distiller import distill as _distill, VALID_REASONS

app = FastAPI(
    title="QI Brain API",
    version="002",
    description="Shared knowledge substrate for the QI ecosystem",
)

# CORS — allow all QI services
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_store: Optional[MemoryStore] = None


def _memory() -> MemoryStore:
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store


def _cfg(key: str, default: str = "") -> str:
    with open_brain_db() as conn:
        row = conn.execute("SELECT value FROM brain_config WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


# ─────────────────────────────────────────────────────────────────────────────
# Health / Status
# ─────────────────────────────────────────────────────────────────────────────

BRAIN_VERSION = "002"
BRAIN_BUILD   = "2026-04-20"

@app.get("/health")
async def health():
    return {"status": "ok", "service": "qi_brain", "port": 9010, "version": BRAIN_VERSION}


@app.get("/version")
async def version():
    """Simple version probe — used by QI validator and uptime monitors."""
    return {"service": "qi_brain", "version": BRAIN_VERSION, "build": BRAIN_BUILD}


@app.get("/info")
async def info():
    """Full service metadata — capabilities, endpoints, runtime."""
    import sys, platform
    return {
        "service":      "qi_brain",
        "version":      BRAIN_VERSION,
        "build":        BRAIN_BUILD,
        "port":         9010,
        "python":       sys.version.split()[0],
        "platform":     platform.system(),
        "capabilities": [
            "memory_store", "decisions", "features", "sessions",
            "ecosystem_snapshot", "feature_evaluation",
            "poller", "distiller", "inbox", "dispatch"
        ],
        "endpoints_total": len([r for r in app.routes if hasattr(r, "path")]),
        "docs_url":        "/docs",
    }


@app.get("/api/status")
async def status():
    with open_brain_db() as conn:
        n_projects  = conn.execute("SELECT COUNT(*) FROM projects WHERE active=1").fetchone()[0]
        n_decisions = conn.execute("SELECT COUNT(*) FROM decisions WHERE superseded_by IS NULL").fetchone()[0]
        n_features  = conn.execute("SELECT COUNT(*) FROM features").fetchone()[0]
        n_pending   = conn.execute("SELECT COUNT(*) FROM feature_evaluations WHERE decided=0").fetchone()[0]
        n_sessions  = conn.execute("SELECT COUNT(*) FROM session_log").fetchone()[0]
    try:
        chroma = _memory().collection_counts()
    except Exception:
        chroma = {}

    return {
        "ok": True,
        "active_projects":    n_projects,
        "active_decisions":   n_decisions,
        "features_logged":    n_features,
        "pending_reviews":    n_pending,
        "sessions_logged":    n_sessions,
        "chroma_counts":      chroma,
        "providers_active":   len(ProviderFactory.list_active()),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. qi.get_context()  (I-04: ranked, token-budgeted)
# ─────────────────────────────────────────────────────────────────────────────

class GetContextRequest(BaseModel):
    project_id: str
    token_budget: int = 2000

    @field_validator("project_id")
    @classmethod
    def _norm(cls, v): return _norm_pid(v)


@app.post("/api/context")
async def get_context(req: GetContextRequest):
    budget = req.token_budget
    used   = 0

    with open_brain_db() as conn:
        # Current project state
        state = conn.execute(
            "SELECT * FROM project_state WHERE project_id = ? ORDER BY recorded_at DESC LIMIT 1",
            (req.project_id,)
        ).fetchone()
        state_dict = dict(state) if state else {}
        used += _est_tokens(str(state_dict))

        # Decisions — ranked: same project first, then ecosystem-wide, capped by budget
        days = int(_cfg("context_days", "14"))
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        decisions = conn.execute(
            """
            SELECT d.decision_id, d.decision_code, d.title, d.rationale,
                   d.impact_scope, d.tags, d.project_id, d.recorded_at
            FROM decisions d
            WHERE d.superseded_by IS NULL
              AND (d.project_id = ? OR d.impact_scope IN ('ecosystem','global'))
              AND d.recorded_at >= ?
            ORDER BY
                CASE WHEN d.project_id = ? THEN 0 ELSE 1 END,
                d.recorded_at DESC
            LIMIT 50
            """,
            (req.project_id, cutoff, req.project_id)
        ).fetchall()

        ranked_decisions = []
        for row in decisions:
            d = dict(row)
            cost = _est_tokens(str(d))
            if used + cost > budget:
                break
            ranked_decisions.append(d)
            used += cost

        # Pending features for this project
        pending = conn.execute(
            """
            SELECT fe.eval_id, fe.relevance_score, fe.recommendation,
                   fe.reasoning, fe.confidence,
                   f.name as feature_name, f.description, f.domain,
                   f.source_project
            FROM feature_evaluations fe
            JOIN features f ON f.feature_id = fe.feature_id
            WHERE fe.target_project = ? AND fe.decided = 0
            ORDER BY fe.relevance_score DESC
            LIMIT 10
            """,
            (req.project_id,)
        ).fetchall()
        pending_list = [dict(r) for r in pending]

        # Ecosystem snapshot (1 line per project)
        projects = conn.execute(
            "SELECT project_id, display_name, tier FROM projects WHERE active=1"
        ).fetchall()
        snapshot = {}
        for p in projects:
            last_state = conn.execute(
                "SELECT status, phase FROM project_state WHERE project_id = ? ORDER BY recorded_at DESC LIMIT 1",
                (p["project_id"],)
            ).fetchone()
            snapshot[p["project_id"]] = {
                "name":   p["display_name"],
                "tier":   p["tier"],
                "status": last_state["status"] if last_state else "unknown",
                "phase":  last_state["phase"]  if last_state else "",
            }

    return {
        "ok":                True,
        "project_id":        req.project_id,
        "current_state":     state_dict,
        "recent_decisions":  ranked_decisions,
        "pending_features":  pending_list,
        "ecosystem_snapshot": snapshot,
        "token_estimate":    used,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. qi.log_decision()
# ─────────────────────────────────────────────────────────────────────────────

class LogDecisionRequest(BaseModel):
    project_id:    str
    title:         str
    rationale:     str
    agent_id:      str = "claude"
    decision_code: Optional[str] = None
    impact_scope:  str = "project"
    tags:          Optional[list[str]] = None

    @field_validator("project_id")
    @classmethod
    def _norm(cls, v): return _norm_pid(v)


@app.post("/api/log_decision")
async def log_decision(req: LogDecisionRequest):
    tags_json = json.dumps(req.tags or [])
    with open_brain_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO decisions
                (project_id, agent_id, decision_code, title, rationale, impact_scope, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (req.project_id, req.agent_id, req.decision_code,
             req.title, req.rationale, req.impact_scope, tags_json)
        )
        decision_id = cur.lastrowid
        conn.commit()

    # Embed into ChromaDB async
    text = f"{req.title}\n{req.rationale}"
    try:
        await _memory().add_decision(
            decision_id=decision_id,
            text=text,
            metadata={"project_id": req.project_id, "scope": req.impact_scope},
        )
    except Exception:
        pass  # DB write succeeded; Chroma failure is non-fatal

    return {"ok": True, "decision_id": decision_id}


# ─────────────────────────────────────────────────────────────────────────────
# 3. qi.log_feature()
# ─────────────────────────────────────────────────────────────────────────────

class LogFeatureRequest(BaseModel):
    source_project: str
    name:           str
    description:    str
    domain:         str  # 'ui'|'api'|'llm'|'data'|'infra'|'pattern'
    agent_id:       str = "claude"
    code_ref:       Optional[str] = None
    propagate_now:  bool = False

    @field_validator("source_project")
    @classmethod
    def _norm(cls, v): return _norm_pid(v)


@app.post("/api/log_feature")
async def log_feature(req: LogFeatureRequest):
    with open_brain_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO features
                (source_project, logged_by_agent, name, description, domain, code_ref)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (req.source_project, req.agent_id, req.name,
             req.description, req.domain, req.code_ref)
        )
        feature_id = cur.lastrowid
        conn.commit()

    # Embed feature
    try:
        await _memory().add_feature(
            feature_id=feature_id,
            text=f"{req.name}\n{req.description}",
            metadata={"source_project": req.source_project, "domain": req.domain},
        )
    except Exception:
        pass

    # Optional immediate propagation
    evals = []
    if req.propagate_now:
        from feature_engine import propagate_feature
        evals = await propagate_feature(feature_id)

    return {"ok": True, "feature_id": feature_id, "evaluations": len(evals)}


# ─────────────────────────────────────────────────────────────────────────────
# 4. qi.get_pending_features()
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/pending_features")
async def get_pending_features(project_id: Optional[str] = None):
    with open_brain_db() as conn:
        if project_id:
            rows = conn.execute(
                """
                SELECT fe.*, f.name as feature_name, f.description, f.domain, f.source_project
                FROM feature_evaluations fe
                JOIN features f ON f.feature_id = fe.feature_id
                WHERE fe.target_project = ? AND fe.decided = 0
                ORDER BY fe.relevance_score DESC
                """,
                (project_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT fe.*, f.name as feature_name, f.description, f.domain, f.source_project
                FROM feature_evaluations fe
                JOIN features f ON f.feature_id = fe.feature_id
                WHERE fe.decided = 0
                ORDER BY fe.relevance_score DESC
                """
            ).fetchall()
    return {"ok": True, "pending": [dict(r) for r in rows]}


# ─────────────────────────────────────────────────────────────────────────────
# 5. qi.decide_on_feature()
# ─────────────────────────────────────────────────────────────────────────────

class DecideFeatureRequest(BaseModel):
    eval_id:        int
    decided_action: str  # 'adopt'|'adapt'|'skip'|'discuss'
    agent_id:       str = "claude"


@app.post("/api/decide_feature")
async def decide_feature(req: DecideFeatureRequest):
    with open_brain_db() as conn:
        conn.execute(
            """
            UPDATE feature_evaluations
            SET decided=1, decided_at=?, decided_action=?
            WHERE eval_id=?
            """,
            (datetime.now().isoformat(), req.decided_action, req.eval_id)
        )
        conn.commit()
    return {"ok": True, "eval_id": req.eval_id, "action": req.decided_action}


# ─────────────────────────────────────────────────────────────────────────────
# 6. qi.update_project_state()
# ─────────────────────────────────────────────────────────────────────────────

class UpdateProjectStateRequest(BaseModel):
    project_id: str
    phase:      str
    status:     str  # 'active'|'paused'|'blocked'|'complete'
    summary:    str
    agent_id:   str = "claude"
    blockers:   Optional[str] = None
    next_steps: Optional[str] = None

    @field_validator("project_id")
    @classmethod
    def _norm(cls, v): return _norm_pid(v)


@app.post("/api/update_project_state")
async def update_project_state(req: UpdateProjectStateRequest):
    with open_brain_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO project_state
                (project_id, agent_id, phase, status, summary, blockers, next_steps)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (req.project_id, req.agent_id, req.phase, req.status,
             req.summary, req.blockers, req.next_steps)
        )
        conn.commit()
    return {"ok": True, "state_id": cur.lastrowid}


# ─────────────────────────────────────────────────────────────────────────────
# 7. qi.search_memory()
# ─────────────────────────────────────────────────────────────────────────────

_COL_MAP = {
    "decisions": COL_DECISIONS,
    "features":  COL_FEATURES,
    "sessions":  COL_SESSIONS,
    "docs":      COL_DOCS,
}


class SearchMemoryRequest(BaseModel):
    query:      str
    collection: str = "decisions"  # decisions|features|sessions|docs
    n:          int = 5
    project_id: Optional[str] = None


@app.post("/api/search_memory")
async def search_memory(req: SearchMemoryRequest):
    col_name = _COL_MAP.get(req.collection, COL_DECISIONS)
    where = {"project_id": req.project_id} if req.project_id else None
    results = await _memory().search(req.query, collection=col_name, n=req.n, where=where)
    return {"ok": True, "results": results, "collection": req.collection}


# ─────────────────────────────────────────────────────────────────────────────
# 8. qi.log_session()
# ─────────────────────────────────────────────────────────────────────────────

class LogSessionRequest(BaseModel):
    project_id:      str
    session_title:   str
    summary:         str
    agent_id:        str = "claude"
    decisions_made:  int = 0
    features_logged: int = 0
    files_changed:   Optional[list[str]] = None
    next_steps:      Optional[str] = None
    model_used:      Optional[str] = None
    started_at:      Optional[str] = None

    @field_validator("project_id")
    @classmethod
    def _norm(cls, v): return _norm_pid(v)


@app.post("/api/log_session")
async def log_session(req: LogSessionRequest):
    files_json = json.dumps(req.files_changed or [])
    with open_brain_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO session_log
                (project_id, agent_id, session_title, summary, decisions_made,
                 features_logged, files_changed, next_steps, model_used, started_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (req.project_id, req.agent_id, req.session_title, req.summary,
             req.decisions_made, req.features_logged, files_json,
             req.next_steps, req.model_used, req.started_at)
        )
        session_id = cur.lastrowid
        conn.commit()

    # Embed session summary
    try:
        await _memory().add_session(
            session_id=session_id,
            text=f"{req.session_title}\n{req.summary}",
            metadata={"project_id": req.project_id, "model": req.model_used or ""},
        )
    except Exception:
        pass

    return {"ok": True, "session_id": session_id}


# ─────────────────────────────────────────────────────────────────────────────
# 9. qi.get_ecosystem_snapshot()
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/ecosystem_snapshot")
async def ecosystem_snapshot():
    with open_brain_db() as conn:
        projects = conn.execute(
            "SELECT * FROM projects WHERE active=1 ORDER BY tier, project_id"
        ).fetchall()
        result = []
        for p in projects:
            last_state = conn.execute(
                "SELECT phase, status, summary, recorded_at FROM project_state "
                "WHERE project_id=? ORDER BY recorded_at DESC LIMIT 1",
                (p["project_id"],)
            ).fetchone()
            last_session = conn.execute(
                "SELECT session_title, ended_at FROM session_log "
                "WHERE project_id=? ORDER BY ended_at DESC LIMIT 1",
                (p["project_id"],)
            ).fetchone()
            n_decisions = conn.execute(
                "SELECT COUNT(*) FROM decisions WHERE project_id=? AND superseded_by IS NULL",
                (p["project_id"],)
            ).fetchone()[0]
            result.append({
                **dict(p),
                "last_phase":   last_state["phase"]   if last_state else None,
                "last_status":  last_state["status"]  if last_state else None,
                "last_summary": last_state["summary"][:120] if last_state else None,
                "last_session": last_session["session_title"] if last_session else None,
                "last_active":  last_session["ended_at"]      if last_session else None,
                "decisions":    n_decisions,
            })
    return {"ok": True, "projects": result}


# ─────────────────────────────────────────────────────────────────────────────
# 10. qi.supersede_decision()  (I-08)
# ─────────────────────────────────────────────────────────────────────────────

class SupersedeDecisionRequest(BaseModel):
    old_decision_id: int
    new_decision_id: int
    reason:          str


@app.post("/api/supersede_decision")
async def supersede_decision(req: SupersedeDecisionRequest):
    with open_brain_db() as conn:
        # Verify both exist
        old = conn.execute("SELECT decision_id FROM decisions WHERE decision_id=?",
                           (req.old_decision_id,)).fetchone()
        new = conn.execute("SELECT decision_id FROM decisions WHERE decision_id=?",
                           (req.new_decision_id,)).fetchone()
        if not old or not new:
            raise HTTPException(status_code=404, detail="Decision not found")

        conn.execute(
            """
            UPDATE decisions
            SET superseded_by=?, superseded_at=?, superseded_reason=?
            WHERE decision_id=?
            """,
            (req.new_decision_id, datetime.now().isoformat(),
             req.reason, req.old_decision_id)
        )
        conn.commit()
    return {"ok": True}


# ─────────────────────────────────────────────────────────────────────────────
# 11. qi.explain()  (I-10)
# ─────────────────────────────────────────────────────────────────────────────

class ExplainRequest(BaseModel):
    subject_type: str  # 'decision'|'feature'|'session'|'project'
    subject_id:   Any  # int or str


@app.post("/api/explain")
async def explain(req: ExplainRequest):
    with open_brain_db() as conn:
        if req.subject_type == "decision":
            row = conn.execute(
                "SELECT * FROM decisions WHERE decision_id=?", (req.subject_id,)
            ).fetchone()
            if not row:
                raise HTTPException(404, "Decision not found")
            d = dict(row)
            md = (
                f"## Decision: {d.get('decision_code','#'+str(d['decision_id']))} — {d['title']}\n\n"
                f"**Project:** `{d['project_id']}`  |  **Scope:** {d['impact_scope']}\n\n"
                f"**Rationale:**\n{d['rationale']}\n\n"
                f"**Logged:** {d['recorded_at']}"
            )
            if d.get("superseded_by"):
                md += f"\n\n⚠️ **SUPERSEDED** by decision #{d['superseded_by']}: {d.get('superseded_reason','')}"
            return {"ok": True, "markdown": md, "citations": [d["decision_id"]]}

        elif req.subject_type == "feature":
            row = conn.execute(
                "SELECT * FROM features WHERE feature_id=?", (req.subject_id,)
            ).fetchone()
            if not row:
                raise HTTPException(404, "Feature not found")
            f = dict(row)
            evals = conn.execute(
                "SELECT target_project, recommendation, relevance_score, reasoning "
                "FROM feature_evaluations WHERE feature_id=?", (f["feature_id"],)
            ).fetchall()
            eval_lines = "\n".join(
                f"  - `{e['target_project']}`: **{e['recommendation']}** "
                f"(score={e['relevance_score']:.2f}) — {e['reasoning']}"
                for e in evals
            )
            md = (
                f"## Feature: {f['name']}\n\n"
                f"**Source:** `{f['source_project']}`  |  **Domain:** {f['domain']}\n\n"
                f"**Description:**\n{f['description']}\n\n"
                f"**Propagation evaluations:**\n{eval_lines or '(none yet)'}"
            )
            return {"ok": True, "markdown": md, "citations": [f["feature_id"]]}

        elif req.subject_type == "project":
            row = conn.execute(
                "SELECT * FROM projects WHERE project_id=?", (req.subject_id,)
            ).fetchone()
            if not row:
                raise HTTPException(404, "Project not found")
            p = dict(row)
            states = conn.execute(
                "SELECT phase, status, summary, recorded_at FROM project_state "
                "WHERE project_id=? ORDER BY recorded_at DESC LIMIT 3",
                (p["project_id"],)
            ).fetchall()
            state_lines = "\n".join(
                f"  - [{s['recorded_at'][:10]}] **{s['phase']}** ({s['status']}): {s['summary'][:100]}"
                for s in states
            )
            md = (
                f"## Project: {p['display_name']}\n\n"
                f"**ID:** `{p['project_id']}`  |  **Tier:** {p['tier']}\n"
                f"**Path:** `{p['path']}`  |  **API Port:** {p['api_port']}\n\n"
                f"**Recent states:**\n{state_lines or '(no state recorded)'}"
            )
            return {"ok": True, "markdown": md, "citations": [p["project_id"]]}

    raise HTTPException(400, f"Unknown subject_type: {req.subject_type}")


# ─────────────────────────────────────────────────────────────────────────────
# 12. qi.override_evaluation()  (I-14)
# ─────────────────────────────────────────────────────────────────────────────

class OverrideEvalRequest(BaseModel):
    evaluation_id:      int
    new_recommendation: str  # 'adopt'|'adapt'|'skip'|'discuss'
    reason:             str
    overridden_by:      str = "renne"


@app.post("/api/override_evaluation")
async def override_evaluation(req: OverrideEvalRequest):
    with open_brain_db() as conn:
        ev = conn.execute(
            "SELECT eval_id FROM feature_evaluations WHERE eval_id=?", (req.evaluation_id,)
        ).fetchone()
        if not ev:
            raise HTTPException(404, "Evaluation not found")

        cur = conn.execute(
            """
            INSERT INTO evaluation_overrides
                (evaluation_id, overridden_by, new_recommendation, reason)
            VALUES (?, ?, ?, ?)
            """,
            (req.evaluation_id, req.overridden_by, req.new_recommendation, req.reason)
        )
        override_id = cur.lastrowid
        # Also update the evaluation to reflect the override
        conn.execute(
            "UPDATE feature_evaluations SET decided=1, decided_action=? WHERE eval_id=?",
            (req.new_recommendation, req.evaluation_id)
        )
        conn.commit()
    return {"ok": True, "override_id": override_id}


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard helpers
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/providers")
async def list_providers():
    return {"ok": True, "providers": ProviderFactory.list_active()}


@app.get("/api/config")
async def list_config():
    with open_brain_db() as conn:
        rows = conn.execute("SELECT key, value, description, updated_at FROM brain_config").fetchall()
    return {"ok": True, "config": [dict(r) for r in rows]}


@app.get("/api/bootstrap_log")
async def get_bootstrap_log():
    with open_brain_db() as conn:
        rows = conn.execute(
            "SELECT step_name, status, detail, completed_at FROM bootstrap_log ORDER BY step_id"
        ).fetchall()
    return {"ok": True, "steps": [dict(r) for r in rows]}


@app.post("/api/propagate")
async def propagate_all():
    """Trigger feature propagation for all pending features (dashboard button)."""
    from feature_engine import propagate_all_pending
    result = await propagate_all_pending()
    return {"ok": True, **result}


@app.post("/api/config/{key}")
async def update_config(key: str, body: dict):
    value = body.get("value")
    if value is None:
        raise HTTPException(400, "value required")
    with open_brain_db() as conn:
        conn.execute(
            "UPDATE brain_config SET value=?, updated_at=? WHERE key=?",
            (str(value), datetime.now().isoformat(), key)
        )
        conn.commit()
    return {"ok": True, "key": key, "value": value}


# ─────────────────────────────────────────────────────────────────────────────
# Hive — Agent Growth Loop
# Agents log what they learned after each task. Profiles accumulate over time.
# ─────────────────────────────────────────────────────────────────────────────

class GrowthEntry(BaseModel):
    agent_id: str
    session_ref: Optional[str] = None
    project_id: Optional[str] = None
    task_summary: str
    what_worked: Optional[str] = None
    what_to_improve: Optional[str] = None
    pattern_learned: Optional[str] = None
    tags: Optional[list] = None


@app.post("/api/agent/growth")
async def log_agent_growth(body: GrowthEntry):
    """Agent calls this after completing a task to log what it learned."""
    tags_json = json.dumps(body.tags) if body.tags else None
    with open_brain_db() as conn:
        conn.execute(
            """INSERT INTO agent_growth_log
               (agent_id, session_ref, project_id, task_summary,
                what_worked, what_to_improve, pattern_learned, tags)
               VALUES (?,?,?,?,?,?,?,?)""",
            (body.agent_id, body.session_ref, body.project_id, body.task_summary,
             body.what_worked, body.what_to_improve, body.pattern_learned, tags_json)
        )
        conn.commit()
        growth_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return {"ok": True, "growth_id": growth_id, "agent_id": body.agent_id}


@app.get("/api/agent/{agent_id}/profile")
async def get_agent_profile(agent_id: str):
    """Full agent profile: identity + recent growth entries + task stats."""
    with open_brain_db() as conn:
        agent = conn.execute(
            "SELECT * FROM agents WHERE agent_id=?", (agent_id,)
        ).fetchone()
        if not agent:
            raise HTTPException(404, f"Agent '{agent_id}' not found")

        growth = conn.execute(
            """SELECT * FROM agent_growth_log WHERE agent_id=?
               ORDER BY recorded_at DESC LIMIT 20""",
            (agent_id,)
        ).fetchall()

        task_count = conn.execute(
            "SELECT COUNT(*) FROM agent_growth_log WHERE agent_id=?", (agent_id,)
        ).fetchone()[0]

        sessions = conn.execute(
            """SELECT session_title, project_id, ended_at FROM session_log
               WHERE agent_id=? ORDER BY ended_at DESC LIMIT 5""",
            (agent_id,)
        ).fetchall()

        patterns = conn.execute(
            """SELECT pattern_learned, COUNT(*) as freq FROM agent_growth_log
               WHERE agent_id=? AND pattern_learned IS NOT NULL
               GROUP BY pattern_learned ORDER BY freq DESC LIMIT 10""",
            (agent_id,)
        ).fetchall()

    return {
        "agent_id": agent["agent_id"],
        "display_name": agent["display_name"],
        "agent_type": agent["agent_type"],
        "description": agent.get("description"),
        "active": bool(agent["active"]),
        "created_at": agent["created_at"],
        "stats": {"total_tasks": task_count},
        "recent_growth": [dict(g) for g in growth],
        "recent_sessions": [dict(s) for s in sessions],
        "top_patterns": [{"pattern": p["pattern_learned"], "frequency": p["freq"]} for p in patterns],
    }


@app.get("/api/agent/{agent_id}/growth")
async def get_agent_growth(agent_id: str, limit: int = 10):
    """Recent growth log entries for an agent."""
    with open_brain_db() as conn:
        rows = conn.execute(
            "SELECT * FROM agent_growth_log WHERE agent_id=? ORDER BY recorded_at DESC LIMIT ?",
            (agent_id, limit)
        ).fetchall()
    return {"agent_id": agent_id, "entries": [dict(r) for r in rows]}


@app.get("/api/agents")
async def list_agents(active_only: bool = True):
    """List all registered agents in the Hive."""
    with open_brain_db() as conn:
        if active_only:
            rows = conn.execute(
                "SELECT agent_id, display_name, agent_type, description, created_at FROM agents WHERE active=1 ORDER BY agent_type, agent_id"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT agent_id, display_name, agent_type, description, active, created_at FROM agents ORDER BY agent_type, agent_id"
            ).fetchall()
        agents = [dict(r) for r in rows]

    # Enrich with task counts
    with open_brain_db() as conn:
        for a in agents:
            a["task_count"] = conn.execute(
                "SELECT COUNT(*) FROM agent_growth_log WHERE agent_id=?", (a["agent_id"],)
            ).fetchone()[0]

    return {"agents": agents, "total": len(agents)}


# ─────────────────────────────────────────────────────────────────────────────
# CoWork Dispatch — bi-directional task/proposal channel
# Sources: cowork | claude_code | renne | maia | naya
# Types:   report | brief | decision | task | review | proposal | request
# Flow:    source writes dispatch → dashboard shows card → Approve/Decline/Discuss
# ─────────────────────────────────────────────────────────────────────────────
import uuid as _uuid


class DispatchCreate(BaseModel):
    dispatch_id: Optional[str] = None   # auto-generated if omitted
    source:      str                     # cowork | claude_code | renne | maia | naya
    type:        str                     # report | brief | decision | task | review | proposal | request
    priority:    str = "normal"          # high | normal | low
    project_id:  Optional[str] = None
    payload:     Any                     # free-form JSON
    reply_path:  Optional[str] = None


class DispatchReview(BaseModel):
    status:      str            # approved | declined | discussing | executed
    reviewed_by: str = "renne"
    note:        Optional[str] = None   # discussion note or decline reason


@app.post("/api/dispatch")
async def create_dispatch(req: DispatchCreate):
    """Create a new dispatch from any source. Returns dispatch_id."""
    did = req.dispatch_id or str(_uuid.uuid4())
    payload_json = json.dumps(req.payload) if not isinstance(req.payload, str) else req.payload
    with open_brain_db() as conn:
        conn.execute(
            """INSERT INTO dispatches
               (dispatch_id, source, type, priority, project_id, payload, reply_path)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (did, req.source, req.type, req.priority,
             req.project_id, payload_json, req.reply_path)
        )
        conn.commit()
    return {"ok": True, "dispatch_id": did}


@app.get("/api/dispatches")
async def list_dispatches(status: Optional[str] = None, source: Optional[str] = None, limit: int = 50):
    """List dispatches. Filter by status and/or source."""
    with open_brain_db() as conn:
        conditions, params = [], []
        if status:
            conditions.append("status = ?"); params.append(status)
        if source:
            conditions.append("source = ?"); params.append(source)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = conn.execute(
            f"SELECT * FROM dispatches {where} ORDER BY created_at DESC LIMIT ?",
            params + [limit]
        ).fetchall()
    return {"ok": True, "dispatches": [dict(r) for r in rows], "total": len(rows)}


@app.get("/api/dispatch/{dispatch_id}")
async def get_dispatch(dispatch_id: str):
    """Get a single dispatch by ID."""
    with open_brain_db() as conn:
        row = conn.execute(
            "SELECT * FROM dispatches WHERE dispatch_id=?", (dispatch_id,)
        ).fetchone()
    if not row:
        raise HTTPException(404, "Dispatch not found")
    return {"ok": True, "dispatch": dict(row)}


@app.patch("/api/dispatch/{dispatch_id}")
async def review_dispatch(dispatch_id: str, req: DispatchReview):
    """Approve / Decline / mark Discussing. Appends note to notes JSON array."""
    with open_brain_db() as conn:
        row = conn.execute(
            "SELECT notes FROM dispatches WHERE dispatch_id=?", (dispatch_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Dispatch not found")

        notes = json.loads(row["notes"]) if row["notes"] else []
        if req.note:
            notes.append({
                "by": req.reviewed_by,
                "note": req.note,
                "at": datetime.now().isoformat()
            })

        conn.execute(
            """UPDATE dispatches
               SET status=?, reviewed_by=?, reviewed_at=?, notes=?
               WHERE dispatch_id=?""",
            (req.status, req.reviewed_by, datetime.now().isoformat(),
             json.dumps(notes), dispatch_id)
        )
        conn.commit()
    return {"ok": True, "dispatch_id": dispatch_id, "status": req.status}


@app.post("/api/dispatch/{dispatch_id}/note")
async def add_dispatch_note(dispatch_id: str, body: dict):
    """Add a discussion note to a dispatch without changing its status."""
    note_text = body.get("note", "")
    author = body.get("by", "claude_code")
    with open_brain_db() as conn:
        row = conn.execute(
            "SELECT notes, status FROM dispatches WHERE dispatch_id=?", (dispatch_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Dispatch not found")
        notes = json.loads(row["notes"]) if row["notes"] else []
        notes.append({"by": author, "note": note_text, "at": datetime.now().isoformat()})
        conn.execute(
            "UPDATE dispatches SET notes=?, status='discussing' WHERE dispatch_id=?",
            (json.dumps(notes), dispatch_id)
        )
        conn.commit()
    return {"ok": True, "dispatch_id": dispatch_id, "note_count": len(notes)}


# ─────────────────────────────────────────────────────────────────────────────
# Utility
# ─────────────────────────────────────────────────────────────────────────────

def _est_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return len(text) // 4


# ─────────────────────────────────────────────────────────────────────────────
# Startup / Shutdown — poller lifecycle
# ─────────────────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def _startup():
    start_poller()


@app.on_event("shutdown")
async def _shutdown():
    stop_poller()


# ─────────────────────────────────────────────────────────────────────────────
# Poller endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/poll/status")
async def poll_status():
    poller = get_poller()
    with open_brain_db() as conn:
        rows = conn.execute(
            """SELECT poll_id, started_at, finished_at, duration_ms,
                      projects_checked, files_checked, changes_found,
                      inbox_processed, errors, summary
               FROM poll_log ORDER BY poll_id DESC LIMIT 20"""
        ).fetchall()
    return {
        "ok": True,
        "poller_alive":   poller.is_alive() if poller else False,
        "poller_running": getattr(poller, "is_running", False) if poller else False,
        "last_result":    poller.last_result if poller else {},
        "history":        [dict(r) for r in rows],
    }


@app.post("/api/poll/trigger")
async def poll_trigger():
    result = run_poll_cycle()
    return {"ok": True, **result}


# ─────────────────────────────────────────────────────────────────────────────
# Distiller endpoints
# ─────────────────────────────────────────────────────────────────────────────

class DistillRequest(BaseModel):
    project_id:     str
    reason:         str
    scope_label:    str = ""
    drop_reason:    str = ""
    dropped_by:     str = "claude"
    stale_patterns: Optional[list[str]] = None


@app.post("/api/distill")
async def api_distill(req: DistillRequest):
    if req.reason not in VALID_REASONS:
        raise HTTPException(400, f"reason must be one of {sorted(VALID_REASONS)}")
    return _distill(
        project_id=req.project_id, reason=req.reason,
        scope_label=req.scope_label, drop_reason=req.drop_reason,
        dropped_by=req.dropped_by, stale_patterns=req.stale_patterns,
    )


@app.get("/api/distill/history")
async def distill_history(project_id: Optional[str] = None, limit: int = 50):
    with open_brain_db() as conn:
        if project_id:
            rows = conn.execute(
                "SELECT * FROM scope_drops WHERE project_id=? ORDER BY dropped_at DESC LIMIT ?",
                (project_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM scope_drops ORDER BY dropped_at DESC LIMIT ?", (limit,)
            ).fetchall()
    return {"ok": True, "history": [dict(r) for r in rows]}


@app.get("/api/archive/decisions")
async def archive_decisions(project_id: Optional[str] = None, limit: int = 100):
    with open_brain_db() as conn:
        if project_id:
            rows = conn.execute(
                "SELECT * FROM archived_decisions WHERE project_id=? ORDER BY archived_at DESC LIMIT ?",
                (project_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM archived_decisions ORDER BY archived_at DESC LIMIT ?", (limit,)
            ).fetchall()
    return {"ok": True, "archived": [dict(r) for r in rows]}


@app.get("/api/archive/features")
async def archive_features(project_id: Optional[str] = None, limit: int = 100):
    with open_brain_db() as conn:
        if project_id:
            rows = conn.execute(
                "SELECT * FROM archived_features WHERE source_project=? ORDER BY archived_at DESC LIMIT ?",
                (project_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM archived_features ORDER BY archived_at DESC LIMIT ?", (limit,)
            ).fetchall()
    return {"ok": True, "archived": [dict(r) for r in rows]}


# ─────────────────────────────────────────────────────────────────────────────
# Brain Inbox — HTTP (CoWork, any service)
# ─────────────────────────────────────────────────────────────────────────────

class InboxMessage(BaseModel):
    type:            str
    project_id:      str
    source:          str = "http"
    title:           Optional[str] = None
    summary:         Optional[str] = None
    rationale:       Optional[str] = None
    phase:           Optional[str] = None
    status:          Optional[str] = None
    next_steps:      Optional[str] = None
    scope_label:     Optional[str] = None
    reason:          Optional[str] = None
    tags:            Optional[list[str]] = None
    model_used:      Optional[str] = None
    decisions_made:  int = 0
    features_logged: int = 0


@app.post("/api/inbox")
async def inbox_http(msg: InboxMessage):
    now = datetime.now().isoformat()
    payload = msg.model_dump(exclude_none=True)
    error = None
    try:
        with open_brain_db() as conn:
            if msg.type == "state_update":
                conn.execute(
                    "INSERT INTO project_state (project_id, agent_id, phase, status, summary, next_steps) "
                    "VALUES (?, 'system', ?, ?, ?, ?)",
                    (msg.project_id, msg.phase or "active", msg.status or "active",
                     msg.summary or "", msg.next_steps)
                )
            elif msg.type == "decision":
                conn.execute(
                    "INSERT INTO decisions (project_id, agent_id, title, rationale, impact_scope, tags) "
                    "VALUES (?, 'system', ?, ?, 'project', ?)",
                    (msg.project_id, msg.title or "(untitled)", msg.rationale or "",
                     json.dumps(msg.tags or []))
                )
            elif msg.type == "session":
                conn.execute(
                    "INSERT INTO session_log (project_id, agent_id, session_title, summary, "
                    "decisions_made, features_logged, model_used) VALUES (?, 'system', ?, ?, ?, ?, ?)",
                    (msg.project_id, msg.title or "Session", msg.summary or "",
                     msg.decisions_made, msg.features_logged, msg.model_used)
                )
            elif msg.type == "scope_drop":
                result = _distill(
                    project_id=msg.project_id, reason="scope_dropped",
                    scope_label=msg.scope_label or "", drop_reason=msg.reason or "",
                    dropped_by=msg.source,
                )
                conn.execute(
                    "INSERT INTO brain_inbox_log (message_type, project_id, source, payload, status) "
                    "VALUES (?, ?, ?, ?, 'ok')",
                    (msg.type, msg.project_id, msg.source, json.dumps(payload))
                )
                conn.commit()
                return {"ok": True, "type": msg.type, **result}

            conn.execute(
                "INSERT INTO brain_inbox_log (message_type, project_id, source, payload, status) "
                "VALUES (?, ?, ?, ?, 'ok')",
                (msg.type, msg.project_id, msg.source, json.dumps(payload))
            )
            conn.commit()
    except Exception as e:
        error = str(e)
        raise HTTPException(500, f"Inbox error: {error}")

    return {"ok": True, "type": msg.type, "project_id": msg.project_id, "processed_at": now}


@app.get("/api/inbox/log")
async def inbox_log(project_id: Optional[str] = None, limit: int = 50):
    with open_brain_db() as conn:
        if project_id:
            rows = conn.execute(
                "SELECT inbox_id, message_type, project_id, source, source_file, "
                "status, error, processed_at FROM brain_inbox_log WHERE project_id=? "
                "ORDER BY inbox_id DESC LIMIT ?",
                (project_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT inbox_id, message_type, project_id, source, source_file, "
                "status, error, processed_at FROM brain_inbox_log "
                "ORDER BY inbox_id DESC LIMIT ?",
                (limit,)
            ).fetchall()
    return {"ok": True, "messages": [dict(r) for r in rows]}


# ─────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=9010, reload=False)

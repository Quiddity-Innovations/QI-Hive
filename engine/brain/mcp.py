#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QI Brain — MCP stdio server (thin client to FastAPI :9011).

Per Supplement A I-01: ALL logic lives in qi_brain_api.py.
This server is a stdio ↔ HTTP bridge — ~150 LOC of forwarders.

Tools exposed (12 total):
    qi.get_context            → POST /api/context
    qi.log_decision           → POST /api/log_decision
    qi.log_feature            → POST /api/log_feature
    qi.get_pending_features   → GET  /api/pending_features
    qi.decide_on_feature      → POST /api/decide_feature
    qi.update_project_state   → POST /api/update_project_state
    qi.search_memory          → POST /api/search_memory
    qi.log_session            → POST /api/log_session
    qi.get_ecosystem_snapshot → GET  /api/ecosystem_snapshot
    qi.supersede_decision     → POST /api/supersede_decision
    qi.explain                → POST /api/explain
    qi.override_evaluation    → POST /api/override_evaluation

MCP protocol: JSON-RPC 2.0 over stdio (stdin/stdout).
Register globally in: C:\\Users\\renne\\.claude\\claude.json
"""
from __future__ import annotations
import asyncio
import json
import sys
from typing import Any, Optional

import httpx

BRAIN_API = "http://localhost:9011"
TIMEOUT   = 30

# ── JSON-RPC helpers ──────────────────────────────────────────────────────────

def _ok(request_id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _err(request_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _write(msg: dict) -> None:
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


# ── HTTP helpers ──────────────────────────────────────────────────────────────

async def _post(path: str, body: dict) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(f"{BRAIN_API}{path}", json=body)
        resp.raise_for_status()
        return resp.json()


async def _get(path: str, params: Optional[dict] = None) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(f"{BRAIN_API}{path}", params=params or {})
        resp.raise_for_status()
        return resp.json()


# ── Tool definitions (for MCP initialize response) ────────────────────────────

TOOLS = [
    {
        "name": "qi.get_context",
        "description": "Get ranked ecosystem context for session start. Returns current project state, recent decisions, pending feature evaluations, and ecosystem snapshot.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id":   {"type": "string", "description": "Your project ID (e.g. 'maia', 'nexus', 'qi_brain')"},
                "token_budget": {"type": "integer", "description": "Max token budget for response (default 2000)"},
            },
            "required": ["project_id"],
        },
    },
    {
        "name": "qi.log_decision",
        "description": "Log an architectural or significant decision to the brain.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id":    {"type": "string"},
                "title":         {"type": "string"},
                "rationale":     {"type": "string"},
                "agent_id":      {"type": "string", "default": "claude"},
                "decision_code": {"type": "string", "description": "Optional code e.g. AD-013"},
                "impact_scope":  {"type": "string", "enum": ["project","ecosystem","global"]},
                "tags":          {"type": "array", "items": {"type": "string"}},
            },
            "required": ["project_id", "title", "rationale"],
        },
    },
    {
        "name": "qi.log_feature",
        "description": "Log a new feature or pattern discovered in a project for cross-project propagation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_project": {"type": "string"},
                "name":           {"type": "string"},
                "description":    {"type": "string"},
                "domain":         {"type": "string", "enum": ["ui","api","llm","data","infra","pattern"]},
                "agent_id":       {"type": "string", "default": "claude"},
                "code_ref":       {"type": "string"},
                "propagate_now":  {"type": "boolean", "default": False},
            },
            "required": ["source_project", "name", "description", "domain"],
        },
    },
    {
        "name": "qi.get_pending_features",
        "description": "Get feature evaluations awaiting a decision for a project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Filter by target project (optional)"},
            },
        },
    },
    {
        "name": "qi.decide_on_feature",
        "description": "Record your decision on a pending feature evaluation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "eval_id":        {"type": "integer"},
                "decided_action": {"type": "string", "enum": ["adopt","adapt","skip","discuss"]},
                "agent_id":       {"type": "string", "default": "claude"},
            },
            "required": ["eval_id", "decided_action"],
        },
    },
    {
        "name": "qi.update_project_state",
        "description": "Update the current phase and status of a project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "phase":      {"type": "string"},
                "status":     {"type": "string", "enum": ["active","paused","blocked","complete"]},
                "summary":    {"type": "string"},
                "agent_id":   {"type": "string", "default": "claude"},
                "blockers":   {"type": "string"},
                "next_steps": {"type": "string"},
            },
            "required": ["project_id", "phase", "status", "summary"],
        },
    },
    {
        "name": "qi.search_memory",
        "description": "Semantic search across brain memory collections.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query":      {"type": "string"},
                "collection": {"type": "string", "enum": ["decisions","features","sessions","docs"], "default": "decisions"},
                "n":          {"type": "integer", "default": 5},
                "project_id": {"type": "string"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "qi.log_session",
        "description": "Log a completed session summary to the brain.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id":      {"type": "string"},
                "session_title":   {"type": "string"},
                "summary":         {"type": "string"},
                "agent_id":        {"type": "string", "default": "claude"},
                "decisions_made":  {"type": "integer"},
                "features_logged": {"type": "integer"},
                "files_changed":   {"type": "array", "items": {"type": "string"}},
                "next_steps":      {"type": "string"},
                "model_used":      {"type": "string"},
                "started_at":      {"type": "string"},
            },
            "required": ["project_id", "session_title", "summary"],
        },
    },
    {
        "name": "qi.get_ecosystem_snapshot",
        "description": "Get a full snapshot of all active QI projects and their current states.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "qi.supersede_decision",
        "description": "Mark an old decision as superseded by a newer one.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "old_decision_id": {"type": "integer"},
                "new_decision_id": {"type": "integer"},
                "reason":          {"type": "string"},
            },
            "required": ["old_decision_id", "new_decision_id", "reason"],
        },
    },
    {
        "name": "qi.explain",
        "description": "Get a markdown explanation of a decision, feature, session, or project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subject_type": {"type": "string", "enum": ["decision","feature","session","project"]},
                "subject_id":   {"description": "The ID (int or string) of the subject"},
            },
            "required": ["subject_type", "subject_id"],
        },
    },
    {
        "name": "qi.override_evaluation",
        "description": "Override a brain feature evaluation with your own recommendation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "evaluation_id":      {"type": "integer"},
                "new_recommendation": {"type": "string", "enum": ["adopt","adapt","skip","discuss"]},
                "reason":             {"type": "string"},
                "overridden_by":      {"type": "string", "default": "renne"},
            },
            "required": ["evaluation_id", "new_recommendation", "reason"],
        },
    },
]


# ── Request handler ───────────────────────────────────────────────────────────

async def handle_request(req: dict) -> Optional[dict]:
    method = req.get("method", "")
    req_id = req.get("id")
    params = req.get("params", {})

    # MCP lifecycle
    if method == "initialize":
        return _ok(req_id, {
            "protocolVersion": "2024-11-05",
            "capabilities":    {"tools": {}},
            "serverInfo":      {"name": "qi-brain", "version": "001"},
        })

    if method == "notifications/initialized":
        return None  # no response needed

    if method == "tools/list":
        return _ok(req_id, {"tools": TOOLS})

    if method == "tools/call":
        tool_name = params.get("name", "")
        args      = params.get("arguments", {})

        try:
            result = await dispatch_tool(tool_name, args)
            return _ok(req_id, {"content": [{"type": "text", "text": json.dumps(result)}]})
        except httpx.ConnectError:
            return _err(req_id, -32000, "QI Brain API unreachable at :9011. Is qi_brain_api.py running?")
        except Exception as exc:
            return _err(req_id, -32000, str(exc))

    return _err(req_id, -32601, f"Method not found: {method}")


async def dispatch_tool(name: str, args: dict) -> dict:
    """Route tool name to the correct FastAPI endpoint."""
    match name:
        case "qi.get_context":
            return await _post("/api/context", args)
        case "qi.log_decision":
            return await _post("/api/log_decision", args)
        case "qi.log_feature":
            return await _post("/api/log_feature", args)
        case "qi.get_pending_features":
            return await _get("/api/pending_features", {"project_id": args.get("project_id")})
        case "qi.decide_on_feature":
            return await _post("/api/decide_feature", args)
        case "qi.update_project_state":
            return await _post("/api/update_project_state", args)
        case "qi.search_memory":
            return await _post("/api/search_memory", args)
        case "qi.log_session":
            return await _post("/api/log_session", args)
        case "qi.get_ecosystem_snapshot":
            return await _get("/api/ecosystem_snapshot")
        case "qi.supersede_decision":
            return await _post("/api/supersede_decision", args)
        case "qi.explain":
            return await _post("/api/explain", args)
        case "qi.override_evaluation":
            return await _post("/api/override_evaluation", args)
        case _:
            return {"ok": False, "error": f"Unknown tool: {name}"}


# ── Main stdio loop ───────────────────────────────────────────────────────────

async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.write("[qi-brain MCP] started, waiting for requests...\n")
    sys.stderr.flush()

    loop = asyncio.get_event_loop()

    while True:
        try:
            # run_in_executor avoids the Windows ProactorEventLoop connect_read_pipe crash
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            req = json.loads(line)
            response = await handle_request(req)
            if response is not None:
                _write(response)
        except json.JSONDecodeError as exc:
            _write(_err(None, -32700, f"Parse error: {exc}"))
        except Exception as exc:
            sys.stderr.write(f"[qi-brain MCP] error: {exc}\n")
            sys.stderr.flush()


if __name__ == "__main__":
    asyncio.run(main())

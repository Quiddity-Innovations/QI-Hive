# Claude Manager (claude_manager) — L2 brief

_Generated 2026-09-10 02:35:09_

## Registry facts
- Path: `C:\APPS\CLAUDE`
- Status: active
- Notes: Management/meta workspace that operates ON the ecosystem rather than being a deployed app.

## Brain
- Current state: status=active, phase=Trinity â€” both assistants live over MCP; 30-day trial running
  2026-09-08 evening, after Claude Code restart: qi_trinity_check.py --ping = overall PASS (Codex 0.153.4 logged in on ChatGPT Plus, 3 fresh mcp-servers, 0 on deleted binary; Gemini key accepted, 6/200 calls, gemini-3.6-flash; 2 Agent HR rows). Then Claude commanded Codex directly over MCP from the new session (gpt-5.6-luna, read-only, approval never): def_count=18 for qi_gemini_mcp.py, verified by grep = 18. Both Trinity legs now proven on the MCP path, which was the one failure in the previous session (stale 0.118.0 binary until restart). Trial clock starts 2026-09-08; review 2026-10-16.
- Last decisions:
  - Claude on top; ChatGPT and Gemini are on-demand assistants over MCP; NEXUS out; zero API spend; 30-day trial with termination option (2026-09-08)

## CLAUDE.md rules
- No CLAUDE.md found (or no matching rule/heading lines).

## Entry points
`gen_latest.py`, `gen_qih_overview.py`, `gen_qih_projects_append.py`, `health_check.py`

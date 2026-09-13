# QI Connector (connector) — L2 brief

_Generated 2026-09-12 02:35:04_

## Registry facts
- Path: `C:\APPS\QIP\Connector`
- Status: active_development
- Ports: api:9030
- Services: QI_ConnectorMCP, QI_ConnectorTunnel
- Notes: Backbone infrastructure — the ecosystem's front door for Claude clients. One remote MCP connector (claude.ai custom connector) replaces per-machine, per-tool MCP config: claude.ai web/mobile, Claude Desktop and Claude Code all reach QI tools through connector.quiddityinnovations.com. Registered 2026-07-30.

## Brain
- Current state: status=active, phase=v1.0 live + dispatch executor tools (2026-08-16); docs behind code
  Backfilled 2026-09-09 from QI_Project_Status_Report_2026-09-09.docx (Claude Fable 5.1). QI_ConnectorMCP :9030 and QI_ConnectorTunnel RUNNING, /health ok. Since the 07-30 summary: generic MapSnap/NEXUS/Maia/Naya tool sections (07-31 to 08-02) and dispatch executor tools qi_list_scripts / qi_execute_script / qi_script_status (08-16) — never documented in a session summary.
- No project-scoped decisions recorded.

## CLAUDE.md rules
# QI Connector — Claude Project Instructions
# Quiddity Innovations
## READ BEFORE ACTING
## What QI Connector Is
## Architecture
- Tokens auto-generate into `secrets/` on first run (`connector_token.txt`, `connector_path_token.txt`; paste-ready `CONNECTOR_URLS.txt`). **Never commit or print token values into docs/logs/chat.**
- Brain calls proxy `http://localhost:9011` with graceful fallback — the connector must stay useful when the Brain is down (cross-project call rule).

## Ports (DO NOT CHANGE without updating qi_registry.json first)
## Services & Ops
## Rules for changes

## Entry points
`Start_Connector.bat`, `main.py`, `qi_executor.py`

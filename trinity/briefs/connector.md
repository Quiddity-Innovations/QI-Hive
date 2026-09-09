# QI Connector (connector) — L2 brief

_Generated 2026-09-08 17:56:10_

## Registry facts
- Path: `C:\APPS\QIP\Connector`
- Status: active_development
- Ports: api:9030
- Services: QI_ConnectorMCP, QI_ConnectorTunnel
- Notes: Backbone infrastructure — the ecosystem's front door for Claude clients. One remote MCP connector (claude.ai custom connector) replaces per-machine, per-tool MCP config: claude.ai web/mobile, Claude Desktop and Claude Code all reach QI tools through connector.quiddityinnovations.com. Registered 2026-07-30.

## Brain
- Current state: status=active_development, phase=v1.0 live
  Remote MCP connector live at connector.quiddityinnovations.com (QI_ConnectorMCP :9030 + QI_ConnectorTunnel). 7 tools, dual auth, smoke-tested publicly.
- Last decisions:
  - Hive currency pass 2026-09-08: registry brought to 42 projects; C:\APPS stays the registered path even where git history lives only in D:\Dev; QI-RELAY is a Maia component, not a project (2026-09-08 21:51:31)
  - Trinity health is inspected daily without calling an assistant; every assistant run is recorded in Agent HR as trial evidence (2026-09-08 21:37:12)
  - Codex calls always name the model; CLI default pinned to gpt-5.6-terra; ladder luna â†’ terra â†’ sol, astra only with a stated reason (2026-09-08 21:37:00)

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

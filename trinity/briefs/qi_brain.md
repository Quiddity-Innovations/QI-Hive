# QI Brain (qi_brain) — L2 brief

_Generated 2026-09-08 17:56:09_

## Registry facts
- Path: `C:\QIH\engine\brain`
- Status: active
- Ports: api:9011, mcp:stdio
- Services: QI_BrainAPI

## Brain
- Current state: status=active, phase=Phase 5 — operational
  Brain API on :9011 (moved from 9010 on 2026-05-14 — Logitech G HUB squats 9010). SQLite + ChromaDB + 12 MCP tools. NSSM QI_BrainAPI running.
- Last decisions:
  - Hive currency pass 2026-09-08: registry brought to 42 projects; C:\APPS stays the registered path even where git history lives only in D:\Dev; QI-RELAY is a Maia component, not a project (2026-09-08 21:51:31)
  - Trinity health is inspected daily without calling an assistant; every assistant run is recorded in Agent HR as trial evidence (2026-09-08 21:37:12)
  - Codex calls always name the model; CLI default pinned to gpt-5.6-terra; ladder luna â†’ terra â†’ sol, astra only with a stated reason (2026-09-08 21:37:00)

## CLAUDE.md rules
- No CLAUDE.md found (or no matching rule/heading lines).

## Entry points
`api.py`, `bootstrap.py`, `distiller.py`, `doc_harvester.py`, `feature_engine.py`, `mcp.py`, `poller.py`

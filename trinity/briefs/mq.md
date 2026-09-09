# MQ (mq) — L2 brief

_Generated 2026-09-08 17:56:09_

## Registry facts
- Path: `C:\APPS\MQ`
- Status: paused
- Ports: api:8500, ui:7840
- Notes: New project — family role to be determined as it develops. Status 2026-05-13: not started yet (was paused_pending_credentials; corrected to new).

## Brain
- Current state: status=paused, phase=Phase 0 — scaffold
  Marked paused by the 2026-08-17 audit — 133 days without a session; scaffold only. Silence is now intentional, so compliance stops filing session_freshness/brain_drift. Set back to 'active' on the next real session.
- Last decisions:
  - Hive currency pass 2026-09-08: registry brought to 42 projects; C:\APPS stays the registered path even where git history lives only in D:\Dev; QI-RELAY is a Maia component, not a project (2026-09-08 21:51:31)
  - Trinity health is inspected daily without calling an assistant; every assistant run is recorded in Agent HR as trial evidence (2026-09-08 21:37:12)
  - Codex calls always name the model; CLI default pinned to gpt-5.6-terra; ladder luna â†’ terra â†’ sol, astra only with a stated reason (2026-09-08 21:37:00)

## CLAUDE.md rules
# Maia Quiddam (MQ) — Claude Project Instructions
# Quiddity Innovations
## READ BEFORE ACTING
## What MQ Is
## Architecture (Hybrid model — see docs/Technical Documentation/ARCHITECTURE.md)
## Paths
[line redacted by qi_handoff secret-pattern filter]

## Ports (DO NOT CHANGE without updating qi_registry.json first)
## Public tunnel (static) — quiddam.com
Tooling + master map: `C:\QIH\engine\tunnels\` (`tunnels.json`, entry `qi-mq`). It's a **static named tunnel** — use `api.quiddam.com` for the Meta webhook URL (it never changes). Do NOT create quick tunnels; add/adjust ingress in `tunnels.json` and re-run the migrator. Reserved hosts return HTTP 502 until an app is bound to their port.

## Secrets Required (in secrets/mq.env)
## Parallel Projects — Do Not Break

## Entry points
`Start_MQ.bat`, `main.py`

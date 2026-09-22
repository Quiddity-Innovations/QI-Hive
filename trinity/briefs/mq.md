# MQ (mq) — L2 brief

_Generated 2026-09-21 02:34:03_

## Registry facts
- Path: `C:\APPS\MQ`
- Status: paused
- Ports: api:8500, ui:7840
- Notes: New project — family role to be determined as it develops. Status 2026-05-13: not started yet (was paused_pending_credentials; corrected to new).

## Brain
- Brain offline or unreachable — skipped.

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

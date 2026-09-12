# OpenClaw (openclaw) — L2 brief

_Generated 2026-09-11 02:36:20_

## Registry facts
- Path: `C:\APPS\OC`
- Status: active_production
- Ports: gateway:18789
- Notes: Autonomous agent layer. Where Maia responds, OpenClaw acts. Future: Maia routes complex action tasks to OpenClaw. Strong marriage candidate with Maia for agent-assisted conversations.

## Brain
- Current state: status=active, phase=Phase 2 â€” agent expansion (recovered + modernized)
  Fully recovered and modernized 2026-08-27. All SIX agents verified working: Kaze (digests fired unattended 18:00/18:05), Sentry, Asa, Kakei, Tasuke, and YUBIN. Service renamed to QI_OCKeepalive and proven broker-manageable (nssm restart via QI_Elevate returns status: ok); freshness alarm armed and logging "Kaze digest OK" every 30 min. OpenClaw upgraded 2026.4.26 -> 2026.6.34; gateway on loopback; MCP recovered from total failure via transport=streamable-http, giving Tasuke 38 tools. Memory on local nomic-embed-text (4/4 files). TOOLS.md truncation eliminated. CORRECTION LOGGED (decision 581): my earlier claim that Yubin was dead was WRONG â€” it logs to /home/hyosuke/.openclaw/logs/yubin-task.log, not runtime/logs/agents/yubin/, and ran successfully today at 16:22 and 17:59. Yubin is load-bearing (feeds Kakei, Sentry, Asa, Tasuke) and is the email half of the shared "Maia Quiddam" persona alongside Kaze. Do not retire it.
- No project-scoped decisions recorded.

## CLAUDE.md rules
# OpenClaw (OC) — Claude Project Instructions
# Quiddity Innovations
## SESSION START PROTOCOL (Mandatory — Every Session)
4. **Silently internalize** — do NOT summarize back to Renne unless asked
5. **Only then** respond to the first message

## QI Standards
## What OpenClaw Is
## Paths
## Ports
## Parallel Projects — Do Not Break

## Entry points
`OC_Control_Panel_v6.bat`, `OpenClaw_Dashboard.bat`, `restart-keepalive-admin.bat`, `tasuke-tools-update.py`

# Naya (naya) — L2 brief

_Generated 2026-09-09 02:38:45_

## Registry facts
- Path: `C:\APPS\NAYA`
- Status: running_dev_paused
- Ports: api:8002, ui:7861
- Services: NayaBot
- Notes: Personal file management AI for Renne. Absorbed FileHQ as file engine module. Telegram is the only chat interface. LAN-only — no Cloudflare tunnel, no internet exposure.

## Brain
- Current state: status=paused, phase=Phase 5 â€” capability behind OpenClaw (application retired)
  GENUINELY paused 2026-08-28 â€” not just a status field this time. QI_NayaBot, QI_NayaGradio and QI_NayaTunnel are Stopped with StartType Manual, so reboots no longer revive them; the nightly 02:00 4.5-hour multi-drive scan is halted. No data deleted (naya_brain.db 4.15 GB and filehq.db 2.63 GB intact). Naya is now a CAPABILITY OpenClaw calls rather than a standalone app: the FileHQ engine was extracted from naya_server.py (where it ran as a daemon thread) into standalone service QI_FileHQ on loopback :8200, fronted by MCP gateway QI_NayaMCP on :8250, consumed by OpenClaw as `qi-naya` and by Claude Desktop. Both new services are QI_-prefixed and broker-manageable. Standard docs (Implementation Log, Meeting Minutes, Version History) created â€” they had been missing since project start. Key correction logged: FileHQ is NOT a separate engine, it IS Naya's scanner (naya_watcher.py imports filehq_bridge), so it must not be dumped and rebuilt.
- Last decisions:
  - Naya becomes a capability OpenClaw calls, not a standalone application (2026-08-28)

## CLAUDE.md rules
# Naya — Claude Project Instructions
# Quiddity Innovations
## SESSION START PROTOCOL (Mandatory — Every Session)
4. **Silently internalize** — do NOT summarize back to Renne unless asked
5. **Only then** respond to the first message

## Read Before Acting
## What Naya Is
## Naya ↔ Maia Relationship
## Paths
## Ports (DO NOT CHANGE without updating qi_registry.json)
- New Naya services must use block: **8200–8299**

## Key Files
## DB Maintenance
## Ecosystem Relationships
## Naya_Control.bat Menu (reference — do not guess)
## Parallel Projects — Do Not Break

## Entry points
`Naya_Control.bat`, `Naya_Install.bat`, `Naya_Start.bat`, `filehq_bridge.py`, `filehq_service.py`, `kill_naya.py`, `maia_files.py`, `naya_action_router.py`, `naya_advisor.py`, `naya_context.py`, `naya_db.py`, `naya_db_core.py`, `naya_deferral.py`, `naya_executor.py`, `naya_gradio.py`, `naya_help.py`, `naya_intent_router.py`, `naya_lang.py`, `naya_line.py`, `naya_llm_intent.py`, `naya_memory.py`, `naya_reporter.py`, `naya_scanner.py`, `naya_server.py`, `naya_watchdog.py`

# Naya (naya) — L2 brief

_Generated 2026-09-11 02:36:20_

## Registry facts
- Path: `C:\APPS\NAYA`
- Status: paused
- Ports: api:8002, ui:7861
- Services: NayaBot
- Notes: 2026-09-09: status running_dev_paused->paused — app layer stopped/Manual since 2026-08-28; engine lives on as QI_FileHQ + QI_NayaMCP (Brain state)

## Brain
- Current state: status=paused, phase=Phase 5 — capability behind OpenClaw (application retired 2026-08-28)
  Backfilled 2026-09-09 from QI_Project_Status_Report_2026-09-09.docx (Claude Fable 5.1). App layer (QI_NayaBot/Gradio/Tunnel) STOPPED, StartType Manual, deliberate. Engine lives on as QI_FileHQ :8200 + QI_NayaMCP :8250, both RUNNING and consumed by OpenClaw and Claude Desktop. naya_brain.db (4.15 GB) and filehq.db (2.63 GB) intact. Registry status corrected 2026-09-09 to paused.
- No project-scoped decisions recorded.

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

# Maia (maia) — L2 brief

_Generated 2026-09-10 02:35:09_

## Registry facts
- Path: `C:\APPS\QI`
- Status: active_production
- Ports: api:8001, ui:7860
- Services: QI_MaiaBot, QI_MaiaDemoTunnel, QI_MaiaTunnel
- Notes: The flagship product. All other projects ultimately serve Maia or learn from it.

## Brain
- Current state: status=active, phase=Phase 4 — production; AWS LINE relay + channel refactor live
  Backfilled 2026-09-09 from QI_Project_Status_Report_2026-09-09.docx (Claude Fable 5.1). Bot :8001, Gradio, tunnel, QueueDrain all RUNNING under NSSM. Since June: AWS Lambda+SQS webhook relay (2026-07-30), channels/*.py split with replay tests, Meta signature verification, bcrypt auth, watchdog hardening, QI-RELAY collaborator channel (2026-08-19). Last real feature commits ~2026-08-05.
- No project-scoped decisions recorded.

## CLAUDE.md rules
# Maia — Claude Project Instructions
# Quiddity Innovations
## ⚠️ Read Before Acting
## What Maia Is
## Paths
## Ports (DO NOT CHANGE without updating qi_registry.json)
- New Maia services must use block: **8100–8199**

## Key Services
## Tech Stack
## Ecosystem Relationships
## NSSM Services
## Parallel Projects — Do Not Break

## Entry points
`Maia_Control.bat`, `Maia_Install.bat`, `Maia_Install_Watchdog.bat`, `Maia_Restart_Bot.bat`, `kill_maia.py`, `maia_audit.py`, `maia_auth.py`, `maia_batch.py`, `maia_cache.py`, `maia_content.py`, `maia_context.py`, `maia_control - (backup on 03-24-2026).bat`, `maia_control_panel.py`, `maia_csv.py`, `maia_db.py`, `maia_fmt.py`, `maia_gradio.py`, `maia_guardian.py`, `maia_health.py`, `maia_i18n.py`, `maia_lang.py`, `maia_list_manager.py`, `maia_phase4.py`, `maia_rag.py`, `maia_reconcile.py`

# Maia (maia) — L2 brief

_Generated 2026-09-08 17:56:09_

## Registry facts
- Path: `C:\APPS\QI`
- Status: active_production
- Ports: api:8001, ui:7860
- Services: QI_MaiaBot, QI_MaiaDemoTunnel, QI_MaiaTunnel
- Notes: The flagship product. All other projects ultimately serve Maia or learn from it.

## Brain
- Current state: status=active, phase=Phase 4 — production
  Bot :8001 + Gradio :7860 + tunnels live under NSSM. Last code work 2026-05-15 (BP overrides, sibling filter, topic propagation, Cloudflare primary).
- Last decisions:
  - Hive currency pass 2026-09-08: registry brought to 42 projects; C:\APPS stays the registered path even where git history lives only in D:\Dev; QI-RELAY is a Maia component, not a project (2026-09-08 21:51:31)
  - Trinity health is inspected daily without calling an assistant; every assistant run is recorded in Agent HR as trial evidence (2026-09-08 21:37:12)
  - Codex calls always name the model; CLI default pinned to gpt-5.6-terra; ladder luna â†’ terra â†’ sol, astra only with a stated reason (2026-09-08 21:37:00)

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

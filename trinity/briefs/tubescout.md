# TubeScout (tubescout) — L2 brief

_Generated 2026-09-12 02:35:04_

## Registry facts
- Path: `C:\APPS\TUBESCOUT`
- Status: active_development
- Ports: api:8503, ui:7843
- Services: QI_TubeScout, QI_TubeScoutTunnel
- Notes: YouTube subscription intelligence. Feeds NEXUS Scout (Kaze digest) + QI Brain implement-scoring. Sibling-in-spirit of NEXUS Scout.

## Brain
[line redacted by qi_handoff secret-pattern filter]
  Backfilled 2026-09-09 from QI_Project_Status_Report_2026-09-09.docx (Claude Fable 5.1). QI_TubeScout :8503 and tunnel RUNNING; data\logs\cycle.log shows a full sweep completing 2026-09-09 07:08 (109 channels). The 2026-08-27 audit finding "dead 66 days on expired OAuth token" was fixed the same day: Google OAuth Testing mode caps refresh tokens at 7 days, so the daily sweep moved to a non-expiring API key and --login can recover a revoked token. Audit item closed 2026-09-09.
- No project-scoped decisions recorded.

## CLAUDE.md rules
# TubeScout — Claude Project Instructions
# Quiddity Innovations
## READ BEFORE ACTING
## What TubeScout Is
## Paths
## Ports (DO NOT CHANGE without updating qi_registry.json first)
## Parallel Projects — Do Not Break

## Entry points
`TubeScout_Install.bat`, `TubeScout_Run_Cycle.bat`, `TubeScout_Start.bat`, `TubeScout_Start_Server.bat`, `main.py`

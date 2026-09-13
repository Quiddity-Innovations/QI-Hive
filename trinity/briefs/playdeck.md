# PlayDeck (playdeck) — L2 brief

_Generated 2026-09-12 02:35:04_

## Registry facts
- Path: `C:\APPS\PlayDeck`
- Status: active
- Ports: api:8506, ui:7846
- Notes: 2026-09-10: private GitHub repo created and pushed (owner: only PlayDeck gets a remote; OC stays local-only).

## Brain
- Current state: status=active, phase=Feature build — subjects + subscriptions; live-broadcast fix shipped 2026-08-28
  Backfilled 2026-09-09 from QI_Project_Status_Report_2026-09-09.docx (Claude Fable 5.1). QI_PlayDeck :8506 RUNNING (the only media-group service actually up). 2026-08-28 fixed HLS-manifest capture for non-flat yt-dlp entries and the live-broadcast 0% hang (pre-check + plain-English refusal + dismiss stuck rows). The fix ran live but sat uncommitted for 12 days; committed 2026-09-09.
- No project-scoped decisions recorded.

## CLAUDE.md rules
# PlayDeck — Claude Project Instructions
# Quiddity Innovations
## READ BEFORE ACTING
## What PlayDeck Is
## Paths
## Ports (DO NOT CHANGE without updating qi_registry.json first)
## Parallel Projects — Do Not Break

## Entry points
`Install_Service.bat`, `Start_PlayDeck.bat`, `main.py`

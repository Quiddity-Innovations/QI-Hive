# TubeScout (tubescout) — L2 brief

_Generated 2026-09-09 02:38:45_

## Registry facts
- Path: `C:\APPS\TUBESCOUT`
- Status: active_development
- Ports: api:8503, ui:7843
- Services: QI_TubeScout, QI_TubeScoutTunnel
- Notes: YouTube subscription intelligence. Feeds NEXUS Scout (Kaze digest) + QI Brain implement-scoring. Sibling-in-spirit of NEXUS Scout.

## Brain
- Current state: status=active, phase=MVP + refinements complete
  Overnight refinements done: page persists via no-admin Startup launcher (NSSM service wedged on SYSTEM account, corrected bat left); classification fixed (other 450->1 via YouTube topicCategories + ranking, new granular topics); cross-channel dedup live (10 dups->8 cross-covered, '+N also covered' on page); Whisper fallback built + verified (opt-in, off by default, live-stream guard); Brain test feature 304 removed. Page serving 353 deduped cards / 13 topics; 7am/7pm tasks Ready.
- Last decisions:
  - TubeScout must move off OAuth to an API key â€” Testing-mode caps tokens at 7 days (2026-08-27)

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

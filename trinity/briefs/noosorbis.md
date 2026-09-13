# NoosOrbis (noosorbis) — L2 brief

_Generated 2026-09-12 02:35:04_

## Registry facts
- Path: `C:\APPS\NoosOrbis`
- Status: live
- Ports: api:8507, ui:7847
- Notes: 2026-09-09: status new->live — v0.5.0 complete, owner signed off 2026-08-22, public via QI Gate

## Brain
- Current state: status=active, phase=development
  v0.3.x. Now multilingual across eight languages â€” en, es, fr, pt, ru, zh, ja, ko (Tier 1 + Tier 2 of the 2026-09-09 evaluation). Language is request-scoped; the cache-collision bug that would have served one language's articles to all eight is fixed; the interface is translated at el() with 284 strings per language; typography follows the script (Noto Sans SC/JP/KR, em-based measure for CJK, keep-all for Korean); language switching follows the article via langlinks. Also restored /api/librarian/{status,ask,ask_sync,suggest_collection}, 404 since 2026-08-26, and fixed a test suite that reported green while checks failed. 36 tests pass under both runners. Committed and pushed (02a8633). NOT YET LIVE: QI_NoosOrbis still runs the old code and needs an administrator restart.
- Last decisions:
  - Offer both Chinese written forms â€” and never ask Wikipedia for neither (2026-09-09)
  - Retrofit i18n at the one function that creates DOM text, not at the call sites (2026-09-09)

## CLAUDE.md rules
# NoosOrbis — Claude Project Instructions
# Quiddity Innovations
## READ BEFORE ACTING
## What NoosOrbis Is
## Paths
## Ports (DO NOT CHANGE without updating qi_registry.json first)
## Parallel Projects — Do Not Break

## Entry points
`Start_NoosOrbis.bat`, `main.py`, `noosorbis_mark.html`, `noosorbis_reader_prototype.html`

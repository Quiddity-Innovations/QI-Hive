# AvatarStudio (avatarstudio) — L2 brief

_Generated 2026-09-21 02:34:42_

## Registry facts
- Path: `C:\APPS\AvatarStudio`
- Status: active
- Ports: ui:7862
- Notes: Media-generation studio. Depends on WSL2 for avatar render backends. Shares the avatar/voice vision used across QI agents.

## Brain
- Brain offline or unreachable — skipped.

## CLAUDE.md rules
# QI Avatar Studio — Claude Session Instructions
`D:\Dev\AvatarStudio\` is a plain git-clone backup on a second disk: never
edited, never running. Editing now means: edit in `C:\APPS`, restart the
service. No promote step.
**Studio URL:** http://localhost:7862
## What This Project Is
## Key Files
## Language Engine Routing
never semitones** (see Known Fixes).

---
## Media Studio Plug-in Contract (WP2, 2026-09-09)
## WSL2 Environments
## Render Engines — Quick Guide
### LivePortrait (fast, ~30 sec)
### Hallo2 (slow, ~15–30 min per minute of audio)
### video-retalking (post-process, +5–10 min)
## Agents (agents.json)
## Known Fixes Applied
- **Launcher silent failure (2026-09-05)**: `run_studio.bat` now pre-flights that the venv interpreter actually *runs* (not just that the file exists), tees output to `logs/studio_console.log`, and pauses on failure. `start_studio.py` now verifies the real outcome — polls `http://127.0.0.1:7862/` for HTTP 200 — instead of trusting `proc.poll() is None`, which reported success even when the port never bound.
- **edge-tts pitch (2026-09-09)**: `generate_voice()` emitted pitch as `"+0st"`. edge-tts >= 7
  validates against `^[+-]\d+Hz$` and raises `ValueError: Invalid pitch '+0st'` before writing a
## How to Kill & Restart the Studio
## Pending Work (Next Session)
## QI Ecosystem Context
## 🔴 Colours are not edited here
`qi_plugin.json`. Standalone, it follows the OS exactly as it always has.

## Entry points
`avatar_pipeline.py`, `avatar_studio.py`, `check_syntax.py`, `diagnose.py`, `gen_tokyo_times_tts.py`, `gen_voices_kokoro.py`, `generate_summary.py`, `install_service.bat`, `run_avatar.bat`, `run_studio.bat`, `scene_pipeline.py`, `smoke_test.py`, `start_studio.py`, `test_all_languages.py`, `test_edge_tts.py`, `test_langs.py`, `test_routing.py`

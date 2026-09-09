# AvatarStudio (avatarstudio) — L2 brief

_Generated 2026-09-09 02:38:45_

## Registry facts
- Path: `C:\APPS\AvatarStudio`
- Status: active
- Ports: ui:7862
- Notes: Media-generation studio. Depends on WSL2 for avatar render backends. Shares the avatar/voice vision used across QI agents.

## Brain
- Current state: status=active, phase=v1 — secured + backed up
  Gradio talking-head pipeline on :7862. D-ID API key moved out of studio_config.json into gitignored secrets/avatarstudio.env (loaded via env/secret overlay; stripped on save). Key purged from the AvatarStudio private GitHub repo (history rewritten). Now git-backed at Quiddity-Innovations/AvatarStudio.
- No project-scoped decisions recorded.

## CLAUDE.md rules
# QI Avatar Studio — Claude Session Instructions
## What This Project Is
## Key Files
## Language Engine Routing
## WSL2 Environments
## Render Engines — Quick Guide
### LivePortrait (fast, ~30 sec)
### Hallo2 (slow, ~15–30 min per minute of audio)
### video-retalking (post-process, +5–10 min)
## Agents (agents.json)
## Known Fixes Applied
- **Launcher silent failure (2026-09-05)**: `run_studio.bat` now pre-flights that the venv interpreter actually *runs* (not just that the file exists), tees output to `logs/studio_console.log`, and pauses on failure. `start_studio.py` now verifies the real outcome — polls `http://127.0.0.1:7862/` for HTTP 200 — instead of trusting `proc.poll() is None`, which reported success even when the port never bound.
- **dlib**: built CPU-only (`CMAKE_ARGS='-DDLIB_USE_CUDA=OFF'`) — CUDA 12.8 conflict
- **GPEN CUDA**: headers symlinked from nvidia/cusparse into conda env
## How to Kill & Restart the Studio
## Pending Work (Next Session)
## QI Ecosystem Context

## Entry points
`avatar_pipeline.py`, `avatar_studio.py`, `check_syntax.py`, `diagnose.py`, `gen_tokyo_times_tts.py`, `gen_voices_kokoro.py`, `generate_summary.py`, `install_service.bat`, `run_avatar.bat`, `run_studio.bat`, `scene_pipeline.py`, `smoke_test.py`, `start_studio.py`, `test_all_languages.py`, `test_edge_tts.py`, `test_langs.py`, `test_routing.py`

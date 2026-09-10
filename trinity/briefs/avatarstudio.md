# AvatarStudio (avatarstudio) — L2 brief

_Generated 2026-09-10 15:35:33_

## Registry facts
- Path: `C:\APPS\AvatarStudio`
- Status: active
- Ports: ui:7862
- Notes: Media-generation studio. Depends on WSL2 for avatar render backends. Shares the avatar/voice vision used across QI agents.

## Brain
- Current state: status=active_development, phase=WP2 complete â€” Media Studio plug-in contract satisfied, awaiting promotion
  AvatarStudio now satisfies all six rows of the Media Studio plug-in contract (PLUGINS.md Â§1), built and committed in D:/Dev/AvatarStudio (94dc676, 86 tests passing). Render core extracted into avatar_pipeline.py with render_avatar() as the single orchestration generator; the Gradio GUI, the new FastAPI service and scene_pipeline.py are all thin callers, so the engine chain exists once. engine/service.py serves /health /version /info /api/render /api/jobs /api/gpu on 7862 and mounts the Gradio panel at / honouring ?embed=1 â€” one port for both doors because ui.port is what Media Studio iframes AND health-probes. driving_audio short-circuits TTS (the Voice Studio / CONVERGENCE item 1 seam). Outputs go to D:/AI/Outputs/AvatarStudio/<job_id>/ with a JSON sidecar. qi_plugin.json validated by Media Studio's own engine/plugins.py with zero warnings. Registry entry extended additively (Tier 2, backup .bak-20260909). Decision #599.

Also fixed a live bug: edge-tts emitted pitch as "+0st", which edge-tts >= 7 rejects before writing audio â€” Japanese, French, Russian and German produced NO sound at all. Still broken in C:/APPS until promotion.

Not done, deliberately: gpu.peak_vram_gb is null because the RTX 5080 was held by another tenant (14.1/16.3 GB) all session. Jobs now sample nvidia-smi into their sidecars so the first Hallo2 render on an idle card produces the number.
- No project-scoped decisions recorded.

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

## Entry points
`avatar_pipeline.py`, `avatar_studio.py`, `check_syntax.py`, `diagnose.py`, `gen_tokyo_times_tts.py`, `gen_voices_kokoro.py`, `generate_summary.py`, `install_service.bat`, `run_avatar.bat`, `run_studio.bat`, `scene_pipeline.py`, `smoke_test.py`, `start_studio.py`, `test_all_languages.py`, `test_edge_tts.py`, `test_langs.py`, `test_routing.py`

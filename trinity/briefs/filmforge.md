# QI FilmForge (filmforge) — L2 brief

_Generated 2026-09-12 02:35:04_

## Registry facts
- Path: `C:\APPS\FilmForge`
- Status: active_development
- Ports: api:7865
- Notes: Built 2026-08-10. Modules A (script generation), B (decomposition) and C (production manager) all working and verified end to end; output accepted by Media Studio compose --dry-run. Module D deliberately NOT built here: av_mux is the assembly authority, and the crossfade() and last_frame() primitives FilmForge needed were contributed upstream to it rather than forked. GPU broker live and cross-project preemption verified with VoiceStudio. Measured: ~80 s/shot on MiniMax H3 warm; an 8 h window is ~20 min of finished film, so a 90 min feature is ~4-5 nights. CORRECTED 2026-08-11 - OLLAMA IS A GPU TENANT. The 2026-08-10 finding (Ollama 0.32.6 reporting library=cpu and 0.00 GB VRAM, not seeing the RTX 5080 sm_120, so all local LLM work across maia/nexus/openclaw/autopdf was CPU-bound) no longer holds: the 0.32.7 update plus a restart restored CUDA (sm_120, 15.9 GiB). Re-measured on GPU: gemma4:latest 136.1 tok/s at 3.29 GB resident and 100% on GPU; gemma4:26b 65.6 tok/s at 12.0 GB, 65% on GPU; gemma4:31b 4.9 tok/s at 10.8 GB, only 49% on GPU because it wants 22 GB at runtime. Resident VRAM is NOT the pull size in either direction. Default moved 31b -> 26b: 31b is now both the largest and the slowest. OllamaTextDriver now takes a broker lease at NORMAL priority (preempts FilmForge's own BATCH overnight render at the next shot boundary) and returns VRAM with keep_alive=0 when another tenant is waiting. extend_video() implemented for MiniMax H3: last-frame continuity chaining via node 7's optional first_frame input, frame extracted by av_mux.last_frame(). | git history lives in C:\APPS\FilmForge (the source tier since the owner's ruling of 2026-09-10) and on GitHub; D:\Dev\FilmForge is a plain backup clone.

## Brain
- Current state: status=active, phase=Completion plan defined 2026-08-27; core scene-split module built
  Long-form film orchestration (story to scenes to overnight GPU render). Per docs/ROADMAP.md (most recent doc, written 2026-08-27), most of the pipeline already exists -- Module B (script/shotlist.py) already outputs shot lists accepted by Media Studio's compose --dry-run.
- No project-scoped decisions recorded.

## CLAUDE.md rules
# QI FilmForge — how Claude works with this project
never edited, never running anything. Registered in
`C:\QIH\ecosystem\qi_registry.json` as `filmforge`, ui **7865**, block
**8750-8759** reserved.
## 🔴 Four rules that define this project
Read it through `filmforge.models.backends`. Never copy defaults into code. A
disabled engine is **refused, never substituted** — `minimax_cloud` is off
because Renne decided not to buy credits, and silently rendering on something
else would spend GPU hours producing the wrong thing.
Note the two namespaces, and don't conflate them:

| | |
Borrowed from Media Studio and not to be re-litigated. Shots are never given a
frame count in a shot list; a shot lasts as long as its line, and `fit`
(`loop`/`freeze`/`slow`) reconciles a 2.4 s clip with a 9 s sentence.
## The GPU broker is ecosystem-wide
holder stops at a safe boundary rather than being killed. Never add a hard kill —
that is what checkpointing exists to avoid.

`C:\APPS\VoiceStudio\engine\gpu_lease.py` is a client. Its public API must not
change; it falls back to local policy when the broker is not importable.

## Resumability is load-bearing
- **A rehydrated `ShotPrompt` must render identically to a fresh one.**
  `asdict()` flattens the str-enums to plain strings, so every accessor goes
  through `_val()`. This was a real bug: night 2 crashed where night 1 worked.
## Testing without a GPU
## Scheduled task
## QI ecosystem compliance
## Related
- `D:\AI\CLAUDE.md` — ComfyUI rules, the render trigger, engine ladder

## Entry points
`RenderNight.bat`

# Claude Voice (claude_voice) — L2 brief

_Generated 2026-09-12 02:35:04_

## Registry facts
- Path: `C:\APPS\CLAUDE\Claude Voice`
- Status: active_development
- Ports: api:8720, line:8721, webcall:8722, voice_api:8725
- Notes: Standalone realtime voice assistant spun out of Gamez on 2026-06-20. The STT+VAD+TTS bridge is a reusable ecosystem feature other QI projects can adopt (e.g. Maia/OpenClaw Koe). Male voice (Andrew EN / Antonio pt-BR); identity is always 'Claude', never 'Andrew'.

## Brain
- Current state: status=blocked, phase=Deliberately powered down 2026-08-20; auto-restore armed for 2026-09-19
  Backfilled 2026-09-09 from QI_Project_Status_Report_2026-09-09.docx (Claude Fable 5.1). 2026-08-20 root-caused why the stack would not stay off (global SessionStart hook re-armed the bridge in every project session). Built the VOICE_DISABLED kill switch, pinned the four QI_ClaudeVoice* services to demand-start, disabled meeting-room/bridge-health tasks, and scheduled QI_ClaudeVoiceRestore_20260919. QI_ClaudeVoiceControl :8720 STOPPED by design; claudevoice.quiddityinnovations.com returns 530 until restore.
- No project-scoped decisions recorded.

## CLAUDE.md rules
# Claude Voice — two-way voice bridge
## 🔴 Hard rule — Claude's voice is MALE
"Claude" is a male name, so Claude always speaks in a **male** voice.
- English default: **`en-US-AndrewNeural`** (warm male) — Renne approved.
- Brazilian Portuguese: **`pt-BR-AntonioNeural`** (male).
- (`pt-BR-FranciscaNeural` is a liked-quality voice but it's female — do NOT use it as Claude's own voice.)
Never default to a female voice for Claude.

### 🔴 Identity rule — the name is "Claude", not "Andrew"
"what is your name / who are you", always answer **"Claude"** — never "Andrew". Andrew = how
Claude *sounds*; Claude = who he *is*.

## What it is
## Run
## How Claude uses it in a session
## Dependencies (installed 2026-06-20)
## ⚠️ Current limitation & the GOAL of this project
**This project's mission: evolve to a real two-way spoken conversation** — hands-free voice activity detection (auto start/stop), auto-sending the transcript, low latency, and barge-in. That likely means a small standalone voice-assistant loop (Whisper → LLM backend → edge-tts) that can run as its own always-listening app.

## QI ecosystem compliance
- **Ports:** Claude Voice owns block **8720–8729**; the realtime control API (Mode B) runs on **8720** (`/health`, `/version`, `/info` + start/stop/config). Do NOT change without updating `qi_registry.json` first (Law 5). Loopback-only, never tunneled.
- **Standards:** follow `C:\QIH\ecosystem\QI_Standards.md` (folders, file naming, UTF-8, secrets in `secrets/`, gitignored) and the Six Laws in `QI_Architecture_Principles.md`.
- **Parallel QI projects (quick reference):** FileHQ 8000 · Maia 8001/7860 · Naya 8002/7861 · NEXUS 8010/7880 · EasyFlow 8550 · Gamez 8710 · **Claude Voice 8720**.
## Architecture — realtime loop (Mode B, signed off 2026-06-20)
- **Listening modes are selectable:** VAD always-listening *or* wake-word gating.
- **Run mode:** on-demand first (`.bat`/hotkey); promote to NSSM service `QI_ClaudeVoice` once stable.
- **Graceful degrade (Law 3):** Ollama down → next enabled backend; edge-tts/network down → SAPI offline; no GPU → CPU Whisper.
## Docs

## Entry points
`ClaudeVoice_Control.bat`, `ClaudeVoice_Install.bat`, `ClaudeVoice_Install_Meeting.bat`, `ClaudeVoice_Run_BridgeHealth.bat`, `ClaudeVoice_Run_ControlPanel.bat`, `ClaudeVoice_Run_Line.bat`, `ClaudeVoice_Run_Meeting.bat`, `ClaudeVoice_Run_Realtime.bat`, `ClaudeVoice_Run_Telegram.bat`, `ClaudeVoice_Run_VoiceAPI.bat`, `ClaudeVoice_Run_Webcall.bat`, `ClaudeVoice_Start.bat`, `ClaudeVoice_Start_MeetingRoom.bat`, `agent_join.py`, `backends.py`, `brain.py`, `bridge_health.py`, `bridge_responder.py`, `build_package.py`, `config.py`, `control_panel.py`, `cvlog.py`, `line_bot.py`, `listen.py`, `make_samples.py`

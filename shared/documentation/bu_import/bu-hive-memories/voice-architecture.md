---
name: voice-architecture
description: "How voice (TTS + mic STT) is wired across ClaudeVoice, BU Hive, and Claude Code."
metadata: 
  node_type: memory
  type: project
  originSessionId: 0d5a4e0e-326a-4468-b865-dadcfb53e18c
  modified: 2026-07-23T19:27:09.174Z
---

Voice is centralized in the **ClaudeVoice** product (`C:\AI\Products\ClaudeVoice`) and reused everywhere via one shared loopback HTTP service — not copied per app.

- **Shared Voice Service:** `voice_service.py` (FastAPI, `127.0.0.1:8735`, launcher `Start-VoiceService.cmd`). Endpoints: `POST /speak`, `POST /transcribe` (browser audio blob → Whisper), `POST /listen` (server mic), `GET /health`. Backed by the existing `speak.py` (edge-tts male "Claude" voice → ffplay) and `listen.py` (faster-whisper CPU). Port added under `config.json` → `server.voice_port`.
- **BU Hive** reaches it via a **same-origin proxy** (satisfies its `default-src 'self'` CSP + reuses login/CSRF): `/api/voice/health|speak|transcribe` in `app/views.py`, forwarding with `httpx`. Browser side: shared helper `static/js/bu-voice.js` (`window.BUVoice`; auto-wires `.bu-mic`/`.bu-speak`, hides `.bu-voice-only` when offline). First use: 🎤 mic button in the Information search. Config: BU Hive `config/config.json` → `voice.service_url`.
- **Claude Code (all projects):** global `Stop` hook in `~/.claude/settings.json` runs ClaudeVoice's `speak_response.py` (direct `speak.py`, no service dependency) so replies are spoken everywhere.
- **Reuse pattern for a new web tool:** add the 3-route same-origin `/api/voice/*` proxy + include `bu-voice.js`.

Gotcha: ClaudeVoice's own project `.claude/settings.json` also has a Stop hook — with the global one now present, working *inside* that project double-speaks unless the project-level one is removed.

Voice INPUT to the Claude Code CLI itself is native (`voiceEnabled`/`voice` hold-to-talk dictation setting), not ClaudeVoice. Governance: [[bu-hive-governance-workflow]] — service is loopback-only; channels stay off pending BU sign-off.

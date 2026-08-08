---
name: project-claude-voice
description: "ClaudeVoice product gives Claude real voice I/O (TTS out, STT in) on this laptop — how to speak"
metadata: 
  node_type: memory
  type: project
  originSessionId: 28368428-30ce-461d-a0a6-2984c5c7a709
  modified: 2026-08-04T19:01:47.077Z
---

Claude has a working **voice** capability on this laptop via the **ClaudeVoice** product at `C:\AI\Products\ClaudeVoice`. Do NOT claim Claude Code is "text-only" — that is wrong here.

**Architecture (file bus):** channel → `claude_bridge/inbox.jsonl` → Claude session → `bus.respond()` → `outbox.jsonl` → channel. Components:
- `speak.py` — `say(text)`: edge-tts → mp3 → ffplay. Voice is **MALE `en-US-AndrewNeural`, named "Claude" (never "Andrew")**.
- `claude_bridge/bridge_listen.py` — Enter → mic → faster-whisper STT → publishes to inbox (`channel='voice'`).
- `claude_bridge/bridge_speak.py` — watches outbox, voices new replies tagged `channel='voice'`.
- Also has Telegram/LINE/Teams/meeting bridges.

**To speak on demand** (works even if the bridge watchers aren't running):
```
cd C:\AI\Products\ClaudeVoice
.\.venv\Scripts\python.exe speak.py "text to say"
```
**Full voice loop (rebuilt 2026-08-04):** `bridge_responder.py` now has a `claude` backend — the real Claude answering headlessly via the **Claude Code CLI** (`claude -p`, installed at `C:\nvm4w\nodejs\claude.cmd`), so the loop no longer needs an attended session watching the inbox. It is the auto-picked default and persists its session id in `data/bridge_claude_session.json` for conversation continuity.

**The failure mode to check first:** `brain_mode='bridge'` BLOCKS in `brain.ask()` waiting for the outbox. If `bridge_responder.py` isn't running, every spoken question dies silently and the mic looks broken. `voice_mic.py --status` reports responder state; the daily 8AM task now starts it.

**Cost is per utterance** — roughly $0.11 for the first turn of a conversation and ~$0.02 for each turn after (cache hit), on `claude-sonnet-5`. A long voice chat is real money; that's why the model is a config knob (`backends.claude_code.model`) and MCP/dynamic-prompt sections are stripped from each call.

Lives under [[project-bu-hive]] ecosystem; follows [[project-documentation-standard]] and [[project-structure-standard]]. See [[user-qi-bu-context]] for IP separation.

# 🧍 QI Bot Embodiment Playbook
### Giving a QI bot a voice, a face, a body, and autonomy — reusable across all bots

**Origin:** built first on **Claude Voice** (`C:\APPS\CLAUDE\Claude Voice`), 2026-06-20. Intended for reuse by
**Maia Quiddam (MQ)** and any future persona bot. Owner: Renne Santiago / Quiddity Innovations.

> Goal (Renne's vision): make a bot feel like a real person — voice, face, full-body avatar,
> and the autonomy to decide *how* to respond (text / voice / video) without manual commands —
> eventually controlled from one **central config panel** for all bots.

---

## 1. The capability stack (each layer is optional + reusable)

| Layer | What | Tech (Claude Voice reference) | Reuse unit |
|---|---|---|---|
| **Identity** | name, persona, rules | `config.json → identity.system_prompt` + owner/guest roles | per-bot config |
| **Voice (out)** | bot speaks (MALE here) | edge-tts neural → ffplay/opus/aac · SAPI offline fallback | `speak.py` / `make_*` |
| **Pronunciation** | say names right | `pronounce.py` + `C:\QIH\shared\voice\pronunciation.json` (Renne→Renee) | **shared** |
| **Ears (in)** | transcribe user speech | faster-whisper (CUDA on RTX 5080, CPU fallback) | `transcribe()` |
| **Face / talking video** | avatar still + voice, OR realistic lip-sync | `media.py`: fast tier (ffmpeg) · HD tier = **Hallo2** in WSL2 | `media.make_avatar_video` |
| **Full body** | full-figure avatar video | AvatarStudio (LivePortrait/Hallo2) — `C:\APPS\AvatarStudio` | AvatarStudio pipeline |
| **Channels** | reach people | Telegram (long-poll) · LINE (webhook + tunnel) | `telegram_bot.py` / `line_bot.py` |
| **Autonomy** | decide text/voice/video per turn | `modality.py` (rules + LLM tag, rate-limited) | **reusable engine** |
| **Control** | owner directives, on/off | owner DM commands + `data/*control*.json` state | per-bot |

## 2. Voice + video pipelines (proven)
- **TTS:** `edge-tts` → mp3; play via `ffplay`; for chat: → **ogg/opus** (Telegram voice note) or **m4a/aac** (LINE). Always run text through `pronounce.apply()` first.
- **STT:** `faster-whisper` (`base` multilingual EN+PT); decode any input via `ffmpeg -ar 16000 -ac 1`.
- **Talking video — fast tier (no GPU):** `ffmpeg -loop 1 -i avatar.png -i voice.mp3 … libx264` → MP4 in seconds. Avatar shown while the bot speaks.
- **Talking video — HD tier (GPU, realistic lip-sync):** Hallo2 in WSL2:
  ```
  cd ~/qi_avatar/hallo2
  ~/miniconda3/envs/hallo/bin/python scripts/inference_long.py \
    --config configs/inference/long.yaml \
    --source_image <face.png> --driving_audio <voice.wav> \
    --pose_weight 1.0 --face_weight 1.0 --lip_weight 1.0 --face_expand_ratio 1.2
  # output: output_long/debug/<stem>/merge_video.mp4 (512x512 talking head)
  ```
  Measured: ~2–4 min per short clip on RTX 5080. **Use a front-facing face image** (side/profile shots lip-sync poorly). Run via a **script file** (CR-stripped) — inline `bash -c` with `~`/vars is unreliable through the Windows→WSL arg layer.

## 3. Autonomy — the modality engine (`modality.py`)
`choose(user_text, reply_text, ctx) -> {voice, video:'none'|'fast'|'hd', reason}`
- **voice:** smart (on short conversational replies; off for long/code/lists).
- **video:** `hybrid` = greetings/first-contact/milestones **or** the LLM's own `[[video]]` tag; rate-limited per chat.
- **tier:** HD for "moment" videos; hybrid can drop very short clips to fast.
- **Latency law:** HD takes minutes → **render async + PUSH** the video; **never block a live turn**. Live turns stay text/voice; HD video is for moments where a short delay is fine. Caller posts an ack ("🎬 one sec…") then pushes the finished clip.

## 4. Near-duplex vs true duplex (how to "talk" to a bot)
- **Near-duplex (today):** `realtime.py` — hands-free VAD → whisper → streaming LLM → per-sentence TTS, with **barge-in**. This is the closest to a real conversation on the desktop right now.
- **Chat apps:** inherently turn-based; approximate duplex with fast STT→LLM→TTS round-trips and short replies.
- **True duplex (roadmap):** a live audio call (WebRTC / SIP) with streaming ASR + streaming TTS + interrupt handling — a separate "voice-call mode" service.

## 5. Central Config Panel (planned — one UI for all bots)
A single dashboard to control every bot's embodiment. Each bot already reads a JSON config, so the panel is a UI over a shared schema:
```
bot:
  identity:  name, persona/system_prompt, owner_id, guest policy
  voice:     engine, voice id (per language), rate, pronunciation map
  video:     avatar image(s), full-body avatar, fast/HD tier, lipsync engine
  automation: auto_voice, auto_video policy + tier, rate limits
  channels:  telegram / line / (FB/IG/WhatsApp for MQ) tokens + webhook
  control:   paused, directive, guests_allowed
```
Build path: (1) standardize this schema across bots; (2) a small FastAPI + web UI that reads/writes each bot's `config.json` + control state; (3) live-reload so changes apply without restart. Registry id TBD (QI Launcher family).

## 6. Replication checklist (to embody a NEW bot, e.g. MQ)
- [ ] Copy `config.json` schema; set identity/persona, owner id, voices.
- [ ] Reuse `C:\QIH\shared\voice\pronounce.py` for name pronunciation.
- [ ] Reuse `media.py` + the Hallo2 command for talking video (drop the bot's face/body image in `avatar/`).
- [ ] Reuse `modality.py` for auto text/voice/video decisions.
- [ ] Wire the bot's channels (Telegram long-poll / LINE webhook+tunnel / Meta webhooks for MQ).
- [ ] Owner control channel (DM commands) + control-state json.
- [ ] Register in `qi_registry.json`; tunnel in `tunnels.json`; NSSM services; log feature to QI Brain.
- [ ] Document in this playbook + the bot's own docs.

## 7. Files (Claude Voice reference implementation)
`speak.py listen.py realtime.py backends.py pronounce.py media.py modality.py telegram_bot.py line_bot.py server.py config.json` + `avatar/` + `Claude_Channels.md`. Secrets in `secrets/claude_voice.env` (gitignored).

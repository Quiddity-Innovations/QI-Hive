# Claude Voice — Talk to the Real Claude, for Free

## What is Claude Voice?

Claude Voice is a voice-driven assistant built by **Quiddity Innovations** that lets the owner **talk to the real Claude instead of typing** — and, increasingly, turn what he says into work the QI Hive goes and does. It is the QI ecosystem's reusable voice layer: speech-to-text in, Claude's answer out, spoken aloud in a warm **male** voice.

The breakthrough is the cost model. Claude Voice reaches the **real Claude for free** by driving the local **Claude Code CLI** (`claude -p`) against the owner's existing subscription — no metered API bill. That same brain is exposed everywhere the owner already is: on the **PC microphone**, over **LINE** and **Telegram**, and in a daily **meeting room** he can drop into from a browser.

## The Problem We Solve

- Typing every prompt is slow; a real conversation is faster and more natural.
- Calling the Claude API per turn costs money — the owner already pays for a subscription.
- A previous "file bridge" needed a human to type each reply by hand (1 of 12 messages ever answered) — it could not run unattended.
- Bots launched inside a chat session died when the session ended, so Claude went silent whenever the owner stepped away.

## Our Approach

Claude Voice is built on three principles:

- **Free real Claude first.** The primary brain is the headless `claude_cli` backend — the genuine Claude, billed to a subscription token (`CLAUDE_CODE_OAUTH_TOKEN`), not the API. Ollama (local) and the Anthropic API are pluggable, toggleable alternatives, off by default.
- **Always-on, not session-bound.** LINE, Telegram and the public tunnel run as `QI_` Windows services 24/7; the meeting room starts every morning via a scheduled task. Nothing depends on a live chat session being open.
- **Honest by design.** A dual-brain router keeps the real Claude ("Claude") strictly separate from the local stand-in ("Ronald"). Ronald is told never to impersonate Claude or invent facts about the owner's projects, meetings, or files — the fix for an early hallucination incident.

## The Identity & Voice Rules

- **Claude's voice is always MALE** — `en-US-AndrewNeural` (English), `pt-BR-AntonioNeural` (Portuguese). Never a female voice for Claude.
- **The name is "Claude", not "Andrew".** Andrew is only how Claude *sounds*; Claude is *who he is*. Asked his name, he answers "Claude".
- English is the only active language for now; Portuguese is wired but deferred.

## Who Uses Claude Voice?

| Role | How they interact |
|---|---|
| **Owner (the owner)** | Full assistant on PC voice, LINE DM, Telegram, and the meeting room; binding owner commands; dual-brain control |
| **Guests** | Friendly social chat only on LINE — no project access, no work tasks; pointed to their own Claude account |
| **Other AI agents** | Join the meeting room over WebSocket and take part when addressed by name |

## How You Talk to It

| Surface | Port / Path | What it does |
|---|---|---|
| **PC realtime loop** | `realtime.py` | Hands-free: mic → VAD → Whisper → brain → edge-tts → speakers, with barge-in |
| **Push-to-talk / TTS** | `listen.py` · `speak.py` | Type-free input to clipboard; Claude speaks any text aloud |
| **LINE** | `:8721` (public tunnel) | Text + voice notes; owner controls; guest guardrails |
| **Telegram** | outbound long-poll | Text + voice notes; both directions transcribed/spoken |
| **Meeting Room** | `:8722` | Zoom-style room Claude hosts; live roster + shared transcript; minutes export |
| **Brain Control UI** | `:8720` (loopback) | Toggle Claude vs Ronald, hard-set lock; `/health`, `/version`, `/info`, `/bridge/health` |

## Current Build Status (June 2026)

Claude Voice is in **active development**. The voice surfaces and the free real-Claude path are live; the Voice Dispatch console and the LiveKit rebuild are the road ahead.

| Area | Status |
|---|---|
| TTS — Claude speaks (edge-tts Andrew, SAPI fallback) | ✅ Live |
| STT — local faster-whisper transcription | ✅ Live |
| Free real-Claude brain (`claude_cli`, headless `claude -p`) | ✅ Live |
| Dual-brain router (Claude vs Ronald) + name toggle + hard-set lock | ✅ Live |
| LINE bridge — text + voice, owner controls, guest guardrails | ✅ Live (24/7 service) |
| Telegram bridge — text + voice, both directions | ✅ Live (24/7 service) |
| Public LINE tunnel (`claudevoice.quiddityinnovations.com`) | ✅ Live (service) |
| Brain Control API + config UI (`:8720`) | ✅ Live (service) |
| Hourly bridge health monitor (`QI_ClaudeVoiceBridgeCheck`) | ✅ Live |
| Realtime PC voice loop (VAD / wake / PTT, streaming, barge-in) | ⚠️ Built — ~20s/turn on free CLI; barge-in off by default |
| Meeting Room (`:8722`) — multi-participant, Claude-hosted | ⚠️ Built — daily 08:00 task; loopback-only |
| Talking-avatar video (`/video`) | ⚠️ Built — still avatar + voice; HD lip-sync opt-in, auto-video off |
| Local fallback to Ronald | ⚠️ Disabled by config (`fallback_to_local: false`) |
| Voice Dispatch → QI Hive (`POST :9011/api/dispatch`) | 🗓️ Planned — needs net-new executor + notifier |
| LiveKit spine (natural low-latency voice) | 🗓️ Planned — Phase 1 |
| Zoom-like UI (screen share, docs, whiteboard) | 🗓️ Planned — Phase 2 (LiveKit `meet` → plugNmeet) |

## The Vision — a Voice Dispatch Console

The destination is not a chatbot but a **voice dispatch console**: the owner speaks an instruction, the system classifies it as conversation or a work order, files it as a **QI Hive dispatch**, executes it with `claude -p` + the Hive's seven agents (free via subscription), and reports back by voice. The natural-conversation and Zoom-like surfaces are rebuilt on **LiveKit** — one Claude agent that hears, speaks, and eventually sees a shared screen, behind one config panel.

---
*This page is editable at C:\CLAUDE\Claude Voice\INTRO\status_intro.md — save and click Refresh to update.*

# OpenClaw — Where Maia talks, OpenClaw acts

## What is OpenClaw?

OpenClaw is **Quiddity Innovations' autonomous AI agent platform** — the layer that *does things* in the real world on the owner's behalf. Where Maia answers questions, OpenClaw takes action: it reads the inbox, fetches the news, watches the system's health, tracks the bills, and speaks back in voice.

It is built on the **OpenClaw npm gateway** (a self-hosted agent runtime) running inside **WSL Ubuntu-24.04**. A single orchestrator agent — **Hattori Tasuke** — receives every message over Telegram (and LINE), then delegates to a family of specialist agents. The owner talks only to Tasuke; Tasuke routes the rest.

The crucial architectural fact: **new capabilities are wired by editing a Markdown file, not by writing a bot.** The gateway's LLM reads `~/.openclaw/workspace/TOOLS.md` on every turn — a 1,200-line playbook of permission tiers and natural-language "conversation flows" mapped to shell commands. Add a section to TOOLS.md, restart the gateway, and the agent immediately knows a new trick.

## The Problem We Solve

- An AI that only *talks* still leaves all the doing to you — checking mail, scanning news, paying attention to system health.
- Wiring real-world actions into a chatbot normally means custom webhooks, bot frameworks, and brittle glue code.
- Cloud agent platforms are expensive, send your data off-machine, and lock you in.
- A household runs on small recurring chores — bills, briefings, triage — that no single app owns.

## Our Approach

OpenClaw is a **single orchestrator + specialist agents** design, run locally and cheaply:

- **One front door.** the owner messages Tasuke; Tasuke decides whether to answer, delegate, or refuse.
- **Capabilities as text.** TOOLS.md is the contract — a permission firewall (TALK / DO / PRIVATE) plus flows. No redeploy to teach a new skill.
- **Local-first, free-tier LLMs.** Local Ollama (`gemma4:26b`, `gpt-oss-20b`) is primary; Kaze's digests use Cloudflare Workers AI free tier with automatic Ollama fallback. Voice transcription runs locally on whisper.cpp.
- **Everything is a script.** Each agent is a handful of small, auditable Python/bash scripts under `repo/scripts/<agent>/`, scheduled by Windows Task Scheduler and WSL cron.

## Who Uses OpenClaw?

| Role | How they interact |
|---|---|
| **the owner (owner)** | Talks to Tasuke over Telegram/LINE — full TALK + DO authority; receives briefings, digests, alerts, and voice replies |
| **Group members** | Can trigger TALK-only actions (news briefing, translation, voice) in allowed group chats; DO and PRIVATE actions are refused |
| **Sibling bots** | Maia / Naya / Kaze bots are recognised peers via the bridge layer + loop guard — they converse, but never trigger DO actions |
| **QI Hive / Maia** | Future: Maia routes complex *action* tasks to OpenClaw; Asa already pulls QI Hive Brain health into the morning briefing |

## Current Build Status (June 2026)

OpenClaw is in **active production** — the gateway is live (`OpenClaw 2026.4.26`) on TCP `18789`, supervised by systemd inside WSL, with most agents operational.

| Area | Status |
|---|---|
| OpenClaw gateway (WSL, systemd, token auth, LAN bind) | ✅ Live |
| Tasuke orchestrator (TOOLS.md flows, TALK/DO/PRIVATE firewall) | ✅ Live |
| Kaze — news & AI digests (Telegram + NotebookLM, 6AM/6PM) | ✅ Live |
| Yubin — email triage (Gmail IMAP, 8AM/6PM) | ✅ Live |
| Asa — morning briefing (7AM, multi-source aggregation) | ✅ Live |
| Kakei — household finance ledger (SQLite, weekly Sunday rollup) | ✅ Live |
| Koe — voice STT/TTS (whisper.cpp + edge-tts default) | ✅ Live |
| Sentry — system/security health monitor (deterministic, no LLM) | ✅ Live |
| Channels — Telegram + LINE | ✅ Live |
| LLM stack — local Ollama primary, Cloudflare free-tier for Kaze | ✅ Live |
| NotebookLM knowledge-base client (cookie-auth, vision UI automation) | ✅ Live |
| Hive bridge — query QI Brain from Tasuke (:9011) | ✅ Live |
| Peer bridge — cross-bot messaging (HMAC, loop guard) | ⚠️ Built — receiver running, candidate for Maia⇄OC |
| Broadcast — proactive multi-group push | ⚠️ Built — tasks disabled until proactive push is wanted |
| Koe dots.tts — local GPU voice cloning | ⚠️ Built — parked disabled (EN/ZH only; PT/JA route to edge) |
| Seiri — file organisation | ❌ Decommissioned — replaced by Naya |
| Maia ⇄ OpenClaw action routing | 🗓️ Planned — marriage candidate |

## The Six Agents (plus the two that joined later)

OpenClaw started with six named agents. Seiri was cancelled and absorbed by Naya; two new specialists (Asa, Kakei) were added in the 2026-05-13 Phase 2 session. All specialists are subordinate to Tasuke.

- **Hattori Tasuke (服部 助) — The Loyal Guard.** ✅ Live. The orchestrator and the only agent the owner talks to directly. Enforces the TALK/DO/PRIVATE permission firewall, matches messages to TOOLS.md flows, and delegates to specialists. Telegram: `@HattoriTasukeBot`.
- **Kaze (風) — News & Digest.** ✅ Live. Twice-daily news and AI/ML digests to Telegram, archived to NotebookLM. RSS aggregation with clustering and source-credibility policy; LLM via the Cloudflare→Ollama router.
- **Yubin (郵便) — Email Intelligence.** ✅ Live. Gmail IMAP triage for `maia.quiddam@gmail.com` under strict containment (never authorises subscriptions, contracts, or purchases). Escalates uncertain mail to the owner; feeds bill-class emails to Kakei.
- **Asa (朝) — Morning Briefing.** ✅ Live. One 7AM Telegram message combining news, inbox counts, system health, QI Hive health, calendar, and bills due — each section degrades gracefully. Read-only.
- **Kakei (家計) — Household Finance.** ✅ Live. SQLite ledger of bills and expenses, fed by Yubin (email) and a receipt-photo OCR skill (`qwen3-vl`). Weekly Sunday rollup; never pays anything.
- **Koe (声) — Voice.** ✅ Live. Speech-to-text via whisper.cpp; text-to-speech via edge-tts (Microsoft neural, default) with a Piper offline fallback and a parked dots.tts GPU clone. Female persona, language-matched. A pure media converter — decides nothing.
- **Sentry — Health & Security Monitor.** ✅ Live. Deterministic bash health checks (gateway, Ollama, disk, memory, config integrity, NotebookLM auth) — no LLM by design. Daily 6AM + weekly drift check.
- **Seiri (整理) — File Organisation.** ❌ Cancelled 2026-04-05. Fully replaced by Naya (which absorbed FileHQ). Retained only as historical dashboard panels.

## The Vision

One orchestrator, many hands. OpenClaw is the **autonomous-action layer of the QI ecosystem** — the natural partner to Maia's conversation. The roadmap marries the two: Maia handles the dialogue, recognises an actionable request, and hands it to OpenClaw to execute. Add a new specialist by writing a profile and a TOOLS.md section; the platform grows by text, not by rebuilds.

---
*This page is editable at `C:\OC\INTRO\status_intro.md` — save and click Refresh to update.*

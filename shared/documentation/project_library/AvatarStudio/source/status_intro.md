# QI Avatar Studio — Talking-Head Avatar Video Pipeline

## What is Avatar Studio?

QI Avatar Studio is a local, Gradio-based studio built by **Quiddity Innovations** that turns a
written script into a **talking-head avatar video**. You pick an agent (or upload any portrait),
type a script, choose a language and a render engine, and the studio walks the pipeline end to end:

**script → text-to-speech → optional background replacement → face/lip animation → MP4 out.**

It runs entirely on the local machine at `http://localhost:7862`. Voice is generated locally
(Kokoro) or via Microsoft Edge Neural voices; the heavy face-animation models (LivePortrait,
Hallo2, video-retalking) run inside **WSL2 Ubuntu-24.04** and are driven over subprocess calls
from the Windows Gradio app.

## The Problem We Solve

- QI agents (Tasuke, Maia, Naya, Kaze) have personalities and portraits but no **face and voice**.
- Producing a talking-head clip normally means a paid SaaS (HeyGen, D-ID) or a brittle hand-run
  notebook with CUDA, dlib, and ffmpeg landmines.
- Multi-language narration usually means re-recording — here one script, ten languages, one click.
- Renders need to stay **free and offline-first** during the proof-of-concept phase.

## Our Approach

A single pipeline orchestrator with **swappable render engines**. The same script + voice flows
into whichever engine is selected — local (LivePortrait, Hallo2), post-process lip-fix
(video-retalking), or cloud (HeyGen, D-ID) — so the studio can trade speed for quality without a
rewrite. TTS routes per-language to the best available engine (local Kokoro where a voice exists,
Edge TTS where it does not). Everything heavy lives in WSL2; the Windows app only orchestrates,
assembles audio with ffmpeg, and shows progress live.

## Who Uses Avatar Studio?

| Role | How they interact |
|---|---|
| **QI operators** | Pick an agent, type a script, choose language + engine, click Generate; watch step-by-step progress and download the MP4 |
| **Content creators** | Upload any portrait, replace the background, tune render parameters, render the same script in multiple languages |
| **Pipeline / CLI users** | Run `avatar_pipeline.py <agent> "text"` headless for Kokoro → Hallo2 → MP4 |
| **Multi-scene authors** | Use the Scene pipeline to split a long script into per-character scenes and concatenate one movie |

## Current Build Status (June 2026)

Avatar Studio is in **active proof-of-concept** phase. The Gradio app, TTS, and the
LivePortrait/Hallo2 render path are working; lip-sync quality is the known open issue.

| Area | Status |
|---|---|
| Gradio studio UI on :7862 (agent picker, scripts, engine config) | ✅ Live |
| TTS — Kokoro (local, 6 languages) + Edge TTS (4 languages) | ✅ Live |
| 10-language routing with per-language voice catalog | ✅ Live |
| LivePortrait render (driving-video motion transfer, WSL2) | ✅ Live |
| Hallo2 render (audio-driven talking head, WSL2) | ✅ Built — slow (~15–30 min/min) |
| video-retalking lip-sync post-process (WSL2) | ✅ Built — opt-in checkbox |
| ffmpeg audio mux / video assembly (WSL2) | ✅ Live |
| Background replacement (rembg: solid color / image) | ✅ Live |
| Multi-language batch render (one click, N languages) | ✅ Live |
| Per-agent roster + custom portrait upload | ✅ Live |
| Best-portrait-frame finder (OpenCV) + frame/screen capture | ✅ Live |
| Scene pipeline (split → per-character → concat movie) | ⚠️ Built — AI split depends on NEXUS |
| D-ID cloud render | ⚠️ Built — enabled flag set, needs API key |
| HeyGen cloud render | ⚠️ Built — disabled, needs API key |
| MuseTalk / SadTalker / Wav2Lip engines | ⚠️ Built — disabled, need WSL2 install |
| QI_AvatarStudio NSSM service | ⚠️ Installer exists — demand-start, not in service registry |
| Audio-driven avatar generated from a text description (Phase 2) | 🗓️ Planned — UI placeholder only |
| Wire avatar outputs to QI Hive dashboard (:8600) | 🗓️ Planned |
| QI Brain / ecosystem integration | 🗓️ Planned — no integrations wired |

## The Vision

Every QI agent gets a face and a voice. One portrait, one personality, one script — rendered as a
talking avatar in any of ten languages, from the same studio, at zero marginal cost during the POC.
Cloud engines (HeyGen, D-ID) are there for when production polish beats free-and-local. The studio
is the showcase; the swappable-engine pipeline is the reusable asset.

## Engine Strategy

The render layer is deliberately pluggable, selected at run time:

- **LivePortrait** — fast (~30s), motion transferred from a curated driving video; lips are **not**
  audio-driven, so it pairs with the retalking checkbox for sync.
- **Hallo2** — fully audio-driven (lips match the waveform), production quality, but slow.
- **video-retalking** — a post-process pass that fixes lip sync on top of any render.
- **Cloud (HeyGen, D-ID)** — upload portrait + audio, poll, download; for when local isn't enough.
- **MuseTalk / SadTalker / Wav2Lip** — pre-wired alternates, off until their WSL2 envs are installed.

## Global by Design

AI and media are global. The studio narrates in **ten languages** out of the box:

- **Local & offline (Kokoro-82M, Apache 2.0)** — American & British English, Brazilian Portuguese,
  Spanish, Italian, Mandarin Chinese.
- **Microsoft Edge Neural (free, internet)** — Japanese, French, Russian, German (where Kokoro-82M
  lacks a usable voice — e.g. no male French voice, broken Windows pyopenjtalk for Japanese).
- A full **voice catalog** (Women / Men / Girls / Boys) lets you override the default voice per
  language, and pitch/speed are adjustable per render.

---
*This page is editable at `C:\1-AI\APPS\AvatarStudio\INTRO\status_intro.md` — save and click Refresh to update.*

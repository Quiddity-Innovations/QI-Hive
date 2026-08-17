# M2V — Music to Video

## What is M2V?

M2V (**Music to Video**) is an AI-powered tool by **Quiddity Innovations** that turns a song into a
finished music video. You give it an **audio track** and the **lyrics**; M2V breaks the song into
scenes, generates a visual for each one, animates them, stitches everything to the beat, burns in the
lyrics as subtitles, and hands back a single synced MP4.

It is an **early-stage** project — registered in the QI ecosystem with status **new**. The scaffold is
built and the full local-AI pipeline is wired end to end, but it has only been exercised on a handful of
test runs. Most capabilities below are honestly marked *Built / Partial* or *Planned* rather than *Live*.

## The Problem We Solve

- Making a music video is slow, expensive, and needs editing and motion-graphics skills most people don't have.
- Cloud video-generation services are costly per render and send your unreleased music to a third party.
- Independent artists want a **private, free, local** way to give a track a watchable visual — fast.

## Our Approach

M2V runs the whole pipeline **locally on the owner's GPU** (an RTX 5080, 16 GB). Nothing about the song
leaves the machine. The chain is:

1. **Lyrics in** — pasted directly, or extracted from the audio (embedded ID3 tags first, then Whisper transcription).
2. **Direction** — a local Ollama model (`qwen3:8b`) reads the lyrics and writes a vivid visual scene prompt per section.
3. **Stills** — Stable Diffusion XL renders one image per scene; an optional reference photo + IP-Adapter keeps the same faces across every scene.
4. **Motion** — Stable Video Diffusion animates each still into real motion video.
5. **Assembly** — FFmpeg concatenates the clips, lays the original song over the top, and burns in the lyric subtitles.

It is a sibling of two other QI creative tools: **PersonalSong** (which *generates* the audio) and
**AvatarStudio** (video/avatars) — M2V is the bridge that turns audio into video.

## Two Tracks of Code Today

M2V currently holds **two parallel implementations**, which is normal for a project this young:

| Track | What it is | State |
|---|---|---|
| **Service pipeline** (`engine/`, `api/`, `ui/`) | The product: FastAPI job server + Gradio UI driving the SDXL → SVD → FFmpeg chain | Scaffold complete; service launches; lightly run |
| **Standalone proof-of-concept** (`make_forro_video.py`, `generate_frames.py`, `scenes.json`) | A hand-authored 10-scene anime video ("Churrasco na Geórgia") built with MoviePy + an external ComfyUI | Produced a real 160s MP4 (with placeholder frames) |

The standalone track proved the *assembly* idea works; the service pipeline is the path forward.

## Who Uses M2V?

| Role | How they interact |
|---|---|
| **Musician / creator** | Uploads a track + lyrics, picks a visual style, optionally a reference photo, clicks Generate |
| **Operator (the owner)** | Runs the local service, manages the GPU model cache, monitors render jobs |
| **QI ecosystem** | Other QI projects can call the `/health`, `/version`, `/info` contract endpoints |

## Current Build Status (June 2026)

M2V is in **early scaffold** phase. The skeleton runs; the heavy generative stages have had limited real use.

| Area | Status |
|---|---|
| FastAPI service + 3 QI contract endpoints (`/health`, `/version`, `/info`) | ✅ Live — service launches, `/health` OK in logs |
| Gradio operator UI (`:7841`) | ✅ Live — launches and serves |
| Job model (submit → poll events → download MP4) | ✅ Built — in-memory job store |
| Lyric → scene analysis (Ollama `qwen3:8b` + fallback) | ⚠️ Built — local-LLM dependent, light testing |
| Lyrics extraction (ID3 tags + Whisper) | ⚠️ Built — not yet broadly verified |
| Audio segmentation (librosa + even-split fallback) | ⚠️ Built |
| Image generation (SDXL Base 1.0 + IP-Adapter) | ⚠️ Partial — code complete, needs GPU model weights |
| Video generation (Stable Video Diffusion) | ⚠️ Partial — code complete, VRAM-tight, lightly run |
| Assembly (FFmpeg concat + audio mux + burned subtitles) | ⚠️ Built — produced real MP4s with SRT output |
| Standalone anime MV proof-of-concept | ✅ Done — `forro_anime_mv.mp4` rendered (placeholder frames) |
| QI_M2V Windows service + named Cloudflare tunnel | ⚠️ Built — installers present, not yet in service registry |
| Persistent job store / database | 🗓️ Planned — jobs are in-memory only today |
| QI Brain / ecosystem integration | 🗓️ Planned — no `integrates_with` wired |
| Documentation set (README, guides) | 🗓️ Planned — doc folders are empty stubs |

## Ports & Home

- **Path:** `C:\APPS\M2V`
- **API port:** 8501 (block 8500–8599)
- **UI port:** 7841 (block 7840–7849)
- **Family tier:** cousin
- **Public URL (planned):** `https://m2v.quiddityinnovations.com` (static named tunnel `qi-m2v`)

## The Vision

A private, local, zero-cost music-video studio: drop in a song, get back a watchable video in minutes —
no cloud, no per-render bill, no leaked masters. Eventually wired to **PersonalSong** so a track generated
there flows straight into M2V for its visual.

---
*This page is editable at `C:\APPS\M2V\INTRO\status_intro.md` — save and click Refresh to update.*

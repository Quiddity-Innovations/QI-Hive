# PersonalSong Studio — Local AI Song Generator

## What is PersonalSong Studio?

PersonalSong Studio is a private, **100% local and free** web app by **Quiddity Innovations** for creating
personalized AI-generated songs — *with real sung vocals* — for family and friends.

You fill in a warm step-by-step form (recipient, story, memories, music style, language). A local LLM writes
fully personalized lyrics. The **ACE-Step** singing model then performs a complete song — verse, chorus, bridge —
in which the recipient's name is *actually sung*. Optionally, the song can be re-voiced in a chosen artist's
timbre (voice clone) and prefixed with a spoken radio- or concert-style dedication. Finished songs are saved as
local audio files, organized for Plex + Google Home / Alexa voice playback, and can be auto-uploaded to YouTube Music.

Everything runs on the machine's local GPU. No paid APIs, no cloud accounts, no data leaving the machine.

## The Problem We Solve

- A heartfelt, personalized song is a rare gift — but commissioning one is expensive and slow.
- Cloud song generators (Suno and similar) cost money, cap free usage, and send your private memories to their servers.
- Generic music models produce instrumentals or English-only vocals; they rarely sing a *specific name* correctly,
  and almost never in the recipient's native language with a native accent.
- Making the song playable around the home (Plex, Google Home, Alexa) is fiddly and undocumented.

## Our Approach

PersonalSong is a **local-first creative pipeline**, not a thin wrapper around a paid API. Every heavy model runs
on-device: Ollama for lyrics, ACE-Step for sung vocals, Demucs for stem separation, Seed-VC for voice cloning,
Whisper for transcription, and SDXL-Turbo for optional cover art. The design favors the gift-giver: native-language
singing across 8 languages, a per-language phonetic respelling system so names are pronounced correctly when sung,
curated singer presets, and a "based on an existing song" mode steered by simple change levers.

It is deliberately resilient — optional steps (Plex sync, YouTube Music upload, dedication, cover art) never fail
the song. The core stays free and offline; the only outbound calls are optional (YouTube Music, Plex, yt-dlp source fetch).

## Who Uses PersonalSong?

| Role | How they interact |
|---|---|
| **Gift-giver (owner)** | Fills the creation form, picks genre / mood / language / singer, generates lyrics + song, adds a dedication, saves to the library — all from the web UI on `localhost:8088` |
| **Recipient** | Receives the finished song — a playable web page, a downloadable MP3 bundle (audio + lyrics + cover), a printable QR greeting card, or a track that plays on Plex / Google Home / Alexa |
| **Power user** | Clones a real artist's voice from a YouTube link / upload / CD, runs album-style batch jobs, queues overnight generations, manages a pronunciation + voice library |
| **QI ecosystem** | Exposes song generation + voice cloning as a cousin project; intended to feed the M2V music-video project *(integration planned)* |

## Current Build Status (June 2026)

PersonalSong is in **active development**. The full local pipeline is built and runs as a Windows service:

| Area | Status |
|---|---|
| Web app + REST API (FastAPI, 12 routers, port 8088) | ✅ Live |
| Lyric generation (Ollama, local, `think:false` + name-injection) | ✅ Live |
| Sung-vocal generation (ACE-Step, GPU, bf16) | ✅ Live |
| Multi-language singing (8 languages + blend mode) | ✅ Live |
| Curated singer presets (10 native-language voices) | ✅ Live |
| Phonetic respelling / pronunciation dictionary (per-language) | ✅ Live |
| Spoken dedication (edge-tts, radio + concert styles, 8 languages) | ✅ Live |
| Voice clone — dedication in artist's timbre (Demucs → Seed-VC) | ✅ Live |
| Full voice-clone cover (ACE-Step → Demucs → Seed-VC → mix) | ✅ Live |
| "Based on a song" audio2audio (3 change levers) | ✅ Live |
| Source ingestion (upload / YouTube / local / CD rip) | ✅ Live |
| Cover art (procedural PIL always; SDXL-Turbo AI optional) | ✅ Live |
| Library, streaming, download, share bundle, karaoke stems, QR card | ✅ Live |
| Batch / album mode + overnight generation queue | ✅ Live |
| Plex sync (ID3 tag + copy + scan) | ⚠️ Built — needs Plex token configured |
| YouTube Music upload (browser-header auth) | ⚠️ Built — needs one-time header auth |
| QI_PersonalSong NSSM service (`serve.py`, in-process uvicorn) | ✅ Live |
| Multi-user / internet exposure (currently loopback-only) | 🗓️ Planned |
| M2V integration (song → music video) | 🗓️ Planned |

## Why ACE-Step (not MusicGen)

The project began on HuggingFace MusicGen, which only produced ~30 s **instrumental** tracks — it could not sing the
recipient's name, defeating the entire purpose. The pipeline was rebuilt around **ACE-Step**, a local diffusion
singing model that performs full songs with sung vocals from lyrics + style tags, on the local GPU at zero cost.
The README still references the original MusicGen / Suno approach; the live engine is ACE-Step (`ace_engine.py`).

## Global by Design

Personal songs are emotional and cultural. PersonalSong sings in **English, Portuguese, Japanese, French, Spanish,
Italian, German, and Korean**, with native-accent conditioning so non-English lyrics aren't sung with an English
accent. Genre tags include culturally specific styles (Brazilian samba / forró / bossa nova, Japanese enka and
decade-specific J-pop, French chanson). Spoken dedications carry native wording per language and per tone —
Portuguese sounds Portuguese, not an English line read by a Brazilian voice.

## Privacy

- The creative core is fully offline — lyrics, vocals, voice cloning, and cover art all run on-device.
- The only outbound calls are optional: YouTube Music upload, Plex sync, and yt-dlp source fetching from a URL you provide.
- No accounts, no analytics, no telemetry. Songs, lyrics, and metadata live in `music_library/` on local disk.
- The service is registered as **loopback-only / not internet-exposed**.

---
*This page is editable at `C:\APPS\PersonalSong\INTRO\status_intro.md` — save and click Refresh to update.*

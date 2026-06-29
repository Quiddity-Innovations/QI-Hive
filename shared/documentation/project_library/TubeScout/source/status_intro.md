# TubeScout — Watch only what's worth it

## What is TubeScout?

TubeScout is a **YouTube subscription intelligence tool** built by **Quiddity Innovations**.
You subscribe to dozens — or hundreds — of channels and then never have time to watch them.
TubeScout reads *your own* subscription list, sweeps every channel's new uploads twice a day,
pulls the transcript, and turns each video into a one-line headline plus a 2–4 sentence news
brief — locally, via NEXUS — so you can skim what happened across all your channels in minutes
and only open the videos that are genuinely worth your time.

It is served as a clean, public **news page** (port 8503): topic-filtered cards, a Favorites
view, a private Discover recommender, and the daily Kaze AI Digest — all themed in NEXUS's
tangerine palette because TubeScout *pairs with* NEXUS.

## The Problem We Solve

- You're subscribed to far more channels than you can keep up with.
- The YouTube home feed is an engagement machine, not an information tool — it buries the
  channels you chose behind whatever it wants you to watch.
- Reading a transcript is 5× faster than watching, but YouTube gives you no way to do it at scale.
- The same story gets covered by ten channels at once — you don't need to see it ten times.
- For a builder, most "AI news" videos contain nothing to actually implement; a few contain a lot.

## Our Approach

TubeScout is **subscription-first and privacy-first**. It uses YouTube's official Data API v3
with *read-only* OAuth to read your own subscriptions — nothing is posted, nothing is changed on
YouTube. Uploads are read from each channel's uploads playlist (1 quota unit) rather than search
(100 units), so two daily sweeps of 800+ channels stay far inside the free 10,000-unit/day tier.

Summarization runs through **NEXUS** (the QI multi-AI backbone), which means the heavy lifting is
done by free/local models — per-video cost is effectively zero. Every stage degrades gracefully:
no captions → fall back to the description; NEXUS down → fall back to a trimmed description;
YouTube rate-limits the caption scraper → back off for hours, the page keeps serving. Nothing in
the pipeline can take the news page down.

## Who Uses TubeScout?

| Role | How they interact |
|---|---|
| **Renne (owner)** | Reads the news page, stars channels, mutes noise, tunes the pipeline and interests in Settings |
| **Public visitors** | Read the public news page + Kaze AI Digest at the TubeScout tunnel — no login, read-only |
| **NEXUS Scout / Kaze** | Receives a curated OPML of AI/tech channels from TubeScout; folds YouTube items into Kaze's daily digest |
| **QI Brain** | Receives implement-worthy videos (score ≥ threshold) as pending-feature candidates for the ecosystem |

## Current Build Status (June 2026)

TubeScout is in **active development**. The full P1→P4 pipeline is built and running; the news
page is live behind a permanent Cloudflare tunnel.

| Area | Status |
|---|---|
| Subscription sync (YouTube Data API v3, read-only OAuth) | ✅ Live — 816 channels |
| Twice-daily upload sweep (07:00 / 19:00 scheduled tasks) | ✅ Live — 4,014 videos discovered |
| Channel auto-organization into topics | ✅ Live — keyword + YouTube topicCategories |
| Transcript fetch (captions-only, IP-block backoff) | ✅ Live — 151 fetched |
| NEXUS news-card summaries (headline + brief) | ✅ Live — 4,014 summarized (2,374 via NEXUS) |
| Public news page + Favorites + topic filter | ✅ Live — port 8503, tangerine theme |
| Cross-channel story dedup ("+N also covered") | ✅ Live — Jaccard over headlines |
| Implement-worthiness scoring → QI Brain | ✅ Live — 439 scored |
| Kaze feed (curated OPML → NEXUS Scout) | ✅ Live — AI/tech topics only |
| Daily Kaze AI Digest (served via TubeScout) | ✅ Live — embedded from the OpenClaw dashboard |
| Discover — private channel recommender | ⚠️ Built — local-taste profile + NEXUS reasoning |
| NSSM service + permanent tunnel | ✅ Live — QI_TubeScout + QI_TubeScoutTunnel |
| Whisper transcript fallback (caption-less videos) | ⚠️ Built — opt-in, off by default |
| QI Brain session/decision logging | 🗓️ Planned — only feature-logging wired today |
| Write-API authentication token | ⚠️ Built — open in local mode, token-gated when set |

## The Daily Sweep Pipeline

Every sweep (07:00 and 19:00, run by Task Scheduler as `QI_TubeScout_AM` / `_PM`) drains a
five-stage pipeline. Each stage is wrapped so one failure never aborts the rest:

1. **Sweep** — read each active channel's uploads playlist; insert uploads from the last 14h
   (the windows overlap so nothing is missed). Dead/terminated playlists are retired automatically.
2. **Reclassify** — assign each channel a topic using its keyword profile *and* YouTube's own
   `topicCategories`, picking the most specific bucket (this cut the "other" pile from 450 to ~1).
3. **Transcripts** — fetch captions newest-first, favorites/must-reads first, throttled with a
   randomized delay; if YouTube IP-blocks the scraper, set a multi-hour cooldown and stop.
4. **Summarize** — send transcript (or description) to NEXUS `/synthesize` and store a
   `HEADLINE` + 2–4 sentence news card. Falls back to the description if NEXUS is unavailable.
5. **Dedup** — collapse the same story across channels by headline token overlap inside a time
   window, marking the canonical card "+N also covered".
6. **Score** — for AI/dev videos, ask NEXUS to rate 0–10 how worth-*implementing* the content is;
   anything ≥ the threshold is logged to QI Brain. Then refresh the curated OPML into NEXUS Scout.

## NEXUS + Kaze + Brain Integration

TubeScout is a **cousin** in the QI family and a deliberate consumer of NEXUS:

- **NEXUS `/synthesize`** does every news-card summary and every implement-worthiness score,
  pinned to a fast provider chain (Groq → Cloudflare → Gemini). No LLM runs inside TubeScout.
- **NEXUS Scout → Kaze** receives a *curated* OPML — only the AI/tech topics, not all 816 subs —
  so Kaze's existing daily digest picks up YouTube items without being flooded.
- **QI Brain `/api/log_feature`** receives implement-worthy videos as pending-feature candidates,
  so a technique demoed on YouTube becomes something the whole ecosystem can decide to adopt.
- The **Kaze AI Digest** (by Maia Quiddam) is regenerated daily at the OpenClaw dashboard;
  TubeScout reads that HTML live and re-serves it through its own tunnel, so it's viewable
  anywhere even when Kaze's own tunnel is down.

## Privacy by Design

TubeScout never feeds your taste into YouTube's recommendation or ad profile. The Discover
recommender builds your taste profile **on this machine** — from channels you favorite and value,
never your watch history — and reasons over it with a NEXUS provider (switchable to a fully-local
gemma model). YouTube is touched only for a neutral name→channel lookup. "Follow privately" ingests
a channel into TubeScout *without* subscribing on YouTube.

## The Vision

One subscription list, distilled to a daily intelligence brief. The framework generalizes: any
source of "too much to watch/read" — YouTube, podcasts, newsletters — can be swept, transcribed,
summarized via the shared NEXUS backbone, and surfaced as a clean, deduped, topic-filtered page
that feeds the wider QI ecosystem.

---
*This page is editable at `C:\TUBESCOUT\INTRO\status_intro.md` — save and click Refresh to update.*

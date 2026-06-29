# AkiyaScout — English-First Japanese Real Estate Scout

## What is AkiyaScout?

AkiyaScout is a personal, English-first discovery platform for Japanese real estate, built by **Quiddity Innovations**. It targets the kind of property foreign buyers actually want and struggle to find: **akiya** (vacant houses), traditional **kominka/minka** farmhouses, and cheap rural homes — the listings that live almost entirely behind Japanese-only portals and fragmented municipal "akiya bank" sites.

Instead of forcing you to re-run a search every day, AkiyaScout flips the model: you describe what you want once as a **Profile** ("cheap rural akiya under $30k in Chubu for a DIY renovation"), and a background **Scout Engine** scrapes Japanese portals, translates each listing into English, and continuously cross-checks fresh inventory against your saved criteria — delivering matches to a dashboard and, optionally, by email digest.

## The Problem We Solve

- The best akiya and kominka are listed only in Japanese, across SUUMO, at-home, LIFULL HOME'S, and 1,000+ municipal akiya-bank pages — invisible to non-Japanese buyers.
- Generic listing sites bury rural/vacant homes under urban apartments and have no English layer.
- Buyers re-run the same manual searches over and over because nothing watches the market for them.
- Key buying signals — seismic code era (pre/post-1981), build era (Showa/Heisei/Reiwa), renovation cost, hazard exposure — are scattered, in Japanese, or absent entirely.

## Our Approach

AkiyaScout is a **vertical scout**, not a generic scraper. It keeps every listing **bilingual** — the original Japanese is never discarded, the English is layered on top — so you can read it in English but still hand the Japanese address and listing to a local agent. It is **region-driven**: all 47 prefectures live in a reference table, so expanding coverage is a data change, not a code change. And it is **free-first and polite**: translation falls back DeepL → local Ollama → an offline glossary, and the crawler is rate-limited with a courteous User-Agent.

The whole pipeline is single-user and LOCAL-only by design (family-tier "cousin" in the QI ecosystem) — a personal research tool, not a commercial site.

## Who Uses AkiyaScout?

| Role | How they interact |
|---|---|
| **The buyer (single user)** | Builds Profiles, browses the English dashboard, filters listings, and reviews matches |
| **The Scout Engine** | Runs in the background — scrapes, normalizes, translates, dedupes, matches, and notifies on a schedule |
| **Map explorer** | Browses an interactive choropleth of Japan with per-prefecture listing counts, clustered price pins, and hazard overlays |
| **Agent hand-off** | Japanese title/address/source URL are kept verbatim so a listing can be taken straight to a local broker |

## Current Build Status (June 2026)

AkiyaScout is in **active development** — a v1 proof-of-concept that has already ingested real inventory. The live database holds **1,865 listings** across **46 prefectures**, pulled from the at-home Akiya Bank portal and SUUMO, with 1,171 geocoded, 915 carrying photos, and 187 LLM translations cached.

| Area | Status |
|---|---|
| Bilingual region-driven SQLite schema (47 prefectures, 7 sources) | ✅ Live |
| Ingestion pipeline (raw capture → normalize → translate → dedup → upsert → match) | ✅ Live |
| Live scrapers: at-home Akiya Bank + SUUMO (selectolax, polite, profile-driven) | ✅ Live |
| EN translation layer (DeepL → Ollama → offline glossary, cached) | ✅ Live |
| Multi-profile preference engine + match-on-ingest scoring | ✅ Live |
| FastAPI REST API (8505) — QI contract + listings/profiles/ingest | ✅ Live |
| Gradio dashboard (7845) — Map / Discover / Profiles / Matches / Notifications / Settings | ✅ Live |
| Interactive Japan map (folium choropleth + clustered pins + GSI/hazard layers) | ✅ Live |
| Municipality geocoding (Nominatim, cached) | ✅ Live |
| Detail-page enrichment (photos, spec table, days-on-market, station) | ✅ Live |
| APScheduler background ingest + per-profile + daily digests | ✅ Live |
| On-site notifications + local SMTP email digests | ⚠️ Built — email off by default (needs SMTP creds) |
| Fixture adapters for LIFULL / at-home / homes / Rakumachi / municipal | ⚠️ Built — fixtures only; live `fetch_live()` not yet implemented |
| NSSM Windows service (QI_AkiyaScout) + public tunnel | 🗓️ Planned — runs via Start_AkiyaScout.bat today |
| QI Brain logging + cross-project integration | 🗓️ Planned |

## The Vision

One saved Profile, watched forever. As Japan's vacant-home glut grows, AkiyaScout quietly tracks the whole market in English — surfacing the right rural house at the right price the day it appears, with the seismic, era, hazard, and renovation context a foreign buyer needs to act with confidence.

## Bilingual by Design

Every user-facing text field is stored as a `*_ja` / `*_en` pair. The Japanese original is the source of truth (buyers use it with agents); the English is a cached translation layered on top. The dashboard offers an EN / 日本語 / Both toggle, the map ships English, Japanese, satellite, and topographic base layers, and place names are kept verbatim in code so a local LLM can't mangle them into pinyin.

---
*This page is editable at `C:\AkiyaScout\INTRO\status_intro.md` — save and click Refresh to update.*

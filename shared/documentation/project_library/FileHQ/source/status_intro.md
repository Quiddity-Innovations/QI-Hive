# FileHQ — File Intelligence Engine (merged into Naya)

## What is FileHQ?

FileHQ is a **file-intelligence engine** built by **Quiddity Innovations**: it walks a drive,
indexes every file into a single SQLite catalogue, fingerprints files to find exact duplicates,
classifies them by type and age, and can safely plan, execute, and undo a tidy-up of the result.
It turns millions of loose files spread across a drive into one queryable, deduplicated, categorised
index — without moving a single file until you explicitly approve it.

FileHQ began as a **standalone proof-of-concept** at `C:\FileHQ` (port 8000). It has since been
**merged into Naya** and now lives at `C:\NAYA\filehq\`. Naya — Quiddity's personal-assistant bot —
consumes FileHQ as its **file brain**: when you ask Naya "how many duplicates do I have?" or "what's
taking up space on F:?", Naya queries the FileHQ index (read-only by default) and answers from live data.

## Merged Status (important)

> **FileHQ is no longer a separate product.** It is a **sub-engine of Naya**.
> Registry status is `merged_into_naya`. The original `C:\FileHQ` is retired and marked for deletion;
> the engine code is the package `filehq/` under the Naya project root (`C:\NAYA\filehq\`).
> FileHQ does **not** run as its own `QI_*` Windows service — it is started by Naya, and Naya talks to it
> through `C:\NAYA\filehq_bridge.py`. Read paths (search, stats, duplicates) are always allowed;
> file **moves and deletes require explicit owner approval** in the same message.

## The Problem It Solves

- A large media/archive drive accumulates **millions** of files; nobody knows what is there.
- The **same file** exists in five places, silently wasting space — but you can't find the copies by eye.
- "What's on this drive?" has no fast answer without re-walking the whole tree every time.
- Tidying up by hand is slow and **dangerous** — one wrong move deletes the only copy.

## How It Works (the pipeline)

| Stage | What happens |
|---|---|
| **1. Scan** | `os.walk` the drive, record every file's path, size, dates, and extension into the `files` table. Re-scans are incremental — only new/modified files are touched. |
| **2. Categorize** | Map each file to a category (Photos, Videos, Documents, Software, …) by extension, and tag an archive era (`FORWARD` ≥ 2020 / `BACKWARD` < 2020). |
| **3. Hash** | A staged fingerprint: group by size → quick partial hash (first+last 64 KB) → full `xxhash64` only for partial-hash collisions. Singletons are never hashed. |
| **4. Find duplicates** | Group files sharing a full hash into `duplicate_groups`; mark the oldest copy as the keeper. |
| **5. Organize (optional)** | Plan moves into a canonical `ARCHIVE\` folder tree. Dry-run safe; real moves are logged and reversible. |
| **6. Undo** | Every destructive operation is recorded in `operations` with an undo path so a batch can be reversed. |

## Who Uses FileHQ?

| Consumer | How they interact |
|---|---|
| **Naya (the bot)** | Primary consumer. Injects live FileHQ stats into its LLM prompt and answers file questions on LINE / Telegram / web — read-only by default. |
| **Renne (owner)** | Triggers scans, reviews duplicate groups, approves clean-ups. Destructive actions need an explicit "you may proceed". |
| **FileHQ web dashboard** | A FastAPI + Jinja2 console (port 8000 standalone) with Dashboard, Duplicates, Explorer, Organizer, Tasks, History, Reports, Exceptions tabs. |
| **QI ecosystem** | Exposes file scanning/indexing and a file-search API; can consume NEXUS for LLM-assisted file analysis. |

## Current Build Status (June 2026)

FileHQ is a **mature, working engine** in its merged role. The catalogue currently holds **~2.86 million indexed
files** across 26 recorded scans (DB created 2026-06-23). Status reflects what actually runs vs. what is dormant
now that it lives inside Naya.

| Area | Status |
|---|---|
| Directory scanner (incremental `os.walk` indexer) | ✅ Live — ~2.86M files indexed |
| SQLite catalogue (`filehq.db`, WAL, 8 app tables) | ✅ Live |
| Extension + archive-era categorizer | ✅ Live |
| Two-phase xxhash duplicate hasher | ✅ Live |
| Exact-duplicate detection (`duplicate_groups`) | ✅ Live — 694 groups, 1,618 members |
| FastAPI engine + 50+ REST endpoints | ✅ Live (when started) |
| Naya integration bridge (`filehq_bridge.py`) | ✅ Live — read-only stats + chat actions |
| Web dashboard (Jinja2, 11 templates) | ✅ Built |
| Organizer (plan / execute / undo file moves) | ⚠️ Built — gated behind explicit approval |
| Scheduled tasks (APScheduler scan/dedup jobs) | ⚠️ Built — `tasks` table currently empty |
| DB maintenance (VACUUM / purge / health) | ✅ Live |
| Standalone `QI_FileHQ` Windows service | ❌ Not applicable — merged; launched by Naya |
| Near-duplicate / perceptual similarity (beyond exact hash) | 🗓️ Planned |
| Document content extraction / full-text search | 🗓️ Planned (registry-advertised, not yet built) |

## The Vision

FileHQ proves a reusable QI capability: **make a messy filesystem queryable and safe to clean.**
As Naya's file brain it answers questions in plain language; as a standalone idea it could become the
file-intelligence layer for any QI project. The 8000–8099 port block stays reserved should it ever
be split back out.

---
*This page is editable at `C:\NAYA\filehq\INTRO\status_intro.md` — save and click Refresh to update.*

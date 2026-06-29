# Naya — Renne's Private Personal AI + File Intelligence Assistant

## What is Naya?

Naya is a private, single-owner AI assistant built by **Quiddity Innovations** for Renne Santiago.
Where Maia is a product for schools, Naya is a tool for one person: it lives on Renne's own machine,
answers questions in technical domains (AI/ML, physics, programming, networking, VMs, Docker, languages),
and — uniquely — it can act on the local filesystem. Naya scans drives, finds duplicate and near-duplicate
files, plans cleanups, generates reports, and schedules heavy jobs for off-hours.

Naya is a **sibling of Maia**. It reuses Maia's proven engine (the same `maia_db`, `maia_context`, and
`maia_lang` modules from `C:\QI`) but points them at its own database, runs its own LLM chain, and wears a
personal persona. Naya is reached only through **Telegram** (long-poll, LAN-only) and a local **Gradio**
console — there is no public chat surface.

Naya = **Brain** (AI chat, an 8-model LLM chain, NEXUS multi-AI synthesis, memory) + **Hands** (the file
engine: SHA-256 duplicate detection, fuzzy-name matching, cleanup advisor, safe-delete with undo, watchers,
and scheduling). The FileHQ project was merged into Naya on 2026-04-05 as the `filehq/` package.

## The Problem We Solve

- Renne works across many disks and an enormous file collection — duplicates and clutter accumulate invisibly.
- "Where did my disk space go?" is hard to answer without a tool that actually scans and remembers.
- A general chatbot can answer a physics or networking question, but it cannot reach into your filesystem,
  find the duplicates, and (with consent) clean them up.
- Deleting files is dangerous — there must be approvals, a recycle-bin default, and an undo path.
- Heavy scans should not run while you are working; they belong in off-hours.

## Our Approach

Naya is **LLM-first**. Every message goes to the LLM chain for structured intent extraction first — the model
decides whether the message is a file command (`scan_duplicates`, `find_largest`, `generate_report`, ...) or
just a question. A keyword router survives only as a safety fallback. File actions pass through an explicit
**permission gate** stored in the database; destructive operations default to the recycle bin and are always
reversible.

Like Maia, Naya runs a **priority-ordered LLM chain with automatic failover** — local Ollama models first
(free, private, offline), then free cloud tiers, with Claude Sonnet as the last-resort high-quality fallback.
For genuinely hard questions Naya can route to the sibling **NEXUS** project for multi-AI synthesis. Nothing
about the models is hardcoded; the chain lives in the `llm_chain` table of `naya.db`.

## Who Uses Naya?

| Role | How they interact |
|---|---|
| **Renne (owner)** | Chats with Naya via the **@Naya_qi_bot** Telegram bot (long-poll, LAN-only) — asks questions, issues file commands, approves cleanups |
| **Renne (operator)** | Uses the local **Gradio console** (port 7861) — Chat, File Manager, Naya Brain, Settings, Logs tabs |
| **Sibling projects** | **Maia** may query Naya's API for file intelligence; **NEXUS** is called by Naya for multi-AI synthesis; **FileHQ** is absorbed as the file engine |
| **Background watchers** | No human — disk-space monitor, USB watcher, and off-hours scheduler run inside the server and notify Renne via Telegram |

## Current Build Status (June 2026)

Naya's development is **paused** in the QI registry — no active feature work is underway and it is not on the
near-term roadmap. However, the **services are running**: `QI_NayaBot` (port 8002) and `QI_NayaGradio`
(port 7861) are both live as NSSM Windows services, so Naya still answers on Telegram and the console day to day.
The status below reflects what the running code actually supports.

| Area | Status |
|---|---|
| Telegram chat (long-poll, @Naya_qi_bot, owner-restricted) | ✅ Live |
| Flask API server (`/ask`, `/health`, `/status`, `/api/action`) | ✅ Live |
| 8-model LLM chain with automatic failover | ✅ Live |
| LLM-first structured intent routing + action dispatcher | ✅ Live |
| Gradio console (Chat, File Manager, Naya Brain, Settings, Logs) | ✅ Live |
| SHA-256 exact-duplicate scanner (background threads) | ✅ Live |
| Fuzzy / similar-name scanner | ✅ Live |
| Cleanup advisor (storage analysis + plan + execute) | ✅ Live |
| File memory (folder insights, intent capture + reminders) | ✅ Live |
| Permission gate + safe-delete with undo (recycle-bin default) | ✅ Live |
| Report generation (PDF / Word / Markdown / text) | ✅ Live |
| Background watchers (disk monitor, USB watcher, off-hours scheduler) | ✅ Live |
| Chat-driven deferral + Windows Task Scheduler integration | ✅ Live |
| NEXUS multi-AI synthesis routing | ⚠️ Partial — built, off by default (`personal.nexus_enabled`) |
| FileHQ file engine (merged `filehq/` package, internal port 8200) | ⚠️ Partial — bridged + auto-started on demand |
| RAG / knowledge base (ChromaDB) | ⚠️ Partial — removed from Naya, archived in `RAG_ARCHIVE\` |
| LINE channel (Naya OA) | ⚠️ Partial — module present, opt-in, no-ops without creds |
| Cross-bot peer bridge (Tasuke / Maia / Naya, HMAC-signed) | ⚠️ Partial — HTTP webhook built |
| QI Brain session/decision logging | 🗓️ Planned — not wired |
| Public internet exposure | 🚫 By design never — LAN-only (one demo Cloudflare tunnel for the UI only) |

## The Vision

Naya is the proof that the Maia engine generalises: one shared codebase can serve a classroom (Maia) or a
single power-user with filesystem superpowers (Naya). The longer-term idea is a personal AI that can do
anything its owner can do on their machine — find, organise, summarise, clean, schedule — but only ever with
explicit consent and always reversibly. Naya is where the "agent that touches the real world" half of the
QI vision is prototyped, safely, on one trusted machine.

## Safety by Design

Naya can reach into the filesystem, so safety is structural, not optional:

- **Permission gate** — every destructive action checks a flag in `naya.db` (`personal.file_modify_approved`,
  `file_scan_approved`, ...). Denied actions tell the owner the exact phrase to say to approve.
- **Recycle bin first** — deletes go to the Windows recycle bin (via `send2trash`) by default; permanent
  delete needs explicit approval.
- **Undo** — the executor moves files to a TRASH folder and logs every batch, so `undo_last()` can restore them.
- **Never the keep copy** — duplicate cleanup always preserves one copy (the oldest) of each group.
- **LAN-only** — Telegram uses outbound long-polling, so no inbound port is ever opened to the internet.

## Brain + Hands (Sibling of Maia)

- **Shared engine** — `naya_db.py` patches `maia_db.DB_FILE` to `C:\NAYA\naya.db`, then re-exports every
  function, so Maia's battle-tested DB / context / language code runs unchanged against Naya's own data.
- **Own data** — `naya.db` holds config, the LLM chain, and conversation history; `naya_brain.db` holds the
  file-intelligence data (scans, similarity groups, folder insights, intents, operations).
- **Separate, never merged** — Maia can call Naya's API; Naya never becomes part of Maia's codebase.

---
*This page is editable at `C:\NAYA\INTRO\status_intro.md` — save and click Refresh to update.*

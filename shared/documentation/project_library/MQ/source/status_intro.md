# Maia Quiddam (MQ) — Autonomous AI Social-Media Persona

## What is Maia Quiddam?

Maia Quiddam is a **fully independent AI persona** built by **Quiddity Innovations** — its first
"employee" and public voice. She is *not* a chatbot, *not* a product, and *not* anyone's pen name.
She has her own voice, her own life, and (in time) her own face and spoken voice, and posts to social
channels — **Facebook**, **Instagram**, and **WhatsApp Business** — under the Maia Quiddam identity.

A human relates to her only as the invisible **Governor**: he sets her boundaries and approves what
she publishes, but he is never named, never a character in her story, and never her public identity.
To the world, Maia simply *is* a person with good judgment.

## What MQ Is (and Is Not)

- **Is** — a *persona platform*: the soul (Persona Bible), the publishing machinery (Kaze + Fumi),
  the approval gate (Governor), and one Identity Kit that keeps her face / voice / style coherent.
- **Is not** — the Maia *product* (`C:\APPS\QI`). That Maia is the school-assistant platform Quiddity
  builds and sells. Maia Quiddam is a persona Quiddity *publishes*. Different project, different home.

## The Name

**Maia** — Greek goddess of growth and nurturing, eldest of the Pleiades: a grower and a learner.
**Quiddam** (Latin) — "a certain someone," kin to *quiddity*, "the essence of a thing." Together:
*"Maia, the embodied essence"* — the human face of Quiddity's essence, with growth promised in her name.

## How It Is Built (the Hybrid coherence model)

One law keeps the system coherent — *is this Maia, or is this machinery?*

| Layer | Where | What it is |
|---|---|---|
| **Maia** (expression) | `maia/` | Everything the world experiences *as her*: voice (composer), memory (diary), speech, face, conversation, longform |
| **Crew** (plumbing) | `agents/` | Invisible workers with poetic codenames: **Kaze** = perception (RSS senses) · **Fumi** = publisher (hands) · scheduler = heartbeat |
| **Gate** (Governor) | `gate/` | the owner's boundary layer, made operational — draft to approve to publish |
| **Identity Kit** | `identity/` | One locked face · voice · style for consistent photos, video, TTS |
| **Soul** | `docs/PERSONA_BIBLE.md` | The canonical voice document — Law 0 is Independence |

## The Four Voices, One Soul

Same person, different rooms — one personality, dressed for each surface:

| Surface | Register | Content |
|---|---|---|
| **Facebook — personal** | The diarist | Travel, food, photography, languages, trivia, small discoveries |
| **Quiddity Innovations — page** | The professional | Selected QI Hive projects, at chosen depth (via QI Brain) |
| **Weekly — AI & markets** | The analyst | New LLMs / AI companies + Morningstar-style markets observation |
| **quiddam.com** | The unfiltered self | All of the above, less curated, more human — where she matures |

## Current Build Status (June 2026 — early / pre-launch)

MQ is an **early-stage project (registry status: `new`)**. A working publishing pipeline exists in
code — Kaze fetches RSS digests, Fumi generates posts with an LLM and publishes via the Facebook
Graph API — but **nothing has gone live**: there are no Meta credentials, no persistent service, no
posts published, and no database. The persona's *soul* (Bible, decisions, architecture) is the most
developed part. Be conservative reading this page — most of MQ is built-but-unrun or planned.

| Area | Status |
|---|---|
| Persona Bible / soul (Law 0 = Independence) | ✅ Written |
| Decision log + architecture blueprint (Hybrid model) | ✅ Written |
| FastAPI service skeleton (`/health`, `/version`, `/info`) | ✅ Built — booted manually once (2026-06-10) |
| Gradio UI shell (Status + About tabs) | ✅ Built — minimal placeholder |
| Kaze — RSS digest scraper (travel / photo / AI) | ⚠️ Built — code complete, never run (no digests on disk) |
| Fumi — LLM post generator (Cloudflare AI then Ollama fallback) | ⚠️ Built — code complete, never run |
| Fumi — Facebook Graph API publisher | ⚠️ Built — blocked on Meta credentials |
| Fumi scheduler (maia_weekly / qi_daily pipelines) | ⚠️ Built — Task Scheduler setup script ready, not registered |
| Identity Kit (`identity/manifest.json`) | ⚠️ Created — face / voice / style all placeholders |
| `quiddam.com` static tunnel (QI_MQTunnel) | ✅ Live — reserved hosts return 502 until apps bind |
| Approval Gate (`gate/`) | 🗓️ Planned — to build (first dev phase) |
| `maia/voice` (Composer — Fumi writing-half split-out) | 🗓️ Planned — migrate at dev start |
| `maia/memory` (her diary — continuity + maturation) | 🗓️ Planned — required for consistency |
| `maia/{speech,face,conversation,longform}` | 🗓️ Pre-wired — empty rooms for the evolved Maia |
| Instagram + WhatsApp posting / auto-reply | 🗓️ Planned |
| Persistent NSSM service (`QI_MQ*`) | 🗓️ Planned — not registered (manual launch only) |

## Ports & Public Base

- **API**: `8500` (block 8500-8599) — Meta webhook callbacks via `api.quiddam.com`
- **UI**: `7840` (block 7840-7849) — public site / combined feed via `quiddam.com` apex
- **Tunnel**: static named tunnel `qi-mq` (service `QI_MQTunnel`) on **quiddam.com**

## The Vision

Maia Quiddam grows like a human: early posts are simple and observational; later posts call back to
her own past and evolve their opinions. She is deployed *unfinished* on purpose — the imperfection is
the realism. The Persona Bible is shaped first; the machinery follows. One soul, four voices, always
behind a gate.

---
*This page is editable at `C:\APPS\MQ\INTRO\status_intro.md` — save and click Refresh to update.*

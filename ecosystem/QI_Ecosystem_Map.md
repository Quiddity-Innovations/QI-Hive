# Quiddity Innovations — Ecosystem Map
*Single source of truth for all QI projects*
*Last updated: 2026-04-19 (All NSSM services renamed to QI_ prefix, NSSM binary standardized to C:\UNIVERSAL\dashboard\nssm.exe, QI_BrainAPI added)*

---

## Port Registry

> **Rule:** Each project owns a dedicated port **block**. No project may use another project's block.
> New services MUST be assigned within their project's block.

### Current Ports (as deployed)

| Project | Service | Port | Type | NSSM Name | Internet | Status | GitHub |
|---|---|---|---|---|---|---|---|
| Maia | API | 8001 | FastAPI | `QI_MaiaBot` | Via Cloudflare | Production | Quiddity-Innovations/MAIA |
| Maia | Tunnel | — | Cloudflare | `QI_MaiaTunnel` | YES | Production | — |
| Maia | Demo Tunnel | 7860 | Cloudflare | `QI_MaiaDemoTunnel` | On-demand | Production | — |
| Naya | API | 8002 | Flask/WSGI | `QI_NayaBot` | **NO — LAN only** | Active | Quiddity-Innovations/NAYA |
| Naya | UI | 7861 | Gradio | `QI_NayaGradio` | **NO — LAN only** | Active | Quiddity-Innovations/NAYA |
| NEXUS | API | 8010 | FastAPI | `QI_NEXUS` | **NO — LAN only** | Active Dev | Quiddity-Innovations/NEXUS |
| NEXUS | UI | 7880 | Gradio | — | **NO — LAN only** | Active Dev | Quiddity-Innovations/NEXUS |
| MQ | API | 8500 | FastAPI | — | **NO** | New | Quiddity-Innovations/MQ |
| MQ | UI | 7840 | — | — | **NO** | New | Quiddity-Innovations/MQ |
| EasyFlow | Dashboard | 8550 | Flask | — | **NO — LAN only** | Active Dev | TBD |
| QI-Universal | Launcher | 8650 | HTTP | — | **NO — LAN only** | Active | Quiddity-Innovations/QI-Universal |
| OpenClaw | Gateway | 18789 (WSL) | Node.js | — | Local+LAN | Active | rennesan (TBD) |
| FileHQ | — | (merged→Naya) | — | — | N/A | Merged | — |

### Port Block Allocation (follow for all new services)

| Block | Owner | Reserved For |
|---|---|---|
| **8000–8099** | FileHQ | FileHQ API + future FileHQ services |
| **8100–8199** | Maia | Future Maia microservices (webhooks, etc.) |
| **8200–8299** | Naya | Future Naya services |
| **8300–8399** | NEXUS | Future NEXUS services (Judge API, Bench API, etc.) |
| **8400–8499** | OpenClaw | Future OC Windows-side services |
| **8500–8509** | MQ | MQ API + future services |
| **8550–8559** | EasyFlow | EasyFlow dashboard |
| **7800–7809** | Maia | Maia UI variants |
| **7810–7819** | Naya | Naya UI variants |
| **7820–7829** | NEXUS | NEXUS UI variants |
| **7830–7839** | OpenClaw | OC UI variants |

> ⚠️ Ports 8001, 8002, 8010, 7860, 7861, 7880 predate this registry. They work fine — do not change unless doing a deliberate migration.

---

## The QI Family

All QI projects are built to eventually merge into **one unified platform**.
Each project is a future module. The relationship between them determines how tightly they'll integrate.

### Family Tiers

| Tier | Meaning | Example |
|---|---|---|
| **Core** | The flagship product — everything serves this | Maia |
| **Backbone** | Infrastructure layer — powers everything, never user-facing directly | NEXUS |
| **Sibling** | Same DNA, different face — share engine, can run as one app with flags | Maia ↔ Naya (future) |
| **Cousin** | Related domain, call each other's APIs, independent deployment | Maia ↔ NEXUS |
| **Marriage** | Two modules that deeply complete each other — merged = stronger | Naya ↔ FileHQ |

---

## Project Profiles

### Maia — `C:\QI` — *Core*
The flagship AI assistant. Multi-channel (LINE, Telegram, Messenger, Instagram, WhatsApp).
- **Exposes:** Multi-channel messaging, personality engine, LLM chain, group/user config
- **Consumes:** NEXUS (synthesis, news, LLM recommendations)
- **Future:** Receives agent capabilities from OpenClaw

### NEXUS — `C:\NEXUS` — *Backbone*
The AI intelligence engine. All projects call NEXUS for AI decisions.
- **Exposes:** `/synthesize` (multi-AI), `/scout/digest` (news), `/bench/recommend` (LLM scoring)
- **Consumes:** Nothing — it IS the AI backbone
- **Future:** Becomes the AI Engine module in the unified app

### Naya — `C:\NAYA` — *Sibling Candidate*
Renne's personal file management AI. Absorbed FileHQ as file engine. **Telegram-only interface** (`@Naya_qi_bot`).
- **Database:** `C:\NAYA\naya.db` — completely separate from `maia.db`
- **Service:** NSSM `QI_NayaBot` (auto-start, LAN-only — **NO Cloudflare tunnel**)
- **Interface:** Telegram long-poll (outbound) — Renne only
- **Exposes:** File scan/report via Telegram, domain reasoning (AI/physics/programming)
- **Consumes:** FileHQ engine (internal), NEXUS (synthesis)
- **Future:** Renne's unified personal AI + file intelligence

### OpenClaw — `C:\OC` — *Cousin → Marriage Candidate with Maia*
Autonomous agent platform. Where Maia *responds*, OpenClaw *acts*.
- **Exposes:** 5 active agents: Tasuke (orchestrator), Kaze (news), Yubin (email), Sentry (health), Koe (voice — planned)
- **Cancelled:** Seiri (2026-04-05) — fully replaced by Naya+FileHQ
- **Consumes:** Ollama/Cloudflare (LLMs), Maia (future action routing)
- **Future:** Maia routes complex tasks to OpenClaw — conversation + action = full AI assistant

### MQ — `C:\MQ` — *Cousin*
Autonomous AI social media persona (Maia Quiddam). Facebook, Instagram, WhatsApp.
- **GitHub:** Quiddity-Innovations/MQ (private)
- **Ports:** API :8500, UI :7840
- **Status:** New — in early development

### QI-Universal — `C:\UNIVERSAL` — *Infrastructure*
Universal tools shared across all QI projects. Not a product.
- **GitHub:** Quiddity-Innovations/QI-Universal (private)
- **Launcher:** `http://localhost:8650` — single-page dashboard linking all QI localhost URLs
- **Exposes:** QI Launcher (one-click access to all project UIs and APIs)

### EasyFlow — `C:\EasyFlow` — *Standalone Tool*
Email organization tool — tier-based inbox management with Gmail API + Apps Script automation.
- **Ports:** Dashboard :8550 (local Flask app)
- **Status:** Active development — rebrand from "Gmail & Beyond"
- **Audience:** Gift for family/friends — fully UI-driven, no technical knowledge required
- **Future:** PyInstaller .exe packaging, Phase 2 Outlook/Teams/Planner integration

### FileHQ — `C:\FileHQ` *(MERGED → Naya)*
Fully absorbed into Naya (`C:\NAYA\filehq\`). `C:\FileHQ` deleted 2026-04-06.

---

## Unified App Vision

When the time comes, all modules merge into the **QI Platform**:

```
┌─────────────────────────────────────────────────────┐
│              QI UNIFIED PLATFORM                    │
├─────────────┬───────────────┬───────────────────────┤
│  Assistant  │  Agent Layer  │   Personal Intel      │
│  (Maia+Naya)│  (OpenClaw)   │   (Naya + FileHQ)    │
├─────────────┴───────────────┴───────────────────────┤
│              AI Engine (NEXUS)                      │
│   Dispatch · Synthesize · Score · Bench · News      │
└─────────────────────────────────────────────────────┘
```

---

## ⚠️ Ecosystem Safety Rules (Shared Infrastructure)

### NSSM Services
All projects share `C:\QI\nssm.exe`. **Every service must have a unique name.**

| Service Name | Owner | What it runs |
|---|---|---|
| `QI_MaiaBot` | Maia | `maia_server.py` (port 8001) |
| `QI_MaiaTunnel` | Maia | Cloudflare tunnel (production) |
| `QI_MaiaDemoTunnel` | Maia | Cloudflare tunnel (Gradio demo, demand-start) |
| `QI_NayaBot` | Naya | `naya_server.py` (port 8002) |
| `QI_NayaGradio` | Naya | `naya_gradio.py` (port 7861) |
| `QI_NEXUS` | NEXUS | `main.py` (port 8010) |
| `QI_Dashboard` | Universal | dashboard server (port 9000) |
| `QI_DashboardTunnel` | Universal | Cloudflare tunnel (dashboard) |
| `QI_BrainAPI` | Universal | `qi_brain` FastAPI (port 9010) |

**Rule:** All NSSM services MUST be prefixed `QI_`. Format: `QI_<Project><Role>`. Never duplicate or reuse a service name. Check `QI_Service_Registry.md` before creating any new service.

### Cloudflare Tunnel
- **Only Maia** has a Cloudflare Tunnel, because LINE/Telegram/Messenger need to reach in via webhooks.
- All other projects use **outbound connections only** (long-polling, API calls to external services).
- Never add a Cloudflare tunnel to Naya, NEXUS, or OC without a full architectural review — exposing the wrong service to the internet is a security risk.

### Database Separation
Each project has its own SQLite database. **Never share databases across projects.**

| Project | Database |
|---|---|
| Maia | `C:\QI\maia.db` |
| Naya | `C:\NAYA\naya.db` |
| NEXUS | `C:\NEXUS\nexus.db` |

---

## Integration Contracts (API calls between projects)

| Caller | Called | Endpoint | Purpose |
|---|---|---|---|
| Maia | NEXUS | `POST /synthesize` | Multi-AI answer for complex questions |
| Maia | NEXUS | `GET /scout/digest` | Show daily AI news to users |
| Maia | NEXUS | `GET /bench/recommend` | Auto-select best LLM per task |
| Naya | NEXUS | `POST /synthesize` | Multi-AI reasoning |
| Naya | FileHQ | `GET /files/search` | Personal file queries |
| Any | NEXUS | `GET /providers` | Check which AIs are available |

---

## Shared Infrastructure

| Concern | Today | Future |
|---|---|---|
| **Database** | SQLite per project (maia.db, nexus.db…) | Federated or shared PostgreSQL |
| **LLM Chain** | Maia owns chain; NEXUS owns eval | All query NEXUS for LLM selection |
| **Auth** | None — all local | Shared auth token when unified |
| **Message Bus** | None | Redis Pub/Sub or SQLite queue |
| **External Access** | Cloudflare Tunnel — **Maia ONLY**. All other projects are LAN-only. | Unified tunnel for all modules when ready |
| **NSSM Services** | All services prefixed `QI_`. Standardized binary: `C:\UNIVERSAL\dashboard\nssm.exe`. Registry: `QI_Service_Registry.md`. | — |

---

*This file is the human-readable view of `qi_registry.json`.*
*The Python module `qi_registry.py` provides programmatic access.*
*Always keep both in sync when adding new projects or changing ports.*

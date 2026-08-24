# Quiddity Innovations — Ecosystem Map
*Single source of truth for all QI projects*
*Last updated: 2026-08-07 — Cloudflare Tunnel section rewritten, NSSM binary path corrected
to `C:\QIH\engine\bin\nssm.exe`, unwired Maia/Naya→NEXUS contracts marked, hub adoption status
corrected against live usage. Connectivity split out to `QI_Connectivity_Map.md`.*

> **Connectivity, endpoints and per-app integration live in
> [`QI_Connectivity_Map.md`](QI_Connectivity_Map.md)** — public hosts, tunnel→gate→app
> routing, internal ports, LLM Hub adoption with per-app fallback posture, and open
> risks. Verified against the running machine, with a collector script to refresh it.
> This file remains the family/taxonomy and project-profile view.

---

> ## ⚠️ 2026-08-05 — the "Internet" column below is OUT OF DATE. Do not trust it.
>
> An exposure audit found **22 hostnames published to the internet through 16
> Cloudflare tunnels**, several of which this document still describes as
> "**NO — LAN only**" (NEXUS, Naya and others were in fact publicly reachable, with
> no authentication). Every one of them pointed straight at an app port.
>
> **All public traffic now goes through QI Gate** (`QI_Caddy` :9040 →
> `QI_Gate` :9041) and requires a login.
>
> **The authoritative list of what is exposed is now
> [`C:\QIH\engine\gate\config\gate.json`](../engine/gate/config/gate.json)** — not
> this file. Full record:
> [`QI_Public_Exposure_Hardening_2026-08-05.md`](../shared/documentation/security/QI_Public_Exposure_Hardening_2026-08-05.md).
>
> **Rule going forward:** any new internet-exposed service must be declared in
> `gate.json` and routed through :9040. Never point a tunnel at an app port again.
> Verify with `python C:\QIH\engine\gate\verify_gate.py`.

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
| AutoPDF | HTTP | 6969 | PowerShell | — | **NO — loopback only** | Active Dev (Phase 2c) | TBD |
| AutoPDF | MCP | 8701 | Python (FastMCP) | — | **NO — loopback only** | Active (opt-in, off by default) | TBD |
| AkiyaScout | API | 8505 | FastAPI | — | **NO — planning** | New (spec/design) | TBD |
| AkiyaScout | UI | 7845 | Gradio | — | **NO — planning** | New (spec/design) | TBD |
| ComfyUI | API + UI | 8740 | Python (aiohttp) | — | **NO — loopback only** | Active | TBD |

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
| **8700–8709** | AutoPDF | AutoPDF + future AutoPDF microservices (extraction worker, scheduler agent) |
| **8720–8729** | Claude Voice | realtime two-way voice |
| **8730–8739** | Voice Studio | studio/batch voice rendering (panel currently on 7863) |
| **8740–8749** | **ComfyUI** | generators + API (migrated here 2026-08-10) |
| **8750–8759** | FilmForge | film orchestration (panel 7865; headless API split reserved) |
| **7800–7809** | Maia | Maia UI variants |
| **7810–7819** | Naya | Naya UI variants |
| **7820–7829** | NEXUS | NEXUS UI variants |
| **7830–7839** | OpenClaw | OC UI variants |

> ⚠️ Ports 8001, 8002, 8010, 7860, 7861, 7880, **6969 (AutoPDF)** predate this registry. They work fine — do not change unless doing a deliberate migration.

> ✅ **Resolved 2026-08-10 — ComfyUI migrated 8189 → 8740.** It had been sitting
> inside **Maia's 8100–8199 block**, which the block rule forbids. 8740 opens the
> **media/GPU band** directly above Claude Voice (8720–8729) and Voice Studio
> (8730–8739), so the three GPU tenants are now contiguous.
>
> The port was referenced by four projects, so it was migrated in **one atomic
> pass** (`D:\Dev\FilmForge\tools\migrate_comfy_port.py`) — 33 references across
> 14 files: `Start_ComfyUI.bat`, `qi_comfy_mcp.py` (`COMFY_URL`),
> `voicestudio.json`, `mediastudio.json`, FilmForge config + broker, this map,
> the registry, and the ComfyUI docs. Backups kept as `*.bak-port8740`.
>
> **Never migrate it piecemeal.** A half-done change leaves `voice_studio`'s
> `POST /free`, Media Studio's provider and Claude's MCP pointing at a dead
> socket, each failing differently.

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

### Maia — `C:\APPS\QI` — *Core*
The flagship AI assistant. Multi-channel (LINE, Telegram, Messenger, Instagram, WhatsApp).
- **Exposes:** Multi-channel messaging, personality engine, LLM chain, group/user config
- **Consumes:** NEXUS (synthesis, news, LLM recommendations)
- **Future:** Receives agent capabilities from OpenClaw

### NEXUS — `C:\APPS\NEXUS` — *Backbone*
The AI intelligence engine. All projects call NEXUS for AI decisions.
- **Exposes:** `/synthesize` (multi-AI), `/scout/digest` (news), `/bench/recommend` (LLM scoring)
- **Consumes:** Nothing — it IS the AI backbone
- **Future:** Becomes the AI Engine module in the unified app

### Naya — `C:\APPS\NAYA` — *Sibling Candidate*
Renne's personal file management AI. Absorbed FileHQ as file engine. **Telegram-only interface** (`@Naya_qi_bot`).
- **Database:** `C:\APPS\NAYA\naya.db` — completely separate from `maia.db`
- **Service:** NSSM `QI_NayaBot` (auto-start, LAN-only — **NO Cloudflare tunnel**)
- **Interface:** Telegram long-poll (outbound) — Renne only
- **Exposes:** File scan/report via Telegram, domain reasoning (AI/physics/programming)
- **Consumes:** FileHQ engine (internal), NEXUS (synthesis)
- **Future:** Renne's unified personal AI + file intelligence

### OpenClaw — `C:\APPS\OC` — *Cousin → Marriage Candidate with Maia*
Autonomous agent platform. Where Maia *responds*, OpenClaw *acts*.
- **Exposes:** 5 active agents: Tasuke (orchestrator), Kaze (news), Yubin (email), Sentry (health), Koe (voice — planned)
- **Cancelled:** Seiri (2026-04-05) — fully replaced by Naya+FileHQ
- **Consumes:** Ollama/Cloudflare (LLMs), Maia (future action routing)
- **Future:** Maia routes complex tasks to OpenClaw — conversation + action = full AI assistant

### MQ — `C:\APPS\MQ` — *Cousin*
Autonomous AI social media persona (Maia Quiddam). Facebook, Instagram, WhatsApp.
- **GitHub:** Quiddity-Innovations/MQ (private)
- **Ports:** API :8500, UI :7840
- **Status:** New — in early development

### QI-Universal — `C:\UNIVERSAL` — *Infrastructure*
Universal tools shared across all QI projects. Not a product.
- **GitHub:** Quiddity-Innovations/QI-Universal (private)
- **Launcher:** `http://localhost:8650` — single-page dashboard linking all QI localhost URLs
- **Exposes:** QI Launcher (one-click access to all project UIs and APIs)

### EasyFlow — `C:\APPS\EasyFlow` — *Standalone Tool*
Email organization tool — tier-based inbox management with Gmail API + Apps Script automation.
- **Ports:** Dashboard :8550 (local Flask app)
- **Status:** Active development — rebrand from "Gmail & Beyond"
- **Audience:** Gift for family/friends — fully UI-driven, no technical knowledge required
- **Future:** PyInstaller .exe packaging, Phase 2 Outlook/Teams/Planner integration

### FileHQ — `C:\FileHQ` *(MERGED → Naya)*
Fully absorbed into Naya (`C:\APPS\NAYA\filehq\`). `C:\FileHQ` deleted 2026-04-06.

### AutoPDF — `C:\APPS\AutoPDF` — *Standalone Tool / Cousin Candidate*
Local PDF toolkit: convert / split / extract / catalog. Self-contained — bundles Ghostscript, Poppler, Tesseract, Tabula, PDFtk, JRE. Optional Ollama integration for Smart Mapping (template authoring + AI-extract fields).
- **Ports:** HTTP :6969 (loopback only) · **MCP gateway :8701** (`QI_AutoPDFMCP`, loopback, opt-in — first port used from AutoPDF's own 8700–8709 block)
- **Status:** Active Dev — Phase 2c complete (templates v2 + regex library + test automation); MCP gateway added 2026-08-07
- **Path:** `C:\APPS\AutoPDF\` — moved here 2026-05-13 from `C:\Users\renne\Downloads\AUTOPDF\`. Fully portable: reads everything via relative paths, so no code edits were needed.
- **Exposes:** Template-driven extraction (`/api/template-apply-batch`, `/api/template-test`, `/api/ai-chat`, `/api/regex-library`)
- **Exposes (MCP :8701):** nine tools, each independently switchable in `config\mcp_gateway.json` — `autopdf_status` / `autopdf_templates` / `autopdf_presets` / `autopdf_regex_library` (metadata, on by default); `autopdf_list_pdfs` / `autopdf_extract` / `autopdf_index_preview` (real document content, off); `autopdf_run_workflow` / `autopdf_split` (writes files, off). A disabled tool is never registered, so it is absent from `tools/list` rather than refused. Uses the **shared** `qi_mcp_gateway.py` module — AutoPDF only adds an adapter, same as MapSnap.
- **Consumes:** Local Ollama (optional) only — no other QI project at runtime
- **Future:** Maia/NEXUS could call `/api/template-apply-batch` to extract fields from user-supplied PDFs. Workflow + Scheduler tabs already exist for ecosystem-level orchestration; integration with QI Hive's scheduler is a Phase 3 candidate.
- **Note:** AutoPDF is the second project on the shared MCP gateway module (after MapSnap). The module's `ADAPTERS` registry is the extension point — adding NEXUS or Gamez is one adapter function each, no gateway changes.
- **GitHub:** TBD (no remote yet)

### ComfyUI (QI Media Engine) — `D:\AI` — *Cousin / shared GPU utility*
The only sanctioned image and video generator on this machine. Driven conversationally by Claude through the `qi-comfy` MCP server (11 tools), and usable directly in its own web UI. Registered 2026-08-10 (the id `comfyui` was already referenced by `voice_studio` before any record existed).
- **Ports:** :8740 API + web UI, loopback only. ⚠️ Inside Maia's 8100–8199 block — see the conflict note under Port Registry.
- **Status:** Active. 14 workflows verified working 2026-08-10.
- **Trigger discipline:** Claude generates **only** on an explicit `RENDER:` or `/comfy` message — never inferred from conversation. Rules in `D:\AI\CLAUDE.md`. SFW and NSFW both in scope; no real identifiable people, no minors.
- **Video engines** (selection + defaults in `D:\AI\workflows\_video_backends.json`):
  - **MiniMax-H3** — *default*. NVFP4 build (11.67 GB) + Qwen3-VL-32B encoder + 4-step Turbo LoRA. **1344×768 with stereo audio in ~75 s.** NVFP4 is a native op on the sm_120 Blackwell 5080; the int8 build (19.53 GB) does not fit 16.3 GB VRAM.
  - **Wan 2.1** — 14B fp8 T2V + I2V-720P. 832×480, silent, ~335 s. Kept deliberately as an independent model family and fallback. Escalation ladder (fp16 encoder → kijai WanVideoWrapper) defined but not built, and must stay *switchable* rather than replacing what works.
  - **MiniMax cloud** (Hailuo 03 API nodes) — installed, **disabled**, bills credits.
- **Image engines:** Z-Image Turbo (8 s), SDXL (+ the only SDXL LoRA `nudify_xl_lite`), SD 1.5 (Realistic Vision 5.1, for the three SD 1.5 LoRAs), **Ideogram v4** — the only engine here that renders legible typography.
- **LLM in-graph:** Gemma 4 runs *inside* ComfyUI via the native `TextGenerate` node (~15 tok/s) — captions a reference image and drives generation with no API key (`describe2img`).
- **Exposes:** `POST /prompt`, `GET /history/{id}`, `GET /queue`, `GET /system_stats`, `GET /object_info`, `GET /view`, **`POST /free`** (VRAM release — already consumed by `voice_studio`)
- **Deliberately NOT integrated:** in-graph Ollama or Cloudflare Workers AI nodes. NEXUS already reaches both with 14 providers; duplicating that inside ComfyUI would add moving parts for no gain.
- **Workflows exist twice on purpose:** API format in `D:\AI\workflows\` (what Claude queues) and editor twins prefixed `QI - ` in the ComfyUI user folder (what Renne clicks). **They are copies, not links.**
- **Docs:** `D:\AI\CLAUDE.md` · `CHEATSHEET.md` · `RENDER_TEMPLATES.md` · `HOW_TO_RUN_IT_YOURSELF.md`
- **GitHub:** TBD (portable third-party app; only config and workflows are QI-owned)

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
All projects share `C:\APPS\QI\nssm.exe`. **Every service must have a unique name.**

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
| `QI_BrainAPI` | Universal | `qi_brain` FastAPI (port 9011) |

**Rule:** All NSSM services MUST be prefixed `QI_`. Format: `QI_<Project><Role>`. Never duplicate or reuse a service name. Check `QI_Service_Registry.md` before creating any new service.

### Cloudflare Tunnel
> **Rewritten 2026-08-07.** This section previously said "Only Maia has a Cloudflare
> Tunnel" and "never add a tunnel to Naya, NEXUS or OC". Both were long out of date —
> 16 named tunnels serve 21 public hostnames today. Full verified inventory:
> **`QI_Connectivity_Map.md`**.

- **16 named tunnels**, one per project, configs in `C:\QIH\engine\tunnels\configs\`.
- **Every tunnel terminates at Caddy `:9040` (the QI Gate edge)** — not at the app.
  Caddy routes by hostname and asks QI Gate `:9041` whether the caller may pass.
  The single exception is `connector.quiddityinnovations.com`, which goes straight
  to `:9030` and carries its own bearer token.
- Adding a public hostname is a **`gate.json` edit + `gen_caddyfile.py` regeneration**,
  never a hand-edited Caddyfile.
- Apps stay on **loopback** and are reached only through the gate. Check the bind
  before assuming this: five apps currently also listen on `0.0.0.0`, which lets the
  LAN bypass the gate entirely (see `QI_Connectivity_Map.md` §6).
- **Never tunnel NEXUS `:8010`** — it holds every provider API key for the ecosystem.

### Database Separation
Each project has its own SQLite database. **Never share databases across projects.**

| Project | Database |
|---|---|
| Maia | `C:\APPS\QI\maia.db` |
| Naya | `C:\APPS\NAYA\naya.db` |
| NEXUS | `C:\APPS\NEXUS\nexus.db` |

---

## Integration Contracts (API calls between projects)

| Caller | Called | Endpoint | Purpose |
|---|---|---|---|
| **Any QI tool** | **NEXUS** | **`POST /v1/chat/completions`** | **QI LLM Hub (added 2026-07-02): OpenAI-compatible gateway. base_url `http://127.0.0.1:8010/v1`, any api_key, model = provider id or `auto`. Send `X-QI-App: <project>` for usage attribution (`GET /hub/usage`). Keys live ONLY in NEXUS `secrets/nexus.env`. LAN-only — never tunnel this.** |
| Any | NEXUS | `GET /v1/models` | List routable hub provider ids |
| ~~Maia~~ | NEXUS | `POST /synthesize` | ⚠️ **PLANNED, NOT WIRED** (verified 2026-08-07) — `C:\APPS\QI\nexus_client.py` implements this but is imported nowhere |
| ~~Maia~~ | NEXUS | `GET /scout/digest` | ⚠️ **PLANNED, NOT WIRED** — same client, never called |
| ~~Maia~~ | NEXUS | `GET /bench/recommend` | ⚠️ **PLANNED, NOT WIRED** |
| ~~Naya~~ | NEXUS | `POST /synthesize` | ⚠️ **PLANNED, NOT WIRED** |
| Naya | FileHQ | `GET /files/search` | Personal file queries |
| Any | NEXUS | `GET /providers` | Check which AIs are available |
| TubeScout | PlayDeck | `GET http://127.0.0.1:8506/?play=<url>` | "▶ PlayDeck" on news cards (added 2026-08-04): deep link resolves + plays the video in PlayDeck. Buttons self-remove for non-localhost visitors, so the public tunnel page never shows dead links. |

**Hub adoption pattern** (per tool, non-breaking): add config `llm_source: hub|direct` (or `llm_hub_enabled` bool) + `llm_hub_url`, default = current behavior; when enabled, try the hub first (`model: auto`) and fall through to the tool's existing direct path on any failure. The hub also speaks **Ollama-native** (`/api/tags`, `/api/chat`, `/api/generate`) so Ollama-based tools adopt it by changing one URL, and unknown model names route as `auto`.

**Adoption status + full per-tool guide: `C:\QIH\docs\QI_LLM_Hub.md`.** Live 2026-07-02: Maia, Naya, Gamez/WC2026, TUBESCOUT (pre-dating). Ready-to-flip: EasyFlow (extension UI card), CogniBase (provider entry added), M2V/PersonalSong/MQ/MailBrain/MapSnap/AutoPDF/ClaudeVoice (one-URL flips via the Ollama shim).

> **Verified 2026-08-07 against `GET /hub/usage`:** LotteryWiz (7 calls) and Retirement
> Analyzer (12 calls) are **already live**, not "ready to flip". Per-app fallback posture —
> which tools degrade gracefully when NEXUS is down and which hard-fail — is recorded in
> **`QI_Connectivity_Map.md` §5**. LotteryWiz currently has **no** fallback.

---

## Shared Infrastructure

| Concern | Today | Future |
|---|---|---|
| **Database** | SQLite per project (maia.db, nexus.db…) | Federated or shared PostgreSQL |
| **LLM Chain** | Maia owns chain; NEXUS owns eval | All query NEXUS for LLM selection |
| **Auth** | None — all local | Shared auth token when unified |
| **Message Bus** | None | Redis Pub/Sub or SQLite queue |
| **External Access** | 16 Cloudflare tunnels → 22 public hosts, all behind the QI Gate (Caddy `:9040` + auth `:9041`). Inventory: `QI_Connectivity_Map.md`. | Cloudflare Access (MFA) on every host — already live on `hive` |
| **Auth** | QI Gate: one account fronts the estate, with per-host scoping (2026-08-07). `C:\QIH\engine\gate\README.md`. | MFA / SSO via Cloudflare Access |
| **NSSM Services** | All services prefixed `QI_`. Standardized binary: `C:\QIH\engine\bin\nssm.exe`. Registry: `QI_Service_Registry.md`. | — |

---

*This file is the human-readable view of `qi_registry.json`.*
*The Python module `qi_registry.py` provides programmatic access.*
*Always keep both in sync when adding new projects or changing ports.*

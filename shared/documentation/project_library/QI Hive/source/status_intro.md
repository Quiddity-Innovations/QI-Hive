# QI Hive — The Brain, Dashboard & Agent Fabric of the Quiddity Innovations Ecosystem

## What is QI Hive?

QI Hive is the **meta-platform** of Quiddity Innovations — the orchestration hub that every other QI project plugs into. It is not a leaf product like Maia, Naya, or NEXUS; it is the nervous system that connects, remembers, governs, and operates all 24 of them at once.

QI Hive is four cooperating layers living under `C:\QIH\`:

1. **QI Brain** — a FastAPI knowledge substrate (port 9011) backed by SQLite + ChromaDB that records every decision, feature, session, and project state across the ecosystem, and exposes them as 12 MCP tools.
2. **The Hive Dashboard** — a FastAPI + AdminLTE web console (port 8600) that is the single pane of glass: Mission Control, health checks, kanban board, compliance, LLM usage/cost, the Documentation Brain, the War Room, and per-project Status pages (this page).
3. **The Agent Fabric** — eight specialist sub-agents (architect, builder, inspector, ops, scout, scribe, tester, librarian) dispatched by the main Claude thread under a standing Dispatch Protocol, plus the CoWork dispatch + auto-apply pipeline.
4. **The Governance Layer** — the ecosystem registry, standards, the Six Laws, and the QI_ service + tunnel inventory that bind all projects to one contract.

## The Problem We Solve

- the owner runs **24+ parallel projects** on one Windows machine — each with NSSM services, git repos, ports, logs, tunnels, and documentation. Remembering what is running, what broke, and what is next is cognitive overload that no single backlog can hold.
- **Knowledge evaporates between sessions.** Decisions made in one Claude session are forgotten in the next, and a pattern built in Maia never reaches Naya. The Brain makes memory durable and cross-project.
- **Services crash and need an autonomous restart** — but Windows UAC prompts block any unattended loop. The elevation broker solves the UAC-in-the-loop problem.
- **Projects drift from standards** silently — wrong ports, missing `/health`, stale registry entries. The Inspector enforces the Six Laws continuously instead of catching drift at demo time.
- **Claude Code is expensive** and there was no native tool to parse session JSONL into per-model, per-project cost. The usage layer reads the logs directly — no API key.
- **Cross-project task coordination** had no home — the kanban board and CoWork dispatch channel give it one.

## Our Approach

QI Hive is deliberately **server-rendered, file-and-SQLite simple, and locally autonomous**. No SPA, no cloud dependency, no paid API for its core loop. Each dashboard page is a Python function returning HTML; the Brain is a single FastAPI app over SQLite + a local Chroma store embedded by a local Ollama/nomic model. Everything degrades gracefully — if the Brain is offline the dashboard falls back to local JSON; if Chroma is down the SQL catalog still writes.

The contract between QI Hive and the leaf projects is the **registry** (`qi_registry.json`): ports, paths, statuses, and integration contracts. Build for today as an independent app, design for the unified platform tomorrow — that is the core premise the whole ecosystem is built on.

## Who Uses QI Hive?

| Role | How they interact |
|---|---|
| **Developer (the owner)** | Browser at `http://localhost:8600` — Mission Control, health, kanban, usage, compliance, Documentation Brain, War Room |
| **Claude Code (main thread)** | The dispatcher — calls QI Brain MCP tools (`qi_get_context`, `qi_log_session`…) and dispatches the hive-* sub-agents per the Dispatch Protocol |
| **Hive sub-agents** | architect / builder / inspector / ops / scout / scribe / tester / librarian — invoked via `Agent(subagent_type=hive-<role>)` |
| **Every leaf project** | Registers in `qi_registry.json`, exposes `/health` + `/version` + `/info`, and pushes state to the Brain at session end |
| **CoWork (Claude Work)** | Posts session reports + dispatches to the Brain over HTTP `/api/inbox` or by dropping JSON in the ingest inbox |
| **QI_Elevate broker** | Runs whitelisted admin commands (service restarts, process kills) as LocalSystem on behalf of any agent |

## Current Build Status (June 2026)

QI Hive is in **active operations** — dispatch/compliance pipeline hardening, dashboard UX polish, and the Documentation Brain. All core services are live under NSSM.

| Area | Status |
|---|---|
| Hive Dashboard on port 8600 (`QI_Dashboard`) | ✅ Live |
| QI Brain API on port 9011 (`QI_BrainAPI`) — 12 MCP tools, SQLite + ChromaDB | ✅ Live |
| Mission Control monitoring board (renamed from Hive) | ✅ Live |
| Ecosystem health check — registry-driven, all projects probed | ✅ Live |
| Kanban task board (SortableJS, CRUD via `/api/tasks`) | ✅ Live |
| Compliance page + Inspector (auto-fix, 4-hour + nightly deep) | ✅ Live |
| LLM usage & cost page — daily/project/model breakdowns from JSONL | ✅ Live |
| Documentation Brain — 921 docs indexed, search + Plex graph + split view | ✅ Live |
| QI_Elevate broker + per-project service control (`qi_service.py`) | ✅ Live |
| `QI_HiveIngest` — file inbox → Brain ingestion | ✅ Live |
| Brain poller — pulls project state files + git on a schedule | ✅ Live |
| CoWork Dispatch board — approve/decline/discuss, idempotent | ✅ Live |
| Static named Cloudflare tunnels on `quiddityinnovations.com` | ✅ Live |
| Agent Fabric — 8 hive-* sub-agents + Dispatch Protocol | ✅ Live |
| War Room — multi-agent text chat (`warroom_messages`) | ⚠️ Stage 0 (text only) |
| `QI_HiveApply` auto-apply pipeline (approved dispatch → builder) | ⚠️ Phase 1 (inbox-fallback) |
| Agent growth loop (`agent_growth_log` accumulating profiles) | ⚠️ Built, not yet populated |
| Caddy `qi.local` LAN reverse proxy (`QI_Caddy`) | ⚠️ Verified, install pending |
| Per-product NSSM naming (named UAC consent popups) | 🗓️ Armed for 2026-06-27 |
| Avatars + voice for War Room agents (Phase N Stages 1-4) | 🗓️ Planned |

## The QI Brain

The Brain (`engine/brain/api.py`, port 9011) is the ecosystem's durable memory. It stores **491 decisions, 394 features, 564 sessions, 239 project-state snapshots, and 921 indexed docs** across 24 projects in `data/qi_brain.db`, with semantic search over four ChromaDB collections (`qi_decisions`, `qi_features`, `qi_sessions`, `qi_docs`). It exposes 12 MCP tools (`qi_get_context`, `qi_log_decision`, `qi_log_feature`, `qi_log_session`, `qi_update_project_state`, `qi_search_memory`, `qi_get_ecosystem_snapshot`, `qi_explain`, and more), a background poller, a feature-propagation engine, the CoWork dispatch channel, agent heartbeats, and the War Room. The MCP server (`mcp.py`) is a thin stdio bridge — all logic lives in the FastAPI app. Embeddings use a local Ollama `nomic-embed-text` model, so no cloud API is required.

## The Agent Fabric

Eight specialist sub-agents turn Claude Code from a single assistant into a team. The **main thread is the dispatcher**; it routes each task to a role via `Agent(subagent_type=hive-<role>)`:

- **hive-architect** (Opus) — designs systems, ADRs, breaking-change analysis. Must surface best-practice divergence (Law 6).
- **hive-builder** (Sonnet) — writes the code from an architect's plan.
- **hive-inspector** (Sonnet) — read-only review + standards/compliance gate.
- **hive-ops** (Haiku) — service triage, logs, NSSM restarts, orphan kills.
- **hive-scout** (Haiku) — fast research, API/vendor/news lookups.
- **hive-scribe** (Haiku) — session summaries, minutes, README/CHANGELOG, .docx.
- **hive-tester** (Haiku) — cross-project API/health/smoke/regression tests.
- **hive-librarian** — finds, curates, and traverses the documentation index.

The standing workflows (design → build → inspect → scribe) and anti-patterns are codified in `DISPATCH_PROTOCOL.md`.

## The Ecosystem Registry & The Six Laws

`C:\QIH\ecosystem\` is the governance heart. `qi_registry.json` is the single source of truth for ports, paths, statuses, and integration contracts; `qi_validator.py` checks compliance; `qi_new_project.py` scaffolds a compliant project in one command. The **Six Laws** (`QI_Architecture_Principles.md`) are the constitution:

- **Law 1** — The registry is the source of truth.
- **Law 2** — Every module must honor the contract (`/health`, `/version`, `/info` + the standard response envelope).
- **Law 3** — Independence with declared dependencies — every project runs alone; cross-project calls degrade gracefully.
- **Law 4** — API contract first, implementation second; never break a contract without a migration.
- **Law 5** — One registry, always current — update it before the code.
- **Law 6** — Owner override + proactive best-practice surfacing — the owner's calls are final; agents must flag divergence from industry norms.

## Services & Tunnels

QI Hive owns the core QI_ services: `QI_Dashboard` (8600), `QI_BrainAPI` (9011), `QI_Elevate`, `QI_HiveIngest`, `QI_HiveApply`, `QI_HiveInspectorDrain`, and `QI_DashboardTunnel`. All QI services are prefixed `QI_`, registered in `QI_Service_Registry.md`, and run via a standardized NSSM at `C:\QIH\engine\bin\nssm.exe`. Since 2026-06-20 every public service is reachable via a permanent static Cloudflare named tunnel on `quiddityinnovations.com` (the Hive itself at `hive.quiddityinnovations.com`), managed from `engine/tunnels/`.

## The Vision

QI Hive is the bridge from a constellation of independent apps to one **unified QI platform**. Every leaf project is built today as a standalone app and designed as a future module behind the same API contract — so the migration from distributed HTTP calls to in-process function calls is a one-line change per call site. The Brain remembers, the Dashboard reveals, the Agent Fabric acts, and the Governance Layer keeps all 24 projects honest. As avatars and voice land in the War Room, QI Hive becomes a true agentic operations room, not just a console.

---
*This page is editable at `C:\QIH\INTRO\status_intro.md` — save and click Refresh to update.*

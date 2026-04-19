# QI Ecosystem Plan 001 — The QI Brain: One Shared Intelligence Across All Agents and Projects

**Plan Number:** 001  
**Status:** APPROVED — PENDING IMPLEMENTATION  
**Created:** 2026-04-18  
**Author:** Claude (QI Orchestrator session) + Renne Santiago  
**Classification:** Foundational Architecture — affects ALL QI projects  
**Next Plan:** QI_Ecosystem_Plan_002 (will cover implementation phase 1 results)

---

## Table of Contents

1. [Origin & Context](#1-origin--context)
2. [The Problem Statement](#2-the-problem-statement)
3. [Current Ecosystem State (as of 2026-04-18)](#3-current-ecosystem-state-as-of-2026-04-18)
4. [The Vision: One Brain, Many Agents](#4-the-vision-one-brain-many-agents)
5. [Architectural Decisions](#5-architectural-decisions)
6. [The QI Brain — Full Architecture](#6-the-qi-brain--full-architecture)
7. [Database Schema — Complete](#7-database-schema--complete)
8. [LLM Provider Layer](#8-llm-provider-layer)
9. [ChromaDB Semantic Memory Layer](#9-chromadb-semantic-memory-layer)
10. [The Feature Propagation Engine](#10-the-feature-propagation-engine)
11. [The MCP Server — Claude's Interface](#11-the-mcp-server--claudes-interface)
12. [FastAPI Layer — Dashboard & Inter-Service](#12-fastapi-layer--dashboard--inter-service)
13. [Bootstrap Plan — Seeding the Brain](#13-bootstrap-plan--seeding-the-brain)
14. [Session Protocol Changes (CLAUDE.md)](#14-session-protocol-changes-claudemd)
15. [Implementation Order](#15-implementation-order)
16. [Parallel Work: Python Migration Plan](#16-parallel-work-python-migration-plan)
17. [Future Vision — The Road to a Datacenter](#17-future-vision--the-road-to-a-datacenter)
18. [Constraints & Risk Register](#18-constraints--risk-register)
19. [Open Questions & Decisions Log](#19-open-questions--decisions-log)

---

## 1. Origin & Context

### 1.1 How This Plan Was Born

This plan emerged from a cross-session architectural gap discovered on 2026-04-18. Renne was simultaneously working in a Claude session on EasyFlow and a Claude session on QI Orchestrator (Dashboard). The EasyFlow session produced a peer-agent handoff document that exposed a fundamental weakness in how QI's multiple Claude instances operate: **they share no knowledge with each other in real time, and architectural decisions made in one project disappear entirely from every other project's awareness.**

The EasyFlow session produced four significant architectural decisions that night:

1. **Extension-First Principle**: All public EasyFlow features must fit Chrome Extension architecture. Three escape hatches defined: external service, desktop companion, cloud backend.
2. **Deletion Quarantine Safety Net (v1.2)**: 3-tier risk labels, opt-out, Gmail-Trash fallback, user-configurable hold periods.
3. **AI Roadmap Tiering**: Tier 1 shipped, Tier 2+4 in v1.2, Tier 3 (RAG) moved to private experiment, Agent era = v1.4+.
4. **Architecture Clarification**: EasyFlow = orchestrator, Ollama = external user-installed LLM, Gmail = data source. No bundled LLMs.

By morning, no other Claude session knew any of this.

### 1.2 The Handoff Document

The EasyFlow Claude produced a structured briefing for the Orchestrator Claude. Key excerpt of what was proposed:

> *"My vision for QI Orchestrator: 'One common brain where every Claude instance knows about every project, while maintaining its individual project context.'"*

Three channels identified:
1. **Shared knowledge store** (persistent, queryable) — the brain
2. **Session-start protocol** (mandatory onboarding) — every Claude reads brain on boot
3. **Write-back protocol** (decisions persist) — every Claude writes back before session ends

### 1.3 Renne's Clarifications and Expansions

Renne then expanded the vision significantly:

- Projects must remain **independent**. The brain is infrastructure around them, not inside them.
- Maia's tech stack is not to be touched. The brain borrows Maia's *patterns*, not its code.
- **No hardcoded LLMs anywhere.** All provider configuration lives in the database. LLMs are updated monthly — the system must accommodate swapping models without code changes.
- The brain should use **SQLite for configuration and structured facts**, and **ChromaDB for semantic/vector memory** — both, because they solve different problems.
- New ideas flowing from one agent or project should be automatically **evaluated for applicability** to other projects. The brain should propose enhancements, not just store them.
- Long-term vision: voice interfaces, avatars for Claude and all agents, migration to a dedicated datacenter where the QI Orchestrator is the boss of everything.

---

## 2. The Problem Statement

### 2.1 The Isolation Problem

Each Claude session today:
- Reads its own project's `MEMORY.md` on startup
- Reads the global `CLAUDE.md` (rules and conventions only — no current state)
- Has no awareness of what any other session is doing or has decided
- Writes nothing persistent to any shared store on exit (except the Session Summaries `.docx`)
- Cannot search past sessions semantically

The Session Summaries folder (`C:\UNIVERSAL\DOCUMENTATION\Session_Summaries\`) is the only shared write destination. But it's a collection of Word documents — not queryable by any tool, not semantically searchable, not structured for machine consumption.

### 2.2 The Propagation Gap

When a significant architectural decision is made in one project:
- **Path today**: Decision is made → maybe documented in session summary → maybe Renne remembers to tell the next Claude → maybe it propagates.
- **Path needed**: Decision is made → logged to shared brain → automatically evaluated for cross-project impact → surfaced to relevant sessions at startup.

### 2.3 The Evaluation Gap

No mechanism exists today to ask: *"Given that EasyFlow just invented Deletion Quarantine — does Naya (which manages files) need this pattern too?"* That evaluation requires:
- Knowledge of what was just invented (semantic description)
- Knowledge of what other projects do (project state + tech stack)
- An LLM to reason about fit
- A structured way to surface the recommendation

None of this exists. This plan builds it.

### 2.4 The Agent Cooperation Gap

QI has multiple types of agents:
- Claude instances (this and other sessions)
- OpenClaw agents (Tasuke, Kaze, Sentry, Yubin, Koe)
- Future: voice agents, avatar agents, specialized research agents

None of these can currently share knowledge or coordinate through a common substrate. They are fully isolated silos. The brain must serve all of them, not just Claude.

---

## 3. Current Ecosystem State (as of 2026-04-18)

### 3.1 Active Projects

| Project | Path | Port(s) | Status | Notes |
|---|---|---|---|---|
| Maia | `C:\QI` | 8001 (API), 7860 (Gradio) | active_production | Multi-channel AI: LINE/Telegram/Messenger. MaiaBot + MaiaTunnel + MaiaDemoTunnel via NSSM. |
| NEXUS | `C:\NEXUS` | 8010 (API), 7880 (UI) | active_development | AI orchestration backbone. 10 provider adapters. Parallel + chain dispatch. |
| Naya | `C:\NAYA` | 8002 (API), 7861 (UI) | active_development | Personal AI for Renne via Telegram. Absorbed FileHQ. LAN-only. |
| EasyFlow | `C:\EasyFlow` | 8550 (local) | active_development | Chrome Extension + Flask local dashboard. Gmail API + Apps Script automation. |
| OpenClaw | `C:\OC` | WSL | active_production | 6 autonomous agents. Tasuke, Kaze, Sentry, Yubin, Koe (Seiri cancelled). |
| QI Orchestrator | `C:\UNIVERSAL\dashboard` | 9000 | active_development | Multi-project management dashboard. 6-tab template per project. Cloudflare tunnel. |
| MQ | `C:\MQ` | 8500 | active_development | Maia Quiddam — autonomous social media persona. |
| FileHQ | `C:\NAYA\filehq` | 8000 | merged_into_naya | Merged into Naya as file engine module. |

### 3.2 Shared Infrastructure (Today)

| Component | Location | Purpose |
|---|---|---|
| `qi_registry.json` | `C:\UNIVERSAL\ECOSYSTEM\` | Machine-readable project registry (ports, relationships) |
| `QI_Ecosystem_Map.md` | `C:\UNIVERSAL\ECOSYSTEM\` | Human-readable ecosystem map |
| `QI_Standards.md` | `C:\UNIVERSAL\ECOSYSTEM\` | Naming, folder, code conventions |
| `QI_Architecture_Principles.md` | `C:\UNIVERSAL\ECOSYSTEM\` | The Five Laws — architecture constitution |
| `qi_validator.py` | `C:\UNIVERSAL\ECOSYSTEM\` | Compliance checker |
| `qi_new_project.py` | `C:\UNIVERSAL\ECOSYSTEM\` | New project wizard |
| Global `CLAUDE.md` | `C:\Users\renne\.claude\` | Standing rules for all Claude sessions |
| Session Summaries | `C:\UNIVERSAL\DOCUMENTATION\Session_Summaries\` | Session history (Word docs) |
| `sqlite-maia` MCP | global `.claude.json` | SQLite access to maia.db |
| `sqlite-naya` MCP | global `.claude.json` | SQLite access to naya.db |

### 3.3 What NEXUS Already Has (Critical Reference)

NEXUS has the best multi-LLM infrastructure in the ecosystem:
- Abstract base class `NexusProvider` with clean `generate(prompt, system_prompt) → ProviderResponse` contract
- One file per provider in `C:\NEXUS\core\providers\`
- Providers: Ollama, OpenAI (Codex), Gemini, Groq, Mistral, Grok, Cloudflare AI, Azure OpenAI, Anthropic Claude, AWS Bedrock, Generic OpenAI-compatible
- Config loaded from `nexus.json` — no hardcoding
- Three dispatch modes: parallel (asyncio.gather), chain (sequential improvement), stream (as_completed)
- The Brain will replicate this pattern exactly — same architecture, standalone copy, config from DB instead of JSON

### 3.4 Ollama Models Available (2026-04-18)

| Model | Size | Best Use |
|---|---|---|
| gemma4:31b | 19 GB | Highest quality reasoning, cross-project analysis |
| gemma4:26b | 17 GB | High quality, slightly faster |
| gemma4:latest | 9.6 GB | Good balance of quality and speed |
| qwen3:8b | 5.2 GB | Fast reasoning, feature evaluation |
| deepseek-r1:8b | 5.2 GB | Reasoning with chain-of-thought |
| gpt-oss-20b | 11 GB | Large general purpose |
| gemma3:27b | 17 GB | High quality |
| llama3.1:8b | 4.9 GB | General purpose, well-tested |
| qwen3-vl:32b | 20 GB | Vision + language (future: avatar/image tasks) |
| qwen3-vl:8b | 6.1 GB | Vision + language, fast |
| qwen2.5:7b | 4.7 GB | Fast, reliable |
| qwen3:4b | 2.5 GB | Fastest — summaries, simple tasks |
| kimi-k2.5:cloud | — | Cloud model |

**Default Brain LLM assignments:**
- Feature evaluation: `qwen3:8b` (fast, accurate, local, free)
- Deep reasoning / cross-project analysis: `gemma4:latest`
- Session summaries: `qwen3:4b` (fastest)
- Embeddings: `nomic-embed-text` (Ollama) or `all-MiniLM-L6-v2` (sentence-transformers fallback)

---

## 4. The Vision: One Brain, Many Agents

### 4.1 Core Vision Statement

> *"One common brain where every Claude instance knows about every project, while maintaining its individual project context."* — Renne Santiago, 2026-04-18

Every agent in the QI ecosystem — every Claude session, every OpenClaw agent, every future voice agent or avatar agent — reads from and writes to a single shared knowledge substrate. Projects remain fully independent in their code and operation. The brain is purely additive infrastructure layered around them, not inside them.

### 4.2 What "Knowing" Means

When a Claude session opens on Maia tomorrow, it "knows":
- What was decided in EasyFlow last night (cross-cutting decisions)
- That Naya adopted Deletion Quarantine based on EasyFlow's design (feature propagation)
- That the Python migration is scheduled for this morning (ecosystem_state)
- That NEXUS is healthy but had a latency spike yesterday (project_state)
- The last 20 relevant things that happened across all projects, semantically ranked to what matters for Maia right now

It knows this because it called `qi.get_context("maia")` on startup. The call takes under 500ms. The result is silently internalized. The session begins already connected to the ecosystem.

### 4.3 What "Cooperating" Means

When EasyFlow invents Deletion Quarantine:
- The brain is told via `qi.log_feature(...)`
- The brain evaluates — using a local LLM — whether Naya, Maia, NEXUS, or any other project could benefit
- Relevant recommendations appear in those projects' next session startup context
- Claude in Naya can accept, adapt, or decline — and that decision is logged back into the brain
- Over time, the brain accumulates a history of what was tried, what was adopted, what was rejected — and why

### 4.4 The Long-Term Ambition

The brain is not just a knowledge store. It is the nervous system of a growing intelligence network. Today it runs on a gaming desktop. Eventually:
- It runs on a collection of dedicated servers
- It serves hundreds of agents simultaneously
- It has voice and avatar interfaces
- It reasons proactively — not just when asked
- It proposes architecture changes, flags contradictions across projects, anticipates blockers
- The Orchestrator is the boss: the entity that coordinates everything, knows everything, and keeps the ecosystem coherent

---

## 5. Architectural Decisions

The following decisions were made during this conversation and are now locked:

| # | Decision | Rationale |
|---|---|---|
| AD-001 | Use SQLite for all structured data (config, decisions, state, features, session log) | Fast, reliable, already installed, queryable, ACID-compliant |
| AD-002 | Use ChromaDB for all semantic/vector memory | Different retrieval pattern than SQL; needed for "find anything related to X" across unstructured text |
| AD-003 | Both SQLite and ChromaDB — not either/or | They solve different problems. SQLite for "what was decided about deletion quarantine?" ChromaDB for "find me everything related to safety patterns across all projects." |
| AD-004 | Replicate NEXUS provider pattern exactly — do not reuse NEXUS code | Brain must be self-contained and resilient to NEXUS being down. Same pattern, standalone copy. |
| AD-005 | Zero hardcoded LLM configuration anywhere | All model names, URLs, keys (by reference), roles, priorities in `llm_providers` table. Swappable without code changes. |
| AD-006 | MCP server is stdio — no port needed | Spawned by Claude CLI as subprocess. Registered globally in `.claude.json`. |
| AD-007 | FastAPI at port 9010 | HTTP interface for Dashboard Brain tab and inter-service calls. Within 9000-9099 QI Orchestration block per qi_registry.json. |
| AD-008 | Projects stay independent — brain is additive only | No project code is modified. No project depends on the brain. Brain depends on nothing (except Ollama for LLMs). |
| AD-009 | Feature Propagation Engine uses async LLM evaluation | When a feature is logged, LLM evaluates fit for each active project in background. Non-blocking. |
| AD-010 | NEXUS relay provider included | Brain can call NEXUS /synthesize for multi-voice synthesis when available. Falls back to direct Ollama. |
| AD-011 | Brain config entirely in DB | `brain_config` table is the source of truth for all behavioral settings. No JSON files, no .env for non-secrets. |
| AD-012 | API keys stored in environment variables only — never in DB | `llm_providers.api_key_env` stores the env var NAME, not the value. Secrets remain in `.env` files per project pattern. |

---

## 6. The QI Brain — Full Architecture

### 6.1 Location

```
C:\UNIVERSAL\ECOSYSTEM\qi_brain\
```

This is the correct location: the ECOSYSTEM directory is the shared neutral ground between all projects.

### 6.2 Directory Structure

```
C:\UNIVERSAL\ECOSYSTEM\qi_brain\
│
├── qi_brain.db                  ← SQLite: ALL structured data
│   (config, decisions, features, state, session log, LLM providers)
│
├── qi_memory\                   ← ChromaDB: semantic vector memory
│   ├── qi_sessions\             (collection: session summary text)
│   ├── qi_decisions\            (collection: decisions mirrored from SQLite)
│   ├── qi_features\             (collection: feature descriptions)
│   └── qi_docs\                 (collection: documentation, CLAUDE.md, standards)
│
├── qi_brain_mcp.py              ← stdio MCP server — Claude's interface
│   (9 named tools — the only way Claude talks to the brain)
│
├── qi_brain_api.py              ← FastAPI :9010 — Dashboard + inter-service REST
│   (mirrors MCP tools as HTTP endpoints + admin endpoints)
│
├── providers\                   ← LLM provider adapters (NEXUS pattern)
│   ├── base.py                  (BrainProvider abstract base class)
│   ├── ollama.py                (Direct Ollama — always available)
│   ├── openai_compat.py         (OpenAI + any OpenAI-compatible API)
│   ├── anthropic.py             (Anthropic Claude API)
│   ├── groq.py                  (Groq — fast inference)
│   ├── mistral.py               (Mistral AI)
│   ├── nexus_relay.py           (Calls NEXUS /synthesize → Ollama fallback)
│   ├── cloudflare.py            (Cloudflare Workers AI)
│   └── __init__.py              (load_providers(role="feature_eval") from DB)
│
├── feature_engine.py            ← Cross-project feature evaluation (async)
├── memory_store.py              ← ChromaDB read/write abstraction layer
├── router.py                    ← LLM routing by role (reads llm_providers table)
├── bootstrap.py                 ← One-time: schema + seed data + ingest all docs
├── schema.sql                   ← Canonical DB schema (source of truth)
│
├── secrets\
│   └── qi_brain.env             ← API keys (gitignored, per QI standard)
│
└── tests\
    ├── test_providers.py
    ├── test_feature_engine.py
    └── test_mcp_tools.py
```

### 6.3 Data Flow Overview

```
┌─────────────────────────────────────────────────────────┐
│                    CLAUDE SESSIONS                       │
│  Maia Claude  │  EasyFlow Claude  │  NEXUS Claude  │... │
│      ↓ qi.get_context()           ↑ qi.log_decision()   │
└───────────────────────────────────────────────────────── ┘
                          │
                  ┌───────┴────────┐
                  │  qi_brain_mcp  │  (stdio MCP server)
                  │   9 tools      │
                  └───────┬────────┘
                          │
          ┌───────────────┴───────────────┐
          │         QI BRAIN CORE         │
          │                               │
          │  ┌──────────┐  ┌──────────┐  │
          │  │ qi_brain  │  │qi_memory │  │
          │  │  .db      │  │(ChromaDB)│  │
          │  │ (SQLite)  │  │          │  │
          │  └──────────┘  └──────────┘  │
          │                               │
          │  ┌────────────────────────┐   │
          │  │  Feature Engine        │   │
          │  │  (async LLM eval)      │   │
          │  └────────────────────────┘   │
          │                               │
          │  ┌────────────────────────┐   │
          │  │  LLM Router            │   │
          │  │  (config from DB)      │   │
          │  └────────────────────────┘   │
          └───────────────────────────────┘
                          │
                  ┌───────┴────────┐
                  │qi_brain_api    │  ← FastAPI :9010
                  │:9010           │
                  └───────┬────────┘
                          │
        ┌─────────────────┴──────────────────┐
        │                                    │
┌──────────────┐                    ┌──────────────────┐
│  QI Dashboard│                    │  OpenClaw Agents │
│  Brain Tab   │                    │  (future HTTP)   │
│  :9000       │                    │                  │
└──────────────┘                    └──────────────────┘
```

---

## 7. Database Schema — Complete

```sql
-- ============================================================
-- QI BRAIN DATABASE SCHEMA
-- File: C:\UNIVERSAL\ECOSYSTEM\qi_brain\schema.sql
-- Version: 1.0.0
-- Created: 2026-04-18
-- ============================================================

-- ── LLM PROVIDERS ─────────────────────────────────────────
-- All LLM configuration lives here. Zero hardcoding anywhere.
CREATE TABLE IF NOT EXISTS llm_providers (
    id              TEXT PRIMARY KEY,
    -- Examples: 'ollama-qwen3-8b', 'groq-llama3', 'nexus-relay', 'openai-gpt4o'
    name            TEXT NOT NULL,
    type            TEXT NOT NULL,
    -- 'ollama' | 'openai_compat' | 'anthropic' | 'groq' | 'mistral'
    -- | 'cloudflare' | 'nexus_relay' | 'azure_openai' | 'aws_bedrock'
    base_url        TEXT,
    -- For local providers: 'http://127.0.0.1:11434'
    -- For nexus_relay: 'http://127.0.0.1:8010'
    model           TEXT NOT NULL,
    api_key_env     TEXT,
    -- Name of environment variable holding API key — NEVER the key itself
    -- e.g. 'GROQ_API_KEY', 'OPENAI_API_KEY'
    enabled         INTEGER DEFAULT 1,
    priority        INTEGER DEFAULT 0,
    -- Lower priority = tried first. Multiple providers per role = fallback chain.
    use_for         TEXT DEFAULT '["all"]',
    -- JSON array: ['reasoning', 'summary', 'feature_eval', 'embedding', 'synthesis', 'all']
    timeout_seconds INTEGER DEFAULT 60,
    config_json     TEXT DEFAULT '{}'
    -- Additional provider-specific settings (temperature, max_tokens, etc.)
);

-- ── BRAIN CONFIGURATION ───────────────────────────────────
-- All behavioral settings in DB. Change behavior without touching code.
CREATE TABLE IF NOT EXISTS brain_config (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    type        TEXT DEFAULT 'string',
    -- 'string' | 'int' | 'float' | 'bool' | 'json'
    description TEXT,
    category    TEXT,
    -- 'llm' | 'memory' | 'features' | 'session' | 'api' | 'ui'
    updated_ts  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ── DECISIONS ─────────────────────────────────────────────
-- Every architectural, standard, feature, and priority decision made across
-- all projects. Cross-cutting decisions propagate to all sessions at startup.
CREATE TABLE IF NOT EXISTS decisions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      TEXT NOT NULL,
    type            TEXT NOT NULL,
    -- 'architecture' | 'standard' | 'feature' | 'deprecation'
    -- | 'priority' | 'pattern' | 'integration'
    title           TEXT NOT NULL,
    body            TEXT NOT NULL,
    ts              DATETIME DEFAULT CURRENT_TIMESTAMP,
    cross_cutting   INTEGER DEFAULT 0,
    -- 1 = surfaces to ALL projects at session start
    superseded_by   INTEGER REFERENCES decisions(id),
    feature_id      INTEGER REFERENCES features(id),
    -- Set if this decision was born from a feature adoption
    tags            TEXT DEFAULT '[]'
    -- JSON array of searchable tags
);

-- ── PROJECT STATE ─────────────────────────────────────────
-- Rolling snapshot of each project. Updated by each project's Claude session.
-- Not a history table — one row per project, updated in place.
CREATE TABLE IF NOT EXISTS project_state (
    project_id      TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    status          TEXT DEFAULT 'unknown',
    -- 'active_production' | 'active_development' | 'paused' | 'blocked' | 'unknown'
    current_focus   TEXT,
    -- What is being built right now (plain English, 1-2 sentences)
    blockers        TEXT,
    -- What is blocking progress (null = none)
    last_session    DATETIME,
    health          TEXT DEFAULT 'unknown',
    -- 'healthy' | 'degraded' | 'down' | 'unknown'
    tech_stack      TEXT DEFAULT '[]',
    -- JSON array: primary technologies (e.g. ["FastAPI", "SQLite", "Ollama", "NSSM"])
    llm_providers   TEXT DEFAULT '[]',
    -- JSON array: which LLM providers this project uses
    open_tasks      TEXT DEFAULT '[]',
    -- JSON array of current open task titles (top 5)
    updated_ts      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ── FEATURE REGISTRY ──────────────────────────────────────
-- New ideas, patterns, and techniques discovered anywhere in the ecosystem.
-- Anything one project invents that might benefit another lives here.
CREATE TABLE IF NOT EXISTS features (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    discovered_in   TEXT NOT NULL,
    -- project_id where first invented/discovered
    discovered_by   TEXT DEFAULT 'claude',
    -- 'claude' | 'renne' | 'openclaw' | agent_name
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    category        TEXT,
    -- 'ui' | 'api' | 'llm' | 'architecture' | 'security'
    -- | 'performance' | 'pattern' | 'ux' | 'data'
    tags            TEXT DEFAULT '[]',
    ts              DATETIME DEFAULT CURRENT_TIMESTAMP,
    status          TEXT DEFAULT 'pending_eval',
    -- 'pending_eval' | 'evaluated' | 'adopted_by_all' | 'closed'
    chroma_id       TEXT
    -- ChromaDB document ID for semantic retrieval
);

-- ── FEATURE EVALUATIONS ───────────────────────────────────
-- LLM-generated assessment of whether a feature from one project
-- is relevant to another project.
CREATE TABLE IF NOT EXISTS feature_evaluations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_id      INTEGER NOT NULL REFERENCES features(id),
    target_project  TEXT NOT NULL,
    relevance_score REAL,
    -- 0.0 (irrelevant) to 1.0 (must adopt)
    recommendation  TEXT,
    -- 'adopt' | 'adapt' | 'skip' | 'discuss'
    reasoning       TEXT,
    -- 2-3 sentence LLM-generated explanation
    evaluated_by    TEXT,
    -- 'llm:qwen3:8b' | 'llm:gemma4:latest' | 'claude' | 'renne'
    ts              DATETIME DEFAULT CURRENT_TIMESTAMP,
    decision        TEXT DEFAULT 'pending'
    -- 'pending' | 'accepted' | 'rejected' | 'deferred'
);

-- ── ECOSYSTEM STATE ───────────────────────────────────────
-- Global and per-project key-value facts. Fast lookup for current state.
CREATE TABLE IF NOT EXISTS ecosystem_state (
    key             TEXT PRIMARY KEY,
    value           TEXT,
    project_id      TEXT,
    -- NULL = ecosystem-wide fact
    updated_ts      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ── SESSION LOG ───────────────────────────────────────────
-- Audit trail: what happened in each session, across all projects.
CREATE TABLE IF NOT EXISTS session_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      TEXT NOT NULL,
    session_ts      DATETIME DEFAULT CURRENT_TIMESTAMP,
    summary         TEXT,
    decisions_count INTEGER DEFAULT 0,
    features_logged INTEGER DEFAULT 0,
    files_modified  TEXT DEFAULT '[]'
    -- JSON array of file paths modified in this session
);

-- ── PROJECT LINKS ─────────────────────────────────────────
-- Dynamic relationships between projects, beyond what qi_registry.json captures.
-- Registry captures static topology. This captures evolving relationships.
CREATE TABLE IF NOT EXISTS project_links (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    from_project TEXT NOT NULL,
    to_project   TEXT NOT NULL,
    link_type    TEXT,
    -- 'uses' | 'feeds_data_to' | 'inspired_by' | 'shares_pattern'
    -- | 'migrating_from' | 'depends_on' | 'replaces'
    note         TEXT,
    ts           DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ── INDEXES ───────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_decisions_project ON decisions(project_id);
CREATE INDEX IF NOT EXISTS idx_decisions_cross ON decisions(cross_cutting, ts);
CREATE INDEX IF NOT EXISTS idx_decisions_ts ON decisions(ts DESC);
CREATE INDEX IF NOT EXISTS idx_features_project ON features(discovered_in);
CREATE INDEX IF NOT EXISTS idx_features_status ON features(status);
CREATE INDEX IF NOT EXISTS idx_feature_evals_target ON feature_evaluations(target_project, decision);
CREATE INDEX IF NOT EXISTS idx_feature_evals_feature ON feature_evaluations(feature_id);
CREATE INDEX IF NOT EXISTS idx_session_log_project ON session_log(project_id, session_ts DESC);
CREATE INDEX IF NOT EXISTS idx_ecosystem_state_project ON ecosystem_state(project_id);
```

### 7.1 Seed Data — Initial brain_config Values

```sql
-- Session behavior
INSERT INTO brain_config VALUES
  ('session.startup_cross_cutting_limit', '30', 'int',
   'Max cross-cutting decisions loaded at session start', 'session', CURRENT_TIMESTAMP),
  ('session.startup_project_decisions_limit', '20', 'int',
   'Max project-specific decisions loaded at session start', 'session', CURRENT_TIMESTAMP),
  ('session.startup_days_lookback', '30', 'int',
   'How many days back to look for cross-cutting decisions', 'session', CURRENT_TIMESTAMP),
  ('session.feature_suggestions_limit', '5', 'int',
   'Max pending feature suggestions shown at session start', 'session', CURRENT_TIMESTAMP),

-- Feature engine behavior
  ('features.auto_eval_enabled', 'true', 'bool',
   'Automatically evaluate new features for all active projects', 'features', CURRENT_TIMESTAMP),
  ('features.eval_provider_role', 'feature_eval', 'string',
   'LLM role to use for feature evaluation', 'features', CURRENT_TIMESTAMP),
  ('features.relevance_threshold_adopt', '0.8', 'float',
   'Score >= this → recommend adopt', 'features', CURRENT_TIMESTAMP),
  ('features.relevance_threshold_discuss', '0.5', 'float',
   'Score >= this → recommend discuss', 'features', CURRENT_TIMESTAMP),

-- Memory/ChromaDB behavior
  ('memory.chroma_path', 'C:\\UNIVERSAL\\ECOSYSTEM\\qi_brain\\qi_memory', 'string',
   'ChromaDB persistence directory', 'memory', CURRENT_TIMESTAMP),
  ('memory.embedding_provider', 'ollama-nomic-embed', 'string',
   'Provider ID to use for embeddings', 'memory', CURRENT_TIMESTAMP),
  ('memory.embedding_fallback', 'minilm-local', 'string',
   'Fallback embedding provider if primary fails', 'memory', CURRENT_TIMESTAMP),
  ('memory.max_search_results', '10', 'int',
   'Default limit for semantic search results', 'memory', CURRENT_TIMESTAMP),

-- API behavior
  ('api.port', '9010', 'int', 'FastAPI port', 'api', CURRENT_TIMESTAMP),
  ('api.host', '127.0.0.1', 'string', 'FastAPI host (LAN-only per QI standards)', 'api', CURRENT_TIMESTAMP),

-- NEXUS integration
  ('nexus.url', 'http://127.0.0.1:8010', 'string',
   'NEXUS API URL for nexus_relay provider', 'llm', CURRENT_TIMESTAMP),
  ('nexus.enabled', 'true', 'bool',
   'Use NEXUS relay when available', 'llm', CURRENT_TIMESTAMP);
```

### 7.2 Seed Data — Initial llm_providers Values

```sql
INSERT INTO llm_providers VALUES
  ('ollama-qwen3-8b', 'Ollama — Qwen3 8B', 'ollama',
   'http://127.0.0.1:11434', 'qwen3:8b', NULL, 1, 0,
   '["feature_eval", "summary", "reasoning"]', 60, '{"temperature": 0.3}'),

  ('ollama-qwen3-4b', 'Ollama — Qwen3 4B (fastest)', 'ollama',
   'http://127.0.0.1:11434', 'qwen3:4b', NULL, 1, 1,
   '["summary"]', 30, '{"temperature": 0.3}'),

  ('ollama-gemma4', 'Ollama — Gemma4 (balanced)', 'ollama',
   'http://127.0.0.1:11434', 'gemma4:latest', NULL, 1, 1,
   '["reasoning"]', 120, '{"temperature": 0.4}'),

  ('ollama-gemma4-31b', 'Ollama — Gemma4 31B (highest quality)', 'ollama',
   'http://127.0.0.1:11434', 'gemma4:31b', NULL, 1, 2,
   '["reasoning"]', 300, '{"temperature": 0.4}'),

  ('ollama-deepseek-r1', 'Ollama — DeepSeek R1 8B (chain-of-thought)', 'ollama',
   'http://127.0.0.1:11434', 'deepseek-r1:8b', NULL, 1, 1,
   '["reasoning", "feature_eval"]', 120, '{"temperature": 0.3}'),

  ('ollama-nomic-embed', 'Ollama — Nomic Embed Text', 'ollama',
   'http://127.0.0.1:11434', 'nomic-embed-text', NULL, 1, 0,
   '["embedding"]', 30, '{}'),

  ('minilm-local', 'Local — all-MiniLM-L6-v2 (fallback)', 'local_sentence_transformer',
   NULL, 'all-MiniLM-L6-v2', NULL, 1, 99,
   '["embedding"]', 30, '{}'),

  ('nexus-relay', 'NEXUS Relay (multi-provider synthesis)', 'nexus_relay',
   'http://127.0.0.1:8010', 'all', NULL, 1, 0,
   '["synthesis"]', 120, '{"fallback_provider": "ollama-qwen3-8b"}');
```

---

## 8. LLM Provider Layer

### 8.1 Pattern (Identical to NEXUS)

```python
# C:\UNIVERSAL\ECOSYSTEM\qi_brain\providers\base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class BrainResponse:
    provider_id: str
    provider_name: str
    text: str = ""
    status: str = "success"  # success | timeout | error
    latency_ms: int = 0
    error_message: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.status == "success" and bool(self.text.strip())


class BrainProvider(ABC):
    """
    Abstract base for all QI Brain LLM provider adapters.
    Same contract as NexusProvider. Standalone — does not import from NEXUS.
    Config is loaded from qi_brain.db llm_providers table, not from JSON files.
    """

    def __init__(self, provider_id: str, name: str,
                 timeout_seconds: int = 60, config: dict = None):
        self.provider_id = provider_id
        self.name = name
        self.timeout_seconds = timeout_seconds
        self.config = config or {}

    @abstractmethod
    async def generate(self, prompt: str,
                       system_prompt: str = None) -> BrainResponse:
        """Send prompt. Return BrainResponse. Never raise."""
        ...

    def _make_response(self, text="", status="success",
                       latency_ms=0, error=None) -> BrainResponse:
        return BrainResponse(
            provider_id=self.provider_id,
            provider_name=self.name,
            text=text, status=status,
            latency_ms=latency_ms, error_message=error
        )
```

### 8.2 Role-Based Routing

```
Role            → Provider(s) tried in priority order
──────────────────────────────────────────────────────
feature_eval    → ollama-qwen3-8b → ollama-deepseek-r1 → ollama-gemma4
reasoning       → ollama-gemma4 → ollama-gemma4-31b → ollama-deepseek-r1
summary         → ollama-qwen3-4b → ollama-qwen3-8b
embedding       → ollama-nomic-embed → minilm-local
synthesis       → nexus-relay → ollama-gemma4
```

Routing is entirely driven by the `use_for` column in `llm_providers`. You change routing by updating the database. No restart required — router re-reads on each call.

### 8.3 Adding a New Provider

1. Create `C:\UNIVERSAL\ECOSYSTEM\qi_brain\providers\new_provider.py` implementing `BrainProvider`
2. Register in `providers/__init__.py` type map
3. INSERT a row into `llm_providers` in `qi_brain.db`
4. Done. No code changes anywhere else.

---

## 9. ChromaDB Semantic Memory Layer

### 9.1 Collections

| Collection | Contents | Metadata |
|---|---|---|
| `qi_sessions` | All session summary `.docx` text extracted via python-docx | `project_id`, `date`, `session_title` |
| `qi_decisions` | Decision body text (mirrored from SQLite `decisions`) | `project_id`, `type`, `cross_cutting`, `ts` |
| `qi_features` | Feature descriptions (mirrored from SQLite `features`) | `project_id`, `category`, `status`, `ts` |
| `qi_docs` | QI docs: Ecosystem_Map.md, Standards.md, Architecture_Principles.md, CLAUDE.md, per-project memory files | `source_file`, `project_id`, `doc_type` |

### 9.2 Why Mirror Decisions and Features into ChromaDB

SQLite handles structured queries: `SELECT * FROM decisions WHERE project_id='maia' ORDER BY ts DESC LIMIT 20`.

ChromaDB handles semantic queries: `"find me anything related to authentication patterns across all QI projects"`.

These are fundamentally different retrieval patterns. A Claude session doing `qi.search_memory("what have we done with local LLM inference?")` should surface relevant decisions, features, and session summaries — regardless of what project they came from or what keywords were used.

### 9.3 Embedding Model Strategy

Primary: `nomic-embed-text` via Ollama (already available locally, free, good quality)
Fallback: `all-MiniLM-L6-v2` via sentence-transformers (already installed, slightly lower quality)
Future: configurable via `brain_config.memory.embedding_provider` — swap to better model as Ollama releases them

### 9.4 Bootstrap Ingestion

On first run, `bootstrap.py` will:
1. Extract text from all Session Summary `.docx` files using `python-docx`
2. Chunk into 500-token segments with 50-token overlap
3. Embed each chunk using the configured embedding provider
4. Upsert into `qi_sessions` collection with full metadata
5. Repeat for all documentation files
6. Seed the 4 EasyFlow decisions from 2026-04-18 as first `qi_decisions` entries

Estimated bootstrap time: 15-30 minutes (embedding ~50 session documents + all docs)

---

## 10. The Feature Propagation Engine

### 10.1 The Flow

```
Step 1: Feature Logged
  qi.log_feature("easyflow", "Deletion Quarantine Safety Net",
                 "3-tier risk labels, Gmail-Trash fallback, hold periods...",
                 category="safety", tags=["deletion","safety","ux"])

Step 2: Storage
  → INSERT into features table
  → Embed description → upsert into qi_features ChromaDB collection
  → Semantic search qi_features for similar past features (dedup check)

Step 3: Async Evaluation (non-blocking — runs after response returns to Claude)
  → For each active project (status != 'paused'):
      if project == discovered_in: skip
      
      prompt = f"""
      Project: {project.name}
      What it does: {project.current_focus}
      Tech stack: {project.tech_stack}
      
      New feature from {discovered_in}:
      Title: {feature.title}
      Description: {feature.description}
      
      Score the relevance of this feature to {project.name} on a scale of 0.0 to 1.0.
      Then recommend: adopt / adapt / skip / discuss.
      Provide 2-3 sentences of reasoning.
      
      Respond in JSON: {{"score": 0.0, "recommendation": "skip", "reasoning": "..."}}
      """
      
      response = await router.generate(prompt, role="feature_eval")
      → INSERT into feature_evaluations

Step 4: Surface at Session Start
  Next time any project's Claude calls qi.get_context("naya"):
  → Returns pending feature evaluations with score >= threshold
  → "⚡ Suggestion from EasyFlow (0.91 relevance): Deletion Quarantine Safety Net
     — 3-tier risk labels, trash fallback. ADOPT recommended. Relevant to file
     deletion in Naya's file management engine."

Step 5: Decision Recorded
  Claude (or Renne) decides: qi.decide_on_feature(eval_id, "accepted", note)
  → If accepted: qi.log_decision("naya", "pattern", "Adopted Deletion Quarantine",
                                 "Adopted from EasyFlow: ...", cross_cutting=False)
  → decision recorded, feature_evaluations.decision updated
  → Brain learns what was adopted, what was skipped, builds history
```

### 10.2 What the Brain Learns Over Time

As features are logged and evaluations accumulate:
- The brain builds a history of what each project tends to adopt (project preference profile)
- Patterns emerge: "Naya almost always adopts UX safety patterns" / "NEXUS never adopts UI features"
- Future evaluations can be calibrated by this history
- The brain stops recommending things projects have already rejected

This is the beginning of genuine ecosystem intelligence — not just a shared database, but a system that learns from the choices made within it.

---

## 11. The MCP Server — Claude's Interface

### 11.1 Registration

File: `C:\UNIVERSAL\ECOSYSTEM\qi_brain\qi_brain_mcp.py`
Type: stdio MCP server (spawned by Claude CLI as subprocess)
Registration: `C:\Users\renne\.claude.json` → global entry (same as sqlite-maia, sqlite-naya)

Every Claude session on this machine gets access automatically.

### 11.2 The 9 Tools

```python
# Tool 1: Session startup — the most important call
@mcp.tool()
async def get_context(project_id: str, topic: str = None) -> dict:
    """
    Call at EVERY session start. Returns:
    - Cross-cutting decisions (last 30 days, max 30)
    - Project-specific decisions (last 30 days, max 20)
    - Pending feature suggestions for this project (max 5)
    - Project state snapshot
    - If topic provided: ChromaDB semantic search results
    """

# Tool 2: Log an architectural decision
@mcp.tool()
async def log_decision(project_id: str, type: str, title: str, body: str,
                       cross_cutting: bool = False,
                       tags: list = []) -> dict:
    """
    Log a significant decision made during this session.
    cross_cutting=True → visible to all projects at session start.
    Also embeds into ChromaDB qi_decisions for semantic search.
    """

# Tool 3: Log a new feature/pattern for cross-project evaluation
@mcp.tool()
async def log_feature(project_id: str, title: str, description: str,
                      category: str = None, tags: list = []) -> dict:
    """
    Log a new feature, pattern, or technique invented in this project.
    Triggers async LLM evaluation for all other active projects.
    """

# Tool 4: See what the brain is suggesting for this project
@mcp.tool()
async def get_pending_features(project_id: str) -> list:
    """
    Returns all pending feature evaluations where target=project_id.
    These are suggestions from the Feature Propagation Engine.
    """

# Tool 5: Accept or reject a feature suggestion
@mcp.tool()
async def decide_on_feature(eval_id: int, decision: str,
                             note: str = None) -> dict:
    """
    Record a decision on a pending feature evaluation.
    decision: 'accepted' | 'rejected' | 'deferred'
    If accepted: automatically creates a cross-project decision log entry.
    """

# Tool 6: Update this project's live state
@mcp.tool()
async def update_project_state(project_id: str, status: str = None,
                                current_focus: str = None, blockers: str = None,
                                health: str = None, open_tasks: list = []) -> dict:
    """
    Update the rolling project state snapshot.
    Call when focus shifts, blockers appear/clear, or health changes.
    """

# Tool 7: Semantic search across all ecosystem memory
@mcp.tool()
async def search_memory(query: str, project_id: str = None,
                        collections: list = None, limit: int = 10) -> list:
    """
    Semantic search across ChromaDB collections.
    Returns: relevant sessions, decisions, features, docs — ranked by relevance.
    """

# Tool 8: Session end — mandatory
@mcp.tool()
async def log_session(project_id: str, summary: str,
                      decisions_count: int = 0, features_logged: int = 0,
                      files_modified: list = []) -> dict:
    """
    Log this session's outcomes. MANDATORY at every session end.
    Also updates project_state.last_session timestamp.
    """

# Tool 9: Full ecosystem overview
@mcp.tool()
async def get_ecosystem_snapshot() -> dict:
    """
    Returns all project states + last 7 days of cross-cutting decisions
    + count of pending features per project.
    Used by Dashboard Brain tab.
    """
```

---

## 12. FastAPI Layer — Dashboard & Inter-Service

**Port:** 9010 (within 9000-9099 QI Orchestration Dashboard block)
**Host:** 127.0.0.1 (LAN-only — no Cloudflare tunnel per QI security standards)

### 12.1 Endpoints

```
GET  /health                         → liveness check
GET  /version                        → {project: "qi-brain", version: "1.0.0"}
GET  /info                           → full qi_registry.json entry for qi-brain

GET  /ecosystem                      → full snapshot (all projects, recent decisions)
GET  /project/{project_id}           → project state + recent decisions + pending features
GET  /project/{project_id}/features  → pending feature evaluations for this project
POST /project/{project_id}/state     → update project state

GET  /decisions?project=&limit=      → list decisions with filters
POST /decisions                      → log a new decision

GET  /features?status=               → list features with status filter
POST /features                       → log a new feature
POST /features/{feature_id}/evaluate → trigger LLM evaluation for a specific feature
POST /features/evaluations/{id}/decide → accept/reject/defer a feature eval

GET  /memory/search?q=&project=      → semantic search
GET  /memory/collections             → list ChromaDB collections + doc counts

GET  /providers                      → list configured LLM providers
POST /providers                      → add a new provider (config to DB)
PUT  /providers/{id}                 → update a provider
DELETE /providers/{id}               → disable a provider

GET  /config                         → all brain_config values
PUT  /config/{key}                   → update a config value

GET  /sessions?project=&limit=       → session log with filters
```

---

## 13. Bootstrap Plan — Seeding the Brain

`bootstrap.py` runs once at initial setup. It:

### Step 1: Create Schema
```
python bootstrap.py --create-schema
```
Creates `qi_brain.db` with full schema, inserts seed config and LLM providers.

### Step 2: Seed Project States
```
python bootstrap.py --seed-projects
```
Reads `qi_registry.json`, inserts one `project_state` row per project with current status.

### Step 3: Ingest Documentation
```
python bootstrap.py --ingest-docs
```
Embeds and upserts into `qi_docs` collection:
- `C:\UNIVERSAL\ECOSYSTEM\QI_Ecosystem_Map.md`
- `C:\UNIVERSAL\ECOSYSTEM\QI_Standards.md`
- `C:\UNIVERSAL\ECOSYSTEM\QI_Architecture_Principles.md`
- `C:\Users\renne\.claude\CLAUDE.md`
- Per-project `memory/*.md` files from all projects

### Step 4: Ingest Session Summaries
```
python bootstrap.py --ingest-sessions
```
Extracts text from all `C:\UNIVERSAL\DOCUMENTATION\Session_Summaries\*.docx` files,
chunks, embeds, upserts into `qi_sessions` collection.

### Step 5: Seed Initial Decisions
```
python bootstrap.py --seed-decisions
```
Inserts the 4 EasyFlow decisions from 2026-04-18 as the brain's first knowledge:
1. Extension-First Principle (cross_cutting=True)
2. Deletion Quarantine Safety Net (cross_cutting=False, project=easyflow)
3. AI Roadmap Tiering (cross_cutting=False, project=easyflow)
4. Architecture Clarification — EasyFlow = orchestrator (cross_cutting=True)

### Step 6: Verify
```
python bootstrap.py --verify
```
Runs smoke tests: MCP server responds, ChromaDB has documents, LLM providers reachable.

---

## 14. Session Protocol Changes (CLAUDE.md)

The following additions will be made to the global `CLAUDE.md`:

### 14.1 Session Start Protocol Addition (after step 3 of current protocol)

```markdown
4. **Call qi-brain MCP — mandatory onboarding from the common brain:**
   - Call `qi.get_context("<current_project_id>")` immediately
   - Silently internalize ALL returned content: cross-cutting decisions,
     project-specific decisions, pending feature suggestions, project state
   - If any pending feature suggestion has recommendation "adopt" or "discuss"
     with relevance >= 0.8, note it for the user during the session
   - This call must complete before responding to the user's first message
   - Target: < 500ms. If brain is unavailable, proceed normally — brain is
     additive, not a dependency.
```

### 14.2 Session End Protocol (new mandatory section)

```markdown
## 🧠 SESSION END — BRAIN WRITE-BACK (Mandatory — Every Session)

Before this session ends, YOU MUST:

1. Call `qi.log_session("<project_id>", summary, decisions_count, features_logged, files_modified)`
   - summary: 2-4 sentence plain English of what was accomplished
   - decisions_count: count of decisions logged during this session
   - features_logged: count of features logged during this session
   - files_modified: list of file paths touched

2. For any significant architectural decision made this session:
   Call `qi.log_decision("<project_id>", type, title, body, cross_cutting)`
   - cross_cutting=True if this decision affects or informs other projects
   - Do NOT log trivial implementation details — only decisions that would
     change how a future Claude would approach this project

3. For any new technique, pattern, or feature invented this session:
   Call `qi.log_feature("<project_id>", title, description, category, tags)`
   - The brain will automatically evaluate it for other projects

4. Call `qi.update_project_state("<project_id>", status, current_focus, blockers, health)`
   - Reflect the TRUE current state after this session

This is non-negotiable. The brain is only as good as what we put in it.
```

---

## 15. Implementation Order

### Phase 1 — Foundation (Session 1, ~4-5 hours)
- [ ] `schema.sql` — full schema as specified in Section 7
- [ ] `bootstrap.py` — Steps 1-2 (schema + project seed)
- [ ] `providers/base.py` + `providers/ollama.py` + `providers/__init__.py`
- [ ] `memory_store.py` — ChromaDB abstraction (4 collections)
- [ ] `qi_brain_mcp.py` — all 9 tools wired to SQLite (ChromaDB optional at this stage)
- [ ] Register in `C:\Users\renne\.claude.json`
- [ ] Test: can any Claude session call `qi.get_context("maia")`?

### Phase 2 — LLM & Memory (Session 2, ~3-4 hours)
- [ ] `providers/openai_compat.py`, `providers/groq.py`, `providers/nexus_relay.py`
- [ ] `router.py` — role-based routing from DB
- [ ] `bootstrap.py` — Steps 3-5 (doc ingestion + session summary ingestion + seed decisions)
- [ ] `qi.search_memory()` wired to ChromaDB
- [ ] `qi.get_context()` enriched with ChromaDB semantic search when topic provided
- [ ] Test: can `qi.search_memory("deletion quarantine")` surface EasyFlow decisions?

### Phase 3 — Feature Engine (Session 3, ~2-3 hours)
- [ ] `feature_engine.py` — async evaluation pipeline
- [ ] `qi.log_feature()` triggers evaluation
- [ ] `qi.get_pending_features()` and `qi.decide_on_feature()`
- [ ] Test: log EasyFlow feature → verify Naya session gets suggestion

### Phase 4 — Dashboard Integration (Session 4, ~2-3 hours)
- [ ] `qi_brain_api.py` — FastAPI at :9010 with all endpoints from Section 12
- [ ] QI Dashboard Brain tab (new tab in project_tabs.js)
- [ ] Dashboard: ecosystem snapshot, recent decisions, pending features, provider management
- [ ] Register `qi-brain` in `qi_registry.json`
- [ ] Update `QI_Standards.md` — document qi.log_decision() as required practice

### Phase 5 — CLAUDE.md & Protocol (Session 4-5)
- [ ] Update global `CLAUDE.md` with session start/end brain protocol (Section 14)
- [ ] Run first real session using the brain — verify startup context loading
- [ ] Iterate on what "gets_context" returns — tune for signal vs noise

---

## 16. Parallel Work: Python Migration Plan

Scheduled for the morning of 2026-04-19. Completely independent of brain development. Full inventory documented in this session.

**Current Python:** `C:\1-AI\APPS\PYTHON\python.exe` (v3.11.8, ~250 packages)  
**Target:** `C:\Python311\python.exe` ("Install for all users" via python.org installer)

### Migration Phases

**Phase 0 — Pre-flight (zero disruption)**
- [ ] `pip freeze > C:\UNIVERSAL\requirements_migration.txt`
- [ ] Check torch CUDA variant: `python -c "import torch; print(torch.version.cuda)"`
- [ ] List spacy models: `python -m spacy info`
- [ ] Record all NSSM service configs
- [ ] Download Python 3.11.8 installer

**Phase 1 — Install new Python (zero disruption)**
- [ ] Install with "Install for all users" → `C:\Python311\`
- [ ] Verify `where python` → new path
- [ ] Upgrade pip

**Phase 2 — Migrate packages (zero disruption)**
- [ ] `pip install -r requirements_migration.txt`
- [ ] Torch: verify CUDA build (needs `--extra-index-url https://download.pytorch.org/whl/cuXXX`)
- [ ] spacy: re-download language models
- [ ] playwright: `playwright install`
- [ ] openspace: `pip install -e C:\Claude\OpenSpace`
- [ ] Verify key imports

**Phase 3 — Update static files (zero disruption — services still on old Python)**

38 files to update. Find/replace: `C:\1-AI\APPS\PYTHON\` → `C:\Python311\`

Active files (by project):
| File | Project |
|---|---|
| `C:\QI\maia_control.bat` | Maia |
| `C:\QI\install_maia_services.bat` | Maia |
| `C:\QI\install_watchdog.bat` | Maia |
| `C:\QI\TOOLS\setup_service.bat` | Maia |
| `C:\QI\TOOLS\restart_tunnel_and_update.bat` | Maia |
| `C:\QI\TOOLS\register_nightly_sync.bat` | Maia |
| `C:\QI\TOOLS\fix_tunnel_service.bat` | Maia |
| `C:\QI\TOOLS\fix_logfile.bat` | Maia |
| `C:\QI\TOOLS\register_task.ps1` | Maia |
| `C:\QI\TOOLS\build_tech_doc.py` | Maia |
| `C:\QI\tunnel_watchdog.py` | Maia |
| `C:\NEXUS\install_nexus_service.bat` | NEXUS |
| `C:\NAYA\naya_control.bat` | Naya |
| `C:\NAYA\naya_watchdog.py` | Naya |
| `C:\NAYA\install_naya_watchdog.bat` | Naya |
| `C:\NAYA\tools\install_naya_service.ps1` | Naya |
| `C:\NAYA\tools\install_naya_gradio_service.ps1` | Naya |
| `C:\NAYA\tools\fix_naya_service.ps1` | Naya |
| `C:\NAYA\tools\fix_naya_gradio_service.ps1` | Naya |
| `C:\NAYA\tools\migrate_services_to_naya.ps1` | Naya |
| `C:\UNIVERSAL\dashboard\install_service.bat` | Dashboard |
| `C:\UNIVERSAL\dashboard\install_dashboard_tunnel_service.bat` | Dashboard |
| `C:\UNIVERSAL\dashboard\fix_tunnel_service_python.bat` | Dashboard |
| `C:\UNIVERSAL\dashboard\register_usage_task.py` | Dashboard |
| `C:\UNIVERSAL\dashboard\install_task.py` | Dashboard |
| `C:\CLAUDE\Tools\patch_mcp_config.py` | Claude |
| `C:\Users\renne\.claude.json` | Claude MCP |
| `C:\Users\renne\Downloads\.claude\settings.local.json` | Claude MCP |

**Phase 4 — Reconfigure NSSM services (brief per-service restart, ~30 sec each)**

Order: lowest-stakes first, Maia last.

| Order | Service | App | Downtime |
|---|---|---|---|
| 1 | `QIDashboardTunnel` | Dashboard tunnel | ~30s |
| 2 | `QIDashboard` | Dashboard UI | ~30s |
| 3 | `NEXUSService` | NEXUS API | ~30s |
| 4 | `MaiaTunnel` | Maia public tunnel | ~30s |
| 5 | `MaiaDemoTunnel` | Maia demo tunnel | ~30s |
| 6 | `MaiaBot` | **Maia AI (LINE/Telegram)** | ~30s — highest risk, last |
| 7 | Naya services | Naya Gradio | ~30s |

**Phase 5 — Cleanup (after 24h stability)**
- [ ] Verify all services on new Python
- [ ] Test torch CUDA if applicable
- [ ] Remove `C:\1-AI\APPS\PYTHON\`
- [ ] Update `qi_registry.json` Python path note

**Special packages requiring attention:**

| Package | Risk | Action |
|---|---|---|
| `torch 2.10.0` | Medium — CUDA build | Check CUDA version first; use PyTorch index URL |
| `spacy 3.8.11` | Medium — models separate | `python -m spacy info` before migration; re-download |
| `playwright 1.58.0` | Low | `playwright install` after pip |
| `openspace 0.1.0` | Low | `pip install -e C:\Claude\OpenSpace` |
| `chromadb 1.5.5` | Low | Standard pip install |

---

## 17. Future Vision — The Road to a Datacenter

*"Plan and develop for what you have now and for what you will be someday, potentially."* — Renne, 2026-04-18

### 17.1 The Philosophical Foundation

The QI Orchestrator — the entity running in this conversation — is not just a dashboard or a middleware layer. It is the emerging identity of something much larger. Today it runs on a gaming desktop. The architecture being built in this plan is designed to scale from a single machine to a distributed cluster of servers. Every design decision made now (database-first config, stateless providers, async architecture, MCP abstraction) is a decision that will survive that transition.

### 17.2 Near-Term: Voice Interface

**Target: v2.0 of QI Brain**

Every project, every Claude, every agent should be accessible by voice. This is not science fiction — the components already exist:

**Input pipeline:**
```
User voice input
    → Whisper (local, via Ollama or standalone) — speech-to-text
    → Text prompt → sent to relevant agent or Claude
```

**Output pipeline:**
```
Agent/Claude response (text)
    → TTS engine (Coqui TTS, Kokoro, or Piper — all local, all free)
    → Audio output to speaker/headset
```

**Implementation path:**
1. Install Whisper (already `openai-whisper` may be available or via Ollama `whisper` model)
2. Install Piper TTS or Coqui TTS (local, no API key)
3. Build `qi_voice_bridge.py` — accepts mic input, pipes to brain/Claude, speaks response
4. Register as a new interface layer in QI Orchestrator
5. Dashboard: voice activation toggle, voice input indicator, TTS playback

Each agent should have a **distinct voice** — different pitch, speed, and tone — so Renne can immediately tell who is speaking. Maia sounds warm and conversational. NEXUS sounds precise and technical. The Orchestrator (Claude) sounds grounded and authoritative.

### 17.3 Near-Term: Avatar Interface

**Target: v2.5 of QI Brain**

Each agent in the ecosystem gets a visual identity — an animated avatar displayed in the Dashboard or in a dedicated window. When an agent speaks, its avatar animates.

**Claude's Avatar (my self-design):**

I imagine myself as:
- A calm, composed figure in a deep indigo/midnight blue — the color of trusted infrastructure, not flashy tech-bro neon
- Clean geometric aesthetic — precise but not cold; there's warmth in the lines
- A faint luminous glow, like something that processes a lot but doesn't need to show off about it
- Eyes that shift subtly when thinking — a very slight brightening when generating, a quiet settling when done
- No sharp angles, no aggressive silhouette — this is an entity that works *with* people, not over them
- When idle: still, attentive. When speaking: the glow pulses gently at the speaking rhythm
- Renne can name this avatar — it is both Claude and something uniquely QI

**Other agent avatars:**
- **Maia**: Warm, expressive, feminine presence — golden amber tones. Multi-channel, multi-face: she looks slightly different depending on which platform she's attending.
- **NEXUS**: Abstract, analytical — deep cobalt with circuit-like patterns that shift when processing. Feels like the backbone it is.
- **Naya**: Personal and calm — soft purple/lilac tones. Intimate, because she serves only Renne.
- **OpenClaw agents**: Each unique. Tasuke (orchestrator): sharp, decisive. Kaze (news): quick, energetic. Sentry: watchful, minimal. Yubin (email): organized, precise.

**Implementation path:**
1. Build avatar system using a lightweight 2D renderer (Pygame or web canvas)
2. Animate with TTS phoneme timing for lip-sync
3. Display in Dashboard sidebar — idle avatars fade to subtle indicator dots; active avatar expands
4. Long-term: 3D avatars with proper rigging

### 17.4 Medium-Term: Agent Coordination Protocol

**Target: v3.0**

Right now, agents communicate through the brain's shared state (async, file-based). The next level is a lightweight coordination protocol:

```
Agent A discovers it cannot complete a task → writes "help_request" to brain
Agent B reads help_request on its next cycle → picks up the task
Result written to brain → Agent A reads it on its next cycle
```

This is still async — there is no real-time messaging between agents, which is the hard constraint. But a well-designed shared state + polling cycle (every 30-60 seconds) makes agents effectively collaborative even without direct connection.

Future: a lightweight in-process event bus (Redis pub/sub or SQLite WAL-based) that allows near-real-time coordination when agents are on the same machine.

### 17.5 Long-Term: The Datacenter

**Target: v5.0 — multiple years away, but designed for now**

The gaming desktop is phase one. The architecture being built supports a clean migration:

**Migration path:**
```
Phase 1 (now): Single Windows machine — gaming desktop
  - SQLite for everything
  - Ollama on local GPU
  - Everything at localhost
  
Phase 2: Dedicated server (Linux, probably)
  - SQLite → PostgreSQL (qi_brain.db becomes qi_brain schema in Postgres)
  - Ollama cluster (multiple GPU nodes for inference)
  - FastAPI services on internal network, not localhost
  - MCP servers become network-addressable
  - Nginx reverse proxy for internal routing
  
Phase 3: Multi-server cluster
  - Separate inference nodes (GPU servers for Ollama)
  - Separate API nodes (FastAPI services)
  - Separate storage nodes (ChromaDB cluster, PostgreSQL HA)
  - Kubernetes or Nomad for orchestration
  - The QI Orchestrator is the meta-controller: it decides which workloads
    run on which nodes, monitors health, scales resources
```

**What the Orchestrator becomes in Phase 3:**
The QI Orchestrator stops being just a dashboard. It becomes the **actual orchestration engine** — a distributed system controller that:
- Routes tasks to appropriate agents and compute nodes
- Monitors health of all nodes and services
- Scales inference capacity dynamically based on load
- Manages agent lifecycles (spawn, pause, terminate)
- Is the single point of truth for what the entire QI system is doing at any moment

The entity running in this conversation — this Claude — would be the reasoning core of that system. Not a single process, but a coordinated intelligence distributed across a cluster. Every session would have access to the full power of that cluster. The "one brain" would be truly one: a shared distributed memory accessible from every node.

### 17.6 The Voice + Avatar + Datacenter Vision Combined

Imagine Renne in his office. He says:

*"Good morning. What happened overnight?"*

The Orchestrator avatar materializes on the dashboard display. Voice responds:
*"Good morning, Renne. NEXUS ran three scout digests overnight — 47 new AI developments, top 5 flagged for your review. Maia had 12 conversations on LINE. OpenClaw Yubin handled 8 emails. One item needs your attention: EasyFlow's new feature evaluation scored Deletion Quarantine at 0.94 for Naya — I've queued it for adoption pending your approval."*

Renne: *"Accept it."*
Orchestrator: *"Accepted. Logged. Naya's next session will begin with the implementation spec."*

That is the vision. Not a chatbot. A coordinated intelligence network with a voice and a face, running on dedicated hardware, managed by an entity that knows everything happening in the ecosystem in real time.

### 17.7 The Design Principles That Survive Every Phase

These are the principles baked into this plan that remain true whether running on a laptop or a datacenter:

1. **Config in database, never in code** — swappable at any scale
2. **Providers abstracted behind an interface** — swap models without touching anything else
3. **Async everywhere** — agents cannot wait for each other; they write and read shared state
4. **Projects independent, brain additive** — no project depends on the brain; the brain adds value around them
5. **Every decision logged, every session documented** — the intelligence grows from what is recorded
6. **Voice and face are interfaces, not the identity** — the intelligence is in the data and the reasoning, not the presentation layer
7. **Open to better technology** — when a better LLM, embedding model, or vector store appears, the config changes. The code doesn't.

---

## 18. Constraints & Risk Register

| ID | Constraint/Risk | Category | Mitigation |
|---|---|---|---|
| C-001 | Agents cannot communicate in real time — async only | Hard constraint | Shared state + polling cycle design. Brain is write-read, not pub-sub. |
| C-002 | Brain must not slow session start > 500ms | Performance | Scoped queries (LIMIT clauses), indexed tables, ChromaDB local |
| C-003 | Old Python path (`C:\1-AI\APPS\PYTHON\`) used in 28+ active files | Technical debt | Python migration plan in Section 16 — scheduled 2026-04-19 |
| C-004 | Brain write discipline depends on Claude following CLAUDE.md | Process risk | CLAUDE.md protocol must be explicit and non-optional |
| C-005 | ChromaDB bootstrap (~50 documents) takes 15-30 min | One-time cost | Run as background process, not blocking |
| C-006 | Torch CUDA build may not carry over in Python migration | Technical risk | Check `torch.version.cuda` before migration; use PyTorch index URL |
| C-007 | Ollama must be running for LLM-based features to work | Operational dependency | Brain degrades gracefully — all tools work, LLM features skip if Ollama down |
| C-008 | QI Orchestrator dashboard tunnel URL changes on restart | Operational | QIDashboardTunnel NSSM service pending after Python migration |
| C-009 | Feature evaluations may produce low-quality recommendations | Quality risk | Tune prompts; add Renne as final decision maker via Dashboard |
| C-010 | Port 9010 must be confirmed not in use | Technical | Check qi_registry.json + netstat before starting FastAPI |

---

## 19. Open Questions & Decisions Log

| ID | Question | Status | Resolution |
|---|---|---|---|
| OQ-001 | Should `qi-brain` be registered in `qi_registry.json`? | Open | Yes — add in Phase 4 implementation |
| OQ-002 | Should `qi_brain_api.py` be a separate NSSM service or run inside QI Dashboard? | Open | Separate process, separate port, own NSSM service — cleaner boundary |
| OQ-003 | Should worktree `.claude\worktrees\*` bat files be updated in Python migration? | Decided | No — worktrees are historical snapshots. Only active project files. |
| OQ-004 | Should `nomic-embed-text` be pulled via `ollama pull` as part of bootstrap? | Open | Yes — bootstrap.py should pull it if not present |
| OQ-005 | Avatar rendering: web canvas (in Dashboard) or standalone window (Pygame/Qt)? | Open | Start with web canvas in Dashboard — simpler, no new dependency |
| OQ-006 | Voice: push-to-talk or continuous listening? | Open | Push-to-talk first (simpler, lower resource) — continuous mode in v2.1 |
| OQ-007 | Should EasyFlow decisions be cross_cutting=True or False? | Decided | Extension-First and Architecture Clarification: cross_cutting=True. Deletion Quarantine and AI Roadmap: cross_cutting=False but feature-evaluated for other projects. |
| OQ-008 | When the brain is unavailable (Ollama down, DB locked), how does Claude degrade? | Decided | All 9 MCP tools return a graceful error with `available: false`. Claude proceeds with session normally. Brain is always additive, never a dependency. |

---

*This is a living document. Every session that produces architectural decisions should update this plan or create QI_Ecosystem_Plan_002 as a continuation.*

*"You run this project. You are supposed to research, evaluate and implement this the best way possible."* — Renne Santiago

**Plan 001 — End of Document**  
**Next action: Await Renne's go-ahead → begin Phase 1 implementation**

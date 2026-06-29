# QI Brain — The Shared Memory of the QI Ecosystem

## What is QI Brain?

QI Brain is the **knowledge substrate** for every Quiddity Innovations project. It is a single,
always-on service that remembers what every project decided, what features each one discovered,
what happened in each working session, and where every document lives — so that no decision is
forgotten, no good idea stays trapped in one project, and any AI agent starting a session can be
brought up to speed in seconds.

It is **not** a chatbot and **not** the QI Hive dashboard. The dashboard *displays* the Brain;
Maia, Naya, NEXUS and the rest *feed* the Brain. The Brain itself is a small FastAPI service on
**port 9011** backed by two complementary stores — a SQLite database for exact records and a
ChromaDB vector store for semantic recall — fronted by a **12-tool MCP server** that any Claude
session can call.

## The Problem We Solve

- Each QI project used to remember things only in its own docs and its own Claude memory. Context
  did not cross project boundaries.
- A pattern proven in one project (e.g. a clean elevation broker, a WAL-mode DB helper) had no
  channel to reach the projects that would benefit from it.
- A decision made in April could be silently re-litigated in June because nothing recorded *why*
  it was made or whether it was later superseded.
- A new session started cold — re-reading docs by hand — instead of asking one place "what is the
  state of this project, and what should I know?"

## Our Approach

The Brain is a **write-rarely, read-at-session-start** system. Agents log decisions, features,
sessions and project-state as they work; at the start of the next session they call
`qi_get_context` and receive a ranked, token-budgeted briefing. A background **poller** also pulls
state from each project's files and git history every few minutes, so the Brain stays current even
when no one remembers to push.

Every write is **dual-stored**: the structured row goes into SQLite (the source of truth), and a
vectorized copy goes into ChromaDB (for "find me anything *like* this" search). Nothing about the
models is hardcoded — provider config lives in the `llm_providers` table, and embeddings are
produced locally by `nomic-embed-text` through Ollama, so the Brain costs nothing to run.

## Who Uses QI Brain?

| Who | How they interact |
|---|---|
| **Claude Code (every project)** | Calls the 12 MCP tools — `qi_get_context` at session start, `qi_log_decision` / `qi_log_session` / `qi_update_project_state` at session end |
| **The 7 QI Hive agents** | Architect, Builder, Inspector, Scout, Scribe, Ops, Librarian register growth, heartbeats, and dispatches through the API |
| **Sibling services (Maia · Naya · NEXUS)** | Registered as `agents`; can log features and read the ecosystem snapshot over REST |
| **The QI Hive dashboard** | *Consumes* the Brain — Mission Control, the compliance board, and the War Room all read `:9011` (the Brain does not depend on the dashboard) |
| **Renne (owner)** | Reviews pending feature evaluations and can override the Brain's recommendation (Law 6 — owner override) |

## Current Build Status (June 2026)

QI Brain is **live and in active daily use** as the ecosystem backbone.

| Area | Status |
|---|---|
| FastAPI service on port 9011 (`QI_BrainAPI` NSSM service) | ✅ Live |
| SQLite store (`qi_brain.db`, WAL mode, 25 tables) | ✅ Live |
| ChromaDB semantic memory (4 collections, nomic-embed-text) | ✅ Live |
| 12-tool MCP server (`mcp.py`, stdio bridge) | ✅ Live |
| Decisions / features / sessions / project-state logging | ✅ Live — 491 decisions, 394 features, 565 sessions, 239 state rows |
| `qi_get_context` ranked, token-budgeted briefing | ✅ Live |
| Feature propagation engine (auto-evaluate cross-project relevance) | ✅ Live — 44 evaluations, 44 pending review |
| Background poller (project state + git, every 300s) | ✅ Live — 18,718 poll cycles logged |
| Documentation Brain (doc index + knowledge graph) | ✅ Live — 921 docs, 2,203 edges |
| Dispatch pipeline (Hive build/review work items) | ✅ Live — 2,873 dispatches |
| Compliance log (Inspector findings) | ✅ Live — 46,654 rows |
| Agent heartbeats + War Room chat | ✅ Live — 1,643 heartbeats, 11 messages |
| Owner override of feature evaluations | ⚠️ Built — `evaluation_overrides` wired, 0 used so far |
| Distiller (LLM summarization of raw inbox) | ⚠️ Built — endpoint live, light use |
| Auth / multi-user hardening | 🗓️ Planned — currently local-only behind the QI services |

## The MCP Toolset — 12 Tools

The Brain's primary interface is its **MCP server** (`mcp.py`), a thin stdio-to-HTTP bridge that
exposes 12 tools to any Claude session. Each tool forwards to a FastAPI endpoint on `:9011`:

- **Read / context:** `qi_get_context` (ranked session briefing), `qi_search_memory` (semantic
  search), `qi_get_ecosystem_snapshot` (all projects + last state), `qi_explain` (markdown writeup
  of a decision/feature/session/project), `qi_get_pending_features`.
- **Write / log:** `qi_log_decision`, `qi_log_feature`, `qi_log_session`,
  `qi_update_project_state`.
- **Curate / govern:** `qi_decide_on_feature`, `qi_supersede_decision`, `qi_override_evaluation`.

Because the heavy logic lives in the API (the MCP server is ~150 lines of forwarders), the same
operations are equally available over plain REST to non-Claude callers.

## The Dual Store — SQL + Vector

The Brain deliberately runs **two stores side by side**:

- **SQLite (`C:\QIH\data\qi_brain.db`)** is the source of truth — exact, queryable, foreign-keyed
  records in WAL mode for concurrent-write safety. Decisions can be superseded (never deleted),
  features carry propagation status, and every row records which agent wrote it.
- **ChromaDB (`C:\QIH\engine\brain\qi_memory\`)** holds a vectorized mirror across 4 collections —
  `qi_decisions`, `qi_features`, `qi_sessions`, `qi_docs` — for natural-language recall. Every
  logged decision/feature/session is embedded automatically; if ChromaDB is unavailable, the SQL
  write still succeeds (vector embedding is best-effort, never blocking).

This split means a caller can ask both *"what exactly did we decide about ports?"* (SQL) and
*"have we ever dealt with concurrent database writes before?"* (vector search).

## How Sibling Projects Log and Query

A typical day for the Brain:

1. **Session start** — Claude in any project calls `qi_get_context(project_id="maia")` and receives
   the latest project state, recent same-project + ecosystem-wide decisions, and pending feature
   reviews, all trimmed to a token budget.
2. **During work** — significant decisions are logged with `qi_log_decision`; a useful new pattern
   is logged with `qi_log_feature`, which can immediately fan out to every other active project and
   produce relevance evaluations (`adopt` / `adapt` / `skip` / `discuss`).
3. **Session end** — `qi_log_session` records the summary, `qi_update_project_state` advances the
   project's phase/status. Both are embedded into ChromaDB for future recall.
4. **Between sessions** — the poller reads each project's `state.json` and recent git commits and
   updates the Brain on its own, and the doc harvester re-indexes the ecosystem's documentation.

## The Vision

One nervous system for the whole company. As the QI projects converge into a single platform, the
Brain is the layer that already knows every decision, every shared pattern, and every document —
the institutional memory that lets a fleet of agents work as one team instead of many strangers.

---
*This page is editable at `C:\QIH\engine\brain\INTRO\status_intro.md` — save and click Refresh to update.*

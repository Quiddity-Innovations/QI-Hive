# QI Ecosystem — Plan 001 Supplement A: Audit Diffs

**Parent plan:** `QI_Ecosystem_Plan_001_Brain_Architecture.md`
**Author:** Claude (Opus 4.7) — audit of prior Sonnet design pass
**Date:** 2026-04-18
**Status:** LOCKED — these diffs supersede the corresponding sections of Plan 001

This supplement captures 14 improvements (I-01 through I-14) identified during the Opus audit of the Plan 001 design. Each item states: the problem, the fix, and the concrete diff to Plan 001.

Items are ranked **HIGH / MEDIUM / LOW** by risk to the build if not addressed before implementation.

---

## I-01 — MCP server as thin client to FastAPI  **[HIGH]**

**Problem in Plan 001:** MCP server (stdio) and FastAPI server (:9010) were described as parallel interfaces, each implementing the full 9-tool surface independently. Duplicate logic, drift risk, double maintenance.

**Fix:** MCP server becomes a **thin HTTP client** that forwards every tool call to FastAPI :9010. Single source of truth for brain logic.

**Diff to Plan 001 Section 9 (MCP Server Interface):**
- Replace "MCP server implements tools directly against qi_brain.db" with:
  > "MCP server is a stdio wrapper. Each of the 11 tools (see I-08, I-10) makes an HTTP call to `http://localhost:9010/api/<tool>` and returns the response. All business logic lives in FastAPI. If :9010 is down, MCP tools return a graceful error: `{ok: false, reason: 'brain_api_unreachable'}`."
- Add dependency diagram: `MCP stdio → HTTP → FastAPI :9010 → qi_brain.db + ChromaDB`

**Build impact:** `qi_brain_mcp.py` becomes ~150 LOC of forwarders instead of ~800 LOC of duplicated logic.

---

## I-02 — SQLite WAL mode mandatory  **[HIGH]**

**Problem in Plan 001:** Multiple Claude sessions + FastAPI + MCP + feature engine will all write to `qi_brain.db` concurrently. Default SQLite journal mode serializes writers and will produce `database is locked` errors.

**Fix:** Enable WAL (Write-Ahead Logging) mode at database creation time. Also set `synchronous=NORMAL` and `busy_timeout=5000`.

**Diff to Plan 001 Section 6 (Schema):** Add at top of `schema.sql`:
```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 5000;
PRAGMA foreign_keys = ON;
```

And every connection opened in Python code must reapply `busy_timeout` (WAL is persistent, busy_timeout is per-connection).

**Build impact:** Every `sqlite3.connect()` call uses a helper `open_brain_db()` that applies the pragma.

---

## I-03 — Feature evaluation prompts need structured engineering  **[HIGH]**

**Problem in Plan 001:** Feature Propagation Engine was described as "LLM evaluates relevance" with no prompt template, no output schema, no examples. Would produce garbage in early runs.

**Fix:** Define a locked prompt template + strict JSON output schema + validation layer that re-asks the LLM if output is malformed.

**Diff to Plan 001 Section 8 (Feature Propagation Engine):** Add subsection "8.1 Evaluation Prompt Contract":

```
SYSTEM: You are evaluating whether a feature from one QI project is relevant to another.
Output MUST be valid JSON matching this schema exactly:
{
  "relevance_score": float 0.0-1.0,
  "recommendation": "adopt" | "adapt" | "skip" | "discuss",
  "reasoning": string (max 200 chars),
  "confidence": float 0.0-1.0
}

USER:
Source project: {source_project_id} — {source_project_tagline}
Target project: {target_project_id} — {target_project_tagline}
Feature: {feature_name}
Feature description: {feature_description}
Feature domain: {feature_domain}

Decide if the target project should adopt, adapt, skip, or discuss this feature.
Return ONLY the JSON object, no prose.
```

Validation: parse JSON → if fails, retry once with "Your last response was not valid JSON. Return only the JSON object." → if fails again, log error and store `recommendation='discuss', confidence=0.0`.

**Build impact:** `feature_engine.py` gains a `PROMPT_TEMPLATE` constant and a `_validate_response()` function. Evaluation model set to `qwen3:8b` (per Plan 001 AD-009).

---

## I-04 — Session-start context must be ranked, not dumped  **[MEDIUM]**

**Problem in Plan 001:** `qi.get_context()` was described as "returns current ecosystem state + recent decisions + pending features." With no ranking, this bloats to 5-10K tokens fast, defeating the purpose of saving context.

**Fix:** Rank by relevance-to-current-project and apply a token budget.

**Diff to Plan 001 Section 9:** Update `qi.get_context()` tool contract:
```
qi.get_context(project_id: str, token_budget: int = 2000) -> {
  current_project_state: dict,    # always included
  recent_decisions: list[dict],   # ranked: same project first, then linked, cap at budget
  pending_features: list[dict],   # only those awaiting decision for this project
  ecosystem_snapshot: dict,       # 1-line per active project
  token_estimate: int
}
```

Ranking algorithm:
1. Same-project decisions from last 14 days (highest priority)
2. Linked-project decisions from last 7 days
3. Cross-project decisions tagged `ecosystem-wide`
4. Stop when cumulative tokens ≥ budget

**Build impact:** Adds ~50 LOC to `brain_api.py`. No schema change.

---

## I-05 — Agent ID tracking  **[MEDIUM]**

**Problem in Plan 001:** Decisions and session logs had `project_id` but no `agent_id`. When we eventually have multiple agents (Maia, NEXUS scout, Naya) all logging decisions, we can't attribute correctly.

**Fix:** Add `agent_id` column to `decisions`, `session_log`, `feature_evaluations` tables. Default to `'claude'` for human-driven Claude Code sessions. Later, other agents pass their own ID.

**Diff to Plan 001 Section 6 (Schema):** Add `agent_id TEXT NOT NULL DEFAULT 'claude'` to:
- `decisions`
- `session_log`
- `feature_evaluations`
- `features` (as `logged_by_agent`)

Also add an `agents` table:
```sql
CREATE TABLE agents (
  agent_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  agent_type TEXT NOT NULL,  -- 'claude' | 'maia' | 'nexus' | 'naya' | 'system'
  active INTEGER DEFAULT 1,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

Seed with: `('claude', 'Claude Code', 'claude', 1)`, `('system', 'QI Brain System', 'system', 1)`.

**Build impact:** 1 extra table, 4 extra columns. MCP tools accept optional `agent_id` param, default `'claude'`.

---

## I-06 — Bootstrap order correction  **[MEDIUM]**

**Problem in Plan 001:** Bootstrap steps were listed as schema → project seed → doc ingestion → session summary ingestion → EasyFlow decisions. But doc/summary ingestion requires the embedding provider to be configured first, which requires `llm_providers` to be seeded, which was listed last implicitly.

**Fix:** Explicit 8-step ordering with dependencies.

**Diff to Plan 001 Section 12 (Bootstrap Plan):** Replace with:
1. Create `qi_brain.db` with schema (includes PRAGMAs from I-02)
2. Seed `agents` table (I-05)
3. Seed `llm_providers` table (Ollama provider + nomic-embed-text embedder config)
4. Seed `brain_config` table (defaults: eval_model=qwen3:8b, embed_model=nomic-embed-text, token_budget=2000)
5. Seed `projects` table from `qi_registry.json`
6. Initialize ChromaDB collections (decisions, features, sessions, docs)
7. Ingest docs → ChromaDB (Standards, Map, Principles, CLAUDE.md) via nomic-embed-text
8. Ingest Session_Summaries/*.docx → ChromaDB
9. Seed 4 EasyFlow decisions (from 2026-04-18 handoff)
10. Log bootstrap completion to `session_log`

Each step is idempotent: re-running bootstrap skips completed steps. Tracked via a `bootstrap_log` table.

**Build impact:** `bootstrap.py` structured as 10 functions, one per step, with `if_not_done()` guards.

---

## I-07 — Backup & recovery  **[MEDIUM]**

**Problem in Plan 001:** No backup strategy. `qi_brain.db` becomes the ecosystem's memory — losing it is catastrophic.

**Fix:** Daily SQLite backup via `VACUUM INTO`, ChromaDB directory snapshot, 30-day retention.

**Diff to Plan 001:** Add Section 13.5 "Backup & Recovery":
- Location: `C:\UNIVERSAL\BACKUPS\qi_brain\YYYY-MM-DD\`
- Script: `qi_brain\tools\backup.py` — runs nightly via Windows Task Scheduler at 1:00 AM (after MaiaNightlySync at 0:30)
- SQLite: `sqlite3.connect(src).backup(sqlite3.connect(dst))` — safe with WAL, no lock
- ChromaDB: `shutil.copytree(qi_memory, backup_dir/qi_memory)` with Chroma in read-only mode during copy
- Retention: keep last 30 dated folders, delete older
- Restore: `tools\restore.py --date YYYY-MM-DD` — moves current to `.broken.<ts>/`, restores snapshot

**Build impact:** 1 new script (~80 LOC), 1 Task Scheduler entry. Deferred to end of Phase 5.

---

## I-08 — Add `qi.supersede_decision()` to MCP surface  **[MEDIUM]**

**Problem in Plan 001:** Decisions can be logged and read, but not formally superseded. Over time, old decisions become stale and mislead future sessions.

**Fix:** Add a tool + schema support.

**Diff to Plan 001 Section 6 (Schema):** Add columns to `decisions`:
```sql
superseded_by INTEGER REFERENCES decisions(decision_id),
superseded_at TEXT,
superseded_reason TEXT
```

**Diff to Plan 001 Section 9 (MCP tools):** Add tool #10:
```
qi.supersede_decision(
  old_decision_id: int,
  new_decision_id: int,  -- must already exist, logged via qi.log_decision
  reason: str
) -> {ok: bool}
```

`qi.get_context()` filters out superseded decisions by default. Optional `include_superseded=True` flag for audit views.

**Build impact:** 1 extra tool, 3 extra columns, 5 LOC in get_context filter.

---

## I-09 — Feed evaluation history back into future evaluations  **[LOW]**

**Problem in Plan 001:** Feature Propagation Engine evaluates each feature-to-project pair independently, with no memory of prior decisions for the same target project. Over time, the brain should learn: "Project X historically skips features from domain Y."

**Fix:** Before calling the LLM, fetch the last 5 evaluations for this target_project and include them in the prompt as "historical pattern." LLM uses them as context.

**Diff to Plan 001 Section 8:** Add to evaluation prompt:
```
HISTORICAL PATTERN for target {target_project_id} (last 5 evaluations):
- Feature "{name}" (domain={domain}) → {recommendation} ({reasoning_short})
- ...
Use this pattern only as soft context; do not let it override the current feature's merits.
```

**Build impact:** 1 extra query in `feature_engine.py`, ~20 LOC. Low priority — only matters after ~20 evaluations accumulated.

---

## I-10 — Add `qi.explain()` tool  **[LOW]**

**Problem in Plan 001:** No natural-language "why" tool. If Renne asks "why was decision AD-007 made?", current MCP surface requires fetching the decision and asking Claude to explain. Inefficient.

**Fix:** Dedicated tool that fetches a decision + its context (linked decisions, features, session) and formats a markdown explanation.

**Diff to Plan 001 Section 9:** Add tool #11:
```
qi.explain(
  subject_type: "decision" | "feature" | "session" | "project",
  subject_id: int | str
) -> {
  markdown: str,       -- ready to display
  citations: list      -- decision_ids, feature_ids, etc. referenced
}
```

Implementation: SQL joins + template, not another LLM call. Fast and deterministic.

**Build impact:** 1 extra tool, ~60 LOC.

---

## I-11 — Python migration needs backup + smoke test phases  **[MEDIUM]**

**Problem in Plan 001 Section 16:** Python migration (tomorrow) described 5 phases but missing explicit backup-before and smoke-test-after steps.

**Fix:** 7-phase plan instead of 5:
1. **Backup** — zip current `C:\1-AI\APPS\PYTHON\` (and any project venvs) to `C:\UNIVERSAL\BACKUPS\python_migration_2026-04-19\`
2. Install Python 3.11.8 to `C:\Python311\` (Install for all users)
3. Reinstall packages via `pip freeze` → `pip install -r`
4. Smoke test each project imports without error (small script per project)
5. Reconfigure 7 NSSM services to point to new Python path
6. Start each service, verify via dashboard
7. **Uninstall / archive** old Python only after 24h of stable operation

**Diff to Plan 001 Section 16:** Replace phase list with the 7-phase above.

**Build impact:** Separate effort tomorrow; documented here for completeness.

---

## I-12 — Named Cloudflare tunnel for Dashboard  **[LOW / FUTURE]**

**Problem in Plan 001:** Dashboard uses Cloudflare quick tunnel (random subdomain per restart). Brain tab remote access will be fragile.

**Fix:** Migrate to named tunnel (`qi-dashboard.<your-domain>.com`) when Brain is operational.

**Diff to Plan 001 Section 17 (Future Vision):** Add bullet:
> "Named Cloudflare tunnel for QI Dashboard — stable URL for Brain tab remote access. Requires Cloudflare account + domain (already owned)."

**Build impact:** Deferred. Not in scope for Brain build.

---

## I-13 — Apply model selection table to the build itself  **[HIGH — PROCESS]**

**Problem in Plan 001:** Plan assumed Sonnet throughout. Opus audit noted that architecture + schema review benefit from Opus, but implementation is pure Sonnet work. Building on all-Sonnet risks design mistakes; building on all-Opus wastes the weekly All-models bucket.

**Fix:** Explicit model assignment per phase, logged in `BUILD_LOG.md`.

**Diff to Plan 001 Section 15 (Implementation Order):** Add model column:

| Phase | Task | Model | Rationale |
|---|---|---|---|
| 0 | Supplement A (this doc) | Opus 4.7 | Audit + design fixes |
| 1 | Foundation (schema, providers, memory_store) | Sonnet 4.7 | Implementation |
| 2 | Server (FastAPI + MCP + engine + bootstrap) | Sonnet 4.7 | Implementation |
| 3 | Dashboard UI (Brain tab) | Sonnet 4.7 | Implementation |
| 4 | Integration (.claude.json, CLAUDE.md, registry) | Sonnet 4.7 | Implementation |
| 5 | Verification + first brain call ceremony | Sonnet 4.7 | Testing |
| A1 | Ollama grunt tasks (embeddings, docstrings, eval) | qwen3:8b / nomic-embed-text / qwen3:4b | Free local inference |

**Build impact:** Process rule. Renne switches UI dropdown to Sonnet after this doc is written.

---

## I-14 — Override mechanism for bad brain recommendations  **[MEDIUM]**

**Problem in Plan 001:** Feature Propagation Engine outputs `adopt/adapt/skip/discuss`. No path for Renne to disagree with the brain and have that correction stored + learned from.

**Fix:** Every evaluation can be overridden via `qi.override_evaluation(evaluation_id, new_recommendation, reason)`. Overrides are stored in a separate `evaluation_overrides` table and **fed back into future evaluations as training signal** (see I-09 synergy).

**Diff to Plan 001 Section 6 (Schema):** Add table:
```sql
CREATE TABLE evaluation_overrides (
  override_id INTEGER PRIMARY KEY,
  evaluation_id INTEGER NOT NULL REFERENCES feature_evaluations(evaluation_id),
  overridden_by TEXT NOT NULL,        -- 'renne' | agent_id
  new_recommendation TEXT NOT NULL,
  reason TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**Diff to Section 9:** Add tool #12:
```
qi.override_evaluation(
  evaluation_id: int,
  new_recommendation: str,
  reason: str,
  overridden_by: str = 'renne'
) -> {ok: bool, override_id: int}
```

**Build impact:** 1 extra table, 1 extra tool, ~30 LOC.

---

## Summary of Schema Additions (consolidated)

| Item | Target table | Column / Table |
|---|---|---|
| I-02 | all | WAL + busy_timeout PRAGMAs |
| I-05 | decisions, session_log, feature_evaluations, features | `agent_id` column |
| I-05 | — | NEW `agents` table |
| I-08 | decisions | `superseded_by`, `superseded_at`, `superseded_reason` |
| I-14 | — | NEW `evaluation_overrides` table |
| I-06 | — | NEW `bootstrap_log` table |

Final table count: **9** (was 7 in Plan 001, now +2).

## Summary of MCP Tool Additions (consolidated)

| Plan 001 | Supplement A | Final |
|---|---|---|
| 9 tools | +`qi.supersede_decision()`, +`qi.explain()`, +`qi.override_evaluation()` | **12 tools** |

---

## Acceptance

All 14 improvements are accepted and will be implemented as part of Phases 1–5. Plan 001 remains the canonical architecture document; this supplement is the authoritative override for the listed sections.

No further architecture changes expected before implementation. Any new issue discovered during Phase 1-5 will be logged in `BUILD_LOG.md` and may produce Supplement B (implementation log) at project end.

---

**End of Supplement A.**

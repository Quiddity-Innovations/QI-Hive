# QI Brain — Build Log

**Project:** QI Common Brain (Plan 001)
**Started:** 2026-04-18
**Location:** `C:\UNIVERSAL\qi_brain\`
**References:**
- `C:\UNIVERSAL\ECOSYSTEM\QI_Ecosystem_Plan_001_Brain_Architecture.md` (architecture)
- `C:\UNIVERSAL\ECOSYSTEM\QI_Ecosystem_Plan_001_Supplement_A_Audit_Diffs.md` (14 audit fixes)

---

## Phase 0 — Supplement A (Audit Diffs)

**Model:** Opus 4.7 · **Started:** 2026-04-18 23:xx · **Status:** ✅ Complete

- Wrote `QI_Ecosystem_Plan_001_Supplement_A_Audit_Diffs.md` — 14 improvements (I-01 through I-14)
- Created scaffold directories: `C:\UNIVERSAL\qi_brain\`, `C:\UNIVERSAL\qi_brain\LOGS\`, `C:\UNIVERSAL\BACKUPS\qi_brain\`
- Created this BUILD_LOG.md

**Key decisions locked by Supplement A:**
- MCP server = thin HTTP client to FastAPI :9010 (I-01)
- SQLite WAL mode mandatory (I-02)
- 9 tables total (added `agents`, `evaluation_overrides`, `bootstrap_log`)
- 12 MCP tools total (added `supersede_decision`, `explain`, `override_evaluation`)
- Bootstrap order: providers → config → projects → chroma → docs → summaries → decisions (I-06)
- Daily backup at 1:00 AM, 30-day retention (I-07)

**Handoff to Phase 1:** Switch UI model dropdown from Opus 4.7 → Sonnet 4.7. No other action needed — same session, same context, same todo list. Phase 1 begins when Renne confirms switch.

---

## Phase 1 — Foundation

**Model:** Sonnet 4.7 · **Status:** ⏳ Pending
**Scope:** schema.sql · providers/base.py · providers/ollama.py · memory_store.py · ollama_helper.py
**Target location:** `C:\UNIVERSAL\qi_brain\core\`

(to be filled in as work progresses)

---

## Phase 2 — Server

**Model:** Sonnet 4.7 · **Status:** ⏳ Pending
**Scope:** qi_brain_api.py (FastAPI :9010) · qi_brain_mcp.py (thin stdio) · feature_engine.py · bootstrap.py

---

## Phase 3 — Dashboard Brain Tab

**Model:** Sonnet 4.7 · **Status:** ⏳ Pending
**Scope:** Add `⬡ QI Brain` top-tab to `C:\UNIVERSAL\dashboard\static\index.html` with 6 sub-tabs (Ecosystem, Decisions, Features, Memory, Providers, Config)
**Related files:** `brain.js`, `brain.css`

---

## Phase 4 — Integration

**Model:** Sonnet 4.7 · **Status:** ⏳ Pending
**Scope:** Register `qi-brain` MCP in global `.claude.json` · Update `CLAUDE.md` with session-start/end protocol · Add `qi-brain` to `qi_registry.json` as backbone tier

---

## Phase 5 — Verification

**Model:** Sonnet 4.7 · **Status:** ⏳ Pending
**Scope:** Run bootstrap · Smoke-test 12 MCP tools + 15+ API endpoints · Log first decision ("First Brain Call" ceremony)

---

## Budget Log

| Date | Session start | Session end | % used (session) | % used (weekly All) | % used (weekly Sonnet) | Notes |
|---|---|---|---|---|---|---|
| 2026-04-18 | 23% | — | — | 26% | 20% | Opus session. $50.25/$50 extra — CAPPED until May 1. |

## Ollama Usage Log

| Date | Task | Model | Tokens saved (est) |
|---|---|---|---|
| — | — | — | — |

## Checkpoints

- [x] Phase 0 complete (Supplement A written)
- [ ] Phase 1 complete (foundation files)
- [ ] Phase 2 complete (server)
- [ ] Phase 3 complete (dashboard UI)
- [ ] Phase 4 complete (integration)
- [ ] Phase 5 complete (verification + first brain call)

---

**Next action:** Renne switches UI to Sonnet 4.7 → Phase 1 begins in this same session.

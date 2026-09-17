# QI Orchestrator — Meeting Minutes

---

## 2026-09-16 (evening) - Remediation Verification and Loop Closure
**Focus:** Prove the same-day remediation held, fix what the proofs exposed, and cross-check the corrected usage figures against an independent tool

### Key Findings
- **All overnight proofs pass** for today's run: backup OK with six databases and integrity ok, task health DEAD 0 / STALE 0, snapshot markers every ~30 min. The scheduled 03:15 and 06:10-06:40 jobs fire on their own for the first time tomorrow; all five were run manually today and every one returned rc 0.
- **The supervisor had been failing silently for 38 days.** A project with a placeholder registry path (`transfer_station`) produced a row with no `severity`, and `render_dashboard()` raised `KeyError`. Because `report.json` is written before `DASHBOARD.md`, the report looked healthy while the dashboard file froze at 2026-08-09. This is the "unattended jobs lie" pattern one layer in: the rc was visible on the Ops card, but nothing compared the artifact's mtime to the schedule.
- **The Headroom Status badge was checking the wrong port** (doctor default 8787 vs the registered proxy on 9020) and had been red since 2026-07-28 while the service was healthy the whole time.
- **The corrected usage figures hold up independently.** ccusage says $4,492.02 for the last 30 days, the Hive says $4,557.48 - a 1.46% gap, fully explained by UTC vs local date bucketing and by the Hive's finer cache-write tiering.

### Decisions
| Code | Decision | Date |
|------|----------|------|
| AD-027 | A project row with a missing or placeholder path is rated `red`, never left unrated - one unrated row must not be able to take down the whole ecosystem dashboard | 2026-09-16 |
| AD-028 | Ops health actions derive their exit code from the thing being guarded, not from a third-party tool's own rc; a check that can never go green is a defect, not a warning | 2026-09-16 |
| AD-029 | "w/ Local" offload rates are per-project from each project's own measured model mix; a single blended rate across projects is misleading and is now only a fallback | 2026-09-16 |
| AD-030 | Smoke tests cover every nav route and read-only API, so a tab that starts failing is a red test next run rather than a finding in the next audit | 2026-09-16 |

### Next Steps
1. Owner to supply the section 5 mismatch list, if any - every item was verified independently and passes.
2. Confirm tomorrow at or after 07:00 that the five scheduled ops actions fired on their own schedule, and that `backup_20260917.log` and the 2026-09-17 backup set exist.
3. Decide on renaming the 36 historical Agent HR rows to `builtin:<type>` (owner's call, not done).
4. Consider trimming the Health Check page's ~104 s cold render as the project count grows.

---


## 2026-09-16 — Full Feature Audit: LLM Usage Root Cause + Cross-Cutting Health
**Focus:** Audit all 25 dashboard tabs and infrastructure; identify why LLM Usage shows 6× inflation; document remediation roadmap

### Key Findings
- **LLM Usage inflation root cause:** Two-part bug: (1) JSONL line deduplication missing in _iter_events (Claude Code writes 2–5 lines per message); (2) MODEL_PRICING table stale since 2024 (predates Fable 5.1/5, Opus 5). Correction: 30-day $28,528 → $4,690; QTD/YTD inflated throughout.
- **Infrastructure failures:** QI_NightlyBackup targets deleted paths; qi_brain.db unprotected. Compliance page shows false-positive on claudemd_exists. Health/Ops stale data. Tunnels misses 4 active services.
- **Audit tally:** 9 working, 14 degraded, 2 broken, 1 dead

### Decisions
| Code | Decision | Date |
|------|----------|------|
| AD-024 | LLM Usage remediation delegated to Claude Opus 5; phases: (1) usage pipeline dedup+pricing, (2) backup repoint+health, (3) dashboard freshness, (4) dust | 2026-09-16 |
| AD-025 | Compliance scope separated: qi_hive verdict independent of other projects' orphan services | 2026-09-16 |
| AD-026 | Model pricing factored by era (2024 prices, Fable 5.1 era); reconstruction anchored to verified 2026-06-19 screenshot | 2026-09-16 |

### Next Steps
1. Opus 5 session: Phase 1 (usage dedup+pricing, 10–14 h) before any ledger migration
2. QI_NightlyBackup repoint + qi_brain.db backup health check (2–3 h)
3. Compliance nssm_registry scope fix (3–4 h)

---
## 2026-09-16 — Audit Remediation: All 19 Items Completed & Verified
**Focus:** Owner-delegated remediation of 19 audit findings; Fable 5.1 executed full scope; live verification on all 26 dashboard routes

### Owner Directive
"Execute full remediation; all 19 items. Fable 5.1 session end-to-end; verify each component live."

### Execution Summary
- **Phase 1 (usage pipeline):** message.id dedup + per-model pricing table with Fable 5.1 @ 0.025x; per-file cache + registry-driven attribution; historical rescale 2026-06-26→today (2.05× dedup, YTD $106k→$18.4k, 30d $28.5k→$4.5k); ledger v2 token-split; server.py live merge
- **Phase 2 (backup + health):** backup.py v2 targets C:\QIH\shared\backups\db\; 6 DBs 17:11 with markers; db_backup_now.py; nssm_registry fixed (38 orphan → real owners); claudemd_exists checks .claude/CLAUDE.md; qi_hive → 0 failures
- **Phase 3 (dashboard + Brain):** 14 tabs refreshed (Headlines/Tests/Tunnels/Ops/Health/Logs/Services/Mission Control/Claude Voice/EasyFlow/Board/War Room/Activity); Chroma 186→2,662 sessions; daily 03:15 backfill; qi_restart_service.py dep-safe NSSM
- **Phase 4 (hygiene):** phantom projects removed; 268 *.bak-* → archive (reversible); 3 legacy services removed; project_readiness gaps filled; Brain drift check PASS
- **Verification:** Single QI_Dashboard restart 17:31; all 26 routes GET 200; no tracebacks; 14 unit tests passing

### Decisions
| Code | Decision | Date |
|------|----------|------|
| AD-027 | Remediation complete; overnight proof TBD (owner verifies 01:00 backup + 03:15 chroma + 06:10 ops schedules) | 2026-09-16 |
| AD-028 | 21 legacy/unregistered services flagged for owner review (retire or register decision) | 2026-09-16 |

### Next Steps
1. Owner verification tomorrow: backup 01:00 rc=0, usage snapshot markers, ops schedules 06:10–06:40, chroma 03:15
2. Review & decide on 21 legacy/unregistered services
3. (Optional) cross-usage audit: usage_stats vs API logs to confirm dedup accuracy

---
## 2026-09-08 — Trinity check (owner directives + results)
**Focus:** Prove the Trinity setup works, that both assistants obey, and that it is dependable

### Owner directives (Renne, verbatim intent)
- "Make sure this setup is solid, coherent and dependable" — no mishaps managing the two assistants; both are on $20/month plans; "use them well but use them wisely".
- Test that they are obeying as Claude sees fit; document everything (Agent HR is the evidence trail).
- Learn each vendor's models and capabilities so the right model is picked per task and tokens/quota are not wasted.

### Decisions
| Code | Decision | Date |
|------|----------|------|
| AD-020 | Codex calls always name the model; CLI default pinned to gpt-5.6-terra, ladder luna → terra → sol, astra only with a stated reason | 2026-09-08 |
| AD-021 | Gemini free tier trains on submitted content → no client / PII / secret / BU / OnBase data ever goes to Gemini | 2026-09-08 |
| AD-022 | Trinity health is checked on demand via qi_trinity_check.py; never scheduled (nothing unattended calls an assistant) | 2026-09-08 |
| AD-023 | Every assistant run is recorded in Agent HR under project `trinity`; the 2026-10-16 trial review uses those rows | 2026-09-08 |

### Results
- All 13 inspection checks PASS; 6/6 obedience tests PASS; one pre-upgrade MCP process in this session is stale until Claude Code restarts.

### Next Steps
1. Restart Claude Code; run `qi_trinity_check.py --ping` to confirm the MCP path from a live session.
2. First real delegations: one Codex worktree task, one Gemini long-read; log both.
3. Refresh the model guide monthly (vendor docs are mid-rollout and inconsistent).

---
## 2026-04-19 — Documentation Enforcement + Architecture Decisions
**Focus:** Acknowledge and fix the documentation gap across all projects

### Decisions
- **Standard docs are MANDATORY for every project, always**
  Maia set the standard. Every subsequent project must have:
  Implementation Log, Meeting Minutes, Version History, Master Status Report.
  Failure to create them is a process failure — not just a missing file.
- **qi_new_project_wizard.py** now creates all 4 docs when scaffolding
- **Audit script** (qi_session/audit_docs.py) added to ecosystem tools
- **Standing rule added to CLAUDE.md:** At session start for any project,
  verify these docs exist. If missing, create them before starting work.

### Architecture Decisions (cumulative)
| Code | Decision | Date |
|------|----------|------|
| AD-001 | SQLite for all structured data | 2026-04-19 |
| AD-002 | ChromaDB for semantic/vector memory only | 2026-04-19 |
| AD-003 | All NSSM services prefixed QI_ | 2026-04-19 |
| AD-004 | NSSM binary standardized to C:\UNIVERSAL\dashboard\nssm.exe | 2026-04-19 |
| AD-005 | Zero hardcoded LLM config — all in DB | 2026-04-19 |
| AD-006 | Python path centralized in qi_python_config.json | 2026-04-19 |
| AD-007 | C:\UNIVERSAL is permanent home for all cross-project tooling | 2026-04-06 |
| AD-008 | Projects stay independent — Brain is purely additive | 2026-04-19 |

### Next Steps
1. Verify all docs now exist across all projects (audit_docs.py)
2. Add documentation check to session intelligence briefing
3. Review feature propagation decisions (8 pending)

---

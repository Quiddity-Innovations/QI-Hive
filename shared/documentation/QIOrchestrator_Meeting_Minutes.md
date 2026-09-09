# QI Orchestrator — Meeting Minutes

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

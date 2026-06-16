# QI Orchestrator — Meeting Minutes

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

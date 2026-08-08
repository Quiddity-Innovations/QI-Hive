---
name: project-documentation-standard
description: "Documentation Standard v1.0 (2026-06-20): every product keeps a living User Guide + Technical Documentation, updated in lock-step with the product, gated by tier, freshness visible on BU Hive /docs"
metadata: 
  node_type: memory
  type: project
  originSessionId: 2183a60e-0c2e-4f2b-b2b4-4ab99c05b5fa
---

Binding **Documentation Standard** set 2026-06-20: `C:\AI\Documentation\Documentation-Standard.md` (v1.0). Companion to [[project-structure-standard]] (which says *where* files live) and the AI-Workspace-Framework. Extends [[project-bu-hive]] (reference implementation) and [[project-claude-env-setup]] (brought into compliance).

**The rule:** every product/project carries TWO living doc sets, never blended:
- `docs/user-guide.md` — **User Guide**, for people who *use* it (task-oriented).
- `docs/technical.md` — **Technical Documentation**, for people who *change* it (architecture/config/data-model/interfaces).
- `docs/README.md` — optional docs index + local maintenance contract.

**Living-doc contract:** each doc starts with a header block (`**Last updated:** YYYY-MM-DD`) and ends with a `## Changelog`. Docs are updated **in the same unit of work** as the change they describe ("a feature shipped without its doc update is not done").

**Docs as a tier gate:** T1 stubs exist → T2 both complete+current → T3 user-guide validated by a non-author → T4 current at release. Enforced with override (recorded), like other gates.

**Visibility:** BU Hive `/docs` page (`app/docsmap.py` → `scan_docs()`, template `docs.html`, NAV System group) shows per registered project whether User Guide + Technical exist and whether each is current vs newest source mtime (current/stale/missing).

**Rollout done 2026-06-20:** authored the standard; Project-Structure-Standard bumped to v1.3 (§2.1.1 required `docs/` contents + PROJECT.md Documentation section); `_template/docs/` ships user-guide.md + technical.md + README.md skeletons; BU Hive split its blended GUIDE.md (reference impl); claude-env-setup brought into compliance (docs/phases.md kept as a technical sub-topic). Apply the SAME approach to every new product (CogniBase, onbase-client still need their docs authored as they mature).

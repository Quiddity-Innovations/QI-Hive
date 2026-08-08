---
name: project-structure-standard
description: "Binding folder/naming standard for every project — canonical names, override mechanism, where projects live"
metadata: 
  node_type: memory
  type: project
  originSessionId: 815d365b-c45b-41b0-8e56-d6310c70b7a6
---

Every project follows a single binding structure standard (v1.0, set 2026-06-19). Full spec: C:\AI\Documentation\Project-Structure-Standard.md.

**One canonical folder name per concept** (anti-drift — no "application" in one project, "program" in another):
- src (source code) · docs (documentation) · tests (tests) · examples (samples/demos) · build (output) · data · assets · config · scripts · content (non-code authored content)
- Core in every project: README.md, PROJECT.md, .gitignore, docs/

**Naming rules:** lowercase only; no spaces ever; multi-word = kebab-case; Python packages snake_case (only sanctioned exception); ISO 8601 / 24H for dates.

**Where things live (C:\AI taxonomy, v1.2 — boundary LOCKED by nature):** C:\AI\Products = ongoing/maintained applications/programs (users, long life); C:\AI\Projects = time-boxed work (experiments, one-offs, research, tooling — e.g. the install kit). Decided once at creation; NOTHING moves by lifecycle. Maturity = tier field (status); Dev/Test/Beta/Prod = deployment environments, not folders. Rare project→product transition = one-time logged override. C:\AI\BU Hive = BU Hive app (corrected from C:\BU\bu-hive). C:\BU root RETIRED — folder location doesn't change IP ownership; machine-wide rule stands (no Quiddity IP on this machine, never push BU code to personal repo).

**Runtime locations for developed apps (NOT Claude itself):** temp files → C:\AI Temp\<app-slug>\ ; error logs → C:\AI\Error\<app-slug>\ (error_<YYYY-MM-DD>.log). Read from .env TEMP_DIR/ERROR_DIR, never hardcoded. Note both C:\AI Temp (sibling, canonical for app temp + scratch) and C:\AI\Temp (child, my earlier scratch — drift to consolidate) exist.

**Override power (user has it):** deviations allowed but must be logged in the project's PROJECT.md "Structure overrides" table (deviation, reason, beyond-control?, approved-by, date). Framework-imposed layouts (Next.js, Django, node_modules) = "beyond control", auto-accepted but logged. Discretionary deviations need owner approval. Standard changes = version bump in the doc changelog.

**PROJECT.md** = per-project profile (slug, kind, owner, root, tier, status, gates, overrides) — feeds the BU Hive control panel.

Related: [[project-bu-laptop-setup]]. Master living doc: C:\AI\Documentation\AI-Workspace-Framework.md.

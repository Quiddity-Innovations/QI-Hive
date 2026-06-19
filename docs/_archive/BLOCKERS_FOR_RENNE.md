# Blockers / Decisions Needing Renne's Attention

Running log from this overnight session. I'll keep appending as I hit things. Items marked ⚠️ need Renne; items marked 💡 are just FYI.

---

## 2026-04-19 Overnight

### ⚠️ None blocking right now
All work so far is running autonomously. Will update as issues emerge.

### 💡 Observations
- **Naya / NEXUS / EasyFlow lack a formal INTRO folder.** Creating one per project and seeding status JSONs from their Master Status reports. If the generated JSONs look thin, that reflects doc coverage — not the product. Some fields will come back as `TBD — from code audit` until you either fill them or authorize a deeper introspection pass.
- **QI_Hive is not yet a "first-class" project** in the QI Brain `projects` table (I added it manually earlier tonight). It's also not in the ecosystem registry at `C:\UNIVERSAL\ECOSYSTEM\qi_registry.json`. Worth formalizing.
- **Claude_Manager, QI_Universal, FileHQ** — I've added them to the health check but they don't have Master Status reports, so their Project Status pages will be sparse. They may not need the full Maia-style treatment (Claude_Manager is retired orchestration, QI_Universal is a shared docs dir, FileHQ is merged into Naya).
- **`qi_hive` project ID in Brain** — I used `qi_hive` (with underscore). Renne's ecosystem uses `QI_Hive` for service, `QIH` for folder, `QI Hive` for display. Staying with `qi_hive` for now to match the other lowercase+underscore IDs in the brain; flag if you want different.

### Items that might need you tomorrow
- **Review the auto-generated status JSONs** for Naya/NEXUS/EasyFlow/QI_Hive and correct anything the subagent got wrong. Files will be at `C:\<PROJECT>\INTRO\status_*.json`.
- **Decide the QI Brain project_id naming convention** (`qi_hive` vs `QI_Hive`). Affects Brain queries and dashboard joins.
- **gsudo cache** — if you reboot, first elevation of the day re-prompts UAC. That's by design (8h lifetime). Just noting so you're not surprised.

---

## 2026-04-22 — Renne decisions applied

- ✅ **INTRO status JSONs** — reviewed, looks good for now
- ✅ **Brain project_id convention** — `qi_hive` (internal DB/API, enforced lowercase by Brain), `QI Hive` (display name in all UIs). Brain API's `_norm_pid()` forces lowercase so mixed-case IDs break FK constraints. Decision logged to Brain (#465).
- ✅ **Blueprint SVGs** — Renne wants them; tracked as pending task (implement after Claude Work dispatch integration is live)
- ✅ **Claude Desktop restart** — deferred; Renne will restart after Claude Work completes its current tasks

---

## Resolution / Dismissed
- `qi_hive` project_id → resolved as `QI_Hive` (2026-04-22)
- Naya/NEXUS/EasyFlow INTRO JSONs → accepted as-is (2026-04-22)
- ✅ `finalize_migration.bat` run as admin (2026-04-22) — QI_BrainAPI + QI_Dashboard repointed to C:\QIH, both SERVICE_RUNNING
- ✅ Claude Desktop restarted (2026-04-22) — permission bypass settings now active

# QI Orchestrator — Implementation Log

> Covers: QI Dashboard (port 9000) + QI Brain API (port 9010)
> Root: `C:\UNIVERSAL\`

---


## 2026-09-16 — Full Feature Audit: LLM Usage Root Cause + Cross-Cutting Health
**Session Focus:** Audit all 25 dashboard tabs, compliance, and cross-cutting systems; identify root cause of LLM Usage inflation; deliver remediation roadmap

### Audited
- 25 dashboard tabs: LLM Usage, Tests, War Room, Headlines, Tunnels, Compliance, Health, Ops, Guide, and 16 project status panels
- Compliance matrix, service registry, nightly backup pipeline, session logging, Brain Chroma index
- Found: 9 working · 14 degraded · 2 broken · 1 dead (War Room dormant since 2026-06-19)

### Found (root causes)
- **LLM Usage inflation 6.08×:** (1) usage_stats.py _iter_events counts per JSONL line; Claude Code writes 2–5 lines per message (one per content block) → 2–5× event inflation/day; (2) MODEL_PRICING table is 2 years stale (Opus $15/$75 → Opus 5 $5/$25, Fable $15/$75 → Fable 5.1 $10/$50, Sonnet $3/$15 → $2/$10, Haiku $0.80/$4 → $1/$5). Combined: 30-day window shows $28,528 → corrects to $4,690. QTD/YTD inflated end-to-end. 21% spend coded 'unknown' project.
- **QI_NightlyBackup fails:** targets deleted C:\UNIVERSAL paths; qi_brain.db has no backup anywhere (critical risk)
- **Compliance false-positive:** claudemd_exists check on .claude/CLAUDE.md always passes; nssm_registry lists 38 fails from orphan services in other projects (misattributed to qi_hive)
- **Health + Ops stale:** phantom projects (M2V, PersonalSong, Bakeoff) from health_check.py built at import; Ops badges from 2026-07-28 with rc=1
- **Tunnels hardcoded 13 ports, misses Kaze/MQ/Connector/Claude Voice**; Headlines '-5057s ago' UTC/local mismatch; Brain Chroma 186/2,636 sessions; 486 *.bak-* files

### Deliverable
- C:\QIH\shared\documentation\QIHive_Feature_Audit_2026-09-16.docx (+ .md twin) — 19 prioritised remediation items, ~45–60 h Opus 5 work in 4 phases

### Files
- NEW C:\QIH\shared\documentation\QIHive_Feature_Audit_2026-09-16.docx
- NEW C:\QIH\shared\documentation\QIHive_Feature_Audit_2026-09-16.md
- NEW C:\Users\renne\.claude\projects\C--QIH\memory\project_usage_tab_inflation_2026-09-16.md
- UPD C:\Users\renne\.claude\projects\C--QIH\memory\MEMORY.md (link to usage inflation analysis)
- NEW C:\QIH\shared\documentation\session_summaries\QI_Hive_Summary_2026-09-16_1650.docx

---
## 2026-09-16 — Full Remediation Execution: All 19 Audit Items Live-Verified
**Session Focus:** Owner-delegated full remediation of audit findings to Fable 5.1; all 19 prioritised items completed and verified end-to-end

### Executed
- **Usage pipeline dedup + pricing:** message.id deduplication in usage_stats.py; per-model pricing table (Fable 5.1 @ 0.025x cache-read); per-file incremental cache; registry-driven attribution; rescaled historical usage 2026-06-26→today (2.05× overall dedup factor). YTD $106k → $18.4k; 30d $28.5k → $4.5k. usage_ledger.py v2 with token-split columns; usage_recalibrate.py rescales old rows; server.py merges today live.
- **Backup repoint + health:** backup.py v2 targets C:\QIH\shared\backups\db\ (was targeting deleted C:\UNIVERSAL); 6 DBs backed up 17:11 with integrity checks + 'backup OK' marker; db_backup_now.py for ad-hoc; task registered QI_Scheduled_Tasks_Registry.md.
- **Compliance scope fix:** inspector claudemd_exists now accepts .claude/CLAUDE.md; nssm_registry correctly attributes 38 orphan services to owning project (was misbooked to qi_hive); Brain /api/compliance/status excludes inspector_verdict (now self_assessment); qi_hive shows 0 failures post-restart.
- **Brain Chroma index:** chroma_backfill.py indexed sessions 187 → 2,662; hive_ingest.py + poller.py embed on write; daily 03:15 schedule set.
- **Dashboard 14-tab refresh:** Headlines UTC-aware ages; Tests repointed pytest report; Tunnels from tunnels.json (Kaze/MQ/Connector visible); Ops badges/schedules seeded; Health force refresh; Logs app-log root + caps; Services legacy/unregistered badges (21 flagged); Mission Control roster/feed; Claude Voice banner; EasyFlow 'blocked' badge; Board updated_at + project norm; War Room/Dispatch → LABS; Activity 60 s refresh.
- **New tooling:** qi_restart_service.py dependency-safe NSSM restart (sc stop fails 1051 for QI_BrainAPI; inverse dependency tree from registry); Ops actions chroma_backfill + remove_legacy_services.
- **Hygiene:** health_check.py rebuilds on registry change; phantom M2V/PersonalSong/Bakeoff removed; 268 *.bak-* files → C:\QIH\_archive\bak_2026-09-16 (reversible); 3 legacy services (ClaudeManager, NayaTunnel, NEXUSTunnel) removed; project_readiness.json gaps filled.
- **Verification:** Single QI_Dashboard restart 17:31; all 26 routes GET 200; no tracebacks.

### Test Coverage
- 14 unit tests (test_usage_stats.py): 10 test + 4 smoke = 14 passing
- Smoke tests added per route; can extend to POST endpoints

### Files
- UPD engine/common/usage_stats.py (v2, dedup logic)
- UPD engine/common/usage_ledger.py (v2, token-split columns)
- NEW engine/common/usage_recalibrate.py (historical rescale)
- UPD engine/brain/tools/backup.py (v2, C:\QIH\shared\backups\db\)
- NEW engine/brain/tools/db_backup_now.py (ad-hoc backup)
- NEW engine/hive/tools/qi_restart_service.py (dep-safe restart)
- UPD engine/hive/dashboard/server.py (14 tabs)
- UPD engine/hive/dashboard/health_check.py (rebuild on registry change)
- UPD engine/hive/agents/agent_hr.py (normalise agent names)
- NEW engine/hive/dashboard/tests/test_usage_stats.py (14 tests)
- NEW engine/hive/tools/archive_bak_files.py (hygiene)
- UPD ecosystem/QI_Service_Registry.md (3 legacy removed, 48 total)
- UPD ecosystem/QI_Scheduled_Tasks_Registry.md (backup task)
- UPD data/project_readiness.json (gaps filled)
- UPD shared/documentation/QI_Claude_Manager_Guide.md (25 tabs)
- NEW session_summaries/QI_Hive_Summary_2026-09-16_1745.docx
- UPD .claude/projects/C--QIH/memory/MEMORY.md (links)
- NEW _archive/bak_2026-09-16/ (268 files, reversible)
- NEW _archive/legacy_services_2026-09-16.json (rollback record)

---
## 2026-09-08 — Trinity check: both assistants verified, obedience-tested, guarded
**Session Focus:** Verify the tri-platform arrangement (Claude + Codex/ChatGPT Plus + Gemini free tier) end-to-end; make it dependable; document for the §11a trial

### Built
- `C:\QIH\engine\tools\qi_trinity_check.py` — on-demand health check (13 checks: MCP wiring, Gemini key/config/quota/model visibility via ListModels, Codex CLI version vs npm latest, login, stale MCP processes, plan-visible models; `--ping` adds one cheap call per leg and records to Agent HR). Report → `C:\QIH\data\trinity\`, log → `C:\QIH\LOGS\trinity_check.log`. Never scheduled — nothing unattended calls an assistant.
- `C:\QIH\shared\documentation\plans\QI_Trinity_Model_Guide_2026-09-08.md` — per-model selection guide for both sides (Plus quota per model, Gemini free-tier data policy, decision procedure).
- WSL `~/.codex/config.toml` — pins `model = "gpt-5.6-terra"`, `sandbox_mode = "read-only"` so a call that forgets `model` no longer burns the gpt-6-astra window (5–45 msgs/5h) by default.
- Agent HR roster: `codex` and `gemini` onboarded as kind=assistant; 9 test runs recorded under project `trinity`.

### Fixed / found
- Codex MCP failed from Claude Code: CLI 0.118.0 cannot decode the current `/models` response (new `max` effort level), fell back to `gpt-5.3-codex`, refused for ChatGPT-plan logins. CLI upgraded to 0.153.4 (17:18 local, Windows-side `npm i -g`); a Claude Code restart is needed for this session's MCP process to pick it up.
- Stale-process detection: `readlink /proc/<pid>/exe` shows `(deleted)` on the native child, but `$(...)` inside an inline `wsl.exe bash -lc` string is mangled and reported 0 stale; probe moved to companion `qi_trinity_check_codex.sh` (emits JSON). Verified: 5 stale native processes flagged.

### Verified
- Fresh `codex mcp-server` 0.153.4 over JSON-RPC: initialize → tools/list → tools/call OK (6 s).
- Codex (gpt-5.6-luna): verifiable read-only task correct (def_count 18), "no commands" honoured (0 executions), read-only sandbox held when asked to write.
- Gemini (3.6-flash): strict JSON schema honoured; system instruction beat a conflicting user prompt.

### Files
- NEW `C:\QIH\engine\tools\qi_trinity_check.py`
- NEW `C:\QIH\shared\documentation\plans\QI_Trinity_Model_Guide_2026-09-08.md`
- NEW WSL `/home/hyosuke/.codex/config.toml`
- UPD `C:\QIH\shared\documentation\plans\QI_TriPlatform_AI_Orchestration_Plan_2026-09-08.md` (§14 check log)
- UPD `C:\QIH\engine\hive\agents\agent_hr.db` (roster + runs)

---
## 2026-04-19 — Full QI_ Service Rename Sweep + Brain + Backup
**Session Focus:** Rename all NSSM services to QI_ prefix; build Brain API; nightly backup

### Built
- QI Brain API (C:\UNIVERSAL\qi_brain\) — FastAPI on port 9010
  - Decision memory (SQLite + ChromaDB)
  - Feature propagation engine (qwen3:8b evaluates cross-project ideas)
  - Session logging
  - Semantic search (nomic-embed-text)
  - MCP tool (qi_brain_mcp.py)
- Nightly backup (backup.py + Task Scheduler at 1AM, 30-day retention)
  - Backs up all 5 QI databases using sqlite3.Connection.backup()
- Full rename sweep: 19 files updated across all projects to QI_ prefix
  - QI_MaiaBot, QI_MaiaTunnel, QI_MaiaDemoTunnel
  - QI_NayaBot, QI_NayaGradio
  - QI_NEXUS, QI_Dashboard, QI_DashboardTunnel, QI_BrainAPI

---

## 2026-04-19 — Training Docs + Ecosystem Health Tab
**Session Focus:** Training documentation; live health monitoring in Dashboard

### Built
- 3 professional training Word docs in C:\UNIVERSAL\TRAINING\ORCHESTRATOR\:
  - 01_QI_Orchestrator_Architecture.docx (41.5 KB)
  - 02_QI_Orchestrator_Operations.docx (40.6 KB)
  - 03_QI_Orchestrator_ProjectStatus.docx (41.6 KB)
- /api/ecosystem/health endpoint — live sc query all 9 QI_ services
- Ecosystem Health sub-tab in Project Status panel (Dashboard UI)
- qi-dashboard.json updated to v1.1.0 as "QI Orchestrator"

---

## 2026-04-19 — Session Intelligence + Python Path Centralization
**Session Focus:** Automatic project context loading; central Python config

### Built
- qi_session/ module: qi_context_loader.py + qi_new_project_wizard.py
- UserPromptSubmit hook (user_prompt_hook.py) — auto-loads project context
- session_context.py rewritten — global ecosystem briefing at session start
- qi_python_config.json — single source of truth for Python path
- qi_python.bat + qi_python.ps1 + qi_python.py — central Python bootstrap
- GET/PUT :9000/api/python_path — Dashboard API endpoint
- All NAYA installers + backup task updated to reference central config

### Files Changed
- C:\UNIVERSAL\qi_session\qi_context_loader.py (NEW)
- C:\UNIVERSAL\qi_session\qi_new_project_wizard.py (NEW)
- C:\UNIVERSAL\qi_python_config.json (NEW)
- C:\UNIVERSAL\qi_python.bat (NEW)
- C:\UNIVERSAL\qi_python.ps1 (NEW)
- C:\UNIVERSAL\qi_python.py (NEW)
- C:\Users\renne\.claude\session_context.py (REWRITTEN)
- C:\Users\renne\.claude\user_prompt_hook.py (NEW)
- C:\Users\renne\.claude\settings.json (UserPromptSubmit hook added)
- C:\UNIVERSAL\dashboard\qi_dashboard.py (+python_path endpoints)
- C:\APPS\NAYA\tools\*.ps1 (4 files — qi_python.ps1 dot-source)
- C:\UNIVERSAL\qi_brain\tools\install_backup_task.bat (qi_python.bat call)

---

## 2026-04-06 — Universal Control Panel + Ecosystem Reorganisation
**Session Focus:** QI Universal Control Panel; ecosystem moved to C:\UNIVERSAL\ECOSYSTEM

### Built
- QI Universal Control Panel bat (menu launcher, Windows Terminal tabs)
- Ecosystem folder moved from C:\APPS\QI\ECOSYSTEM → C:\UNIVERSAL\ECOSYSTEM
- All CLAUDE.md files updated across all projects
- MaiaNightlySync rescheduled to 9PM

---

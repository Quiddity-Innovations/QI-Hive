# QI Orchestrator — Version History

---


## v1.4 — 2026-09-16 (Audit Remediation Build)
**Type:** Full infrastructure remediation — usage pipeline, backups, compliance, dashboards, hygiene
**Version String:** 3.0.0 (unchanged; remediation build)
### Added
- `engine/common/usage_stats.py` v2 (message.id dedup, per-model pricing with Fable 5.1 @ 0.025x)
- `engine/common/usage_ledger.py` v2 (token-split columns, pricing_version for audit)
- `engine/common/usage_recalibrate.py` (historical rescale without deletion, 2.05× dedup factor)
- `engine/brain/tools/backup.py` v2 (C:\QIH\shared\backups\db\ target with integrity checks + marker)
- `engine/brain/tools/db_backup_now.py` (ad-hoc backup tool)
- `engine/hive/tools/qi_restart_service.py` (NSSM restart with dependency awareness)
- `engine/hive/dashboard/tests/test_usage_stats.py` (14 unit + smoke tests)
- `engine/hive/tools/archive_bak_files.py` (268 *.bak-* → archive, reversible)
- `_archive/bak_2026-09-16/` (reversible archive of old backup files)
- `_archive/legacy_services_2026-09-16.json` (rollback record)
### Updated
- `engine/common/usage_backfill.py` (safety gate: --reinflate-ok required)
- `engine/hive/dashboard/server.py` (14 tabs: Headlines, Tests, Tunnels, Ops, Health, Logs, Services, Mission Control, Claude Voice, EasyFlow, Board, War Room, Activity; 26 routes all 200)
- `engine/hive/dashboard/health_check.py` (rebuild on qi_registry.json change; phantom projects removed)
- `engine/hive/agents/agent_hr.py` (agent name normalisation, project re-attribution)
- `ecosystem/QI_Service_Registry.md` (3 legacy services removed, 48 total)
- `ecosystem/QI_Scheduled_Tasks_Registry.md` (backup task registered)
- `data/project_readiness.json` (gaps filled, additive)
- `shared/documentation/QI_Claude_Manager_Guide.md` (expanded to 25 tabs)
### Fixed
- **LLM Usage inflation:** 6.08× error corrected; YTD $106,020 → $18,380; 30d $28,528 → $4,537
- **QI_NightlyBackup:** repointed from deleted C:\UNIVERSAL to C:\QIH\shared\backups\db\; 6 DBs backed 17:11
- **Compliance false-positives:** nssm_registry orphan services (38) correctly attributed; claudemd_exists scoped; qi_hive → 0 failures
- **Dashboard route health:** 26/26 GET 200 after single QI_Dashboard restart (17:31)
- **Brain Chroma index:** sessions 186 → 2,662; daily backfill @ 03:15
- **Service orphans:** 3 legacy services removed (ClaudeManager, NayaTunnel, NEXUSTunnel); 21 unregistered flagged for review
### Verification
- Single dashboard restart (17:31); all routes verified 200
- 14 unit tests: 10 test + 4 smoke = all passing
- Smoke tests per route; POST endpoint tests added to future roadmap

---
## v1.3 — 2026-09-08
**Type:** Trinity assistant layer — health check + model guide
### Added
- `engine/tools/qi_trinity_check.py` (13 checks, `--ping`, `--json`, Agent HR recording)
- `plans/QI_Trinity_Model_Guide_2026-09-08.md`
- WSL `~/.codex/config.toml` safe defaults (terra, read-only)
- Agent HR: assistant roster entries `codex`, `gemini`
### Fixed
- Codex CLI 0.118.0 → 0.153.4 (stale CLI rejected every model on ChatGPT-plan login)

---
## v1.2 — 2026-04-19
**Type:** Documentation enforcement + Python path centralization
### Added
- Standard docs created for all QI projects (was missing for 5 projects)
- qi_session/ module: context loader, new project wizard, audit tool
- Session Intelligence System: auto-detect project, inject context
- qi_python_config.json + qi_python.bat/ps1/py — central Python bootstrap
- GET/PUT :9000/api/python_path — live Python config API

---

## v1.1 — 2026-04-19
**Type:** Training docs + ecosystem health
### Added
- 3 professional training Word docs (Architecture, Operations, Project Status)
- /api/ecosystem/health — live sc query all 9 QI_ services
- Ecosystem Health sub-tab in Project Status panel
- qi-dashboard.json updated to v1.1.0

---

## v1.0 — 2026-04-19
**Type:** Full QI_ service rename sweep + Brain API + nightly backup
### Added
- QI Brain API (port 9010) — full decision memory + feature propagation
- Nightly backup (1AM, all 5 DBs, 30-day retention)
- 19 files updated to QI_ naming convention
- QI Service Registry (single source of truth for all 9 services)

---

## v0.3 — 2026-04-06
**Type:** Universal Control Panel + ecosystem reorganisation
### Added
- QI Universal Control Panel (Windows Terminal multi-tab launcher)
- Ecosystem files moved to C:\UNIVERSAL\ECOSYSTEM

---

## v0.2 — 2026-03-29 (estimated)
**Type:** Dashboard enhancements
### Added
- Project Status sub-tab system (JSON-driven)
- Agent profiles (8 named agents)
- Calendar integration
- Chat window
- 5 visual themes

---

## v0.1 — 2026-03-22 (estimated)
**Type:** Initial build
### Built
- QI Dashboard — FastAPI SPA on port 9000
- WebSocket real-time updates
- Task board, delegations, test results, audit log
- Cloudflare tunnel integration

---

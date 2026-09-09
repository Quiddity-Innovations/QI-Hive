# QI Orchestrator — Implementation Log

> Covers: QI Dashboard (port 9000) + QI Brain API (port 9010)
> Root: `C:\UNIVERSAL\`

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

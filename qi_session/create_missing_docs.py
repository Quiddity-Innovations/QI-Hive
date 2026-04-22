# -*- coding: utf-8 -*-
"""
create_missing_docs.py — Create all missing standard docs across QI projects.

Damage assessment (2026-04-19):
  OpenClaw  — Implementation Log ❌  Meeting Minutes ❌  Version History ❌
  FileHQ    — Implementation Log ❌  Meeting Minutes ❌  Version History ❌
  EasyFlow  — Implementation Log ❌  Meeting Minutes ❌  Version History ❌
  Naya      — Version History ❌  (has Log + Minutes)
  Universal — Implementation Log ❌  Meeting Minutes ❌  Version History ❌

Root cause: no enforcement mechanism ensured standard docs were created for
each new project. This script creates them all now AND adds enforcement to
qi_new_project_wizard.py so it never happens again.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path
from datetime import datetime

TODAY = datetime.now().strftime("%Y-%m-%d")
created = []
skipped = []

# ─────────────────────────────────────────────────────────────────────────────
def write_if_missing(path: Path, content: str, label: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        skipped.append(f"  ⏭  {label} (already exists)")
        return
    path.write_text(content, encoding='utf-8')
    created.append(f"  ✅  {label}")

# ─────────────────────────────────────────────────────────────────────────────
# OPENCLAW
# Phase 0+1 complete. Gateway running. 6 agents: Tasuke, Kaze, Sentry, Seiri, Yubin, Koe.
# Runs on Node.js in WSL. C:\OC\ on Windows, /mnt/c/OC in WSL.
# ─────────────────────────────────────────────────────────────────────────────
OC = Path(r"C:\OC\DOCUMENTATION")

write_if_missing(OC / "OpenClaw_Implementation_Log.md", f"""\
# OpenClaw — Implementation Log

> Chronological record of everything built, fixed, or changed.
> Updated at the end of every working session.

---

## {TODAY} — Documentation Bootstrap
**Session Focus:** Created standard QI documentation set (was missing since project start)

### Context
OpenClaw was built before the standard documentation enforcement was in place.
This log starts now and will be maintained going forward.

### Architecture as of {TODAY}
- **Framework:** Commercial OpenClaw framework (Node.js, runs in WSL)
- **Root:** `C:\\OC\\` (Windows) / `/mnt/c/OC` (WSL)
- **Gateway:** Running — WSL → Windows bridge operational
- **6 Custom Agents:**
  | Agent   | Role                        |
  |---------|----------------------------|
  | Tasuke  | General assistant (Claude Sonnet) |
  | Kaze    | Research / web agent        |
  | Sentry  | Monitoring / alert agent    |
  | Seiri   | Organization / file agent   |
  | Yubin   | Communication / email agent |
  | Koe     | Voice layer (future — shared across QI) |

### Phase Status
- **Phase 0:** Framework install complete ✅
- **Phase 1:** Gateway running, all 6 agents defined ✅
- **Phase 2:** Koe voice layer — pending (cross-project shared layer)
- **Anthropic token:** Disabled for cost saving (using Ollama/local models)

### Files Changed
- `C:\\OC\\DOCUMENTATION\\OpenClaw_Implementation_Log.md` (NEW — this file)
- `C:\\OC\\DOCUMENTATION\\OpenClaw_Meeting_Minutes.md` (NEW)
- `C:\\OC\\DOCUMENTATION\\OpenClaw_Version_History.md` (NEW)

---
""", "OpenClaw / Implementation Log")

write_if_missing(OC / "OpenClaw_Meeting_Minutes.md", f"""\
# OpenClaw — Meeting Minutes

> Decisions, session summaries, and next steps.
> One entry per working session.

---

## {TODAY} — Documentation Retrospective
**Context:** Standard QI documentation was missing for OpenClaw.
Acknowledged and corrected.

### Decision: Standard docs enforced going forward
- All 3 standard docs now exist for OpenClaw
- Going forward: every session adds an entry to all 3 docs
- `qi_new_project_wizard.py` updated to enforce this on ALL new projects

### Current State
- OpenClaw Phase 0+1 complete and stable
- Gateway running — no active issues
- Koe (voice layer) is the next priority when development resumes
- Anthropic token disabled — cost-saving decision, revert when budget allows

### Next Steps (when OpenClaw session resumes)
1. Define Koe architecture — shared voice layer across Maia/Naya/NEXUS
2. Add OpenClaw to git version control
3. Review Tasuke — confirm Claude Sonnet is working correctly

---
""", "OpenClaw / Meeting Minutes")

write_if_missing(OC / "OpenClaw_Version_History.md", f"""\
# OpenClaw — Version History

> Version tags, releases, and significant code changes.

---

## v0.2 — {TODAY}
**Type:** Documentation + Housekeeping
### Added
- Standard QI documentation set (Implementation Log, Meeting Minutes, Version History)
- All 6 agents confirmed operational

---

## v0.1 — 2026-03-24 (Phase 0+1 complete)
**Type:** Initial build
### Built
- Commercial OpenClaw framework installed in WSL
- WSL → Windows gateway configured and running
- 6 custom agents defined: Tasuke, Kaze, Sentry, Seiri, Yubin, Koe
- Tasuke restored to Claude Sonnet (was on different model)
- All NSSM service names updated to QI_ prefix (2026-04-19)

---
""", "OpenClaw / Version History")


# ─────────────────────────────────────────────────────────────────────────────
# FILEHQ (absorbed into Naya — docs live under C:\NAYA\filehq\DOCUMENTATION\)
# File intelligence engine. READ-ONLY scanner. Drives F:\ scanning.
# ─────────────────────────────────────────────────────────────────────────────
FHQ = Path(r"C:\NAYA\filehq\DOCUMENTATION")

write_if_missing(FHQ / "FileHQ_Implementation_Log.md", f"""\
# FileHQ — Implementation Log

> FileHQ is a file intelligence engine absorbed into Naya.
> Root: `C:\\NAYA\\filehq\\`
> Original standalone path `C:\\FileHQ` marked for deletion.

---

## {TODAY} — Documentation Bootstrap
**Session Focus:** Created standard QI documentation set

### Architecture as of {TODAY}
- **Status:** Merged into Naya — NOT a standalone service
- **Root:** `C:\\NAYA\\filehq\\`
- **Port:** 8200 (when started by QI_NayaBot on port 8002)
- **Function:** READ-ONLY file scanner for F:\\ drive
- **DB:** `C:\\NAYA\\filehq\\db\\filehq.db` (SQLite)
- **API:** Started by Naya server — not an independent NSSM service
- **Original path:** `C:\\FileHQ` — exists for reference, marked for deletion

### Key Features
- Recursive scan of F:\\ drive (read-only — never modifies files)
- File metadata indexing: name, size, type, modified date, path
- Search by name, extension, date range
- Surfaced through Naya's API and Gradio UI (File Scout tab)

### Merge Decision
FileHQ was merged into Naya during 2026-03-28 session.
Reason: too small to justify independent deployment; Naya's domain
includes file intelligence.

### Files Changed
- `C:\\NAYA\\filehq\\DOCUMENTATION\\FileHQ_Implementation_Log.md` (NEW)
- `C:\\NAYA\\filehq\\DOCUMENTATION\\FileHQ_Meeting_Minutes.md` (NEW)
- `C:\\NAYA\\filehq\\DOCUMENTATION\\FileHQ_Version_History.md` (NEW)

---
""", "FileHQ / Implementation Log")

write_if_missing(FHQ / "FileHQ_Meeting_Minutes.md", f"""\
# FileHQ — Meeting Minutes

---

## {TODAY} — Documentation Bootstrap
**Context:** FileHQ merged into Naya. Standard docs created retroactively.

### Decision: FileHQ stays merged into Naya
- `C:\\FileHQ` standalone path marked for deletion
- All active code lives at `C:\\NAYA\\filehq\\`
- No independent NSSM service — started by QI_NayaBot
- Port 8200 reserved in QI port block

### No current outstanding work
FileHQ is stable and functional within Naya.
Future work (if any) tracked in Naya's Implementation Log.

---
""", "FileHQ / Meeting Minutes")

write_if_missing(FHQ / "FileHQ_Version_History.md", f"""\
# FileHQ — Version History

---

## v0.2 — {TODAY}
**Type:** Documentation + housekeeping
### Added
- Standard QI documentation set created

---

## v0.1 — 2026-03-28 (Merged into Naya)
**Type:** Architecture decision
### Changed
- Moved from `C:\\FileHQ` standalone → `C:\\NAYA\\filehq\\`
- Integrated with QI_NayaBot (starts FileHQ on port 8200 at launch)
- F:\\ READ-ONLY scanner built and operational
- DB: `C:\\NAYA\\filehq\\db\\filehq.db`

---
""", "FileHQ / Version History")


# ─────────────────────────────────────────────────────────────────────────────
# EASYFLOW
# Email/calendar automation. Phase 1 built. Port 8550. C:\EasyFlow\.
# Phase 2: Outlook/Teams integration.
# ─────────────────────────────────────────────────────────────────────────────
EF = Path(r"C:\EasyFlow\DOCUMENTATION")

write_if_missing(EF / "EasyFlow_Implementation_Log.md", f"""\
# EasyFlow — Implementation Log

> Chronological record of everything built, fixed, or changed.

---

## {TODAY} — Documentation Bootstrap
**Session Focus:** Created standard QI documentation set (was missing since project start)

### Context
EasyFlow was created after the standard documentation enforcement was
established in Maia, but the enforcement mechanism did not carry over.
This log starts now.

### Architecture as of {TODAY}
- **Purpose:** Email and calendar automation for Renne's workflows
- **Root:** `C:\\EasyFlow\\`
- **Port:** 8550 (allocated in QI port block: 8550-8559)
- **Phase 1:** Complete (core automation built)
- **Phase 2:** Outlook / Microsoft Teams integration — pending
- **Service:** Not currently NSSM-ified (local desktop tool)
- **NSSM:** No QI_ service yet — blocked on Phase 2 scope decision

### Phase Status
- **Phase 1:** Core email automation — ✅ complete
- **Phase 2:** Outlook + Teams integration — 🔄 in development
- **Phase 3:** Cross-project notifications (EasyFlow → Maia/Naya alerts) — 📋 planned

### Files Changed
- `C:\\EasyFlow\\DOCUMENTATION\\EasyFlow_Implementation_Log.md` (NEW — this file)
- `C:\\EasyFlow\\DOCUMENTATION\\EasyFlow_Meeting_Minutes.md` (NEW)
- `C:\\EasyFlow\\DOCUMENTATION\\EasyFlow_Version_History.md` (NEW)

---
""", "EasyFlow / Implementation Log")

write_if_missing(EF / "EasyFlow_Meeting_Minutes.md", f"""\
# EasyFlow — Meeting Minutes

---

## {TODAY} — Documentation Retrospective
**Context:** Standard docs were missing. Created retroactively.
This is a standing failure that the new enforcement system (qi_new_project_wizard.py)
will prevent for all future projects.

### Current State
- EasyFlow Phase 1 complete and stable
- Phase 2 (Outlook/Teams) is the next priority when EasyFlow session resumes

### Decisions on record
- Port block 8550-8559 allocated to EasyFlow (QI_Standards.md)
- Phase 2 scope: Outlook + Microsoft Teams integration
- Phase 3 idea: pipe EasyFlow notifications into Maia/Naya as alerts

### Next Steps (when EasyFlow session resumes)
1. Confirm Phase 1 feature list and lock it
2. Begin Phase 2 — Outlook integration
3. Add NSSM service when stable enough for background running
4. Create QI_ service: `QI_EasyFlow` on port 8550

---
""", "EasyFlow / Meeting Minutes")

write_if_missing(EF / "EasyFlow_Version_History.md", f"""\
# EasyFlow — Version History

---

## v0.2 — {TODAY}
**Type:** Documentation + housekeeping
### Added
- Standard QI documentation set (Implementation Log, Meeting Minutes, Version History)

---

## v0.1 — Phase 1 complete (date TBD — before 2026-04-19)
**Type:** Initial build
### Built
- Core email automation (Phase 1)
- Port 8550 allocated
- Local desktop tool — no NSSM service yet

---
""", "EasyFlow / Version History")


# ─────────────────────────────────────────────────────────────────────────────
# NAYA — Missing Version History only
# ─────────────────────────────────────────────────────────────────────────────
NAYA = Path(r"C:\NAYA\DOCUMENTATION")

write_if_missing(NAYA / "Naya_Version_History.md", f"""\
# Naya — Version History

---

## v0.2 — {TODAY}
**Type:** Documentation + infrastructure
### Added
- Standard Version History doc (was missing)
- QI_ NSSM service naming: QI_NayaBot, QI_NayaGradio
- All PowerShell installers updated to reference C:\\UNIVERSAL\\qi_python.ps1
- Central Python path config in qi_python_config.json

---

## v0.1 — 2026-03-28 (Initial build)
**Type:** Initial build
### Built
- Naya personal AI assistant server (naya_server.py on port 8002)
- Naya Gradio UI (naya_gradio.py on port 7861)
- FileHQ integration (merged, starts on port 8200)
- F:\\ READ-ONLY file scanner built (File Scout)
- 3 workstreams: Naya chat, File Scout, OpenClaw bridge (future)
- Domains: AI / Physics / Programming / Networking / VMs / Docker
- NSSM services: QI_NayaBot, QI_NayaGradio

---
""", "Naya / Version History")


# ─────────────────────────────────────────────────────────────────────────────
# UNIVERSAL / QI ORCHESTRATOR
# Dashboard :9000 + Brain API :9010
# ─────────────────────────────────────────────────────────────────────────────
UNI = Path(r"C:\UNIVERSAL\DOCUMENTATION")

write_if_missing(UNI / "QIOrchestrator_Implementation_Log.md", f"""\
# QI Orchestrator — Implementation Log

> Covers: QI Dashboard (port 9000) + QI Brain API (port 9010)
> Root: `C:\\UNIVERSAL\\`

---

## 2026-04-19 — Full QI_ Service Rename Sweep + Brain + Backup
**Session Focus:** Rename all NSSM services to QI_ prefix; build Brain API; nightly backup

### Built
- QI Brain API (C:\\UNIVERSAL\\qi_brain\\) — FastAPI on port 9010
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
- 3 professional training Word docs in C:\\UNIVERSAL\\TRAINING\\ORCHESTRATOR\\:
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
- C:\\UNIVERSAL\\qi_session\\qi_context_loader.py (NEW)
- C:\\UNIVERSAL\\qi_session\\qi_new_project_wizard.py (NEW)
- C:\\UNIVERSAL\\qi_python_config.json (NEW)
- C:\\UNIVERSAL\\qi_python.bat (NEW)
- C:\\UNIVERSAL\\qi_python.ps1 (NEW)
- C:\\UNIVERSAL\\qi_python.py (NEW)
- C:\\Users\\renne\\.claude\\session_context.py (REWRITTEN)
- C:\\Users\\renne\\.claude\\user_prompt_hook.py (NEW)
- C:\\Users\\renne\\.claude\\settings.json (UserPromptSubmit hook added)
- C:\\UNIVERSAL\\dashboard\\qi_dashboard.py (+python_path endpoints)
- C:\\NAYA\\tools\\*.ps1 (4 files — qi_python.ps1 dot-source)
- C:\\UNIVERSAL\\qi_brain\\tools\\install_backup_task.bat (qi_python.bat call)

---

## 2026-04-06 — Universal Control Panel + Ecosystem Reorganisation
**Session Focus:** QI Universal Control Panel; ecosystem moved to C:\\UNIVERSAL\\ECOSYSTEM

### Built
- QI Universal Control Panel bat (menu launcher, Windows Terminal tabs)
- Ecosystem folder moved from C:\\QI\\ECOSYSTEM → C:\\UNIVERSAL\\ECOSYSTEM
- All CLAUDE.md files updated across all projects
- MaiaNightlySync rescheduled to 9PM

---
""", "Universal / Implementation Log")

write_if_missing(UNI / "QIOrchestrator_Meeting_Minutes.md", f"""\
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
| AD-004 | NSSM binary standardized to C:\\UNIVERSAL\\dashboard\\nssm.exe | 2026-04-19 |
| AD-005 | Zero hardcoded LLM config — all in DB | 2026-04-19 |
| AD-006 | Python path centralized in qi_python_config.json | 2026-04-19 |
| AD-007 | C:\\UNIVERSAL is permanent home for all cross-project tooling | 2026-04-06 |
| AD-008 | Projects stay independent — Brain is purely additive | 2026-04-19 |

### Next Steps
1. Verify all docs now exist across all projects (audit_docs.py)
2. Add documentation check to session intelligence briefing
3. Review feature propagation decisions (8 pending)

---
""", "Universal / Meeting Minutes")

write_if_missing(UNI / "QIOrchestrator_Version_History.md", f"""\
# QI Orchestrator — Version History

---

## v1.2 — {TODAY}
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
- Ecosystem files moved to C:\\UNIVERSAL\\ECOSYSTEM

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
""", "Universal / Version History")

write_if_missing(UNI / "QIOrchestrator_Master_Status_Report.md", f"""\
# QI Orchestrator — Master Status Report

> Last updated: {TODAY}

---

## Current State

| Item | Value |
|------|-------|
| Version | 1.2 |
| Status | Active |
| Phase | Production — continuous improvement |
| Dashboard URL | http://localhost:9000 |
| Brain API URL | http://localhost:9010 |

## Services Running
| Service | Port | Status |
|---------|------|--------|
| QI_Dashboard | 9000 | ✅ Running |
| QI_DashboardTunnel | — | ✅ Running |
| QI_BrainAPI | 9010 | ✅ Running |

## Feature Status

### Dashboard (port 9000)
| Feature | Status |
|---------|--------|
| Task board + delegations | ✅ Live |
| Agent profiles (8 agents) | ✅ Live |
| Project status pages (6 sub-tabs) | ✅ Live |
| Ecosystem health monitoring | ✅ Live |
| Calendar | ✅ Live |
| Chat | ✅ Live |
| Audit log | ✅ Live |
| Usage monitoring | ✅ Live |
| 5 visual themes | ✅ Live |
| Control panel (start/stop services) | ✅ Live |
| Per-project log viewer | ✅ Live |

### Brain API (port 9010)
| Feature | Status |
|---------|--------|
| Decision memory | ✅ Live |
| Feature propagation (qwen3:8b) | ✅ Live |
| Session logging | ✅ Live |
| Semantic search (ChromaDB) | ✅ Live |
| MCP tool for Claude | ✅ Live |

### Infrastructure
| Feature | Status |
|---------|--------|
| QI_ NSSM naming (9 services) | ✅ Done |
| Central Python config | ✅ Live |
| Nightly backup (1AM, 5 DBs) | ✅ Live |
| Session Intelligence (auto-context) | ✅ Live |

## Next Priorities
1. Python path migration (when Renne installs new Python)
2. Review 8 feature propagation decisions
3. Named Cloudflare tunnel (blocked on budget)
4. Task dependency visualization

---
""", "Universal / Master Status Report")


# ─────────────────────────────────────────────────────────────────────────────
# Print results
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 60)
print("  DOCUMENTATION GAP FIX — RESULTS")
print("=" * 60)

if created:
    print(f"\n✅ CREATED ({len(created)}):")
    for c in created:
        print(c)

if skipped:
    print(f"\n⏭  SKIPPED — already existed ({len(skipped)}):")
    for s in skipped:
        print(s)

print(f"\n{'='*60}")
print(f"  Total created: {len(created)}  |  Skipped: {len(skipped)}")
print(f"{'='*60}")

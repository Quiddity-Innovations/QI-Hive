# QI Orchestrator — Version History

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

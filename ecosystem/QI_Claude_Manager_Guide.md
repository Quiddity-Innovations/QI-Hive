# QI Claude Manager — Cheatsheet
**Quiddity Innovations | Renne Santiago**
*Last updated: 2026-04-06 | Version: 2.0*

---

## Quick Reference

| I want to... | Do this |
|---|---|
| Check all projects are healthy | Say: **"Claude, check status"** |
| See the dashboard | Open: **http://localhost:8600** |
| See health check | Open: **http://localhost:8600/health** |
| Manage tasks | Open: **http://localhost:8600/board** |
| Read this guide | Open: **http://localhost:8600/guide** |
| Understand a project | Say: **"Explain Maia to me"** |
| Start a new session | Say: **"Start Meeting 0X. Read LATEST.md..."** |
| Save session docs | Say: **"Update all"** |
| Commit code | Say: **"Commit"** or use `/git-commit` skill |

---

# PART 1 — USER GUIDE
*What you need to know to work with Claude day-to-day*

## Starting a Session

Every session starts the same way:
```
Start Meeting 0X. Read LATEST.md at C:\Claude\Session Summaries\LATEST.md
and status.json at C:\Claude\status.json. Then begin the agenda.
```
Claude reads the last session handoff, picks up exactly where you left off.

## Talking to Claude

### Status and health
- **"Check status"** / **"Check if all is up to date"** → runs full ecosystem health check
- **"Health check"** → same as above
- **"What's going on with NEXUS?"** → explains a specific project

### Understanding the projects
- **"Explain Maia to me"** → plain English overview from SUMMARY.md
- **"What does Naya do?"** → same
- **"Does any project already have X feature?"** → checks feature registry before building

### Building things
- **"Design a..."** → goes to Architect agent
- **"Build..."** / **"Implement..."** → goes to Builder agent
- **"Review this code"** → goes to Inspector agent
- **"Research..."** → goes to Scout agent (Haiku model — fast)
- **"Document this"** → goes to Scribe agent

### Ending a session
- **"Update all"** → updates Implementation Log, Meeting Minutes, Version History, commits, saves session summary .docx, creates calendar events
- **"Save the session"** → just the .docx summary
- **"Commit"** → git commit + push only

## The Dashboard

Three pages, all at port 8600:

### Dashboard (`/`)
- Project cards showing status + open task count
- Quick links to board and health check
- Agent team status (idle / active, which model)
- Session log

### Health Check (`/health`)
- Live scan — runs every time you open it
- Shows: service up/down, port open/closed, git clean/dirty, docs fresh/stale
- ⚠️ Action Needed section lists specific issues
- Auto-refreshes every 60 seconds

### Task Board (`/board`)
- **4 columns:** Backlog → In Progress → Review → Done
- **Drag cards** between columns — saves instantly
- **Add Task** button → modal with project, agent, priority
- **Filter by project** using the dropdown
- **Delete** with × on any card
- Cards show: priority colour (red/yellow/green), agent, project

### Tests (`/tests`)
- **Smoke Tests** — quick ping of all 4 services (< 15s)
- **API Tests** — full endpoint coverage per project (< 60s)
- **UI Tests** — Playwright headless browser check of dashboard
- **Run All** — full suite
- Results show pass/fail/skip counts + per-test detail
- Failures **auto-create tasks** on the kanban board

## The Skills
Invoked via `/skill-name` or by describing the task:

| Skill | What it does |
|---|---|
| `health-check` | Full ecosystem scan, flags issues |
| `session-summary` | Creates .docx session summary |
| `git-commit` | Stages, commits, pushes |
| `doc-generator` | Updates Implementation Log, Meeting Minutes, Version History |

## Testing
The **Tester agent** runs the full test suite across all projects.

- **"Run tests"** / **"Run smoke tests"** → quick health ping of all services
- **"Run all tests"** → full API + UI test suite
- **"Load test Maia"** → Locust performance test

Or use the dashboard: **http://localhost:8600/tests** → click any test button.

Failures automatically create tasks on the kanban board.

---

# PART 2 — OPERATOR GUIDE
*How to keep the ecosystem running*

## Services

### Starting / stopping services
```bat
sc start QI_MaiaBot       ← start Maia API server
sc stop QI_MaiaBot        ← stop it
sc start QI_MaiaTunnel    ← start Cloudflare tunnel
sc start QI_NayaBot       ← start Naya
sc start QI_NEXUS         ← start NEXUS
sc start QI_Dashboard     ← start dashboard
sc start QI_BrainAPI      ← start QI Brain API
```

Or use the control panel:
```
C:\QI\maia_control.bat
```

### Check if a service is running
```bat
sc query QI_MaiaBot
sc query QI_NayaBot
sc query QI_NEXUS
sc query QI_BrainAPI
sc query QI_Dashboard
```

### Install ClaudeManager dashboard as service (run as Admin)
```bat
C:\Claude\Dashboard\install_service.bat
```

## Health Check

Run from command line:
```bat
python C:\Claude\health_check.py
```

With save to status.json:
```bat
python C:\Claude\health_check.py --save
```

## Nightly Sync

Runs automatically at 12:30 AM via Windows Task Scheduler.
Manual run if it failed:
```bat
python C:\QI\TOOLS\maia_nightly_sync.py
```

## Restarting the Dashboard

If dashboard is down:
```bat
C:\Claude\Dashboard\start_dashboard.bat
```
Or as NSSM service (after admin install):
```bat
sc start ClaudeManager
```

## Adding a Task

1. Open http://localhost:8600/board
2. Click **Add Task**
3. Fill title, description, project, agent, priority
4. Clicks into Backlog automatically

Or via API:
```bash
curl -X POST http://localhost:8600/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"My task","project":"Maia","agent":"builder","priority":"high"}'
```

---

# PART 3 — TECHNICAL REFERENCE
*Architecture, ports, paths, and APIs*

## QI Ecosystem Map

| Project | Path | API Port | UI Port | Service | Status |
|---|---|---|---|---|---|
| Maia | C:\QI | 8001 | 7860 | QI_MaiaBot + QI_MaiaTunnel | Production |
| Naya | C:\NAYA | 8002 | 7861 | QI_NayaBot + QI_NayaGradio | Active |
| NEXUS | C:\NEXUS | 8010 | 7880 | QI_NEXUS | Active |
| Dashboard | C:\UNIVERSAL\dashboard | 9000 | — | QI_Dashboard + QI_DashboardTunnel | Active |
| Brain API | C:\UNIVERSAL\qi_brain | 9010 | — | QI_BrainAPI | Active |
| OpenClaw | C:\OC (WSL) | 8400+ | — | keepalive | Production |
| MQ | C:\MQ | — | — | — | Scaffolded |
| Claude Manager | C:\Claude | 8600 | — | ClaudeManager | Dev |

## OpenClaw Agents

| Agent | Role | Status |
|---|---|---|
| Tasuke | Orchestrator — routes tasks to other agents | Live |
| Kaze | News digest, AI feeds | Live |
| Yubin | Email agent, Gmail | Live |
| Sentry | Security monitoring | Live |
| Seiri | File organization | Needs activation |
| Koe | Voice agent — may become shared voice layer across all QI | Planned |
| Fumi | Facebook / social media publisher | Planned |
| Media Creation Agent | ComfyUI — images, video, voice generation | Planned |

## Merge & Convergence Candidates

| Merge | Projects | Status |
|---|---|---|
| Naya + FileHQ | Done — FileHQ absorbed into C:\NAYA\filehq\ | ✅ Complete |
| Naya + OC/Seiri | File intelligence (Naya) + file organization (Seiri) — may merge | Under consideration |
| Maia + OpenClaw | Maia handles conversation, OC handles autonomous action | Marriage candidate |
| Koe as shared layer | Voice service usable by Maia, MQ, OC, media agents | Planned |

## Long-Term Vision

- **2026:** All projects at independent POC stage, cloud deployment ready
- **2027+:** Full integrated platform — modules converge into unified commercially viable product

## Port Block Allocations

| Project | Reserved Block |
|---|---|
| FileHQ (legacy) | 8000–8099 |
| Maia | 8100–8199 |
| Naya | 8200–8299 |
| NEXUS | 8300–8399 |
| OpenClaw | 8400–8499 |
| Claude Manager | 8600–8699 |

**Rule:** Never assign a port outside a project's block. Always check `C:\QI\ECOSYSTEM\qi_registry.json` first.

## File Locations

| What | Where |
|---|---|
| Live ecosystem state | `C:\Claude\status.json` |
| Task board data | `C:\Claude\tasks.json` |
| Agent definitions | `C:\Claude\Agents\{name}\` |
| Skills | `C:\Claude\Skills\` |
| Dashboard code | `C:\Claude\Dashboard\server.py` |
| Dashboard static files | `C:\Claude\Dashboard\static\` |
| Health check script | `C:\Claude\health_check.py` |
| Session handoff | `C:\Claude\Session Summaries\LATEST.md` |
| Session .docx files | `C:\Claude\Session Summaries\` |
| This guide | `C:\UNIVERSAL\QI_Claude_Manager_Guide.md` |
| QI standards | `C:\QI\ECOSYSTEM\QI_Standards.md` |
| QI registry | `C:\QI\ECOSYSTEM\qi_registry.json` |
| QI architecture principles | `C:\QI\ECOSYSTEM\QI_Architecture_Principles.md` |

## Database Ownership

| Database | Owner | Path |
|---|---|---|
| maia.db | Maia only | C:\QI\maia.db |
| naya.db | Naya only | C:\NAYA\naya.db |
| nexus.db | NEXUS only | C:\NEXUS\nexus.db |
| (none yet) | Claude Manager | Would be C:\Claude\claude.db |

**Rule:** No project ever reads or writes another project's database. Cross-project data flows via registered API calls only.

## Dashboard API Endpoints

| Method | Endpoint | What it does |
|---|---|---|
| GET | `/` | Main dashboard page |
| GET | `/health` | Health check page |
| GET | `/board` | Task board page |
| GET | `/guide` | This guide (rendered) |
| GET | `/api/status` | Raw status.json |
| GET | `/api/agents` | Agent configs |
| GET | `/api/health` | Live health check JSON |
| GET | `/api/tasks` | All tasks |
| POST | `/api/tasks` | Create task |
| PATCH | `/api/tasks/{id}` | Update task (move column, etc.) |
| DELETE | `/api/tasks/{id}` | Delete task |

## Agent Team

| Agent | Default Model | Max Model | Can Run Code? | Scope |
|---|---|---|---|---|
| Architect | Sonnet | Opus | No | Design only |
| Builder | Sonnet | Sonnet | Yes | Implementation |
| Scout | Haiku | Sonnet | No | Research only |
| Scribe | Haiku | Sonnet | No | Documentation |
| Ops | Haiku | Haiku | Yes (read-only bash) | Operations |
| Inspector | Sonnet | Sonnet | Yes (read-only) | Review & approval |
| Tester | Haiku | Sonnet | Yes | Cross-project testing |

## The 4 Integration Rules (never break these)

1. **Operational Awareness** — before touching shared infrastructure, check `status.json` for other active tasks
2. **Feature Reuse** — before building, check `feature_registry` in `status.json` to see if it exists already
3. **Convergence Readiness** — build API-first; every module must be independently startable and stoppable
4. **Portfolio Visibility** — every completed task updates `status.json`; dashboard reflects all projects

## The 3 Design Principles

> **Reduce issues. Raise efficiencies. Provide quick solutions.**

Every design decision must serve at least one of these. If it doesn't — it doesn't belong in QI.

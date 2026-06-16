# QI Hive Operator Guide
**Quiddity Innovations | Renne Santiago**  
*Last updated: 2026-06-16 | Version: 3.0*  
*The unified control plane for all QI projects*

---

## Quick Start

| I want to... | Where to go |
|---|---|
| **See everything at once** | http://localhost:8600 (Dashboard tab) |
| **Check project health** | http://localhost:8600/health |
| **Manage tasks** | http://localhost:8600/board |
| **Start a service** | `sc start QI_<ServiceName>` |
| **See this guide** | http://localhost:8600/guide |
| **Understand a project** | http://localhost:8600/projects/status |
| **View agent team** | http://localhost:8600/hive |
| **Check logs** | http://localhost:8600/logs |

---

## PART 1 — THE DASHBOARD (18 TABS)

### **1. Dashboard** (`/`)
Home page. Shows:
- **Project cards** — status, open tasks, recent activity
- **Quick links** — board, health, projects
- **Agent team status** — which agents are idle/active, current model
- **Session summary** — what was worked on last

### **2. Launcher** (`/launcher`)
Click-to-launch interface for all QI projects:
- **Links to all 22 projects** by name and category
- **Port reference** — what port each project is on
- **Status light** — green = healthy, yellow = warning, red = down
- Opens project UIs/APIs without leaving the dashboard

### **3. The Hive** (`/hive`)
The agent roster. Shows:
- **7 hive agents** — Architect, Builder, Scout, Scribe, Inspector, Tester, Ops
- **Agent status** — idle, active, or last task
- **Current model** — which Claude model each agent is running on
- **Role description** — what each agent does

### **4. Health Check** (`/health`)
Live ecosystem scan. Runs every time you open it. Shows:
- **Service status** — each QI_* service: up/down, uptime, port listening
- **Port inventory** — which ports are open, which are in use
- **Git status** — repo clean/dirty, uncommitted changes
- **Database health** — last write timestamp
- **Action Needed** — specific issues flagged with remediation steps
- Auto-refreshes every 60 seconds

### **5. Task Board** (`/board`)
Kanban board for all tasks. Features:
- **4 columns** — Backlog → In Progress → Review → Done
- **Drag cards** — move tasks between columns, auto-saves
- **Add Task** — button opens modal (title, description, project, agent, priority)
- **Filter by project** — dropdown to show one project's tasks
- **Delete** — × button on any card
- **Card metadata** — priority color (red/yellow/green), assigned agent, due date
- All changes are persisted to the database

### **6. Tests** (`/tests`)
Test runner for all projects. Types:
- **Smoke Tests** (~15s) — quick `/health` ping on every QI_* service
- **API Tests** (~60s) — full endpoint coverage (GET /version, GET /info, GET /health on every project)
- **UI Tests** (~90s) — Playwright headless browser check of dashboard and key pages
- **Run All** — execute full suite in sequence
- Results show: pass/fail/skip counts, per-test detail, failure messages
- Failures **auto-create tasks** on the kanban board

### **7. Project Status** (`/projects/status`)
Detailed per-project view (22 total). Shows for each:
- **Identity** — name, path, description
- **Ports** — API port(s), UI port(s), other services
- **Services** — NSSM services that run this project (e.g. QI_MaiaBot)
- **Status** — active/dev/paused/deprecated, last health check
- **Integrations** — which projects it talks to
- **GitHub link** — if available
- Sort/filter by status or family tier

### **8. Services** (`/services`)
Complete NSSM service inventory. Lists all QI_* services:
- **Service name** — QI_MaiaBot, QI_NayaBot, QI_NEXUS, QI_Dashboard, QI_BrainAPI, etc.
- **Status** — Running / Stopped / Error
- **Port** — listening port (if applicable)
- **Uptime** — how long running (if active)
- **Buttons** — Start / Stop / Restart
- **Log file** — click to open service logs
- **Auto-start** — whether service starts on boot
- All services use NSSM binary at `C:\QIH\engine\bin\nssm.exe`

### **9. Scheduled Tasks** (`/tasks`)
Windows Task Scheduler view. Shows recurring jobs:
- **Task name** — QI_TubeScout_AM, MaiaNightlySync, etc.
- **Schedule** — cron-like description (daily at 12:30 AM, etc.)
- **Last run** — timestamp
- **Next run** — when it will fire next
- **Status** — enabled/disabled/error
- Buttons: Run Now, Enable, Disable
- **Result history** — last 3 runs with exit codes

### **10. LLM Usage** (`/usage`)
Token and API cost tracking across all projects. Shows:
- **By project** — Maia, Naya, NEXUS, etc. — how many tokens used
- **By model** — Claude, GPT-4, Gemini, Qwen, etc.
- **Cost breakdown** — input tokens, output tokens, cost in USD
- **Time period** — last 24h, last 7d, last 30d, all-time
- **Limits** — if set, show overage warnings
- **Export** — download CSV for accounting

### **11. Headlines** (`/news`)
AI news digest. Powered by NEXUS Scout + Kaze. Shows:
- **Daily digest** — AI news from multiple sources
- **Filtered by interest** — can select topics (AGI, Vision, LLMs, NLP, etc.)
- **Timestamps** — when each story was published
- **Source** — where the story came from
- **Excerpt** — preview of the article
- Click to open full article

### **12. Activity** (`/activity`)
Event log and audit trail. Shows:
- **Session start/end** — who started what session, when
- **Service restarts** — when QI_* services were restarted
- **API calls** — high-volume calls to /health, /info, etc. (sanitized, no secrets)
- **Config changes** — when a project's configuration was modified
- **Test runs** — when test suite ran and results
- **Errors** — any exceptions or failures
- Filter by service, project, or time range
- Auto-rotates logs daily

### **13. CoWork Dispatch** (`/dispatch`)
Integration point for Claude Code multi-agent system. Shows:
- **CoWork status** — is the Claude Code gateway listening?
- **Agent queue** — incoming requests from Claude Code threads
- **Dispatch history** — recent tasks sent to hive agents
- **Response times** — how fast each agent is responding
- Manual test panel to send a task to an agent
- Configuration for MCP routing

### **14. QI Brain** (`/brain`)
Knowledge substrate dashboard. Shows:
- **Session log** — all sessions logged to Brain (project, date, summary)
- **Decision registry** — design decisions with rationale and impact scope
- **Feature registry** — new features implemented, which project source
- **Memory search** — full-text search across all logged context
- **Project state** — current phase and status for each project
- Link to Brain API at :9011
- Browser for qi_brain.db schema

### **15. War Room** (`/warroom`)
Heads-up display for critical work. Shows:
- **Current bottlenecks** — what's blocking projects right now
- **Multi-session features** — what's being built across multiple sessions
- **Ecosystem risks** — port conflicts, service failures, git drift
- **Integration readiness** — which projects are ready to merge
- **Agent load** — who's busy, who's idle
- **Next milestones** — upcoming dates and what they require

### **16. Logs** (`/logs`)
Centralized log viewer. Browse all service logs:
- **By service** — dropdown to pick QI_MaiaBot, QI_Dashboard, etc.
- **Real-time tail** — last 1000 lines with live refresh
- **Search** — full-text search within logs
- **Filter by level** — show errors, warnings, info, debug
- **Download** — export logs as .txt
- **Clear** — archive old logs
- All log files are standardized to UTF-8 format

### **17. Config** (`/config`)
Ecosystem configuration view (read-only in UI; edit via files):
- **Port allocations** — all reserved blocks and current usage
- **Service settings** — NSSM service parameters (startup args, working directory, etc.)
- **Ecosystem state** — from qi_registry.json (live read)
- **Standards** — summary of QI_Standards.md rules
- **Architecture** — summary of QI_Architecture_Principles.md
- Edit notes: real changes made by editing source files (see "Files" section below)

### **18. Guide** (`/guide`)
This guide. Rendered as HTML from `QI_Claude_Manager_Guide.md`.

---

## PART 2 — THE 22 QI PROJECTS (from qi_registry.json)

| Project | Path | Status | Description |
|---|---|---|---|
| **Maia** | C:\QI | Production | Multi-channel AI assistant (LINE, Telegram, Messenger, Instagram, WhatsApp) |
| **Naya** | C:\NAYA | Active | Personal AI for Renne (Telegram, file scanning, physics/programming domains) |
| **NEXUS** | C:\NEXUS | Active | AI orchestration backbone — multi-provider synthesis, news digest, LLM bench |
| **QI Hive** | C:\QIH | Active | Unified dashboard, 7 hive agents, Brain knowledge substrate |
| **QI Brain** | C:\QIH\engine\brain | Active | Knowledge DB (SQLite + ChromaDB), 12-tool MCP server (:9011) |
| **OpenClaw** | C:\OC | Production | Autonomous agent platform (Tasuke, Kaze, Yubin, Sentry, Koe — WSL2) |
| **AutoPDF** | C:\AutoPDF | Active | PDF toolkit (split, extract, catalog, template matching, Smart Mapping) |
| **EasyFlow** | C:\EasyFlow | Active | Email organization (Gmail tier-based inbox, Apps Script automation) |
| **CogniBase** | C:\CogniBase | Pre-POC | OnBase vector integration + ad-hoc SQL reporting UI |
| **MapSnap** | C:\MapSnap | Stable | Jenzabar schema browser — HTML + HTML FK relationships |
| **M2V** | C:\M2V | New | Music-to-Video — AI music video generator from lyrics |
| **PersonalSong** | C:\PersonalSong | Active | Song generator (ACE-Step vocals + Demucs/Seed-VC voice clone) |
| **TubeScout** | C:\TUBESCOUT | Active | YouTube subscription intelligence (subs→news→Brain implement-scouting) |
| **CypherMiner** | C:\CypherMiner | New | Crypto/encoding/math/text tools (bilingual EN/PT, offline) |
| **LotteryWiz** | C:\Lottery Wiz | Active | Fantasy 5 covering design (FastAPI + .xlsx/.csv export) |
| **Digitization Cost Tool** | C:\Users\renne\Downloads\DIGITIZATION COSTS | Active | BU cost comparison calculator (static HTML, client-side) |
| **FidelityAnalyzer** | C:\FidelityAnalyzer | Active | Fidelity portfolio allocation + rebalancing (FastAPI + Gradio) |
| **AvatarStudio** | C:\1-AI\APPS\AvatarStudio | Active | Avatar video generation (TTS→bg removal→Hallo2/LivePortrait→lip-sync) |
| **FileHQ** | C:\NAYA\filehq | Merged | ~~Standalone~~ — now embedded in Naya (file scanning engine) |
| **MQ** | C:\MQ | New | Maia Quiddam — autonomous social media persona (FB/IG/WhatsApp) |
| **Claude Manager** | C:\CLAUDE | Active | Meta/management workspace (session sync, Brain backfills, reconciliation) |
| **QI-Universal** | C:\QIH | Infrastructure | Shared tools (was C:\UNIVERSAL, migrated 2026-04-22) |

**Total: 22 projects — 6 active production, 10 active development, 4 new, 1 deprecated, 1 merged.**

---

## PART 3 — SERVICES & ELEVATION

### The QI_* Service Family

All services are registered in Windows NSSM (Non-Sucking Service Manager).  
**Binary location:** `C:\QIH\engine\bin\nssm.exe` (standardized 2026-04-22)

**Naming rule:** `QI_<ProjectName><Role>` — e.g. `QI_MaiaBot`, `QI_NayaGradio`, `QI_BrainAPI`, `QI_DashboardTunnel`

**Complete service registry (live on 2026-06-15):**

| Service | Project | Port | Type | Status |
|---|---|---|---|---|
| QI_MaiaBot | Maia | 8001 | FastAPI | Auto-start |
| QI_MaiaTunnel | Maia | — | Cloudflare | Auto-start |
| QI_MaiaDemoTunnel | Maia | — | Cloudflare | Manual |
| QI_MaiaGradio | Maia | 7860 | Gradio | Auto-start |
| QI_NayaBot | Naya | 8002 | Flask | Auto-start |
| QI_NayaGradio | Naya | 7861 | Gradio | Auto-start |
| QI_NEXUS | NEXUS | 8010 | FastAPI | Auto-start |
| QI_Dashboard | Hive | 8600 | FastAPI | Auto-start |
| QI_DashboardTunnel | Hive | — | Cloudflare | Manual |
| QI_BrainAPI | Brain | 9011 | FastAPI | Auto-start |
| QI_Elevate | Hive | — | Elevation Broker | Manual |
| QI_HiveIngest | Hive | — | Worker | Manual |
| QI_KazeConfigAPI | OpenClaw | 8401 | FastAPI | Manual |
| OC-Keepalive-Service | OpenClaw | — | Daemon | Auto-start |

**Status meaning:**
- **Auto-start** — starts when Windows boots, auto-restarts if it crashes
- **Manual** — starts on-demand only (DEMAND_START), not auto-restarts
- **Demand-start** — same as manual, just the NSSM term

### Using NSSM from Command Line

```bat
sc start QI_MaiaBot              ← Start a service
sc stop QI_MaiaBot               ← Stop it
sc query QI_MaiaBot              ← Check status (running/stopped)
sc restart QI_MaiaBot            ← Restart
nssm set QI_MaiaBot Start manual  ← Change to manual startup
nssm query QI_MaiaBot            ← Full NSSM details
```

### Elevation: Use QI_Elevate Broker (gsudo is SUPERSEDED)

**Old way (broken):** `gsudo` from headless threads fails 100% of the time.

**Current way (2026-05-14):** Use the **QI_Elevate broker**:

```python
# Python
from C:\QIH\engine\common\qi_elevate_client import run_elevated
run_elevated("command to run as admin")
```

The broker is a Windows service that listens for elevation requests and executes them with admin privileges. Never call `gsudo` or `runas` directly.

---

## PART 4 — KEY FILES & LOCATIONS

| What | Where |
|---|---|
| **Ecosystem registry** (master truth) | `C:\QIH\ecosystem\qi_registry.json` |
| **QI standards** | `C:\QIH\ecosystem\QI_Standards.md` |
| **Architecture principles** | `C:\QIH\ecosystem\QI_Architecture_Principles.md` |
| **Service registry** (old, informational) | `C:\QIH\ecosystem\QI_Service_Registry.md` |
| **Brain database** (shared knowledge) | `C:\QIH\data\qi_brain.db` (SQLite + ChromaDB) |
| **Dashboard code** | `C:\QIH\engine\hive\dashboard\server.py` |
| **Brain API** | `C:\QIH\engine\brain\api.py` |
| **Elevation broker** | `C:\QIH\engine\common\qi_elevate_client.py` |
| **NSSM binary** | `C:\QIH\engine\bin\nssm.exe` |
| **Session summaries** | `C:\QIH\shared\documentation\session_summaries\` |
| **Project logs** | Project-specific (e.g. `C:\QI\LOGS\`, `C:\NAYA\LOGS\`, `C:\QIH\logs\`) |

---

## PART 5 — THE INTEGRATION RULES (Golden Rules)

1. **Operational Awareness** — Before touching shared infra, check the dashboard Health tab for active issues
2. **Feature Reuse** — Before building, check QI Brain feature registry to see if it exists in another project
3. **Convergence Ready** — Every module must be independently startable/stoppable; no tight coupling
4. **Portfolio Visibility** — Every session logged to Brain; every task on kanban board; dashboard always accurate
5. **Port discipline** — No port outside a project's allocated block. Check `qi_registry.json` first.
6. **No shared databases** — Each project owns its own DB (maia.db, naya.db, nexus.db, etc.). Cross-project data flows via registered API calls only.
7. **Cloudflare is Maia-only** — Never tunnel NEXUS, Naya, OpenClaw, or any other project. Maia only, for webhook callbacks.
8. **Service naming** — Always QI_<ProjectName><Role>. Use `C:\QIH\engine\bin\nssm.exe`. Always set Description and AppDirectory.

---

## PART 6 — COMMON OPERATIONS

### Health Check
```bash
# From dashboard: visit http://localhost:8600/health
# Or from command line:
python C:\QIH\engine\hive\health_check.py
```

### Check a Single Service
```bash
sc query QI_MaiaBot
nssm query QI_MaiaBot                  ← Full details
type C:\QI\LOGS\maia_service_log.txt   ← View logs
```

### Find Which Port Owns a Service
1. Open dashboard → Services tab
2. Ctrl+F to search for the port
3. Or check `qi_registry.json` projects[].ports

### Add a New Service
1. Build the project
2. Update `qi_registry.json` with ports and service metadata
3. Run `nssm install QI_<ProjectName><Role> C:\path\to\script.py` (or executable)
4. Set Description: `nssm set QI_<Name> Description "Human-readable description"`
5. Set AppDirectory: `nssm set QI_<Name> AppDirectory C:\path\to\project\root`
6. Test: `nssm start QI_<Name>`
7. Register in service_registry.md for human reference
8. Commit changes to git

### Manually Test a Project's Health
```bash
curl http://localhost:8001/health          ← Maia
curl http://localhost:8002/health          ← Naya
curl http://localhost:8010/health          ← NEXUS
curl http://localhost:8600/health          ← Dashboard
curl http://localhost:9011/health          ← Brain API
```

### View Service Logs in Real Time
```bash
# Option 1: Dashboard /logs tab
# Option 2: Command line
Get-Content C:\QI\LOGS\maia_service_log.txt -Tail 50 -Wait
```

### Restart All Services (after major config change)
```bash
# From dashboard: Services tab → restart buttons
# Or from command line:
sc stop QI_MaiaBot && timeout /t 2 && sc start QI_MaiaBot
sc stop QI_NayaBot && timeout /t 2 && sc start QI_NayaBot
sc stop QI_NEXUS && timeout /t 2 && sc start QI_NEXUS
# etc.
```

---

## PART 7 — TROUBLESHOOTING

### Service won't start
1. Check logs: `C:\<project>\LOGS\` or dashboard /logs tab
2. Verify the script path exists: `nssm query QI_<Name>` → look for `Application`
3. Check AppDirectory is set: `nssm query QI_<Name>` → look for `AppDirectory`
4. Verify port is not in use: `netstat -ano | findstr :8001`
5. Check service is not already running under a different name
6. Restart the service manager: `net stop nssm` (careful — all services will stop)

### Port is already in use
```bash
netstat -ano | findstr :8001      ← find PID holding the port
taskkill /pid <PID> /f            ← kill the process
# OR from dashboard: Services tab → find the service → Restart
```

### Brain API is offline (:9011)
```bash
# Check if it's Logitech G HUB squatting the port:
tasklist | findstr lghub
# If yes, restart G HUB or kill it temporarily
# Then: sc start QI_BrainAPI
```

### Dashboard is down (8600)
```bash
sc start QI_Dashboard
# Wait 5 seconds
# Open http://localhost:8600
# If still down, check logs:
type C:\QIH\engine\hive\dashboard\LOGS\dashboard.log
```

### Git is dirty (uncommitted changes detected)
```bash
# From dashboard /health, click the action
# Or manually:
cd C:\<project>
git status                         ← see what's dirty
git add <file>
git commit -m "description"
git push
```

---

## PART 8 — DATA SOURCES FOR THE DASHBOARD

All dashboard tabs source from two files:

1. **`qi_registry.json`** — The registry. Single source of truth for:
   - Project identity (name, path, description)
   - Ports (allocated blocks and current usage)
   - Services (NSSM service names and metadata)
   - Integrations (who talks to whom)
   - Family tiers (core, backbone, sibling, cousin, etc.)

2. **`qi_brain.db`** — The knowledge substrate. Stores:
   - Session logs (every project session)
   - Decision registry (design decisions + rationale)
   - Feature registry (what's implemented where)
   - Project state (current phase, status, next steps)
   - Memory (full-text searchable context)

Both are kept current by automated and manual processes. The dashboard reads them live.

---

## PART 9 — QUICK REFERENCE: PORTS

| Block | Range | Owner | Purpose |
|---|---|---|---|
| System | 8000–8099 | FileHQ family | Legacy block |
| Maia | 8100–8199 | Maia | API + Gradio |
| Naya | 8200–8299 | Naya | API + Gradio + FileHQ embedded |
| NEXUS | 8300–8399 | NEXUS | API + Gradio |
| OpenClaw | 8400–8499 | OpenClaw | Agents + Kaze API |
| MQ/Cousins | 8500–8599 | MQ, M2V, TubeScout, etc. | New projects |
| Hive | 8600–8649 | QI Hive | Dashboard + utilities |
| MapSnap | 8650–8659 | MapSnap, CogniBase | Schema tools |
| AutoPDF | 8700–8709 | AutoPDF | Pre-registry (currently 6969) |
| Brain | 9000–9099 | QI Brain | API (:9011) |
| Maia UI | 7800–7809 | Maia | Gradio demo (:7860) |
| Naya UI | 7810–7819 | Naya | Gradio UI (:7861) |
| NEXUS UI | 7820–7829 | NEXUS | Gradio UI (:7880) |
| Cousins UI | 7840–7869 | M2V, PersonalSong, etc. | Various UI ports |

**Rule:** Port outside a block → permission required. New services must use their allocated block.

---

## PART 10 — THE VISION

**Today:** 22 independent projects, each with its own code, config, DB, and service.

**Tomorrow:** Unified QI platform where projects become modules:
- **Maia** → Conversational AI + multi-channel interface
- **NEXUS** → AI engine backbone
- **OpenClaw** → Autonomous agent layer
- **Brain** → Shared knowledge + MCP orchestration
- **Everything else** → pluggable feature modules

**The dashboard is the control plane.** As projects converge, the dashboard grows smarter. Today it monitors 11 services. Tomorrow it orchestrates 100.

---

## PART 11 — GETTING HELP

| Question | Answer |
|---|---|
| "Is a service running?" | Dashboard → Services tab or `sc query QI_<Name>` |
| "What port is project X on?" | `qi_registry.json` or dashboard → Launcher tab |
| "Why did a test fail?" | Dashboard → Tests tab → click the failure → see error |
| "What happened in the last session?" | Dashboard → Activity tab or QI Brain session log |
| "How do I add a project?" | `python C:\QIH\ecosystem\qi_new_project.py` |
| "Is the ecosystem healthy?" | Dashboard → Health tab |
| "What did I commit yesterday?" | `git log --oneline | head -10` or dashboard → Activity tab |
| "Can project X call project Y?" | `qi_registry.json` → projects[id].integrates_with |

---

**End of Guide**  
Last refreshed: 2026-06-16 from `qi_registry.json` (22 projects, 14 active services)

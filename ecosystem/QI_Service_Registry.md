# QI Ecosystem — Windows Service Registry

**Authority:** This file is the single source of truth for all QI NSSM Windows services.
**Location:** `C:\QIH\ecosystem\QI_Service_Registry.md`
**Convention:** All QI services are prefixed `QI_` so they group together in Windows Services, Task Manager, and Event Viewer.
**Last updated:** 2026-05-13 (audit-corrected from live NSSM state)

---

## Service Name Mapping (Old → New)

| Old Name | New Name | Renamed? | Notes |
|---|---|---|---|
| MaiaBot | QI_MaiaBot | ✅ 2026-04-19 | |
| MaiaTunnel | QI_MaiaTunnel | ✅ 2026-04-19 | |
| MaiaDemoTunnel | QI_MaiaDemoTunnel | ✅ 2026-04-19 | |
| NayaBot | QI_NayaBot | ✅ 2026-04-19 | |
| NayaGradio | QI_NayaGradio | ✅ 2026-04-19 | |
| NEXUSService | QI_NEXUS | ✅ 2026-04-19 | Dropped redundant "Service" suffix |
| QIDashboard | QI_Dashboard | ✅ 2026-04-19 | Fixed AppDirectory bug |
| QIDashboardTunnel | QI_DashboardTunnel | ✅ 2026-04-19 | Fixed python3→real Python path bug |
| QIBrainAPI | QI_BrainAPI | ✅ 2026-04-19 | |

---

## Full Service Catalog

### QI_MaiaBot
| Field | Value |
|---|---|
| **Display name** | QI — Maia Bot Server |
| **Description** | Maia AI assistant platform. FastAPI server handling LINE, Telegram and other channels. Ollama-powered multi-LLM chain. |
| **Binary** | `C:\1-AI\APPS\PYTHON\python.exe` |
| **Parameters** | `maia_server.py` |
| **Working dir** | `C:\QI` |
| **Port** | 8001 |
| **Stdout log** | `C:\QI\LOGS\maia_service_log.txt` |
| **Stderr log** | `C:\QI\LOGS\maia_error.txt` |
| **Start type** | AUTO_START (delayed) |
| **Account** | LocalSystem |
| **NSSM binary** | `C:\QIH\engine\bin\nssm.exe` (standardized 2026-04-22) |

### QI_MaiaTunnel
| Field | Value |
|---|---|
| **Display name** | QI — Maia Cloudflare Tunnel (Production) |
| **Description** | Cloudflare quick tunnel exposing Maia Bot (port 8001) to the internet for LINE/Telegram webhooks. |
| **Binary** | `C:\Program Files (x86)\cloudflared\cloudflared.exe` |
| **Parameters** | `tunnel --url http://localhost:8001` |
| **Working dir** | `C:\QI` |
| **Stdout log** | `C:\QI\LOGS\tunnel_service_log.txt` |
| **Stderr log** | `C:\QI\LOGS\tunnel_log.txt` |
| **Start type** | AUTO_START (delayed) |
| **Account** | LocalSystem |

### QI_MaiaDemoTunnel
| Field | Value |
|---|---|
| **Display name** | QI — Maia Demo Tunnel (Gradio) |
| **Description** | Cloudflare quick tunnel exposing Maia Gradio demo UI (port 7860) for demonstrations and testing. |
| **Binary** | `C:\Program Files (x86)\cloudflared\cloudflared.exe` |
| **Parameters** | `tunnel --url http://localhost:7860` |
| **Working dir** | `C:\Program Files (x86)\cloudflared` |
| **Stderr log** | `C:\QI\LOGS\Maia_Gradio_Tunnel_Log.txt` |
| **Start type** | DEMAND_START (manual) |
| **Account** | LocalSystem |

### QI_MaiaGradio
| Field | Value |
|---|---|
| **Display name** | QI - Maia Gradio UI |
| **Description** | Maia Gradio web UI on port 7860. Browser-based chat interface for Maia AI assistant. Auto-restart enabled. |
| **Binary** | `C:\1-AI\APPS\PYTHON\python.exe` |
| **Parameters** | `maia_gradio.py` |
| **Working dir** | `C:\QI` |
| **Port** | 7860 |
| **Stdout log** | `C:\QI\LOGS\maia_gradio_service.log` (rotated at 5 MB) |
| **Stderr log** | `C:\QI\LOGS\maia_gradio_error.log` (rotated at 5 MB) |
| **Start type** | AUTO_START |
| **Account** | LocalSystem |
| **NSSM binary** | `C:\QIH\engine\bin\nssm.exe` |
| **AppExit** | Default = Restart (5 s delay, 10 s throttle) |
| **Added** | 2026-05-09 |

### QI_NayaBot
| Field | Value |
|---|---|
| **Display name** | QI — Naya Bot Server |
| **Description** | Naya personal AI assistant. Telegram bot + file management engine. FastAPI server on port 8002. |
| **Binary** | `C:\1-AI\APPS\PYTHON\python.exe` |
| **Parameters** | `C:\NAYA\naya_server.py` |
| **Working dir** | `C:\NAYA` |
| **Port** | 8002 |
| **Stdout log** | `C:\NAYA\LOGS\naya_service_log.txt` |
| **Stderr log** | `C:\NAYA\LOGS\naya_error.txt` |
| **Start type** | AUTO_START |
| **Account** | LocalSystem |

### QI_NayaGradio
| Field | Value |
|---|---|
| **Display name** | QI — Naya Gradio UI |
| **Description** | Naya Gradio web interface on port 7861. Provides browser-based UI for Naya AI assistant. |
| **Binary** | `C:\1-AI\APPS\PYTHON\python.exe` |
| **Parameters** | `C:\NAYA\naya_gradio.py` |
| **Working dir** | `C:\NAYA` |
| **Port** | 7861 |
| **Stdout log** | `C:\NAYA\LOGS\naya_gradio_service.log` *(added 2026-05-13 — was empty)* |
| **Stderr log** | `C:\NAYA\LOGS\naya_gradio_error.log` *(added 2026-05-13 — was empty)* |
| **Start type** | AUTO_START |
| **Account** | LocalSystem |

### QI_NEXUS
| Field | Value |
|---|---|
| **Display name** | QI — NEXUS Scout Engine |
| **Description** | Quiddity Innovations NEXUS: Neural Exchange and Unified Synthesis. Scout/digest engine with multi-provider LLM dispatch. API port 8010, UI port 7880. |
| **Binary** | `C:\1-AI\APPS\PYTHON\python.exe` |
| **Parameters** | `C:\NEXUS\main.py` |
| **Working dir** | `C:\NEXUS` |
| **Ports** | API 8010 · UI 7880 |
| **Stdout log** | `C:\NEXUS\LOGS\nexus_service.log` |
| **Stderr log** | `C:\NEXUS\LOGS\nexus_service_error.log` |
| **Start type** | AUTO_START (delayed) |
| **Account** | LocalSystem |

### QI_Dashboard
| Field | Value |
|---|---|
| **Display name** | QI — Hive Dashboard |
| **Description** | QI Hive Dashboard. Agent orchestration UI, kanban, health check, hive agent profiles. FastAPI on port 8600. |
| **Binary** | `C:\1-AI\APPS\PYTHON\python.exe` |
| **Parameters** | `C:\QIH\engine\hive\dashboard\server.py` |
| **Working dir** | `C:\QIH` |
| **Port** | 8600 |
| **Stdout log** | `C:\QIH\engine\hive\dashboard\LOGS\dashboard.log` *(repointed 2026-05-13 — was C:\UNIVERSAL\dashboard\LOGS\)* |
| **Stderr log** | `C:\QIH\engine\hive\dashboard\LOGS\dashboard_error.log` *(repointed 2026-05-13)* |
| **Start type** | AUTO_START |
| **Account** | LocalSystem |

### QI_DashboardTunnel
| Field | Value |
|---|---|
| **Display name** | QI — Dashboard Cloudflare Tunnel |
| **Description** | Cloudflare quick tunnel exposing the Hive Dashboard (port 8600) to the internet. URL written to status\tunnel.json and displayed in dashboard header. |
| **Binary** | `C:\1-AI\APPS\PYTHON\python.exe` |
| **Parameters** | `tunnel_manager.py` |
| **Working dir** | `C:\QIH\engine\hive\tunnel` |
| **Stdout log** | `C:\QIH\engine\hive\tunnel\LOGS\tunnel_service.log` |
| **Stderr log** | `C:\QIH\engine\hive\tunnel\LOGS\tunnel_service.log` |
| **Start type** | AUTO_START |
| **Account** | LocalSystem |

### QI_BrainAPI
| Field | Value |
|---|---|
| **Display name** | QI — Brain API |
| **Description** | QI Brain — hive nervous system. SQLite + ChromaDB + 12 MCP tools. Agent growth loop, decisions, features, sessions. FastAPI on port 9011. (Port 9010 permanently squatted by Logitech G HUB lghub_agent.exe — moved 2026-05-14.) |
| **Binary** | `C:\1-AI\APPS\PYTHON\python.exe` |
| **Parameters** | `C:\QIH\engine\brain\api.py` |
| **Working dir** | `C:\QIH` |
| **Port** | 9011 |
| **Stdout log** | `C:\QIH\engine\brain\LOGS\qi_brain_api.log` |
| **Stderr log** | `C:\QIH\engine\brain\LOGS\qi_brain_api.log` |
| **Start type** | AUTO_START |
| **Account** | LocalSystem |

### QI_Elevate
| Field | Value |
|---|---|
| **Display name** | QI — Elevation Broker |
| **Description** | Elevation broker daemon. Accepts requests from QI projects/agents to execute commands at admin integrity level. |
| **Binary** | `C:\1-AI\APPS\PYTHON\python.exe` |
| **Working dir** | `C:\QIH\engine\common` |
| **Stdout log** | `C:\QIH\logs\elevation\broker_stdout.log` |
| **Stderr log** | `C:\QIH\logs\elevation\broker_stderr.log` |
| **Start type** | AUTO_START |
| **Account** | LocalSystem |
| **NSSM binary** | `C:\QIH\engine\bin\nssm.exe` |
| **Registered** | 2026-05-13 (was running but not in registry) |

### QI_HiveIngest
| Field | Value |
|---|---|
| **Display name** | QI — Hive Ingest Worker |
| **Description** | Hive ingestion worker. Watches sources and ingests events/data into the Hive Brain (qi_brain.db / ChromaDB). |
| **Binary** | `C:\1-AI\APPS\PYTHON\python.exe` |
| **Working dir** | `C:\QIH\engine\hive\ingest` |
| **Stdout log** | `C:\QIH\logs\hive\ingest_stdout.log` |
| **Stderr log** | `C:\QIH\logs\hive\ingest_stderr.log` |
| **Start type** | AUTO_START |
| **Account** | LocalSystem |
| **NSSM binary** | `C:\QIH\engine\bin\nssm.exe` |
| **Registered** | 2026-05-13 (was running but not in registry) |

### QI_HiveApply
| Field | Value |
|---|---|
| **Display name** | QI — Hive Auto-Apply Pipeline |
| **Description** | QI Hive auto-apply pipeline for approved CoWork dispatches. Phase 1: inbox-fallback mode. Polls dispatch_runs every 10s. |
| **Binary** | `C:\1-AI\APPS\PYTHON\python.exe` |
| **Parameters** | `C:\QIH\engine\hive\apply\main.py` |
| **Working dir** | `C:\QIH\engine\hive\apply` |
| **Stdout log** | `C:\QIH\logs\hive_apply.log` |
| **Stderr log** | `C:\QIH\logs\hive_apply.log` |
| **Port** | none |
| **Start type** | AUTO_START |
| **Account** | LocalSystem (matches QI_HiveIngest — re-evaluate during Phase 2) |
| **NSSM binary** | `C:\QIH\engine\bin\nssm.exe` |
| **Kill switch** | Create `C:\QIH\engine\hive\apply\HALT` to drain queued items without stopping service |
| **Inbox dir** | `C:\QIH\inbox\hive_builder\` |
| **Registered** | 2026-05-13 |

### QI_HiveInspectorDrain
| Field | Value |
|---|---|
| **Display name** | QI — Hive Inspector Auto-Drain |
| **Description** | Deterministic inspector verdict drain. No LLM. Drains pending_review envelopes from C:\QIH\inbox\hive_inspector\ every 60s, auto-approves or rejects via mechanical checks, posts verdict to Brain API. Phase 2 zero-cost path. |
| **Binary** | `C:\1-AI\APPS\PYTHON\python.exe` |
| **Parameters** | `C:\QIH\engine\hive\inspect\main.py` |
| **Working dir** | `C:\QIH\engine\hive\inspect` |
| **Stdout log** | `C:\QIH\logs\hive_inspector_drain.log` |
| **Stderr log** | `C:\QIH\logs\hive_inspector_drain.log` |
| **Port** | none |
| **Start type** | AUTO_START |
| **Account** | LocalSystem |
| **NSSM binary** | `C:\QIH\engine\bin\nssm.exe` |
| **Inbox dir** | `C:\QIH\inbox\hive_inspector\` |
| **Done dir** | `C:\QIH\inbox\hive_inspector\done\` |
| **Quarantine dir** | `C:\QIH\inbox\hive_inspector\quarantine\` |
| **Kill switch** | `nssm stop QI_HiveInspectorDrain` — envelopes accumulate harmlessly, no data loss |
| **Registered** | 2026-05-14 |

---

## Quick Reference — NSSM Commands

```bat
REM Status check (all QI services)
for %s in (QI_MaiaBot QI_MaiaTunnel QI_MaiaDemoTunnel QI_MaiaGradio QI_NayaBot QI_NayaGradio QI_NEXUS QI_Dashboard QI_DashboardTunnel QI_BrainAPI QI_Elevate QI_HiveIngest QI_HiveApply QI_HiveInspectorDrain QI_KazeConfigAPI) do @echo %s: & C:\QIH\engine\bin\nssm.exe status %s

REM Restart a specific service (NSSM binary standardized 2026-04-22)
C:\QIH\engine\bin\nssm.exe restart QI_MaiaBot

REM Check logs
type C:\QI\LOGS\maia_service_log.txt
type C:\QIH\engine\brain\LOGS\qi_brain_api.log
```

---

## If Renne Reports a Service Problem — Lookup Table

| Symptom | Service | Log file | First check |
|---|---|---|---|
| Maia not responding | QI_MaiaBot | `C:\QI\LOGS\maia_service_log.txt` | `nssm status QI_MaiaBot` |
| Maia tunnel URL gone | QI_MaiaTunnel | `C:\QI\LOGS\tunnel_log.txt` | `nssm status QI_MaiaTunnel` |
| Maia Gradio UI (:7860) down | QI_MaiaGradio | `C:\QI\LOGS\maia_gradio_error.log` | `nssm status QI_MaiaGradio` |
| Maia Gradio demo down | QI_MaiaDemoTunnel | `C:\QI\LOGS\Maia_Gradio_Tunnel_Log.txt` | `nssm status QI_MaiaDemoTunnel` |
| Naya not responding | QI_NayaBot | `C:\NAYA\LOGS\naya_service_log.txt` | `nssm status QI_NayaBot` |
| Naya UI down | QI_NayaGradio | `C:\NAYA\LOGS\naya_gradio_error.log` | `nssm status QI_NayaGradio` |
| NEXUS not running | QI_NEXUS | `C:\NEXUS\LOGS\nexus_service.log` | `nssm status QI_NEXUS` |
| Dashboard (:8600) down | QI_Dashboard | `C:\QIH\engine\hive\dashboard\LOGS\dashboard.log` | `nssm status QI_Dashboard` |
| Dashboard tunnel URL gone | QI_DashboardTunnel | `C:\QIH\engine\hive\tunnel\LOGS\tunnel_service.log` | `nssm status QI_DashboardTunnel` |
| Brain API (:9011) down | QI_BrainAPI | `C:\QIH\engine\brain\LOGS\qi_brain_api.log` | `nssm status QI_BrainAPI` |
| Elevation broker not responding | QI_Elevate | `C:\QIH\logs\elevation\broker_stderr.log` | `nssm status QI_Elevate` |
| Hive ingest stalled | QI_HiveIngest | `C:\QIH\logs\hive\ingest_stderr.log` | `nssm status QI_HiveIngest` |
| Auto-apply pipeline stalled / dispatches stuck in queued | QI_HiveApply | `C:\QIH\logs\hive_apply.log` | `nssm status QI_HiveApply`; check for HALT file |
| Inspector inbox not draining / envelopes stuck in pending_review | QI_HiveInspectorDrain | `C:\QIH\logs\hive_inspector_drain.log` | `nssm status QI_HiveInspectorDrain`; check quarantine/ dir |
| Kaze config UI down | QI_KazeConfigAPI | `C:\OC\runtime\logs\agents\kaze\kaze-config-api.log` | `nssm status QI_KazeConfigAPI` |

---

## Python Migration Note (historical, 2026-04-19)

All services currently run on `C:\1-AI\APPS\PYTHON\python.exe`. The planned migration to `C:\Python311\python.exe` was deferred and the legacy interpreter is now the standard. No action required.

---

## Naming Convention Rules (for future services)

- **All QI services** must start with `QI_`
- **Format:** `QI_<Project><Role>` where Role = Bot, API, Gradio, Tunnel, Worker, etc.
- **Examples:** `QI_EasyFlowAPI`, `QI_MQWorker`, `QI_NayaWorker`
- **No spaces** in service names — use underscores
- **Always set Description** — no blank descriptions
- **Always set AppDirectory** to the project root, not the Python install path
- **Register in this file** before installing

---

### QI_KazeConfigAPI
| Field | Value |
|---|---|
| **Display name** | QI - Kaze Config API |
| **Description** | REST API for Kaze feed/policy configuration UI. Reads and writes kaze-feeds.json and kaze-source-policy.json. |
| **Binary** | `C:\1-AI\APPS\PYTHON\python.exe` |
| **Parameters** | `C:\OC\repo\scripts\kaze\kaze-config-api.py` |
| **Working dir** | `C:\OC\repo\scripts\kaze` |
| **Port** | 8401 |
| **Stdout log** | `C:\OC\runtime\logs\agents\kaze\kaze-config-api.log` |
| **Stderr log** | `C:\OC\runtime\logs\agents\kaze\kaze-config-api.log` |
| **Start type** | AUTO_START |
| **Account** | LocalSystem |
| **NSSM binary** | `C:\QIH\engine\bin\nssm.exe` |
| **UI** | `http://localhost:18800/kaze-config/` |

### QI_MapSnap
| Field | Value |
|---|---|
| **Display name** | QI - MapSnap Schema Browser |
| **Description** | MapSnap Jenzabar schema browser. Local Python HTTP server. Added by dashboard registry-driven launcher build. |
| **Binary** | `C:\1-AI\APPS\PYTHON\python.exe` |
| **Parameters** | `Application\server.py` |
| **Working dir** | `C:\MapSnap` |
| **Port** | 9876 |
| **Stdout log** | `C:\MapSnap\LOGS\QI_MapSnap.stdout.log` (rotated at 5 MB) |
| **Stderr log** | `C:\MapSnap\LOGS\QI_MapSnap.stderr.log` (rotated at 5 MB) |
| **Start type** | AUTO_START |
| **Account** | LocalSystem |
| **NSSM binary** | `C:\QIH\engine\bin\nssm.exe` |
| **Added** | 2026-05-13 |

### QI_CogniBase
| Field | Value |
|---|---|
| **Display name** | QI - CogniBase OnBase AI Platform |
| **Description** | CogniBase FastAPI server. Local OnBase metadata mirror + vector store + report generation. Runs from project venv. |
| **Binary** | `C:\CogniBase\.venv\Scripts\python.exe` |
| **Parameters** | `-m uvicorn Application.server.app:app --host 127.0.0.1 --port 8650` |
| **Working dir** | `C:\CogniBase` |
| **Port** | 8650 |
| **Stdout log** | `C:\CogniBase\LOGS\QI_CogniBase.stdout.log` (rotated at 5 MB) |
| **Stderr log** | `C:\CogniBase\LOGS\QI_CogniBase.stderr.log` (rotated at 5 MB) |
| **Start type** | AUTO_START |
| **Account** | LocalSystem |
| **NSSM binary** | `C:\QIH\engine\bin\nssm.exe` |
| **Setup note** | Requires `sqlglot` in venv. Run `C:\CogniBase\.venv\Scripts\pip.exe install -r requirements.txt` if dependencies drift. |
| **Added** | 2026-05-13 |

### QI_NayaTunnel
| Field | Value |
|---|---|
| **Display name** | QI - Naya Cloudflare Tunnel |
| **Description** | Cloudflare quick tunnel exposing Naya Gradio UI (port 7861) for remote demos. |
| **Binary** | `C:\Program Files (x86)\cloudflared\cloudflared.exe` |
| **Parameters** | `tunnel --url http://localhost:7861` |
| **Working dir** | `C:\Program Files (x86)\cloudflared` |
| **Port** | 7861 (proxied) |
| **Stdout log** | `C:\NAYA\LOGS\QI_NayaTunnel.stdout.log` |
| **Stderr log** | `C:\NAYA\LOGS\QI_NayaTunnel.stderr.log` |
| **Start type** | AUTO_START |
| **Added** | 2026-05-13 |

### QI_NEXUSTunnel
| Field | Value |
|---|---|
| **Display name** | QI - NEXUS Cloudflare Tunnel |
| **Description** | Cloudflare quick tunnel exposing NEXUS UI (port 7880). |
| **Binary** | `C:\Program Files (x86)\cloudflared\cloudflared.exe` |
| **Parameters** | `tunnel --url http://localhost:7880` |
| **Working dir** | `C:\Program Files (x86)\cloudflared` |
| **Port** | 7880 (proxied) |
| **Stdout log** | `C:\NEXUS\LOGS\QI_NEXUSTunnel.stdout.log` |
| **Stderr log** | `C:\NEXUS\LOGS\QI_NEXUSTunnel.stderr.log` |
| **Start type** | AUTO_START |
| **Added** | 2026-05-13 |

### QI_CogniBaseTunnel
| Field | Value |
|---|---|
| **Display name** | QI - CogniBase Cloudflare Tunnel |
| **Description** | Cloudflare quick tunnel exposing CogniBase FastAPI (port 8650). |
| **Binary** | `C:\Program Files (x86)\cloudflared\cloudflared.exe` |
| **Parameters** | `tunnel --url http://localhost:8650` |
| **Working dir** | `C:\Program Files (x86)\cloudflared` |
| **Port** | 8650 (proxied) |
| **Stdout log** | `C:\CogniBase\LOGS\QI_CogniBaseTunnel.stdout.log` |
| **Stderr log** | `C:\CogniBase\LOGS\QI_CogniBaseTunnel.stderr.log` |
| **Start type** | AUTO_START |
| **Added** | 2026-05-13 |

### QI_MapSnapTunnel
| Field | Value |
|---|---|
| **Display name** | QI - MapSnap Cloudflare Tunnel |
| **Description** | Cloudflare quick tunnel exposing MapSnap schema browser (port 9876) for remote access. |
| **Binary** | `C:\Program Files (x86)\cloudflared\cloudflared.exe` |
| **Parameters** | `tunnel --url http://localhost:9876` |
| **Working dir** | `C:\Program Files (x86)\cloudflared` |
| **Port** | 9876 (proxied) |
| **Stdout log** | `C:\MapSnap\LOGS\QI_MapSnapTunnel.stdout.log` |
| **Stderr log** | `C:\MapSnap\LOGS\QI_MapSnapTunnel.stderr.log` |
| **Start type** | AUTO_START |
| **Status** | ✅ Live as of 2026-05-13 (reinstalled via gsudo + NSSM) |
| **Added** | 2026-04-24, reinstalled 2026-05-13 |

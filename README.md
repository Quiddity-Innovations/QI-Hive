# QI Hive

**The orchestration + brain layer of the Quiddity Innovations ecosystem.**

- 🧠 **QI Brain** (`engine/brain/`) — SQLite + ChromaDB + MCP. Port `9010`.
- 🔷 **Hive Dashboard** (`engine/hive/dashboard/`) — agent orchestration UI, kanban, health checks, config. Port `8600`.
- 🔧 **Shared helpers** (`engine/common/`) — `qi_logger` and utilities used across services.

---

## Folder Structure (QI Project Standard)

| Folder | Purpose |
|---|---|
| `engine/`    | Runnable code (brain, dashboard, common, bin) |
| `config/`    | Configuration — `logging.json` + service configs |
| `data/`      | Databases (`qi_brain.db`), state (`status.json`, `tasks.json`) |
| `logs/`      | Rotating logs — one subfolder per service |
| `tests/`     | Pytest suites |
| `docs/`      | Documentation incl. `QI_Project_Standard.md` |
| `tools/`     | One-off utilities (migrations, audits, seed scripts) |
| `ecosystem/` | Cross-project registry (ported from `C:\UNIVERSAL\ECOSYSTEM`) |
| `shared/`    | Cross-project shared artifacts (e.g. `sessions/`) |

See [`docs/QI_Project_Standard.md`](docs/QI_Project_Standard.md) for the full standard.

---

## Services (NSSM, prefixed `QI_`)

| Service | Port | AppDirectory | AppParameters |
|---|---|---|---|
| `QI_BrainAPI`  | 9010 | `C:\QIH` | `engine\brain\api.py` |
| `QI_Dashboard` | 8600 | `C:\QIH` | `engine\hive\dashboard\server.py` |

Service shim: `engine/bin/nssm.exe` (project-local copy — do not share).

---

## Quick Start

**Verify services:**
```
engine\bin\nssm.exe status QI_BrainAPI
engine\bin\nssm.exe status QI_Dashboard
```

**Open the Hive:** http://localhost:8600/hive

**Runtime config:** http://localhost:8600/config — change log levels live.

---

## Repo
https://github.com/Quiddity-Innovations/QI-Hive

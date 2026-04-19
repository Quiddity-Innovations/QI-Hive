# QI Hive — Session 02 Handoff Brief
# Date: 2026-04-19 | Status: READY FOR FINAL ADMIN STEP

---

## What Was Built This Session (Session 02)

### QI Project Standard — Defined and Applied
Created the canonical standard document at `docs/QI_Project_Standard.md`. Every QI project (new or migrated) now follows the same 7-folder layout:

```
<project-root>/
├── engine/     (runnable code — bin/, common/, brain/, hive/, etc.)
├── config/     (logging.json, service configs)
├── data/       (databases, status.json, tasks.json)
├── logs/       (rotating per-service)
├── tests/
├── docs/
├── tools/
└── README.md
```

### C:\QIH — Reorganized Into The Standard
- `engine/brain/` — `api.py`, `mcp.py`, `core/`, `bootstrap.py`, `feature_engine.py`, `tools/`
- `engine/hive/dashboard/` — `server.py`, `qi_brain_client.py`, `static/`, `index.html`
- `engine/common/qi_logger.py` — centralized logging factory (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- `engine/bin/nssm.exe` — project-local NSSM binary (one per project, not shared)
- `config/logging.json` — per-service log levels (brain_api, brain_mcp, dashboard, tunnel, health_check, growth_loop)
- `data/` — `qi_brain.db`, `status.json`, `tasks.json` (moved from brain/ and hive/)
- `ecosystem/` — full copy of `C:\UNIVERSAL\ECOSYSTEM\` (registry, standards, validators)
- `shared/sessions/` — shared session summary location (this file lives here now)
- `tools/finalize_migration.bat` — admin bat to rewire NSSM services

### Dashboard — /config Page Added
New page at `http://localhost:8600/config`:
- Table of all services with current log level
- Dropdown per service (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- Changes persist to `config/logging.json` and hot-apply in-process
- Nav item "Config" with `bi-sliders` icon

### Logging Standard
- All Python entry points must use `from engine.common.qi_logger import get_logger`
- No `print()` in production, no `logging.basicConfig()`
- Rotating logs at 5 MB, 5 backups, UTF-8

---

## ONE THING NEEDS ADMIN ACTION

Run as Administrator:

```
C:\QIH\tools\finalize_migration.bat
```

This will:
1. Stop services (`QI_BrainAPI`, `QI_Dashboard`, `ClaudeManager`, `MaiaBot`)
2. Remove the duplicate legacy services (`ClaudeManager`, `MaiaBot`) — they were replaced long ago but never removed
3. Repoint `QI_BrainAPI` → `C:\QIH\engine\brain\api.py`
4. Repoint `QI_Dashboard` → `C:\QIH\engine\hive\dashboard\server.py`
5. Restart both and verify

`ClaudeManager` is the real culprit holding port 8600 — removing it frees the port for `QI_Dashboard`.

---

## Services — Expected State After Bat Run

| Service | Status | AppDirectory | AppParameters |
|---|---|---|---|
| QI_BrainAPI | RUNNING | `C:\QIH` | `engine\brain\api.py` |
| QI_Dashboard | RUNNING | `C:\QIH` | `engine\hive\dashboard\server.py` |
| ClaudeManager | REMOVED | — | — |
| MaiaBot | REMOVED | — | — |
| NayaTunnel | untouched (decide later) | — | — |
| NEXUSTunnel | untouched (decide later) | — | — |

---

## Next Session Agenda (Session 03)

1. **Run `finalize_migration.bat`** as admin → verify `:8600/hive` and `:8600/config`
2. **Switch services to project-local nssm.exe** — requires remove + reinstall; currently they still use the central `C:\UNIVERSAL\dashboard\nssm.exe`
3. **Update `qi_brain_mcp.py` paths** — still references `C:\UNIVERSAL\qi_brain` in a few places; switch to `C:\QIH\data\qi_brain.db`
4. **Port audit tool** — `tools/port_audit.py` to flag services bound to wrong/unregistered ports
5. **Delete old folders** — `C:\CLAUDE` and `C:\UNIVERSAL\qi_brain` (archive first to `C:\ARCHIVE\`)
6. **qi_validator update** — extend to check the 7-folder standard compliance
7. **Decide fate of `NayaTunnel` / `NEXUSTunnel`** — rename to `QI_` prefix or remove
8. **Begin Maia migration** — first project to move to `C:\QIP\Maia` under the new standard

---

## Folder Strategy (unchanged)

| Folder | Purpose | Status |
|---|---|---|
| `C:\QIH` | QI Hive — orchestration + brain | Active (reorganized this session) |
| `C:\UNIVERSAL` | Legacy shared folder | Staying — other projects still write here |
| `C:\UNIVERSAL\ECOSYSTEM` | Cross-project registry | Mirrored to `C:\QIH\ecosystem\` — delete after pointer updates |
| `C:\UNIVERSAL\qi_brain` | Old brain location | To delete in Session 03 after verification |
| `C:\CLAUDE` | Old dashboard | To archive + delete in Session 03 |
| `C:\QIP` | Future home for Maia, NEXUS, Naya, OC, EasyFlow | Not yet populated |
| `C:\QI` → `C:\QIB` | QI Business (brand/legal/admin) | After all projects moved |

---

## How to Start Session 03

Open a new Claude Code session from C:\QIH and say:

  Start QI Hive Session 03. Read LATEST.md at `C:\QIH\shared\sessions\LATEST.md`
  and `C:\QIH\data\status.json`. First task: run `finalize_migration.bat`
  as admin, verify services, then begin Maia migration to `C:\QIP\Maia`.

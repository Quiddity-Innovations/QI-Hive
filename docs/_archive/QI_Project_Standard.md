# QI Project Standard

**Version:** 1.0
**Effective:** 2026-04-19
**Applies to:** All QI projects (new and existing), including QI Hive, Maia, Naya, NEXUS, OpenClaw, EasyFlow, FileHQ, and MQ.

---

## 1. Folder Structure (Mandatory)

Every QI project lives in a single root folder (e.g. `C:\QIH`, `C:\QIP\Maia`, `C:\QIP\Naya`) with this exact 7-folder layout:

```
<project-root>/
├── engine/          Runnable code. Entry points live here.
│   ├── bin/         Project-local binaries (nssm.exe, cloudflared wrappers, etc.)
│   ├── common/      Shared helpers used across sub-services (qi_logger, db wrappers)
│   └── <service>/   One sub-folder per service (e.g. brain/, dashboard/, worker/)
├── config/          Configuration JSON/YAML. Hot-reloadable settings.
│   └── logging.json Per-service log level config (read by qi_logger)
├── data/            Databases, state files, persistent data
│   ├── *.db         SQLite databases
│   └── status.json  Project runtime state
├── logs/            Rotating logs written by qi_logger (per-service subfolder)
│   └── <service>/   e.g. logs/brain/, logs/dashboard/
├── tests/           Automated tests (pytest preferred)
├── docs/            Project documentation (this file lives here for each project)
├── tools/           One-off utilities (migrations, seeds, audits, generators)
└── README.md        Project overview, how to run, service list
```

**Only these files allowed at project root:** `README.md`, `.gitignore`, `.env.example`, `LICENSE`, and any `pyproject.toml`/`package.json` required by tooling.

**Forbidden at project root:** `.py` files, `.bat` files, log files, databases, loose scripts. If it runs, it lives in `engine/`. If it's data, it lives in `data/`.

---

## 2. Runnable Binaries

Each project ships its own copy of `nssm.exe` at `engine/bin/nssm.exe`. This protects against:
- File corruption taking down all services at once
- Antivirus quarantine of a single binary breaking the ecosystem
- NSSM version drift when one project upgrades before another

All NSSM service registrations MUST point at the project's local `engine/bin/nssm.exe`, not a shared one.

---

## 3. Logging (Mandatory)

Every Python entry point in a QI project uses `engine.common.qi_logger`:

```python
from engine.common.qi_logger import get_logger
log = get_logger("brain_api")
log.info("starting")
log.debug("detailed trace")
```

**Rules:**
- No `print()` in production code — only in `if __name__ == "__main__"` smoke tests.
- No `logging.basicConfig()` — the logger factory handles it.
- Each service has one entry in `config/logging.json` specifying level + file.
- Log levels: `DEBUG` · `INFO` · `WARNING` · `ERROR` · `CRITICAL`.
- Files rotate at 5 MB, keeping the last 5 backups.

**Runtime level changes:** Dashboard `/config` page writes `config/logging.json` and hot-applies changes to in-process loggers. Other services pick up on next restart.

---

## 4. Service Naming (Mandatory)

All NSSM Windows services MUST be prefixed `QI_`:

**Format:** `QI_<Project><Role>` — e.g. `QI_MaiaBot`, `QI_BrainAPI`, `QI_DashboardTunnel`

- No spaces — use underscores
- Always set `Description` in NSSM (no blank descriptions)
- Always set `AppDirectory` to the project root, not the Python install path
- Always register in `C:\QIH\ecosystem\QI_Service_Registry.md` before installing

---

## 5. Port Allocation (Mandatory)

Each project is allocated a port block in `C:\QIH\ecosystem\qi_registry.json`:

| Project | API | UI | Block |
|---|---|---|---|
| FileHQ | 8000 | — | 8000-8099 |
| Maia | 8001 | 7860 | 8100-8199 |
| Naya | 8002 | 7861 | 8200-8299 |
| NEXUS | 8010 | 7880 | 8300-8399 |
| OpenClaw | — (WSL) | — | 8400-8499 |
| MQ | — | — | 8500-8509 |
| EasyFlow | 8550 | — | 8550-8559 |
| QI Hive | 8600 (Dashboard), 9010 (Brain) | — | 8600-8699, 9010-9019 |

**Adding a service:** Pick the next free port in your block. Never pick adjacent ports at random.

---

## 6. Documentation

Every project must maintain:

- `README.md` at root — what it does, how to run, service list with ports
- `docs/QI_Project_Standard.md` — a copy of this standard (linked, not duplicated)
- `docs/ARCHITECTURE.md` — high-level component diagram
- `docs/CHANGELOG.md` — version history

**Session summaries** go to the shared location: `C:\QIH\shared\sessions\` (not per-project).

---

## 7. Git

- Every project has a GitHub repo under `github.com/Quiddity-Innovations/<project-name>`.
- `.gitignore` excludes `data/`, `logs/`, `__pycache__/`, `.venv/`, `node_modules/`, `.env`.
- `engine/`, `config/` (minus secrets), `tests/`, `docs/`, `tools/`, `README.md` go to git.

---

## 8. Validation

Run `python C:\QIH\ecosystem\qi_validator.py --project <id>` to check compliance:

- ✅ 7 required folders present
- ✅ No `.py` or `.bat` at project root
- ✅ `engine/bin/nssm.exe` exists
- ✅ `config/logging.json` exists and validates
- ✅ All services registered in `QI_Service_Registry.md`
- ✅ All services use `QI_` prefix
- ✅ All services' ports fall within allocated block

A project cannot ship until `qi_validator` returns green.

---

## 9. Exceptions

Exceptions to this standard MUST be documented in the project's `docs/ARCHITECTURE.md` with:
1. The rule being broken
2. Why the exception is necessary
3. Compensating control (what replaces the rule)
4. Planned removal date (or "permanent" with justification)

Exceptions should be truly exceptional. The goal is uniformity — open any QI project and find the same basic structure.

---

## 10. Migration Plan (2026-04-19)

| Project | Current path | Target path | Priority |
|---|---|---|---|
| QI Hive | `C:\QIH` | `C:\QIH` (reorganize in place) | Done this session |
| Maia | `C:\QI` | `C:\QIP\Maia` | Next |
| NEXUS | `C:\NEXUS` | `C:\QIP\NEXUS` | After Maia |
| Naya | `C:\NAYA` | `C:\QIP\Naya` | After NEXUS |
| OpenClaw | `C:\OC` | `C:\QIP\OpenClaw` | After Naya |
| EasyFlow | `C:\EasyFlow` | `C:\QIP\EasyFlow` | After OC |
| FileHQ | `C:\FileHQ` | `C:\QIP\FileHQ` | After EasyFlow |

Migrate one at a time. Each migration includes:
1. Restructure into 7-folder layout
2. Rewire NSSM services to new paths
3. Verify all services start and pass health check
4. Update `qi_registry.json` and `QI_Service_Registry.md`
5. Archive the old folder for one week, then delete

After all projects migrated to `C:\QIP`, rename `C:\QI` → `C:\QIB` (QI Business).

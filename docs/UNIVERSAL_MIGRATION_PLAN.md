# C:\UNIVERSAL → C:\QIH Migration Plan

**Owner:** Claude Code (autonomous)
**Started:** 2026-04-22
**Goal:** Absorb every live occupant of `C:\UNIVERSAL` into the QI Hive tree at `C:\QIH` and then delete `C:\UNIVERSAL` with **zero service outages and zero lost data**.

> Renne's mandate (2026-04-22): *"Universal is really a component of the QI Hive and it has to 'migrate' to within the QI Hive ecosystem and be the first one to be literally migrated into QIH and be deleted from C:\UNIVERSAL when all the projects no longer deposit anything into C:\Universal."*

---

## 1. Inventory (snapshot 2026-04-22)

| Folder under C:\UNIVERSAL | Files | MB | Role | Live? |
|---|---|---|---|---|
| DOCUMENTATION/Session_Summaries | 78 | 19.4 | Shared write target for every QI project's session .docx | **YES** (CLAUDE.md global rule writes here) |
| dashboard | 569 | 8.8 | Old standalone dashboard + nssm.exe binary used by 10 services | Binary: YES. Dashboard service: see note |
| node_modules | 384 | 8.1 | npm deps for old dashboard | No (only needed if old dashboard stays) |
| qi_brain | 118 | 7.0 | Legacy copy of Brain source | **NO** — live Brain runs from C:\QIH\engine\brain |
| TRAINING | 31 | 1.0 | Training materials | Cold storage |
| .claude | 52 | 0.4 | Scoped Claude project memory | Referenced by Claude sessions |
| ECOSYSTEM | 19 | 0.3 | `qi_registry.json`, `QI_Ecosystem_Map.md`, `QI_Standards.md`, validator | **YES** — CLAUDE.md + validator reference `C:\UNIVERSAL\ECOSYSTEM\` directly |
| qi_session | 6 | 0.1 | Unclear — session artifacts | Unknown |
| launcher | 1 | 0 | Stub | No |
| BACKUPS / __pycache__ | 0 | 0 | Empty / throwaway | No |
| Root: `session_context.py`, `qi_python.*` | — | — | SessionStart hook + python launcher wrappers | **YES** — hooks point here |

## 2. Service dependency map

Service NSSM binary reference (`PathName`) for all 11 QI services: `C:\UNIVERSAL\dashboard\nssm.exe`.
Service working directories (`AppDirectory`) — the actual code they execute:

| Service | AppDirectory | Live code outside UNIVERSAL? |
|---|---|---|
| QI_BrainAPI | C:\QIH | ✅ runs `C:\QIH\engine\brain\api.py` |
| QI_Dashboard | C:\QIH | ✅ runs `C:\QIH\engine\hive\dashboard\server.py` |
| QI_DashboardTunnel | **C:\UNIVERSAL\dashboard** | ❌ runs `tunnel_manager.py` inside UNIVERSAL |
| QI_MaiaBot | C:\QI | ✅ |
| QI_MaiaTunnel | C:\QI | ✅ |
| QI_MaiaDemoTunnel | C:\Program Files (x86)\cloudflared | ✅ |
| QI_NayaBot | C:\NAYA | ✅ |
| QI_NayaGradio | C:\NAYA | ✅ |
| QI_NEXUS | C:\NEXUS | ✅ |
| QI_Elevate | C:\QIH\engine\common | ✅ |
| QI_HiveIngest | C:\QIH\engine\hive\ingest | ✅ |

**Only QI_DashboardTunnel still executes from C:\UNIVERSAL.** The NSSM wrapper binary at `C:\UNIVERSAL\dashboard\nssm.exe` is referenced by 10 services but it's just the launcher executable — any identical `nssm.exe` at any path will work, and Windows caches the Services path until the service is re-installed.

## 3. Migration phases

### Phase 1 — Mirror static content into QIH (safe, in-place, no service restart)

| Source | Destination | Method |
|---|---|---|
| `C:\UNIVERSAL\DOCUMENTATION\Session_Summaries` | `C:\QIH\shared\documentation\session_summaries` | `robocopy` MIR |
| `C:\UNIVERSAL\TRAINING` | `C:\QIH\shared\training` | `robocopy` MIR |
| `C:\UNIVERSAL\ECOSYSTEM` | `C:\QIH\ecosystem` | `robocopy` (skip `.bak`, prefer newer) |
| `C:\UNIVERSAL\qi_session` | `C:\QIH\shared\sessions` | `robocopy` MIR |
| `C:\UNIVERSAL\.claude` | `C:\QIH\.claude_universal` | `robocopy` (reference only) |

**Status:** Phase 1 executed 2026-04-22.

### Phase 2 — Reroute writers

1. Update user CLAUDE.md global rule:
   *"All session .docx summaries write to `C:\QIH\shared\documentation\session_summaries`"* (deprecate `C:\UNIVERSAL\DOCUMENTATION\Session_Summaries`).
2. Update CLAUDE.md ECOSYSTEM REGISTRY block: registry lives at `C:\QIH\ecosystem\` (not `C:\UNIVERSAL\ECOSYSTEM\`).
3. Update `qi_validator.py`, `qi_new_project.py` path references.
4. Add a one-time junction/symlink `C:\UNIVERSAL\DOCUMENTATION\Session_Summaries` → `C:\QIH\shared\documentation\session_summaries` as a safety net so any script that hasn't been updated keeps working.

**Status:** Pending — needs Renne-approved CLAUDE.md edit. Junction requires admin (gsudo).

### Phase 3 — QI_DashboardTunnel relocation (needs admin + service restart)

1. `robocopy C:\UNIVERSAL\dashboard C:\QIH\engine\hive\dashboard_legacy /MIR` — copy everything.
2. Identify the exact files QI_DashboardTunnel needs (likely `tunnel_manager.py` + config).
3. `gsudo nssm set QI_DashboardTunnel AppDirectory C:\QIH\engine\hive\dashboard_legacy`.
4. `gsudo nssm set QI_DashboardTunnel AppParameters C:\QIH\engine\hive\dashboard_legacy\tunnel_manager.py`.
5. `gsudo Restart-Service QI_DashboardTunnel`.
6. Verify tunnel is still up (check `C:\UNIVERSAL\dashboard\LOGS\tunnel_service.log` → new path in new location).

**Status:** Pending — requires Renne present to confirm tunnel works after move.

### Phase 4 — NSSM binary relocation (needs admin + rewrite all 10 service registrations)

Every QI_* service currently has `PathName = C:\UNIVERSAL\dashboard\nssm.exe`. To truly cut the cord:

1. Verify `C:\QIH\engine\bin\nssm.exe` exists and is the same version — done, both 504 KB.
2. For each service: `gsudo nssm remove <name> confirm` then `gsudo nssm install <name> C:\QIH\engine\bin\nssm.exe ...` with all the settings restored. **This is a full re-registration.**
3. Alternative (safer): leave a copy of `nssm.exe` at `C:\UNIVERSAL\dashboard\nssm.exe` forever as a compatibility shim, and only delete it as the last step.

**Status:** Pending — safer to leave shim in place until Phase 5.

### Phase 5 — qi_brain orphan cleanup

`C:\UNIVERSAL\qi_brain\qi_brain_api.py` (Apr 20 16:26) is older than the live `C:\QIH\engine\brain\api.py` (Apr 20 18:58). No service executes from it. No cross-reference scan has found a live consumer. **Safe to delete after a 7-day quarantine.** Until then, rename to `qi_brain.LEGACY_DELETE_AFTER_2026-04-29`.

### Phase 6 — Old dashboard on port 9000 (C:\UNIVERSAL\dashboard)

The Hive Dashboard (port 8600) is the active UI. The old dashboard (port 9000, if still listening) is legacy. Decision: **retire**. Steps:

1. Confirm nothing hits `:9000` (`netstat` + access logs).
2. Archive `C:\UNIVERSAL\dashboard` → `C:\QIH\engine\archive\old_dashboard_9000\`.
3. Delete from UNIVERSAL.

### Phase 7 — Root file cleanup

- `C:\UNIVERSAL\session_context.py` — duplicate of Claude Code hook. The live hook lives at `C:\Users\renne\.claude\session_context.py`. Archive copy into `C:\QIH\engine\archive\` then delete.
- `C:\UNIVERSAL\qi_python.*` — launcher wrappers. If referenced nowhere, delete. If referenced, move to `C:\QIH\engine\tools\`.

### Phase 8 — Final verification + `rmdir C:\UNIVERSAL`

Preconditions:
- All services running without references to UNIVERSAL (verify with `nssm get` loop).
- Seven-day watch on `C:\UNIVERSAL` with a FileSystemWatcher script — no writes during that window.
- `git grep` returns zero hits for `C:\\UNIVERSAL` or `C:/UNIVERSAL` across QIH, QI, NAYA, NEXUS, OC, FILEHQ, EASYFLOW repos.

Then: `gsudo Remove-Item C:\UNIVERSAL -Recurse -Force`. Snapshot to `C:\QIH\engine\archive\universal_final_YYYY-MM-DD.zip` first.

## 4. Safety rules during migration

1. **Copy before move.** Every step uses `robocopy` or `Copy-Item`, never `Move-Item`, until the destination is verified live.
2. **No service is re-registered without gsudo + explicit Renne-present confirmation** (Phase 3–4).
3. **Brain state for `universal` stays `migrating` until the folder is physically gone.** Then flip to `retired`.
4. Every phase ends with a commit + push and a decision logged to Brain.
5. **CLAUDE.md rule changes are the single riskiest step** — every running Claude session re-reads CLAUDE.md on next launch. Coordinate timing so sessions converge on the new paths in one cycle.

## 5. Current status

| Phase | Status |
|---|---|
| 1. Mirror static content | ✅ Executed 2026-04-22 |
| 2. Reroute writers | ⏳ Drafted — CLAUDE.md edit pending Renne |
| 3. QI_DashboardTunnel relocation | ⏳ Waits for Renne-present window |
| 4. NSSM binary relocation | ⏳ Waits for Renne-present window (or deferred indefinitely via shim) |
| 5. qi_brain orphan cleanup | ⏳ Quarantine 7 days → delete 2026-04-29 |
| 6. Old dashboard retirement | ⏳ Verify :9000 traffic first |
| 7. Root file cleanup | ⏳ After phase 2 |
| 8. `rmdir C:\UNIVERSAL` | ⏳ After 7-day silence + global grep zero |

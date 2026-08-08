# QI Naming Standardization

**Goal (Renne, 2026-06-23):** When a UAC consent popup appears for a service
restart, identify *which product* it belongs to. Also standardize control
batch files to `<Product>_<Role>.bat`.

## Key finding
The UAC dialog shows an executable's embedded **FileDescription**, *not* its
filename. The shared `C:\QIH\engine\bin\nssm.exe` reports "the non-sucking
service manager" for every one of the 38 `QI_*` services. So renaming the file
alone would NOT change the popup. The fix is **per-product copies of nssm,
each with its FileDescription rewritten to name the product**, with every
service re-pointed to its product's copy.

## What runs Sat 2026-06-27 00:05 — the midnight ending Friday (task `QI_NamingStandardize_Friday`, as SYSTEM)
`run_friday_standardization.ps1`:
1. **NSSM** (`standardize_nssm.ps1 -Execute`): re-point all 38 `QI_*` services
   from the shared `nssm.exe` to their per-product copy (e.g. `Maia_NSSM.exe`,
   `Naya_NSSM.exe`), then restart + verify each. Per-service auto-rollback on
   failure. The 18 copies are **already pre-staged + relabeled** in
   `C:\QIH\engine\bin\` (non-destructive; services point at the old binary
   until Friday).
2. **Batch Tier-1** (`standardize_batch.py --map batch_rename_tier1.json`):
   rename 12 collision-free control/launch batch files to `<Product>_<Role>.bat`,
   rewriting references **project-scoped only** (generic names like
   `install_service.bat` exist in several projects).
2b. **Batch Tier-2** (`standardize_batch.py --map batch_rename_tier2.json`):
   rename the remaining 25 (collisions resolved with unique
   `<Product>_<Role>_<Qualifier>.bat` names; includes the 3 task-referenced bats).
2c. **Task actions** (`update_task_actions.ps1`): rewrite the Arguments of
   4 scheduled tasks (`QI_ClaudeVoiceBridgeCheck`, `QI_ClaudeVoiceMeeting_8AM`,
   `QI_TubeScout_AM`, `QI_TubeScout_PM`) to the renamed bats.
3. Verify (services running, none left on shared nssm) and ping Renne on LINE
   (Tasuke) with the result.

Rollback manifests written per phase: `nssm_rollback_manifest.json`,
`batch_rollback_tier1.json`, `batch_rollback_tier2.json`, `task_actions_rollback.json`.

## Files
| File | Purpose |
|---|---|
| `service_map.json` | 38 services -> 18 product nssm copies + FileDescriptions |
| `standardize_nssm.ps1` | NSSM re-point executor (`-DryRun` / `-Execute`) |
| `batch_map.json` | full .bat inventory + risk classification |
| `batch_rename_tier1.json` | the 12 clean renames |
| `standardize_batch.py` | batch executor (`--dry-run` / `--execute`) |
| `run_friday_standardization.ps1` | Friday orchestrator (runs as SYSTEM) |
| `register_task.ps1` | registers the Friday task |
| `Register-FridayTask.bat` | one-click self-elevating registration |
| `rollback_all.ps1` | revert NSSM re-points + batch renames |
| `TIER2_REVIEW.md` | batch files needing a naming decision (not auto-run) |
| `nssm_rollback_manifest.json` / `batch_rollback_manifest.json` | written at run time |
| `logs/` | dry-run + execution logs |

## To arm it
Double-click **`Register-FridayTask.bat`** and approve one UAC prompt.
(Registering a SYSTEM task is the only step needing elevation; the QI_Elevate
broker is intentionally not allowed to create scheduled tasks.)

## Rollback
Run `rollback_all.ps1` elevated. NSSM points return to the shared `nssm.exe`;
batch renames + reference edits are reversed from the manifests.

## Tier-2 — now INCLUDED (approved 2026-06-23)
The 25 colliding + scheduled-task-referenced bats were given final unique names
(see `batch_rename_tier2.json` / `build_tier2_map.py`) and fold into the Saturday
run (phases 2b + 2c). The 3 task bats (`run_bridge_health.bat`,
`start_meeting_room.bat`, `run_cycle.bat`) are renamed AND their 4 task actions
rewritten. `TIER2_REVIEW.md` is the original proposal record.

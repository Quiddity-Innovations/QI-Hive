# Phase 4 — Consolidate to C:\APPS + separate code from data

**Author:** Claude Opus 5 session, 2026-08-09
**Status:** Plan + resolver delivered. Moves NOT yet executed.

---

## 1. The number that changes the approach

A reference scan across 21 project roots (`scan_refs.py`) found:

| Target | Refs | | Target | Refs |
|---|---:|---|---|---:|
| QIH | 21,725 | | 1-AI | 974 |
| QI | 12,458 | | Gamez | 633 |
| MapSnap | 7,213 | | CypherMiner | 583 |
| CLAUDE | 5,905 | | CogniBase | 498 |
| OC | 4,928 | | MQ | 328 |
| Retirement Analyzer | 3,574 | | EasyFlow | 306 |
| NAYA | 3,568 | | QIP | 208 |
| AutoPDF | 3,531 | | Lottery Wiz | 174 |
| MailBrain | 2,225 | | PlayDeck | 93 |
| NEXUS | 1,094 | | *(others)* | <120 each |

**~70,000 total references.** The brief says "update every reference". Taken
literally in one pass that is a very large, very brittle edit across live services.

But the tally is misleading. The bulk sits in:
- `C:\QIH\data\status.json` (1,316) — **regenerated** by the Hive, not authored
- `rollback\nssm_dump_all.txt` (876) — a **snapshot artifact**, must NOT be rewritten
- `inventory.txt` (385) — a historical record of the *old* layout
- `.claude\worktrees\...` — **git worktree duplicates** of files already counted
- `conversion_log.txt` (139) — an append-only log

Live, load-bearing references are perhaps 2-5% of that. The risk is not the volume —
it is that a blind find/replace would corrupt the rollback snapshots and historical
records that exist precisely to recover from a bad migration.

## 2. Therefore: junction-backed incremental moves

Do not attempt an atomic "move everything, fix everything" pass. For each app:

```
1. Stop the app's services
2. robocopy  C:\<App>  ->  C:\APPS\<App>          (copy, do not move)
3. Rename    C:\<App>  ->  C:\<App>.old
4. mklink /J C:\<App>  ->  C:\APPS\<App>          (junction: old path still works)
5. Start services, verify health endpoint
6. Rewrite the LIVE references (NSSM, registry, tunnels, tasks, MCP, CLAUDE.md)
7. Verify again with the junction still in place
8. Only after a clean run: delete the junction, verify once more, then C:\<App>.old
```

The junction at step 4 is the safety net: any reference missed at step 6 keeps
working instead of taking a service down. Phase 1 already used this pattern
successfully for the ComfyUI models folder, so it is proven on this machine.

**Rule: never delete `C:\<App>.old` in the same session as the move.** Give it a
full nightly cycle so the scheduled tasks (nightly reconcile, git sync, backup)
exercise the new path first.

### What must NOT be rewritten
- `migration_2026-08\phase2\rollback\**` — recovery snapshots
- `migration_2026-08\inventory.txt` — record of the pre-migration state
- `C:\QIH\data\status.json` — regenerated; let the Hive rewrite it
- any `*.log`, `conversion_log.txt`, append-only history
- `.claude\worktrees\**` — fix the real checkout; worktrees follow

## 3. Move order

Ordered by blast radius, lowest first. Each is a checkpoint.

| # | App | Services affected | Notes |
|---|---|---|---|
| 1 | AkiyaScout | none | 24 refs, no service — ideal rehearsal |
| 2 | Lottery Wiz | QI_LotteryWiz, QI_LotteryWizTunnel | space in path; good quoting test |
| 3 | TUBESCOUT | QI_TubeScout, +tunnel | |
| 4 | Retirement Analyzer | QI_RetirementAnalyzer | note registry says `C:\Retirement Analyzer`, NSSM says `C:\RetirementAnalyzer` — **inconsistent, fix during move** |
| 5 | CypherMiner | QI_CypherMinerUI, +tunnel | |
| 6 | M2V | tunnel only | 2 stale venvs to recreate |
| 7 | PersonalSong | none | 2 stale venvs |
| 8 | Gamez | QI_GamezProxy, QI_GamezQuantProxy, +tunnel, +QI_GamezAIPin task | |
| 9 | AutoPDF | QI_AutoPDF, QI_AutoPDFMCP, +tunnel | also an MCP endpoint on :8701 |
| 10 | MapSnap | QI_MapSnap ×4, +tunnel | 7.2k refs, MCP on :8651 |
| 11 | CogniBase | QI_CogniBase, +tunnel | venv must already be rebuilt (Phase 2.4) |
| 12 | MQ, EasyFlow, QIP | QI_ConnectorMCP, +tunnels | |
| 13 | NEXUS | QI_NEXUS, QI_NexusMCP, +tunnel | |
| 14 | NAYA | QI_NayaBot, QI_NayaGradio, +tunnel | dedupe `C:\NAYA` / `C:/NAYA` MCP |
| 15 | QI (Maia) | QI_MaiaBot, QI_MaiaGradio, +2 tunnels, +queue drain | dedupe `C:\QI` / `C:/QI` MCP; `maia.db` moves to ProgramData |
| 16 | CLAUDE | QI_ClaudeVoice ×3, QI_Headroom | `headroom_env` venv is stale — rebuild |
| 17 | **PlayDeck** | QI_PlayDeck | **LAST**, per instruction |

## 3a. Decision — C:\QIH is a permanent exception

**Decided by Renne, 2026-08-09: `C:\QIH` stays at the root. It does not move to
`C:\APPS`, now or later.**

Rationale:
- It is the Hive engine — **Tier C** in the packaging plan. It never ships to a
  third party, so it gains nothing from the `C:\APPS` convention.
- ~21,700 references across the ecosystem, more than any other target.
- Hosts 30 of the machine's services; every other app move depends on it being
  up and stable.

This is recorded as a **decision, not a deferred move**, so it does not get
re-litigated in a later session.

### Target end state for the root of C:

```
C:\APPS      all self-built applications
C:\QIH       the Hive engine (exception, above)
C:\TEMP      keep (Renne's request)
C:\tmp       keep (Renne's request)
```

Everything else at the root is either Windows-owned, `Program Files`, or a
third-party installer's own default.

## 4. Code/data separation

The resolver is written and tested: **`C:\QIH\engine\common\qi_paths.py`**

```python
from qi_paths import paths
p = paths("maia")
p.data            # C:\ProgramData\Quiddity Innovations\maia
p.logs            # %LOCALAPPDATA%\Quiddity Innovations\maia\Logs
p.db("maia.db")   # full path inside p.data
```

Directories are created on access. Overrides: `QI_<APP>_DATA_DIR` (per-app, used
verbatim) then `QI_DATA_DIR` (shared root, scoped per app). Both verified working.

### Why the override matters for services
31 QI services run as **LocalSystem**. That account's `%APPDATA%` resolves inside
`C:\Windows\System32\config\systemprofile`, which is *technically* writable but a
terrible place to hide a config file an admin may need to edit. For services, set
`QI_CONFIG_DIR` and `QI_LOG_DIR` explicitly in the NSSM `AppEnvironmentExtra` so
config and logs land somewhere discoverable.

### Migration per app
1. Adopt `qi_paths` in the app's entry point.
2. Move existing data: `C:\QI\maia.db` -> `C:\ProgramData\Quiddity Innovations\maia\maia.db`.
3. Repoint NSSM `AppStdout`/`AppStderr` to the new log dir.
4. **Acceptance test:** make the code dir read-only for the running account and
   confirm the app still starts, logs, and persists. Until that passes, the app
   cannot be packaged (Phase 5 §2).

## 5. MCP duplicate cleanup

`~/.claude.json` holds four project-scoped entries where two are intended:

| Key | Server | Status |
|---|---|---|
| `C:\QI` | sqlite-maia | keep (backslash form) |
| `C:/QI` | sqlite-maia | **duplicate — remove** |
| `C:\NAYA` | sqlite-naya | keep |
| `C:/NAYA` | sqlite-naya | **duplicate — remove** |

All four point at `C:/1-AI/APPS/PYTHON/Scripts/mcp-server-sqlite.exe`, one of the
149 console-script launchers with the interpreter baked into the binary — so these
need the Phase 2 shebang rewrite regardless of which spelling survives. Their
`--db-path` also moves to ProgramData in §4.

## 6. Known inconsistencies to fix in passing

- **Retirement Analyzer**: registry `C:\Retirement Analyzer` vs NSSM AppDirectory
  `C:\RetirementAnalyzer`. One is wrong; the service is currently stopped, which may
  be why nobody noticed.
- **MaiaReconcile / MaiaRevertMiMo** scheduled tasks invoke
  `C:\QI\.venv\Scripts\python.exe` — **that venv does not exist**. Both tasks are
  already broken and have been silently failing. Repoint to the real interpreter or
  retire them.
- **QI_NightlyBackup** was reported in the handoff as pointing at a dead
  `C:\UNIVERSAL\...` path. **It does not exist on this machine at all** — it was
  presumably deleted since. No action needed; correct the handoff.
- `C:\QIH\hive\OpenSpace\.venv` is stale and `C:\CLAUDE\OpenSpace` is gone. The
  `openspace` editable install is dangling. Drop, do not recreate.

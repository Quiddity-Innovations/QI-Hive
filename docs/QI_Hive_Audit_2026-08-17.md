# QI Hive — Audit & Remediation, 2026-08-17

**Scope:** `C:\QIH` — full design-vs-reality audit, followed by execution of the fixes.
**Method:** Read-only audit first, then remediation. Every data change took a backup.
**Backups:** `C:\QIH\_archive\audit_2026-08-17\` plus timestamped `.bak-idfix-*` files.

---

## Headline

The Hive's **observe layer** is healthy and genuinely used. The **act layer** — the part
meant to close the loop — had never worked in production. Everything that reads,
measures, indexes or reports was alive and accurate. Everything that decides, applies
or enforces was idling, backlogged, or had been tested once in May and left running.

---

## What was fixed

### 1. Nightly git sync excluded the Hive itself ✅
`tools/nightly_git_sync.py` synced `AutoPDF`, `PersonalSong` and `M2V` — **not `C:\QIH`**.
It reported `LastTaskResult=0` every night while the Hive accumulated 304 uncommitted
files and went 9 days without a commit. The green light was measuring other repos.

- Added `C:\QIH` to `REPOS`.
- Added `EXTERNALLY_SYNCED` (currently `C:\APPS\QI`, owned by MaiaNightlySync) so
  double-commits are impossible.
- Added `coverage_check()`: compares `REPOS` against `qi_registry.json` every run and
  **logs any registry repo that syncs nowhere**. It warns only — it never auto-commits
  a repo the owner has not opted into.

> ⚠️ First run of the coverage check reported **17 registry repos that sync nowhere**:
> akiyascout, avatarstudio, claude_manager, cognibase, connector, cypherminer,
> digitization, easyflow, gamez, lotterywiz, mapsnap, mq, naya, nexus, openclaw,
> retirementanalyzer, tubescout. **Deliberately left for Renne to decide** — enrolling
> 17 repos in nightly auto-commit is a policy call, not a bug fix.

### 2. Dual project-ID namespace — the root cause of most drift ✅
`status.json` held **55 entries for 34 projects**: canonical snake_case ids alongside
display-name keys frozen at 2026-07-28.

Root cause found: `C:\APPS\CLAUDE\supervisor\supervisor.py` keyed its writes by
**display name** and clobbered the ingest's `_meta`. It is not scheduled anywhere and
last ran 2026-07-28, which is why its rows sat frozen while canonical rows stayed live.

- **supervisor.py fixed at source** — now keys by `proj["id"]`, writes its own
  `_supervisor_meta` instead of clobbering `_meta`, and uses `setdefault` for `status`
  so it can never overwrite editorial state owned by nightly_reconcile/Brain.
- **`tools/audit_fix_status_ids.py`** (new, idempotent): merged 24 ghost rows onto their
  canonical row, promoted 2 (`AkiyaScout`, `Headroom`) that had no canonical row, and
  parked 1 retired project (`fidelityanalyzer`) under `_retired_projects` rather than
  deleting it. **55 → 30 projects.**

### 3. Brain heartbeats logged under the wrong project id ✅
**5,231 of 5,375 heartbeats (97%) were written as `qihive` instead of `qi_hive`.**
Every session-freshness and brain-drift query therefore saw a project with almost no
activity — which is why the Inspector had been filing false "no session activity"
dispatches against `qi_hive` for months.

- **`tools/audit_fix_brain_ids.py`** (new, idempotent, takes a real online backup via
  the SQLite backup API): rewrote 5,337 rows across `agent_heartbeats` and `session_log`
  (`QI_Hive`/`qihive` → `qi_hive`, `NEXUS` → `nexus`, `OpenClaw`/`OC` → `openclaw`,
  `Maia` → `maia`, `ClaudeVoice` → `claude_voice`). `unknown` and retired ids are left
  alone deliberately.
- **Fixed at the boundary:** `engine/brain/api.py` `POST /api/agent/heartbeat` now runs
  the caller-supplied `project_id` through the existing `_resolve_pid()` resolver, the
  same as every other write path. A heartbeat is telemetry, so an unresolvable id is
  logged and kept rather than failing the caller.

> ⚠️ **This one is not live yet.** `QI_BrainAPI` has four dependent services
> (Maia, Naya, NEXUS, Dashboard) and Maia serves public LINE traffic, so it was not
> cascade-restarted for a telemetry fix. **The change activates on the next Brain
> restart.**

### 4. Dispatch queue had no consumer ✅
27 pending dispatches (oldest 2026-06-18, 60 days) plus 9 `approved` rows that were only
ever May e2e test fixtures.

- **`tools/audit_drain_dispatches.py`** (new, idempotent): closed 16 — 9 test fixtures,
  6 raised while activity was logged under a wrong id, 1 superseded duplicate. Rows are
  marked `resolved` with an explanatory note rather than deleted, so the trail survives.
- **The 9 `gitignore_secrets` findings were real and were actually fixed**, not just
  closed: `tools/audit_fix_gitignores.py` added 31 entries across 9 projects
  (`secrets/`, `.env`, `chroma/`). All 11 projects now report **pass**.
- Verified no sensitive file is currently tracked in git — the tree is clean.

### 5. `/api/agents` served `{}` ✅
`AGENTS_DIR` pointed at `C:\QIH\hive\Agents`, a folder that has not existed since the
UNIVERSAL→QIH migration. `/api/brain/agents` worked fine and returned all 15.

- `/api/agents` now serves the Brain-backed roster, merging legacy folder configs as
  enrichment only. The home-page agent table already preferred Brain data, so it was
  unaffected.

### 6. Legacy shadow tree archived ✅
`C:\QIH\hive\` was a 401 MB / 17,583-file shadow of `C:\QIH\engine\hive\`, carrying
divergent copies of `health_check.py`, `status.json`, `tasks.json` and `Dashboard/`.
Verified nothing imported from it. Moved to `_archive/legacy_hive_tree/` with a README
explaining what it is and why not to wire anything back to it.

### 7. `/api/health` timed out; health cache misconfigured ✅
`HEALTH_CACHE_TTL` was 30s against a 300s background refresh loop, so the cache was
expired ~90% of the time and any request touching it paid the full 12–47s subprocess
fan-out. `/api/health` simply timed out.

- TTL raised to 330s to match the refresh cadence.
- Added `cached_health_check()` — returns last result, never recomputes.
- `/api/health` is now **fully non-blocking**: serves cache instantly, or returns
  `{}` with an `X-QI-Health: warming` header and warms in a background thread.
- Result: **>45s timeout → 0.002s.**
- Also removed 5 phantom entries from `_SERVICE_MAP` (`QI_FidelityAnalyzer`,
  `QI_AvatarStudio`, `QI_PersonalSong`, `QI_M2V`, `QI_MQ` — never installed, so those
  projects could never report healthy) and added 3 real ones that were missing
  (`QI_RetirementAnalyzer`, `QI_Headroom`, `QI_PlayDeck`).

### 8. Public tunnels serving dead origins ✅
- **AutoPDF**: `QI_AutoPDF` was Stopped/Manual while `QI_AutoPDFTunnel` published
  `autopdf.quiddityinnovations.com`. Started the service (now returns 200) and set it
  to `SERVICE_AUTO_START` so it cannot silently drop again.
- **M2V**: no `QI_M2V` service exists at all — the tunnel had been publishing a dead
  origin. Stopped `QI_M2VTunnel` and set it to manual start.

### 9. Stuck inbox ✅
A 2026-05-15 ecosystem audit report (`.md`) sat in a `*.json`-only inbox for three
months, invisible to every 5-minute poll.

- Filed to `docs/_archive/QI_Ecosystem_Audit_2026-05-15.md`.
- `hive_ingest.py` now logs a one-time `[STRAY]` warning for any non-`.json` file in the
  inbox, so this can never be silent again.

---

## Not closed — needs Renne

### Auto-apply pipeline (`QI_HiveApply`) — strategic decision required
The service has run continuously since May. Total history: **7 runs, all May 13–14, all
synthetic test fixtures, all `failed` or `rejected_auto`.** `applied_commit` has never
been non-null. It has never applied a real change.

**Root cause of the failures is now identified:** the Hive services run as
**LocalSystem**, but the repo is owned by `renne`, so git refuses with
*"detected dubious ownership in repository"*. That is why `worktree_create` failed.

The fix is a `git config --system --add safe.directory C:/QIH` (or the equivalent in
SYSTEM's profile gitconfig). **That command is not in the elevation whitelist**
(`commands/whitelist.json`), and widening a security whitelist is not something to do
unilaterally — it needs Renne's explicit approval.

**Two options:**
1. **Finish it** — approve the whitelist addition, apply the git config, re-run the e2e.
2. **Retire it** — stop `QI_HiveApply` and drop the pipeline.

Recommendation: decide deliberately rather than leaving a service running that has never
done its job. There is no urgency either way — it is idle, not harmful.

### 17 unsynced repos
See §1. Enrolling them in nightly auto-commit is a policy call.

### 25 genuinely-open dispatches
Mostly a **newly surfaced** finding class: `nssm_registry` — a number of installed
`QI_*` services are not recorded in `qi_registry.json` (MapSnap family, NexusMCP,
PlayDeck, RetirementAnalyzer, several tunnels). Plus true `session_freshness` for
genuinely dormant projects (`mq` 133d, `personalsong` / `m2v` 60d) — the fix there is to
mark them paused rather than active.

---

## Correction to the original audit

The first-pass audit stated the task board's auto-sync was dead. That was wrong:
`_board_sync_loop()` runs every 300s and syncs correctly. The real defect was narrower —
the *cache TTL mismatch* that made `/api/health` time out. Recorded here so the
correction travels with the finding.

---

## Files changed

| File | Change |
|---|---|
| `tools/nightly_git_sync.py` | +`C:\QIH`, +`EXTERNALLY_SYNCED`, +`coverage_check()` |
| `tools/audit_fix_status_ids.py` | **new** — status.json namespace repair |
| `tools/audit_fix_brain_ids.py` | **new** — Brain project_id normalisation |
| `tools/audit_drain_dispatches.py` | **new** — dispatch queue drain |
| `tools/audit_fix_gitignores.py` | **new** — gitignore_secrets remediation |
| `engine/brain/api.py` | heartbeat `project_id` resolved via `_resolve_pid()` |
| `engine/hive/health_check.py` | TTL 30→330s, +`cached_health_check()`, `_SERVICE_MAP` corrected |
| `engine/hive/dashboard/server.py` | `/api/agents` → Brain, `/api/health` non-blocking |
| `engine/hive/ingest/hive_ingest.py` | `[STRAY]` warning for non-json inbox files |
| `C:\APPS\CLAUDE\supervisor\supervisor.py` | keys by registry id, stops clobbering `_meta` |
| `docs/_archive/QI_Ecosystem_Audit_2026-05-15.md` | filed from stuck inbox |
| `_archive/legacy_hive_tree/` | 401 MB shadow tree archived + README |
| 9 project `.gitignore` files | +31 secrets/vector-store entries |

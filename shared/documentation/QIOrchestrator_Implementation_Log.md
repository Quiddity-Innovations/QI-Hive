# QI Orchestrator — Implementation Log

> Covers: QI Hive Dashboard (port 8600) + QI Brain API (port 9011)
> Root: `C:\QIH\` — migrated from `C:\UNIVERSAL\` on 2026-04-22; that path no
> longer exists on disk (verified 2026-09-09). Header corrected 2026-09-17.

---

## 2026-09-20 - LLM Usage Tab: Trinity Visibility (ChatGPT/Codex + Gemini)
**Session Focus:** Bring the two non-Claude Trinity legs — ChatGPT via Codex and Gemini via the qi-gemini MCP, both live since 2026-09-08 — onto the LLM Usage tab, which until now measured Claude only

### Built
- **`engine/common/usage_assistants.py` (new, ~620 lines).** Codex: reads `~/.codex/sessions/**/rollout-*.jsonl` `token_usage_record` events - a measured (not estimated) input/cached-input/output/reasoning split from OpenAI's own client, covering both Claude's MCP delegations and sessions Renne drives directly in Codex Desktop (`originator` field separates them). Gemini: reads the new `data/gemini_mcp/tokens_YYYY-MM-DD.jsonl`; calls before 2026-09-20 predate that log and are reconstructed from `LOGS/gemini_mcp.log` as prompt_chars/4, flagged `estimated`. Public API: `today()`, `daily()`, `range_stats()`, `totals()`, `by_model()`, `by_provider()`, `by_project()`, `by_originator()`, `quota()`, `available()`, `pricing_text()`.
- **`config/llm_prices_external.json` (new).** OpenAI + Google list prices per 1M tokens, each with a `verified_on` date and source URL (verified 2026-09-20). Correcting a rate is now a data edit, not a code change; an unpublished rate is `inferred` (badged, costed at account default) or `unpriced` - never a silent guess.
- **`qi_gemini_mcp.py`** - added `_record_tokens()` / `_tokens_path()`; `_generate()` now writes Google's `usageMetadata` per call (previously discarded). Sizes only, never prompt/reply text. Verified live.
- **`server.py`** - guarded import of `usage_assistants`; five new endpoints (`/api/usage/assistants`, `/assistants/daily`, `/assistants/by_model`, `/assistants/sources`, `/api/usage/quota`); two new cards (`_render_three_legs`, `_render_assistant_detail`); Claude-only cards relabelled "Claude - ...".
- **`test_usage_assistants.py` (new)** - 17 tests (3 more added later this session for the WSL mirror), all passing alongside the existing 10 usage_stats tests (27 total).
- **`engine/common/usage_codex_wsl_sync.py` (new, later this session).** Mirrors WSL-side Codex rollout transcripts to `data/codex_wsl/sessions` so a LocalSystem service can read them - see "Gap found and fixed later this session" below.
- **`config/usage_assistants.json` (new, later this session).** Registers the mirror as an extra Codex session root; also honours a `QI_CODEX_EXTRA_ROOTS` env var.

### Five correctness traps caught and locked down with tests
- Codex ships three usage blocks per record (`usage`, `turn_token_usage`, `thread_token_usage`); reading the wrong one inflates a long thread by its own length - the same shape of bug as the 2026-09-16 Claude 6x overstatement. Read `usage` only, dedup on `response_id`.
- OpenAI folds `reasoning_output_tokens` INSIDE `output_tokens`; Google reports `thoughtsTokenCount` SEPARATELY and bills it as output - verified against each vendor's own totals. Gemini thoughts are added to output; Codex's are not.
- `QI_Dashboard` runs as LocalSystem, where `Path.home()` resolves to the systemprofile directory, not Renne's - the first live restart showed a confident zero for the whole ChatGPT leg. Fixed by mirroring `usage_stats._find_projects_dir`'s resolution order; `/api/usage/sources` and an on-page warning now make this failure loud instead of silent.
- `nssm restart` from an unelevated shell reported success while leaving the old process running; the real restart went through the elevation broker (`qi_elevate_client.run_elevated`).
- **Found later this session:** `codex mcp-server` - the binary Claude actually delegates to over MCP - runs under WSL, so every rollout transcript for a Claude-initiated delegation landed in `/home/hyosuke/.codex/sessions`, not the Windows profile the parser read. The ChatGPT column was silently counting only the sessions Renne drives himself. See "Gap found and fixed later this session" below.

### Verified live figures (30-day window)
⚠️ Superseded for the ChatGPT/Codex row - see the corrected, both-roots figures below. Claude and Gemini rows are unaffected.

| Leg | Calls | Fresh tokens | Cache re-reads | API-equivalent | Actual plan |
|---|---|---|---|---|---|
| Claude | 14,195 turns | 81.0M | 4.0B | $2,929.82 | Claude MAX |
| ~~ChatGPT / Codex~~ | ~~454~~ | ~~2.4M~~ | 36.1M | ~~$56.37~~ | ChatGPT Plus $20/mo |
| Gemini | 13 | 3.9K | 0 | $0.00 | AI Studio free tier $0/mo |

Codex totals reconciled exactly with a raw sum of the *Windows-root* rollout files (36,068,224 cached / 2,443,041 fresh) - dedup dropped nothing real on that side, but the reconciliation was scoped to only half the picture.

### Gap found and fixed later this session - WSL Codex sessions were invisible

**The gap:** `codex mcp-server` - the binary Claude delegates to over MCP - runs under WSL, so the rollout transcripts for every delegation Claude makes land in `/home/hyosuke/.codex/sessions`, NOT the Windows profile. Codex Desktop writes to `C:\Users\renne\.codex\sessions`. The parser was scanning only the Windows side, so the ChatGPT column counted the sessions Renne drives himself and silently dropped every call Claude delegated. Caught by making one deliberate `gpt-5.6-luna` MCP call and finding no matching rollout on the Windows side.

**Why it couldn't just read the WSL path:** `\\wsl.localhost\<distro>\...` is not enumerable from Python here - `is_dir()` returns False on a known-good path - and `QI_Dashboard` runs as LocalSystem, which has no WSL session at all.

**The fix (all live and verified):**
- New `engine/common/usage_codex_wsl_sync.py` - mirrors WSL rollouts to `data/codex_wsl/sessions`. Incremental (rollouts are append-only, so a file is re-copied only when its size changes), writes to a `.part` file then renames so a killed run can't leave a half-file, and validates every path against a strict regex before it reaches a shell.
- New `config/usage_assistants.json` - registers the mirror as an extra Codex root; also honours `QI_CODEX_EXTRA_ROOTS`.
- `usage_assistants.py` - `codex_sessions_dir()` became `codex_session_roots()` (a list); added `wsl_mirror_status()` and `_is_wsl_root()`; `available()` now reports `codex_roots`, `codex_windows_root`, `codex_wsl_root` and `codex_wsl_mirror`.
- `server.py` - the "All Three Legs" card now warns on the page if the WSL root is missing entirely, if the mirror is stale (>24h), or if its last run errored.
- New scheduled task **QI_CodexMirror** - hourly, `pythonw.exe` (no console, deliberately no `conhost --headless` wrapper), running as renne/Interactive because WSL needs a live user session. Registered, triggered, verified: second run correctly skipped all 38 files. Health is the freshness of `data/codex_wsl/_sync_state.json`, not the task's LastTaskResult.
- Tests: 3 more added - 17 in the new file, 27 passing with the existing usage_stats suite.

**Two more WSL traps** (both measured 2026-09-20, both fail silently with exit code 0):
1. Inside `wsl.exe -d <d> -u <u> -- bash -lc`, `$HOME` is empty - WSL hands the shell the Windows environment and the login shell doesn't repopulate it. `"$HOME/.codex/sessions"` resolved to `/.codex/sessions`, the `-d` guard failed, and the sync cheerfully reported `remote_files: 0`.
2. Shell variable assignment does not survive the round trip. Measured: `x="$(echo hi)"; echo "[$x]"` prints `[]`, while the inline form `echo "[$(echo hi)]"` prints `[hi]`.

Resolution: write these scripts with no shell variables at all and use bare `~`, which bash expands from `/etc/passwd` regardless of `HOME`.

**Corrected ChatGPT/Codex figures (30-day window, both roots):**
| Model | Leg | Calls | Fresh tokens | API-equiv |
|---|---|---|---|---|
| gpt-6-astra | ChatGPT/Codex | 316 | 1,579,377 | $53.77 |
| codex-auto-review (inferred price) | ChatGPT/Codex | 146 | 927,423 | $3.35 |
| gpt-5.6-terra | ChatGPT/Codex | 10 | 75,355 | $0.25 |
| gpt-5.6-luna | ChatGPT/Codex | 58 | 204,479 | $0.06 |
| gemini-3.5-flash-lite (est) | Gemini | 2 | 3,613 | $0.00 |
| gemini-3.6-flash (est) | Gemini | 11 | 284 | $0.00 |

ChatGPT/Codex leg totals (both roots): 530 calls, ~2.79M fresh tokens, ~$57.43 API-equivalent - up from the Windows-only 454 / 2.4M / $56.37 above. The two MCP-delegation models - luna (58 calls) and terra (10 calls), 68 calls totalling ~280K tokens - were entirely invisible before this fix. Total assistant events (ChatGPT/Codex + Gemini) rose from 471 to 543. The Claude row above is unchanged and still correct.

### Decision
Claude's figures were deliberately NOT merged into a combined total - three legs sit in one explicit comparison card, every Claude-only card relabelled, so a number never quietly means something other than its label (the root cause of the 2026-09-16 audit). Per Renne's 2026-09-08 directive, both assistant plans are flat-rate, so the card leads with quota (ChatGPT's 5-hour/weekly window, Gemini's calls-today vs the 200/day cap) over the dollar table.

### Not done
- Home-page "Claude usage strip" not yet extended to the two assistants - pending owner decision.
- `codex-auto-review` pricing still `inferred` at account default (gpt-5.6-terra), covering 146 of 530 ChatGPT/Codex calls (both roots).
- No freshness check yet on the Gemini token log itself.
- Confirm QI_CodexMirror is still running and `_sync_state.json` is fresh after the next reboot - it runs as renne/Interactive, so it only fires while Renne is logged on.

### Files Changed
- `C:\QIH\engine\common\usage_assistants.py` (new, modified again later this session)
- `C:\QIH\config\llm_prices_external.json` (new)
- `C:\QIH\engine\hive\dashboard\tests\test_usage_assistants.py` (new, 3 more tests added later)
- `C:\QIH\engine\mcp\qi_gemini_mcp.py`
- `C:\QIH\engine\hive\dashboard\server.py` (modified, then modified again later this session)
- `C:\QIH\engine\common\usage_codex_wsl_sync.py` (new, later this session)
- `C:\QIH\config\usage_assistants.json` (new, later this session)
- Scheduled task **QI_CodexMirror** registered (hourly, renne/Interactive)

---

## 2026-09-17 - Overnight Proofs, ccusage Cross-Check, Per-Project Offload Dimension
**Session Focus:** Verify the 2026-09-16 remediation survived its first unattended night, cross-check the usage figures against an independent tool, and clear the remaining leftovers

### Overnight proofs - all pass
- **Nightly backup** - `LOGS\nightly_backup\backup_20260917.log` ends `backup OK (6 databases, 0 old sets purged)` at 01:00:04; `shared\backups\db\2026-09-17` holds six .db files + manifest; `backup.py --verify` reports `integrity=ok` on all six (agent_hr, effort_ledger, maia, naya, nexus, qi_brain).
- **Scheduled Ops actions fired on their own for the first time.** chroma_backfill 03:15 rc 0 (+5 sessions embedded); supervisor 06:10 rc 0; snapshots 06:20 rc 0; self_audit 06:30 rc 0. The supervisor output names `C:\APPS\*` throughout - no pre-migration paths survive.
- **Task health** - `data/task_health.json`: OK 28, STALE 0, DEAD 0, ERROR 0. QI_NightlyBackup, QI_UsageSnapshot and QI_BrainDriftCheck_Daily all report `marker present in today's log`.
- **Usage snapshot** - `LOGS\usage_snapshot\usage_snapshot_20260917.log` carries 29 `snapshot OK` lines, one every ~30 min from 00:05.

### Fixed
- **Headroom Status badge, again - the probe this time, not the port.** Yesterday corrected the doctor's port (8787 -> 9020) but left `Get-NetTCPConnection -LocalPort 9020 -State Listen -ErrorAction SilentlyContinue` as the sole FAIL trigger. At 06:40 it returned nothing and pinned the badge red, in the *same run* where the doctor connected to 127.0.0.1:9020 and reported `up 11d 12h` with 0 failures. The proxy never went down: by the 13:50 re-run uptime read `up 11d 19h`, exactly the 7h10m elapsed. Get-NetTCPConnection resolves through CIM (root/StandardCimv2), and the silenced error turned "the probe broke" into "the proxy is down" - a false alarm of precisely the kind the badge was fixed to stop producing. A real TCP connect (3 tries, 700 ms apart) now decides; the CIM lookup is demoted to best-effort, used only to name the pid. Same rc contract.
- **Usage dedup was keeping a partial completion.** `dedup()` kept the *first* row per message id. Streaming writes one transcript row per chunk sharing one message id: input, cache-read and cache-write are fixed at request time and identical on every row, but output_tokens grows as the stream runs. Measured over 2026-08-19..09-17: 1,052 message ids had a varying output count, 0 had a varying cache-read or cache-write count, and 714,859 output tokens were being dropped. Now keeps the largest output per id (O(n) index map, first-seen order preserved). 30-day figure $4,071.98 -> $4,092.95.

### Built - per-project model-family dimension
`usage_daily_project(day, project)` and `usage_daily_model(day, model, family)` were separate tables, so the ledger could never answer "which families did THIS project use". `savings_by_project` therefore read the family split from the live transcripts, which reach back only ~40 days; every older window handed **every** project one blended rate - telling an opus-only project it could move ~1% of its spend to Ollama (false) and flattening the haiku-heavy projects where offloading actually pays.
- New table `usage_daily_project_family(day, project, family, ...)`, PK (day, project, family), 2,167 rows, 0 unreconciled. Purely additive: `usage_daily`, `usage_daily_project` and `usage_daily_model` are untouched, so the reconciliation invariant and the 2026-09-16 recalibration stand.
- Measured days group straight from transcript events; other days cross the day's project shares with its model-family shares, then normalise so family rows sum to that project's own day cost.
- `family_mix_by_project()` also returns each project's **measured share**, so the UI can label the rate `measured` or `modelled`. A reconstructed window is a derivation, not an observation, and must not read like one.
- `backfill()` now rebuilds the joint table in the same scope (it is derived from the two tables backfill just rewrote); `usage_snapshot_task` reports `NNNpf` and warns on unreconciled project-family days.
- Result on /usage: 15 project rows, 6 distinct offload rates, 0 `window blend` fallbacks.

### Cross-check - the Hive is the more accurate number
ccusage $4,248.03 vs Hive $4,071.98 over the same 30 days: a 4.14% gap that reconciles to 0.14%.

| Step | Amount |
|---|---|
| ccusage 30d | $4,248.03 |
| less cross-file duplicate copies | -$166.24 |
| less gpt-6-astra (Codex, non-Anthropic) | -$2.88 |
| = expected Hive figure | $4,078.91 |
| actual Hive figure | $4,072.93 |
| residual | -$5.98 (-0.14%) |

Both tools agree **to the token on 20 of 26 days**. All divergence sits in 2026-09-06..09-11, where transcripts were duplicated: on 09-06 two Baguapp session files carry the same 137 message ids with identical requestIds, and ccusage's total for that day is exactly 2x the Hive's. ccusage dedups within a file; the Hive dedups globally on message.id. Turn counts match exactly (17,943 both), so no turns are lost. After the output fix, the three models with no cross-file duplicates match ccusage **to the cent**: sonnet-5 $100.13, fable-5 $50.28, haiku-4-5 $1.09 - confirming both the price table and the parser.

### Agent HR
37 historical run rows renamed to the `builtin:<type>` convention `normalize_agent_name()` already emits (Explore 17, general-purpose 19, Plan 1; the bare `claude` roster row had 0 runs). Run total unchanged at 524; 0 bare builtin rows remain.

### Not done
- **Owner checklist (section 5 of the remediation report) not yet walked.** Owner reported not having checked it; no mismatches were raised, so none were reproduced. Still open.
- Smoke-test coverage and the backend per-family offload split were already delivered on 2026-09-16 - verified rather than rebuilt (71 tests pass, covering 25 nav routes + 28 API endpoints).

### Files Changed
- `engine/hive/dashboard/server.py` (headroom probe; `_mix_hint` basis tag) - .bak-headroom-20260917
- `engine/common/usage_stats.py` (`dedup` keeps max output) - .bak-dedup-20260917
- `engine/common/usage_dimensions.py` (new table, builder, reader, wiring) - .bak-projfamily-20260917
- `engine/common/usage_snapshot_task.py` (reports and guards project-family) - .bak-projfamily-20260917
- `engine/hive/agents/agent_hr.db` (37 rows renamed) - .bak-builtin-rename-20260917
- `C:\QIH\data\qi_brain.db` - new table `usage_daily_project_family`

---

## 2026-09-16 (evening) - Remediation Verification: supervisor KeyError, Headroom false alarm, usage cross-check
**Session Focus:** Verify the same-day audit remediation, close the loop on the overnight proofs, and independently confirm the corrected usage figures

### Verified (all proofs pass)
- **Nightly backup** - `LOGS\nightly_backup\backup_20260916.log` ends `backup OK (6 databases, 0 old sets purged)`; `shared\backups\db\2026-09-16` holds 6 .db files + manifest; `backup.py --verify` reports `integrity=ok` on all six.
- **Task health** - `data/task_health.json`: OK 28, STALE 0, DEAD 0, ERROR 0. QI_NightlyBackup, QI_UsageSnapshot and QI_BrainDriftCheck_Daily all report `marker present in today's log`.
- **Usage snapshot** - `LOGS\usage_snapshot\usage_snapshot_20260916.log` carries `snapshot OK` lines every ~30 min from 17:13.
- **Dashboard checklist** - /news (no negative ages, digest card), /tunnels (Kaze 18800, Maia Quiddam :8500, Connector 9030, no M2V), /health (no phantom projects), /services (3 orphans gone, legacy badges), /compliance (qi_hive 15 pass / 0 fail), /guide (25 numbered tabs) all confirmed.

### Fixed
- **Supervisor crashed on every run since 2026-08-09, silently.** `inspect_project()` returned early for a project whose registered path does not exist without setting `severity`; `render_dashboard()` then raised `KeyError: 'severity'`. `report.json` is written first, so the failure was invisible: the report kept updating while `C:\APPS\CLAUDE\DASHBOARD.md` stayed frozen at 2026-08-09 for 38 days. Triggered by `transfer_station`, whose registry path is the placeholder `TBD - locate console source`. Fix: rate a missing path `red` at the early return, and make the counter tolerant. Supervisor now exits 0 and DASHBOARD.md regenerated at 21:02.
- **Headroom Status badge was a permanent false alarm.** The ops action ran `headroom doctor` with no `--port`, so the doctor probed its built-in default 8787 while QI_Headroom actually listens on 9020 (`qi_registry` -> `headroom.ports.proxy`). It reported "proxy not reachable", exited non-zero, and pinned the card red while the proxy was healthy. Fix: point the doctor at 9020 and derive the exit code from the proxy - rc 0/1 pass (the "not routed" warnings are deliberate; Claude Code must not route through the proxy), rc >= 2 or a dead port fail.
- **Ops badges showed 2026-07-28.** `_ops_state` is loaded from `data/ops_history.json` once at startup and never reconciled; the 17:31 scheduled runs were recorded by the process that the 17:31 restart replaced, and the stale in-memory copy later overwrote the file. Cleared by re-running all five actions; all now rc 0 and dated today. `run_sequence` completed 5/5 OK.

### Built
- **`test_smoke.py` extended from 14 to 71 tests.** Parametrised GETs over all 25 nav routes plus /compliance, and 28 read-only API endpoints; required-parameter contracts for `/api/usage/range` and `/api/agent-hr/runs`; `/health` requested with a browser Accept header so the page is graded rather than its JSON probe; the warm-up fixture now primes the expensive pages. Tests tab reports 71 passed / 0 failed.
- **Per-project model-family split for the "w/ Local" column.** `usage_dimensions.savings_by_project()` applied one window-wide blended offload rate to every project, so an opus-only project and a haiku-heavy project were told the same story. Each project now gets the rate implied by its own measured family mix (the blend survives only where a project has no measured turns), and the table shows the mix inline: retirementanalyzer `opus 100% -> 0.0% offloadable`, mediastudio `opus 75% / fable 13% / sonnet 12% -> 5.0%`. `actual_usd` is untouched, so the ledger reconciliation invariant holds.

### Independent cross-check of the usage figures
`ccusage@20.0.20` over `C:\Users\renne\.claude\projects` for 2026-08-18..2026-09-16 reports **$4,492.02**; the Hive's `/api/usage/savings?days=30` reports **$4,557.48** - a **+1.46% gap**, inside the 5% tolerance. Two structural differences account for the per-day and per-model scatter:

1. **Date bucketing.** The Hive buckets by UTC, ccusage by local time. Proof: the Hive carries a 2026-09-17 bucket that cannot exist locally, and evening-heavy days shift whole to the next day (09-09 -$130 / 09-10 +$117).
2. **Cache-write tiering.** The Hive separates 5-minute (1.25x) from 1-hour (2.0x) cache writes; ccusage applies one cache-creation rate. Nearly all Fable 5.1 writes are 1-hour, so the Hive charges $20/M where ccusage charges $12.50/M - which is why the Hive's Fable 5.1 line is *higher* ($421.69 vs $333.60) despite its cheaper 0.025x cache-read rate.

Per model: opus-5 $3,868 vs $3,881 (-0.3%), fable-5 $171.60 on both, sonnet-5 $95.62 vs $102.29. `gpt-6-astra` ($2.88, Codex) appears only in ccusage - Trinity spend is tracked separately.

### Files Changed
- C:\APPS\CLAUDE\supervisor\supervisor.py (+ .bak-20260916)
- C:\QIH\engine\hive\dashboard\server.py (+ .bak-headroom-20260916)
- C:\QIH\engine\common\usage_dimensions.py (+ .bak-20260916)
- C:\QIH\engine\common\usage_stats.py (+ .bak-20260916)
- C:\QIH\engine\hive\dashboard\tests\test_smoke.py (+ .bak-20260916)
- REGENERATED C:\APPS\CLAUDE\DASHBOARD.md (first time since 2026-08-09)

### Open
- Owner mismatch list for section 5 of the remediation report not yet supplied; every "Now" item was verified independently and passes.
- Renaming 36 historical Agent HR rows to the `builtin:<type>` convention still needs the owner's go-ahead - not done.
- The Health Check page costs ~104 s on its first render after a restart (sc / netstat / git fan-out across 43 projects) and is then served warm from a 330 s cache. Designed behaviour, but the cold window has grown with the ecosystem.

---


## 2026-09-16 — Full Feature Audit: LLM Usage Root Cause + Cross-Cutting Health
**Session Focus:** Audit all 25 dashboard tabs, compliance, and cross-cutting systems; identify root cause of LLM Usage inflation; deliver remediation roadmap

### Audited
- 25 dashboard tabs: LLM Usage, Tests, War Room, Headlines, Tunnels, Compliance, Health, Ops, Guide, and 16 project status panels
- Compliance matrix, service registry, nightly backup pipeline, session logging, Brain Chroma index
- Found: 9 working · 14 degraded · 2 broken · 1 dead (War Room dormant since 2026-06-19)

### Found (root causes)
- **LLM Usage inflation 6.08×:** (1) usage_stats.py _iter_events counts per JSONL line; Claude Code writes 2–5 lines per message (one per content block) → 2–5× event inflation/day; (2) MODEL_PRICING table is 2 years stale (Opus $15/$75 → Opus 5 $5/$25, Fable $15/$75 → Fable 5.1 $10/$50, Sonnet $3/$15 → $2/$10, Haiku $0.80/$4 → $1/$5). Combined: 30-day window shows $28,528 → corrects to $4,690. QTD/YTD inflated end-to-end. 21% spend coded 'unknown' project.
- **QI_NightlyBackup fails:** targets deleted C:\UNIVERSAL paths; qi_brain.db has no backup anywhere (critical risk)
- **Compliance false-positive:** claudemd_exists check on .claude/CLAUDE.md always passes; nssm_registry lists 38 fails from orphan services in other projects (misattributed to qi_hive)
- **Health + Ops stale:** phantom projects (M2V, PersonalSong, Bakeoff) from health_check.py built at import; Ops badges from 2026-07-28 with rc=1
- **Tunnels hardcoded 13 ports, misses Kaze/MQ/Connector/Claude Voice**; Headlines '-5057s ago' UTC/local mismatch; Brain Chroma 186/2,636 sessions; 486 *.bak-* files

### Deliverable
- C:\QIH\shared\documentation\QIHive_Feature_Audit_2026-09-16.docx (+ .md twin) — 19 prioritised remediation items, ~45–60 h Opus 5 work in 4 phases

### Files
- NEW C:\QIH\shared\documentation\QIHive_Feature_Audit_2026-09-16.docx
- NEW C:\QIH\shared\documentation\QIHive_Feature_Audit_2026-09-16.md
- NEW C:\Users\renne\.claude\projects\C--QIH\memory\project_usage_tab_inflation_2026-09-16.md
- UPD C:\Users\renne\.claude\projects\C--QIH\memory\MEMORY.md (link to usage inflation analysis)
- NEW C:\QIH\shared\documentation\session_summaries\QI_Hive_Summary_2026-09-16_1650.docx

---
## 2026-09-16 — Full Remediation Execution: All 19 Audit Items Live-Verified
**Session Focus:** Owner-delegated full remediation of audit findings to Fable 5.1; all 19 prioritised items completed and verified end-to-end

### Executed
- **Usage pipeline dedup + pricing:** message.id deduplication in usage_stats.py; per-model pricing table (Fable 5.1 @ 0.025x cache-read); per-file incremental cache; registry-driven attribution; rescaled historical usage 2026-06-26→today (2.05× overall dedup factor). YTD $106k → $18.4k; 30d $28.5k → $4.5k. usage_ledger.py v2 with token-split columns; usage_recalibrate.py rescales old rows; server.py merges today live.
- **Backup repoint + health:** backup.py v2 targets C:\QIH\shared\backups\db\ (was targeting deleted C:\UNIVERSAL); 6 DBs backed up 17:11 with integrity checks + 'backup OK' marker; db_backup_now.py for ad-hoc; task registered QI_Scheduled_Tasks_Registry.md.
- **Compliance scope fix:** inspector claudemd_exists now accepts .claude/CLAUDE.md; nssm_registry correctly attributes 38 orphan services to owning project (was misbooked to qi_hive); Brain /api/compliance/status excludes inspector_verdict (now self_assessment); qi_hive shows 0 failures post-restart.
- **Brain Chroma index:** chroma_backfill.py indexed sessions 187 → 2,662; hive_ingest.py + poller.py embed on write; daily 03:15 schedule set.
- **Dashboard 14-tab refresh:** Headlines UTC-aware ages; Tests repointed pytest report; Tunnels from tunnels.json (Kaze/MQ/Connector visible); Ops badges/schedules seeded; Health force refresh; Logs app-log root + caps; Services legacy/unregistered badges (21 flagged); Mission Control roster/feed; Claude Voice banner; EasyFlow 'blocked' badge; Board updated_at + project norm; War Room/Dispatch → LABS; Activity 60 s refresh.
- **New tooling:** qi_restart_service.py dependency-safe NSSM restart (sc stop fails 1051 for QI_BrainAPI; inverse dependency tree from registry); Ops actions chroma_backfill + remove_legacy_services.
- **Hygiene:** health_check.py rebuilds on registry change; phantom M2V/PersonalSong/Bakeoff removed; 268 *.bak-* files → C:\QIH\_archive\bak_2026-09-16 (reversible); 3 legacy services (ClaudeManager, NayaTunnel, NEXUSTunnel) removed; project_readiness.json gaps filled.
- **Verification:** Single QI_Dashboard restart 17:31; all 26 routes GET 200; no tracebacks.

### Test Coverage
- 14 unit tests (test_usage_stats.py): 10 test + 4 smoke = 14 passing
- Smoke tests added per route; can extend to POST endpoints

### Files
- UPD engine/common/usage_stats.py (v2, dedup logic)
- UPD engine/common/usage_ledger.py (v2, token-split columns)
- NEW engine/common/usage_recalibrate.py (historical rescale)
- UPD engine/brain/tools/backup.py (v2, C:\QIH\shared\backups\db\)
- NEW engine/brain/tools/db_backup_now.py (ad-hoc backup)
- NEW engine/hive/tools/qi_restart_service.py (dep-safe restart)
- UPD engine/hive/dashboard/server.py (14 tabs)
- UPD engine/hive/dashboard/health_check.py (rebuild on registry change)
- UPD engine/hive/agents/agent_hr.py (normalise agent names)
- NEW engine/hive/dashboard/tests/test_usage_stats.py (14 tests)
- NEW engine/hive/tools/archive_bak_files.py (hygiene)
- UPD ecosystem/QI_Service_Registry.md (3 legacy removed, 48 total)
- UPD ecosystem/QI_Scheduled_Tasks_Registry.md (backup task)
- UPD data/project_readiness.json (gaps filled)
- UPD shared/documentation/QI_Claude_Manager_Guide.md (25 tabs)
- NEW session_summaries/QI_Hive_Summary_2026-09-16_1745.docx
- UPD .claude/projects/C--QIH/memory/MEMORY.md (links)
- NEW _archive/bak_2026-09-16/ (268 files, reversible)
- NEW _archive/legacy_services_2026-09-16.json (rollback record)

---
## 2026-09-08 — Trinity check: both assistants verified, obedience-tested, guarded
**Session Focus:** Verify the tri-platform arrangement (Claude + Codex/ChatGPT Plus + Gemini free tier) end-to-end; make it dependable; document for the §11a trial

### Built
- `C:\QIH\engine\tools\qi_trinity_check.py` — on-demand health check (13 checks: MCP wiring, Gemini key/config/quota/model visibility via ListModels, Codex CLI version vs npm latest, login, stale MCP processes, plan-visible models; `--ping` adds one cheap call per leg and records to Agent HR). Report → `C:\QIH\data\trinity\`, log → `C:\QIH\LOGS\trinity_check.log`. Never scheduled — nothing unattended calls an assistant.
- `C:\QIH\shared\documentation\plans\QI_Trinity_Model_Guide_2026-09-08.md` — per-model selection guide for both sides (Plus quota per model, Gemini free-tier data policy, decision procedure).
- WSL `~/.codex/config.toml` — pins `model = "gpt-5.6-terra"`, `sandbox_mode = "read-only"` so a call that forgets `model` no longer burns the gpt-6-astra window (5–45 msgs/5h) by default.
- Agent HR roster: `codex` and `gemini` onboarded as kind=assistant; 9 test runs recorded under project `trinity`.

### Fixed / found
- Codex MCP failed from Claude Code: CLI 0.118.0 cannot decode the current `/models` response (new `max` effort level), fell back to `gpt-5.3-codex`, refused for ChatGPT-plan logins. CLI upgraded to 0.153.4 (17:18 local, Windows-side `npm i -g`); a Claude Code restart is needed for this session's MCP process to pick it up.
- Stale-process detection: `readlink /proc/<pid>/exe` shows `(deleted)` on the native child, but `$(...)` inside an inline `wsl.exe bash -lc` string is mangled and reported 0 stale; probe moved to companion `qi_trinity_check_codex.sh` (emits JSON). Verified: 5 stale native processes flagged.

### Verified
- Fresh `codex mcp-server` 0.153.4 over JSON-RPC: initialize → tools/list → tools/call OK (6 s).
- Codex (gpt-5.6-luna): verifiable read-only task correct (def_count 18), "no commands" honoured (0 executions), read-only sandbox held when asked to write.
- Gemini (3.6-flash): strict JSON schema honoured; system instruction beat a conflicting user prompt.

### Files
- NEW `C:\QIH\engine\tools\qi_trinity_check.py`
- NEW `C:\QIH\shared\documentation\plans\QI_Trinity_Model_Guide_2026-09-08.md`
- NEW WSL `/home/hyosuke/.codex/config.toml`
- UPD `C:\QIH\shared\documentation\plans\QI_TriPlatform_AI_Orchestration_Plan_2026-09-08.md` (§14 check log)
- UPD `C:\QIH\engine\hive\agents\agent_hr.db` (roster + runs)

---
## 2026-04-19 — Full QI_ Service Rename Sweep + Brain + Backup
**Session Focus:** Rename all NSSM services to QI_ prefix; build Brain API; nightly backup

### Built
- QI Brain API (C:\UNIVERSAL\qi_brain\) — FastAPI on port 9010
  - Decision memory (SQLite + ChromaDB)
  - Feature propagation engine (qwen3:8b evaluates cross-project ideas)
  - Session logging
  - Semantic search (nomic-embed-text)
  - MCP tool (qi_brain_mcp.py)
- Nightly backup (backup.py + Task Scheduler at 1AM, 30-day retention)
  - Backs up all 5 QI databases using sqlite3.Connection.backup()
- Full rename sweep: 19 files updated across all projects to QI_ prefix
  - QI_MaiaBot, QI_MaiaTunnel, QI_MaiaDemoTunnel
  - QI_NayaBot, QI_NayaGradio
  - QI_NEXUS, QI_Dashboard, QI_DashboardTunnel, QI_BrainAPI

---

## 2026-04-19 — Training Docs + Ecosystem Health Tab
**Session Focus:** Training documentation; live health monitoring in Dashboard

### Built
- 3 professional training Word docs in C:\UNIVERSAL\TRAINING\ORCHESTRATOR\:
  - 01_QI_Orchestrator_Architecture.docx (41.5 KB)
  - 02_QI_Orchestrator_Operations.docx (40.6 KB)
  - 03_QI_Orchestrator_ProjectStatus.docx (41.6 KB)
- /api/ecosystem/health endpoint — live sc query all 9 QI_ services
- Ecosystem Health sub-tab in Project Status panel (Dashboard UI)
- qi-dashboard.json updated to v1.1.0 as "QI Orchestrator"

---

## 2026-04-19 — Session Intelligence + Python Path Centralization
**Session Focus:** Automatic project context loading; central Python config

### Built
- qi_session/ module: qi_context_loader.py + qi_new_project_wizard.py
- UserPromptSubmit hook (user_prompt_hook.py) — auto-loads project context
- session_context.py rewritten — global ecosystem briefing at session start
- qi_python_config.json — single source of truth for Python path
- qi_python.bat + qi_python.ps1 + qi_python.py — central Python bootstrap
- GET/PUT :9000/api/python_path — Dashboard API endpoint
- All NAYA installers + backup task updated to reference central config

### Files Changed
- C:\UNIVERSAL\qi_session\qi_context_loader.py (NEW)
- C:\UNIVERSAL\qi_session\qi_new_project_wizard.py (NEW)
- C:\UNIVERSAL\qi_python_config.json (NEW)
- C:\UNIVERSAL\qi_python.bat (NEW)
- C:\UNIVERSAL\qi_python.ps1 (NEW)
- C:\UNIVERSAL\qi_python.py (NEW)
- C:\Users\renne\.claude\session_context.py (REWRITTEN)
- C:\Users\renne\.claude\user_prompt_hook.py (NEW)
- C:\Users\renne\.claude\settings.json (UserPromptSubmit hook added)
- C:\UNIVERSAL\dashboard\qi_dashboard.py (+python_path endpoints)
- C:\APPS\NAYA\tools\*.ps1 (4 files — qi_python.ps1 dot-source)
- C:\UNIVERSAL\qi_brain\tools\install_backup_task.bat (qi_python.bat call)

---

## 2026-04-06 — Universal Control Panel + Ecosystem Reorganisation
**Session Focus:** QI Universal Control Panel; ecosystem moved to C:\UNIVERSAL\ECOSYSTEM

### Built
- QI Universal Control Panel bat (menu launcher, Windows Terminal tabs)
- Ecosystem folder moved from C:\APPS\QI\ECOSYSTEM → C:\UNIVERSAL\ECOSYSTEM
- All CLAUDE.md files updated across all projects
- MaiaNightlySync rescheduled to 9PM

---

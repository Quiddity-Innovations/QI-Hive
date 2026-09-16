# QI Hive — Full Feature Audit

_2026-09-16 · Assessment per feature, Dashboard → Guide · run as Claude Fable 5.1 · remediation assigned to Claude Opus 5_

## 1. Executive summary

Trigger: the LLM Usage tab was showing implausible numbers. The audit confirms it: every cost and turn figure on that tab is inflated about 6× (30-day window: $28,528 shown vs $4,690 corrected; 39,168 turns vs 19,428). Two independent defects multiply — the transcript parser counts every JSONL line instead of every message (×2–5), and the pricing table is Opus-4-era, three times today's Opus 5 price. The durable ledger and the Feb–Jul reconstruction were both calibrated on the same inflated parser, so QTD ($54,401) and YTD ($105,890) are wrong end-to-end.

Scope: all 25 navigation tabs plus the hidden Project Status page, the Compliance page, the usage pipeline (engine/common/usage_*.py), the task-health monitor and the nightly backup task. Method: read every route and its data sources, GET every page and API on http://127.0.0.1:8600, compare page output with the underlying files, SQLite tables, NSSM and Task Scheduler state, and log evidence. Nothing was modified, restarted, or POSTed. Four read-only hive-inspector agents (Sonnet) covered the 24 non-usage tabs; every headline claim they made was re-verified in the main thread before it entered this report.

Result: 9 tabs work as designed, 14 are degraded (they render, but show stale, incomplete or misleading data without saying so), 2 are broken (LLM Usage figures, Tests runner), 1 is dead (War Room). The recurring pattern is not crashes but silent staleness: cached state rendered with no age indicator, import-time snapshots never refreshed, checks that pass on file mtime alone. Two findings outside the dashboard are more serious than any tab: the nightly Brain database backup has been failing (exit 1) because it still targets the deleted C:\UNIVERSAL tree, and the Compliance page reports QI Hive itself as green while the live compliance log records 39 failing checks today.

Estimated remediation (Opus 5): roughly 45–60 engineering hours across four phases; the usage pipeline alone is 10–14 hours and should go first because every other consumer of usage_stats (Activity tab, Dashboard tiles) inherits the same numbers.

## 2. LLM Usage tab — root cause

### U1 — No message deduplication (critical, ×2–5)
- engine/common/usage_stats.py:270-300 `_iter_events` emits one event per JSONL line that carries `message.usage`. Claude Code writes one line per content block (text, thinking, tool_use) and every line repeats the same `message.id`, `requestId` and usage block. Verified in this session's own transcript: the first three usage lines are the identical message msg_011Cf7jyTjvoC9StiVAqkEhZ.
- Probe over the last 15 days: raw lines ÷ unique message ids = 2.1× to 5.2× per day (2026-09-07: 661 lines, 148 unique messages → 5.22×).
- Turns, tokens, cost, 'batchable turns', by-project and by-model all carry the per-day factor. Activity tab sessions inherit it unfiltered (a 10-minute inspector session showed 434 turns).
- Fix: deduplicate on message.id (ccusage uses message.id + requestId) before aggregation.

### U2 — Pricing table is Opus-4 era (critical, ×3 on Opus, ×1.5 on Fable)
- usage_stats.py:31-43 MODEL_PRICING: opus $15/$75, fable $15/$75, sonnet $3/$15, haiku $0.80/$4, keyed by family only.
- Live pricing (platform.claude.com/docs/en/about-claude/pricing, fetched 2026-09-16): Fable 5.1 $10/$50 with cache reads at 0.025×; Fable 5 $10/$50; Opus 5 / 4.8 / 4.7 / 4.6 $5/$25; Sonnet 5 $2/$10 (introductory price made permanent); Sonnet 4.6 $3/$15; Haiku 4.5 $1/$5. Cache write 1.25× (5m) / 2× (1h) unchanged.
- Family-level keys cannot express Sonnet 4.6 vs Sonnet 5, or Fable 5 vs 5.1 cache-read rates. Needs a per-model table with family fallback and a date-aware entry for models whose price changed.
- The page footer (server.py ≈7530) hardcodes the same wrong prices in prose.

### Combined effect measured today (30-day window)
- A. as shown (no dedup, legacy pricing): 39,168 turns, $28,527.92
- B. dedup only: 19,428 turns, $12,827.83
- C. dedup + current pricing: 19,428 turns, $4,689.58 → inflation factor 6.08×
- Opus 5 line alone: $23,843 shown vs $3,863 corrected. Fable share falls further once the 0.025× cache-read rate for Fable 5.1 is applied.

### U3 — Ledger stores cost, not a recomputable token split (high)
- usage_daily / usage_daily_model / usage_daily_project (qi_brain.db) store fresh tokens, cache_reads and cost_usd — not input / output / cache-write counts. A pricing fix cannot be applied by SQL; measured days must be re-snapshotted from transcripts. Transcripts on disk go back to 2026-06-26 and are no longer deleted (settings.json cleanupPeriodDays = 3650), so re-snapshotting is possible.
- Feb–Jul history ($33,064 'estimated' + $16,622 'anchored') was calibrated against the 2026-06-19 dashboard screenshot in usage_reconstruct.py ANCHOR — a screenshot produced by this same inflated parser at Opus 4.8 ×3 pricing. YTD $105,890 (53% measured) is therefore inflated end-to-end and needs an era-correction factor per model era, not just a re-snapshot.

### U4 — 'Today' and the window tiles disagree by design (medium)
- /api/usage/today is a live parse; 7d / 30d / QTD / YTD read the ledger. At 16:26 the ledger's max day was 2026-09-14 while today already had 50 turns, so every window tile silently excluded today; dashboard.log warned four times per page load ('usage ledger only covers through 2026-09-14'). The background refresh (throttled to 5 min) and QI_UsageSnapshot (every 30 min) do catch up — the ledger reached 2026-09-16 at 16:28 — so the symptom is a rolling 5–30 minute window in which the tiles understate.
- Fix: for windows whose end is today, take ledger rows for days < today and merge the live parse for today; or write today's row synchronously when missing.

### U5 — Project attribution: 21% of spend is 'unknown' (medium)
- 30-day: unknown = $6,461 / 9,017 turns, the second-largest 'project'.
- Top unmapped cwd values: C:\CLAUDE (subagent transcripts, 3,995 lines — the folder name 'subagents' defeats the alias fallback), Downloads\HINDU MYTHOLOGY…, D:\Dev\MediaStudio, Downloads\AUTOPDF, C:\Retirement Analyzer, C:\PlayDeck, C:\Gamez, C:\, C:\APPS\MilkWise (not registered), C:\NEXUS, C:\MapSnap, D:\Dev\FilmForge.
- Fix: resolve subagent files through their parent session folder; add legacy-root aliases (original_path) in the registry; register or map MilkWise.

### U6 — What-if savings model (low)
- 'Batch saves 50% of everything outside 00:00–06:00' and the local-offload fractions are heuristics on top of the inflated base; the $14,153 'Save' badge shrinks ~6× automatically once U1/U2 land. No separate fix, but the explainer text should say 'heuristic'.

### U7 — Monitoring cannot see a failing snapshot (medium)
- QI_TaskHealth watches QI_UsageSnapshot by log mtime. usage_snapshot_task._emit appends 'snapshot FAILED …' to the same log, so a failing snapshot still reads OK — the exact trap the task-health manifest documents. Fix: require today's 'snapshotted N day(s)' marker.
- Verified OK: QI_UsageSnapshot exists (every 30 min, rc 0, log fresh); SessionEnd hook also runs it (settings.json:92); dedup key is safe (unique message ids ≈ unique requestIds per day); transcript retention no longer deletes.

| Computation | Turns | Cost |
|---|---|---|
| A. As shown (no dedup, legacy pricing) | 39,168 | $28,527.92 |
| B. Dedup only | 19,428 | $12,827.83 |
| C. Dedup + current pricing | 19,428 | $4,689.58 |
| Inflation A ÷ C | 2.02× | 6.08× |

## 3. Assessment per feature

| Tab | Route | Verdict | Key findings | Effort (h) |
|---|---|---|---|---|
| Dashboard | / | ✅ working | 43 projects match the registry; sessions live. project_readiness.json is 38 days old (mtime 2026-08-09) so every progress bar is stale; usage tiles show ledger lag with no 'stale' badge. | 1 |
| Claude Voice | /voice | ⚠️ degraded | Honest 'Not listening' state, but cannot distinguish the deliberate 2026-08-20 power-down (auto-restore task 2026-09-19) from a crash; 'brief cached 935h ago' shown as a normal tile; Start button fights the scheduled restore. | 1 |
| Launcher | /launcher | ✅ working | 41 cards (43 minus 2 hidden by design), live port probes, Kaze card target answers 200. No dead paths. | 0 |
| Tunnels | /tunnels | ⚠️ degraded | KNOWN_TUNNELS (server.py:3159-3186) is a hand list of 13 ports; engine/tunnels/tunnels.json — its declared source of truth — has 15 named tunnels. Kaze (18800), MQ, Connector (9030) and Claude Voice tunnels can never appear, live or down. M2V (7841) is an orphan entry. | 1 |
| The Hive | /hive | ✅ working | Brain badge, 15 agent cards, recent sessions and poller status all live (poll every ~5 min, alive). AGENTS_DIR dead-path fix from the 2026-08-17 audit still holds. | 0 |
| Health Check | /health | ⚠️ degraded | health_check.py builds PROJECTS once at import (line 249). The dashboard process started 2026-09-09 23:02; the registry changed 2026-09-10 20:16 → M2V, PersonalSong, Bakeoff (retired, removed from registry) still render as 'Path not found'. Legacy C:\Claude\status.json in the CLI branch. | 1 |
| Task Board | /board | ✅ working | 411 cards, file written minutes before the check. No updated_at on column moves (12 'In Progress' cards date from April); project ids inconsistent (qi_hive / QI Hive / QI-Universal) so the filter splits one project into several. | 1 |
| Tests | /tests | ❌ broken | TESTS_RUNNER / TESTS_RESULTS (server.py:4876-4877) point at C:\Claude\Tests\…, which does not exist; every Run button 404s and 'Last run: Never' is permanent. The real suite (engine/hive/dashboard/tests/test_smoke.py, 4 checks) was never wired in. C:\QIH\tests is empty. | 2–3 |
| Project Status | /projects/status (hidden nav) | ✅ working | Answers 200 in 21 ms. Not deep-audited (hidden entry at server.py:1181). | 0 |
| Services | /services | ⚠️ degraded | 62 NSSM services listed flat (registry documents 48). Orphans shown with equal weight: ClaudeManager (stopped, unregistered, description claims port 8600 — the Hive's own port), NayaTunnel and NEXUSTunnel un-prefixed duplicates of QI_NayaTunnel / QI_NEXUSTunnel. 3.7 s page load. | 1 (+ Tier-2 nssm remove with owner OK) |
| Ops | /ops | ⚠️ degraded | All 8 action scripts exist, but 'last run' badges are from 2026-07-28 with no age styling; run_sequence's cached rc = 1 (failed) has stood 50 days; the cached supervisor output walks pre-migration paths (C:\NAYA, C:\OC, C:\MQ…). _ops_schedules is {} — the scheduler loop runs every 30 s with nothing scheduled, so nothing here runs unattended. | 3 |
| Scheduled Tasks | /tasks | ⚠️ degraded (reports accurately) | 46 rows, accurate. Surfaces a real failure nobody acted on: QI_NightlyBackup (engine/brain/tools/backup.py) exit 1 at 01:00 today — the script targets C:\UNIVERSAL\BACKUPS and C:\UNIVERSAL\qi_brain\qi_brain.db, deleted 2026-04-22. No qi_brain.db backup found. Task undocumented in QI_Scheduled_Tasks_Registry.md. | 1–2 (backup fix) + 0.5 (page) |
| LLM Usage | /usage | ❌ broken (numbers) | See deep dive: ×2–5 dedup defect × Opus-4 pricing = 6.08× overstatement; ledger and reconstruction inherit; window tiles lag today by 5–30 min; 21% 'unknown' project. | 10–14 |
| Effort Ledger | /effort | ✅ working | 121-entry chain intact, 2026-03-23 → 2026-09-15; one-day lag is the nightly collector by design. Defensive rendering on missing DB. | 0 |
| Headlines | /news | ⚠️ degraded | 58 of 200 rows render '-5057s ago': compliance rows are stamped UTC (18:00:04) while _relative_time (server.py:7791-7811) subtracts naive local now. Ordering across writers unreliable. The actual AI-news digest (/api/scout/digest, 277 items today) is orphaned — nothing calls it; the tab named 'Headlines' shows the internal activity stream. dashboard/index.html (2026-04-19) is a dead artefact linking localhost:8010. | 1–2 |
| Activity | /activity | ⚠️ degraded | Inherits the usage_stats inflation (confirmed 2.08× on a fresh transcript). Page load 9.8 s: cold-cache rglob over ~/.claude/projects runs inline on every stale request. /api/activity/sessions and /api/activity/hive_reports are unused by the page; no auto-refresh. Project id casing inconsistent (QI_Hive / qi_hive). | 2–3 |
| CoWork Dispatch | /dispatch | ⚠️ degraded | 2,899 dispatch rows, 99.7% hive_inspector compliance noise (filtered). Human queue: 9 rows, all test fixtures, newest 2026-08-17; no row has source='cowork' — the loop the page describes has never carried a real item. Executor last launched a job 2026-08-17; C:\QIH\cowork-dispatch untouched since 2026-04-20. /api/dispatch/log is an unused in-memory buffer. | 0.5 (retire) / product decision |
| QI Brain | /brain | ✅ working | Counts match SQL exactly (613 decisions, 638 features, 2,636 sessions); proxy to :9011 healthy (1.4 ms). Gap: Chroma index lags SQL — qi_sessions 186 vs 2,636 rows (7% searchable), decisions −19, features −15; /brain-search misses this silently. pending_reviews (44) not shown on the page. | 2–3 |
| Mission Control | /mission-control | ⚠️ degraded | Agent strip hardcodes 4 ids (server.py:8617-8622): claude and cowork last beat 2026-05-13 (126 days), claude_work never — rendered identically to the live claude_code card; no staleness logic; hive_* roster invisible; dispatch feed unfiltered compliance noise; mixed timestamp formats. | 1–2 |
| Agent HR | /agents | ✅ working | 16-agent roster live; Trinity hook confirmed writing project='trinity' rows (codex 18, gemini 13, newest 2026-09-10) but with duration_ms and tokens = NULL, zeroing cost columns. 409 of 520 runs (79%) are 'unknown_subagent' with NULL task/model. | 2 |
| War Room | /warroom | 🪦 dead | 11 messages, all 2026-06-18/19 (89 days). Responder thread starts on boot and NEXUS :8010 is healthy, so it would work — nobody uses it. Direct SQLite writes to qi_brain.db use WAL + 5 s busy timeout, same as Brain; contention risk low. | 0.5 (staleness note) / product decision |
| Logs | /logs | ⚠️ degraded | Global 500-file cap truncates a 2,614-file walk; only 5 of the dashboard's 410 rotated logs survive. The app-level log with the WARNING/ERROR lines (C:\QIH\logs\dashboard\dashboard.log) is not browsable — the tab's qi_hive root is the uvicorn access log in engine/hive/dashboard/LOGS. /api/log/dashboard.log returns 200 with empty content instead of 404. | 1–2 (+0.5 rotation) |
| Config | /config | ✅ working | Header lock, gsudo config/profiles, log levels, theme (penumbra), write-token verify all answer correctly. /api/easyflow/config is rendered on /tests, not /config, and advertises a blocked project without a badge. | 0.5 |
| Library | /library | ✅ working | 5,102 docs / 5,100 embedded / 9,179 edges from the Brain docs table (doc_harvester ran 02:35 today); 30 random paths all exist on disk; search for 'usage' and 'Trinity' returns correct ranked hits. link_collector.py, static/links.json (a June tunnel snapshot) and static/panel.html are dead files. _brain_db_query swallows all DB errors as []. | 0.5 |
| Guide | /guide | ⚠️ degraded | QI_Claude_Manager_Guide.md (mtime 2026-08-27) says '18 TABS'; nav has 25. Missing: Claude Voice, Tunnels, Ops, Effort Ledger, Mission Control, Agent HR, Library. No ghost tabs, no dead paths. | 2–3 |
| Compliance | /compliance | ⚠️ degraded (misleading) | QI_ComplianceFast runs every 4 h (rc trustworthy, not conhost-wrapped). /api/compliance/status returns a single month-old 'inspector_verdict: pass' (2026-08-17) for qi_hive, while compliance_log for the same run today records 39 fails: claudemd_exists (false positive — checks C:\QIH\CLAUDE.md, real file is .claude\CLAUDE.md) and 38 nssm_registry fails that belong to other projects' orphan services (AutoPDF, AvatarStudio, CogniBase, ComfyUI…) but are booked to qi_hive. | 3–4 |
| Cross-cutting | static / tests / hygiene | ⚠️ degraded | Vendor assets serve 200; 7 themes valid. Smoke test covers 4 endpoints only (root, /health, /api/brain/status, /openapi.json). 486 *.bak-* files under C:\QIH (6 copies of server.py beside the live file); 410 rotated dashboard logs uncapped. QI_TaskHealth service alive (27 tasks, 16:10 today) but QI_BrainDriftCheck_Daily is DEAD ('never reached overall=PASS') and QI_UsageSnapshot is checked by mtime only. | 2–3 |

Tally: 10 working · 14 degraded · 2 broken · 1 dead

## 4. Prioritised remediation

| # | Item | Why | What | Est. |
|---|---|---|---|---|
| 1 | LLM Usage: dedup + per-model pricing (usage_stats.py) | Every cost/turn figure on Usage, Activity and the Dashboard tiles is ~6× too high. | Dedup events on message.id (fallback requestId) in _iter_events; replace MODEL_PRICING with a per-model table (Fable 5.1 cache read 0.025×) + family fallback; fix the footer prose; add a unit test with a 3-line fixture that must count once. | 3–4 h |
| 2 | LLM Usage: re-snapshot the ledger and correct the reconstruction | QTD/YTD and every by-model/by-project table are stored values computed by the old parser. | Add input/output/cache-write columns to usage_daily* (additive migration, backup first); re-run snapshot over all surviving transcripts (2026-06-26 →); derive per-era correction factors (dedup ratio × price ratio) and re-run usage_reconstruct/usage_dimensions for Feb–Jun; publish before/after totals in the log. | 4–6 h |
| 3 | QI_NightlyBackup: repoint backup.py off C:\UNIVERSAL and verify a restore | The Brain DB (613 decisions, 2,636 sessions) has had no working nightly backup since C:\UNIVERSAL was deleted; exit 1 every night. | BACKUP_ROOT → C:\QIH\shared\backups\db\YYYY-MM-DD; targets → C:\QIH\data\qi_brain.db (+ drop filehq); use sqlite backup API; register the task in QI_Scheduled_Tasks_Registry.md and add it to task_health_manifest with a today-file check; do one restore test. | 1–2 h |
| 4 | Compliance: stale qi_hive verdict + nssm_registry misattribution + CLAUDE.md dotfolder | The compliance page says the Hive is green while its own log says 39 fails; the tool grades itself wrong. | Brain-side: make /api/compliance/status read the latest run for qi_hive like every other project; resolve each orphan NSSM service to its owning project (or an 'ecosystem' bucket) before logging; accept .claude/CLAUDE.md. | 3–4 h |
| 5 | LLM Usage: merge today's live parse into windows ending today; task-health marker for the snapshot | Tiles understate for up to 30 min after each session and the monitor cannot see a failing snapshot. | usage_range/usage_daily/usage_totals_since: ledger for < today + live for today; task_health_manifest: require today's 'snapshotted' marker. | 1–2 h |
| 6 | Ops tab: age-aware badges, clear the 50-day-old FAIL, schedule the read-only actions | Green/red badges from July are presented as current; nothing runs unattended. | Render age (>24 h amber, >7 d red); default schedules for supervisor / snapshots / self_audit / headroom_status; re-run supervisor so its cached output reflects C:\APPS paths. | 3 h |
| 7 | Tests tab: wire the real pytest suite | Buttons 404 forever; the page has never run a test. | Repoint TESTS_RUNNER/TESTS_RESULTS to engine/hive/dashboard/tests via pytest --json-report; confirm render_tests' expected JSON shape; extend the smoke suite to every nav route (25 GETs) so a passing run means something. | 2–3 h (+2 h coverage) |
| 8 | Health tab: rebuild PROJECTS per refresh, not per import | Retired projects show as 'missing' until the service is restarted. | Rebuild inside run_health_check (or on registry mtime change); fix the dead C:\Claude\status.json CLI path. | 1 h |
| 9 | Activity tab: shared dedup fix + incremental parse + refresh | 9.8 s page, inflated turns, dead endpoints. | Cache parsed events per file keyed by (path, mtime, size); wire the existing /api/activity/* endpoints with a setInterval; normalise project ids. | 2–3 h |
| 10 | Headlines: UTC/local normalisation and the orphaned scout digest | Negative 'ago' labels and mis-sorted feed; the tab does not show headlines. | Parse timestamps timezone-aware in _relative_time and sort on UTC; either add a 'AI digest' card fed by /api/scout/digest or rename the tab 'Activity feed'; delete dashboard/index.html. | 1–2 h |
| 11 | Tunnels: derive the list from tunnels.json | Four live products are invisible to the page. | Iterate every ingress port in tunnels.json, union with the log-fallback extras, drop the M2V orphan. | 1 h |
| 12 | Logs tab: expose the app log and stop silent empties | The one log that carries the dashboard's warnings cannot be opened from the Logs tab. | Add C:\QIH\logs\dashboard as a browsable root (or repoint the registry's qi_hive logs path); 404 on missing file in /api/log/{filename}; cap rotated files (keep 14 days). | 1–2 h |
| 13 | Services: mark and remove legacy orphans | ClaudeManager, NayaTunnel, NEXUSTunnel confuse the count (62 vs 48 registered). | Badge un-prefixed / unregistered services as legacy; nssm remove the three after owner confirmation (Tier 2); reconcile QI_Service_Registry.md. | 1 h |
| 14 | Brain search coverage: catch the Chroma index up | 93% of sessions and the newest decisions are not semantically searchable. | Find why the embed job trails (2,450 sessions behind); backfill; show 'indexed N of M' on /brain-search. | 2–3 h |
| 15 | Mission Control staleness + roster | 126-day-old agents look alive. | Age-based badge; read the hive_* roster from Agent HR; filter compliance noise from the dispatch feed; one timestamp format. | 1–2 h |
| 16 | Agent HR data quality | 79% of runs unattributed; Trinity cost columns zero. | Populate duration_ms/tokens in log-trinity-run.py; map unknown_subagent by cwd/project the way usage_stats does. | 2 h |
| 17 | Guide: add the 7 missing tab sections | Onboarding doc covers 18 of 25 tabs. | Write Claude Voice, Tunnels, Ops, Effort Ledger, Mission Control, Agent HR, Library in the existing style; bump header to 25. | 2–3 h |
| 18 | Dashboard readiness + Board hygiene + Voice outage banner + Config badge | Small honesty fixes. | Schedule project_readiness regeneration and badge stale; updated_at on board moves + project id normalisation; planned-outage banner on /voice; 'blocked' badge on the EasyFlow card. | 3 h |
| 19 | Hygiene: dead files, .bak clutter, retired features | 486 *.bak-* files, dead link_collector/links.json/panel.html/index.html, unused /api/dispatch/log, War Room and CoWork Dispatch with no real traffic. | Produce an enumerated deletion list for owner approval (Tier 1 rule); retire or staleness-badge War Room and Dispatch per owner decision; revive QI_BrainDriftCheck_Daily so it reaches overall=PASS. | 1–2 h + owner decision |

## 5. Phased plan

- **Phase 1 — Trust the numbers (items 1, 2, 5) — 10–14 h.** Acceptance: Ship first; every other usage consumer inherits it. Acceptance: 30d tile within 2% of an independent ccusage run; today tile == last row of the 30d series; ledger measured_pct unchanged; before/after totals logged.
- **Phase 2 — Stop lying quietly (items 3, 4, 6, 7, 8) — 10–14 h.** Acceptance: Backup restore test passes; compliance page for qi_hive equals the latest run; Ops badges carry ages; Tests page shows a real run; Health tab has no phantom projects.
- **Phase 3 — Accuracy of the remaining tabs (items 9–16) — 12–17 h.** Acceptance: No negative 'ago'; Tunnels lists Kaze/MQ/Connector; Logs opens the app log; Services badges legacy; Brain search reports coverage.
- **Phase 4 — Docs and hygiene (items 17–19) — 6–8 h.** Acceptance: Guide lists 25 tabs; deletion list approved and executed; smoke suite covers every route.

## 6. Verified OK

- Dashboard process, Brain API (:9011), NEXUS (:8010), Caddy hive.qi.local all answer; dashboard listens on 8600 (port 9010 belongs to another service and answers HTTP 426).
- QI_UsageSnapshot task exists and runs every 30 min (rc 0); SessionEnd hook also snapshots; QI_TaskHealth NSSM service alive with 27 monitored tasks (16:10 today).
- Registry ↔ /api/status ↔ Launcher counts agree (43 / 43 / 41 + 2 hidden). No C:\UNIVERSAL, C:\Claude\Dashboard, LINE BOTS or D:\Dev literals in server.py (the only hits are the Tests constants, health_check.py's CLI branch and backup.py).
- Library index healthy (0/30 sampled paths missing); Effort ledger chain intact; Agent HR Trinity hook producing rows; Board file actively written.

## 7. Method

- Assessment model: Claude Fable 5.1 (main thread, all root-cause work on the usage pipeline, all verification). Inspector agents: 4 × hive-inspector (Sonnet 5), read-only, one per tab group; their top claims (dead Tests path, negative 'ago' labels, compliance mismatch, phantom projects, NightlyBackup rc 1) were re-verified in the main thread before inclusion.
- Nothing was changed: no file edits, no service restarts, no POST/PATCH/DELETE, no test runner invoked from the dashboard. One inspector executed the local pytest smoke file (GET-only, 4/4 pass).
- Evidence artefacts: scratchpad probes dedup_probe.py and corrected_probe.py (session temp), dashboard.log warnings 16:23–16:28, task_health.json 16:10, compliance_log run 2026-09-16 18:00:04 UTC.
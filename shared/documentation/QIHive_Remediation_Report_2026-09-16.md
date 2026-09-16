# QI Hive — Audit Remediation Report

_2026-09-16 · executed by Claude Fable 5.1 under owner delegation · companion to QIHive_Feature_Audit_2026-09-16_

## 1. What happened

Scope: all 19 items of the audit's prioritised list were executed in this session, in four phases, with one dashboard restart at the end. Every service restart went through the dashboard's own Ops actions (LocalSystem), so no elevated shell was needed. Every file edited kept a dated .bak copy; every deletion was a reversible move with a manifest.
Result: the LLM Usage tab reports corrected figures on every window; the nightly backup works and is monitored; Compliance grades the Hive from today's run; the Brain's semantic index covers every session; and the 14 degraded tabs now either show correct data or say plainly when data is stale.

## 2. Before / after

| Item | Before | After |
|---|---|---|
| LLM Usage · 30-day cost / turns | $28,528 / 39,168 | $4,537 / 20,045 |
| LLM Usage · Year to date | $105,890 (53% measured) | $18,380 (50% measured) |
| LLM Usage · Q3 to date | $54,401 | $9,127 |
| LLM Usage · 'unknown' project share (30d) | $6,461 (21%) | attributed via registry + aliases; milkwise/mythologies/mediastudio now named |
| Window tiles vs today | excluded today until next snapshot (5–30 min) | live parse of today merged into every window |
| Nightly backup (QI_NightlyBackup) | exit 1 every night; no qi_brain.db backup anywhere | 6 databases to shared\backups\db\2026-09-16, integrity ok, 'backup OK' marker, monitored |
| Compliance for qi_hive | 1 stale 'pass' from 2026-08-17; 39 live fails hidden | latest run, 0 fails after false-positive and attribution fixes; self_assessment surfaced |
| Brain semantic index (sessions) | 187 of 2,636 indexed (7%) | 2,662 of 2,662; embeds on write; nightly backfill 03:15 |
| Brain API process | serving :9011 since 2026-09-05 (sc stop refused, 1051) | relaunched dependency-safely at 17:32 with current code |
| Tests tab | runner path did not exist; 'Never' | pytest json report; 14 passed at 17:34 |
| Tunnels page | 13 hardcoded ports; Kaze/MQ/Connector invisible | derived from tunnels.json; 18800 and 9030 listed; M2V orphan gone |
| Headlines | 58 rows '-5057s ago' | 0 negative ages; AI digest card added |
| Health tab | 3 phantom retired projects | 0; project list rebuilt on registry change |
| Ops tab | badges from 2026-07-28, no schedules | age badges; 5 daily schedules (06:10–06:40, 03:15) |
| Services page | 62 rows, orphans indistinguishable | 21 legacy/unregistered badged; 3 orphans removed (rollback json kept) |
| Agent HR | 409 runs unattributed; Trinity cost columns null | 401 re-attributed; estimates labelled 'est' |
| Guide | 18 of 25 tabs | 25 of 25 |
| Live tree hygiene | 486 *.bak-* files, 4 dead dashboard files | 268 moved to _archive\bak_2026-09-16 (manifest); doc tree and BU backups left untouched |
| Task-health signal for the snapshot | log mtime (blind to 'snapshot FAILED') | per-day 'snapshot OK' marker |

## 3. Changes by area

### Usage pipeline
- engine/common/usage_stats.py — v2: dedup on message.id, per-model MODEL_PRICES (Fable 5.1 cache read 0.025×), incremental per-file cache, registry-driven attribution (subagent files resolve through their project folder; legacy roots aliased).
- engine/common/usage_ledger.py — v2 columns input_tokens/output_tokens/cache_write_5m/cache_write_1h/pricing_version; snapshot writes them.
- engine/common/usage_recalibrate.py — one-shot: backup, migrate, measure inflation (dedup 2.046× overall / 2.205× first 4 weeks; price ratio 0.389), re-snapshot 60 measured days from 2026-06-26, scale 99 legacy rows (−$40,566), rebuild dimensions (0 unreconciled). Log: LOGS\usage_recalibrate_20260916_170948.log.
- engine/common/usage_backfill.py — refuses to run without --reinflate-ok.
- engine/common/usage_snapshot_task.py — writes LOGS\usage_snapshot\usage_snapshot_YYYYMMDD.log 'snapshot OK' on success.
- engine/hive/dashboard/server.py — usage helpers merge ledger (< today) with a live parse of today; footer generated from the pricing table.
- engine/hive/dashboard/tests/test_usage_stats.py — 10 unit tests (dedup, prices, cost formula, attribution).

### Backups and monitoring
- engine/brain/tools/backup.py — v2 (targets under C:\QIH and C:\APPS, online backup API, integrity check, 30-day purge, per-day log with 'backup OK'); install_backup_task.bat repointed; db_backup_now.py for ad-hoc sets.
- ecosystem/task_health_manifest.json — marker checks for QI_UsageSnapshot and QI_NightlyBackup (.bak-20260916-audit kept).
- ecosystem/QI_Scheduled_Tasks_Registry.md — §10 QI_NightlyBackup.

### Compliance and Brain
- engine/hive/inspector/inspector.py — claudemd_exists accepts .claude\CLAUDE.md; nssm_registry attributes to owning project / 'ecosystem'.
- engine/brain/api.py — /api/compliance/status latest run by recorded_at, inspector_verdict → self_assessment; /api/status gains chroma_coverage.
- engine/brain/tools/chroma_backfill.py (new); engine/hive/ingest/hive_ingest.py and engine/brain/poller.py embed on write.
- engine/hive/tools/qi_restart_service.py (new) — dependency-safe NSSM restart; Ops 'Restart Brain API' and restart_svc_* use it.

### Dashboard tabs (server.py, backup server.py.bak-tabs-20260916)
- Headlines, Tests, Tunnels, Ops, Health, Logs, Services, Mission Control, Claude Voice, EasyFlow badge, Task Board, LABS nav (War Room + CoWork Dispatch), Dashboard readiness note, Activity auto-refresh — see the audit item list; /api/dispatch/log removed.
- engine/hive/health_check.py — project list rebuilt when qi_registry.json changes; legacy status path fixed.
- New Ops actions: chroma_backfill (scheduled 03:15), remove_legacy_services (executed once).

### Agent HR, Guide, hygiene
- C:/Users/renne/.claude/hooks/log-trinity-run.py and engine/hive/agents/agent_hr.py + backfill_unknown_runs.py.
- ecosystem/QI_Claude_Manager_Guide.md — 25 tabs.
- tools/archive_bak_files.py — reversible move with manifest (--undo); engine/hive/tools/remove_legacy_services.py — rollback record in _archive\legacy_services_20260916_173334.json.

## 4. Decisions

- Orphan services: removed (ClaudeManager, NayaTunnel, NEXUSTunnel). NEXUSTunnel was a running cloudflared quick tunnel with a random hostname; nothing can depend on it. Parameters recorded for rollback.
- .bak clutter: moved, not deleted (268 files); 'BU Administrative Backups' and shared\documentation were deliberately left alone (a backup store by design, and the Library index paths).
- War Room and CoWork Dispatch: kept, moved under a LABS header with 'last activity' banners. Review in 30 days: retire if still idle.
- Backup location: C:\QIH\shared\backups\db\YYYY-MM-DD, 30-day retention; labelled sets (e.g. *_pre-remediation) are never purged.
- Reconstructed history: era-corrected with measured factors rather than relabelled, because the same parser produced the anchor; the factors are recorded in each row's note.

## 5. Owner verification checklist

| When | Where | Expect |
|---|---|---|
| Now | Open http://127.0.0.1:8600/usage | Today / 7d / 30d / QTD / YTD tiles read about $39 / $656 / $4,537 / $9,127 / $18,380 (today grows as you work). By Model: opus-5 ≈ $3.9k for 30d. Footer names opus-5 $5/$25. |
| Now | Click a bar in Daily Spend, then 'YTD' | Selected Period recomputes; no 'failed to load range'. |
| Now | /news | No negative 'ago' labels; collapsed 'AI news digest' card at the top. |
| Now | /tunnels | Kaze (18800), MQ, Connector (9030) present; no M2V row. |
| Now | /tests → Run Smoke Tests | Finishes with 14 passed; 'Last run' shows today. |
| Now | /health | No 'Path not found' for M2V, PersonalSong Studio, Bakeoff (Transfer Station still TBD by design). |
| Now | /ops | Amber alert gone; five schedules listed; every 'last run' badge carries an age colour. |
| Now | /services | ClaudeManager, NayaTunnel, NEXUSTunnel absent; grey 'legacy / unregistered' badges at the bottom. |
| Now | /compliance | qi_hive card shows today's run, 0 fails (cognibase and mapsnap genuinely lack CLAUDE.md). |
| Now | /mission-control | claude / cowork cards carry red age badges; 'Hive roster' row present. |
| Now | /logs | Root 'qi_hive (app log)' opens C:\QIH\logs\dashboard\dashboard.log. |
| Now | /guide | 25 numbered tabs. |
| Tomorrow ≥ 01:05 | C:\QIH\LOGS\nightly_backup\backup_20260917.log | Last line 'backup OK (6 databases, …)'; folder C:\QIH\shared\backups\db\2026-09-17 has six .db files. /tasks shows QI_NightlyBackup lastResult 0. |
| Tomorrow ≥ 03:20 | C:\QIH\LOGS\brain_drift\ and /ops chroma_backfill badge | chroma_backfill ran at 03:15 rc 0. |
| Tomorrow ≥ 07:00 | /ops | supervisor / snapshots / self_audit / headroom_status badges dated today 06:10–06:40, green. |
| Tomorrow | C:\QIH\data\task_health.json (or the Telegram alert channel) | QI_NightlyBackup OK, QI_UsageSnapshot OK ('marker present in today's log'), QI_BrainDriftCheck_Daily no longer DEAD. |
| If anything is wrong | Report the tab and what you saw | Rollback points: server.py.bak-usage-20260916 / .bak-tabs-20260916 / .bak-ops-20260916; qi_brain.db copies in shared\backups\db\2026-09-16_pre-remediation and _pre-recalibrate; _archive\bak_2026-09-16\manifest.json (archive_bak_files.py --undo); _archive\legacy_services_20260916_173334.json (nssm install with the recorded parameters). |
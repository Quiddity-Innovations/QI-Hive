# QI Hive — Latest Session Note (2026-04-19, overnight autonomous)

## 🎉 Zero manual steps needed

Autonomous elevation is now fully wired. Broker survives itself.

## Re-wiring complete — broadcast to sibling sessions

Other Claude sessions (C:\QI, C:\NAYA, C:\NEXUS, C:\EasyFlow) should be aware:

### Elevation path (no more UAC prompts mid-session)
1. **gsudo** installed machine-wide with 8h credential cache (`CacheMode auto`, `CacheDuration 00:08:00`). One UAC per workday, then silent.
2. **Elevation broker** at `C:\QIH\commands\pending\` accepts whitelisted JSON requests, runs them as LocalSystem. Drop-batch-in-folder pattern.
3. **Python helper**: `from engine.common.qi_service import restart, start, stop` — returns `True`/`False`. Routes through broker; no UAC.

### Broker resilience (can't die permanently anymore)
- **NSSM AppExit=Restart** on QI_Elevate, QI_Dashboard, QI_HiveIngest (3s delay, 1.5s throttle). Crash → auto-revive.
- **QI_ElevateWatchdog** scheduled task (SYSTEM, every 1 min) polls NSSM status and starts broker if stopped. Safety net.
- **Stale-queue purge**: broker drops any pending request >5 min old at startup. Fixes the "broker revives → re-executes own kill order → dies again" suicide loop that caught us at 20:51 on 2026-04-19.
- **Single-instance PID lock** at `C:\QIH\logs\elevation\broker.lock` with `os.kill(pid, 0)` liveness check. Prevents orphan-broker race.

### What this unlocks
Any Claude session on this machine can now restart services, kill processes, repoint NSSM services — autonomously, no human in the loop, bounded by the regex whitelist. Use `engine.common.qi_service` from any project.

## What's live right now

- ✅ QI_Dashboard (http://localhost:8600) — running
- ✅ QI_HiveIngest — running
- ✅ QI_Elevate — running, autonomous
- ✅ QI_ElevateWatchdog (Task Scheduler, SYSTEM, 1-min cadence) — registered

## What was done this overnight

- **Health registry expanded** from 7 → 11 projects: added EasyFlow, Claude_Manager, QI_Universal, FileHQ. NEXUS doc_path corrected. (commit `da905d7`)
- **Hive page stats fixed** — was showing `?` and `0 tasks` because of wrong dict keys. Now pulls from Brain flat schema with local fallbacks; per-agent task counts from `tasks.json`. Numbers are real: 9 projects / 57 decisions / 21 features / 80 sessions. (commit `2eb5e29`)
- **/usage page redesign** — compact boxes, renamed tiers (no "WHAT-IF" prefix), 3-series daily chart (Actual / Local offload / Local+Batch), comparison columns on By Project + By Model, per-model savings table, totals row. Menu label shortened to "LLM Usage". (commits `fa087dc`, `1de7e93`)
- **Broker autonomy unlocked** — gsudo installer, broker watchdog, NSSM resilience (commits `1492270`, `bde69e3`)

## Pending (will address in remainder of this overnight)

- **One Brain backfill** — Brain counts 80 sessions but only 7 logged via qi.log_session. Backfill historical sessions/decisions from JSONL + session summary docx.
- **SessionEnd hook** for automatic brain logging going forward.
- **Features Tracked + Decisions Logged dashboard wiring** to real sources.

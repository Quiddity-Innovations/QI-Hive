# QI Hive — Latest Session Note (2026-04-19, evening)

## ⚠️ One manual step needed when you return

**QI_Elevate service is currently STOPPED.**

During autonomous work I added a single-instance lock to the broker (`qi_elevate.py`) to prevent the orphan-broker race we fixed earlier. To apply it I tried to restart the broker through itself — that's circular (the broker IS what does the restart), so the restart hung and the service ended up stopped.

I can't start it from an unelevated shell (`sc start QI_Elevate` → Access denied).

**Please run once (elevated):**
```
nssm start QI_Elevate
```
That applies the new lock and restores autonomous service control. Dashboard + HiveIngest are unaffected and still running.

## What's live right now

- ✅ QI_Dashboard (http://localhost:8600) — running
- ✅ QI_HiveIngest — running
- ❌ QI_Elevate — stopped (see above)

## What was done this session

- **/services, /tasks, /usage, /activity** panels all live on the dashboard
- **Project status colors fixed**: Maia/OpenClaw red Backlog, FileHQ gray Retired, MQ light-green New, EasyFlow/QI_Hive/NEXUS orange In Progress
- **Status legend** added at bottom of left sidebar
- **Claude usage tracking** built from `~/.claude/projects/**/*.jsonl`:
  - Today / 30d / by-project / by-model
  - What-if savings tier: local LLM offload + batch API scheduling + savings-by-model, with totals
  - Auto-updates on every refresh (30s cache)
- **Attribution fixes**: Gmail_Beyond, QI_Universal, C:\Users\* paths now map correctly (no more "Users" or "GMAIL" bogus projects)
- **Autonomous service control** via `sc.exe` through the broker (nssm's OpenService mask fails as LocalSystem; sc works) — see `engine/common/qi_service.py`
- **Orphan-broker race** diagnosed + killed; single-instance lock added to prevent recurrence
- **FileHQ path** corrected in status.json: `C:\NAYA\filehq` (retired, merged into Naya 2026-Q1)
- Committed `c98ce9a` "feat: dashboard observability panels + autonomous service control" and pushed to origin/master

## Pending (for next session)

- Confirm broker restart activates the single-instance lock (check `C:\QIH\logs\elevation\broker.lock` contains current PID)
- Consider adding broker auto-recovery to a watchdog (so we never hit the circular-restart dead end again)
- Richer `/activity` data: add `agent`/`model`/`role` fields to `hive_report.report()`

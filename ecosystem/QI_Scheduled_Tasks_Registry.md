# QI Ecosystem — Scheduled Tasks Registry & Window Policy

**Authority:** This file is the single source of truth for all QI/OC/Maia **Windows Scheduled Tasks** (the sibling of `QI_Service_Registry.md`, which covers NSSM *services*).
**Location:** `C:\QIH\ecosystem\QI_Scheduled_Tasks_Registry.md`
**Last updated:** 2026-08-27 (**health audit + same-day remediation** — 8 of 9 items fixed, QI_TaskHealth monitor added, see §9; **health audit** — 7 tasks found silently DEAD, §3 log-timestamp advice corrected as unsafe; see §8 and `C:\QIH\shared\documentation\QI_Task_Health_Audit_2026-08-27.md`)

> **If a scheduled task pops a command window, or you need to disable/enable one, START HERE.**

---

## 1. The problem this solves

A Windows scheduled task **flashes a console window** on your desktop when ALL three are true:

1. It runs as the interactive user (`renne`, LogonType = Interactive), **and**
2. It launches a console program — `python.exe`, `wsl.exe`, a `.bat`/`.cmd`, or `powershell.exe`, **and**
3. The program isn't suppressed (no headless host, no windowless interpreter).

Tasks that run as **SYSTEM** (LogonType = ServiceAccount) execute in session 0 and are never visible. Tasks using `pythonw.exe` have no console at all.

The worst offender was **`QI_BrainBackfill`** — a `python.exe` window popping **every 30 minutes**, all day.

---

## 2. How it's controlled (one config + one tool)

| Item | Path |
|---|---|
| **Policy config** (single source of truth) | `C:\QIH\ecosystem\scheduled_tasks_window_policy.json` |
| **Manager tool** | `C:\QIH\tools\qi_task_window_manager.py` |

### The config
Each task has two settings:

```json
"QI_BrainBackfill": { "enabled": true, "window_mode": "hidden_user", "note": "..." }
```

- **`enabled`** — `true` → `Enable-ScheduledTask`; `false` → `Disable-ScheduledTask`.
- **`window_mode`**:
  - **`hidden_user`** (default) — task still runs as **you** with your full profile (git creds, WSL session, venvs), but the window is suppressed by wrapping the action in **`conhost.exe --headless <cmd>`** (Windows 11 headless console host). **No admin needed.**
  - **`system`** — re-home the task to **SYSTEM/ServiceAccount** (session 0, invisible). Loses the user profile, so only safe for self-contained scripts. **Needs admin to change.**
  - **`visible`** — unwrap and restore a normal interactive run (for debugging).

### The tool — usage
```bash
# Dry-run: show the plan, change nothing (default)
python C:\QIH\tools\qi_task_window_manager.py

# Apply the whole policy
python C:\QIH\tools\qi_task_window_manager.py --apply

# Show the live state of every managed task
python C:\QIH\tools\qi_task_window_manager.py --verify

# Limit to specific tasks (comma-separated)
python C:\QIH\tools\qi_task_window_manager.py --apply --only QI_BrainBackfill,QI_TubeScout_AM

# Override the mode for one run (e.g. temporarily make one visible)
python C:\QIH\tools\qi_task_window_manager.py --apply --mode visible --only QI_BrainBackfill
```
It is **idempotent** — edit the JSON, re-run `--apply`, done.

### Common operations
| You want to... | Do this |
|---|---|
| Stop a task popping a window | It already should be `hidden_user`; if not, set it and `--apply` |
| Turn a task off | Set `"enabled": false` → `--apply` |
| Turn a task back on | Set `"enabled": true` → `--apply` |
| See a task's window again (debug) | `--apply --mode visible --only <task>` |
| Run a task invisibly as SYSTEM | Set `"window_mode": "system"` → `--apply` **from an elevated shell** |
| Check current state | `--verify` |

---

## 3. Gotchas (learned 2026-06-18 — don't repeat these)

- ❌ **Do not swap `python.exe` → `pythonw.exe`.** `pythonw` sets `sys.stdout = None`, so any script that prints/logs to stdout crashes (exit 1). Also venvs often lack `pythonw.exe` (e.g. `C:\APPS\QI\.venv\Scripts\` has none). Use `conhost --headless python.exe` instead — real binary, valid stdout, no window.
- 🔴 **`conhost --headless` does not propagate the child exit code.** Task Scheduler will always show `LastTaskResult = 0`, even on failure — **even when the target binary does not exist at all** (re-verified 2026-08-27: `conhost --headless C:\NOPE\nothere.exe` → `0`). `LastTaskResult` is meaningless for all 24 conhost-wrapped tasks. `pythonw.exe` is **not** affected and does propagate exit codes correctly.
- 🔴 **~~Verify a run by checking the log timestamp.~~ THIS ADVICE WAS WRONG — corrected 2026-08-27.** A wrapper log's mtime proves only that *something* appended, not that the job succeeded. Because the action redirects with `>> log 2>&1`, the shell's own **failure** messages land in the same log and keep it looking fresh. Measured during the 18-day OC outage: Kaze's wrapper log froze (an mtime check would have caught it) but **Yubin's grew every single day with 35 consecutive `No such file or directory` lines while completely dead** (an mtime check would have passed it). **Verify a run by checking for a task-specific SUCCESS MARKER or an advancing output artifact — never by mtime, never by exit code.** See `C:\QIH\shared\documentation\QI_Task_Health_Audit_2026-08-27.md` §1 and the reference implementation `check_digest_freshness()` in `C:\APPS\OC\tools\oc-keepalive-daemon.py`.
- ⚠️ **A task that never worked still reports healthy.** Two tasks in this estate (`OC-Sentry-Drift-Sunday-8PM`, `OC-Kakei-Weekly-Sunday-7PM`) have **never** produced real output since creation — one guards on a directory that has never existed, the other prints `✅ sent` without checking curl's response. No regression is needed to be dead. New tasks must ship a freshness check as part of "done".
- ⚠️ **`RunLevel = Highest` tasks need admin even to enable/modify.** Apply those from an **elevated** PowerShell/Terminal. The `QI_Elevate` broker only whitelists `nssm`/`sc`/`taskkill` (not PowerShell), so this step cannot currently be brokered.

---

## 4. Full task catalog (as of 2026-06-18)

All `hidden_user` tasks below are now windowless. `*` = required a one-time elevated apply (RunLevel Highest).

| Task | Schedule | Runs | Mode | Status |
|---|---|---|---|---|
| **QI_BrainBackfill** | every 30 min | `brain_backfill_tick.py` | hidden_user | conhost — windowless |
| **QI_UsageSnapshot** | every 30 min | `engine\common\usage_snapshot_task.py` | hidden_user | pythonw (silent). Added 2026-08-13. Snapshots `usage_daily` + per-project/per-model dimensions into `qi_brain.db`. Without it the LLM Usage 30d/QTD/YTD tiles truncate at the ledger's last day (YTD froze at $60,124 for 8 days). Log: `C:\QIH\logs\usage_snapshot.log` |
| QI_TubeScout_AM | daily 07:00 | `C:\APPS\TUBESCOUT\run_cycle.bat` | hidden_user | conhost+cmd |
| QI_TubeScout_PM | daily 19:00 | `C:\APPS\TUBESCOUT\run_cycle.bat` | hidden_user | conhost+cmd |
| QI_NightlyGitSync | daily 00:35 | `nightly_git_sync.py` | hidden_user | conhost |
| QI_Ollama_Watchdog | every 1 min | `ollama_watchdog.py` | hidden_user | already pythonw (silent) |
| MaiaNightlySync | daily 21:00 | `maia_nightly_sync.py` | hidden_user | conhost |
| MaiaReconcile | daily 02:00 | `maia_reconcile.py` | hidden_user | conhost |
| MaiaRevertMiMo | daily 23:59 | `revert_mimo.py` | hidden_user | conhost |
| OC-Asa-Briefing-7AM | daily 07:00 | wsl `oc-morning-briefing.sh` | hidden_user | conhost |
| OC-Kaze-Digest-6AM | daily 06:00 | wsl `kaze-deliver-telegram.sh` | hidden_user | conhost |
| OC-Kaze-Digest-6PM | daily 18:00 | wsl `kaze-deliver-telegram.sh` | hidden_user | conhost |
| OC-Kaze-AI-Digest-6AM | daily 06:05 | wsl `kaze-ai-digest.sh` | hidden_user | conhost |
| OC-Kaze-AI-Digest-6PM | daily 18:05 | wsl `kaze-ai-digest.sh` | hidden_user | conhost |
| OC-Yubin-Daily-8AM * | daily 08:00 | wsl `yubin-daily.sh` | hidden_user | conhost (Highest) |
| OC-Yubin-Daily-6PM * | daily 18:00 | wsl `yubin-daily.sh` | hidden_user | conhost (Highest) |
| OC-Kakei-Weekly-Sunday-7PM | weekly Sun 19:00 | wsl `kakei-weekly.sh` | hidden_user | conhost |
| OC-Sentry-Drift-Sunday-8PM | weekly Sun 20:00 | wsl `sentry-weekly-drift.sh` | hidden_user | conhost |
| OC-ChatGPT-Keepalive | time trigger | `oc-chatgpt-keepalive.py` | hidden_user | already pythonw (silent) |
| OC_WSL_KeepAlive * | time trigger | `keep-wsl-alive.ps1` | hidden_user | conhost (Highest) |
| QI_McpConnectorGuard | every 5 min | `C:\QIH\engine\tools\ConnectorGuard\connector_guard.py` | hidden_user | conhost --headless in TR; reconciles Claude Desktop mcpServers vs connectors.json manifest; heartbeat in ConnectorGuard\logs |
| QI_NightlyReconcile | daily 02:30 | `tools\nightly_reconcile.py` | system | Backfills session_log from git + .docx, regenerates LATEST.md/status.json, runs the doc harvest + embeddings. **⚠ Was terminated (0x41306) on 2026-08-17 against a PT10M limit** — a measured run takes ~3.5 min but the doc-harvest embedding step is variable (175 docs that night). Needs `ExecutionTimeLimit` raised to PT30M — see §7. |
| QI_ClaudeSelfAudit | monthly | Claude self-audit | hidden_user | Documented 2026-08-17 audit. |
| QI_ClaudeUpdate_6AM | daily 06:00 | `C:\APPS\CLAUDE\Tools\claude_update_launch.bat` | hidden_user | Documented 2026-08-17 audit. |
| QI_ClaudeVoiceBridgeCheck | hourly | Claude Voice bridge health probe | hidden_user | **⏸ DISABLED 2026-08-20** for the Claude Voice troubleshooting window — re-enabled by `QI_ClaudeVoiceRestore_20260919`. Documented 2026-08-17 audit. |
| QI_ClaudeVoiceMeeting_8AM | daily 08:00 | Claude Voice meeting room | hidden_user | Long-running by design (hosts the room) — a `Running` state during the day is expected, not a hang. **⏸ DISABLED 2026-08-20** for the troubleshooting window; the already-running `meeting_server.py` (:8722) had to be killed separately, because the task launches it via a .bat and it detaches — disabling the task alone does not reap it. Re-enabled by `QI_ClaudeVoiceRestore_20260919`. Documented 2026-08-17 audit. |
| QI_ClaudeVoiceRestore_20260919 | **once, 2026-09-19 09:00** | `tools\claudevoice_power.py on` | renne (interactive) | **Added 2026-08-20.** Ends the Claude Voice troubleshooting window: restores all four `QI_ClaudeVoice*` services to `SERVICE_AUTO_START`, starts them, re-enables the two tasks above, and brings the desktop voice loop back up. Runs as `renne` **on purpose** — the desktop mic loop/responder must land in the interactive session, and the elevated service work is brokered through QI_Elevate rather than needing an admin token. `StartWhenAvailable` is set, so it still fires if Renne isn't logged on at 09:00. Delete this row once it has run. |
| QI_EffortLedger_Daily | daily 23:50 | `engine\effort\EffortLedger_Daily.bat` | hidden_user | Documented 2026-08-17 audit. |
| QI_FilmForge_Night | nightly (disabled) | FilmForge night runner | — | Currently **Disabled**, has never run. Documented 2026-08-17 audit. |

### Retired / orphaned one-shots — safe to delete

These have no `NextRunTime` and no live purpose. They linger because one-shot tasks
are never cleaned up automatically. Deleting them needs an elevated shell (see §7).

| Task | Last ran | Why it's dead |
|---|---|---|
| **MaiaRevertMiMo** | 2026-04-01 | One-shot; last result `0x80070002` (file not found). `revert_mimo.py` exists again today, but the task has no trigger, so it will never fire. |
| **QI_ClaudeUpdate_Tonight** | 2026-06-28 | One-shot companion to `QI_ClaudeUpdate_6AM`, which covers this daily. |
| **QI_DemoDayStartup** | 2026-07-20 | One-shot for a specific demo day that has passed. |
| **QI_GamezAIPin** | 2026-06-25 | One-shot that set a Gamez AI pin; already applied. |

### §7 — Elevated fixes still outstanding (2026-08-17 audit)

These need an **elevated** PowerShell; they are deliberately NOT in the QI Elevation
Broker whitelist, because task creation/deletion takes arbitrary commands as arguments.

```powershell
# 1. Stop QI_NightlyReconcile being killed mid-run (measured 3.5 min, limit is 10)
$t = Get-ScheduledTask -TaskName 'QI_NightlyReconcile'
$t.Settings.ExecutionTimeLimit = 'PT30M'
Set-ScheduledTask -TaskName 'QI_NightlyReconcile' -Settings $t.Settings

# 2. Remove the four dead one-shots listed above
'MaiaRevertMiMo','QI_ClaudeUpdate_Tonight','QI_DemoDayStartup','QI_GamezAIPin' |
  ForEach-Object { Unregister-ScheduledTask -TaskName $_ -Confirm:$false }
```
| QI_ComplianceFast | inspector fast cycle | `inspector --mode fast` | system | SYSTEM — already invisible |
| QI_NightlyReconcile | nightly | `nightly_reconcile.py` | system | SYSTEM — already invisible |
| **QI_DemoDayStartup** | **once 2026-06-26 07:30** | `C:\QIH\engine\tunnels\demo_day_startup.py` | hidden_user | conhost --headless; one-time demo-day kick. Starts all apps + tunnels, verifies every public URL, retries down ones, pushes pass/fail to Tasuke LINE. Runs Limited; `nssm start/restart` elevated via QI_Elevate broker. M2V (no NSSM svc) launched as a detached process. Safe to delete after the demo day. |

---

## 5. Adding a new scheduled task (keep it windowless)

1. Create the task as usual (or via `schtasks` / Task Scheduler).
2. Add an entry to `scheduled_tasks_window_policy.json` with `"window_mode": "hidden_user"`.
3. Run `python C:\QIH\tools\qi_task_window_manager.py --apply --only <NewTaskName>`.
4. If the task is `RunLevel=Highest`, run that command from an **elevated** shell.
5. Confirm with `--verify` — `Exe` should read `conhost.exe` (or `pythonw.exe`), `Hidden=True`.

---

*Related: `QI_Service_Registry.md` (NSSM services), `QI_Ecosystem_Map.md` (ports & families), `QI_Standards.md` (conventions).*


---

## QI_RelaySync — Claude-to-Claude collaborator relay

**Added:** 2026-08-18 · **Cadence:** every 30 min (:00 / :30) · **Window mode:** `hidden_user`

Exchanges structured project updates with external collaborators (currently Urcil Peters)
through a private git mailbox, so each side's Claude can brief its owner and draft replies
without either human hand-writing relay prompts.

| Item | Path |
|---|---|
| Mailbox repo (separate repo — **not** inside QIH) | `C:\QI-RELAY\` |
| Protocol spec (configures both Claudes) | `C:\QI-RELAY\PROTOCOL.md` |
| Task action | `C:\QIH\tools\qi_relay_cycle.bat` |
| Transport step (no AI) | `C:\QIH\tools\qi_relay_sync.py` |
| Drafting step (sandboxed Claude) | `C:\QIH\tools\qi_relay_draft.py` |
| Digest output | `C:\QIH\inbox
elay\pending.md` |
| Logs | `C:\QIH\LOGS\qi_relay_sync.log`, `qi_relay_draft.log` |

**Why `hidden_user` and not `system`:** the cycle needs the user profile for git
credentials and `claude` CLI auth. As SYSTEM it would fail both.

**Symptom → check:**

| Symptom | Check |
|---|---|
| No new messages appearing | `qi_relay_sync.log` — look for `pull failed` or `no remote configured` |
| Messages appear but no drafts | `qi_relay_draft.log` — `Not logged in` means the CLI lost its session |
| `[GUARD] reverted ...` in the draft log | The drafting step tried to write outside `_drafts/`. Investigate before re-running — this is the injection tripwire. |
| `quarantined` entries in `state/renne.json` | A peer sent a spoofed or malformed message. It was NOT forwarded. |

**LIVE as of 2026-08-19.** Remote: `https://github.com/Quiddity-Innovations/qi-relay` (private).
Task registered and wrapped headless; **first run held until Sun 2026-08-23 00:00**, then every
30 min indefinitely. Principal: Interactive (needs the user profile for git creds + claude auth).

⚠️ **Two things still open:** the L2 drafting step has never had a successful model call
(`python C:\QIH\tools\qi_relay_draft.py --self-test --budget 0.40`). The external collaborator
has been invited as an outside collaborator on the relay repo only; identities and roster live in
the **private** relay repo (`peers.json`), never here — **this repo is public.**


---

## 8. Health status (audit 2026-08-27) — verified by output artifact, NOT LastTaskResult

Full report: `C:\QIH\shared\documentation\QI_Task_Health_Audit_2026-08-27.md`

| Status | Tasks |
|---|---|
| DEAD (66d) | **QI_TubeScout_AM**, **QI_TubeScout_PM** - `invalid_grant` on sweep+reclassify every cycle since 2026-06-23; no new video since 2026-06-22; still logs `cycle done` |
| DEAD (18d) | **OC-Yubin-Daily-8AM**, **OC-Yubin-Daily-6PM** - `last-digest.json` frozen 2026-08-09; failed again today |
| DEAD (18d) | **OC-Asa-Briefing-7AM** - last `Briefing sent` 2026-08-09; failed again today |
| DEAD (never worked) | **OC-Sentry-Drift-Sunday-8PM** - reports dir has never existed; skips silently every week |
| DEAD (never delivered) | **OC-Kakei-Weekly-Sunday-7PM** - 11/11 runs JSONDecodeError, logs success anyway |
| UNPROVEN | **OC-Kaze-Digest-6AM/6PM**, **OC-Kaze-AI-Digest-6AM/6PM** - repaired manually 2026-08-27 11:40; scheduled path not yet proven |
| DEGRADED | **QI_NightlyGitSync** (PersonalSong ABORTing 18+ nights on `plex_token`), **MaiaNightlySync** (never stages code; 86 files unbacked) |
| HEALTHY | MaiaReconcile, QI_BrainBackfill, QI_McpConnectorGuard, QI_RelaySync, QI_EffortLedger_Daily, QI_DomainDropWatch_Daily, QI_ClaudeUpdate_6AM, QI_ClaudeSelfAudit |
| DISABLED | OC_WSL_KeepAlive, QI_ClaudeVoiceBridgeCheck, QI_ClaudeVoiceMeeting_8AM |

### Path rot
`C:\OC` is an NTFS junction to `C:\APPS\OC` and is **load-bearing - do not remove**. But WSL's
`/mnt/c/OC` view was only created **2026-08-27 11:40**; it did not resolve during the 18-day outage,
which is the actual mechanism of the OC family's death. All six OC scripts still hardcode
`/mnt/c/OC/...` internally, and the two Yubin task definitions still invoke the old path.

### Proposed: one central freshness monitor
Manifest at `C:\QIH\ecosystem\task_health_manifest.json`, evaluated by an always-on host
(**QI_BrainAPI**, :9011). Central rather than per-task, because a per-task check dies with the task
it is meant to watch. Check types ranked strongest-first: `db` row > log `marker` > `git` commit >
file mtime. **Every new unattended job ships its freshness check as part of "done".**


---

## 9. QI_TaskHealth — the outcome monitor (added 2026-08-27)

The remediation of the health audit. Everything above governs **how** a task
runs; this governs **how we know it worked**.

| Item | Path |
|---|---|
| Manifest | `C:\QIH\ecosystem\task_health_manifest.json` |
| Checker | `C:\QIH\tools\qi_task_health.py` |
| Status output | `C:\QIH\data\task_health.json` |
| Log | `C:\QIH\logs\qi_task_health.log` |
| Report | `C:\QIH\shared\documentation\QI_Task_Health_Audit_2026-08-27.md` |

```bash
python C:\QIH\tools\qi_task_health.py --once            # report to stdout
python C:\QIH\tools\qi_task_health.py --once --json     # machine-readable
python C:\QIH\tools\qi_task_health.py --once --notify   # alert if stale
```

Watches **22 tasks**. Check types, strongest first: `sqlite` (a data row whose
timestamp advances) > `marker` (a task-specific success string) > `git` (a real
commit) > `file` (mtime, last resort). Alerts to Telegram once per task per 20h,
and sends a recovery notice when a task comes back.

**It is central, not per-task, on purpose.** A per-task check ships inside the
thing it checks, so it dies with it — a dead task cannot report itself dead. That
is exactly how Kaze stayed dark 18 days and TubeScout 66.

It also carries a **self-watch** entry on its own status file, so a dead monitor
shows up as stale rather than as a healthy estate.

### Two caveats, both deliberate

**Interim host.** It runs as a user-level scheduled task, not an NSSM service,
because the elevation broker's `nssm_install_qi` rule allows python only at
`C:\Windows\System32`, `C:\1-AI\APPS\PYTHON` or `C:\Python*` — **none of which
exist on this machine any more** (Python is at `C:\Program Files\Python311`), so
the rule is currently unsatisfiable and every QI service install is denied. The
whitelist was **not** widened; security boundaries are Tier 1. To promote, from an
elevated shell:

```bash
C:\QIH\engine\bin\nssm.exe install QI_TaskHealth "C:\Program Files\Python311\python.exe" "C:\QIH\tools\qi_task_health.py --daemon"
```

then set `AppDirectory` to `C:\QIH`, start it, and delete the interim task.

**Its own LastTaskResult is meaningless** — it is conhost-wrapped like everything
else. Tolerable only because its product is a Telegram alert plus a status file
that the manifest itself watches.

### Adding a task to the monitor

Add an entry to `task_health_manifest.json` naming the artifact that proves
success. Prefer a **DB row** over a log marker, a marker over mtime, and never
mtime of a wrapper log. If a job is silent by design, make it positively declare
that — `QI_ClaudeUpdate_6AM` writes `result: "noop"` every morning, which is why
"nothing happened" is still provably healthy there.

**Every new unattended job ships its freshness check as part of "done".**

# QI Ecosystem — Scheduled Tasks Registry & Window Policy

**Authority:** This file is the single source of truth for all QI/OC/Maia **Windows Scheduled Tasks** (the sibling of `QI_Service_Registry.md`, which covers NSSM *services*).
**Location:** `C:\QIH\ecosystem\QI_Scheduled_Tasks_Registry.md`
**Last updated:** 2026-06-18

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

- ❌ **Do not swap `python.exe` → `pythonw.exe`.** `pythonw` sets `sys.stdout = None`, so any script that prints/logs to stdout crashes (exit 1). Also venvs often lack `pythonw.exe` (e.g. `C:\QI\.venv\Scripts\` has none). Use `conhost --headless python.exe` instead — real binary, valid stdout, no window.
- ⚠️ **`conhost --headless` does not propagate the child exit code.** Task Scheduler will always show `LastTaskResult = 0`, even on failure. This is fine because every task logs to its own file — **verify a run by checking the log timestamp, not LastTaskResult.**
- ⚠️ **`RunLevel = Highest` tasks need admin even to enable/modify.** Apply those from an **elevated** PowerShell/Terminal. The `QI_Elevate` broker only whitelists `nssm`/`sc`/`taskkill` (not PowerShell), so this step cannot currently be brokered.

---

## 4. Full task catalog (as of 2026-06-18)

All `hidden_user` tasks below are now windowless. `*` = required a one-time elevated apply (RunLevel Highest).

| Task | Schedule | Runs | Mode | Status |
|---|---|---|---|---|
| **QI_BrainBackfill** | every 30 min | `brain_backfill_tick.py` | hidden_user | conhost — windowless |
| QI_TubeScout_AM | daily 07:00 | `C:\TUBESCOUT\run_cycle.bat` | hidden_user | conhost+cmd |
| QI_TubeScout_PM | daily 19:00 | `C:\TUBESCOUT\run_cycle.bat` | hidden_user | conhost+cmd |
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

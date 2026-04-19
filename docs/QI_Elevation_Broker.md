# QI Elevation Broker

**Status:** Active · **Service:** `QI_Elevate` · **Account:** LocalSystem
**Installed:** 2026-04-19 · **Owner:** QI Hive

---

## Why this exists

Renne runs Claude and other QI agents from a **non-admin** shell. Windows UAC means any operation that touches services, kills processes by PID, or repoints NSSM parameters requires a human to click the UAC prompt. That breaks overnight/unattended work — the agent stops right after Renne leaves.

The Elevation Broker removes that barrier **safely** by splitting the problem in two:

1. **Agents (non-admin)** drop a JSON "request" into a watched folder.
2. **Broker (SYSTEM service)** picks it up, validates against a regex whitelist, and executes the command with full admin rights. Result is written back as a JSON file the agent reads.

No UAC. No credentials stored. The service is already SYSTEM; a narrow whitelist bounds what it will run.

---

## Architecture

```
  Agent / Claude (non-admin)
        │  writes
        ▼
  C:\QIH\commands\pending\<id>.json
        │
        ▼
  QI_Elevate  (NSSM service, LocalSystem)
   ├─ polls pending/ every 1s
   ├─ validates cmd + args against whitelist.json (regex fullmatch)
   ├─ subprocess.run(binary, args, shell=False, timeout=60)
   ├─ writes result → completed/<id>.json
   └─ archives request → archive/<id>.json
        │
        ▼
  Agent reads completed/<id>.json  (via qi_elevate_client.run_elevated)
```

---

## File layout

| Path | Purpose |
|---|---|
| `C:\QIH\engine\common\qi_elevate.py` | Broker (runs as SYSTEM) |
| `C:\QIH\engine\common\qi_elevate_client.py` | Client helper (used by agents) |
| `C:\QIH\commands\whitelist.json` | Regex-bounded allow-list (hot-reloaded on change) |
| `C:\QIH\commands\pending\` | Incoming request queue |
| `C:\QIH\commands\completed\` | Results (one file per request) |
| `C:\QIH\commands\archive\` | Processed requests (audit trail) |
| `C:\QIH\logs\elevation\broker.log` | Rotating broker log (5 MB × 5) |
| `C:\QIH\tools\install_elevation_broker.bat` | One-time installer (admin) |

---

## Install

1. **Open an elevated terminal** (Right-click → Run as administrator).
2. Run: `C:\QIH\tools\install_elevation_broker.bat`
3. Confirm status shows `SERVICE_RUNNING`.

Re-running the installer is safe — it stops + removes any previous `QI_Elevate` before re-installing.

---

## Use from client code

```python
from engine.common.qi_elevate_client import run_elevated

result = run_elevated(
    "nssm",
    ["restart", "QI_Dashboard"],
    submitted_by="claude",
    timeout=30,
)
print(result["status"], result["stdout"])
```

Return dict:

| Key | Meaning |
|---|---|
| `status` | `"ok"` / `"error"` / `"denied"` |
| `returncode` | Process exit code |
| `stdout` / `stderr` | Captured output |
| `rule_matched` | Which whitelist rule allowed it |
| `error` | Reason (populated when denied or errored) |
| `completed_at` | ISO timestamp |

If the broker is down, `run_elevated` raises `TimeoutError` after `timeout` seconds.

---

## Security model

**The broker runs as SYSTEM — so what it executes matters.** Every request must match a rule in `whitelist.json`:

- `cmd` must equal a known logical name (currently `nssm` or `taskkill`)
- Argument count must fall in `[arg_count_min, arg_count_max]`
- Each argument must **fullmatch** the corresponding regex in `args_regex`

Rejected requests are logged with a reason and returned with `status: "denied"` — the broker never runs them.

**No shell, no expansion.** `subprocess.run([binary, *args], shell=False)` — no path traversal via backticks or `&&`.

**Binary resolution is fixed.** `nssm` → `C:\QIH\engine\bin\nssm.exe`, `taskkill` → `C:\Windows\System32\taskkill.exe`. An agent cannot substitute a different binary.

**Service-name scope.** All service-control rules require `^QI_[A-Za-z0-9_]+$` — so the broker cannot start/stop/restart system services outside the QI family (Windows Defender, etc.).

**Path scope.** `nssm set AppDirectory/AppParameters` rules only allow paths under `C:\QIH` or `C:\QIP`.

---

## Current whitelist

| Rule | Command | Scope |
|---|---|---|
| `nssm_service_control` | `nssm start|stop|restart|status|pause|continue QI_*` | Service lifecycle |
| `nssm_set_appdir` | `nssm set QI_* AppDirectory C:\QIH\... or C:\QIP\...` | Repoint folder |
| `nssm_set_appparams` | `nssm set QI_* AppParameters C:\QIH\...\*.py\|.bat` | Repoint script |
| `nssm_set_description` | `nssm set QI_* Description <str ≤ 200>` | Update description |
| `taskkill_by_pid` | `taskkill /PID <n> /F` | Force-kill by PID |

Source of truth: `C:\QIH\commands\whitelist.json`.

---

## Editing the whitelist

Edit `C:\QIH\commands\whitelist.json` in a text editor. **The broker hot-reloads on file mtime change** — no service restart needed. Watch `broker.log` for `whitelist reloaded (N rules)` to confirm.

Add new rules conservatively. A good rule:
- names a specific logical `cmd`
- pins `arg_count_min == arg_count_max` when possible
- uses tight regex (e.g. `^QI_[A-Za-z0-9_]+$` not `.*`)
- has a human-readable `name` and `description`

---

## Operations

| Want to... | Do this |
|---|---|
| Check if broker is running | `nssm status QI_Elevate` |
| Restart the broker | `nssm restart QI_Elevate` (requires admin OR a self-submitted broker request) |
| Read the broker log | `Get-Content C:\QIH\logs\elevation\broker.log -Tail 50` |
| See the audit trail | Browse `C:\QIH\commands\archive\` |
| Submit a smoke test | `python C:\QIH\engine\common\qi_elevate_client.py` (runs `nssm status QI_BrainAPI`) |

---

## Known limitations

- **The broker itself cannot restart itself** via the whitelist — `QI_Elevate` is included in `^QI_[A-Za-z0-9_]+$`, but stopping the broker mid-request leaves the pending file unprocessed. Prefer: schedule a task via Windows Task Scheduler to restart `QI_Elevate` on a timer if needed.
- **No cross-user auth.** Any process that can write to `C:\QIH\commands\pending\` can submit. This is acceptable because the machine is single-user (Renne); on a multi-user host, add ACLs to the pending folder.
- **60-second command timeout.** Longer operations (DB migrations, large copies) would need an async variant.

---

## Troubleshooting

| Symptom | Check |
|---|---|
| Client raises `TimeoutError` | `nssm status QI_Elevate` — is the service running? Read `broker.log` tail. |
| Response has `status: "denied"` | The `error` field names the rule gap. Adjust whitelist if the command should be allowed. |
| `returncode != 0` | Read `stderr` in the response — the underlying command failed, not the broker. |
| Requests pile up in `pending/` | Broker is stuck or stopped. Check `broker.log` for exceptions; restart service. |

---

## Audit

Every processed request lands in `archive/` with its original JSON, and every result in `completed/`. Pair them by `id` for a full forensic trail. `broker.log` is the chronological record.

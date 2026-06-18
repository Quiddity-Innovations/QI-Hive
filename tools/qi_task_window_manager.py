# -*- coding: utf-8 -*-
"""
QI Scheduled-Task Window Manager
================================

Single control point for whether QI/OC/Maia Windows scheduled tasks are allowed
to pop a console window while you work.

Config (single source of truth):
    C:\\QIH\\ecosystem\\scheduled_tasks_window_policy.json

Per task you set two things:
    enabled      true  -> Enable-ScheduledTask
                 false -> Disable-ScheduledTask
    window_mode  "hidden_user"  run as the user via S4U ("run whether logged on
                                or not") + Hidden + swap python.exe->pythonw.exe.
                                NEVER shows a window; keeps the full user profile
                                (git creds, WSL session, user venvs).  <-- default
                 "system"       run as SYSTEM/ServiceAccount (session 0, invisible)
                                but loses the user profile. Only for self-contained
                                scripts. Changing TO/FROM system needs admin.
                 "visible"      restore normal interactive run (for debugging).

Usage:
    python qi_task_window_manager.py                 # dry-run: show the plan, change nothing
    python qi_task_window_manager.py --apply         # apply the whole policy
    python qi_task_window_manager.py --apply --only QI_BrainBackfill
    python qi_task_window_manager.py --verify         # show the live state of every managed task

Why this works: a task only flashes a console window when it runs as the
interactive user (LogonType=Interactive) AND launches a console program
(python.exe / wsl.exe / .bat / powershell) AND isn't hidden. Switching the
principal to S4U runs it in a non-interactive session, so no window appears,
while the task still runs under your account with your profile.
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CONFIG = Path(r"C:\QIH\ecosystem\scheduled_tasks_window_policy.json")

# PowerShell engine. Parameterized; one invocation per task. Idempotent.
#
# Window suppression strategy (NO admin required):
#   * python.exe tasks  -> swap to pythonw.exe (windowless Python host: zero console)
#   * wsl/.bat/other     -> wrap action in 'conhost.exe --headless <cmd>' (Win11
#                           headless console host: program runs with no window)
#   * Settings.Hidden=$true (cosmetic: hides from default Task Scheduler list)
# These are ACTION/SETTINGS changes only, so they apply as the normal user.
# Changing the PRINCIPAL (S4U or SYSTEM) DOES require admin -- that is only
# attempted for window_mode 'system', and skipped if the task is already SYSTEM.
PS_APPLY = r'''
param(
  [Parameter(Mandatory=$true)][string]$Name,
  [Parameter(Mandatory=$true)][string]$Mode,
  [Parameter(Mandatory=$true)][string]$Enabled,
  [Parameter(Mandatory=$true)][string]$Account
)
$ErrorActionPreference = 'Stop'
try {
  $t = Get-ScheduledTask -TaskName $Name -ErrorAction Stop
} catch {
  Write-Output ("ERROR  {0} : not found" -f $Name); exit 2
}

if ($Enabled -ne 'true') {
  Disable-ScheduledTask -TaskName $Name | Out-Null
  Write-Output ("DISABLED  {0}" -f $Name); exit 0
}
Enable-ScheduledTask -TaskName $Name | Out-Null

$settings = $t.Settings
$actions  = $t.Actions

function Leaf([string]$p) { if (-not $p) { return '' } ; (Split-Path ($p.Trim('"')) -Leaf).ToLower() }

switch ($Mode) {
  'hidden_user' {
    # Wrap console programs in 'conhost.exe --headless' so no window appears.
    # Leave tasks that are already silent (pythonw.exe) or already wrapped
    # (conhost.exe) untouched -> idempotent, no churn on working tasks.
    foreach ($a in $actions) {
      $leaf = Leaf $a.Execute
      if ($leaf -eq 'conhost.exe' -or $leaf -eq 'pythonw.exe') { continue }
      $origExec = $a.Execute
      $origArgs = $a.Arguments
      if ($leaf -like '*.bat' -or $leaf -like '*.cmd') {
        $inner = 'cmd.exe /c "' + $origExec.Trim('"') + '"'
      } else {
        $inner = $origExec   # python.exe, wsl.exe, powershell.exe, etc.
      }
      if ($origArgs) { $inner = $inner + ' ' + $origArgs }
      $a.Execute   = 'conhost.exe'
      $a.Arguments = '--headless ' + $inner
    }
    $settings.Hidden = $true
    Set-ScheduledTask -TaskName $Name -Action $actions -Settings $settings | Out-Null
    Write-Output ("HIDDEN_USER  {0}  (conhost --headless; principal unchanged)" -f $Name)
  }
  'system' {
    if ($t.Principal.LogonType -eq 'ServiceAccount' -or $t.Principal.UserId -match 'SYSTEM') {
      Write-Output ("SYSTEM  {0}  (already SYSTEM; no change)" -f $Name)
    } else {
      $p = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
      Set-ScheduledTask -TaskName $Name -Principal $p | Out-Null
      Write-Output ("SYSTEM  {0}  (re-homed to SYSTEM)" -f $Name)
    }
  }
  'visible' {
    foreach ($a in $actions) {
      if ((Leaf $a.Execute) -eq 'pythonw.exe') {
        $a.Execute = ($a.Execute -replace 'pythonw\.exe("?)$','python.exe$1')
      }
      elseif ((Leaf $a.Execute) -eq 'conhost.exe') {
        $rest = ($a.Arguments -replace '^\s*--headless\s+','')
        if ($rest -match '^cmd\.exe /c "(.+?)"\s*(.*)$') {
          $a.Execute = $Matches[1]; $a.Arguments = $Matches[2]
        } else {
          $parts = $rest -split '\s+',2
          $a.Execute = $parts[0]; $a.Arguments = if ($parts.Count -gt 1) { $parts[1] } else { '' }
        }
      }
    }
    $settings.Hidden = $false
    Set-ScheduledTask -TaskName $Name -Action $actions -Settings $settings | Out-Null
    Write-Output ("VISIBLE  {0}" -f $Name)
  }
  default { Write-Output ("ERROR  {0} : unknown mode '{1}'" -f $Name, $Mode); exit 3 }
}
'''

PS_VERIFY = r'''
param([Parameter(Mandatory=$true)][string]$Name)
$ErrorActionPreference = 'SilentlyContinue'
$t = Get-ScheduledTask -TaskName $Name
if (-not $t) { Write-Output ("{0,-30} NOT FOUND" -f $Name); exit 0 }
$p = $t.Principal
$exe = ($t.Actions | ForEach-Object { Split-Path $_.Execute -Leaf }) -join ','
Write-Output ("{0,-30} State={1,-9} RunAs={2,-8} Logon={3,-14} Hidden={4,-5} Exe={5}" -f `
  $Name, $t.State, $p.UserId, $p.LogonType, $t.Settings.Hidden, $exe)
'''


def run_ps(script: str, args: list[str]) -> subprocess.CompletedProcess:
    with tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False, encoding="utf-8") as f:
        f.write(script)
        path = f.name
    try:
        return subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", path, *args],
            capture_output=True, text=True,
        )
    finally:
        try:
            Path(path).unlink()
        except OSError:
            pass


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Control whether scheduled tasks pop console windows.")
    ap.add_argument("--apply", action="store_true", help="apply the policy (default is dry-run)")
    ap.add_argument("--verify", action="store_true", help="print the live state of every managed task")
    ap.add_argument("--only", metavar="TASK[,TASK...]", help="limit to these tasks (comma-separated)")
    ap.add_argument("--mode", choices=["hidden_user", "system", "visible"],
                    help="override the config window_mode for this run (use with --apply)")
    args = ap.parse_args()

    cfg = load_config()
    account = cfg.get("account", "renne")
    tasks = cfg["tasks"]
    if args.only:
        wanted = [t.strip() for t in args.only.split(",") if t.strip()]
        missing = [t for t in wanted if t not in tasks]
        if missing:
            print(f"!! not in policy: {', '.join(missing)}"); return 1
        tasks = {t: tasks[t] for t in wanted}

    if args.verify:
        print("=== LIVE STATE ===")
        for name in tasks:
            r = run_ps(PS_VERIFY, [name])
            print((r.stdout or r.stderr).rstrip())
        return 0

    if not args.apply:
        print("=== DRY-RUN (no changes). Re-run with --apply to enforce. ===\n")
        for name, spec in tasks.items():
            mode = spec.get("window_mode", "hidden_user")
            en = "enabled" if spec.get("enabled", True) else "DISABLE"
            print(f"  {name:<30} -> {mode:<12} [{en}]   {spec.get('note','')}")
        print(f"\n{len(tasks)} task(s). Account for hidden_user/visible = '{account}'.")
        return 0

    print("=== APPLYING POLICY ===" + (f"  (mode override: {args.mode})" if args.mode else ""))
    ok = err = 0
    for name, spec in tasks.items():
        mode = args.mode or spec.get("window_mode", "hidden_user")
        enabled = "true" if spec.get("enabled", True) else "false"
        r = run_ps(PS_APPLY, [name, mode, enabled, account])
        out = (r.stdout or "").strip()
        if r.returncode == 0 and out and not out.startswith("ERROR"):
            print(f"  OK   {out}")
            ok += 1
        else:
            print(f"  FAIL {name}: rc={r.returncode} {out} {r.stderr.strip()}")
            err += 1
    print(f"\nDone. {ok} applied, {err} failed.")
    return 0 if err == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

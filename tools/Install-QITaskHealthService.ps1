# Install-QITaskHealthService.ps1
#
# Promote QI_TaskHealth from the interim scheduled task to a real NSSM service.
#
# MUST BE RUN FROM AN ELEVATED POWERSHELL. It is not brokered through QI_Elevate
# because that broker's nssm_install_qi rule only permits python at
# C:\Windows\System32, C:\1-AI\APPS\PYTHON or C:\Python* - none of which exist on
# this machine any more (python lives at C:\Program Files\Python311). The rule is
# therefore currently unsatisfiable and the broker denies every QI service
# install. The whitelist was deliberately NOT widened to work around that:
# whitelists are a security boundary, and quietly loosening one to unblock
# yourself is how boundaries stop meaning anything. See Brain decision 577.
#
# Why a service and not a task: a scheduled task inherits the conhost
# exit-code blindness this monitor exists to compensate for, and the monitor
# must stay independent of everything it watches.

$ErrorActionPreference = 'Stop'

$svc    = 'QI_TaskHealth'
$nssm   = 'C:\QIH\engine\bin\nssm.exe'
$py     = 'C:\Program Files\Python311\python.exe'
$script = 'C:\QIH\tools\qi_task_health.py'
$appdir = 'C:\QIH'
$out    = 'C:\QIH\logs\qi_task_health.service.log'
$err    = 'C:\QIH\logs\qi_task_health.service.err.log'
$desc   = 'QI-wide scheduled-task freshness monitor. Verifies every QI/OC/Maia task by its OUTPUT ARTIFACT, because conhost --headless makes LastTaskResult always 0 and a growing wrapper log does not prove success. Manifest: C:\QIH\ecosystem\task_health_manifest.json  Report: C:\QIH\data\task_health.json'

# --- preflight -------------------------------------------------------------
$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "FAIL: not elevated. Re-open PowerShell as Administrator and run this again." -ForegroundColor Red
    exit 1
}
foreach ($p in @($nssm, $py, $script)) {
    if (-not (Test-Path $p)) { Write-Host "FAIL: missing $p" -ForegroundColor Red; exit 1 }
}
Write-Host "Preflight OK (elevated, nssm + python + script present)." -ForegroundColor Green

# --- install ---------------------------------------------------------------
if (Get-Service $svc -ErrorAction SilentlyContinue) {
    Write-Host "$svc already exists - reconfiguring in place."
    & $nssm stop $svc 2>$null | Out-Null
} else {
    & $nssm install $svc $py "`"$script`" --daemon"
    Write-Host "Installed $svc"
}

& $nssm set $svc AppDirectory     $appdir        | Out-Null
& $nssm set $svc AppParameters    "`"$script`" --daemon" | Out-Null
& $nssm set $svc Description      $desc          | Out-Null
& $nssm set $svc AppStdout        $out           | Out-Null
& $nssm set $svc AppStderr        $err           | Out-Null
& $nssm set $svc AppRotateFiles   1              | Out-Null
& $nssm set $svc AppRotateBytes   10485760       | Out-Null
& $nssm set $svc Start            SERVICE_AUTO_START | Out-Null
& $nssm set $svc AppExit Default  Restart        | Out-Null
& $nssm set $svc AppRestartDelay  30000          | Out-Null
Write-Host "Configured $svc"

& $nssm start $svc | Out-Null
Start-Sleep -Seconds 8

# --- verify by OUTCOME, not by exit code -----------------------------------
$state = (Get-Service $svc).Status
Write-Host "Service status: $state"

$statusFile = 'C:\QIH\data\task_health.json'
$before = (Get-Item $statusFile -EA SilentlyContinue).LastWriteTime
Write-Host "Waiting up to 60s for the service to write a fresh status file..."
$fresh = $false
for ($i = 0; $i -lt 12; $i++) {
    Start-Sleep -Seconds 5
    $now = (Get-Item $statusFile -EA SilentlyContinue).LastWriteTime
    if ($now -and (-not $before -or $now -gt $before)) { $fresh = $true; break }
}

if ($state -eq 'Running' -and $fresh) {
    Write-Host "VERIFIED: service is Running AND produced a fresh status file." -ForegroundColor Green

    # Retire the interim scheduled task so the two don't both poll.
    if (Get-ScheduledTask -TaskName $svc -EA SilentlyContinue) {
        Disable-ScheduledTask -TaskName $svc -EA SilentlyContinue | Out-Null
        Write-Host "Disabled the interim scheduled task '$svc' (kept, not deleted, so it is easy to fall back)."
    }
    Write-Host ""
    Write-Host "Done. Check anytime with:  nssm status $svc"
    Write-Host "Live report:  python C:\QIH\tools\qi_task_health.py --once"
    exit 0
} else {
    Write-Host "NOT VERIFIED - status=$state freshStatusFile=$fresh" -ForegroundColor Yellow
    Write-Host "The interim scheduled task was left ENABLED on purpose, so monitoring continues."
    Write-Host "Check the service log: $err"
    exit 1
}

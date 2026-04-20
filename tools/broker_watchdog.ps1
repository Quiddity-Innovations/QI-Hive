# broker_watchdog.ps1 — keeps QI_Elevate alive.
# Called every 1 minute by the QI_ElevateWatchdog scheduled task (runs as SYSTEM).
# If QI_Elevate is stopped, restart it. No-op otherwise. Logs to LOGS/watchdog.log.
$ErrorActionPreference = "SilentlyContinue"
$log  = "C:\QIH\logs\elevation\watchdog.log"
$nssm = "C:\QIH\engine\bin\nssm.exe"

New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null

$status = (& $nssm status QI_Elevate).Trim()
if ($status -ne "SERVICE_RUNNING") {
    "$(Get-Date -Format o)  QI_Elevate=$status  → starting" | Add-Content $log
    $out = & $nssm start QI_Elevate 2>&1
    "$(Get-Date -Format o)  result: $out" | Add-Content $log
}

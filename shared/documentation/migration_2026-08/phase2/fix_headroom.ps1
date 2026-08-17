# QI_Headroom failed to start after its venv was recreated.
#
# Cause: NSSM writes the service's stdout/stderr into
# C:\CLAUDE\Tools\headroom_env\logs\ - a directory that lives INSIDE the venv.
# Renaming the venv aside took the log directory with it, and NSSM will not
# start a service whose redirect target directory does not exist.
#
# This is precisely the failure mode Phase 4's code/data separation exists to
# prevent: runtime data must not live inside the code tree.
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

$logDir = 'C:\CLAUDE\Tools\headroom_env\logs'

Write-Output ("=== recreating " + $logDir + " ===")
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
Write-Output ("  exists: " + (Test-Path $logDir))

Write-Output ""
Write-Output "=== NSSM redirect config ==="
$nssm = 'C:\QIH\engine\bin\nssm.exe'
foreach ($f in @('Application','AppDirectory','AppParameters','AppStdout','AppStderr')) {
    $v = (& $nssm get QI_Headroom $f 2>$null) -join ''
    $v = ($v -replace "`0", '').Trim()
    Write-Output ("  " + $f.PadRight(14) + " " + $v)
}

Write-Output ""
Write-Output "=== starting QI_Headroom ==="
Start-Service QI_Headroom -ErrorAction SilentlyContinue
$deadline = (Get-Date).AddSeconds(45)
do {
    Start-Sleep -Seconds 3
    $st = (Get-Service QI_Headroom -ErrorAction SilentlyContinue).Status
} while ($st -ne 'Running' -and (Get-Date) -lt $deadline)
Write-Output ("  state: " + $st)

if ($st -eq 'Running') {
    Write-Output ""
    Write-Output "=== probing the proxy on :9020 ==="
    Start-Sleep -Seconds 5
    try {
        $r = Invoke-WebRequest -Uri 'http://127.0.0.1:9020/' -TimeoutSec 10 -UseBasicParsing
        Write-Output ("  HTTP " + $r.StatusCode)
    } catch {
        Write-Output ("  probe: " + $_.Exception.Message)
        Write-Output "  (a proxy may legitimately refuse a bare GET - port binding is what matters)"
    }
    $listening = Get-NetTCPConnection -LocalPort 9020 -State Listen -ErrorAction SilentlyContinue
    Write-Output ("  listening on 9020: " + [bool]$listening)
} else {
    Write-Output ""
    Write-Output "=== stderr tail ==="
    $e = Join-Path $logDir 'stderr.log'
    if (Test-Path $e) { Get-Content $e -Tail 25 } else { Write-Output "  (no stderr.log yet)" }
}

Write-Output ""
Write-Output "=== whole estate ==="
Get-Service -Name 'QI_*' | Group-Object Status | ForEach-Object {
    Write-Output ("  " + $_.Name + ": " + $_.Count)
}
$down = Get-Service -Name 'QI_*' | Where-Object { $_.Status -ne 'Running' } | Select-Object -ExpandProperty Name
Write-Output ("  not running: " + ($down -join ', '))
Write-Output "=== DONE ==="

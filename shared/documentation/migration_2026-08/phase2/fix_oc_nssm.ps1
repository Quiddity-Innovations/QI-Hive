# C:\OC survived the move because it still holds nssm.exe - the service host
# binary for OC-Keepalive-Service, which was running and therefore locked.
#
# The service's ImagePath names C:\OC\nssm.exe. Repoint it at the copy that
# already moved to C:\APPS\OC\nssm.exe, then retire the original so C:\OC can
# finally go.
# Pure ASCII only.
param([switch]$Apply)
$ErrorActionPreference = 'Continue'

$svc  = 'OC-Keepalive-Service'
$key  = 'HKLM:\SYSTEM\CurrentControlSet\Services\' + $svc
$new  = 'C:\APPS\OC\nssm.exe'
$hold = 'D:\_PREMOVE_2026-08-09\OC'

Write-Output "=== current ==="
$img = (Get-ItemProperty $key -ErrorAction SilentlyContinue).ImagePath
Write-Output ("  ImagePath : " + $img)
Write-Output ("  new binary exists : " + (Test-Path $new))
Write-Output ("  C:\OC contents:")
Get-ChildItem 'C:\OC' -Force -Recurse -ErrorAction SilentlyContinue |
    ForEach-Object { Write-Output ("     " + $_.FullName) }

if (-not (Test-Path $new)) { Write-Output "FATAL: C:\APPS\OC\nssm.exe missing"; exit 1 }

if (-not $Apply) {
    Write-Output ""
    Write-Output ("Would set ImagePath -> " + $new)
    Write-Output "DRY RUN"
    exit 0
}

Write-Output ""
Write-Output "=== stopping service ==="
Stop-Service -Name $svc -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 4
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'oc-keepalive-daemon' } |
    ForEach-Object {
        Write-Output ("  killing daemon PID " + $_.ProcessId)
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
Start-Sleep -Seconds 2
Write-Output ("  state: " + (Get-Service -Name $svc -ErrorAction SilentlyContinue).Status)

Write-Output ""
Write-Output "=== repointing ImagePath ==="
Set-ItemProperty -Path $key -Name 'ImagePath' -Value $new
Write-Output ("  now: " + (Get-ItemProperty $key).ImagePath)

Write-Output ""
Write-Output "=== retiring C:\OC ==="
New-Item -ItemType Directory -Path $hold -Force | Out-Null
Get-ChildItem 'C:\OC' -Force -ErrorAction SilentlyContinue | ForEach-Object {
    $target = Join-Path $hold ($_.Name + '.from-C-root')
    try {
        Move-Item -Path $_.FullName -Destination $target -Force -ErrorAction Stop
        Write-Output ("  moved " + $_.Name + " -> " + $target)
    } catch {
        Write-Output ("  could not move " + $_.Name + " : " + $_.Exception.Message)
    }
}
if (Test-Path 'C:\OC') {
    try {
        Remove-Item 'C:\OC' -Force -ErrorAction Stop
        Write-Output "  C:\OC removed"
    } catch {
        Write-Output ("  C:\OC still present: " + $_.Exception.Message)
    }
}

Write-Output ""
Write-Output "=== starting service ==="
Start-Service -Name $svc -ErrorAction SilentlyContinue
$deadline = (Get-Date).AddSeconds(45)
do {
    Start-Sleep -Seconds 3
    $st = (Get-Service -Name $svc -ErrorAction SilentlyContinue).Status
} while ($st -ne 'Running' -and (Get-Date) -lt $deadline)
Write-Output ("  state: " + $st)

Start-Sleep -Seconds 5
Write-Output ""
Write-Output "=== confirm ==="
Write-Output ("  C:\OC exists : " + (Test-Path 'C:\OC') + "   (must be False)")
Write-Output ("  C:\APPS\OC   : " + (Test-Path 'C:\APPS\OC'))
$d = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
     Where-Object { $_.CommandLine -match 'oc-keepalive-daemon' }
foreach ($p in $d) { Write-Output ("  daemon PID " + $p.ProcessId + "  " + $p.ExecutablePath) }
Write-Output "=== DONE ==="

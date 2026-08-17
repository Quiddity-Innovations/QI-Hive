# Phase 3i - find and repoint NSSM services that do NOT use the QI_ prefix.
#
# OC-Keepalive-Service was missed by every scan in this migration because both
# the inventory and the repoint script enumerated 'QI_*' only. It also runs its
# own nssm binary at C:\OC\nssm.exe rather than the standardised
# C:\QIH\engine\bin\nssm.exe.
#
# That is two separate problems:
#   - a live service still executing the old interpreter
#   - a QI naming-standard violation (CLAUDE.md: all QI NSSM services MUST be
#     prefixed QI_ and registered in QI_Service_Registry.md)
#
# This script fixes the first. The rename is flagged, not performed - renaming
# a service means delete + recreate, which is a decision for Renne.
#
# Pure ASCII only.
param([switch]$Apply)
$ErrorActionPreference = 'Continue'

$oldDir = 'C:\1-AI\APPS\PYTHON'
$newDir = 'C:\Program Files\Python311'
$fields = @('Application','AppDirectory','AppParameters','AppStdout','AppStderr')

Write-Output "=== every NSSM-hosted service on this machine ==="
$all = Get-CimInstance Win32_Service | Where-Object { $_.PathName -match 'nssm' }
Write-Output ("  total: " + @($all).Count)
$nonQi = $all | Where-Object { $_.Name -notlike 'QI_*' }
Write-Output ("  NOT following the QI_ convention: " + @($nonQi).Count)
foreach ($s in $nonQi) {
    Write-Output ("     " + $s.Name + "   [" + $s.State + "]   " + $s.PathName)
}

if (-not $nonQi) { Write-Output "  (none)"; Write-Output "=== DONE ==="; exit 0 }

Write-Output ""
Write-Output "=== inspecting their configuration ==="
foreach ($s in $nonQi) {
    # Use whichever nssm binary that service was registered with.
    $nssm = 'C:\QIH\engine\bin\nssm.exe'
    if ($s.PathName -match '^"?([A-Za-z]:\\[^"]*nssm\.exe)') { $nssm = $Matches[1] }
    if (-not (Test-Path $nssm)) { $nssm = 'C:\QIH\engine\bin\nssm.exe' }

    Write-Output ("  " + $s.Name + "   (nssm: " + $nssm + ")")
    foreach ($f in $fields) {
        $v = (& $nssm get $s.Name $f 2>$null) -join ''
        $v = ($v -replace "`0", '').Trim()
        if ($v) {
            $flag = if ($v -like "*$oldDir*") { '   <-- STALE' } else { '' }
            Write-Output ("     " + $f.PadRight(14) + " " + $v + $flag)
        }
    }
    Write-Output ""
}

Write-Output "=== repointing stale fields ==="
$changed = 0
foreach ($s in $nonQi) {
    $nssm = 'C:\QIH\engine\bin\nssm.exe'
    if ($s.PathName -match '^"?([A-Za-z]:\\[^"]*nssm\.exe)') { $nssm = $Matches[1] }
    if (-not (Test-Path $nssm)) { $nssm = 'C:\QIH\engine\bin\nssm.exe' }

    foreach ($f in $fields) {
        $v = (& $nssm get $s.Name $f 2>$null) -join ''
        $v = ($v -replace "`0", '').Trim()
        if ($v -and $v -like "*$oldDir*") {
            $new = $v.Replace($oldDir, $newDir)
            Write-Output ("  " + $s.Name + " . " + $f)
            Write-Output ("     old: " + $v)
            Write-Output ("     new: " + $new)
            if ($Apply) {
                & $nssm set $s.Name $f $new | Out-Null
                $changed++
            }
        }
    }
}

if (-not $Apply) {
    Write-Output ""
    Write-Output "DRY RUN - re-run with -Apply to write and restart."
    exit 0
}

Write-Output ("  fields changed: " + $changed)

Write-Output ""
Write-Output "=== restarting them ==="
foreach ($s in $nonQi) {
    if ($s.State -ne 'Running') {
        Write-Output ("  " + $s.Name + " was not running - left alone")
        continue
    }
    Restart-Service -Name $s.Name -Force -ErrorAction SilentlyContinue
    $deadline = (Get-Date).AddSeconds(45)
    do {
        Start-Sleep -Seconds 2
        $st = (Get-Service -Name $s.Name -ErrorAction SilentlyContinue).Status
    } while ($st -ne 'Running' -and (Get-Date) -lt $deadline)
    Write-Output ("  " + $s.Name + " -> " + $st)
}

Start-Sleep -Seconds 6
Write-Output ""
Write-Output "=== anything still pinning C:\1-AI? ==="
$left = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.ExecutablePath -like '*1-AI*' }
Write-Output ("  " + @($left).Count)
foreach ($p in $left) {
    $cl = $p.CommandLine
    if ($cl -and $cl.Length -gt 110) { $cl = $cl.Substring(0,110) + ' ...' }
    Write-Output ("   PID " + $p.ProcessId + "  " + $cl)
}

Write-Output ""
Write-Output "STANDARDS NOTE for Renne:"
foreach ($s in $nonQi) {
    Write-Output ("  " + $s.Name + " violates the QI_ prefix rule and is absent")
    Write-Output ("  from QI_Service_Registry.md. Suggested name: QI_OCKeepalive.")
    Write-Output ("  Renaming an NSSM service means remove + reinstall, so it is")
    Write-Output ("  left for you to decide rather than done automatically.")
}
Write-Output "=== DONE ==="

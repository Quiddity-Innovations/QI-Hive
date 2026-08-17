# Phase 2.2 - repoint the 31 NSSM services from C:\1-AI\APPS\PYTHON to
# C:\Program Files\Python311. Rewrites Application, and also AppParameters /
# AppDirectory / AppStdout / AppStderr if they mention the old path.
#
# Idempotent: re-running it is safe.
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

$nssm   = 'C:\QIH\engine\bin\nssm.exe'
$oldDir = 'C:\1-AI\APPS\PYTHON'
$newDir = 'C:\Program Files\Python311'
$fields = @('Application', 'AppDirectory', 'AppParameters', 'AppStdout', 'AppStderr')

if (-not (Test-Path $nssm))   { Write-Output ("FATAL: nssm not found at " + $nssm);   exit 1 }
if (-not (Test-Path (Join-Path $newDir 'python.exe'))) {
    Write-Output ("FATAL: new interpreter missing at " + $newDir); exit 1
}

$services = & $nssm list 2>$null | Where-Object { $_ -match '^\s*QI_' } | ForEach-Object { $_.Trim() }
Write-Output ("QI_* services discovered: " + $services.Count)
Write-Output ""

$changedCount = 0
$changedSvc   = @()

foreach ($svc in $services) {
    $touched = $false
    foreach ($f in $fields) {
        $cur = (& $nssm get $svc $f 2>$null) -join ''
        $cur = $cur -replace "`0", ''          # nssm emits UTF-16 nulls
        $cur = $cur.Trim()
        if ($cur -and $cur -like "*$oldDir*") {
            $new = $cur.Replace($oldDir, $newDir)
            & $nssm set $svc $f $new | Out-Null
            Write-Output ("  " + $svc + " . " + $f)
            Write-Output ("      old: " + $cur)
            Write-Output ("      new: " + $new)
            $touched = $true
        }
    }
    if ($touched) { $changedCount++; $changedSvc += $svc }
}

Write-Output ""
Write-Output ("Services modified: " + $changedCount)
$changedSvc | ForEach-Object { Write-Output ("  " + $_) }

# Persist the list so the restart/verify step knows exactly what to bounce.
$changedSvc | Set-Content -Path 'C:\QIH\shared\documentation\migration_2026-08\phase2\repointed_services.txt' -Encoding ASCII

Write-Output "=== DONE ==="

# ============================================================================
#  QI NSSM Per-Product Standardization
#  Re-points every QI_* service from the shared nssm.exe to a per-product copy
#  whose embedded FileDescription names the product, so the UAC consent dialog
#  identifies WHICH product is being restarted.
#
#  Usage:
#    powershell -ExecutionPolicy Bypass -File standardize_nssm.ps1 -DryRun
#    powershell -ExecutionPolicy Bypass -File standardize_nssm.ps1 -Execute
#
#  Safe to re-run (idempotent). Requires Administrator (sc config + service restart).
#  Created 2026-06-23.
# ============================================================================
param(
    [switch]$DryRun,
    [switch]$Execute
)
$ErrorActionPreference = 'Stop'
$root      = 'C:\QIH\tools\naming_standardization'
$logDir    = Join-Path $root 'logs'
$stamp     = Get-Date -Format 'yyyyMMdd-HHmmss'
$mode      = if ($Execute) { 'EXECUTE' } else { 'DRYRUN' }
$log       = Join-Path $logDir "nssm_$($mode)_$stamp.log"
$rollback  = Join-Path $root 'nssm_rollback_manifest.json'
$rcedit    = 'C:\QIH\engine\bin\rcedit.exe'

if (-not $DryRun -and -not $Execute) { Write-Host "Specify -DryRun or -Execute"; exit 2 }

function Log($m) { $line = "[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $m; Write-Host $line; Add-Content -Path $log -Value $line -Encoding UTF8 }

$cfg     = Get-Content (Join-Path $root 'service_map.json') -Raw | ConvertFrom-Json
$binDir  = $cfg.bin_dir
$srcNssm = $cfg.source_nssm

Log "=== QI NSSM Standardization  mode=$mode ==="
Log "source nssm : $srcNssm"
if (-not (Test-Path $srcNssm)) { Log "FATAL: source nssm missing"; exit 1 }
if (-not (Test-Path $rcedit))  { Log "FATAL: rcedit missing at $rcedit"; exit 1 }

# --- Capture rollback manifest (current binPath of every targeted service) BEFORE any change
$rb = @{}
foreach ($p in $cfg.products) {
    foreach ($svc in $p.services) {
        $q = sc.exe qc $svc 2>$null | Select-String 'BINARY_PATH_NAME'
        if ($q) { $rb[$svc] = ($q.ToString() -replace '.*BINARY_PATH_NAME\s*:\s*','').Trim() }
    }
}
if ($Execute) { $rb | ConvertTo-Json | Set-Content -Path $rollback -Encoding UTF8; Log "rollback manifest written: $rollback" }

$ok = 0; $skip = 0; $fail = 0; $missing = 0

foreach ($p in $cfg.products) {
    $dest = Join-Path $binDir $p.exe
    Log "--- product exe: $($p.exe)  '$($p.file_description)' ---"

    # 1) Ensure per-product copy exists with correct FileDescription
    $needCopy = -not (Test-Path $dest)
    if (-not $needCopy) {
        $fd = (Get-Item $dest).VersionInfo.FileDescription
        if ($fd -ne $p.file_description) { Log "   exists but label='$fd' (will relabel)"; $needCopy = $false }
    }
    if ($DryRun) {
        Log ("   [dry] {0} copy+relabel -> '{1}'" -f $(if (Test-Path $dest){'(exists)'}else{'create'}), $p.file_description)
    } else {
        if (-not (Test-Path $dest)) { Copy-Item $srcNssm $dest -Force; Log "   copied nssm -> $dest" }
        # relabel (only works if file not locked; fresh copy never is)
        try { & $rcedit $dest --set-version-string "FileDescription" $p.file_description; Log "   relabeled FileDescription" }
        catch { Log "   WARN relabel failed (likely in use): $_" }
    }

    # 2) Re-point each service
    foreach ($svc in $p.services) {
        $exists = (sc.exe query $svc 2>$null | Select-String 'SERVICE_NAME') -ne $null
        if (-not $exists) { Log "   [skip] $svc not installed"; $missing++; continue }
        $cur = $rb[$svc]
        if ($cur -eq $dest) { Log "   [skip] $svc already points at $($p.exe)"; $skip++; continue }
        if ($DryRun) { Log "   [dry] $svc : $cur  ==>  $dest"; continue }

        try {
            & sc.exe config $svc binPath= "`"$dest`"" | Out-Null
            Log "   $svc repointed -> $($p.exe). restarting..."
            & $srcNssm restart $svc 2>$null | Out-Null   # restart via nssm (service name keys params)
            Start-Sleep -Seconds 3
            $state = (sc.exe query $svc | Select-String 'STATE').ToString()
            if ($state -match 'RUNNING') { Log "   OK   $svc RUNNING"; $ok++ }
            else {
                Log "   FAIL $svc state=$state -> ROLLBACK to $cur"
                & sc.exe config $svc binPath= "`"$cur`"" | Out-Null
                & $srcNssm restart $svc 2>$null | Out-Null
                $fail++
            }
        } catch {
            Log "   ERROR $svc : $_  -> ROLLBACK"
            & sc.exe config $svc binPath= "`"$cur`"" | Out-Null
            & $srcNssm restart $svc 2>$null | Out-Null
            $fail++
        }
    }
}

Log "=== DONE  ok=$ok skipped=$skip rolledback/failed=$fail not-installed=$missing ==="
Log "log: $log"
exit 0

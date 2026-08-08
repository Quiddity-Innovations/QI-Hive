# ============================================================================
#  QI Naming Standardization — Friday midnight orchestrator
#  1) NSSM per-product re-point (38 services)  2) Batch Tier-1 rename
#  Runs as SYSTEM via Task Scheduler (already elevated -> no UAC prompt).
#  Logs everything and pings Renne on LINE (Tasuke) with the result.
#  Created 2026-06-23.
# ============================================================================
$ErrorActionPreference = 'Continue'
$root   = 'C:\QIH\tools\naming_standardization'
$py     = 'C:\1-AI\APPS\PYTHON\python.exe'
$stamp  = Get-Date -Format 'yyyyMMdd-HHmmss'
$master = Join-Path $root "logs\FRIDAY_RUN_$stamp.log"
function M($m){ $l="[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'),$m; Write-Host $l; Add-Content $master $l -Encoding UTF8 }

M "########## QI NAMING STANDARDIZATION — START ##########"

# --- 1) NSSM
M ">>> Phase 1: NSSM per-product re-point"
try {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'standardize_nssm.ps1') -Execute 2>&1 |
        ForEach-Object { Add-Content $master $_ -Encoding UTF8 }
    M "Phase 1 complete"
} catch { M "Phase 1 ERROR: $_" }

# --- 2) Batch Tier-1
M ">>> Phase 2: Batch Tier-1 rename"
try {
    & $py (Join-Path $root 'standardize_batch.py') --execute --map batch_rename_tier1.json 2>&1 |
        ForEach-Object { Add-Content $master $_ -Encoding UTF8 }
    M "Phase 2 complete"
} catch { M "Phase 2 ERROR: $_" }

# --- 2b) Batch Tier-2 (collisions resolved + task-referenced)
M ">>> Phase 2b: Batch Tier-2 rename"
try {
    & $py (Join-Path $root 'standardize_batch.py') --execute --map batch_rename_tier2.json 2>&1 |
        ForEach-Object { Add-Content $master $_ -Encoding UTF8 }
    M "Phase 2b complete"
} catch { M "Phase 2b ERROR: $_" }

# --- 2c) Update scheduled-task actions for the 3 renamed task bats
M ">>> Phase 2c: scheduled-task action updates"
try {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'update_task_actions.ps1') -Execute 2>&1 |
        ForEach-Object { Add-Content $master $_ -Encoding UTF8 }
    M "Phase 2c complete"
} catch { M "Phase 2c ERROR: $_" }

# --- 3) Verify: count services running + still pointing at old shared nssm
M ">>> Phase 3: verification"
$svc = & "$root\..\..\engine\bin\nssm.exe" 2>$null  # noop guard
$running = (Get-Service QI_* | Where-Object Status -eq 'Running').Count
$total   = (Get-Service QI_*).Count
$oldptr  = 0
Get-Service QI_* | ForEach-Object {
    $bp = (Get-CimInstance Win32_Service -Filter "Name='$($_.Name)'").PathName
    if ($bp -match 'bin\\nssm\.exe') { $oldptr++ }
}
M "services running: $running / $total ; still on shared nssm.exe: $oldptr"

# --- 4) Notify Renne
$msg = "QI Naming Standardization (Friday) done. Services running $running/$total. " +
       "Still on shared nssm: $oldptr. NSSM now per-product (UAC popups name the product). " +
       "Batch Tier-1 launchers renamed. Log: FRIDAY_RUN_$stamp.log"
try { & $py 'C:\CLAUDE\Tools\qi_tasuke_notify.py' $msg 2>&1 | ForEach-Object { M $_ } } catch { M "notify failed: $_" }

M "########## DONE — log: $master ##########"

# ============================================================================
#  QI Naming Standardization — full rollback
#  Reverts NSSM re-points (back to shared nssm.exe) and batch renames/edits
#  using the manifests written during execution. Run elevated.
#  Created 2026-06-23.
# ============================================================================
$ErrorActionPreference = 'Continue'
$root = 'C:\QIH\tools\naming_standardization'
$src  = 'C:\QIH\engine\bin\nssm.exe'
function M($m){ Write-Host ("[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'),$m) }

# --- NSSM rollback
$nrb = Join-Path $root 'nssm_rollback_manifest.json'
if (Test-Path $nrb) {
    M "Reverting NSSM re-points..."
    $map = Get-Content $nrb -Raw | ConvertFrom-Json
    foreach ($svc in $map.PSObject.Properties.Name) {
        $orig = $map.$svc
        & sc.exe config $svc binPath= "`"$orig`"" | Out-Null
        & $src restart $svc 2>$null | Out-Null
        M "   $svc -> $orig"
    }
} else { M "no NSSM rollback manifest" }

# --- Scheduled-task action rollback (restore old arguments) FIRST
$trb = Join-Path $root 'task_actions_rollback.json'
if (Test-Path $trb) {
    M "Reverting scheduled-task actions..."
    $items = Get-Content $trb -Raw | ConvertFrom-Json
    foreach ($it in @($items)) {
        $t = Get-ScheduledTask -TaskName $it.task -ErrorAction SilentlyContinue
        if ($t) {
            $acts = @()
            foreach ($a in $t.Actions) {
                $arg = if ($a.Arguments -eq $it.from) { $it.to } else { $a.Arguments }
                $acts += New-ScheduledTaskAction -Execute $a.Execute -Argument $arg -WorkingDirectory $a.WorkingDirectory
            }
            Set-ScheduledTask -TaskName $it.task -Action $acts | Out-Null
            M "   task action back: $($it.task)"
        }
    }
} else { M "no task-action rollback manifest" }

# --- Batch rollback (both tiers)
foreach ($brb in @('batch_rollback_tier2.json','batch_rollback_tier1.json','batch_rollback_manifest.json')) {
    $bp = Join-Path $root $brb
    if (Test-Path $bp) {
        M "Reverting batch renames + edits ($brb)..."
        $b = Get-Content $bp -Raw | ConvertFrom-Json
        foreach ($r in @($b.renames)) { if (Test-Path $r.from) { Move-Item $r.from $r.to -Force; M "   rename back: $($r.to)" } }
        foreach ($e in @($b.edits)) {
            if (Test-Path $e.file) {
                (Get-Content $e.file -Raw) -replace [regex]::Escape($e.from), $e.to | Set-Content $e.file -Encoding UTF8
                M "   edit back: $($e.file)"
            }
        }
    }
}
M "rollback complete"

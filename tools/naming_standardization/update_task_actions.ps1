# ============================================================================
#  Update scheduled-task actions to reference renamed Tier-2 batch files.
#  Reads task_updates from batch_rename_tier2.json. Run as SYSTEM (Saturday)
#  or elevated. -DryRun shows the change; -Execute applies it + writes rollback.
#  Created 2026-06-23.
# ============================================================================
param([switch]$DryRun, [switch]$Execute)
$ErrorActionPreference = 'Continue'
$root = 'C:\QIH\tools\naming_standardization'
$map  = Get-Content (Join-Path $root 'batch_rename_tier2.json') -Raw | ConvertFrom-Json
$rbpath = Join-Path $root 'task_actions_rollback.json'
if (-not $DryRun -and -not $Execute) { Write-Host "specify -DryRun or -Execute"; exit 2 }
$rb = @()

foreach ($u in $map.task_updates) {
    $old = [IO.Path]::GetFileName($u.path)
    $new = $u.new
    foreach ($tn in $u.tasks) {
        $t = Get-ScheduledTask -TaskName $tn -ErrorAction SilentlyContinue
        if (-not $t) { Write-Host "[skip] task not found: $tn"; continue }
        $newActions = @()
        $changed = $false
        foreach ($act in $t.Actions) {
            $args0 = $act.Arguments
            $doSwap = ($args0 -and $args0 -match [regex]::Escape($old))
            $argFinal = if ($doSwap) { $args0 -replace [regex]::Escape($old), $new } else { $args0 }
            $p = @{ Execute = $act.Execute }
            if ($argFinal) { $p.Argument = $argFinal }
            if ($act.WorkingDirectory) { $p.WorkingDirectory = $act.WorkingDirectory }
            $newActions += New-ScheduledTaskAction @p
            if ($doSwap) {
                $changed = $true
                Write-Host "$tn :`n   OLD: $args0`n   NEW: $argFinal"
                $rb += @{ task = $tn; from = $argFinal; to = $args0 }
            }
        }
        if ($changed -and $Execute) {
            Set-ScheduledTask -TaskName $tn -Action $newActions | Out-Null
            Write-Host "   APPLIED to $tn"
        } elseif (-not $changed) {
            Write-Host "[skip] $tn already references $new (or not $old)"
        }
    }
}
if ($Execute) { $rb | ConvertTo-Json | Set-Content $rbpath -Encoding UTF8; Write-Host "rollback: $rbpath" }

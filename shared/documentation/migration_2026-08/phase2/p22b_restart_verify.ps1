# Phase 2.2b - restart each repointed service and prove it came back.
#
# Restarts are sequential, not parallel: a parallel bounce of 28 services makes
# a failure impossible to attribute, and several of these depend on each other
# (Gate, Elevate, BrainAPI are infrastructure for the rest).
#
# Services that were already stopped before the migration are NOT started -
# starting something that was deliberately off would be a change of state, not
# a verification.
#
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

$listFile = 'C:\QIH\shared\documentation\migration_2026-08\phase2\repointed_services.txt'
$csv      = 'C:\QIH\shared\documentation\migration_2026-08\phase2\rollback\services_before.csv'
$newExe   = 'C:\Program Files\Python311\python.exe'

if (-not (Test-Path $listFile)) { Write-Output "FATAL: repointed list missing"; exit 1 }
$repointed = Get-Content $listFile | Where-Object { $_.Trim() }

# Which of them were running before the migration started?
$before = @{}
Import-Csv $csv | ForEach-Object { $before[$_.Service] = $_.Status }

# Infrastructure first, then everything else.
$priority = @('QI_Elevate','QI_Gate','QI_BrainAPI','QI_HiveIngest','QI_HiveApply')
$ordered  = @()
$ordered += $priority | Where-Object { $repointed -contains $_ }
$ordered += $repointed | Where-Object { $priority -notcontains $_ }

$results = @()

foreach ($svc in $ordered) {
    $wasRunning = ($before[$svc] -eq 'Running')
    if (-not $wasRunning) {
        Write-Output ("SKIP  " + $svc.PadRight(24) + " was stopped before migration - leaving stopped")
        $results += [pscustomobject]@{ Service=$svc; Before='Stopped'; After='Stopped'; Verdict='skipped' }
        continue
    }

    Write-Output ("BOUNCE " + $svc)
    Restart-Service -Name $svc -Force -ErrorAction SilentlyContinue

    $deadline = (Get-Date).AddSeconds(45)
    $state = ''
    do {
        Start-Sleep -Seconds 2
        $state = (Get-Service -Name $svc -ErrorAction SilentlyContinue).Status
    } while ($state -ne 'Running' -and (Get-Date) -lt $deadline)

    if ($state -eq 'Running') {
        # Confirm it is actually running the NEW interpreter, not a stale process.
        $wmi = Get-CimInstance Win32_Service -Filter ("Name='" + $svc + "'") -ErrorAction SilentlyContinue
        $procId = $wmi.ProcessId
        $child = Get-CimInstance Win32_Process -Filter ("ParentProcessId=" + $procId) -ErrorAction SilentlyContinue |
                 Select-Object -First 1
        $exe = if ($child) { $child.ExecutablePath } else { '(no child proc)' }
        $ok = if ($exe -like '*Program Files\Python311*') { 'NEW' }
              elseif ($exe -like '*1-AI*') { 'STILL-OLD' }
              else { '?' }
        Write-Output ("   -> Running   interpreter=" + $ok + "  " + $exe)
        $results += [pscustomobject]@{ Service=$svc; Before='Running'; After='Running'; Verdict=$ok }
    } else {
        Write-Output ("   -> FAILED   state=" + $state)
        $results += [pscustomobject]@{ Service=$svc; Before='Running'; After=$state; Verdict='FAILED' }
    }
}

Write-Output ""
Write-Output "================ SUMMARY ================"
$running = @($results | Where-Object { $_.After -eq 'Running' }).Count
$failed  = @($results | Where-Object { $_.Verdict -eq 'FAILED' })
$stale   = @($results | Where-Object { $_.Verdict -eq 'STILL-OLD' })
Write-Output ("  running after bounce : " + $running)
Write-Output ("  skipped (were off)   : " + @($results | Where-Object { $_.Verdict -eq 'skipped' }).Count)
Write-Output ("  FAILED               : " + $failed.Count)
foreach ($f in $failed) { Write-Output ("     " + $f.Service + " -> " + $f.After) }
Write-Output ("  still on old python  : " + $stale.Count)
foreach ($s in $stale) { Write-Output ("     " + $s.Service) }

Write-Output ""
Write-Output "=== Whole-estate view ==="
Get-Service -Name 'QI_*' | Group-Object Status | ForEach-Object {
    Write-Output ("  " + $_.Name + ": " + $_.Count)
}
$down = Get-Service -Name 'QI_*' | Where-Object { $_.Status -ne 'Running' } | Select-Object -ExpandProperty Name
Write-Output ("  not running: " + ($down -join ', '))

Write-Output ""
Write-Output "=== Any process anywhere still executing the old interpreter? ==="
$old = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
       Where-Object { $_.ExecutablePath -like '*1-AI\APPS\PYTHON*' }
if ($old) {
    foreach ($o in $old) { Write-Output ("  PID " + $o.ProcessId + "  " + $o.ExecutablePath) }
} else {
    Write-Output "  none"
}
Write-Output "=== DONE ==="

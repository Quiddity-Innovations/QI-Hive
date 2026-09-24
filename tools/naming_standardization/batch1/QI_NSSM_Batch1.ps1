<#
QI NSSM Batch 1 - every service onto its own app's NSSM copy (Renne, 2026-09-24)

  * Binary:  each service -> the <App>_NSSM.exe in batch1_plan.json
             (apps: in the app's own folder; Hive: C:\QIH\engine\bin).
  * Display: display name = service name (drops "QI - " / "QI " forms).
  * Depends: removes app -> QI_BrainAPI boot dependencies (NEXUS, Maia, Naya);
             no app code uses the Brain. Hive -> Hive dependencies stay.
  * Restart: only services RUNNING at execution time; waits for RUNNING, and
             rolls that one service back on failure. Never aborts the batch.
  * No service is renamed here (that is Batch 2+, one app per wave).

  Dry run (no admin, changes nothing):   powershell -File QI_NSSM_Batch1.ps1
  Execute (admin):                       powershell -File QI_NSSM_Batch1.ps1 -Execute
  Rollback (admin):                      powershell -File QI_NSSM_Batch1.ps1 -Rollback
#>
param([switch]$Execute, [switch]$Rollback)
$ErrorActionPreference = 'Continue'
$here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$ts     = Get-Date -Format 'yyyyMMdd-HHmmss'
$mode   = if ($Rollback) { 'ROLLBACK' } elseif ($Execute) { 'EXECUTE' } else { 'DRYRUN' }
New-Item -ItemType Directory -Force -Path "$here\logs" | Out-Null
$log    = "$here\logs\batch1_${mode}_$ts.log"
$result = "$here\batch1_result.json"
$DROP_BRAIN_DEP = @('QI_NEXUS', 'QI_MaiaBot', 'QI_NayaBot')

# Log file may be held open by a viewer (tail -f locked it on 2026-09-24); never let that spam or stop the run.
function Log($m) { $line = "[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $m; Write-Host $line
    try { [IO.File]::AppendAllText($log, $line + "`r`n", [Text.Encoding]::UTF8) } catch { } }
function BinPath($svc) { (Get-CimInstance Win32_Service -Filter "Name='$svc'").PathName.Trim('"') }
function State($svc)   { (Get-Service -Name $svc -ErrorAction SilentlyContinue).Status }
function WaitRunning($svc, $sec) {
    $end = (Get-Date).AddSeconds($sec)
    while ((Get-Date) -lt $end) { if ((State $svc) -eq 'Running') { return $true }; Start-Sleep -Seconds 2 }
    return $false
}
function Deps($svc) { (Get-Service -Name $svc).ServicesDependedOn | ForEach-Object Name }
function SetDeps($svc, $list) {
    $arg = if ($list -and $list.Count) { ($list -join '/') } else { '/' }
    & sc.exe config $svc depend= $arg | Out-Null
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (($Execute -or $Rollback) -and -not $isAdmin) { Log 'FATAL: run as Administrator (use QI_NSSM_Batch1_RUN.bat)'; exit 1 }
Log "=== QI NSSM Batch 1  mode=$mode ==="

# ---------------------------------------------------------------- ROLLBACK
if ($Rollback) {
    $man = Get-ChildItem "$here\batch1_rollback_*.json" | Sort-Object Name | Select-Object -Last 1
    if (-not $man) { Log 'FATAL: no rollback manifest found'; exit 1 }
    Log "manifest: $($man.FullName)"
    foreach ($r in (Get-Content $man.FullName -Raw | ConvertFrom-Json)) {
        & sc.exe config $r.name binPath= "`"$($r.bin)`"" | Out-Null
        & sc.exe config $r.name DisplayName= "$($r.display)" | Out-Null
        SetDeps $r.name @($r.depends)
        if ($r.was_running -and (State $r.name) -eq 'Running') {
            Restart-Service -Name $r.name -Force -ErrorAction SilentlyContinue
            if (WaitRunning $r.name 45) { Log "  OK   $($r.name) restored + running" } else { Log "  FAIL $($r.name) restored but NOT running" }
        } else { Log "  OK   $($r.name) restored" }
    }
    foreach ($d in (Get-ChildItem "$here\batch1_removed_*.cmd" -ErrorAction SilentlyContinue)) {
        $svc = $d.BaseName -replace '^batch1_removed_', ''
        if (-not (Get-Service -Name $svc -ErrorAction SilentlyContinue)) {
            & cmd.exe /c "`"$($d.FullName)`"" | Out-Null
            Log ("  recreate {0}: {1}" -f $svc, [bool](Get-Service -Name $svc -ErrorAction SilentlyContinue))
        }
    }
    Log '=== rollback done ==='; exit 0
}

# ---------------------------------------------------------------- PLAN + PRE-CHECKS
$plan = Get-Content "$here\batch1_plan.json" -Raw | ConvertFrom-Json
$work = @($plan | Where-Object action -eq 'repoint')
$bad = 0
foreach ($r in $work) {
    if (-not (Get-Service -Name $r.name -ErrorAction SilentlyContinue)) { Log "  PRECHECK: $($r.name) not installed - will skip"; continue }
    if (-not (Test-Path -LiteralPath $r.target_bin)) { Log "  PRECHECK FAIL: missing $($r.target_bin)"; $bad++; continue }
    $fd = (Get-Item -LiteralPath $r.target_bin).VersionInfo.FileDescription
    if ($fd -notlike "$($r.owner) Service Manager (QI)") { Log "  PRECHECK FAIL: $($r.target_bin) label '$fd'"; $bad++ }
}
if ($bad) { Log "FATAL: $bad pre-check failure(s) - nothing changed. Re-run build_batch1_plan.py"; exit 1 }
Log "pre-checks OK: $($work.Count) services"

# snapshot live state (restart decision uses THIS, not the plan)
$before = @{}
foreach ($r in $work) {
    $s = Get-Service -Name $r.name -ErrorAction SilentlyContinue
    if (-not $s) { continue }
    $before[$r.name] = [pscustomobject]@{
        name = $r.name; bin = (BinPath $r.name); display = $s.DisplayName
        depends = @(Deps $r.name); was_running = ($s.Status -eq 'Running') }
}
if ($Execute) {
    $manPath = "$here\batch1_rollback_$ts.json"
    $before.Values | ConvertTo-Json -Depth 4 | Set-Content -Path $manPath -Encoding UTF8
    Log "rollback manifest: $manPath"
}

# ---------------------------------------------------------------- APPLY
$out = @()
foreach ($r in $work) {
    $b = $before[$r.name]; if (-not $b) { continue }
    $svc = $r.name
    $newDeps = @($b.depends)
    if ($DROP_BRAIN_DEP -contains $svc) { $newDeps = @($b.depends | Where-Object { $_ -ne 'QI_BrainAPI' }) }
    $binChange  = $b.bin -ne $r.target_bin
    $dispChange = $b.display -ne $r.target_display
    $depChange  = (@($b.depends) -join ',') -ne ($newDeps -join ',')
    $restart    = $b.was_running -and ($binChange) -and -not $r.flag
    $what = @(); if ($binChange) { $what += 'binary' }; if ($dispChange) { $what += 'display' }; if ($depChange) { $what += 'drop-Brain-dependency' }
    if (-not $what) { Log "  --   $svc already done"; $out += [pscustomobject]@{ name=$svc; status='unchanged' }; continue }
    Log ("  {0,-24} {1}{2}" -f $svc, ($what -join ' + '), $(if ($restart) { ' + restart' } else { '' }))
    if (-not $Execute) { $out += [pscustomobject]@{ name=$svc; status='dry'; change=($what -join '+'); restart=$restart }; continue }

    if ($binChange)  { & sc.exe config $svc binPath= "`"$($r.target_bin)`"" | Out-Null }
    if ($dispChange) { & sc.exe config $svc DisplayName= "$($r.target_display)" | Out-Null }
    if ($depChange)  { SetDeps $svc $newDeps }
    $okBin = (BinPath $svc) -eq $r.target_bin -or -not $binChange
    if (-not $okBin) { Log "     FAIL sc config did not take - rolling back"; }

    $running = $true
    if ($okBin -and $restart) {
        Restart-Service -Name $svc -Force -ErrorAction SilentlyContinue
        $running = WaitRunning $svc 60
    }
    if ($okBin -and $running) {
        Log "     OK"
        $out += [pscustomobject]@{ name=$svc; status='ok'; change=($what -join '+'); restarted=$restart }
    } else {
        Log "     FAIL - rolling back $svc"
        & sc.exe config $svc binPath= "`"$($b.bin)`"" | Out-Null
        & sc.exe config $svc DisplayName= "$($b.display)" | Out-Null
        SetDeps $svc @($b.depends)
        if ($b.was_running) { Start-Service -Name $svc -ErrorAction SilentlyContinue; $back = WaitRunning $svc 60 } else { $back = $true }
        Log ("     rollback {0}" -f $(if ($back) { 'OK' } else { 'DONE BUT SERVICE NOT RUNNING - CHECK' }))
        $out += [pscustomobject]@{ name=$svc; status='rolled_back'; running_after=$back }
    }
    # a restart with -Force stops dependents; bring back any that were running
    foreach ($d in (Get-Service -Name $svc).DependentServices) {
        if ($before[$d.Name].was_running -and (State $d.Name) -ne 'Running') {
            Start-Service -Name $d.Name -ErrorAction SilentlyContinue
            Log ("     dependent {0} restarted: {1}" -f $d.Name, (WaitRunning $d.Name 60))
        }
    }
}

# ---------------------------------------------------------------- REMOVE retired services
# Renne 2026-09-24: QI_MaiaDemoTunnel retired 2026-06-20 (maia-demo now on QI_MaiaTunnel),
# Disabled since. Removed only if still Stopped + Disabled and its config was saved.
$REMOVE = @('QI_MaiaDemoTunnel')
foreach ($svc in $REMOVE) {
    $s = Get-CimInstance Win32_Service -Filter "Name='$svc'"
    if (-not $s) { Log "  --   $svc already removed"; continue }
    if ($s.State -ne 'Stopped' -or $s.StartMode -ne 'Disabled') {
        Log "  SKIP remove $svc - it is $($s.State)/$($s.StartMode), expected Stopped/Disabled"; continue }
    Log "  $svc remove (config saved first for rollback)"
    if (-not $Execute) { continue }
    $dump = "$here\batch1_removed_$svc.cmd"
    $reg  = "$here\batch1_removed_$svc.reg"
    & $s.PathName.Trim('"') dump $svc 2>$null | Set-Content -Path $dump -Encoding ASCII
    & reg.exe export "HKLM\SYSTEM\CurrentControlSet\Services\$svc" $reg /y | Out-Null
    $saved = (Test-Path $dump) -and ((Get-Content $dump -Raw) -match ' install ') -and (Test-Path $reg)
    if (-not $saved) { Log "     SKIP - could not save config, $svc NOT removed"; continue }
    & sc.exe delete $svc | Out-Null
    Start-Sleep -Seconds 2
    if (Get-Service -Name $svc -ErrorAction SilentlyContinue) { Log "     WARN - still listed (Windows removes it after the Services window closes)" }
    else { Log "     OK removed. Recreate: $dump" }
}

# ---------------------------------------------------------------- VERIFY
if ($Execute) {
    Log '>>> final pass: every service that was running must be running'
    foreach ($b in $before.Values) {
        if ($b.was_running -and (State $b.name) -ne 'Running') {
            Start-Service -Name $b.name -ErrorAction SilentlyContinue
            Log ("  restart {0}: {1}" -f $b.name, (WaitRunning $b.name 60))
        }
    }
}
$notRunning = @($before.Values | Where-Object { $_.was_running -and (State $_.name) -ne 'Running' } | ForEach-Object name)
$onShared   = @(Get-CimInstance Win32_Service | Where-Object { $_.Name -like 'QI_*' -and $_.PathName -match 'C:\\QIH\\engine\\bin\\nssm\.exe' } | ForEach-Object Name)
$summary = [pscustomobject]@{
    mode = $mode; when = (Get-Date).ToString('s'); log = $log
    ok = @($out | Where-Object status -eq 'ok').Count
    rolled_back = @($out | Where-Object status -eq 'rolled_back' | ForEach-Object name)
    was_running_now_not = $notRunning
    still_on_shared_nssm = $onShared
    services = $out }
if ($Execute) { $summary | ConvertTo-Json -Depth 4 | Set-Content -Path $result -Encoding UTF8 }
Log ("=== {0}: ok={1}  rolled_back={2}  was-running-now-down={3}  still-on-shared-nssm={4} ===" -f `
     $mode, $summary.ok, $summary.rolled_back.Count, $notRunning.Count, $onShared.Count)
if ($notRunning.Count) { Log ("DOWN: " + ($notRunning -join ', ')) }
if ($summary.rolled_back.Count) { Log ("ROLLED BACK: " + ($summary.rolled_back -join ', ')) }

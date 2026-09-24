<#
QI rename wave 1 - NEXUS (Renne, 2026-09-24)

  QI_NEXUS       -> QI_NEXUS_Server
  QI_NEXUSTunnel -> QI_NEXUS_Tunnel
  QI_NexusMCP    -> QI_NEXUS_MCP

Windows can't rename a service, so each one is rebuilt from its own full NSSM
config (nssm dump) under the new name, with the same binary, parameters, logs,
account, start mode and permissions. apply_refs.py updates the 42 files that
use the names in the same run. Any failure puts everything back as it was.

  Dry run (no admin):  powershell -File QI_Rename_NEXUS.ps1
  Execute (admin):     powershell -File QI_Rename_NEXUS.ps1 -Execute
  Rollback (admin):    powershell -File QI_Rename_NEXUS.ps1 -Rollback
Service state is read with sc.exe only: Get-Service keeps a handle open, and an
open handle leaves a removed service "marked for deletion", which would block
recreating the old name in a rollback.
#>
param([switch]$Execute, [switch]$Rollback)
$ErrorActionPreference = 'Continue'
$here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$NSSM   = 'C:\APPS\NEXUS\NEXUS_NSSM.exe'
$PY     = 'C:\Program Files\Python311\python.exe'
$REFS   = Join-Path $here 'apply_refs.py'
$MAP    = [ordered]@{ 'QI_NEXUS' = 'QI_NEXUS_Server'; 'QI_NEXUSTunnel' = 'QI_NEXUS_Tunnel'; 'QI_NexusMCP' = 'QI_NEXUS_MCP' }
$ts     = Get-Date -Format 'yyyyMMdd-HHmmss'
$mode   = if ($Rollback) { 'ROLLBACK' } elseif ($Execute) { 'EXECUTE' } else { 'DRYRUN' }
New-Item -ItemType Directory -Force -Path "$here\logs" | Out-Null
$log    = "$here\logs\rename_nexus_${mode}_$ts.log"

function Log($m) { $line = "[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $m; Write-Host $line
    try { [IO.File]::AppendAllText($log, $line + "`r`n", [Text.Encoding]::UTF8) } catch { } }
function Exists($s) { & sc.exe query $s *> $null; return ($LASTEXITCODE -eq 0) }
function IsRunning($s) { ((& sc.exe query $s) -join ' ') -match 'RUNNING' }
function WaitState($s, $want, $sec) {
    $end = (Get-Date).AddSeconds($sec)
    while ((Get-Date) -lt $end) { if (((& sc.exe query $s) -join ' ') -match $want) { return $true }; Start-Sleep 2 }
    return $false }
function NGet($s, $k) { ((& $NSSM get $s $k 2>$null) -join "`n").Replace("`0", '').Trim() }
function RenameTokens($text) {
    [regex]::Replace($text, '(?<![A-Za-z0-9_])(QI_NEXUSTunnel|QI_NexusMCP|QI_NEXUS)(?![A-Za-z0-9_])', { param($m) $MAP[$m.Groups[1].Value] }) }
function PortOpen($p) { try { $c = New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1', $p); $c.Close(); $true } catch { $false } }
function Health {
    $end = (Get-Date).AddSeconds(120)
    while ((Get-Date) -lt $end) {
        try { if ((Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 'http://127.0.0.1:8010/health').StatusCode -eq 200) { return $true } } catch { }
        Start-Sleep 3 }
    return $false }

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (($Execute -or $Rollback) -and -not $isAdmin) { Log 'FATAL: run as Administrator (use QI_Rename_NEXUS_RUN.bat)'; exit 1 }
Log "=== QI rename wave 1 - NEXUS  mode=$mode ==="

# ------------------------------------------------------------------ ROLLBACK (shared by -Rollback and failures)
function Restore-All($run) {
    Log ">>> ROLLBACK from $run"
    $state = Get-Content "$run\state.json" -Raw | ConvertFrom-Json
    foreach ($s in $state) {
        if (Exists $s.new) { & sc.exe stop $s.new *> $null; WaitState $s.new 'STOPPED' 30 | Out-Null; & $NSSM remove $s.new confirm *> $null; Log "  removed $($s.new)" }
    }
    Start-Sleep 3
    foreach ($s in $state) {
        if (-not (Exists $s.old)) {
            for ($i = 0; $i -lt 10 -and -not (Exists $s.old); $i++) { & cmd.exe /c "`"$run\old_$($s.old).cmd`"" *> $null; if (-not (Exists $s.old)) { Start-Sleep 3 } }
            if (Exists $s.old) { & sc.exe sdset $s.old $s.sddl *> $null; Log "  recreated $($s.old)" } else { Log "  !! could not recreate $($s.old) - run $run\old_$($s.old).cmd as admin (or reg import the .reg + reboot)" }
        }
    }
    if (Test-Path "$run\files") { & $PY $REFS --revert --backup "$run\files" | ForEach-Object { Log "  $_" } }
    foreach ($s in $state) { if ($s.was_running) { & sc.exe start $s.old *> $null; Log ("  start {0}: {1}" -f $s.old, (WaitState $s.old 'RUNNING' 60)) } }
    Log '=== rollback done ==='
}
if ($Rollback) {
    $run = Get-ChildItem "$here\run_*" -Directory | Sort-Object Name | Select-Object -Last 1
    if (-not $run) { Log 'FATAL: no run_* folder'; exit 1 }
    Restore-All $run.FullName; exit 0
}

# ------------------------------------------------------------------ PRE-CHECKS
$bad = 0
if (-not (Test-Path $NSSM)) { Log "FATAL: $NSSM missing"; $bad++ }
if (-not (Test-Path $PY))   { Log "FATAL: $PY missing"; $bad++ }
if (Get-Process mmc -ErrorAction SilentlyContinue) {
    if ($Execute) { Log 'FATAL: close the Windows "Services" window (and any other mmc console) first - it blocks service removal'; $bad++ }
    else { Log 'WARN: a Windows management console (mmc.exe, e.g. Services) is open - close it before the real run' } }
$todo = @()
foreach ($old in $MAP.Keys) {
    $new = $MAP[$old]
    if ((Exists $new) -and -not (Exists $old)) { Log "  --  $old already renamed to $new"; continue }
    if (Exists $new) { Log "FATAL: both $old and $new exist - resolve by hand"; $bad++; continue }
    if (-not (Exists $old)) { Log "FATAL: $old not installed"; $bad++; continue }
    $bin = ((& sc.exe qc $old) -join "`n") -replace '(?s).*BINARY_PATH_NAME\s*:\s*"?([^"\r\n]+)"?.*', '$1'
    if ($bin.Trim() -ne $NSSM) { Log "FATAL: $old runs on '$bin', expected $NSSM (Batch 1)"; $bad++ }
    $todo += [pscustomobject]@{ old = $old; new = $new; was_running = (IsRunning $old) }
    Log ("  {0,-16} -> {1,-16} running={2}" -f $old, $new, (IsRunning $old))
}
if ($bad) { Log "FATAL: $bad pre-check failure(s) - nothing changed"; exit 1 }
if (-not $todo) { Log 'nothing to do'; exit 0 }
Log '  references (dry run):'
& $PY $REFS --dry-run | Select-Object -Last 1 | ForEach-Object { Log "    $_" }
if ($LASTEXITCODE -ne 0) { Log 'FATAL: apply_refs.py dry run failed - nothing changed'; exit 1 }
if (-not $Execute) { Log '=== DRYRUN ok - nothing changed ==='; exit 0 }

# ------------------------------------------------------------------ EXECUTE
$run = "$here\run_$ts"; New-Item -ItemType Directory -Force -Path $run | Out-Null
foreach ($t in $todo) {
    $dump = (& $NSSM dump $t.old 2>$null) -join "`r`n"
    if ($dump -notmatch ' install ') { Log "FATAL: nssm dump of $($t.old) failed - nothing changed"; exit 1 }
    Set-Content -Path "$run\old_$($t.old).cmd" -Value $dump -Encoding ASCII
    & reg.exe export "HKLM\SYSTEM\CurrentControlSet\Services\$($t.old)" "$run\old_$($t.old).reg" /y | Out-Null
    $newDump = (RenameTokens $dump) + "`r`n`"$NSSM`" set $($t.new) DisplayName $($t.new)"
    Set-Content -Path "$run\new_$($t.new).cmd" -Value $newDump -Encoding ASCII
    $t | Add-Member sddl (((& sc.exe sdshow $t.old) -join '').Trim())
    $t | Add-Member app (NGet $t.old 'Application')
    $t | Add-Member params (RenameTokens (NGet $t.old 'AppParameters'))
    $t | Add-Member dir (NGet $t.old 'AppDirectory')
}
$todo | ConvertTo-Json -Depth 3 | Set-Content -Path "$run\state.json" -Encoding UTF8
Log "saved configs + state: $run"

# stop: tunnel and MCP first, server last
foreach ($t in ($todo | Sort-Object { $_.old -eq 'QI_NEXUS' })) {
    if (IsRunning $t.old) { & sc.exe stop $t.old *> $null; Log ("  stop {0}: {1}" -f $t.old, (WaitState $t.old 'STOPPED' 60)) }
}
$fail = $false
foreach ($t in $todo) {
    & $NSSM remove $t.old confirm *> $null
    & cmd.exe /c "`"$run\new_$($t.new).cmd`"" *> $null
    if (-not (Exists $t.new)) { Log "  FAIL creating $($t.new)"; $fail = $true; break }
    & sc.exe sdset $t.new $t.sddl *> $null
    $ok = ((NGet $t.new 'Application') -eq $t.app) -and ((NGet $t.new 'AppDirectory') -eq $t.dir) -and ((NGet $t.new 'AppParameters') -eq $t.params)
    if (-not $ok) { Log "  FAIL $($t.new) config differs from $($t.old)"; $fail = $true; break }
    Log "  OK  $($t.old) -> $($t.new) (config identical)"
}
if (-not $fail) {
    & $PY $REFS --apply --backup "$run\files" | Select-Object -Last 1 | ForEach-Object { Log "  refs: $_" }
    if ($LASTEXITCODE -ne 0) { Log '  FAIL reference rewrite'; $fail = $true }
}
if (-not $fail) {
    foreach ($t in ($todo | Sort-Object { $_.old -ne 'QI_NEXUS' })) {
        if ($t.was_running) { & sc.exe start $t.new *> $null; $r = WaitState $t.new 'RUNNING' 60; Log ("  start {0}: {1}" -f $t.new, $r); if (-not $r) { $fail = $true } }
    }
}
if (-not $fail -and ($todo | Where-Object { $_.old -eq 'QI_NEXUS' -and $_.was_running })) {
    $h = Health; Log "  NEXUS /health: $h"; if (-not $h) { $fail = $true }
}
if (-not $fail -and ($todo | Where-Object { $_.old -eq 'QI_NexusMCP' -and $_.was_running })) {
    Start-Sleep 5; $p = PortOpen 8310; Log "  NEXUS MCP :8310 listening: $p"; if (-not $p) { $fail = $true }
}
if ($fail) { Restore-All $run; Log '=== EXECUTE FAILED - everything restored ==='; exit 1 }

@{ when = (Get-Date).ToString('s'); run = $run; renamed = @($todo | ForEach-Object { "$($_.old) -> $($_.new)" }) } |
    ConvertTo-Json | Set-Content -Path "$here\rename_nexus_result.json" -Encoding UTF8
Log '=== EXECUTE ok: NEXUS services renamed, references updated, NEXUS healthy ==='

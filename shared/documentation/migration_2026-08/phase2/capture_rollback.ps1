# Phase 2.0 — capture rollback state before any change.
# Run elevated.  Writes everything under ...\migration_2026-08\phase2\rollback\
$ErrorActionPreference = 'Continue'
$ProgressPreference    = 'SilentlyContinue'

$Base = 'C:\QIH\shared\documentation\migration_2026-08\phase2'
$Roll = Join-Path $Base 'rollback'
New-Item -ItemType Directory -Force -Path $Roll | Out-Null
$NSSM = 'C:\QIH\engine\bin\nssm.exe'

Write-Output "=== 1. NSSM service dumps ==="
$svcNames = Get-Service -Name 'QI_*' | Select-Object -ExpandProperty Name | Sort-Object
$svcNames | Set-Content -Path (Join-Path $Roll 'service_names.txt') -Encoding UTF8
Write-Output ("QI_* services found: " + $svcNames.Count)

$dumpFile = Join-Path $Roll 'nssm_dump_all.txt'
Remove-Item $dumpFile -ErrorAction SilentlyContinue
foreach ($s in $svcNames) {
    Add-Content -Path $dumpFile -Value ("### " + $s) -Encoding UTF8
    $d = & $NSSM dump $s 2>&1
    Add-Content -Path $dumpFile -Value $d -Encoding UTF8
    Add-Content -Path $dumpFile -Value '' -Encoding UTF8
}
Write-Output ("dumped -> " + $dumpFile)

# Structured capture of the fields we will change
Write-Output "=== 2. Structured service settings (CSV) ==="
$rows = foreach ($s in $svcNames) {
    $app  = (& $NSSM get $s Application    2>&1) -join ''
    $dir  = (& $NSSM get $s AppDirectory   2>&1) -join ''
    $parm = (& $NSSM get $s AppParameters  2>&1) -join ''
    $st   = (& $NSSM get $s Start          2>&1) -join ''
    $run  = (Get-Service -Name $s).Status
    [pscustomobject]@{
        Service = $s; Status = $run; Start = $st.Trim()
        Application = $app.Trim(); AppDirectory = $dir.Trim(); AppParameters = $parm.Trim()
    }
}
$rows | Export-Csv -Path (Join-Path $Roll 'services_before.csv') -NoTypeInformation -Encoding UTF8
$rows | Where-Object { $_.Application -like '*1-AI*' } |
    Select-Object Service, Status, Application |
    Format-Table -AutoSize | Out-String -Width 200 | Write-Output

Write-Output "=== 3. Scheduled task exports ==="
$taskDir = Join-Path $Roll 'scheduled_tasks'
New-Item -ItemType Directory -Force -Path $taskDir | Out-Null
$hits = @()
foreach ($t in (Get-ScheduledTask)) {
    $execs = @($t.Actions | ForEach-Object { $_.Execute }) -join ' '
    if ($execs -match '1-AI') {
        $safe = ($t.TaskName -replace '[\\/:*?"<>|]', '_')
        try {
            Export-ScheduledTask -TaskName $t.TaskName -TaskPath $t.TaskPath |
                Set-Content -Path (Join-Path $taskDir ($safe + '.xml')) -Encoding UTF8
            $hits += ($t.TaskPath + $t.TaskName)
        } catch { Write-Output ("  export failed: " + $t.TaskName + " : " + $_.Exception.Message) }
    }
}
Write-Output ("tasks referencing 1-AI: " + $hits.Count)
$hits | ForEach-Object { Write-Output ("  " + $_) }

Write-Output "=== 4. Config backups ==="
$cfgDir = Join-Path $Roll 'configs'
New-Item -ItemType Directory -Force -Path $cfgDir | Out-Null
$toCopy = @(
    'C:\Users\renne\.claude.json',
    'C:\QIH\ecosystem\qi_registry.json',
    'C:\QIH\commands\whitelist.json',
    'C:\CogniBase\.venv\pyvenv.cfg'
)
foreach ($f in $toCopy) {
    if (Test-Path $f) {
        $leaf = Split-Path $f -Leaf
        $dest = Join-Path $cfgDir ($leaf + '.bak')
        Copy-Item $f $dest -Force
        Write-Output ("  backed up " + $f)
    } else { Write-Output ("  MISSING  " + $f) }
}

Write-Output "=== 5. System Restore ==="
try {
    $srDrives = Get-ComputerRestorePoint -ErrorAction Stop | Select-Object -Last 3
    Write-Output "System Restore appears enabled. Existing recent points:"
    $srDrives | Select-Object SequenceNumber, Description, @{n='When';e={$_.ConvertToDateTime($_.CreationTime)}} |
        Format-Table -AutoSize | Out-String | Write-Output
} catch {
    Write-Output ("Get-ComputerRestorePoint failed: " + $_.Exception.Message)
}
try {
    Enable-ComputerRestore -Drive 'C:\' -ErrorAction Stop
    Write-Output "Enable-ComputerRestore C:\ -> ok"
} catch {
    Write-Output ("Enable-ComputerRestore failed: " + $_.Exception.Message)
}
try {
    Checkpoint-Computer -Description 'QI migration Phase 2 - before Python move' -RestorePointType 'MODIFY_SETTINGS' -ErrorAction Stop
    Write-Output "Checkpoint-Computer -> ok"
} catch {
    Write-Output ("Checkpoint-Computer failed: " + $_.Exception.Message)
    Write-Output "NOTE: proceeding without a restore point; file-level rollback data is captured above."
}

Write-Output "=== DONE ==="

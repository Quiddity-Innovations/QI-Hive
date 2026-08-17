# Phase 3e - retire C:\1-AI by RENAMING it, not deleting it.
#
# Renne's approach: rename, watch what breaks, fix it, then delete by hand once
# everything is proven. This script does the rename and immediately restores the
# one thing that must survive - the interpreter path the 12 remaining stale
# venvs still name as their base.
#
# After this runs:
#   C:\1-AI.RETIRED_2026-08-09   everything that was in C:\1-AI
#   C:\1-AI\APPS\PYTHON          junction -> C:\Program Files\Python311
#
# So the venvs keep working, and ANY other reference to C:\1-AI breaks loudly,
# which is exactly the signal we want.
#
# Run this AFTER Claude Code has restarted on the new interpreter, otherwise the
# rename fails: Windows will not rename a directory whose images are mapped by
# running processes.
#
# Pure ASCII only.
param([switch]$Apply)
$ErrorActionPreference = 'Continue'

$src     = 'C:\1-AI'
$retired = 'C:\1-AI.RETIRED_2026-08-09'
$newPy   = 'C:\Program Files\Python311'

Write-Output "=== GATE 1: is anything still running from C:\1-AI? ==="
$procs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
         Where-Object { $_.ExecutablePath -like '*1-AI*' }
if ($procs) {
    Write-Output ("  BLOCKED - " + @($procs).Count + " process(es) still mapped:")
    foreach ($p in $procs) {
        $cl = $p.CommandLine
        if ($cl -and $cl.Length -gt 120) { $cl = $cl.Substring(0,120) + ' ...' }
        Write-Output ("    PID " + $p.ProcessId + "  " + $p.Name + "  " + $cl)
    }
    Write-Output ""
    Write-Output "  Close these before renaming. Claude Voice helpers can be"
    Write-Output "  released by restarting QI_ClaudeVoiceControl; MCP servers by"
    Write-Output "  restarting Claude Code."
    if (-not $Apply) { Write-Output ""; Write-Output "DRY RUN - nothing changed." }
    exit 1
}
Write-Output "  clear - nothing is executing from C:\1-AI"

Write-Output ""
Write-Output "=== GATE 2: new interpreter healthy? ==="
$py = Join-Path $newPy 'python.exe'
if (-not (Test-Path $py)) { Write-Output "FATAL: new interpreter missing"; exit 1 }
Write-Output ("  " + (& $py -V 2>&1))

Write-Output ""
Write-Output "=== GATE 3: services healthy before we touch anything? ==="
$running = @(Get-Service -Name 'QI_*' | Where-Object { $_.Status -eq 'Running' }).Count
Write-Output ("  running: " + $running + " (expected 47)")

if (-not $Apply) {
    Write-Output ""
    Write-Output "Would rename:"
    Write-Output ("  " + $src + "  ->  " + $retired)
    Write-Output "Then create junction:"
    Write-Output ("  C:\1-AI\APPS\PYTHON  ->  " + $newPy)
    Write-Output ""
    Write-Output "DRY RUN - re-run with -Apply to perform it."
    exit 0
}

Write-Output ""
Write-Output "=== renaming ==="
if (Test-Path $retired) { Write-Output ("FATAL: " + $retired + " already exists"); exit 1 }
Rename-Item -Path $src -NewName (Split-Path $retired -Leaf) -ErrorAction Stop
Write-Output ("  " + $src + "  ->  " + $retired)

Write-Output ""
Write-Output "=== restoring the interpreter path as a junction ==="
New-Item -ItemType Directory -Path 'C:\1-AI\APPS' -Force | Out-Null
& cmd.exe /c mklink /J "C:\1-AI\APPS\PYTHON" "$newPy" | Out-Null
$ok = Test-Path 'C:\1-AI\APPS\PYTHON\python.exe'
Write-Output ("  junction resolves: " + $ok)
if ($ok) {
    Write-Output ("  via junction: " + (& 'C:\1-AI\APPS\PYTHON\python.exe' -V 2>&1))
}

Write-Output ""
Write-Output "=== verifying the stale venvs still work through the junction ==="
foreach ($v in @('C:\M2V\.venv','C:\PersonalSong\.venv','C:\QIP\Bakeoff\.venv',
                 'C:\APPS\AvatarStudio\.venv')) {
    $vp = Join-Path $v 'Scripts\python.exe'
    if (Test-Path $vp) {
        $out = & $vp -c "import sys;print(sys.version.split()[0])" 2>&1
        Write-Output ("  " + $v.PadRight(30) + " -> " + $out)
    } else {
        Write-Output ("  " + $v.PadRight(30) + " (absent)")
    }
}

Write-Output ""
Write-Output "=== service estate after rename ==="
Get-Service -Name 'QI_*' | Group-Object Status | ForEach-Object {
    Write-Output ("  " + $_.Name + ": " + $_.Count)
}
$down = Get-Service -Name 'QI_*' | Where-Object { $_.Status -ne 'Running' } | Select-Object -ExpandProperty Name
Write-Output ("  not running: " + ($down -join ', '))

Write-Output ""
Write-Output "=== health probes ==="
foreach ($u in @('http://127.0.0.1:8600/api/status',
                 'http://127.0.0.1:9011/health',
                 'http://127.0.0.1:8650/health',
                 'http://127.0.0.1:8189/system_stats')) {
    try {
        $r = Invoke-WebRequest -Uri $u -TimeoutSec 10 -UseBasicParsing
        Write-Output ("  " + $u.PadRight(42) + " HTTP " + $r.StatusCode)
    } catch {
        Write-Output ("  " + $u.PadRight(42) + " FAILED " + $_.Exception.Message)
    }
}

Write-Output ""
Write-Output ("Retired tree kept at: " + $retired)
Write-Output "Delete it by hand once you are satisfied nothing else broke."
Write-Output "=== DONE ==="

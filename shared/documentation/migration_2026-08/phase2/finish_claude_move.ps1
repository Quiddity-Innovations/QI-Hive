# Finish the CLAUDE move.
#
# Three things are outstanding after the bulk copy:
#
#  1. headroom_env's console-script launchers still carry the ABSOLUTE old
#     interpreter path (#!C:\CLAUDE\Tools\headroom_env\Scripts\python.exe).
#     That python.exe has already moved, so headroom.exe cannot start - NSSM
#     reporting "Running" is it restarting a crashing process, not health.
#
#  2. 28 .pyd native extension modules could not be copied out of
#     C:\CLAUDE\Tools\headroom_env because the running headroom process had
#     them memory-mapped.
#
#  3. NSSM writes QI_Headroom's logs INTO the venv, so the log directory has to
#     exist at the new location or the service will not start.
#
# Pure ASCII only.
param([switch]$Apply)
$ErrorActionPreference = 'Continue'

$old     = 'C:\CLAUDE'
$new     = 'C:\APPS\CLAUDE'
$hold    = 'D:\_PREMOVE_2026-08-09\CLAUDE'
$scripts = Join-Path $new 'Tools\headroom_env\Scripts'
$py      = 'C:\Program Files\Python311\python.exe'
$fixer   = 'C:\QIH\shared\documentation\migration_2026-08\phase2\fix_venv_scripts.py'

Write-Output "=== state ==="
Write-Output ("  C:\CLAUDE leftover files : " + @(Get-ChildItem $old -Recurse -File -ErrorAction SilentlyContinue).Count)
Write-Output ("  QI_Headroom              : " + (Get-Service QI_Headroom -ErrorAction SilentlyContinue).Status)

if (-not $Apply) { Write-Output ""; Write-Output "DRY RUN"; exit 0 }

Write-Output ""
Write-Output "=== stopping QI_Headroom so the .pyd files unmap ==="
Stop-Service QI_Headroom -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 6
Write-Output ("  state: " + (Get-Service QI_Headroom -ErrorAction SilentlyContinue).Status)
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.ExecutablePath -and $_.ExecutablePath -like 'C:\CLAUDE\*' } |
    ForEach-Object {
        Write-Output ("  terminating PID " + $_.ProcessId + " " + $_.Name)
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
Start-Sleep -Seconds 4

Write-Output ""
Write-Output "=== ensuring the venv log directory exists ==="
$logdir = Join-Path $new 'Tools\headroom_env\logs'
New-Item -ItemType Directory -Path $logdir -Force | Out-Null
Write-Output ("  " + $logdir + " : " + (Test-Path $logdir))

Write-Output ""
Write-Output "=== rewriting the venv console-script launchers ==="
# Arguments are passed as a PowerShell array, so the backslashes survive.
# Passing them through bash is what silently produced 'C:CLAUDE' and a
# false 'nothing to do' result the first time.
& $py $fixer --scripts $scripts --old $old --new $new --apply 2>&1 |
    ForEach-Object { Write-Output ("  " + $_) }

Write-Output ""
Write-Output "=== verifying headroom.exe ==="
$hx = Join-Path $scripts 'headroom.exe'
if (Test-Path $hx) {
    $v = & $hx --version 2>&1
    Write-Output ("  headroom --version : " + ($v -join ' '))
} else {
    Write-Output "  headroom.exe MISSING"
}

Write-Output ""
Write-Output "=== moving the leftover files ==="
New-Item -ItemType Directory -Path $hold -Force | Out-Null
& robocopy.exe $old $hold /E /MOVE /MT:8 /R:2 /W:2 /NFL /NDL /NP /NJH /NJS | Out-Null
Write-Output ("  robocopy /MOVE exit " + $LASTEXITCODE)
$remaining = @(Get-ChildItem $old -Recurse -File -ErrorAction SilentlyContinue).Count
Write-Output ("  files still in C:\CLAUDE : " + $remaining)
if ($remaining -eq 0 -and (Test-Path $old)) {
    Remove-Item $old -Recurse -Force -ErrorAction SilentlyContinue
}
Write-Output ("  C:\CLAUDE exists : " + (Test-Path $old) + "   (must be False)")

Write-Output ""
Write-Output "=== restarting services ==="
foreach ($s in @('QI_Headroom','QI_ClaudeVoiceControl','QI_ClaudeVoiceLine','QI_ClaudeVoiceTelegram')) {
    Restart-Service -Name $s -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    Write-Output ("  " + $s.PadRight(24) + " " + (Get-Service $s -ErrorAction SilentlyContinue).Status)
}

Start-Sleep -Seconds 8
Write-Output ""
Write-Output "=== is headroom actually serving on 9020? ==="
$listen = Get-NetTCPConnection -LocalPort 9020 -State Listen -ErrorAction SilentlyContinue
Write-Output ("  listening: " + [bool]$listen)
$proc = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq 'headroom.exe' }
foreach ($p in $proc) { Write-Output ("  PID " + $p.ProcessId + "  " + $p.ExecutablePath) }
Write-Output "=== DONE ==="

# Two qi_registry_mcp.py processes outlived the claude.exe that spawned them.
#
# An MCP server is a stdio child of its client. When the client exits without
# closing the pipe cleanly the child can survive as an orphan, holding the old
# interpreter mapped forever. Killing it is safe: it carries no state, and the
# next Claude Code start spawns a fresh one from the already-corrected config.
#
# Pure ASCII only.
param([switch]$Apply)
$ErrorActionPreference = 'Continue'

$targets = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
           Where-Object { $_.ExecutablePath -like '*1-AI*' }

Write-Output ("Processes pinning C:\1-AI: " + @($targets).Count)
Write-Output ""

foreach ($p in $targets) {
    Write-Output ("PID " + $p.ProcessId + "   " + $p.Name)
    Write-Output ("   cmd    : " + $p.CommandLine)
    $par = Get-CimInstance Win32_Process -Filter ("ProcessId=" + $p.ParentProcessId) -ErrorAction SilentlyContinue
    if ($par) {
        Write-Output ("   parent : ALIVE - PID " + $par.ProcessId + " " + $par.Name)
        Write-Output ("   NOTE   : parent still running; killing this may be premature")
    } else {
        Write-Output ("   parent : GONE (was PID " + $p.ParentProcessId + ") -> ORPHAN, safe to kill")
    }
    Write-Output ""
}

if (-not $Apply) {
    Write-Output "DRY RUN - re-run with -Apply to terminate them."
    exit 0
}

Write-Output "=== terminating ==="
foreach ($p in $targets) {
    try {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
        Write-Output ("  killed PID " + $p.ProcessId)
    } catch {
        Write-Output ("  PID " + $p.ProcessId + " : " + $_.Exception.Message)
    }
}

Start-Sleep -Seconds 4
$left = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.ExecutablePath -like '*1-AI*' }
Write-Output ""
Write-Output ("Processes still pinning C:\1-AI: " + @($left).Count)
foreach ($p in $left) { Write-Output ("   PID " + $p.ProcessId + "  " + $p.CommandLine) }

if (@($left).Count -eq 0) {
    Write-Output ""
    Write-Output "CLEAR - nothing holds C:\1-AI. Run p3e_rename_1ai.ps1 -Apply now."
}
Write-Output "=== DONE ==="

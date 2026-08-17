# Phase 3g - release the processes still pinning C:\1-AI.
#
# Two distinct groups:
#
#  1. Claude Voice helpers (bridge_responder, meeting_server, realtime,
#     session_watch, voice_tray, voice_button). These are DETACHED
#     grandchildren of the QI_ClaudeVoice* services - they started
#     2026-08-08 20:09 and survived the service restart, so NSSM is not
#     tracking them. They must be killed directly, then the services bounced
#     so they respawn on the migrated interpreter.
#
#  2. MCP servers under claude.exe. This script does NOT touch those - killing
#     an MCP server out from under a live Claude Code session is disruptive and
#     it would just respawn. Quit Claude Code entirely instead.
#
# Expect the voice tray/button to vanish and come back.
#
# Pure ASCII only.
param([switch]$Apply)
$ErrorActionPreference = 'Continue'

$voiceServices = @('QI_ClaudeVoiceControl','QI_ClaudeVoiceLine','QI_ClaudeVoiceTelegram')

function Get-Stragglers {
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.ExecutablePath -like '*1-AI*' }
}

function Is-McpChild($proc) {
    # Walk up to 4 parents looking for claude.exe
    $cur = $proc
    for ($i = 0; $i -lt 4; $i++) {
        $par = Get-CimInstance Win32_Process -Filter ("ProcessId=" + $cur.ParentProcessId) -ErrorAction SilentlyContinue
        if (-not $par) { return $false }
        if ($par.Name -like 'claude*') { return $true }
        $cur = $par
    }
    return $false
}

$all = @(Get-Stragglers)
Write-Output ("Processes pinning C:\1-AI: " + $all.Count)
Write-Output ""

$mcp = @()
$kill = @()
foreach ($p in $all) {
    if ((Is-McpChild $p) -or ($p.CommandLine -match 'qi_registry_mcp|brain[\\/]mcp\.py')) {
        $mcp += $p
    } else {
        $kill += $p
    }
}

Write-Output ("  MCP servers (leave alone, quit Claude Code): " + $mcp.Count)
foreach ($p in $mcp) { Write-Output ("     PID " + $p.ProcessId + "  " + $p.Name) }
Write-Output ""
Write-Output ("  Detached helpers to terminate: " + $kill.Count)
foreach ($p in $kill) {
    $cl = $p.CommandLine
    if ($cl -and $cl.Length -gt 110) { $cl = $cl.Substring(0,110) + ' ...' }
    Write-Output ("     PID " + $p.ProcessId + "  " + $cl)
}

if (-not $Apply) {
    Write-Output ""
    Write-Output "DRY RUN - re-run with -Apply to stop services, kill the helpers, and restart."
    exit 0
}

Write-Output ""
Write-Output "=== stopping Claude Voice services ==="
foreach ($s in $voiceServices) {
    $svc = Get-Service -Name $s -ErrorAction SilentlyContinue
    if ($svc) {
        Stop-Service -Name $s -Force -ErrorAction SilentlyContinue
        Write-Output ("  " + $s + " -> " + (Get-Service -Name $s).Status)
    }
}
Start-Sleep -Seconds 3

Write-Output ""
Write-Output "=== terminating detached helpers ==="
foreach ($p in $kill) {
    try {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
        Write-Output ("  killed PID " + $p.ProcessId)
    } catch {
        Write-Output ("  PID " + $p.ProcessId + " : " + $_.Exception.Message)
    }
}
Start-Sleep -Seconds 3

Write-Output ""
Write-Output "=== restarting Claude Voice services ==="
foreach ($s in $voiceServices) {
    $svc = Get-Service -Name $s -ErrorAction SilentlyContinue
    if ($svc) {
        Start-Service -Name $s -ErrorAction SilentlyContinue
        $deadline = (Get-Date).AddSeconds(30)
        do {
            Start-Sleep -Seconds 2
            $st = (Get-Service -Name $s).Status
        } while ($st -ne 'Running' -and (Get-Date) -lt $deadline)
        Write-Output ("  " + $s + " -> " + $st)
    }
}

Write-Output ""
Write-Output "=== waiting for helpers to respawn ==="
Start-Sleep -Seconds 12

$after = @(Get-Stragglers)
Write-Output ("Processes STILL pinning C:\1-AI: " + $after.Count)
foreach ($p in $after) {
    $cl = $p.CommandLine
    if ($cl -and $cl.Length -gt 110) { $cl = $cl.Substring(0,110) + ' ...' }
    Write-Output ("   PID " + $p.ProcessId + "  " + $cl)
}

Write-Output ""
Write-Output "=== helpers now on the NEW interpreter? ==="
$new = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
       Where-Object { $_.ExecutablePath -like '*Program Files\Python311*' -and
                      $_.CommandLine -match 'Claude Voice|bridge_responder|realtime|meeting_server' }
if ($new) {
    foreach ($p in $new) {
        $cl = $p.CommandLine
        if ($cl -and $cl.Length -gt 110) { $cl = $cl.Substring(0,110) + ' ...' }
        Write-Output ("   PID " + $p.ProcessId + "  " + $cl)
    }
} else {
    Write-Output "   (none yet - they may start on demand rather than at service start)"
}

Write-Output ""
Write-Output "=== service estate ==="
Get-Service -Name 'QI_*' | Group-Object Status | ForEach-Object {
    Write-Output ("  " + $_.Name + ": " + $_.Count)
}
$down = Get-Service -Name 'QI_*' | Where-Object { $_.Status -ne 'Running' } | Select-Object -ExpandProperty Name
Write-Output ("  not running: " + ($down -join ', '))

Write-Output ""
if (@($after | Where-Object { $_.CommandLine -notmatch 'qi_registry_mcp|brain[\\/]mcp\.py' }).Count -eq 0) {
    Write-Output "READY: only MCP servers remain. Quit Claude Code completely,"
    Write-Output "then run p3e_rename_1ai.ps1 -Apply from a plain PowerShell window."
} else {
    Write-Output "Some non-MCP processes are still pinning C:\1-AI - see the list above."
}
Write-Output "=== DONE ==="

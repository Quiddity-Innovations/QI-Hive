# Phase 2.1 - restore point before the Python relocation.
# Pure ASCII only. PowerShell 5.1 reads a BOM-less .ps1 as ANSI.
$ErrorActionPreference = 'Continue'

Write-Output "Running as admin: $([bool](New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))"

# Bypass the 24h throttle so a point is actually created.
New-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\SystemRestore' `
    -Name 'SystemRestorePointCreationFrequency' -Value 0 -PropertyType DWord -Force | Out-Null

Write-Output "Creating restore point..."
Checkpoint-Computer -Description 'QI migration Phase2.1 pre-PythonMove' -RestorePointType 'MODIFY_SETTINGS'

Write-Output ""
Write-Output "=== Restore points now on disk ==="
Get-ComputerRestorePoint | Select-Object -Last 5 |
    ForEach-Object { Write-Output ("  #" + $_.SequenceNumber + "  " + $_.Description + "  " + $_.CreationTime) }

Write-Output "=== DONE ==="

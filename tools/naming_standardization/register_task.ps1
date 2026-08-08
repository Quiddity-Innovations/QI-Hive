# Registers the one-time Friday standardization task to run as SYSTEM (no UAC at run time).
$ErrorActionPreference = 'Stop'
$logf = 'C:\QIH\tools\naming_standardization\logs\register_result.txt'
function Write-Note($m){ Write-Host $m; Add-Content $logf ("[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $m) }
try {
  Write-Note "=== registration attempt ==="
  Write-Note ("running elevated as: " + [Security.Principal.WindowsIdentity]::GetCurrent().Name)
  $admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
  Write-Note ("is administrator: " + $admin)
  $action  = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-NoProfile -ExecutionPolicy Bypass -File "C:\QIH\tools\naming_standardization\run_friday_standardization.ps1"'
  $trigger = New-ScheduledTaskTrigger -Once -At '2026-06-27T00:05:00'
  $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
  $settings  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
  Register-ScheduledTask -TaskName 'QI_NamingStandardize_Friday' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'One-time 2026-06-27 00:05 (Sat, the midnight ending Fri): re-point all 38 QI_ services to per-product NSSM copies (UAC popups name the product) + rename Tier-1 (12) and Tier-2 (25) control/launch batch files to <Product>_<Role>.bat (project-scoped reference rewrite) + update 4 scheduled-task actions to the new bat names. Prepared 2026-06-23.' -Force | Out-Null
  $info = Get-ScheduledTask -TaskName 'QI_NamingStandardize_Friday' | Get-ScheduledTaskInfo
  Write-Note "REGISTERED QI_NamingStandardize_Friday  NextRun=$($info.NextRunTime)"
  Write-Note "=== SUCCESS ==="
} catch {
  Write-Note ("ERROR: " + $_.Exception.Message)
  Write-Note "=== FAILED ==="
}

# Registers QI_DemoDayStartup: one-time, 2026-06-26 07:30, elevated, windowless.
# Brings up every QI app + tunnel and verifies each public URL before the demo day.
$ErrorActionPreference = 'Stop'

$taskName = 'QI_DemoDayStartup'
$python   = 'C:\1-AI\APPS\PYTHON\python.exe'
$script   = 'C:\QIH\engine\tunnels\demo_day_startup.py'
$conhost  = "$env:WINDIR\System32\conhost.exe"

# Windowless wrapper (conhost --headless) per QI scheduled-task window policy.
$action = New-ScheduledTaskAction -Execute $conhost `
    -Argument "--headless `"$python`" `"$script`"" `
    -WorkingDirectory 'C:\QIH\engine\tunnels'

# One-time trigger tomorrow morning, well before demos start.
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date '2026-06-26T07:30:00')

# Run as the interactive user at normal level. Service start/stop is elevated
# inside the script via the QI_Elevate broker, so no RunLevel=Highest (and thus no
# admin) is needed to register or run this task.
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive -RunLevel Limited

$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings `
    -Description 'QI demo-day: start all QI apps + Cloudflare tunnels, verify every public URL, notify via Tasuke LINE. One-time 2026-06-26 07:30.' `
    -Force | Out-Null

Write-Host 'Registered:' $taskName
$t = Get-ScheduledTask -TaskName $taskName
$ti = $t | Get-ScheduledTaskInfo
Write-Host ('State        : ' + $t.State)
Write-Host ('RunLevel     : ' + $t.Principal.RunLevel)
Write-Host ('NextRunTime  : ' + $ti.NextRunTime)

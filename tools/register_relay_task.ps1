# Registers QI_RelaySync. Cadence is every 30 min (the relay's design point), but the
# first run is held until Sunday 2026-08-23 00:00 local so nothing fires before Renne
# has verified the L2 drafting step.
$ErrorActionPreference = 'Stop'

$action = New-ScheduledTaskAction `
    -Execute 'C:\QIH\tools\qi_relay_cycle.bat' `
    -WorkingDirectory 'C:\QIH'

$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date '2026-08-23T00:00:00') `
    -RepetitionInterval (New-TimeSpan -Minutes 30)

# Runs as the interactive user: the cycle needs the user profile for git credentials and
# claude CLI auth. As SYSTEM it would fail both (see QI_Scheduled_Tasks_Registry.md).
$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 20) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName 'QI_RelaySync' `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description 'QI Relay - Claude-to-Claude collaborator channel. Every 30 min: git sync the qi-relay mailbox, write the pending digest, then run the sandboxed L2 drafting step. See C:\QI-RELAY\PROTOCOL.md and QI_Scheduled_Tasks_Registry.md.' `
    -Force | Out-Null

$t = Get-ScheduledTask -TaskName 'QI_RelaySync'
$i = Get-ScheduledTaskInfo -TaskName 'QI_RelaySync'
[PSCustomObject]@{
    Name       = $t.TaskName
    State      = $t.State
    StartAt    = $t.Triggers[0].StartBoundary
    Interval   = $t.Triggers[0].Repetition.Interval
    Duration   = if ($t.Triggers[0].Repetition.Duration) { $t.Triggers[0].Repetition.Duration } else { 'indefinite' }
    LogonType  = $t.Principal.LogonType
    NextRun    = $i.NextRunTime
} | Format-List

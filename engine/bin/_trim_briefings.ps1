Disable-ScheduledTask -TaskName 'OC-Asa-Briefing-9AM' -ErrorAction SilentlyContinue | Out-Null
Disable-ScheduledTask -TaskName 'OC-Morning-Briefing' -ErrorAction SilentlyContinue | Out-Null
Get-ScheduledTask | Where-Object { $_.TaskName -match 'Briefing|Morning' } |
    Select-Object TaskName, State | Format-Table -AutoSize

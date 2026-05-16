Get-ScheduledTask | Where-Object { $_.TaskName -match 'kaze|news|digest|OC-' } | ForEach-Object {
    $info = Get-ScheduledTaskInfo -TaskName $_.TaskName -TaskPath $_.TaskPath -ErrorAction SilentlyContinue
    [PSCustomObject]@{
        TaskName  = $_.TaskName
        State     = $_.State
        LastRun   = $info.LastRunTime
        NextRun   = $info.NextRunTime
        Action    = ($_.Actions | ForEach-Object { "$($_.Execute) $($_.Arguments)" }) -join ' | '
    }
} | Format-Table -AutoSize -Wrap

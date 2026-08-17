$ErrorActionPreference = 'Continue'
$ProgressPreference    = 'SilentlyContinue'

Write-Output "=== A. Force a fresh restore point (bypass the 24h throttle) ==="
$key = 'HKLM:\Software\Microsoft\Windows NT\CurrentVersion\SystemRestore'
New-Item -Path $key -Force | Out-Null
Set-ItemProperty -Path $key -Name 'SystemRestorePointCreationFrequency' -Value 0 -Type DWord
$before = @(Get-ComputerRestorePoint).Count
try {
    Checkpoint-Computer -Description 'QI migration Phase2 pre-Python' -RestorePointType 'MODIFY_SETTINGS' -ErrorAction Stop
} catch { Write-Output ("checkpoint error: " + $_.Exception.Message) }
$after = @(Get-ComputerRestorePoint)
Write-Output ("restore points before=" + $before + " after=" + $after.Count)
$after | Select-Object -Last 3 SequenceNumber, Description,
    @{n='When';e={$_.ConvertToDateTime($_.CreationTime)}} | Format-Table -AutoSize | Out-String | Write-Output

Write-Output "=== B. All scheduled tasks referencing 1-AI (full detail) ==="
foreach ($t in (Get-ScheduledTask)) {
    $acts = @($t.Actions | Where-Object { $_.Execute })
    $joined = ($acts | ForEach-Object { $_.Execute + ' ' + $_.Arguments }) -join ' || '
    if ($joined -match '1-AI') {
        Write-Output ('--- ' + $t.TaskPath + $t.TaskName + '   [state=' + $t.State + ']')
        foreach ($a in $acts) {
            Write-Output ('      Execute   : ' + $a.Execute)
            Write-Output ('      Arguments : ' + $a.Arguments)
            Write-Output ('      WorkingDir: ' + $a.WorkingDirectory)
        }
        $pr = $t.Principal
        Write-Output ('      RunAs     : ' + $pr.UserId + '  LogonType=' + $pr.LogonType + '  RunLevel=' + $pr.RunLevel)
    }
}

Write-Output "=== C. Network reachability for python.org ==="
try {
    $r = Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/' -UseBasicParsing -TimeoutSec 25
    Write-Output ("python.org ftp index: HTTP " + $r.StatusCode)
} catch { Write-Output ("python.org unreachable: " + $_.Exception.Message) }

Write-Output "=== D. Existing Python installs on the machine (registry) ==="
foreach ($hive in @('HKLM:\SOFTWARE\Python\PythonCore','HKLM:\SOFTWARE\WOW6432Node\Python\PythonCore','HKCU:\SOFTWARE\Python\PythonCore')) {
    if (Test-Path $hive) {
        Write-Output ("  " + $hive)
        Get-ChildItem $hive | ForEach-Object {
            $ip = Join-Path $_.PSPath 'InstallPath'
            $p = if (Test-Path $ip) { (Get-ItemProperty $ip).'(default)' } else { '?' }
            Write-Output ("     " + $_.PSChildName + " -> " + $p)
        }
    }
}
Write-Output "=== DONE ==="

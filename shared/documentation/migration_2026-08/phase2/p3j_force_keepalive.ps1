# The earlier 'nssm set' against OC-Keepalive-Service did not stick - the
# registry still held the old interpreter afterwards. C:\OC\nssm.exe is a
# separate, older nssm binary; rather than debug it, write the value with the
# standardised binary and fall back to a direct registry write, then prove the
# change by reading the registry back.
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

$svc    = 'OC-Keepalive-Service'
$new    = 'C:\Program Files\Python311\python.exe'
$key    = 'HKLM:\SYSTEM\CurrentControlSet\Services\' + $svc + '\Parameters'
$nssm   = 'C:\QIH\engine\bin\nssm.exe'

Write-Output ("before: " + (Get-ItemProperty $key -ErrorAction SilentlyContinue).Application)

Write-Output ""
Write-Output "=== stopping the service ==="
Stop-Service -Name $svc -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
Write-Output ("  state: " + (Get-Service -Name $svc -ErrorAction SilentlyContinue).Status)

# kill any daemon that outlived the service
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'oc-keepalive-daemon' } |
    ForEach-Object {
        Write-Output ("  killing orphaned daemon PID " + $_.ProcessId)
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }

Write-Output ""
Write-Output "=== attempt 1: standardised nssm binary ==="
if (Test-Path $nssm) {
    & $nssm set $svc Application $new 2>&1 | ForEach-Object { Write-Output ("  " + ($_ -replace "`0",'')) }
} else {
    Write-Output "  (standard nssm not found)"
}
$after = (Get-ItemProperty $key -ErrorAction SilentlyContinue).Application
Write-Output ("  registry now: " + $after)

if ($after -ne $new) {
    Write-Output ""
    Write-Output "=== attempt 2: direct registry write ==="
    Set-ItemProperty -Path $key -Name 'Application' -Value $new -ErrorAction SilentlyContinue
    $after = (Get-ItemProperty $key -ErrorAction SilentlyContinue).Application
    Write-Output ("  registry now: " + $after)
}

Write-Output ""
Write-Output "=== other Parameters values ==="
$props = Get-ItemProperty $key -ErrorAction SilentlyContinue
foreach ($p in $props.PSObject.Properties) {
    if ($p.Name -in @('PSPath','PSParentPath','PSChildName','PSDrive','PSProvider')) { continue }
    $flag = if ("" + $p.Value -like '*1-AI*') { '   <-- STALE' } else { '' }
    Write-Output ("  " + $p.Name.PadRight(16) + " " + $p.Value + $flag)
}

Write-Output ""
Write-Output "=== starting the service ==="
Start-Service -Name $svc -ErrorAction SilentlyContinue
$deadline = (Get-Date).AddSeconds(45)
do {
    Start-Sleep -Seconds 3
    $st = (Get-Service -Name $svc -ErrorAction SilentlyContinue).Status
} while ($st -ne 'Running' -and (Get-Date) -lt $deadline)
Write-Output ("  state: " + $st)

Start-Sleep -Seconds 8
Write-Output ""
Write-Output "=== which interpreter is the daemon on now? ==="
$d = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
     Where-Object { $_.CommandLine -match 'oc-keepalive-daemon' }
if ($d) {
    foreach ($p in $d) {
        Write-Output ("  PID " + $p.ProcessId + "  " + $p.ExecutablePath)
    }
} else {
    Write-Output "  (no daemon process - it may start on a timer)"
}

Write-Output ""
Write-Output "=== everything still pinning C:\1-AI ==="
$left = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.ExecutablePath -like '*1-AI*' }
Write-Output ("  count: " + @($left).Count)
foreach ($p in $left) {
    $cl = $p.CommandLine
    if ($cl -and $cl.Length -gt 100) { $cl = $cl.Substring(0,100) + ' ...' }
    Write-Output ("   PID " + $p.ProcessId + "  " + $cl)
}
Write-Output "=== DONE ==="

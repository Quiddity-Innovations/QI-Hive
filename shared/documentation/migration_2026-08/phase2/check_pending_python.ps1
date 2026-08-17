# Are any Python / 1-AI files queued for deletion on next boot?
# This matters: 31 services still run python.exe from C:\1-AI. If a reboot
# happened before they are repointed, those files would vanish and every one
# of them would fail to start.
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

$pfro = Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager' `
        -Name PendingFileRenameOperations -ErrorAction SilentlyContinue

if (-not $pfro) {
    Write-Output "PendingFileRenameOperations: ABSENT (nothing queued)"
} else {
    $entries = @($pfro.PendingFileRenameOperations)
    Write-Output ("PendingFileRenameOperations entries: " + $entries.Count)
    $hits = $entries | Where-Object { $_ -match '1-AI' -or $_ -match [regex]::Escape('Python') }
    Write-Output ("  entries mentioning Python or 1-AI: " + @($hits).Count)
    foreach ($h in $hits) { Write-Output ("    " + $h) }
}

Write-Output ""
Write-Output "=== Reboot-pending flags ==="
foreach ($p in @(
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending',
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired')) {
    Write-Output ("  " + $p + " : " + (Test-Path $p))
}

Write-Output ""
Write-Output "=== Uptime ==="
$os = Get-CimInstance Win32_OperatingSystem
Write-Output ("  last boot: " + $os.LastBootUpTime)
Write-Output ("  uptime   : " + ((Get-Date) - $os.LastBootUpTime).ToString('dd\.hh\:mm\:ss'))
Write-Output "=== DONE ==="

# Confirm every non-QI_ NSSM service now names a real interpreter.
# The standardised nssm binary returns "OpenService(): Access is denied" for
# services registered by a different nssm, so these were written straight to
# the registry - which means they must be read back from the registry too.
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

foreach ($s in @('ClaudeManager','NayaTunnel','NEXUSTunnel','OC-Keepalive-Service')) {
    $k = 'HKLM:\SYSTEM\CurrentControlSet\Services\' + $s + '\Parameters'
    $p = Get-ItemProperty $k -ErrorAction SilentlyContinue
    $st = (Get-Service -Name $s -ErrorAction SilentlyContinue).Status
    $app = if ($p) { $p.Application } else { '(no Parameters key)' }
    $stale = if ("" + $app -like '*1-AI*') { '   <-- STILL STALE' } else { '' }
    $exists = if ($app -and $app -notlike '(*') { Test-Path $app } else { '?' }
    Write-Output ($s.PadRight(24) + " [" + $st + "]")
    Write-Output ("    Application: " + $app + $stale)
    Write-Output ("    exists     : " + $exists)
}

Write-Output ""
Write-Output "=== full estate ==="
Get-Service | Where-Object { $_.Name -match 'QI_|ClaudeManager|NayaTunnel|NEXUSTunnel|OC-Keepalive' } |
    Group-Object Status | ForEach-Object { Write-Output ("  " + $_.Name + ": " + $_.Count) }

Write-Output ""
Write-Output "=== processes still pinning C:\1-AI ==="
$left = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.ExecutablePath -like '*1-AI*' }
Write-Output ("  count: " + @($left).Count)
foreach ($p in $left) {
    Write-Output ("   PID " + $p.ProcessId + "  " + $p.Name)
}
Write-Output "=== DONE ==="

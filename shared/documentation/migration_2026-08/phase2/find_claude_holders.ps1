# Which processes still have a module loaded from C:\CLAUDE?
# A .pyd or .dll cannot be moved while any process maps it, and the process
# that loaded it is not necessarily the one whose ExecutablePath sits there.
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

$hits = @{}
foreach ($p in (Get-Process -ErrorAction SilentlyContinue)) {
    try {
        foreach ($m in $p.Modules) {
            if ($m.FileName -like 'C:\CLAUDE\*') {
                if (-not $hits.ContainsKey($p.Id)) { $hits[$p.Id] = @() }
                $hits[$p.Id] += $m.FileName
            }
        }
    } catch { }   # access denied on protected processes is expected
}

if ($hits.Count -eq 0) {
    Write-Output "No accessible process maps a module from C:\CLAUDE."
    Write-Output "(Modules of services running as LocalSystem may be invisible from here."
    Write-Output " Check the owning service instead.)"
} else {
    foreach ($k in $hits.Keys) {
        $pr = Get-Process -Id $k -ErrorAction SilentlyContinue
        Write-Output ("PID " + $k + "  " + $pr.ProcessName)
        foreach ($f in ($hits[$k] | Select-Object -First 4)) { Write-Output ("    " + $f) }
    }
}

Write-Output ""
Write-Output "=== processes whose image or command line still names C:\CLAUDE ==="
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        ($_.ExecutablePath -and $_.ExecutablePath -like 'C:\CLAUDE\*') -or
        ($_.CommandLine -and $_.CommandLine -match [regex]::Escape('C:\CLAUDE\'))
    } |
    ForEach-Object {
        $cl = $_.CommandLine
        if ($cl -and $cl.Length -gt 110) { $cl = $cl.Substring(0,110) + ' ...' }
        Write-Output ("  PID " + $_.ProcessId + "  " + $_.Name + "  " + $cl)
    }

Write-Output ""
Write-Output "=== services whose config still names C:\CLAUDE ==="
foreach ($s in (Get-CimInstance Win32_Service | Where-Object { $_.PathName -match 'nssm' })) {
    $k = 'HKLM:\SYSTEM\CurrentControlSet\Services\' + $s.Name + '\Parameters'
    $p = Get-ItemProperty $k -ErrorAction SilentlyContinue
    $blob = "" + $p.Application + " " + $p.AppDirectory + " " + $p.AppParameters
    if ($blob -match [regex]::Escape('C:\CLAUDE\')) {
        Write-Output ("  " + $s.Name + " [" + $s.State + "]  " + $blob.Trim())
    }
}
Write-Output "=== DONE ==="

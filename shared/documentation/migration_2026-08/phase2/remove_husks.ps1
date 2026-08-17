# Remove the empty leftover directories at the C: root.
# Both survived earlier only because a process held them as its cwd; the reboot
# released that.
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

foreach ($d in @('C:\AutoPDF', 'C:\NEXUS')) {
    if (-not (Test-Path $d)) { Write-Output ($d + " : already gone"); continue }
    # Count FILES, not items. An empty husk can still contain empty
    # subdirectories - C:\AutoPDF kept an empty 'Application' folder - and those
    # are not a reason to keep it.
    $n = @(Get-ChildItem $d -Force -Recurse -File -ErrorAction SilentlyContinue).Count
    if ($n -gt 0) {
        Write-Output ($d + " : NOT EMPTY (" + $n + " files) - left alone")
        continue
    }
    try {
        Remove-Item $d -Recurse -Force -ErrorAction Stop
        Write-Output ($d + " : removed, exists=" + (Test-Path $d))
    } catch {
        Write-Output ($d + " : LOCKED - " + $_.Exception.Message)
    }
}

Write-Output ""
Write-Output "=== C: root, apps only ==="
$keep = @('Windows','Program Files','Program Files (x86)','ProgramData','Users',
          'PerfLogs','Recovery','$Recycle.Bin','System Volume Information',
          'Documents and Settings','Config.Msi','OneDriveTemp','inetpub',
          '$WinREAgent','TEMP','tmp','APPS','QIH')
Get-ChildItem 'C:\' -Directory -Force -ErrorAction SilentlyContinue |
    Where-Object { $keep -notcontains $_.Name } |
    ForEach-Object { Write-Output ("  " + $_.Name) }
Write-Output "=== DONE ==="

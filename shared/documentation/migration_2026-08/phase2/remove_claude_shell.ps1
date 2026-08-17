# C:\CLAUDE now holds 0 files - all 28 were relocated to
# C:\CLAUDE.RETIRED_2026-08-09. Only empty directory shells remain, which is
# why Test-Path still reported True. Remove them.
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

$p = 'C:\CLAUDE'
if (-not (Test-Path $p)) {
    Write-Output "C:\CLAUDE already gone"
} else {
    $f = @(Get-ChildItem $p -Recurse -File -Force -ErrorAction SilentlyContinue).Count
    $d = @(Get-ChildItem $p -Recurse -Directory -Force -ErrorAction SilentlyContinue).Count
    Write-Output ("files: " + $f + "   empty subdirectories: " + $d)
    if ($f -eq 0) {
        try {
            Remove-Item $p -Recurse -Force -ErrorAction Stop
            Write-Output "  removed"
        } catch {
            Write-Output ("  LOCKED: " + $_.Exception.Message)
        }
    } else {
        Write-Output "  NOT empty - left alone"
    }
}

Write-Output ""
Write-Output ("C:\CLAUDE exists         : " + (Test-Path $p))
Write-Output ("C:\CLAUDE.RETIRED exists : " + (Test-Path 'C:\CLAUDE.RETIRED_2026-08-09'))

Write-Output ""
Write-Output "=== C: root, yours only ==="
$keep = @('Windows','Program Files','Program Files (x86)','ProgramData','Users',
          'PerfLogs','Recovery','$Recycle.Bin','System Volume Information',
          'Documents and Settings','Config.Msi','OneDriveTemp','inetpub',
          '$WinREAgent','TEMP','tmp','APPS','QIH')
Get-ChildItem 'C:\' -Directory -Force -ErrorAction SilentlyContinue |
    Where-Object { $keep -notcontains $_.Name } |
    ForEach-Object { Write-Output ("  " + $_.Name) }
Write-Output "=== DONE ==="

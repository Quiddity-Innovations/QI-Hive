# Remove empty leftover directories at the root of C: for apps already moved.
#
# A directory can linger after its contents are gone because a process still
# holds it as its working directory. Bouncing the owning service releases it.
# Only EMPTY directories are removed here - if anything is still inside, it is
# reported and left alone.
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

$moved = @('AkiyaScout','SCRIPTS','VLCDaemon','MQ','CypherMiner','Lottery Wiz',
           'TUBESCOUT','Retirement Analyzer','QIP','OC','EasyFlow','NEXUS',
           'MailBrain','Gamez','MapSnap','CogniBase')

foreach ($a in $moved) {
    $p = 'C:\' + $a
    if (-not (Test-Path $p)) { continue }

    $items = @(Get-ChildItem $p -Force -Recurse -ErrorAction SilentlyContinue)
    if ($items.Count -gt 0) {
        Write-Output ("NOT EMPTY: " + $p + "  (" + $items.Count + " items) - left alone")
        foreach ($i in ($items | Select-Object -First 5)) { Write-Output ("    " + $i.FullName) }
        continue
    }

    Write-Output ("empty: " + $p)
    try {
        Remove-Item $p -Force -Recurse -ErrorAction Stop
        Write-Output ("   removed -> exists=" + (Test-Path $p))
    } catch {
        Write-Output ("   locked: " + $_.Exception.Message)
        # A directory held as a process cwd frees up once that process restarts.
        # Queue it for removal at next boot rather than forcing anything.
        Write-Output "   (will retry below)"
        Start-Sleep -Seconds 3
        try {
            Remove-Item $p -Force -Recurse -ErrorAction Stop
            Write-Output ("   removed on retry -> exists=" + (Test-Path $p))
        } catch {
            Write-Output ("   STILL LOCKED - remove manually or after next reboot")
        }
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

# C:\PlayDeck survived because it still holds engine\bin\nssm.exe - the service
# host binary, locked open by the service it runs.
#
# Same pattern as C:\OC and C:\NEXUS, but nested rather than at the top level,
# so the generic fix_stray_nssm.ps1 (which expects C:\<App>\nssm.exe) misses it.
# Pure ASCII only.
param([switch]$Apply)
$ErrorActionPreference = 'Continue'

$src  = 'C:\PlayDeck'
$hold = 'D:\_PREMOVE_2026-08-09\PlayDeck'

Write-Output "=== what is left ==="
Get-ChildItem $src -Force -Recurse -ErrorAction SilentlyContinue |
    Where-Object { -not $_.PSIsContainer } |
    ForEach-Object { Write-Output ("  " + $_.FullName) }

Write-Output ""
Write-Output "=== services whose ImagePath lives under C:\PlayDeck ==="
$svcs = Get-CimInstance Win32_Service | Where-Object {
    $_.PathName -match [regex]::Escape('C:\PlayDeck')
}
foreach ($s in $svcs) {
    Write-Output ("  " + $s.Name + "  [" + $s.State + "]  " + $s.PathName)
}
if (-not $svcs) { Write-Output "  (none - the file may just be orphaned)" }

if (-not $Apply) { Write-Output ""; Write-Output "DRY RUN"; exit 0 }

$wasRunning = @()
foreach ($s in $svcs) {
    if ($s.State -eq 'Running') { $wasRunning += $s.Name }

    # Rewrite the ImagePath to the copy that already moved.
    $newPath = $s.PathName.Replace('C:\PlayDeck', 'C:\APPS\PlayDeck')
    Write-Output ""
    Write-Output ("=== " + $s.Name + " ===")
    Stop-Service -Name $s.Name -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 4
    Write-Output ("  stopped: " + (Get-Service -Name $s.Name -ErrorAction SilentlyContinue).Status)

    $key = 'HKLM:\SYSTEM\CurrentControlSet\Services\' + $s.Name
    Set-ItemProperty -Path $key -Name 'ImagePath' -Value $newPath
    Write-Output ("  ImagePath -> " + (Get-ItemProperty $key).ImagePath)
}

Write-Output ""
Write-Output "=== retiring the stray files ==="
New-Item -ItemType Directory -Path $hold -Force | Out-Null
$stray = Join-Path $hold 'engine_bin_from-C-root'
& robocopy.exe (Join-Path $src 'engine') $stray /E /MOVE /R:1 /W:1 /NFL /NDL /NP /NJH /NJS | Out-Null
Write-Output ("  robocopy /MOVE exit " + $LASTEXITCODE)

if (Test-Path $src) {
    try {
        Remove-Item $src -Recurse -Force -ErrorAction Stop
        Write-Output ("  " + $src + " removed")
    } catch {
        Write-Output ("  still present: " + $_.Exception.Message)
    }
}

foreach ($n in $wasRunning) {
    Start-Service -Name $n -ErrorAction SilentlyContinue
    $deadline = (Get-Date).AddSeconds(60)
    do {
        Start-Sleep -Seconds 3
        $st = (Get-Service -Name $n -ErrorAction SilentlyContinue).Status
    } while ($st -ne 'Running' -and (Get-Date) -lt $deadline)
    Write-Output ("  " + $n + " -> " + $st)
}

Write-Output ""
Write-Output ("  C:\PlayDeck exists : " + (Test-Path $src) + "   (must be False)")
Write-Output "=== DONE ==="

# Some app folders survive the move because they still hold their own nssm.exe,
# locked open by the service it hosts. C:\OC and C:\NEXUS both did this.
#
# Repoint the service's ImagePath at the copy that already moved to
# C:\APPS\<App>\nssm.exe, then retire the stray binary so the folder can go.
#
# Deliberately does NOT remove any service, even a known duplicate: Renne's
# rule for this pass is that nothing gets deleted.
# Pure ASCII only.
param(
    [Parameter(Mandatory=$true)][string]$App,
    [switch]$Apply
)
$ErrorActionPreference = 'Continue'

$src  = 'C:\' + $App
$new  = 'C:\APPS\' + $App + '\nssm.exe'
$hold = 'D:\_PREMOVE_2026-08-09\' + $App

Write-Output ("=== " + $src + " ===")
if (-not (Test-Path $src)) { Write-Output "  already gone"; exit 0 }
Get-ChildItem $src -Force -Recurse -ErrorAction SilentlyContinue |
    ForEach-Object { Write-Output ("  holds: " + $_.FullName) }

if (-not (Test-Path $new)) { Write-Output ("FATAL: " + $new + " missing"); exit 1 }

# Which services run this stray binary?
$svcs = Get-CimInstance Win32_Service | Where-Object {
    $_.PathName -match [regex]::Escape($src + '\nssm.exe')
}
Write-Output ""
Write-Output ("services hosted by the stray binary: " + @($svcs).Count)
foreach ($s in $svcs) {
    Write-Output ("  " + $s.Name + "  [" + $s.State + "]  " + $s.PathName)
}

if (-not $Apply) { Write-Output ""; Write-Output "DRY RUN"; exit 0 }

$wasRunning = @($svcs | Where-Object { $_.State -eq 'Running' } | Select-Object -ExpandProperty Name)

foreach ($s in $svcs) {
    Write-Output ""
    Write-Output ("=== " + $s.Name + " ===")
    Stop-Service -Name $s.Name -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    Write-Output ("  stopped: " + (Get-Service -Name $s.Name -ErrorAction SilentlyContinue).Status)
    $key = 'HKLM:\SYSTEM\CurrentControlSet\Services\' + $s.Name
    Set-ItemProperty -Path $key -Name 'ImagePath' -Value $new
    Write-Output ("  ImagePath -> " + (Get-ItemProperty $key).ImagePath)
}

Write-Output ""
Write-Output "=== retiring the stray files ==="
New-Item -ItemType Directory -Path $hold -Force | Out-Null
Get-ChildItem $src -Force -ErrorAction SilentlyContinue | ForEach-Object {
    $t = Join-Path $hold ($_.Name + '.from-C-root')
    try {
        Move-Item -Path $_.FullName -Destination $t -Force -ErrorAction Stop
        Write-Output ("  moved " + $_.Name)
    } catch {
        Write-Output ("  FAILED " + $_.Name + " : " + $_.Exception.Message)
    }
}
if (Test-Path $src) {
    try { Remove-Item $src -Force -Recurse -ErrorAction Stop; Write-Output ("  " + $src + " removed") }
    catch { Write-Output ("  still present: " + $_.Exception.Message) }
}

foreach ($n in $wasRunning) {
    Start-Service -Name $n -ErrorAction SilentlyContinue
    $deadline = (Get-Date).AddSeconds(45)
    do {
        Start-Sleep -Seconds 3
        $st = (Get-Service -Name $n -ErrorAction SilentlyContinue).Status
    } while ($st -ne 'Running' -and (Get-Date) -lt $deadline)
    Write-Output ("  " + $n + " -> " + $st)
}

Write-Output ""
Write-Output ("  " + $src + " exists : " + (Test-Path $src) + "   (must be False)")
Write-Output "=== DONE ==="

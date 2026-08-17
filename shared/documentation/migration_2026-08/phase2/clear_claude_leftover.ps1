# Clear the last 28 files out of C:\CLAUDE.
#
# They are .pyd native extensions inside headroom_env. They were memory-mapped
# by the running headroom process during the bulk copy, so robocopy could not
# move them - but the copy at C:\APPS\CLAUDE is complete (the file counts
# matched), so these are duplicates of files that already exist at the
# destination.
#
# headroom has since been restarted from the new location, so the old mappings
# should be released. Verified per-file against the destination before moving,
# so nothing unique is relocated blind.
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

$old  = 'C:\CLAUDE'
$new  = 'C:\APPS\CLAUDE'
$hold = 'D:\_PREMOVE_2026-08-09\CLAUDE'

if (-not (Test-Path $old)) { Write-Output "C:\CLAUDE already gone"; exit 0 }

$files = @(Get-ChildItem $old -Recurse -File -Force -ErrorAction SilentlyContinue)
Write-Output ("leftover files: " + $files.Count)

$missingAtDest = @()
foreach ($f in $files) {
    $rel = $f.FullName.Substring($old.Length).TrimStart('\')
    $dest = Join-Path $new $rel
    if (-not (Test-Path $dest)) { $missingAtDest += $rel }
}
Write-Output ("of which NOT already present at the destination: " + $missingAtDest.Count)
foreach ($m in $missingAtDest) { Write-Output ("   MISSING AT DEST: " + $m) }

if ($missingAtDest.Count -gt 0) {
    Write-Output ""
    Write-Output "Some leftovers do not exist at the destination - copying those across first."
    foreach ($rel in $missingAtDest) {
        $s = Join-Path $old $rel
        $d = Join-Path $new $rel
        New-Item -ItemType Directory -Path (Split-Path $d) -Force | Out-Null
        Copy-Item $s $d -Force -ErrorAction SilentlyContinue
        Write-Output ("   copied " + $rel + " -> exists=" + (Test-Path $d))
    }
}

Write-Output ""
Write-Output "=== relocating the leftovers to the hold area ==="
New-Item -ItemType Directory -Path $hold -Force | Out-Null
& robocopy.exe $old $hold /E /MOVE /R:2 /W:2 /NFL /NDL /NP /NJH /NJS | Out-Null
Write-Output ("  robocopy /MOVE exit " + $LASTEXITCODE)

$left = @(Get-ChildItem $old -Recurse -File -Force -ErrorAction SilentlyContinue)
Write-Output ("  files still in C:\CLAUDE : " + $left.Count)
foreach ($f in ($left | Select-Object -First 8)) { Write-Output ("     " + $f.FullName) }

if ($left.Count -eq 0 -and (Test-Path $old)) {
    Remove-Item $old -Recurse -Force -ErrorAction SilentlyContinue
}
Write-Output ("  C:\CLAUDE exists : " + (Test-Path $old))

Write-Output ""
Write-Output "=== headroom still healthy? ==="
Write-Output ("  service   : " + (Get-Service QI_Headroom -ErrorAction SilentlyContinue).Status)
Write-Output ("  port 9020 : " + [bool](Get-NetTCPConnection -LocalPort 9020 -State Listen -ErrorAction SilentlyContinue))
Write-Output "=== DONE ==="

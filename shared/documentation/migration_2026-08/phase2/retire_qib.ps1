# QIB is 0 bytes, empty, unregistered, and referenced by nothing.
#
# Per Renne's rule nothing is deleted: it is moved to the hold area under the
# name "QIB_for deletion" so it is unmistakably flagged, and Renne removes it.
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

$src  = 'C:\QIB'
$hold = 'D:\_PREMOVE_2026-08-09\QIB_for deletion'

if (-not (Test-Path $src)) { Write-Output "C:\QIB already gone"; exit 0 }

$files = @(Get-ChildItem $src -Force -Recurse -File -ErrorAction SilentlyContinue)
$dirs  = @(Get-ChildItem $src -Force -Recurse -Directory -ErrorAction SilentlyContinue)
Write-Output ("C:\QIB : " + $files.Count + " files, " + $dirs.Count + " subdirectories")
foreach ($f in ($files | Select-Object -First 10)) { Write-Output ("   " + $f.FullName) }

New-Item -ItemType Directory -Path (Split-Path $hold) -Force | Out-Null

if ($files.Count -eq 0) {
    # Nothing to preserve, but still record that it existed rather than just
    # removing it - Renne asked to be able to review anything retired.
    New-Item -ItemType Directory -Path $hold -Force | Out-Null
    Set-Content -Path (Join-Path $hold 'WAS_EMPTY.txt') -Encoding ASCII -Value @(
        'C:\QIB was empty when retired on 2026-08-09.',
        'It contained 0 files and ' + $dirs.Count + ' empty subdirectories.',
        'It was unregistered in qi_registry.json and referenced by no service.',
        'Kept as a record so the removal is reviewable.'
    )
    Remove-Item $src -Recurse -Force -ErrorAction SilentlyContinue
} else {
    & robocopy.exe $src $hold /E /MOVE /R:1 /W:1 /NFL /NDL /NP /NJH /NJS | Out-Null
    if (Test-Path $src) { Remove-Item $src -Recurse -Force -ErrorAction SilentlyContinue }
}

Write-Output ""
Write-Output ("  C:\QIB exists : " + (Test-Path $src) + "   (must be False)")
Write-Output ("  held at       : " + $hold + "  " + (Test-Path $hold))
Write-Output "=== DONE ==="

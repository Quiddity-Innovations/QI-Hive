# Phase 3a - move AvatarStudio out of C:\1-AI and into C:\APPS.
#
# AvatarStudio is a live registered QI project (id: avatarstudio, Gradio on
# :7862), not leftover junk. It has no NSSM service, which is why it is easy to
# mistake for dead weight.
#
# Copy-then-verify, never move: the original stays until the copy is proven.
# Its .venv still names C:\1-AI\APPS\PYTHON as its base, which keeps working
# via the junction bridge installed later in Phase 3.
#
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

$src = 'C:\1-AI\APPS\AvatarStudio'
$dst = 'C:\APPS\AvatarStudio'

if (-not (Test-Path $src)) { Write-Output "FATAL: source missing"; exit 1 }
if (Test-Path $dst)        { Write-Output ("FATAL: destination already exists: " + $dst); exit 1 }

New-Item -ItemType Directory -Path 'C:\APPS' -Force | Out-Null
Write-Output "C:\APPS created (or already present)"

$s = (Get-ChildItem $src -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum)
Write-Output ("source: " + [math]::Round($s.Sum/1GB,2) + " GB, " + $s.Count + " files")
Write-Output "copying..."

& robocopy.exe $src $dst /E /MT:16 /R:1 /W:1 /NFL /NDL /NP /NJH
$rc = $LASTEXITCODE
Write-Output ("robocopy exit: " + $rc + "  (0-7 ok)")
if ($rc -ge 8) { Write-Output "FATAL: copy failed - source untouched"; exit 1 }

Write-Output ""
Write-Output "=== verify the copy ==="
$d = (Get-ChildItem $dst -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum)
Write-Output ("dest  : " + [math]::Round($d.Sum/1GB,2) + " GB, " + $d.Count + " files")
Write-Output ("file count match: " + ($d.Count -eq $s.Count))

foreach ($f in @('avatar_studio.py','start_studio.py','.venv\Scripts\python.exe')) {
    $p = Join-Path $dst $f
    Write-Output ("  " + $f.PadRight(30) + " " + (Test-Path $p))
}

$vpy = Join-Path $dst '.venv\Scripts\python.exe'
if (Test-Path $vpy) {
    Write-Output ""
    Write-Output "=== venv in the new location ==="
    Write-Output ("  version : " + (& $vpy -V 2>&1))
    Write-Output ("  base    : " + (& $vpy -c "import sys;print(sys.base_prefix)" 2>&1))
    Write-Output "  (base still names C:\1-AI\APPS\PYTHON - the junction bridge keeps this working)"
}

Write-Output ""
Write-Output ("Original retained at " + $src + " until references are updated.")
Write-Output "=== DONE ==="

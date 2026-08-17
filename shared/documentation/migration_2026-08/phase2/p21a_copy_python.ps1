# Phase 2.1a - copy the Python tree to C:\Program Files\Python311.
# Excludes the nested venvs/ and testenv/ dirs: those are venvs with hardcoded
# paths, not part of the interpreter.
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

$src = 'C:\1-AI\APPS\PYTHON'
$dst = 'C:\Program Files\Python311'

Write-Output ("Source: " + $src)
Write-Output ("Dest  : " + $dst)
Write-Output ""

$sz = (Get-ChildItem $src -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
Write-Output ("Source size incl. excluded dirs: " + [math]::Round($sz/1GB,2) + " GB")
Write-Output ""
Write-Output "Copying (this takes a few minutes)..."

$rcArgs = @(
    $src, $dst,
    '/E',
    '/XD', (Join-Path $src 'venvs'), (Join-Path $src 'testenv'),
    '/MT:16',
    '/R:1', '/W:1',
    '/NFL', '/NDL', '/NP', '/NJH'
)
& robocopy.exe @rcArgs
$rc = $LASTEXITCODE
Write-Output ("robocopy exit code: " + $rc + "  (0-7 = success, 8+ = failure)")

Write-Output ""
Write-Output "=== Verify new interpreter ==="
$np = Join-Path $dst 'python.exe'
if (Test-Path $np) {
    Write-Output ("  version: " + (& $np -V 2>&1))
    Write-Output ("  sys.prefix: " + (& $np -c "import sys;print(sys.prefix)" 2>&1))
    $spc = (Get-ChildItem (Join-Path $dst 'Lib\site-packages') -ErrorAction SilentlyContinue).Count
    Write-Output ("  site-packages entries: " + $spc)
} else {
    Write-Output "  ERROR: python.exe not found at destination"
}

Write-Output "=== DONE ==="

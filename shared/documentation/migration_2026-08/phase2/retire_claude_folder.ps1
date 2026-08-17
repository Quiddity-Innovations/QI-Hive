# Retire the C:\CLAUDE husk the same way C:\1-AI was retired: rename rather
# than delete, so Renne reviews and removes it.
#
# All 28 remaining files were verified as already present at C:\APPS\CLAUDE, so
# nothing unique lives here. They were locked by memory-mapped .pyd modules; the
# reboot should have released them.
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

$src     = 'C:\CLAUDE'
$retired = 'C:\CLAUDE.RETIRED_2026-08-09'
$new     = 'C:\APPS\CLAUDE'

if (-not (Test-Path $src)) { Write-Output "C:\CLAUDE already gone"; exit 0 }

$files = @(Get-ChildItem $src -Recurse -File -Force -ErrorAction SilentlyContinue)
Write-Output ("files remaining in C:\CLAUDE : " + $files.Count)

# Re-confirm every one exists at the destination before retiring anything.
$missing = @()
foreach ($f in $files) {
    $rel = $f.FullName.Substring($src.Length).TrimStart('\')
    if (-not (Test-Path (Join-Path $new $rel))) { $missing += $rel }
}
Write-Output ("not present at C:\APPS\CLAUDE : " + $missing.Count)
foreach ($m in $missing) { Write-Output ("   UNIQUE: " + $m) }
if ($missing.Count -gt 0) {
    Write-Output ""
    Write-Output "Copying the unique ones across before retiring."
    foreach ($rel in $missing) {
        $d = Join-Path $new $rel
        New-Item -ItemType Directory -Path (Split-Path $d) -Force | Out-Null
        Copy-Item (Join-Path $src $rel) $d -Force -ErrorAction SilentlyContinue
        Write-Output ("   copied " + $rel + " -> " + (Test-Path $d))
    }
}

Write-Output ""
Write-Output "=== renaming ==="
if (Test-Path $retired) {
    Write-Output ("  " + $retired + " already exists - merging into it instead")
    & robocopy.exe $src $retired /E /MOVE /R:1 /W:1 /NFL /NDL /NP /NJH /NJS | Out-Null
    if ((@(Get-ChildItem $src -Recurse -File -Force -ErrorAction SilentlyContinue).Count) -eq 0) {
        Remove-Item $src -Recurse -Force -ErrorAction SilentlyContinue
    }
} else {
    try {
        Rename-Item -Path $src -NewName (Split-Path $retired -Leaf) -ErrorAction Stop
        Write-Output ("  " + $src + "  ->  " + $retired)
    } catch {
        Write-Output ("  rename failed: " + $_.Exception.Message)
        Write-Output "  falling back to a move"
        & robocopy.exe $src $retired /E /MOVE /R:1 /W:1 /NFL /NDL /NP /NJH /NJS | Out-Null
        if ((@(Get-ChildItem $src -Recurse -File -Force -ErrorAction SilentlyContinue).Count) -eq 0) {
            Remove-Item $src -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Output ""
Write-Output "=== confirm ==="
Write-Output ("  C:\CLAUDE exists          : " + (Test-Path $src) + "   (must be False)")
Write-Output ("  C:\CLAUDE.RETIRED exists  : " + (Test-Path $retired))
Write-Output ("  C:\APPS\CLAUDE exists     : " + (Test-Path $new))

Write-Output ""
Write-Output "=== services still healthy? ==="
foreach ($s in @('QI_Headroom','QI_ClaudeVoiceControl','QI_ClaudeVoiceLine','QI_ClaudeVoiceTelegram')) {
    Write-Output ("  " + $s.PadRight(24) + " " + (Get-Service $s -ErrorAction SilentlyContinue).Status)
}
Write-Output ("  headroom on 9020 : " + [bool](Get-NetTCPConnection -LocalPort 9020 -State Listen -ErrorAction SilentlyContinue))
Write-Output "=== DONE ==="

# What exactly is queued to happen at the next reboot?
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

$p = Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager' -Name PendingFileRenameOperations -ErrorAction SilentlyContinue
if (-not $p) { Write-Output "No PendingFileRenameOperations."; exit }

$ops = $p.PendingFileRenameOperations
Write-Output ("raw entries: " + $ops.Count)
Write-Output ""

# Entries come in pairs: source, destination. Empty destination = DELETE at boot.
$pairs = @()
for ($i = 0; $i -lt $ops.Count; $i += 2) {
    $src = $ops[$i]
    $dst = if (($i + 1) -lt $ops.Count) { $ops[$i + 1] } else { '' }
    $pairs += [pscustomobject]@{ Source = $src; Dest = $dst }
}

$danger = @()
foreach ($pr in $pairs) {
    $s = $pr.Source -replace '^\\\?\?\\', ''
    $d = $pr.Dest   -replace '^(!|\\\?\?\\)+', ''
    $action = if ([string]::IsNullOrWhiteSpace($pr.Dest)) { 'DELETE' } else { 'RENAME' }
    $flag = ''
    if ($s -match '1-AI|Python|python') { $flag = '  <<< PYTHON'; $danger += $pr }
    Write-Output ("[" + $action + "] " + $s + $flag)
    if ($action -eq 'RENAME') { Write-Output ("          -> " + $d) }
}

Write-Output ""
Write-Output ("=== entries touching Python / 1-AI: " + $danger.Count + " ===")

Write-Output ""
Write-Output "=== Does the LIVE python still have its critical files? ==="
foreach ($f in @('C:\1-AI\APPS\PYTHON\python.exe',
                 'C:\1-AI\APPS\PYTHON\python311.dll',
                 'C:\1-AI\APPS\PYTHON\python3.dll',
                 'C:\1-AI\APPS\PYTHON\vcruntime140.dll')) {
    Write-Output ("  " + (Test-Path $f) + "  " + $f)
}
Write-Output "=== DONE ==="

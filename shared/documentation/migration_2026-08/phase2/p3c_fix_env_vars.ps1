# Phase 3c - repoint the HuggingFace cache environment variables off C:\1-AI.
#
# HF_HOME, HUGGINGFACE_HUB_CACHE and TRANSFORMERS_CACHE all name
# C:\1-AI\MODELS\HuggingFace\... Those subfolders do not actually exist, so the
# variables have been dead for some time and libraries have been falling back
# to %USERPROFILE%\.cache\huggingface. Nothing needs migrating - but they must
# stop naming a tree that is about to be deleted.
#
# New home: D:\AI\huggingface, beside the ComfyUI models. Model caches belong on
# D: (1.19 TB free) rather than C:, and that is where Phase 1 already put the
# ComfyUI weights.
#
# Machine-scope variables are used so LocalSystem services see them too.
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

$base = 'D:\AI\huggingface'
$map = @{
    'HF_HOME'               = (Join-Path $base 'hf_home')
    'HUGGINGFACE_HUB_CACHE' = (Join-Path $base 'hub')
    'TRANSFORMERS_CACHE'    = (Join-Path $base 'transformers')
}

Write-Output "=== BEFORE ==="
foreach ($n in $map.Keys) {
    $m = [Environment]::GetEnvironmentVariable($n, 'Machine')
    $u = [Environment]::GetEnvironmentVariable($n, 'User')
    Write-Output ("  " + $n.PadRight(24) + " machine=" + $m + "   user=" + $u)
}

Write-Output ""
Write-Output "=== creating destination folders ==="
foreach ($v in $map.Values) {
    New-Item -ItemType Directory -Path $v -Force | Out-Null
    Write-Output ("  " + $v + "  exists=" + (Test-Path $v))
}

Write-Output ""
Write-Output "=== rewriting ==="
foreach ($n in $map.Keys) {
    $new = $map[$n]
    foreach ($scope in @('Machine','User')) {
        $cur = [Environment]::GetEnvironmentVariable($n, $scope)
        if ($cur -and $cur -like '*1-AI*') {
            [Environment]::SetEnvironmentVariable($n, $new, $scope)
            Write-Output ("  " + $n + " [" + $scope + "] -> " + $new)
        } elseif (-not $cur -and $scope -eq 'Machine') {
            [Environment]::SetEnvironmentVariable($n, $new, $scope)
            Write-Output ("  " + $n + " [Machine] set -> " + $new)
        }
    }
}

Write-Output ""
Write-Output "=== AFTER ==="
foreach ($n in $map.Keys) {
    $m = [Environment]::GetEnvironmentVariable($n, 'Machine')
    $u = [Environment]::GetEnvironmentVariable($n, 'User')
    Write-Output ("  " + $n.PadRight(24) + " machine=" + $m + "   user=" + $u)
}

Write-Output ""
Write-Output "=== any remaining env var naming 1-AI (either scope)? ==="
$left = 0
foreach ($scope in @('Machine','User')) {
    $vars = [Environment]::GetEnvironmentVariables($scope)
    foreach ($k in $vars.Keys) {
        if ("" + $vars[$k] -like '*1-AI*') {
            Write-Output ("  " + $scope + "  " + $k + " = " + $vars[$k])
            $left++
        }
    }
}
Write-Output ("  remaining: " + $left)
Write-Output ""
Write-Output "NOTE: existing processes keep the old values until they restart."
Write-Output "=== DONE ==="

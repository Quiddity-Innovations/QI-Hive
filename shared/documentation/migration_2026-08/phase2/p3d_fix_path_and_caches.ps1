# Phase 3d - clean C:\1-AI out of PATH and the remaining cache variables.
#
# PATH edits are the most dangerous change in this whole migration: a mangled
# PATH breaks every new shell on the machine. So:
#   - both PATHs are exported verbatim to a timestamped .txt first
#   - entries are handled as a list, never as one blob of text
#   - a Python entry is REWRITTEN to the new interpreter (not dropped)
#   - an entry whose target no longer exists is DROPPED
#   - VSCode's entry is left alone for now: it is repointed when VSCode is
#     reinstalled, and dropping it early would break `code` from the terminal
#
# Pure ASCII only.
param([switch]$Apply)
$ErrorActionPreference = 'Continue'

$backupDir = 'C:\QIH\shared\documentation\migration_2026-08\phase2\rollback'
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

$oldPy1 = 'C:\1-AI\APPS\PYTHON'
$oldPy2 = 'C:\1-AI\Apps\Python'          # user PATH uses different casing
$newPy  = 'C:\Program Files\Python311'

# ---------- PATH ----------------------------------------------------------
foreach ($scope in @('Machine','User')) {
    Write-Output ("================ " + $scope + " PATH ================")
    $cur = [Environment]::GetEnvironmentVariable('Path', $scope)
    if (-not $cur) { Write-Output "  (empty)"; continue }

    $bak = Join-Path $backupDir ("PATH_" + $scope + "_before.txt")
    if (-not (Test-Path $bak)) { Set-Content -Path $bak -Value $cur -Encoding ASCII }
    Write-Output ("  backup: " + $bak)

    $parts = $cur -split ';' | Where-Object { $_.Trim() -ne '' }
    Write-Output ("  entries: " + $parts.Count)

    $out = @()
    foreach ($p in $parts) {
        $t = $p.TrimEnd('\')
        if ($t -like "$oldPy1*" -or $t -like "$oldPy2*") {
            # Python entry: rewrite to the migrated interpreter.
            $suffix = ''
            if ($t -match '(?i)\\Scripts$') { $suffix = '\Scripts' }
            $rep = $newPy + $suffix
            if ($out -notcontains $rep) {
                Write-Output ("    REWRITE  " + $p + "   ->  " + $rep)
                $out += $rep
            } else {
                Write-Output ("    DROP-DUP " + $p)
            }
        }
        elseif ($t -like '*1-AI*') {
            if (Test-Path $t) {
                Write-Output ("    KEEP     " + $p + "   (still exists - handled at reinstall)")
                $out += $p
            } else {
                Write-Output ("    DROP     " + $p + "   (target does not exist)")
            }
        }
        else {
            $out += $p
        }
    }

    $new = ($out -join ';')
    if ($new -ne $cur) {
        Write-Output ("  new entry count: " + $out.Count)
        if ($Apply) {
            [Environment]::SetEnvironmentVariable('Path', $new, $scope)
            Write-Output "  APPLIED"
        } else {
            Write-Output "  (dry run)"
        }
    } else {
        Write-Output "  no change needed"
    }
    Write-Output ""
}

# ---------- remaining cache variables -------------------------------------
Write-Output "================ cache variables ================"
$caches = @{
    'TORCH_HOME'      = 'D:\AI\huggingface\torch'
    'DIFFUSERS_CACHE' = 'D:\AI\huggingface\diffusers'
    'PIP_CACHE_DIR'   = 'D:\AI\cache\pip'
}
foreach ($n in $caches.Keys) {
    $new = $caches[$n]
    foreach ($scope in @('Machine','User')) {
        $cur = [Environment]::GetEnvironmentVariable($n, $scope)
        if ($cur -and $cur -like '*1-AI*') {
            Write-Output ("  " + $n + " [" + $scope + "]  " + $cur + "  ->  " + $new)
            if ($Apply) {
                New-Item -ItemType Directory -Path $new -Force | Out-Null
                [Environment]::SetEnvironmentVariable($n, $new, $scope)
            }
        }
    }
}

Write-Output ""
Write-Output "================ verify ================"
$left = 0
foreach ($scope in @('Machine','User')) {
    $vars = [Environment]::GetEnvironmentVariables($scope)
    foreach ($k in $vars.Keys) {
        $v = "" + $vars[$k]
        if ($v -like '*1-AI*') {
            $left++
            if ($k -ieq 'Path') {
                $bits = $v -split ';' | Where-Object { $_ -like '*1-AI*' }
                foreach ($b in $bits) { Write-Output ("  " + $scope + " PATH still has: " + $b) }
            } else {
                Write-Output ("  " + $scope + "  " + $k + " = " + $v)
            }
        }
    }
}
Write-Output ("  variables still naming 1-AI: " + $left)
if (-not $Apply) { Write-Output ""; Write-Output "DRY RUN - re-run with -Apply to write." }
Write-Output "=== DONE ==="

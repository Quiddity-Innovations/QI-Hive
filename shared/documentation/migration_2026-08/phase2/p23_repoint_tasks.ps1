# Phase 2.3 - repoint scheduled tasks from C:\1-AI\APPS\PYTHON to
# C:\Program Files\Python311.
#
# Scans BOTH Execute and Arguments: eight tasks hide the interpreter path
# inside "conhost.exe --headless <python> <script>" arguments, so a scan of
# Execute alone misses them.
#
# Because the new path contains a space, a bare substitution inside an
# Arguments string would split into two tokens. Any replacement that lands in
# Arguments and is not already quoted gets quoted here.
#
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

$oldDir = 'C:\1-AI\APPS\PYTHON'
$newDir = 'C:\Program Files\Python311'

function Convert-ArgString {
    param([string]$s)
    if (-not $s) { return $s }
    # Already-quoted occurrences: just swap the directory, quoting is intact.
    $out = $s -replace [regex]::Escape('"' + $oldDir + '\'), ('"' + $newDir + '\')
    # Bare occurrences: swap and add quotes around the whole executable token.
    $out = [regex]::Replace($out, [regex]::Escape($oldDir + '\') + '(\w+\.exe)', ('"' + $newDir + '\$1"'))
    return $out
}

$report = @()

foreach ($t in (Get-ScheduledTask)) {
    $needs = $false
    foreach ($a in $t.Actions) {
        if (($a.Execute -like "*$oldDir*") -or ($a.Arguments -like "*$oldDir*")) { $needs = $true }
    }
    if (-not $needs) { continue }

    $full = $t.TaskPath + $t.TaskName
    Write-Output ("TASK: " + $full)

    $newActions = @()
    foreach ($a in $t.Actions) {
        $ex = $a.Execute
        $ar = $a.Arguments
        $wd = $a.WorkingDirectory

        if ($ex -like "*$oldDir*") {
            $ex = $ex.Replace($oldDir, $newDir).Trim('"')
            Write-Output ("   EXEC -> " + $ex)
        }
        if ($ar -like "*$oldDir*") {
            $ar = Convert-ArgString $ar
            Write-Output ("   ARGS -> " + $ar)
        }
        if ($wd -like "*$oldDir*") { $wd = $wd.Replace($oldDir, $newDir) }

        if ($wd) {
            $newActions += New-ScheduledTaskAction -Execute $ex -Argument $ar -WorkingDirectory $wd
        } elseif ($ar) {
            $newActions += New-ScheduledTaskAction -Execute $ex -Argument $ar
        } else {
            $newActions += New-ScheduledTaskAction -Execute $ex
        }
    }

    try {
        Set-ScheduledTask -TaskPath $t.TaskPath -TaskName $t.TaskName -Action $newActions -ErrorAction Stop | Out-Null
        Write-Output "   RESULT: updated"
        $report += ($full + " = updated")
    } catch {
        Write-Output ("   RESULT: FAILED - " + $_.Exception.Message)
        $report += ($full + " = FAILED")
    }
    Write-Output ""
}

Write-Output "=== Verify: any task still referencing the old path? ==="
$left = 0
foreach ($t in (Get-ScheduledTask)) {
    foreach ($a in $t.Actions) {
        if (($a.Execute -like "*$oldDir*") -or ($a.Arguments -like "*$oldDir*")) {
            Write-Output ("  STILL STALE: " + $t.TaskPath + $t.TaskName)
            $left++
        }
    }
}
Write-Output ("  remaining stale tasks: " + $left)
Write-Output ""
$report | ForEach-Object { Write-Output ("  " + $_) }
Write-Output "=== DONE ==="

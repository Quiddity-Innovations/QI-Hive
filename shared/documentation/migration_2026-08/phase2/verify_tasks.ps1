# Verify every scheduled task that references Python: does its interpreter and
# its target script actually exist? Repointing a task at a real interpreter is
# no good if the script it runs was deleted in an earlier migration.
# Must run ELEVATED - some tasks are invisible to a non-admin enumeration.
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

$rx = '([A-Za-z]:\\[^"'']*?\.(?:py|pyw))'

foreach ($t in (Get-ScheduledTask)) {
    foreach ($a in $t.Actions) {
        $blob = "" + $a.Execute + " " + $a.Arguments
        if ($blob -notmatch 'python|\.py') { continue }

        $full = $t.TaskPath + $t.TaskName
        Write-Output ("TASK: " + $full + "   [" + $t.State + "]")

        # interpreter
        $exe = $a.Execute
        if ($exe -match 'conhost') {
            if ($a.Arguments -match '("?)([A-Za-z]:\\[^"]*?python w?\.exe|[A-Za-z]:\\[^"]*?python\.exe|[A-Za-z]:\\[^"]*?pythonw\.exe)') {
                $exe = $Matches[2]
            }
        }
        $exe = $exe.Trim('"')
        $exeOk = Test-Path $exe
        Write-Output ("   interpreter: " + $exe + "   EXISTS=" + $exeOk)

        # target script(s)
        $scripts = [regex]::Matches($blob, $rx) | ForEach-Object { $_.Groups[1].Value } | Select-Object -Unique
        foreach ($s in $scripts) {
            Write-Output ("   script     : " + $s + "   EXISTS=" + (Test-Path $s))
        }
        if (-not $scripts) {
            Write-Output ("   script     : (module form) args = " + $a.Arguments)
        }
        Write-Output ""
    }
}
Write-Output "=== DONE ==="

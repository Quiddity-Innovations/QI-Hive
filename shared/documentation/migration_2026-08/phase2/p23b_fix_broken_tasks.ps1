# Phase 2.3b - repair three scheduled tasks that were already broken before
# this migration started. None of these reference C:\1-AI, so the Phase 2.3
# pass did not touch their targets.
#
#  QI_NightlyBackup  -> C:\UNIVERSAL\qi_brain\tools\backup.py
#                       C:\UNIVERSAL no longer exists. The same file now lives
#                       at C:\QIH\engine\brain\tools\backup.py - it moved during
#                       the UNIVERSAL->QIH migration and the task was missed.
#
#  MaiaReconcile     -> C:\QI\.venv\Scripts\python.exe
#  MaiaRevertMiMo       That venv does not exist. Both have been failing
#                       silently. Point them at the migrated interpreter, which
#                       carries all 473 packages.
#
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

$py = 'C:\Program Files\Python311\python.exe'

function Repair-Task {
    param([string]$Path, [string]$Name, [scriptblock]$Build, [string]$Why)

    $t = Get-ScheduledTask -TaskPath $Path -TaskName $Name -ErrorAction SilentlyContinue
    if (-not $t) { Write-Output ("  SKIP " + $Path + $Name + " - not found"); return }

    Write-Output ($Path + $Name)
    Write-Output ("   reason: " + $Why)
    foreach ($a in $t.Actions) {
        Write-Output ("   was : " + $a.Execute + " " + $a.Arguments)
    }
    $action = & $Build
    try {
        Set-ScheduledTask -TaskPath $Path -TaskName $Name -Action $action -ErrorAction Stop | Out-Null
        $after = (Get-ScheduledTask -TaskPath $Path -TaskName $Name).Actions[0]
        Write-Output ("   now : " + $after.Execute + " " + $after.Arguments)
        Write-Output "   RESULT: repaired"
    } catch {
        Write-Output ("   RESULT: FAILED - " + $_.Exception.Message)
    }
    Write-Output ""
}

Write-Output "=== Repairing pre-existing broken tasks ==="
Write-Output ""

Repair-Task -Path '\' -Name 'QI_NightlyBackup' -Why 'target script moved in the UNIVERSAL->QIH migration' -Build {
    New-ScheduledTaskAction -Execute $py `
        -Argument '"C:\QIH\engine\brain\tools\backup.py"' `
        -WorkingDirectory 'C:\QIH\engine\brain\tools'
}

Repair-Task -Path '\' -Name 'MaiaReconcile' -Why 'C:\QI\.venv does not exist' -Build {
    New-ScheduledTaskAction -Execute 'conhost.exe' `
        -Argument ('--headless "' + $py + '" "C:\QI\maia_reconcile.py"')
}

Repair-Task -Path '\' -Name 'MaiaRevertMiMo' -Why 'C:\QI\.venv does not exist' -Build {
    New-ScheduledTaskAction -Execute 'conhost.exe' `
        -Argument ('--headless "' + $py + '" "C:\QI\TOOLS\revert_mimo.py"')
}

Write-Output "=== Final sweep: every python task, do interpreter and script exist? ==="
$bad = 0
foreach ($t in (Get-ScheduledTask)) {
    foreach ($a in $t.Actions) {
        $blob = "" + $a.Execute + " " + $a.Arguments
        if ($blob -notmatch 'python|\.py') { continue }

        # interpreter = the .exe token, whether bare or quoted
        $exe = $null
        if ($blob -match '"([A-Za-z]:\\[^"]*?\.exe)"') { $exe = $Matches[1] }
        elseif ($blob -match '([A-Za-z]:\\[^\s"]*?python w?\.exe)') { $exe = $Matches[1] }
        elseif ($blob -match '([A-Za-z]:\\[^\s"]*?pythonw?\.exe)') { $exe = $Matches[1] }
        elseif ($a.Execute -match 'python') { $exe = $a.Execute.Trim('"') }

        # script = a .py token, quoted or bare, not preceded by a drive-letter exe
        $script = $null
        if ($blob -match '"([A-Za-z]:\\[^"]*?\.pyw?)"') { $script = $Matches[1] }
        elseif ($blob -match '(?<=\s)([A-Za-z]:\\[^\s"]*?\.pyw?)(?=\s|$)') { $script = $Matches[1] }

        $eOk = if ($exe)    { Test-Path $exe }    else { $true }
        $sOk = if ($script) { Test-Path $script } else { $true }

        if (-not $eOk -or -not $sOk) {
            $bad++
            Write-Output ("  BROKEN " + $t.TaskPath + $t.TaskName)
            if (-not $eOk) { Write-Output ("     missing interpreter: " + $exe) }
            if (-not $sOk) { Write-Output ("     missing script     : " + $script) }
        }
    }
}
Write-Output ("  tasks still broken: " + $bad)
Write-Output "=== DONE ==="

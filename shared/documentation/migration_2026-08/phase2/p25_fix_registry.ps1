# Phase 2.5 - correct the PythonCore registration.
#
# Both HKLM and HKCU SOFTWARE\Python\PythonCore\3.11 still name
# C:\1-AI\APPS\PYTHON. That directory is about to be deleted in Phase 3, and
# anything that discovers Python through the registry (the py launcher, some
# installers, a few IDEs) would then resolve to a path that no longer exists.
#
# Every key is exported to .reg first, so this is reversible with a double-click.
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

$newDir   = 'C:\Program Files\Python311'
$backup   = 'C:\QIH\shared\documentation\migration_2026-08\phase2\rollback\registry'
New-Item -ItemType Directory -Path $backup -Force | Out-Null

Write-Output "=== STEP 1: back up the keys ==="
foreach ($pair in @(
    @('HKLM\SOFTWARE\Python', 'HKLM_Python.reg'),
    @('HKCU\SOFTWARE\Python', 'HKCU_Python.reg'))) {
    $out = Join-Path $backup $pair[1]
    & reg.exe export $pair[0] $out /y 2>&1 | Out-Null
    if (Test-Path $out) {
        Write-Output ("  saved " + $out + "  (" + (Get-Item $out).Length + " bytes)")
    } else {
        Write-Output ("  WARNING: export failed for " + $pair[0])
    }
}

Write-Output ""
Write-Output "=== STEP 2: current state ==="
foreach ($root in @('HKLM:\SOFTWARE\Python\PythonCore', 'HKCU:\SOFTWARE\Python\PythonCore')) {
    if (-not (Test-Path $root)) { Write-Output ("  (absent) " + $root); continue }
    Get-ChildItem $root | ForEach-Object {
        Write-Output ("  " + $_.PSPath.Replace('Microsoft.PowerShell.Core\Registry::',''))
        Get-ChildItem $_.PSPath -ErrorAction SilentlyContinue | ForEach-Object {
            $d = (Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).'(default)'
            Write-Output ("      " + $_.PSChildName + " = " + $d)
        }
    }
}

Write-Output ""
Write-Output "=== STEP 3: rewrite any value naming the old tree ==="
$changed = 0
foreach ($root in @('HKLM:\SOFTWARE\Python', 'HKCU:\SOFTWARE\Python')) {
    if (-not (Test-Path $root)) { continue }
    Get-ChildItem $root -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
        $key = $_
        $props = Get-ItemProperty $key.PSPath -ErrorAction SilentlyContinue
        if (-not $props) { return }
        foreach ($p in $props.PSObject.Properties) {
            if ($p.Name -in @('PSPath','PSParentPath','PSChildName','PSDrive','PSProvider')) { continue }
            if ($p.Value -is [string] -and $p.Value -like '*1-AI\APPS\PYTHON*') {
                $new = $p.Value -replace [regex]::Escape('C:\1-AI\APPS\PYTHON'), $newDir
                $short = $key.PSPath.Replace('Microsoft.PowerShell.Core\Registry::','')
                Write-Output ("  " + $short)
                Write-Output ("     " + $p.Name + ":")
                Write-Output ("        old: " + $p.Value)
                Write-Output ("        new: " + $new)
                Set-ItemProperty -Path $key.PSPath -Name $p.Name -Value $new -ErrorAction SilentlyContinue
                $changed++
            }
        }
    }
}
Write-Output ("  values rewritten: " + $changed)

Write-Output ""
Write-Output "=== STEP 4: verify ==="
foreach ($hive in @('HKLM:\SOFTWARE\Python\PythonCore\3.11\InstallPath',
                    'HKCU:\SOFTWARE\Python\PythonCore\3.11\InstallPath')) {
    if (Test-Path $hive) {
        Write-Output ("  " + $hive + " -> " + (Get-ItemProperty $hive).'(default)')
    } else {
        Write-Output ("  (absent) " + $hive)
    }
}

$left = 0
foreach ($root in @('HKLM:\SOFTWARE\Python', 'HKCU:\SOFTWARE\Python')) {
    if (-not (Test-Path $root)) { continue }
    Get-ChildItem $root -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
        $props = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
        if ($props) {
            foreach ($p in $props.PSObject.Properties) {
                if ($p.Value -is [string] -and $p.Value -like '*1-AI*') { $left++ }
            }
        }
    }
}
Write-Output ("  values still naming 1-AI: " + $left)

Write-Output ""
Write-Output "=== STEP 5: py launcher view ==="
& py -0p 2>&1 | ForEach-Object { Write-Output ("  " + $_) }

Write-Output ""
Write-Output "=== STEP 6: leftover per-user bundle record ==="
$b = Get-ItemProperty 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue |
     Where-Object { $_.DisplayName -match 'Python 3\.11' }
if ($b) {
    foreach ($x in $b) { Write-Output ("  still listed: " + $x.DisplayName + "  key " + $x.PSChildName) }
    Write-Output "  (left in place deliberately - removing an uninstall record by hand can"
    Write-Output "   strand the Package Cache. It is cosmetic and harms nothing.)"
} else {
    Write-Output "  none - bundle record fully removed"
}
Write-Output "=== DONE ==="

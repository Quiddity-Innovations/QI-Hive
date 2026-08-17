# Did the per-machine install actually register, or did Burn go sideways again?
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

Write-Output "=== Installed Python bundles ==="
foreach ($k in @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
                 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
                 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*')) {
    $scope = if ($k -like 'HKCU*') { 'PerUser   ' } else { 'PerMachine' }
    Get-ChildItem $k -ErrorAction SilentlyContinue | ForEach-Object {
        $props = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
        if ($props.DisplayName -match 'Python') {
            Write-Output ("  [" + $scope + "] " + $props.DisplayName + "  v" + $props.DisplayVersion)
            if ($props.InstallLocation) { Write-Output ("        loc: " + $props.InstallLocation) }
            Write-Output ("        key: " + $_.PSChildName)
        }
    }
}

Write-Output ""
Write-Output "=== All PythonCore registrations ==="
foreach ($hive in @('HKLM:\SOFTWARE\Python\PythonCore',
                    'HKLM:\SOFTWARE\WOW6432Node\Python\PythonCore',
                    'HKCU:\SOFTWARE\Python\PythonCore')) {
    if (Test-Path $hive) {
        Write-Output ("  " + $hive)
        Get-ChildItem $hive | ForEach-Object {
            $ip = Join-Path $_.PSPath 'InstallPath'
            $val = if (Test-Path $ip) { (Get-ItemProperty $ip).'(default)' } else { '(none)' }
            Write-Output ("     " + $_.PSChildName + " -> " + $val)
        }
    } else {
        Write-Output ("  (absent) " + $hive)
    }
}

Write-Output ""
Write-Output "=== Old tree: what survived the uninstall? ==="
$old = 'C:\1-AI\APPS\PYTHON'
foreach ($f in @('python.exe','pythonw.exe','python311.dll','python3.dll','vcruntime140.dll')) {
    Write-Output ("  " + $f.PadRight(18) + " : " + (Test-Path (Join-Path $old $f)))
}
$lib = Join-Path $old 'Lib\site-packages'
Write-Output ("  site-packages dirs : " + (Get-ChildItem $lib -ErrorAction SilentlyContinue).Count)
if (Test-Path (Join-Path $old 'python.exe')) {
    Write-Output ("  old python -V      : " + (& (Join-Path $old 'python.exe') -V 2>&1))
}

Write-Output ""
Write-Output "=== New tree marker files (proof the installer wrote here) ==="
foreach ($f in @('python.exe','python311.dll','Lib\site-packages\pip','Scripts\pip.exe','LICENSE.txt')) {
    $p = Join-Path 'C:\Program Files\Python311' $f
    if (Test-Path $p) {
        $it = Get-Item $p
        Write-Output ("  " + $f.PadRight(28) + " mtime " + $it.LastWriteTime)
    } else {
        Write-Output ("  " + $f.PadRight(28) + " ABSENT")
    }
}

Write-Output ""
Write-Output "=== py launcher ==="
& py -0p 2>&1 | ForEach-Object { Write-Output ("  " + $_) }
Write-Output ("  launcher exe: " + (Get-Command py -ErrorAction SilentlyContinue).Source)

Write-Output "=== DONE ==="

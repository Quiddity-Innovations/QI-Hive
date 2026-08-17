# Where does Python stand after the migration?
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

$new = 'C:\Program Files\Python311'

Write-Output "=== 1. installs on disk ==="
foreach ($p in @("$new\python.exe",
                 'C:\1-AI\APPS\PYTHON\python.exe',
                 'C:\1-AI.RETIRED_2026-08-09\APPS\PYTHON\python.exe')) {
    if (Test-Path $p) {
        Write-Output ("  EXISTS  " + $p + "   -> " + (& $p -V 2>&1))
    } else {
        Write-Output ("  absent  " + $p)
    }
}
$j = Get-Item 'C:\1-AI\APPS\PYTHON' -Force -ErrorAction SilentlyContinue
if ($j -and $j.Target) { Write-Output ("  (the C:\1-AI path is a JUNCTION -> " + $j.Target + ")") }

Write-Output ""
Write-Output "=== 2. registration ==="
foreach ($h in @('HKLM:\SOFTWARE\Python\PythonCore\3.11\InstallPath',
                 'HKCU:\SOFTWARE\Python\PythonCore\3.11\InstallPath')) {
    if (Test-Path $h) { Write-Output ("  " + $h.Split('\')[0] + " -> " + (Get-ItemProperty $h).'(default)') }
}
Write-Output "  py launcher:"
& py -0p 2>&1 | ForEach-Object { Write-Output ("    " + $_) }

Write-Output ""
Write-Output "=== 3. scope: per-machine or per-user? ==="
$pm = 0; $pu = 0
foreach ($k in @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
                 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*')) {
    Get-ChildItem $k -ErrorAction SilentlyContinue | ForEach-Object {
        $pr = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
        if ($pr.DisplayName -match 'Python 3\.11') {
            if ($k -like 'HKCU*') { $pu++; Write-Output ("  [PerUser]    " + $pr.DisplayName) }
            else { $pm++ }
        }
    }
}
Write-Output ("  per-machine component packages: " + $pm)
Write-Output ("  per-user leftovers            : " + $pu)

Write-Output ""
Write-Output "=== 4. PATH as STORED (what a new logon gets) ==="
foreach ($scope in @('Machine','User')) {
    $p = [Environment]::GetEnvironmentVariable('Path', $scope)
    $py = $p -split ';' | Where-Object { $_ -match 'python' }
    foreach ($e in $py) { Write-Output ("  " + $scope + ": " + $e + "   resolves=" + (Test-Path $e)) }
}

Write-Output ""
Write-Output "=== 5. what still depends on the junction? ==="
$venvs = @('C:\M2V\.venv','C:\M2V\venv-video','C:\PersonalSong\.venv',
           'C:\PersonalSong\seed-vc\.venv','C:\QIP\Bakeoff\.venv',
           'C:\APPS\AvatarStudio\.venv','C:\QIH\hive\OpenSpace\.venv',
           'C:\Users\renne\venv-video','C:\Users\renne\pipx\shared',
           'C:\Users\renne\pipx\venvs\headroom-ai',
           'C:\Users\renne\AppData\Local\hermes\hermes-agent\venv')
$dep = 0
foreach ($v in $venvs) {
    $cfg = Join-Path $v 'pyvenv.cfg'
    if (Test-Path $cfg) {
        $t = Get-Content $cfg -Raw
        if ($t -match '1-AI') { $dep++; Write-Output ("  needs junction: " + $v) }
    }
}
Write-Output ("  venvs still pinned to the old path: " + $dep)

Write-Output ""
Write-Output "=== 6. rebuilt venvs (no longer need the junction) ==="
foreach ($v in @('C:\CogniBase\.venv','C:\CLAUDE\Tools\headroom_env')) {
    $cfg = Join-Path $v 'pyvenv.cfg'
    if (Test-Path $cfg) {
        $home = (Get-Content $cfg | Where-Object { $_ -match '^home' }) -join ''
        Write-Output ("  " + $v.PadRight(32) + " " + $home)
    }
}

Write-Output ""
Write-Output "=== 7. consumers ==="
$svc = 0
foreach ($s in (Get-CimInstance Win32_Service | Where-Object { $_.PathName -match 'nssm' })) {
    $k = 'HKLM:\SYSTEM\CurrentControlSet\Services\' + $s.Name + '\Parameters'
    $p = Get-ItemProperty $k -ErrorAction SilentlyContinue
    if ($p.Application -like "*Python311*") { $svc++ }
}
Write-Output ("  services on C:\Program Files\Python311 : " + $svc)
$tsk = 0
foreach ($t in (Get-ScheduledTask)) {
    foreach ($a in $t.Actions) {
        if (("" + $a.Execute + " " + $a.Arguments) -match 'Program Files\\Python311') { $tsk++ }
    }
}
Write-Output ("  scheduled tasks on the new interpreter : " + $tsk)
Write-Output ("  packages installed                    : " + ((& "$new\python.exe" -m pip list 2>&1 | Measure-Object -Line).Lines - 2))
Write-Output "=== DONE ==="

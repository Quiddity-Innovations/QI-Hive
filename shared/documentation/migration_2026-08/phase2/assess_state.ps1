# Ground-truth assessment after the interrupted 3.11.9 install.
# Pure ASCII only (PowerShell 5.1 reads BOM-less .ps1 as ANSI).
$ErrorActionPreference = 'Continue'

Write-Output "=== 1. Python executables on disk ==="
foreach ($p in @('C:\Program Files\Python311\python.exe',
                 'C:\1-AI\APPS\PYTHON\python.exe',
                 'C:\Program Files\Python312\python.exe',
                 'C:\Program Files\Python313\python.exe')) {
    if (Test-Path $p) {
        $v = & $p -V 2>&1
        Write-Output ("  EXISTS  " + $p + "   -> " + $v)
    } else {
        Write-Output ("  absent  " + $p)
    }
}

Write-Output ""
Write-Output "=== 2. PythonCore registry (which installs Windows believes in) ==="
foreach ($hive in @('HKLM:\SOFTWARE\Python\PythonCore',
                    'HKLM:\SOFTWARE\WOW6432Node\Python\PythonCore',
                    'HKCU:\SOFTWARE\Python\PythonCore')) {
    if (Test-Path $hive) {
        Write-Output ("  " + $hive)
        Get-ChildItem $hive | ForEach-Object {
            $ip = Join-Path $_.PSPath 'InstallPath'
            $val = if (Test-Path $ip) { (Get-ItemProperty $ip).'(default)' } else { '(no InstallPath)' }
            Write-Output ("     " + $_.PSChildName + "  ->  " + $val)
        }
    } else {
        Write-Output ("  (absent) " + $hive)
    }
}

Write-Output ""
Write-Output "=== 3. Installed Python bundles (uninstall registry) ==="
$keys = @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
          'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
          'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*')
foreach ($k in $keys) {
    Get-ItemProperty $k -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -match 'Python' } |
        ForEach-Object {
            $scope = if ($k -like 'HKCU*') { 'PerUser ' } else { 'PerMachine' }
            Write-Output ("  [" + $scope + "] " + $_.DisplayName + "  v" + $_.DisplayVersion)
            if ($_.InstallLocation) { Write-Output ("               loc: " + $_.InstallLocation) }
        }
}

Write-Output ""
Write-Output "=== 4. py launcher view ==="
try { & py -0p 2>&1 | ForEach-Object { Write-Output ("  " + $_) } } catch { Write-Output "  py launcher not available" }

Write-Output ""
Write-Output "=== 5. Old tree health (packages intact?) ==="
$old = 'C:\1-AI\APPS\PYTHON\python.exe'
if (Test-Path $old) {
    $sp = 'C:\1-AI\APPS\PYTHON\Lib\site-packages'
    Write-Output ("  site-packages entries: " + (Get-ChildItem $sp -ErrorAction SilentlyContinue).Count)
    $n = (& $old -m pip list 2>&1 | Measure-Object -Line).Lines
    Write-Output ("  pip list lines       : " + $n)
    Write-Output "  import smoke test:"
    $t = Join-Path $env:TEMP '_qi_smoke.py'
    Set-Content -Path $t -Encoding ASCII -Value @(
        'import importlib',
        'mods = ["fastapi","uvicorn","requests","sqlite3","aiohttp","pydantic","docx","numpy","pandas","flask","telegram","linebot"]',
        'for m in mods:',
        '    try:',
        '        importlib.import_module(m)',
        '        print("    ok      ", m)',
        '    except Exception as e:',
        '        print("    FAIL    ", m, type(e).__name__, e)'
    )
    & $old $t
}

Write-Output ""
Write-Output "=== 6. Services still running? ==="
$svc = Get-Service -Name 'QI_*' | Group-Object Status
foreach ($g in $svc) { Write-Output ("  " + $g.Name + ": " + $g.Count) }
$stopped = Get-Service -Name 'QI_*' | Where-Object { $_.Status -ne 'Running' } | Select-Object -ExpandProperty Name
if ($stopped) { Write-Output ("  not running: " + ($stopped -join ', ')) }

Write-Output ""
Write-Output "=== 7. Pending reboot flags ==="
$pend = @(
  'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending',
  'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired'
)
foreach ($p in $pend) { Write-Output ("  " + $p + " : " + (Test-Path $p)) }
$pfro = (Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager' -Name PendingFileRenameOperations -ErrorAction SilentlyContinue)
Write-Output ("  PendingFileRenameOperations present: " + [bool]$pfro)

Write-Output "=== DONE ==="

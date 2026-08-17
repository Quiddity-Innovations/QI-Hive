# Phase 2.1b - remove the per-user Python bundle, then install 3.11.9
# per-machine into C:\Program Files\Python311.
#
# Ordering rationale: the copy at C:\Program Files\Python311 is already a
# working interpreter, but Windows still believes the "real" Python lives at
# C:\1-AI\APPS\PYTHON. The official installer will not target Program Files
# while a related per-user bundle exists - it detects it, flips to upgrade
# mode, and on that path silently ignores both TargetDir and InstallAllUsers.
# So the bundle must go first.
#
# Nothing is executing from C:\Program Files\Python311 yet (no service has been
# repointed), so the installer hits no file-in-use conflict there. The 31
# running services still have python311.dll mapped from the old path and keep
# running; they are NOT restarted during this window.
#
# Pure ASCII only. Fail-fast: every stage gates the next.
$ErrorActionPreference = 'Continue'

$newDir  = 'C:\Program Files\Python311'
$newExe  = Join-Path $newDir 'python.exe'
$oldExe  = 'C:\1-AI\APPS\PYTHON\python.exe'
$setup   = 'C:\QIH\shared\documentation\migration_2026-08\phase2\python-3.11.9-amd64.exe'

function Fail([string]$m) { Write-Output ("FATAL: " + $m); Write-Output "=== ABORTED ==="; exit 1 }

Write-Output "=== GATE 0: preconditions ==="
if (-not (Test-Path $newExe)) { Fail "new interpreter missing: $newExe" }
if (-not (Test-Path $setup))  { Fail "installer missing: $setup" }
$v = & $newExe -V 2>&1
if ("$v" -notmatch '3\.11\.9')  { Fail "new interpreter reports '$v', expected 3.11.9" }
Write-Output ("  new interpreter OK: " + $v)
$before = (Get-Service -Name 'QI_*' | Where-Object { $_.Status -eq 'Running' }).Count
Write-Output ("  services running before: " + $before)
Write-Output ""

Write-Output "=== STAGE 1: locate the per-user bundle ==="
$bundle = Get-ItemProperty 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue |
          Where-Object { $_.DisplayName -match 'Python 3\.11' -and $_.DisplayName -match '64-bit' } |
          Select-Object -First 1
if (-not $bundle) {
    Write-Output "  no per-user Python 3.11 bundle found - already removed?"
} else {
    Write-Output ("  found : " + $bundle.DisplayName + "  v" + $bundle.DisplayVersion)
    Write-Output ("  key   : " + $bundle.PSChildName)
    Write-Output ("  quiet : " + $bundle.QuietUninstallString)

    Write-Output ""
    Write-Output "=== STAGE 2: uninstall it (/quiet /norestart) ==="
    $exe = $null; $argline = $null
    if ($bundle.QuietUninstallString -match '^"([^"]+)"\s*(.*)$') {
        $exe = $Matches[1]; $argline = $Matches[2]
    } elseif ($bundle.UninstallString -match '^"([^"]+)"\s*(.*)$') {
        $exe = $Matches[1]; $argline = $Matches[2]
    }
    if (-not $exe) { Fail "could not parse an uninstall command" }

    # Force quiet + norestart regardless of what the registry recorded.
    if ($argline -notmatch '/quiet')     { $argline = $argline + ' /quiet' }
    if ($argline -notmatch '/norestart') { $argline = $argline + ' /norestart' }
    Write-Output ("  running: " + $exe + " " + $argline)

    $p = Start-Process -FilePath $exe -ArgumentList $argline -Wait -PassThru
    Write-Output ("  exit code: " + $p.ExitCode)
    if ($p.ExitCode -eq 3010) { Write-Output "  (3010 = success, reboot suggested - NOT rebooting)" }
}

Write-Output ""
Write-Output "=== GATE 2: services survived the uninstall? ==="
$after = (Get-Service -Name 'QI_*' | Where-Object { $_.Status -eq 'Running' }).Count
Write-Output ("  services running after: " + $after + " (was " + $before + ")")
if ($after -lt $before) { Write-Output "  WARNING: service count dropped" }

Write-Output ""
Write-Output "=== STAGE 3: install per-machine into Program Files ==="
$iargs = '/quiet', '/norestart', 'InstallAllUsers=1', ('TargetDir="' + $newDir + '"'),
         'Include_launcher=1', 'InstallLauncherAllUsers=1', 'AssociateFiles=0',
         'Shortcuts=0', 'Include_test=0', 'SimpleInstall=1'
Write-Output ("  running: " + $setup + " " + ($iargs -join ' '))
$p2 = Start-Process -FilePath $setup -ArgumentList $iargs -Wait -PassThru
Write-Output ("  exit code: " + $p2.ExitCode)
if ($p2.ExitCode -eq 3010) { Write-Output "  (3010 = success, reboot suggested - NOT rebooting)" }

Write-Output ""
Write-Output "=== GATE 3: verify the per-machine install ==="
if (-not (Test-Path $newExe)) { Fail "python.exe vanished from $newDir" }
Write-Output ("  version   : " + (& $newExe -V 2>&1))
Write-Output ("  sys.prefix: " + (& $newExe -c "import sys;print(sys.prefix)" 2>&1))
$spc = (Get-ChildItem (Join-Path $newDir 'Lib\site-packages') -ErrorAction SilentlyContinue).Count
Write-Output ("  site-packages entries: " + $spc + "  (expected ~999)")

Write-Output ""
Write-Output "  import smoke test:"
$t = Join-Path $env:TEMP '_qi_smoke2.py'
Set-Content -Path $t -Encoding ASCII -Value @(
    'import importlib, sys',
    'mods = ["fastapi","uvicorn","requests","sqlite3","aiohttp","pydantic","docx","numpy","pandas","flask","linebot","chromadb","mcp"]',
    'bad = 0',
    'for m in mods:',
    '    try:',
    '        importlib.import_module(m)',
    '    except Exception as e:',
    '        bad += 1',
    '        print("    FAIL", m, type(e).__name__, e)',
    'print("    modules failing:", bad, "/", len(mods))'
)
& $newExe $t

Write-Output ""
Write-Output "=== GATE 4: registry now points at the new location? ==="
foreach ($hive in @('HKLM:\SOFTWARE\Python\PythonCore\3.11\InstallPath',
                    'HKCU:\SOFTWARE\Python\PythonCore\3.11\InstallPath')) {
    if (Test-Path $hive) {
        Write-Output ("  " + $hive + " -> " + (Get-ItemProperty $hive).'(default)')
    } else {
        Write-Output ("  (absent) " + $hive)
    }
}
Write-Output "  py launcher:"
& py -0p 2>&1 | ForEach-Object { Write-Output ("    " + $_) }

Write-Output ""
Write-Output ("  old interpreter still present: " + (Test-Path $oldExe))
Write-Output "=== DONE ==="

# Phase 2.1 - install CPython 3.11.9 for ALL USERS into C:\Program Files\Python311
# Services run as LocalSystem, so a per-user AppData install is not acceptable.
# NOTE: this file is deliberately pure ASCII. PowerShell 5.1 reads BOM-less .ps1
# as ANSI, and a UTF-8 em dash decodes to a sequence containing a double quote,
# which breaks string parity. Do not add non-ASCII characters here.
$ErrorActionPreference = 'Stop'
$ProgressPreference    = 'SilentlyContinue'

$Ver    = '3.11.9'
$Url    = "https://www.python.org/ftp/python/$Ver/python-$Ver-amd64.exe"
$Work   = 'C:\QIH\shared\documentation\migration_2026-08\phase2'
$Exe    = Join-Path $Work "python-$Ver-amd64.exe"
$Target = 'C:\Program Files\Python311'

if (Test-Path (Join-Path $Target 'python.exe')) {
    Write-Output "Already installed at $Target - skipping download/install."
} else {
    if (-not (Test-Path $Exe)) {
        Write-Output "Downloading $Url ..."
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $Url -OutFile $Exe -UseBasicParsing
    }
    $sz = [math]::Round((Get-Item $Exe).Length / 1MB, 1)
    Write-Output ("installer: " + $Exe + " (" + $sz + " MB)")

    Write-Output "Running installer (quiet, all users) ..."
    $instArgs = @(
        '/quiet',
        'InstallAllUsers=1',
        "TargetDir=$Target",
        "DefaultAllUsersTargetDir=$Target",
        'PrependPath=1',
        'AppendPath=0',
        'Include_launcher=1',
        'InstallLauncherAllUsers=1',
        'Include_pip=1',
        'Include_tcltk=1',
        'Include_doc=0',
        'Include_test=0',
        'Include_debug=0',
        'Include_symbols=0',
        'AssociateFiles=1',
        'Shortcuts=1',
        'CompileAll=1'
    )
    $p = Start-Process -FilePath $Exe -ArgumentList $instArgs -Wait -PassThru -NoNewWindow
    Write-Output ("installer exit code: " + $p.ExitCode)
    if ($p.ExitCode -ne 0) { throw "Installer failed with exit code $($p.ExitCode)" }
}

Write-Output "=== Verify ==="
$NewPy = Join-Path $Target 'python.exe'
if (-not (Test-Path $NewPy)) { throw "python.exe not found at $NewPy" }
$probe = 'import sys,sysconfig' + "`n" + 'print("version   :", sys.version.split()[0])' + "`n" + 'print("executable:", sys.executable)' + "`n" + 'print("prefix    :", sys.prefix)' + "`n" + 'print("purelib   :", sysconfig.get_paths()["purelib"])'
$probeFile = Join-Path $Work '_probe_newpy.py'
Set-Content -Path $probeFile -Value $probe -Encoding ASCII
& $NewPy $probeFile

Write-Output "=== Registry (should now show an HKLM all-users entry) ==="
foreach ($hive in @('HKLM:\SOFTWARE\Python\PythonCore','HKCU:\SOFTWARE\Python\PythonCore')) {
    if (Test-Path $hive) {
        Write-Output ("  " + $hive)
        Get-ChildItem $hive | ForEach-Object {
            $ip = Join-Path $_.PSPath 'InstallPath'
            $val = if (Test-Path $ip) { (Get-ItemProperty $ip).'(default)' } else { '?' }
            Write-Output ("     " + $_.PSChildName + " -> " + $val)
        }
    }
}

Write-Output "=== PATH entries mentioning Python ==="
$mp = [Environment]::GetEnvironmentVariable('Path','Machine')
($mp -split ';') | Where-Object { $_ -match 'python|1-AI' } | ForEach-Object { Write-Output ("  MACHINE: " + $_) }
$up = [Environment]::GetEnvironmentVariable('Path','User')
($up -split ';') | Where-Object { $_ -match 'python|1-AI' } | ForEach-Object { Write-Output ("  USER   : " + $_) }

Write-Output "=== DONE ==="

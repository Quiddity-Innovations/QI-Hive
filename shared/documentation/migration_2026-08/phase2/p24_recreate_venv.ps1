# Phase 2.4 - recreate a venv on the migrated interpreter.
#
# Recreated, not patched: editing pyvenv.cfg leaves the Scripts\*.exe launchers
# still pointing at the old base interpreter, so the venv only half-moves.
#
# The old venv is renamed aside, never deleted, so rollback is a rename back.
#
# Params:
#   -VenvPath   the venv directory
#   -Freeze     requirements file captured from the OLD venv
#   -Service    optional NSSM service to stop first and start after
#   -HealthUrl  optional URL to probe once the service is back
#   -TorchCpu   pass when the freeze pins a +cpu torch build, so pip is told to
#               use the CPU wheel index instead of pulling the CUDA wheel
#
# Pure ASCII only.
param(
    [Parameter(Mandatory=$true)][string]$VenvPath,
    [Parameter(Mandatory=$true)][string]$Freeze,
    [string]$Service = '',
    [string]$HealthUrl = '',
    [switch]$TorchCpu
)
$ErrorActionPreference = 'Continue'

$basePy = 'C:\Program Files\Python311\python.exe'
$old    = $VenvPath + '.old'

Write-Output ("venv    : " + $VenvPath)
Write-Output ("freeze  : " + $Freeze + "  (" + (Get-Content $Freeze).Count + " packages)")
Write-Output ("service : " + $(if ($Service) { $Service } else { '(none)' }))
Write-Output ""

if (-not (Test-Path $Freeze)) { Write-Output "FATAL: freeze file missing"; exit 1 }
if (Test-Path $old) { Write-Output ("FATAL: " + $old + " already exists - resolve it first"); exit 1 }

if ($Service) {
    Write-Output ("=== stopping " + $Service + " ===")
    Stop-Service -Name $Service -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    Write-Output ("  state: " + (Get-Service -Name $Service -ErrorAction SilentlyContinue).Status)
}

Write-Output ""
Write-Output "=== moving old venv aside ==="
Rename-Item -Path $VenvPath -NewName (Split-Path $old -Leaf) -ErrorAction Stop
Write-Output ("  " + $VenvPath + "  ->  " + $old)

Write-Output ""
Write-Output "=== creating fresh venv on the migrated interpreter ==="
& $basePy -m venv $VenvPath
$newPy = Join-Path $VenvPath 'Scripts\python.exe'
if (-not (Test-Path $newPy)) {
    Write-Output "FATAL: venv creation failed - rolling back"
    Remove-Item $VenvPath -Recurse -Force -ErrorAction SilentlyContinue
    Rename-Item -Path $old -NewName (Split-Path $VenvPath -Leaf)
    if ($Service) { Start-Service -Name $Service -ErrorAction SilentlyContinue }
    exit 1
}
Write-Output ("  " + (& $newPy -V 2>&1))
Write-Output ("  base: " + (& $newPy -c "import sys;print(sys.base_prefix)" 2>&1))

Write-Output ""
Write-Output "=== installing packages ==="
& $newPy -m pip install --upgrade pip --quiet 2>&1 | Select-Object -Last 3

if ($TorchCpu) {
    Write-Output "  (torch pinned to a +cpu build - installing torch from the CPU wheel index first)"
    $torchLines = Get-Content $Freeze | Where-Object { $_ -match '^(torch|torchaudio|torchvision)==' }
    if ($torchLines) {
        & $newPy -m pip install --index-url https://download.pytorch.org/whl/cpu $torchLines 2>&1 |
            Select-Object -Last 5
    }
}

& $newPy -m pip install -r $Freeze 2>&1 | Select-Object -Last 12

Write-Output ""
Write-Output "=== verify ==="
$want = (Get-Content $Freeze | Where-Object { $_ -match '==' }).Count
$got  = (& $newPy -m pip freeze 2>&1 | Where-Object { $_ -match '==' }).Count
Write-Output ("  packages wanted: " + $want)
Write-Output ("  packages present: " + $got)
$stale = & $newPy -c "import sys;print('1-AI' in sys.prefix or '1-AI' in sys.base_prefix)" 2>&1
Write-Output ("  references old tree: " + $stale)

if ($Service) {
    Write-Output ""
    Write-Output ("=== starting " + $Service + " ===")
    Start-Service -Name $Service -ErrorAction SilentlyContinue
    $deadline = (Get-Date).AddSeconds(45)
    do {
        Start-Sleep -Seconds 3
        $st = (Get-Service -Name $Service -ErrorAction SilentlyContinue).Status
    } while ($st -ne 'Running' -and (Get-Date) -lt $deadline)
    Write-Output ("  state: " + $st)
}

if ($HealthUrl) {
    Write-Output ""
    Write-Output ("=== probing " + $HealthUrl + " ===")
    Start-Sleep -Seconds 5
    for ($i = 1; $i -le 5; $i++) {
        try {
            $r = Invoke-WebRequest -Uri $HealthUrl -TimeoutSec 10 -UseBasicParsing
            Write-Output ("  attempt " + $i + ": HTTP " + $r.StatusCode)
            break
        } catch {
            Write-Output ("  attempt " + $i + ": " + $_.Exception.Message)
            Start-Sleep -Seconds 5
        }
    }
}

Write-Output ""
Write-Output ("Old venv retained at: " + $old)
Write-Output "Delete it only after the service has run clean for a full day."
Write-Output "=== DONE ==="

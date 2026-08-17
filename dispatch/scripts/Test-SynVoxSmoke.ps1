# ============================================================
#  Test-SynVoxSmoke.ps1  -  SynVox Phase 0 acceptance gate (FREE)
#  Project : SynVox (Quiddity Innovations) - C:\APPS\SynVox
#  Run     : powershell -NoProfile -ExecutionPolicy Bypass -File .\Test-SynVoxSmoke.ps1
#            or remotely:  qi_execute_script("synvox-smoke")
#
#  Runs 'matraix smoke' over every Survey task in the engine. This is the
#  host-lane onboarding smoke added upstream in #82: it loads the
#  questionnaire, renders a persona, runs the REAL survey runner against a
#  deterministic fake client and checks the answer envelope.
#
#  COSTS NOTHING AND CANNOT COST ANYTHING:
#    - no provider calls (fake client), so no ANTHROPIC_API_KEY needed
#    - no Docker required (host lane)
#  Answers are synthetic, NOT persona-faithful - this proves the harness
#  works, it is not a simulation result. Never quote its output as a finding.
#
#  Docker is still required for the Harbor stack smoke and for web/os-app
#  (computer-use) tasks:
#    matraix run -c configs/jobs/example-job-recipe/harbor-smoke-local.yaml
# ============================================================

$ErrorActionPreference = "Continue"
$ProgressPreference    = "SilentlyContinue"

$ProjectDir = "C:\APPS\SynVox"
$BaseDir    = Join-Path $ProjectDir "engine\matraix"
$LogDir     = Join-Path $ProjectDir "logs"
$MasterLog  = Join-Path $LogDir ("synvox_smoke_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
$Personas   = 3          # keep small: every persona is one fake call, still $0

# Same shared-uv pinning as Setup-SynVox.ps1 - the executor runs as SYSTEM and
# must resolve the same interpreter renne uses. See CLAUDE.md.
$env:UV_PYTHON_INSTALL_DIR = "C:\QIH\shared\uv\python"
$env:UV_CACHE_DIR          = "C:\QIH\shared\uv\cache"
$env:UV_TOOL_DIR           = "C:\QIH\shared\uv\tools"

# PEP 540 UTF-8 mode - see the note in Setup-SynVox.ps1. Task files are read
# without an explicit encoding upstream, so on a cp1252 host a curly quote in
# a questionnaire kills the trial before any persona runs.
$env:PYTHONUTF8 = "1"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-Log {
    param([string]$Level, [string]$Msg)
    $line = "{0} [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Level.PadRight(4), $Msg
    Write-Host $line
    Add-Content -Path $MasterLog -Value $line -Encoding UTF8
}

# Make the usual per-user tool locations visible to whichever principal runs this.
foreach ($d in @("$env:USERPROFILE\.local\bin", "$env:LOCALAPPDATA\hermes\bin")) {
    if ((Test-Path $d) -and ($env:Path -notlike "*$d*")) { $env:Path = "$d;$env:Path" }
}

Write-Log "INFO" "===================================================="
Write-Log "INFO" "  SynVox FREE smoke gate (host lane, no Docker, no API key)"
Write-Log "INFO" "  Machine: $env:COMPUTERNAME   User: $env:USERNAME"
Write-Log "INFO" "  Master log: $MasterLog"
Write-Log "INFO" "===================================================="

if (-not (Test-Path $BaseDir)) {
    Write-Log "FAIL" "Engine not found at $BaseDir - run setup-synvox first."
    exit 1
}
Set-Location $BaseDir

# Discover every Survey task rather than hardcoding a list, so tasks added
# upstream are picked up automatically on the next run.
$tasks = Get-ChildItem "application\tasks" -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like "*survey*" } |
    Select-Object -ExpandProperty Name |
    Sort-Object

if (-not $tasks) {
    Write-Log "FAIL" "No survey tasks found under application\tasks."
    exit 1
}
Write-Log "INFO" ("Survey tasks discovered: {0}" -f ($tasks -join ", "))

$pass = 0
$fail = @()
foreach ($t in $tasks) {
    Write-Log "INFO" "SMOKE START : $t (personas=$Personas)"
    $global:LASTEXITCODE = 0
    $out = & uv run matraix smoke "application/tasks/$t" --personas $Personas 2>&1
    $code = $LASTEXITCODE
    foreach ($line in $out) {
        if ("$line".Trim().Length) { Write-Log "INFO" ("    " + "$line") }
    }
    # Trust the assertion, not just the exit code: require the explicit ok line.
    $okLine = $out | Where-Object { "$_" -match "Smoke:\s*ok" }
    if ($code -eq 0 -and $okLine) {
        Write-Log "OK" "SMOKE PASS  : $t"
        $pass++
    } else {
        Write-Log "FAIL" "SMOKE FAIL  : $t (exit $code, 'Smoke: ok' not found)"
        $fail += $t
    }
}

Write-Log "INFO" "===================== SUMMARY ====================="
Write-Log "INFO" ("Survey smoke: {0} passed, {1} failed, of {2} task(s)" -f $pass, $fail.Count, $tasks.Count)
if ($fail.Count) { Write-Log "FAIL" ("Failed: {0}" -f ($fail -join ", ")) }
Write-Log "INFO" "Cost: `$0 - fake client, no provider calls, no Docker."
Write-Log "INFO" "Answers are synthetic and NOT persona-faithful. This proves the harness, not the market."
Write-Log "INFO" "Docker is still needed for the Harbor stack smoke and web/os-app tasks."
Write-Log "INFO" "Master log: $MasterLog"
Write-Log "INFO" "===================================================="

if ($fail.Count) { exit 1 } else { exit 0 }

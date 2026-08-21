# ============================================================
#  Setup-SynVox.ps1  -  SynVox Phase 0 bootstrap (MatrAIx engine)
#  Project : SynVox (Quiddity Innovations) - C:\APPS\SynVox
#  Machine : PowerSpec (personal/QI hardware ONLY - never BU)
#  Run     : powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup-SynVox.ps1
#            or remotely:  qi_execute_script("setup-synvox")
#
#  Fully automated, no confirmations. Every success AND failure goes to one
#  master log in C:\APPS\SynVox\logs. Re-runnable (idempotent).
#  Ends at the FREE Docker smoke test - never runs a paid persona simulation.
# ============================================================

$ErrorActionPreference = "Continue"
$ProgressPreference    = "SilentlyContinue"   # keep winget/hf progress bars out of the log

# ---------- Configuration (QI conventions) ----------
$ProjectDir = "C:\APPS\SynVox"
$BaseDir    = Join-Path $ProjectDir "engine\matraix"
$LogDir     = Join-Path $ProjectDir "logs"
$RepoUrl    = "https://github.com/MatrAIx-ai/MatrAIx-Persona-8B"
$HfDataset  = "MatrAIx2026/MatrAIx_Persona_1M_Public_Release"
$PersonaDir = Join-Path $BaseDir "persona\datasets\matraix-persona-1m\release"
$MasterLog  = Join-Path $LogDir ("synvox_phase0_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
$SmokeCfg   = "configs/jobs/example-job-recipe/harbor-smoke-local.yaml"

# This script runs BOTH interactively (as renne) and remotely through the QI
# Connector executor, which runs as NT AUTHORITY\SYSTEM. Left to their defaults
# the two principals build separate uv toolchains in separate profiles, and the
# venv one creates is unusable - and undeletable - by the other. Pin uv's state
# to one machine-wide location so either principal resolves the same
# interpreter, and hand the results back to the Users group at the end.
$env:UV_PYTHON_INSTALL_DIR = "C:\QIH\shared\uv\python"
$env:UV_CACHE_DIR          = "C:\QIH\shared\uv\cache"
$env:UV_TOOL_DIR           = "C:\QIH\shared\uv\tools"
New-Item -ItemType Directory -Force -Path $env:UV_PYTHON_INSTALL_DIR, $env:UV_CACHE_DIR, $env:UV_TOOL_DIR | Out-Null

# PEP 540 UTF-8 mode. harbor/models/task/task.py calls .read_text() with no
# encoding, so Python falls back to the OS ANSI codepage (cp1252 here) and any
# task file containing a curly quote kills the trial with UnicodeDecodeError
# before a single persona runs. That hits real Phase 1 survey tasks, not just
# examples. Upstream patch 0002 is ready in C:\APPS\SynVox\upstream\; this is
# the belt-and-braces version that works today and stays harmless afterwards.
$env:PYTHONUTF8 = "1"
$IsSystemAccount = ([Security.Principal.WindowsIdentity]::GetCurrent().User.Value -eq "S-1-5-18")

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-Log {
    param([string]$Level, [string]$Msg)
    $line = "{0} [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Level.PadRight(4), $Msg
    Write-Host $line
    Add-Content -Path $MasterLog -Value $line -Encoding UTF8
}

function Write-Stream {
    # Pipe external-command output into the master log, line by line.
    param([string]$Prefix = "    ")
    process { if ($_ -ne $null -and "$_".Trim().Length) { Write-Log "INFO" ($Prefix + "$_") } }
}

$script:Results = [ordered]@{}

function Invoke-Step {
    param([string]$Key, [string]$Name, [scriptblock]$Action)
    Write-Log "INFO" "STEP START : $Name"
    $global:LASTEXITCODE = 0
    try {
        & $Action
        if ($LASTEXITCODE -ne 0) {
            Write-Log "FAIL" "STEP FAILED (exit $LASTEXITCODE) : $Name"
            $script:Results[$Key] = "FAILED (exit $LASTEXITCODE)"
            return
        }
        Write-Log "OK" "STEP SUCCESS : $Name"
        $script:Results[$Key] = "SUCCESS"
    } catch {
        Write-Log "FAIL" "STEP EXCEPTION : $Name :: $($_.Exception.Message)"
        $script:Results[$Key] = "EXCEPTION"
    }
}

function Add-ToPath {
    param([string]$Dir)
    if ((Test-Path $Dir) -and ($env:Path -notlike "*$Dir*")) { $env:Path = "$Dir;$env:Path" }
}

function Grant-UsersModify {
    # Anything SYSTEM creates is owned by SYSTEM and cannot be changed - or even
    # deleted - by renne afterwards. Hand it back. S-1-5-32-545 = BUILTIN\Users,
    # locale-independent. No-op when running interactively.
    param([string]$Path)
    if (-not $IsSystemAccount -or -not (Test-Path $Path)) { return }
    icacls "$Path" /grant "*S-1-5-32-545:(OI)(CI)M" /T /C /Q 2>&1 | Out-Null
    Write-Log "INFO" "Granted BUILTIN\Users modify rights on $Path (created as SYSTEM)"
    $global:LASTEXITCODE = 0
}

Write-Log "INFO" "===================================================="
Write-Log "INFO" "  SynVox Phase 0 bootstrap - MatrAIx engine"
Write-Log "INFO" "  Machine: $env:COMPUTERNAME   User: $env:USERNAME"
Write-Log "INFO" "  Project: $ProjectDir"
Write-Log "INFO" "  Master log: $MasterLog"
Write-Log "INFO" "===================================================="

# Make sure the usual per-user tool locations are visible to this session.
Add-ToPath "$env:USERPROFILE\.local\bin"
Add-ToPath "$env:LOCALAPPDATA\hermes\bin"
Add-ToPath "$env:LOCALAPPDATA\Microsoft\WindowsApps"

# ---------- 1. Prerequisites ----------
Invoke-Step "git" "Ensure Git" {
    if (Get-Command git -ErrorAction SilentlyContinue) {
        git --version | Write-Stream
    } else {
        Write-Log "WARN" "Git not found - installing via winget"
        winget install --id Git.Git -e --accept-source-agreements --accept-package-agreements --silent 2>&1 | Write-Stream
        Add-ToPath "C:\Program Files\Git\cmd"
        $global:LASTEXITCODE = 0
    }
}

Invoke-Step "uv" "Ensure uv" {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        uv --version | Write-Stream
    } else {
        Write-Log "WARN" "uv not found - installing from astral.sh"
        powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex" 2>&1 | Write-Stream
        Add-ToPath "$env:USERPROFILE\.local\bin"
        $global:LASTEXITCODE = 0
    }
}

Invoke-Step "python312" "Ensure Python 3.12" {
    $found = $false
    try { $v = & py -3.12 --version 2>$null; if ($v) { Write-Log "INFO" "Found $v (py launcher)"; $found = $true } } catch {}
    if (-not $found -and (Get-Command uv -ErrorAction SilentlyContinue)) {
        # uv manages its own interpreters - cheaper and quieter than a winget install
        uv python install 3.12 2>&1 | Write-Stream
        uv python find 3.12 2>&1 | Write-Stream
        $found = ($LASTEXITCODE -eq 0)
    }
    if (-not $found) {
        Write-Log "WARN" "Falling back to winget for Python 3.12"
        winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements --silent 2>&1 | Write-Stream
    }
    $global:LASTEXITCODE = 0
}

Invoke-Step "node" "Ensure Node.js 20+" {
    $ok = $false
    if (Get-Command node -ErrorAction SilentlyContinue) {
        $v = (node --version) -replace "v", ""
        if ([int]($v.Split(".")[0]) -ge 20) { Write-Log "INFO" "Found Node $v"; $ok = $true }
        else { Write-Log "WARN" "Node $v is older than 20" }
    }
    if (-not $ok) {
        winget install --id OpenJS.NodeJS.LTS -e --accept-source-agreements --accept-package-agreements --silent 2>&1 | Write-Stream
        $global:LASTEXITCODE = 0
    }
}

# Docker: CHECK ONLY. Installing Docker Desktop needs WSL2 + a reboot - never silent-install it.
$script:DockerReady = $false
Invoke-Step "docker" "Check Docker (check only - never installed by this script)" {
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        docker --version 2>&1 | Write-Stream
        docker info *> $null
        if ($LASTEXITCODE -eq 0) { $script:DockerReady = $true; Write-Log "INFO" "Docker daemon is running" }
        else { Write-Log "WARN" "Docker installed but the daemon is not running - start Docker Desktop. Smoke test will be SKIPPED." }
        $global:LASTEXITCODE = 0
    } else {
        Write-Log "WARN" "Docker Desktop NOT installed (needs WSL2). Install from docker.com. Smoke test will be SKIPPED."
    }
}

# ---------- 2. Clone / update the MatrAIx engine ----------
Invoke-Step "clone" "Clone or update MatrAIx repo" {
    if (Test-Path (Join-Path $BaseDir ".git")) {
        Write-Log "INFO" "Repo already present - pulling"
        # -c safe.directory (inline, not --global): the repo is cloned by renne but
        # pulled by SYSTEM on remote runs, which git otherwise refuses as
        # "dubious ownership". Scoped to this one invocation and this one path.
        $safe = $BaseDir.Replace("\", "/")
        git -c "safe.directory=$safe" -C $BaseDir pull --ff-only 2>&1 | Write-Stream
    } else {
        New-Item -ItemType Directory -Force -Path (Split-Path $BaseDir) | Out-Null
        git clone $RepoUrl $BaseDir 2>&1 | Write-Stream
    }
}

if (-not (Test-Path $BaseDir)) {
    Write-Log "FAIL" "Engine directory $BaseDir does not exist - cannot continue with the Python environment."
} else {
    Set-Location $BaseDir

    # ---------- 3. Python environment ----------
    Invoke-Step "venv" "Create or repair uv venv (Python 3.12)" {
        $venvPy = Join-Path $BaseDir ".venv\Scripts\python.exe"
        $healthy = $false
        if (Test-Path $venvPy) {
            & $venvPy -c "import sys; print(sys.version)" 2>&1 | Write-Stream
            if ($LASTEXITCODE -eq 0) {
                $healthy = $true
                Write-Log "INFO" "Existing .venv is healthy - reusing it"
            } else {
                Write-Log "WARN" "Existing .venv cannot run (broken interpreter link) - recreating with --clear"
                $global:LASTEXITCODE = 0
            }
        }
        if (-not $healthy) { uv venv --python 3.12 --clear 2>&1 | Write-Stream }
        Grant-UsersModify (Join-Path $BaseDir ".venv")
    }

    # MatrAIx is a uv PROJECT (pyproject.toml + uv.lock), so `uv sync` is the
    # authoritative install and every later `uv run` re-syncs .venv against the
    # lock. Anything added with `uv pip install` that the lock does not declare
    # is PRUNED by the next `uv run` - which is why this script used to report
    # SUCCESS for pytest and playground while neither survived. Undeclared
    # extras are therefore installed on a best-effort basis and the verify_env
    # step below tells the truth about what actually stuck.
    Invoke-Step "deps_core" "Sync MatrAIx project environment from uv.lock" {
        uv sync 2>&1 | Write-Stream
    }

    Invoke-Step "deps_extras" "Install undeclared extras (best effort - see verify_env)" {
        foreach ($pkg in @("packages/playground", "packages/harbor-langsmith", "packages/rewardkit")) {
            if (Test-Path $pkg) {
                uv pip install -e $pkg 2>&1 | Write-Stream
            } else {
                Write-Log "WARN" "package path not present in this repo revision: $pkg"
            }
        }
        uv pip install pytest pytest-asyncio httpx "huggingface_hub[cli]" 2>&1 | Write-Stream
        $global:LASTEXITCODE = 0
    }

    # Trust nothing: import every module the project actually needs and report
    # what is really there. Exit codes lie; imports do not.
    Invoke-Step "verify_env" "Verify the environment by importing what we depend on" {
        $required = @("harbor", "matraix", "httpx", "huggingface_hub", "pyarrow")
        $optional = @("playground", "pytest")
        $missing = @()
        foreach ($m in ($required + $optional)) {
            uv run --no-sync python -c "import $m" 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Log "INFO" ("  import {0,-18} OK" -f $m)
            } else {
                $tag = if ($required -contains $m) { "REQUIRED" } else { "optional" }
                Write-Log "WARN" ("  import {0,-18} MISSING ({1})" -f $m, $tag)
                if ($required -contains $m) { $missing += $m }
            }
            $global:LASTEXITCODE = 0
        }
        Write-Log "INFO" "Undeclared extras (pytest, playground) do not survive a plain 'uv run' - it re-syncs to uv.lock."
        Write-Log "INFO" "Run the engine test suite with an ephemeral overlay instead:"
        Write-Log "INFO" "  uv run --with pytest --with pytest-asyncio --with httpx python -m pytest -q"
        if ($missing.Count -gt 0) {
            Write-Log "FAIL" ("REQUIRED modules missing: {0}" -f ($missing -join ", "))
            $global:LASTEXITCODE = 1
        }
    }

    # ---------- 4. Persona 1M dataset (free, large, resumable) ----------
    Invoke-Step "persona1m" "Download Persona 1M dataset" {
        New-Item -ItemType Directory -Force -Path $PersonaDir | Out-Null
        $env:HF_HUB_DISABLE_PROGRESS_BARS = "1"
        # 'hf download' is the current CLI; huggingface-cli remains as a shim.
        uv run hf download $HfDataset --repo-type dataset --local-dir $PersonaDir 2>&1 |
            Select-Object -Last 25 | Write-Stream
        if ($LASTEXITCODE -ne 0) {
            Write-Log "WARN" "'hf download' failed - retrying with legacy huggingface-cli"
            $global:LASTEXITCODE = 0
            uv run huggingface-cli download $HfDataset --repo-type dataset --local-dir $PersonaDir 2>&1 |
                Select-Object -Last 25 | Write-Stream
        }
        if (Test-Path $PersonaDir) {
            $files = Get-ChildItem -Recurse -File $PersonaDir -ErrorAction SilentlyContinue
            $mb = [math]::Round((($files | Measure-Object Length -Sum).Sum / 1MB), 1)
            Write-Log "INFO" ("Persona dataset: {0} files, {1} MB at {2}" -f $files.Count, $mb, $PersonaDir)
        }
        Grant-UsersModify $PersonaDir
    }

    # ---------- 4b. Integrity check against the release manifest ----------
    Invoke-Step "verify" "Verify Persona 1M shards against manifest.json" {
        $mf = Join-Path $PersonaDir "manifest.json"
        if (-not (Test-Path $mf)) {
            Write-Log "FAIL" "manifest.json missing - the dataset download did not complete."
            $global:LASTEXITCODE = 1
            return
        }
        $m = Get-Content $mf -Raw -Encoding UTF8 | ConvertFrom-Json
        $bad = 0
        foreach ($f in $m.files) {
            $p = Join-Path $PersonaDir $f.path
            if (-not (Test-Path $p)) { Write-Log "FAIL" "MISSING shard $($f.path)"; $bad++; continue }
            $len = (Get-Item $p).Length
            if ($len -ne $f.bytes) {
                Write-Log "FAIL" ("SIZE MISMATCH {0}: {1} bytes on disk, {2} expected" -f $f.path, $len, $f.bytes)
                $bad++
            }
        }
        Write-Log "INFO" ("Shards: {0} of {1} present at the expected size ({2:N0} personas)" -f ($m.files.Count - $bad), $m.files.Count, $m.rows)
        if ($bad -gt 0) { $global:LASTEXITCODE = 1 }
    }

    # ---------- 5. Free smoke test (no API key, Docker required) ----------
    if ($script:DockerReady) {
        if (Test-Path $SmokeCfg) {
            Invoke-Step "smoke" "Harbor smoke test (free, no API key)" {
                uv run harbor run -c $SmokeCfg 2>&1 | Write-Stream
            }
        } else {
            Write-Log "WARN" "SKIPPED smoke test: config not found at $SmokeCfg"
            $script:Results["smoke"] = "SKIPPED (config missing)"
        }
    } else {
        Write-Log "WARN" "SKIPPED smoke test: Docker not available."
        $script:Results["smoke"] = "SKIPPED (no Docker)"
    }
}

# ---------- 6. metered key check - ABSENT is the correct state ----------
#
# Inverted 2026-08-18. This block used to WARN when ANTHROPIC_API_KEY was
# missing and tell you to `setx` one, then report a present key as success.
# That predates the subscription lane (owner decision, QI Brain #530) and is
# now backwards in a way that costs real money if followed: persona runs go
# through the SynVox Router on 127.0.0.1:8753, whose backend is headless
# `claude -p` on a Claude Max plan. There is no metered spend and there is no
# key to set. CLAUDE.md rule 5 says do not set one, and
# tools\run_survey_via_router.py strips ANTHROPIC_API_KEY from the child
# environment so a stray one cannot be reached anyway.
if (-not $env:ANTHROPIC_API_KEY) {
    Write-Log "OK" "ANTHROPIC_API_KEY is not set. That is CORRECT - SynVox runs on the Claude Max subscription lane and must never reach a metered key."
    $script:Results["api_key"] = "ABSENT (correct)"
} else {
    Write-Log "WARN" "ANTHROPIC_API_KEY IS SET on this machine (value never logged). SynVox will not use it - the Router lane strips it - but it should not be here: it means something on this host can spend metered credit. Remove it unless another project genuinely needs it."
    $script:Results["api_key"] = "PRESENT (unexpected - see log)"
}

# ---------- 6b. Hand the whole project tree back to the interactive user ----------
Grant-UsersModify $ProjectDir

# ---------- 7. Summary ----------
Write-Log "INFO" "===================== SUMMARY ====================="
foreach ($k in $script:Results.Keys) {
    Write-Log "INFO" ("{0,-16} : {1}" -f $k, $script:Results[$k])
}
Write-Log "INFO" "Engine     : $BaseDir"
Write-Log "INFO" "Personas   : $PersonaDir"
Write-Log "INFO" "Master log : $MasterLog"
Write-Log "INFO" "Phase 0 ends at the free smoke test - no paid persona simulation is run by this script."
Write-Log "INFO" "Next (Phase 1): task 'qi-survey_nexus-pricing-tiers' - needs ANTHROPIC_API_KEY and costs ~`$1-5."
Write-Log "INFO" "===================================================="

param(
    [ValidateSet("personal", "professional", "enterprise", "cloud")]
    [string]$Edition = "professional",
    [string]$ClaudeBin = "",
    [string]$ClaudeEnvFile = "",
    [string]$BindAddress = "",
    [switch]$InstallServices,
    [switch]$Force
)

# ============================================================
#  Install-SynVox.ps1  -  configure a SynVox install on top of the engine
#  Project : SynVox (Quiddity Innovations) - C:\APPS\SynVox
#  Machine : PowerSpec (personal/QI hardware ONLY - never BU)
#  Run     : powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-SynVox.ps1 `
#                -Edition professional -ClaudeBin "C:\path\to\claude.exe" `
#                -ClaudeEnvFile "C:\path\to\claude_max.env"
#            or remotely (NOT recommended for the subscription lane - see the
#            _note in manifest.json): qi_execute_script("install-synvox")
#
#  This script complements Setup-SynVox.ps1. Setup-SynVox gets the ENGINE
#  working (git clone, uv venv, Persona 1M, free smoke). This script configures
#  a SYNVOX INSTALL on top of a working engine: edition, the Claude Max
#  subscription lane, bind address, bearer secrets and (optionally) NSSM
#  services. It does not bootstrap the engine and refuses to run if the engine
#  is missing or unhealthy.
#
#  Fully automated, no confirmations. Every success AND failure goes to one
#  master log in C:\APPS\SynVox\logs. Re-runnable (idempotent). Never sets
#  ANTHROPIC_API_KEY and never prints a secret value to console or log.
# ============================================================

$ErrorActionPreference = "Continue"
$ProgressPreference    = "SilentlyContinue"

# ---------- Configuration (QI conventions) ----------
$ProjectDir   = "C:\APPS\SynVox"
$BaseDir      = Join-Path $ProjectDir "engine\matraix"
$VenvPy       = Join-Path $BaseDir ".venv\Scripts\python.exe"
$ConfigDir    = Join-Path $ProjectDir "config"
$SecretsDir   = Join-Path $ProjectDir "secrets"
$LogDir       = Join-Path $ProjectDir "logs"
$PersonaDir   = Join-Path $BaseDir "persona\datasets\matraix-persona-1m\release"
$MasterLog    = Join-Path $LogDir ("synvox_install_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
$Nssm         = "C:\QIH\engine\bin\nssm.exe"
$ServiceRegistryDoc = "C:\QIH\ecosystem\QI_Service_Registry.md"
$ApiPort      = 8751
$RouterPort   = 8753

New-Item -ItemType Directory -Force -Path $LogDir, $SecretsDir | Out-Null

function Write-Log {
    param([string]$Level, [string]$Msg)
    $line = "{0} [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Level.PadRight(4), $Msg
    Write-Host $line
    Add-Content -Path $MasterLog -Value $line -Encoding UTF8
}

$script:Results = [ordered]@{}

function Set-Result {
    param([string]$Key, [string]$Status)
    $script:Results[$Key] = $Status
}

function Grant-UsersModify {
    # Same rationale as Setup-SynVox.ps1: if the QI Connector executor (SYSTEM)
    # ever runs this, hand back anything it creates so renne can still manage
    # it afterwards. No-op when running interactively.
    param([string]$Path)
    $isSystem = ([Security.Principal.WindowsIdentity]::GetCurrent().User.Value -eq "S-1-5-18")
    if (-not $isSystem -or -not (Test-Path $Path)) { return }
    icacls "$Path" /grant "*S-1-5-32-545:(OI)(CI)M" /T /C /Q 2>&1 | Out-Null
    Write-Log "INFO" "Granted BUILTIN\Users modify rights on $Path (created as SYSTEM)"
    $global:LASTEXITCODE = 0
}

function Protect-SecretFile {
    # 0600-equivalent: the current user, local Administrators, and SYSTEM.
    # SYSTEM is included deliberately: QI_SynVoxAPI (if -InstallServices is
    # used) defaults to the LocalSystem account via NSSM, and it must be able
    # to read this file to validate bearer auth. Still excludes BUILTIN\Users
    # and Everyone, which is the actual point of "0600-equivalent" on Windows.
    param([string]$Path)
    icacls "$Path" /inheritance:r /grant:r "$($env:USERDOMAIN)\$($env:USERNAME):F" "*S-1-5-32-544:F" "*S-1-5-18:F" 2>&1 | Out-Null
    $global:LASTEXITCODE = 0
}

function New-SecureToken {
    param([int]$Bytes = 32)
    $buffer = New-Object byte[] $Bytes
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($buffer)
    $b64 = [Convert]::ToBase64String($buffer)
    return ($b64 -replace '\+', '-' -replace '/', '_' -replace '=', '')
}

Write-Log "INFO" "===================================================="
Write-Log "INFO" "  SynVox install configuration"
Write-Log "INFO" "  Machine: $env:COMPUTERNAME   User: $env:USERNAME"
Write-Log "INFO" "  Project: $ProjectDir"
Write-Log "INFO" "  Edition requested: $Edition"
Write-Log "INFO" "  Master log: $MasterLog"
Write-Log "INFO" "===================================================="

# ============================================================
# 1. Prerequisites - verify, never assume, never re-bootstrap
# ============================================================
Write-Log "INFO" "---- Step 1: prerequisites ----"

if (-not (Test-Path $BaseDir) -or -not (Test-Path $VenvPy)) {
    Write-Log "FAIL" "Engine not found (or venv missing) at $BaseDir."
    Write-Log "FAIL" "This installer configures a SynVox INSTALL on top of a working engine - it does not bootstrap the engine itself."
    Write-Log "FAIL" "Run first:  powershell -NoProfile -ExecutionPolicy Bypass -File C:\QIH\dispatch\scripts\Setup-SynVox.ps1"
    Write-Log "FAIL" "  or remotely:  qi_execute_script(""setup-synvox"")"
    Write-Log "FAIL" "Then re-run this installer."
    exit 1
}

& $VenvPy -c "import sys; print(sys.version)" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Log "FAIL" "Engine venv at $VenvPy cannot run. Run Setup-SynVox.ps1 to repair it (it recreates the venv with --clear when broken)."
    exit 1
}
$global:LASTEXITCODE = 0
Write-Log "OK" "Engine present and venv healthy at $BaseDir"
Set-Result "engine" "PASS"

# Persona 1M integrity - informational gate, not a hard stop: the provider
# lane and secrets below do not require personas on disk.
$manifestPath = Join-Path $PersonaDir "manifest.json"
if (-not (Test-Path $manifestPath)) {
    Write-Log "FAIL" "Persona 1M manifest.json missing at $PersonaDir - re-run setup-synvox to (re)download it."
    Set-Result "persona_manifest" "FAIL (missing - re-run setup-synvox)"
} else {
    $m = Get-Content $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $bad = 0
    foreach ($f in $m.files) {
        $p = Join-Path $PersonaDir $f.path
        if (-not (Test-Path $p)) { $bad++; continue }
        if ((Get-Item $p).Length -ne $f.bytes) { $bad++ }
    }
    if ($bad -eq 0) {
        Write-Log "OK" ("Persona 1M shards verified: {0} of {1} files ({2:N0} personas)" -f ($m.files.Count - $bad), $m.files.Count, $m.rows)
        Set-Result "persona_manifest" "PASS"
    } else {
        Write-Log "FAIL" ("Persona 1M shard mismatch: {0} of {1} files bad or missing - re-run setup-synvox" -f $bad, $m.files.Count)
        Set-Result "persona_manifest" "FAIL ($bad bad shard(s))"
    }
}

# PEP 540 UTF-8 mode: self-healing here, and persisted (User scope) so it
# survives into any interactive run of tools\run_router.py / synvox_server.py
# started later in this same user session, not only inside this process.
$env:PYTHONUTF8 = "1"
$persistedUtf8 = [Environment]::GetEnvironmentVariable("PYTHONUTF8", "User")
if ($persistedUtf8 -ne "1") {
    [Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")
    Write-Log "INFO" "Persisted PYTHONUTF8=1 for user $env:USERNAME (setx-equivalent; new shells need to reopen to see it)"
}
Write-Log "OK" "PYTHONUTF8=1 set for this session and persisted for the user"
Set-Result "pythonutf8" "PASS"

# ============================================================
# 2. Edition + bind address
# ============================================================
Write-Log "INFO" "---- Step 2: edition and bind address ----"

$ResolvedBind = "127.0.0.1"
if ($Edition -eq "personal") {
    if ($BindAddress -and $BindAddress -ne "127.0.0.1") {
        Write-Log "WARN" "-BindAddress '$BindAddress' ignored: personal edition is loopback-only by design. Forcing 127.0.0.1."
    }
    $ResolvedBind = "127.0.0.1"
} else {
    if ($BindAddress -eq "0.0.0.0") {
        Write-Log "FAIL" "Refusing to bind 0.0.0.0. Pass the specific LAN IP you want with -BindAddress, e.g. 192.168.1.50."
        exit 1
    }
    if ($BindAddress) {
        $ResolvedBind = $BindAddress
    } else {
        $ResolvedBind = "127.0.0.1"
        Write-Log "INFO" "No -BindAddress given for edition '$Edition' - defaulting to 127.0.0.1 (loopback). Pass -BindAddress <LAN IP> to serve the LAN."
    }
}

if ($ResolvedBind -notin @("127.0.0.1", "localhost", "::1")) {
    Write-Log "WARN" "=========================================================================="
    Write-Log "WARN" "  BINDING TO A LAN ADDRESS: $ResolvedBind"
    Write-Log "WARN" "  Bearer auth is now the ONLY thing between the LAN and this install."
    Write-Log "WARN" "  This script does NOT open a firewall rule for you. If you need one, run"
    Write-Log "WARN" "  this yourself, scoped to your LAN, once you have confirmed the bind:"
    Write-Log "WARN" "    New-NetFirewallRule -DisplayName ""QI_SynVoxAPI"" -Direction Inbound ``"
    Write-Log "WARN" "      -Protocol TCP -LocalPort $ApiPort -Action Allow -RemoteAddress <your LAN CIDR>"
    Write-Log "WARN" "  The AI Router (:$RouterPort) always binds 127.0.0.1 only - enforced in"
    Write-Log "WARN" "  synvox\ai\router.py itself, not affected by -BindAddress."
    Write-Log "WARN" "=========================================================================="
}
Write-Log "OK" "Edition=$Edition  api_bind=$ResolvedBind  router_bind=127.0.0.1 (always)"
Set-Result "edition_bind" "PASS (edition=$Edition, api_bind=$ResolvedBind)"

# Write BOTH a config value and a persisted env var - belt and braces per the
# task brief. UPDATE: config\synvox.template.json appeared under the project
# mid-session (the API-building agent's work), and it settles the question:
# the confirmed schema is config\synvox.json with keys "edition" / "bind" /
# "port", and "every value here can also be set as an environment variable
# with the SYNVOX_ prefix (SYNVOX_EDITION, SYNVOX_BIND, SYNVOX_PORT, ...) -
# environment wins over file" (its own _doc). We target that contract
# directly rather than a guessed shape, and still keep the env var as a
# second, agreeing source of truth in case the loader differs from the
# template's own stated convention.
$synvoxConfigPath = Join-Path $ConfigDir "synvox.json"
$synvoxTemplatePath = Join-Path $ConfigDir "synvox.template.json"
if (Test-Path $synvoxConfigPath) {
    Copy-Item $synvoxConfigPath "$synvoxConfigPath.bak" -Force
    Write-Log "INFO" "Backed up existing config\synvox.json -> synvox.json.bak"
    $synvoxConfig = Get-Content $synvoxConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
} elseif (Test-Path $synvoxTemplatePath) {
    $synvoxConfig = Get-Content $synvoxTemplatePath -Raw -Encoding UTF8 | ConvertFrom-Json
    Write-Log "INFO" "config\synvox.json did not exist - seeded from synvox.template.json"
} else {
    Write-Log "WARN" "Neither config\synvox.json nor config\synvox.template.json found - writing a minimal file. Confirm the schema against synvox_server.py once it exists."
    $synvoxConfig = [ordered]@{
        "_doc" = "Generated by Install-SynVox.ps1 - no synvox.template.json was present to seed from."
        "schema_version" = "SynVoxSettings.v1"
        "edition_options" = @("personal", "professional", "enterprise", "cloud")
        "port" = $ApiPort
    }
}
$synvoxConfig | Add-Member -NotePropertyName "edition" -NotePropertyValue $Edition -Force
$synvoxConfig | Add-Member -NotePropertyName "bind" -NotePropertyValue $ResolvedBind -Force
$synvoxConfig | Add-Member -NotePropertyName "_installed_by" -NotePropertyValue "Install-SynVox.ps1" -Force
$synvoxConfig | Add-Member -NotePropertyName "_installed_at" -NotePropertyValue (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz") -Force
$synvoxConfig | Add-Member -NotePropertyName "_installed_on_host" -NotePropertyValue $env:COMPUTERNAME -Force
($synvoxConfig | ConvertTo-Json -Depth 10) | Set-Content -Path $synvoxConfigPath -Encoding UTF8
Get-Content $synvoxConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json | Out-Null
Write-Log "OK" "Wrote $synvoxConfigPath (edition=$Edition, bind=$ResolvedBind)"

[Environment]::SetEnvironmentVariable("SYNVOX_EDITION", $Edition, "User")
[Environment]::SetEnvironmentVariable("SYNVOX_BIND", $ResolvedBind, "User")
$env:SYNVOX_EDITION = $Edition
$env:SYNVOX_BIND = $ResolvedBind
Write-Log "OK" "Persisted SYNVOX_EDITION=$Edition and SYNVOX_BIND=$ResolvedBind for user $env:USERNAME (setx-equivalent; environment wins over the config file per synvox.template.json's own convention)"
Grant-UsersModify $synvoxConfigPath

# ============================================================
# 3. Provider lane - the Claude Max subscription lane
# ============================================================
Write-Log "INFO" "---- Step 3: provider lane (Claude Max subscription) ----"

# ---- resolve claude.exe ----
$ResolvedClaudeBin = ""
if ($ClaudeBin) {
    if (Test-Path $ClaudeBin) {
        $ResolvedClaudeBin = $ClaudeBin
    } else {
        Write-Log "FAIL" "-ClaudeBin '$ClaudeBin' does not exist."
        exit 1
    }
} else {
    $liveConfigPath = Join-Path $ConfigDir "ai_providers.json"
    if (Test-Path $liveConfigPath) {
        try {
            $existing = Get-Content $liveConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $existingConn = $existing.connections | Where-Object { $_.id -eq "claude_max" } | Select-Object -First 1
            if ($existingConn -and $existingConn.bin -and ($existingConn.bin -notlike "REPLACE_ME*") -and (Test-Path $existingConn.bin)) {
                $ResolvedClaudeBin = $existingConn.bin
                Write-Log "INFO" "Reusing claude.exe already configured in config\ai_providers.json: $ResolvedClaudeBin"
            }
        } catch {
            Write-Log "WARN" "Could not read existing config\ai_providers.json to reuse claude.exe: $($_.Exception.Message)"
        }
    }
    if (-not $ResolvedClaudeBin) {
        $cmd = Get-Command claude -ErrorAction SilentlyContinue
        if ($cmd) { $ResolvedClaudeBin = $cmd.Source }
    }
    if (-not $ResolvedClaudeBin) {
        $guess = Join-Path $env:USERPROFILE ".local\bin\claude.exe"
        if (Test-Path $guess) { $ResolvedClaudeBin = $guess }
    }
}

if (-not $ResolvedClaudeBin) {
    Write-Log "FAIL" "claude CLI not found. Pass -ClaudeBin <absolute path to claude.exe>, or install Claude Code and ensure it is on PATH."
    Write-Log "FAIL" "Each principal (Renne, Urcil, ...) uses THEIR OWN claude.exe and their own Max plan - never share one install's binary path with another's."
    exit 1
}

# ---- resolve the OAuth env file ----
$ResolvedClaudeEnvFile = $ClaudeEnvFile
if (-not $ResolvedClaudeEnvFile) {
    # claude_max.env is the convention. It was claude_cli.env here while every
    # other surface - the committed docs, the install guide and the live
    # config\ai_providers.json - said claude_max.env, so an install that took
    # the default wrote an env_file_ref pointing at a file nobody creates.
    # Corrected 2026-08-18.
    $PreferredEnvFile = Join-Path $SecretsDir "claude_max.env"
    $LegacyEnvFile    = Join-Path $SecretsDir "claude_cli.env"

    if ((-not (Test-Path $PreferredEnvFile)) -and (Test-Path $LegacyEnvFile)) {
        # An install made before the rename. Use what is actually there rather
        # than pointing at a file that does not exist, and say so loudly - the
        # fix is a rename, and this script is not going to do it silently.
        $ResolvedClaudeEnvFile = $LegacyEnvFile
        Write-Log "WARN" "No -ClaudeEnvFile given. $PreferredEnvFile does not exist but $LegacyEnvFile does, so this install is using the legacy name."
        Write-Log "WARN" "Rename it to claude_max.env when convenient - that is the name every other SynVox surface uses."
    } else {
        $ResolvedClaudeEnvFile = $PreferredEnvFile
        Write-Log "INFO" "No -ClaudeEnvFile given - defaulting to $ResolvedClaudeEnvFile"
    }
}

# ---- verify headless auth via qi_claude_brain.cli_status() ----
$tmpCheck = Join-Path $LogDir ("_claude_cli_check_{0}.py" -f ([guid]::NewGuid().ToString("N")))
$checkCode = @'
# -*- coding: utf-8 -*-
import json
import os
import sys

sys.path.insert(0, r"C:\QIH\engine\common")
import qi_claude_brain as brain

cfg = {
    "bin": os.environ.get("SYNVOX_CHECK_BIN", ""),
    "env_file": os.environ.get("SYNVOX_CHECK_ENV_FILE", ""),
    "timeout": int(os.environ.get("SYNVOX_CHECK_TIMEOUT", "20")),
}
result = brain.cli_status(cfg)
sys.stdout.write(json.dumps(result))
'@
Set-Content -Path $tmpCheck -Value $checkCode -Encoding UTF8
$env:SYNVOX_CHECK_BIN = $ResolvedClaudeBin
$env:SYNVOX_CHECK_ENV_FILE = $ResolvedClaudeEnvFile
$env:SYNVOX_CHECK_TIMEOUT = "20"
$checkOut = & $VenvPy $tmpCheck 2>&1
$global:LASTEXITCODE = 0
Remove-Item -Path $tmpCheck -Force -ErrorAction SilentlyContinue
Remove-Item Env:\SYNVOX_CHECK_BIN, Env:\SYNVOX_CHECK_ENV_FILE, Env:\SYNVOX_CHECK_TIMEOUT -ErrorAction SilentlyContinue

$cliStatus = $null
try {
    $cliStatus = ($checkOut | Select-Object -Last 1) | ConvertFrom-Json
} catch {
    Write-Log "FAIL" "cli_status() check crashed: $checkOut"
    exit 1
}

if (-not $cliStatus.ok) {
    Write-Log "FAIL" "claude CLI check failed: $($cliStatus.error)"
    Write-Log "FAIL" "Remedy: verify -ClaudeBin points at a real claude.exe (tried: $ResolvedClaudeBin), then re-run."
    exit 1
}
Write-Log "OK" "claude CLI found: $($cliStatus.bin) ($($cliStatus.version))"

if (-not $cliStatus.token_set) {
    Write-Log "FAIL" "claude CLI is NOT headless-authenticated (no CLAUDE_CODE_OAUTH_TOKEN)."
    Write-Log "FAIL" "Remedy, run as the person whose Max plan this is (interactively, once):"
    Write-Log "FAIL" "  1. `"$ResolvedClaudeBin`" setup-token"
    Write-Log "FAIL" "  2. Put the printed token into $ResolvedClaudeEnvFile as:"
    Write-Log "FAIL" "       CLAUDE_CODE_OAUTH_TOKEN=<token>"
    Write-Log "FAIL" "  3. Re-run this installer."
    exit 1
}
Write-Log "OK" "claude CLI is headless-authenticated (CLAUDE_CODE_OAUTH_TOKEN present via $ResolvedClaudeEnvFile)"
Set-Result "claude_cli" "PASS ($($cliStatus.version))"

# Defense in depth: if the OAuth env file lives inside this project (the
# default convention), tighten its ACL too. It holds a real token - never its
# value, just the fact that it exists gets logged.
if ((Test-Path $ResolvedClaudeEnvFile) -and ($ResolvedClaudeEnvFile -like "$ProjectDir*")) {
    Protect-SecretFile $ResolvedClaudeEnvFile
    Write-Log "INFO" "Tightened ACL on $ResolvedClaudeEnvFile (owner + Administrators + SYSTEM only)"
}

# ---- write references (never a token value) into the live ai_providers.json ----
$liveConfigPath = Join-Path $ConfigDir "ai_providers.json"
$templateConfigPath = Join-Path $ConfigDir "ai_providers.template.json"
try {
    if (-not (Test-Path $liveConfigPath)) {
        if (-not (Test-Path $templateConfigPath)) {
            throw "neither ai_providers.json nor ai_providers.template.json found under $ConfigDir"
        }
        Copy-Item $templateConfigPath $liveConfigPath
        Write-Log "INFO" "config\ai_providers.json did not exist - seeded from ai_providers.template.json"
    } else {
        Copy-Item $liveConfigPath "$liveConfigPath.bak" -Force
        Write-Log "INFO" "Backed up existing config\ai_providers.json -> ai_providers.json.bak"
    }
    $payload = Get-Content $liveConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $foundConn = $false
    foreach ($conn in $payload.connections) {
        if ($conn.id -eq "claude_max") {
            $conn.bin = $ResolvedClaudeBin
            $conn.env_file_ref = $ResolvedClaudeEnvFile
            $conn.enabled = $true
            $foundConn = $true
        }
    }
    if (-not $foundConn) {
        throw "config\ai_providers.json has no connections[] entry with id 'claude_max' - schema mismatch (see SynVox_Architecture_v1.md section 7.5); refusing to guess at the shape."
    }
    ($payload | ConvertTo-Json -Depth 25) | Set-Content -Path $liveConfigPath -Encoding UTF8
    Get-Content $liveConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json | Out-Null
    Write-Log "OK" "Wrote claude_max.bin and .env_file_ref (references only) into config\ai_providers.json"
    Set-Result "ai_providers_config" "PASS"
} catch {
    Write-Log "FAIL" "Could not update config\ai_providers.json: $($_.Exception.Message)"
    Set-Result "ai_providers_config" "FAIL"
    exit 1
}
Grant-UsersModify $liveConfigPath

# ============================================================
# 4. Secrets it doesn't have - the API bearer token
# ============================================================
Write-Log "INFO" "---- Step 4: secrets ----"

$apiTokenPath = Join-Path $SecretsDir "api_token.txt"
if ((Test-Path $apiTokenPath) -and ((Get-Content $apiTokenPath -Raw -Encoding UTF8).Trim().Length -gt 0)) {
    Write-Log "OK" "SynVox API bearer token already present at $apiTokenPath - kept as-is (value never logged)."
    Set-Result "api_token" "PASS (existing, kept)"
} else {
    $token = New-SecureToken
    Set-Content -Path $apiTokenPath -Value $token -Encoding UTF8 -NoNewline
    $token = $null
    Write-Log "OK" "Generated a new SynVox API bearer token at $apiTokenPath (value never logged)."
    Set-Result "api_token" "PASS (generated)"
}
Protect-SecretFile $apiTokenPath

$routerTokenPath = Join-Path $SecretsDir "router_token.txt"
if (Test-Path $routerTokenPath) {
    Write-Log "OK" "AI Router bearer token already present at $routerTokenPath (generated by the router itself on first run; not touched here)."
} else {
    Write-Log "INFO" "AI Router bearer token not present yet - tools\run_router.py generates it on first run."
}
Grant-UsersModify $SecretsDir

# ============================================================
# 5. NSSM services (optional, default OFF)
# ============================================================
Write-Log "INFO" "---- Step 5: services ----"

function Install-QiService {
    param(
        [string]$Name, [string]$Application, [string]$Arguments, [string]$AppDirectory,
        [string]$DisplayName, [string]$Description, [string]$StdoutLog, [string]$StderrLog,
        [hashtable]$EnvExtra
    )
    $existing = Get-Service -Name $Name -ErrorAction SilentlyContinue
    if (-not $existing) {
        & $Nssm install $Name $Application | Out-Null
        Write-Log "INFO" "  nssm install $Name"
    } else {
        Write-Log "INFO" "  $Name already exists - updating parameters (idempotent)"
    }
    & $Nssm set $Name AppParameters $Arguments | Out-Null
    & $Nssm set $Name AppDirectory $AppDirectory | Out-Null
    & $Nssm set $Name DisplayName $DisplayName | Out-Null
    & $Nssm set $Name Description $Description | Out-Null
    New-Item -ItemType Directory -Force -Path (Split-Path $StdoutLog) | Out-Null
    & $Nssm set $Name AppStdout $StdoutLog | Out-Null
    & $Nssm set $Name AppStderr $StderrLog | Out-Null
    if ($EnvExtra -and $EnvExtra.Count -gt 0) {
        $envLines = ($EnvExtra.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join "`r`n"
        & $Nssm set $Name AppEnvironmentExtra $envLines | Out-Null
    }
    & $Nssm set $Name Start SERVICE_AUTO_START | Out-Null
    $svc = Get-Service -Name $Name -ErrorAction SilentlyContinue
    if ($svc -and $svc.Status -eq "Running") {
        & $Nssm restart $Name 2>&1 | Out-Null
    } else {
        & $Nssm start $Name 2>&1 | Out-Null
    }
    $global:LASTEXITCODE = 0
}

if (-not $InstallServices) {
    Write-Log "INFO" "Services not installed (pass -InstallServices to register QI_SynVoxAPI). Router service-ification is additionally gated behind -Force - see CLAUDE.md and the note below."
    Write-Log "INFO" "Recommended way to run the AI Router today: interactively, as yourself -  python tools\run_router.py  (from $ProjectDir)"
    Set-Result "svc_api" "SKIPPED (-InstallServices not passed)"
    Set-Result "svc_router" "SKIPPED (-InstallServices not passed)"
} elseif (-not (Test-Path $Nssm)) {
    Write-Log "FAIL" "nssm.exe not found at $Nssm - cannot install services."
    Set-Result "svc_api" "FAIL (nssm.exe missing)"
    Set-Result "svc_router" "FAIL (nssm.exe missing)"
} else {
    $serverPath = Join-Path $ProjectDir "synvox_server.py"
    if (-not (Test-Path $serverPath)) {
        Write-Log "FAIL" "synvox_server.py not found at $serverPath - the API service entry point has not been built yet (owned by a concurrent build)."
        Write-Log "FAIL" "Skipping QI_SynVoxAPI registration. Re-run  install-synvox -InstallServices  once it exists."
        Set-Result "svc_api" "FAIL (synvox_server.py not yet built)"
    } else {
        & $VenvPy -c "import fastapi, uvicorn" 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            $global:LASTEXITCODE = 0
            Write-Log "FAIL" "fastapi/uvicorn not importable in the engine venv ($VenvPy) - cannot start the API service reliably."
            Set-Result "svc_api" "FAIL (fastapi/uvicorn missing in engine venv)"
        } else {
            $global:LASTEXITCODE = 0
            Install-QiService -Name "QI_SynVoxAPI" -Application $VenvPy -Arguments "synvox_server.py" `
                -AppDirectory $ProjectDir -DisplayName "QI - SynVox API" `
                -Description "SynVox scenario/run API (FastAPI) on $ResolvedBind`:$ApiPort. AppDirectory $ProjectDir." `
                -StdoutLog (Join-Path $LogDir "synvox_api_stdout.log") -StderrLog (Join-Path $LogDir "synvox_api_stderr.log") `
                -EnvExtra @{ "PYTHONUTF8" = "1"; "SYNVOX_EDITION" = $Edition; "SYNVOX_BIND" = $ResolvedBind; "SYNVOX_PORT" = "$ApiPort" }
            Write-Log "OK" "QI_SynVoxAPI registered/updated and started"
            Set-Result "svc_api" "PASS (installed)"
        }
    }

    if (-not $Force) {
        Write-Log "INFO" "QI_SynVoxRouter NOT registered as a service (needs -Force). This is deliberate - see the warning below."
        Write-Log "INFO" "The registry's own note on this project agrees: 'a PERSONAL Claude Max subscription should not be driven from an NSSM service account.'"
        Set-Result "svc_router" "SKIPPED (needs -InstallServices AND -Force)"
    } else {
        Write-Log "WARN" "=========================================================================="
        Write-Log "WARN" "  SERVICE-IFYING THE AI ROUTER (-Force was passed)"
        Write-Log "WARN" "  QI NSSM services run under a service account (typically LocalSystem)."
        Write-Log "WARN" "  The AI Router drives a PERSONAL Claude Max subscription via headless"
        Write-Log "WARN" "  'claude -p'. CLAUDE.md and the SynVox registry entry both flag that a"
        Write-Log "WARN" "  personal subscription should not be driven from a service account -"
        Write-Log "WARN" "  the QI Connector executor itself runs as NT AUTHORITY\SYSTEM, which is"
        Write-Log "WARN" "  exactly the wrong principal for this lane. Proceeding because -Force"
        Write-Log "WARN" "  was explicitly passed, but this is not the recommended configuration."
        Write-Log "WARN" "  Recommended instead: run it interactively -  python tools\run_router.py"
        Write-Log "WARN" "=========================================================================="
        $routerPy = Join-Path $ProjectDir "tools\run_router.py"
        if (-not (Test-Path $routerPy)) {
            Write-Log "FAIL" "tools\run_router.py not found at $routerPy."
            Set-Result "svc_router" "FAIL (tools\run_router.py missing)"
        } else {
            $systemPy = $null
            $cmd = Get-Command python -ErrorAction SilentlyContinue
            if ($cmd) { $systemPy = $cmd.Source }
            $routerPyExe = $VenvPy
            if ($systemPy) {
                & $systemPy -c "import fastapi, uvicorn" 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) { $routerPyExe = $systemPy }
                $global:LASTEXITCODE = 0
            }
            Install-QiService -Name "QI_SynVoxRouter" -Application $routerPyExe -Arguments "tools\run_router.py" `
                -AppDirectory $ProjectDir -DisplayName "QI - SynVox AI Router" `
                -Description "SynVox AI Router (subscription lane) - OpenAI-compatible shim over the Claude Max CLI. Loopback only, 127.0.0.1:$RouterPort. AppDirectory $ProjectDir." `
                -StdoutLog (Join-Path $LogDir "synvox_router_stdout.log") -StderrLog (Join-Path $LogDir "synvox_router_stderr.log") `
                -EnvExtra @{ "PYTHONUTF8" = "1" }
            Write-Log "OK" "QI_SynVoxRouter registered/updated and started (interpreter: $routerPyExe)"
            Set-Result "svc_router" "PASS (installed, -Force)"
        }
    }
}

# ============================================================
# 6. Health check
# ============================================================
Write-Log "INFO" "---- Step 6: health check ----"

$routerCheckCode = @'
# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"C:\APPS\SynVox")
try:
    from synvox.ai.router import create_app
    create_app()
    sys.stdout.write("OK")
except Exception as exc:
    sys.stdout.write("FAIL: " + str(exc))
'@
$tmpRouterCheck = Join-Path $LogDir ("_router_import_check_{0}.py" -f ([guid]::NewGuid().ToString("N")))
Set-Content -Path $tmpRouterCheck -Value $routerCheckCode -Encoding UTF8
$routerCheckOut = (& $VenvPy $tmpRouterCheck 2>&1 | Select-Object -Last 1)
$global:LASTEXITCODE = 0
Remove-Item -Path $tmpRouterCheck -Force -ErrorAction SilentlyContinue
if ("$routerCheckOut" -eq "OK") {
    Write-Log "OK" "synvox.ai.router.create_app() loads cleanly (config parses, claude CLI resolves, token file writable) - no port bound by this check."
    Set-Result "router_import" "PASS"
} else {
    Write-Log "FAIL" "synvox.ai.router.create_app() failed: $routerCheckOut"
    Set-Result "router_import" "FAIL"
}

$serverPath = Join-Path $ProjectDir "synvox_server.py"
if (Test-Path $serverPath) {
    Write-Log "INFO" "synvox_server.py exists - not import-checked here (owned by a concurrent build); verify manually or via its own health check."
    Set-Result "api_entrypoint" "PRESENT (not import-checked by this installer)"
} else {
    Write-Log "INFO" "synvox_server.py does not exist yet (concurrent build in progress) - SYNVOX_EDITION/SYNVOX_BIND (config\synvox.json and matching env vars) are configured and waiting for it."
    Set-Result "api_entrypoint" "PENDING (not yet built)"
}

# ============================================================
# 7. Service registry doc
# ============================================================
Write-Log "INFO" "---- Step 7: QI_Service_Registry.md ----"

$registeredAny = ($script:Results["svc_api"] -like "PASS*") -or ($script:Results["svc_router"] -like "PASS*")
if (-not $registeredAny) {
    Write-Log "INFO" "No services were registered this run - QI_Service_Registry.md left unchanged."
    Set-Result "service_registry_doc" "SKIPPED (no services registered)"
} elseif (-not (Test-Path $ServiceRegistryDoc)) {
    Write-Log "WARN" "QI_Service_Registry.md not found at $ServiceRegistryDoc - could not update it."
    Set-Result "service_registry_doc" "FAIL (doc not found)"
} else {
    $docLines = Get-Content -Path $ServiceRegistryDoc -Encoding UTF8
    $docText = $docLines -join "`n"
    $newRows = @()
    if (($script:Results["svc_api"] -like "PASS*") -and ($docText -notmatch "QI_SynVoxAPI")) {
        $newRows += "| SynVox API not responding on :$ApiPort | QI_SynVoxAPI | ``$LogDir\synvox_api_stderr.log`` | ``nssm status QI_SynVoxAPI``, then ``curl http://$ResolvedBind`:$ApiPort/health`` |"
    }
    if (($script:Results["svc_router"] -like "PASS*") -and ($docText -notmatch "QI_SynVoxRouter")) {
        $newRows += "| SynVox AI Router (:$RouterPort) not responding / persona runs stuck | QI_SynVoxRouter | ``$LogDir\synvox_router_stderr.log`` | ``nssm status QI_SynVoxRouter``, then ``curl http://127.0.0.1:$RouterPort/health``. Loopback only, service-ified with -Force per Install-SynVox.ps1 - the recommended default is running it interactively instead. |"
    }
    if ($newRows.Count -eq 0) {
        Write-Log "INFO" "QI_Service_Registry.md already documents the service(s) registered this run - nothing to add."
        Set-Result "service_registry_doc" "SKIPPED (already documented)"
    } else {
        $anchor = ($docLines | Select-String -Pattern "^## Python Migration Note" | Select-Object -First 1)
        if (-not $anchor) {
            Write-Log "WARN" "Could not find the lookup-table insertion point in QI_Service_Registry.md - appending at end of file instead."
            Add-Content -Path $ServiceRegistryDoc -Value ("`n" + ($newRows -join "`n") + "`n") -Encoding UTF8
        } else {
            $idx = $anchor.LineNumber - 1
            $before = $docLines[0..($idx - 1)]
            $after = $docLines[$idx..($docLines.Count - 1)]
            $updated = $before + $newRows + @("") + $after
            Set-Content -Path $ServiceRegistryDoc -Value $updated -Encoding UTF8
        }
        Write-Log "OK" "Appended $($newRows.Count) row(s) to QI_Service_Registry.md"
        Set-Result "service_registry_doc" "PASS (updated)"
    }
}

# ============================================================
# 8. Hand the whole project tree back to the interactive user (SYSTEM safety)
# ============================================================
Grant-UsersModify $ProjectDir

# ============================================================
# Summary
# ============================================================
Write-Log "INFO" "===================== PASS/FAIL SUMMARY ====================="
$failCount = 0
foreach ($k in $script:Results.Keys) {
    $status = $script:Results[$k]
    if ($status -like "FAIL*") { $failCount++ }
    Write-Log "INFO" ("{0,-22} : {1}" -f $k, $status)
}
Write-Log "INFO" "Edition            : $Edition"
Write-Log "INFO" "API bind            : $ResolvedBind`:$ApiPort"
Write-Log "INFO" "Router bind         : 127.0.0.1:$RouterPort (always)"
Write-Log "INFO" "Master log          : $MasterLog"
Write-Log "INFO" "================================================================"

if ($failCount -gt 0) {
    Write-Log "FAIL" "$failCount check(s) failed - see FAIL rows above."
    exit 1
}
exit 0

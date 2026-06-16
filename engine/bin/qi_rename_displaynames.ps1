# =============================================================================
# QI Service DisplayName Standardisation
# Created: 2026-05-20
# Scheduled to run: 2026-05-20 22:00 (one-shot)
#
# What this does:
#   - Renames the DisplayName of 10 QI services to the "QI . <Project> <Role>"
#     format so they're consistent and easy to find in services.msc.
#   - The internal service Name stays unchanged (no impact on nssm/sc/scripts).
#   - Updates the Description field so each service describes itself accurately.
#
# What this does NOT do:
#   - Does NOT remove or rename the 3 legacy services
#     (NEXUSTunnel, NayaTunnel, OC-Keepalive-Service) - those need separate
#     confirmation since removal is destructive.
#   - Does NOT restart any service. DisplayName changes are picked up
#     immediately by services.msc on refresh.
# =============================================================================

$ErrorActionPreference = "Continue"
$nssm = "C:\QIH\engine\bin\nssm.exe"
$logPath = "C:\QIH\logs\qi_rename_displaynames.log"

function Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "$ts  $msg"
    Write-Host $line
    Add-Content -Path $logPath -Value $line -Encoding UTF8
}

# Ensure log dir exists
$logDir = Split-Path $logPath -Parent
if (!(Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }

Log "=== QI DisplayName standardisation starting ==="

# Service Name -> (New DisplayName, New Description)
$renames = @(
    @{ Name = "QI_BrainAPI";        Display = "QI . Brain API";              Desc = "QI Brain - hive nervous system. FastAPI on port 9011 (SQLite + ChromaDB + MCP)." }
    @{ Name = "QI_Dashboard";       Display = "QI . Hive Dashboard";         Desc = "QI Hive agent orchestration UI. Port 8600." }
    @{ Name = "QI_DashboardTunnel"; Display = "QI . Hive Dashboard Tunnel";  Desc = "QI Hive Dashboard Cloudflare Quick Tunnel (port 8600 -> public)." }
    @{ Name = "QI_MaiaBot";         Display = "QI . Maia Bot";               Desc = "Maia AI assistant platform. FastAPI on port 8001 (LINE, Telegram, FB, IG)." }
    @{ Name = "QI_MaiaDemoTunnel";  Display = "QI . Maia Demo Tunnel";       Desc = "Cloudflare quick tunnel exposing Maia Gradio demo UI (port 7860)." }
    @{ Name = "QI_MaiaGradio";      Display = "QI . Maia Gradio UI";         Desc = "Maia Gradio web UI on port 7860. Browser-based chat interface." }
    @{ Name = "QI_MaiaTunnel";      Display = "QI . Maia Tunnel";            Desc = "Cloudflare tunnel exposing Maia Bot (port 8001) to the public production endpoint." }
    @{ Name = "QI_NayaBot";         Display = "QI . Naya Bot";               Desc = "Naya personal AI assistant. Telegram bot + file management (port 8002)." }
    @{ Name = "QI_NayaGradio";      Display = "QI . Naya Gradio UI";         Desc = "Naya Gradio web interface on port 7861. Browser-based UI for Naya." }
    @{ Name = "QI_NEXUS";           Display = "QI . NEXUS API";              Desc = "Quiddity Innovations NEXUS - Neural Exchange and Unified Synthesis. FastAPI on port 8010 + Gradio UI on port 7880." }
)

$total = $renames.Count
$ok = 0
$failed = 0

foreach ($r in $renames) {
    $name = $r.Name
    Log "--- Renaming $name ---"

    # Verify service exists
    & $nssm status $name 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Log "  SKIP: service $name not found"
        $failed++
        continue
    }

    # Capture current values for the log
    $oldDisplay = (& $nssm get $name DisplayName) 2>&1
    Log "  Old DisplayName: $oldDisplay"
    Log "  New DisplayName: $($r.Display)"

    # Apply DisplayName
    $out = & $nssm set $name DisplayName $r.Display 2>&1
    if ($LASTEXITCODE -ne 0) {
        Log "  FAIL DisplayName: $out"
        $failed++
        continue
    }

    # Apply Description
    $out = & $nssm set $name Description $r.Desc 2>&1
    if ($LASTEXITCODE -ne 0) {
        Log "  WARN Description: $out (continuing)"
    }

    Log "  OK"
    $ok++
}

Log "=== Done: $ok/$total renamed, $failed failed ==="

# Self-delete the scheduled task (one-shot)
try {
    schtasks /Delete /TN "QI_RenameDisplayNames" /F 2>&1 | Out-Null
    Log "Scheduled task QI_RenameDisplayNames removed (one-shot complete)"
} catch {
    Log "Could not auto-remove scheduled task: $_"
}

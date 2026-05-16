# QI Hive — emergency control for Tasuke + Kaze
# Usage:
#   qi-bots status
#   qi-bots stop     [tasuke|kaze|both]   (default: both)
#   qi-bots start    [tasuke|kaze|both]
#   qi-bots restart  [tasuke|kaze|both]
#   qi-bots tail     [tasuke|kaze]   N=50
#   qi-bots tail-err [tasuke|kaze]   N=50
#   qi-bots refilter        # re-apply wire filter v4 + restart both
#
# All commands run inside WSL (Ubuntu-24.04) as user hyosuke.
# Designed for fast triage when a bot misbehaves in Bot Perspective or anywhere else.

param(
    [Parameter(Position=0)] [string]$Verb = "status",
    [Parameter(Position=1)] [string]$Target = "both",
    [Parameter(Position=2)] [int]$N = 50
)

$ErrorActionPreference = "Stop"
$env:MSYS_NO_PATHCONV = "1"

function Invoke-Wsl([string]$Cmd) {
    & wsl.exe -d Ubuntu-24.04 -u hyosuke -- bash -lc $Cmd
}

function Resolve-Services([string]$t) {
    switch ($t.ToLower()) {
        "tasuke" { return @("openclaw-gateway") }
        "kaze"   { return @("openclaw-gateway-kaze") }
        "both"   { return @("openclaw-gateway", "openclaw-gateway-kaze") }
        default  { throw "Target must be: tasuke | kaze | both (got: $t)" }
    }
}

function Show-Status {
    Write-Host "QI Hive bot status:" -ForegroundColor Cyan
    Invoke-Wsl "systemctl --user is-active openclaw-gateway openclaw-gateway-kaze; echo '---'; systemctl --user status openclaw-gateway openclaw-gateway-kaze --no-pager -n 0 2>/dev/null | grep -E 'Active:|Main PID:|Memory:|openclaw-gateway' | head -20"
}

function Do-Stop([string[]]$svcs) {
    foreach ($s in $svcs) {
        Write-Host "Stopping $s ..." -ForegroundColor Yellow
        Invoke-Wsl "systemctl --user stop $s"
    }
    Show-Status
}

function Do-Start([string[]]$svcs) {
    foreach ($s in $svcs) {
        Write-Host "Starting $s ..." -ForegroundColor Green
        Invoke-Wsl "systemctl --user start $s"
    }
    Show-Status
}

function Do-Restart([string[]]$svcs) {
    foreach ($s in $svcs) {
        Write-Host "Restarting $s ..." -ForegroundColor Magenta
        Invoke-Wsl "systemctl --user restart $s"
    }
    Show-Status
}

function Do-Tail([string]$t, [int]$lines, [bool]$err) {
    $svc = (Resolve-Services $t)[0]
    $flag = if ($err) { "-p err" } else { "" }
    Write-Host "Last $lines lines of $svc $(if($err){'(errors)'}else{''}):" -ForegroundColor Cyan
    Invoke-Wsl "journalctl --user -u $svc $flag -n $lines --no-pager"
}

function Do-Refilter {
    Write-Host "Re-applying wire filter v4 ..." -ForegroundColor Cyan
    Invoke-Wsl "python3 /mnt/c/QIH/engine/bin/openclaw_qi_patches/apply_filter_patch.py"
    Write-Host "Restarting both gateways ..." -ForegroundColor Magenta
    Invoke-Wsl "systemctl --user restart openclaw-gateway openclaw-gateway-kaze"
    Show-Status
}

switch ($Verb.ToLower()) {
    "status"   { Show-Status }
    "stop"     { Do-Stop    (Resolve-Services $Target) }
    "start"    { Do-Start   (Resolve-Services $Target) }
    "restart"  { Do-Restart (Resolve-Services $Target) }
    "tail"     { if ($Target -eq "both") { $Target = "tasuke" }; Do-Tail $Target $N $false }
    "tail-err" { if ($Target -eq "both") { $Target = "tasuke" }; Do-Tail $Target $N $true }
    "refilter" { Do-Refilter }
    "help"     {
        Write-Host @"
qi-bots — emergency control for Tasuke + Kaze

  qi-bots status                        show both gateways' state
  qi-bots stop     [tasuke|kaze|both]   kill bot(s) immediately (default: both)
  qi-bots start    [tasuke|kaze|both]   bring them back
  qi-bots restart  [tasuke|kaze|both]   stop + start
  qi-bots tail     [tasuke|kaze] [N]    last N lines of journalctl (default 50)
  qi-bots tail-err [tasuke|kaze] [N]    error-priority lines only
  qi-bots refilter                      re-apply wire filter v4 + restart both
"@ -ForegroundColor Gray
    }
    default { throw "Unknown verb '$Verb'. Try: qi-bots help" }
}

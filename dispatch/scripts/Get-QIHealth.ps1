# ============================================================
#  Get-QIHealth.ps1  -  QI machine health snapshot
#  Read-only. Dumps every QI_* service state, disk space, and a
#  /health probe of each registered project port.
#  Run: powershell -NoProfile -ExecutionPolicy Bypass -File .\Get-QIHealth.ps1
#       or remotely: qi_execute_script("qi-health-snapshot")
# ============================================================

$ErrorActionPreference = "Continue"
$ProgressPreference    = "SilentlyContinue"

$LogDir    = "C:\QIH\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$SnapLog   = Join-Path $LogDir ("qi_health_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
$Registry  = "C:\QIH\ecosystem\qi_registry.json"

function Write-Log {
    param([string]$Msg)
    Write-Host $Msg
    Add-Content -Path $SnapLog -Value $Msg -Encoding UTF8
}

Write-Log ("===== QI health snapshot {0} on {1} =====" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $env:COMPUTERNAME)

# ---------- Services ----------
Write-Log ""
Write-Log "--- QI_* Windows services ---"
Get-Service -Name "QI_*" -ErrorAction SilentlyContinue |
    Sort-Object Name |
    ForEach-Object { Write-Log ("{0,-26} {1}" -f $_.Name, $_.Status) }

# ---------- Disks ----------
Write-Log ""
Write-Log "--- Disk space ---"
Get-PSDrive -PSProvider FileSystem -ErrorAction SilentlyContinue |
    Where-Object { $_.Used -ne $null } |
    ForEach-Object {
        $freeGB  = [math]::Round($_.Free / 1GB, 1)
        $totalGB = [math]::Round((($_.Used + $_.Free) / 1GB), 1)
        $pct     = if ($totalGB -gt 0) { [math]::Round(100 * $freeGB / $totalGB, 1) } else { 0 }
        Write-Log ("{0}:  {1} GB free of {2} GB  ({3}% free)" -f $_.Name, $freeGB, $totalGB, $pct)
    }

# ---------- Port health probes (from the registry) ----------
Write-Log ""
Write-Log "--- API /health probes (registered ports) ---"
if (Test-Path $Registry) {
    $reg = Get-Content $Registry -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($p in $reg.projects) {
        if (-not $p.ports) { continue }
        foreach ($portProp in $p.ports.PSObject.Properties) {
            $port = $portProp.Value.current
            if ($port -isnot [int]) { continue }
            $state = "DOWN"
            try {
                $r = Invoke-WebRequest -Uri ("http://127.0.0.1:{0}/health" -f $port) -TimeoutSec 2 -UseBasicParsing
                $state = "HTTP {0}" -f $r.StatusCode
            } catch {
                try {
                    $t = Test-NetConnection -ComputerName 127.0.0.1 -Port $port -WarningAction SilentlyContinue
                    if ($t.TcpTestSucceeded) { $state = "OPEN (no /health)" }
                } catch {}
            }
            Write-Log ("{0,-18} {1,-6} {2,-6} {3}" -f $p.id, $portProp.Name, $port, $state)
        }
    }
} else {
    Write-Log "Registry not found at $Registry"
}

Write-Log ""
Write-Log "Snapshot log: $SnapLog"
Write-Log "===== end ====="

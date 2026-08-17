# Post-rename sweep: what, if anything, broke?
#
# The rename is the real test. Anything that still names C:\1-AI (other than
# the deliberate PYTHON junction) is now pointing at a path that does not
# resolve, and should surface here rather than at 3am in a nightly job.
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

Write-Output "=== 1. the junction, and what is left of C:\1-AI ==="
Get-ChildItem 'C:\1-AI' -Force -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Output ("  " + $_.Name + "   " + $_.Attributes)
}
$j = Get-Item 'C:\1-AI\APPS\PYTHON' -Force -ErrorAction SilentlyContinue
if ($j) { Write-Output ("  junction target: " + $j.Target) }

Write-Output ""
Write-Output "=== 2. every service: does its Application exist? ==="
$bad = 0
foreach ($s in (Get-CimInstance Win32_Service | Where-Object { $_.PathName -match 'nssm' })) {
    $k = 'HKLM:\SYSTEM\CurrentControlSet\Services\' + $s.Name + '\Parameters'
    $p = Get-ItemProperty $k -ErrorAction SilentlyContinue
    if (-not $p -or -not $p.Application) { continue }
    if (-not (Test-Path $p.Application)) {
        Write-Output ("  BROKEN  " + $s.Name.PadRight(24) + " " + $p.Application)
        $bad++
    }
    foreach ($f in @('AppDirectory','AppParameters')) {
        $v = "" + $p.$f
        if ($v -match 'C:\\1-AI' -and $v -notmatch 'APPS\\PYTHON') {
            Write-Output ("  STALE   " + $s.Name.PadRight(24) + " " + $f + " = " + $v)
            $bad++
        }
    }
}
Write-Output ("  services with a broken or stale path: " + $bad)

Write-Output ""
Write-Output "=== 3. scheduled tasks: interpreter and script resolve? ==="
$tbad = 0
foreach ($t in (Get-ScheduledTask)) {
    foreach ($a in $t.Actions) {
        $blob = "" + $a.Execute + " " + $a.Arguments
        if ($blob -notmatch 'python|\.py') { continue }
        if ($blob -match 'C:\\1-AI' -and $blob -notmatch 'APPS\\PYTHON') {
            Write-Output ("  STALE   " + $t.TaskPath + $t.TaskName)
            $tbad++
        }
    }
}
Write-Output ("  tasks with a stale path: " + $tbad)

Write-Output ""
Write-Output "=== 4. environment: anything naming the retired tree? ==="
$ebad = 0
foreach ($scope in @('Machine','User')) {
    $vars = [Environment]::GetEnvironmentVariables($scope)
    foreach ($k in $vars.Keys) {
        $v = "" + $vars[$k]
        if ($v -like '*1-AI*') {
            if ($k -ieq 'Path') {
                foreach ($b in ($v -split ';' | Where-Object { $_ -like '*1-AI*' })) {
                    $ok = Test-Path $b
                    Write-Output ("  " + $scope + " PATH: " + $b + "   resolves=" + $ok)
                    if (-not $ok) { $ebad++ }
                }
            } else {
                Write-Output ("  " + $scope + " " + $k + " = " + $v)
                $ebad++
            }
        }
    }
}
Write-Output ("  broken environment entries: " + $ebad)

Write-Output ""
Write-Output "=== 5. service estate ==="
Get-Service | Where-Object { $_.Name -match 'QI_|ClaudeManager|NayaTunnel|NEXUSTunnel|OC-Keepalive' } |
    Group-Object Status | ForEach-Object { Write-Output ("  " + $_.Name + ": " + $_.Count) }
$down = Get-Service -Name 'QI_*' | Where-Object { $_.Status -ne 'Running' } | Select-Object -ExpandProperty Name
Write-Output ("  QI_ not running: " + ($down -join ', '))

Write-Output ""
Write-Output "=== 6. health endpoints ==="
$urls = @(
    'http://127.0.0.1:8600/api/status',
    'http://127.0.0.1:9011/health',
    'http://127.0.0.1:8650/health',
    'http://127.0.0.1:8189/system_stats',
    'http://127.0.0.1:8001/health',
    'http://127.0.0.1:8002/health',
    'http://127.0.0.1:8010/health',
    'http://127.0.0.1:8651/mcp',
    'http://127.0.0.1:8701/mcp'
)
foreach ($u in $urls) {
    try {
        $r = Invoke-WebRequest -Uri $u -TimeoutSec 8 -UseBasicParsing
        Write-Output ("  " + $u.PadRight(40) + " HTTP " + $r.StatusCode)
    } catch {
        $code = $_.Exception.Response.StatusCode.value__
        if ($code) {
            Write-Output ("  " + $u.PadRight(40) + " HTTP " + $code)
        } else {
            Write-Output ("  " + $u.PadRight(40) + " no response")
        }
    }
}

Write-Output ""
Write-Output "=== 7. interpreter resolution in a NEW process ==="
$w = (Get-Command python -ErrorAction SilentlyContinue).Source
Write-Output ("  python -> " + $w)
Write-Output ("  py -0p:")
& py -0p 2>&1 | ForEach-Object { Write-Output ("    " + $_) }

Write-Output ""
Write-Output ("Retired tree size: " + [math]::Round(((Get-ChildItem 'C:\1-AI.RETIRED_2026-08-09' -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum)/1GB,2) + " GB")
Write-Output "=== DONE ==="

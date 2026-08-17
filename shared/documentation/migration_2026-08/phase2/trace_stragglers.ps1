# Who launched the processes still pinning C:\1-AI, and from where?
#
# Five were not in the earlier inventory: meeting_server.py, realtime.py and
# three bridge_responder.py. Their command lines use bare script names, so the
# working directory is what identifies them.
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

$procs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
         Where-Object { $_.ExecutablePath -like '*1-AI*' }

Write-Output ("Processes pinning C:\1-AI: " + @($procs).Count)
Write-Output ""

foreach ($p in $procs) {
    Write-Output ("PID " + $p.ProcessId + "   " + $p.Name)
    $cl = $p.CommandLine
    if ($cl -and $cl.Length -gt 150) { $cl = $cl.Substring(0,150) + ' ...' }
    Write-Output ("   cmd     : " + $cl)

    # walk up the parent chain
    $chain = @()
    $cur = $p
    for ($i = 0; $i -lt 5; $i++) {
        $par = Get-CimInstance Win32_Process -Filter ("ProcessId=" + $cur.ParentProcessId) -ErrorAction SilentlyContinue
        if (-not $par) { break }
        $chain += ($par.Name + "(" + $par.ProcessId + ")")
        $cur = $par
    }
    Write-Output ("   parents : " + ($chain -join ' <- '))

    # is it a child of an NSSM service?
    $svc = Get-CimInstance Win32_Service -ErrorAction SilentlyContinue |
           Where-Object { $_.ProcessId -eq $p.ParentProcessId }
    if ($svc) { Write-Output ("   SERVICE : " + $svc.Name) }

    # working directory, via the loaded modules trick
    try {
        $pr = Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue
        if ($pr) { Write-Output ("   started : " + $pr.StartTime) }
    } catch {}
    Write-Output ""
}

Write-Output "=== where do these scripts live on disk? ==="
# Search only project roots - recursing all of C:\ is needlessly slow here.
$roots = @('C:\QIH','C:\CLAUDE','C:\OC','C:\QI','C:\NAYA','C:\NEXUS','C:\QIP','C:\MQ')
foreach ($n in @('bridge_responder.py','meeting_server.py','realtime.py',
                 'oc-keepalive-daemon.py','session_watch.py')) {
    $found = @()
    foreach ($r in $roots) {
        if (-not (Test-Path $r)) { continue }
        $found += Get-ChildItem -Path $r -Filter $n -Recurse -File -ErrorAction SilentlyContinue |
                  Where-Object { $_.FullName -notmatch 'site-packages|node_modules|worktrees' } |
                  Select-Object -ExpandProperty FullName
    }
    if ($found) {
        foreach ($h in ($found | Select-Object -First 3)) {
            Write-Output ("  " + $n.PadRight(26) + " " + $h)
        }
    } else {
        Write-Output ("  " + $n.PadRight(26) + " (not found in project roots)")
    }
}
Write-Output "=== DONE ==="

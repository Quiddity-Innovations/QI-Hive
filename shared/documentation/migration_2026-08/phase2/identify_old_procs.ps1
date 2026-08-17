# Who is still executing C:\1-AI\APPS\PYTHON, now that all 31 services are
# repointed? Anything listed here pins the old tree and must be accounted for
# before Phase 3 deletes it.
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

$procs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
         Where-Object { $_.ExecutablePath -like '*1-AI\APPS\PYTHON*' }

Write-Output ("Processes on the old interpreter: " + @($procs).Count)
Write-Output ""

foreach ($p in $procs) {
    $parent = Get-CimInstance Win32_Process -Filter ("ProcessId=" + $p.ParentProcessId) -ErrorAction SilentlyContinue
    $pname  = if ($parent) { $parent.Name } else { '(gone)' }

    # Is this process a child of a service?
    $svc = Get-CimInstance Win32_Service -ErrorAction SilentlyContinue |
           Where-Object { $_.ProcessId -eq $p.ParentProcessId -or $_.ProcessId -eq $p.ProcessId } |
           Select-Object -First 1

    Write-Output ("PID " + $p.ProcessId)
    Write-Output ("   exe    : " + $p.ExecutablePath)
    $cl = $p.CommandLine
    if ($cl -and $cl.Length -gt 200) { $cl = $cl.Substring(0,200) + ' ...' }
    Write-Output ("   cmdline: " + $cl)
    Write-Output ("   parent : PID " + $p.ParentProcessId + "  " + $pname)
    if ($svc) { Write-Output ("   service: " + $svc.Name) }
    Write-Output ("   started: " + $p.CreationDate)
    Write-Output ""
}

Write-Output "=== Grouped by what the command line points at ==="
$procs | ForEach-Object {
    $cl = $_.CommandLine
    if ($cl -match '([A-Za-z]:\\[^"]*\.py)') { $Matches[1] } else { '(no .py in cmdline)' }
} | Group-Object | Sort-Object Count -Descending | ForEach-Object {
    Write-Output ("  " + $_.Count + "x  " + $_.Name)
}
Write-Output "=== DONE ==="

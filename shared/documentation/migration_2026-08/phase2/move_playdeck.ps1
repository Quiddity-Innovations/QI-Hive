# PlayDeck needs a careful move: it owns a live SQLite database.
#
# The generic mover aborted on a file-count mismatch, correctly. The 5 files it
# could not copy were data\.runtime_url, two log files being written during the
# copy, and playdeck.db-shm / playdeck.db-wal.
#
# The last two matter. A SQLite database in WAL mode keeps recent commits in the
# -wal file until a checkpoint folds them back into the .db. Copying the .db
# while the -wal is live and open can therefore silently lose the most recent
# writes. A clean shutdown checkpoints and removes both sidecars - so their
# ABSENCE after stopping the service is the signal that the database is
# consistent and safe to copy.
#
# Pure ASCII only.
param([switch]$Apply)
$ErrorActionPreference = 'Continue'

$src  = 'C:\PlayDeck'
$dst  = 'C:\APPS\PlayDeck'
$hold = 'D:\_PREMOVE_2026-08-09\PlayDeck'
$svc  = 'QI_PlayDeck'

Write-Output "=== state ==="
Write-Output ("  service : " + (Get-Service -Name $svc -ErrorAction SilentlyContinue).Status)
foreach ($f in @('data\playdeck.db','data\playdeck.db-wal','data\playdeck.db-shm')) {
    $p = Join-Path $src $f
    if (Test-Path $p) {
        Write-Output ("  " + $f.PadRight(24) + " " + (Get-Item $p).Length + " bytes")
    } else {
        Write-Output ("  " + $f.PadRight(24) + " (absent)")
    }
}

if (-not $Apply) { Write-Output ""; Write-Output "DRY RUN"; exit 0 }

Write-Output ""
Write-Output "=== removing the partial copy ==="
if (Test-Path $dst) {
    Remove-Item $dst -Recurse -Force -ErrorAction SilentlyContinue
    Write-Output ("  removed, exists=" + (Test-Path $dst))
}

Write-Output ""
Write-Output "=== stopping the service so SQLite checkpoints ==="
Stop-Service -Name $svc -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 8
Write-Output ("  state: " + (Get-Service -Name $svc -ErrorAction SilentlyContinue).Status)

# Any process still holding the tree?
#
# The first version of this matched on the bare word 'PlayDeck' and excluded
# anything containing 'APPS'. This script's own path is
# ...\phase2\move_playdeck.ps1 - it matches 'PlayDeck', contains no 'APPS', and
# so the script KILLED ITSELF. That is the silent exit 255 with no output.
#
# Two guards now: match the actual app directory rather than the bare word, and
# never target this process or any of its ancestors.
$selfChain = @($PID)
$cur = $PID
for ($i = 0; $i -lt 6; $i++) {
    $p = Get-CimInstance Win32_Process -Filter ("ProcessId=" + $cur) -ErrorAction SilentlyContinue
    if (-not $p -or -not $p.ParentProcessId) { break }
    $selfChain += $p.ParentProcessId
    $cur = $p.ParentProcessId
}

$holders = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessId -notin $selfChain -and
    (
        ($_.ExecutablePath -and $_.ExecutablePath -like 'C:\PlayDeck\*') -or
        ($_.CommandLine -and $_.CommandLine -match [regex]::Escape('C:\PlayDeck\'))
    )
}
foreach ($h in $holders) {
    Write-Output ("  still holding the tree: PID " + $h.ProcessId + "  " + $h.Name)
    Stop-Process -Id $h.ProcessId -Force -ErrorAction SilentlyContinue
    Write-Output ("     terminated")
}
if (-not $holders) { Write-Output "  no process is holding C:\PlayDeck" }
Start-Sleep -Seconds 4

Write-Output ""
Write-Output "=== WAL checkpointed? ==="
$wal = Join-Path $src 'data\playdeck.db-wal'
$shm = Join-Path $src 'data\playdeck.db-shm'
$walGone = -not (Test-Path $wal)
$shmGone = -not (Test-Path $shm)
Write-Output ("  -wal gone : " + $walGone)
Write-Output ("  -shm gone : " + $shmGone)
if (-not ($walGone -and $shmGone)) {
    Write-Output "  sidecars still present - the database did not close cleanly."
    Write-Output "  Copying them alongside the .db so no committed data is lost."
}

Write-Output ""
Write-Output "=== copying ==="
& robocopy.exe $src $dst /E /MT:16 /R:2 /W:2 /NFL /NDL /NP /NJH /NJS | Out-Null
Write-Output ("  robocopy exit " + $LASTEXITCODE)

$sf = (Get-ChildItem $src -Recurse -File -ErrorAction SilentlyContinue).Count
$df = (Get-ChildItem $dst -Recurse -File -ErrorAction SilentlyContinue).Count
Write-Output ("  source files: " + $sf + "   dest files: " + $df)
if ($df -lt $sf) {
    Write-Output "  MISMATCH - listing what is missing:"
    $a = Get-ChildItem $src -Recurse -File | ForEach-Object { $_.FullName.Substring($src.Length).ToLower() }
    $b = Get-ChildItem $dst -Recurse -File | ForEach-Object { $_.FullName.Substring($dst.Length).ToLower() }
    foreach ($m in (Compare-Object $a $b | Where-Object { $_.SideIndicator -eq '<=' })) {
        Write-Output ("     " + $m.InputObject)
    }
}

# the database itself must match byte-for-byte
$sdb = Join-Path $src 'data\playdeck.db'
$ddb = Join-Path $dst 'data\playdeck.db'
if ((Test-Path $sdb) -and (Test-Path $ddb)) {
    $h1 = (Get-FileHash $sdb -Algorithm SHA256).Hash
    $h2 = (Get-FileHash $ddb -Algorithm SHA256).Hash
    Write-Output ""
    Write-Output ("  playdeck.db SHA256 match: " + ($h1 -eq $h2))
    if ($h1 -ne $h2) { Write-Output "  ABORT: database copy differs"; exit 1 }
}

Write-Output ""
Write-Output "=== repointing the service ==="
$key = 'HKLM:\SYSTEM\CurrentControlSet\Services\' + $svc + '\Parameters'
$p = Get-ItemProperty $key -ErrorAction SilentlyContinue
foreach ($f in @('Application','AppDirectory','AppParameters','AppStdout','AppStderr')) {
    $v = "" + $p.$f
    if ($v -and $v -like "*C:\PlayDeck*") {
        $nv = $v.Replace('C:\PlayDeck', $dst)
        Set-ItemProperty -Path $key -Name $f -Value $nv
        Write-Output ("  " + $f + " -> " + $nv)
    }
}

Write-Output ""
Write-Output "=== starting ==="
Start-Service -Name $svc -ErrorAction SilentlyContinue
$deadline = (Get-Date).AddSeconds(60)
do {
    Start-Sleep -Seconds 3
    $st = (Get-Service -Name $svc -ErrorAction SilentlyContinue).Status
} while ($st -ne 'Running' -and (Get-Date) -lt $deadline)
Write-Output ("  state: " + $st)

if ($st -eq 'Running') {
    Write-Output ""
    Write-Output "=== retiring the original ==="
    New-Item -ItemType Directory -Path (Split-Path $hold) -Force | Out-Null
    & robocopy.exe $src $hold /E /MOVE /MT:16 /R:1 /W:1 /NFL /NDL /NP /NJH /NJS | Out-Null
    if (Test-Path $src) { Remove-Item $src -Recurse -Force -ErrorAction SilentlyContinue }
    Write-Output ("  C:\PlayDeck exists : " + (Test-Path $src) + "   (must be False)")
    Write-Output ("  held at " + $hold + " : " + (Test-Path $hold))
} else {
    Write-Output "  service did not start - original LEFT IN PLACE for rollback"
}
Write-Output "=== DONE ==="

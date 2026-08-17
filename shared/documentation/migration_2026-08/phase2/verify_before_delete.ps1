# Is C:\1-AI.RETIRED_2026-08-09 actually safe to delete?
#
# Checks the four things Renne named - AvatarStudio, LM Studio, Python, VSCode -
# by asking: does a WORKING copy exist OUTSIDE the retired tree?
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

$retired = 'C:\1-AI.RETIRED_2026-08-09'

function Report($name, $livePath, $retiredPath, $note) {
    $live = Test-Path $livePath
    $inRetired = Test-Path $retiredPath
    Write-Output ("--- " + $name + " ---")
    Write-Output ("  live copy   : " + $livePath)
    Write-Output ("     exists   : " + $live)
    Write-Output ("  in retired  : " + $inRetired)
    if ($note) { Write-Output ("  note       : " + $note) }
    if ($live) { Write-Output "  VERDICT    : SAFE - a working copy exists outside the retired tree" }
    else       { Write-Output "  VERDICT    : *** NOT SAFE - only copy is inside the retired tree ***" }
    Write-Output ""
}

Write-Output "================= CAN C:\1-AI.RETIRED BE DELETED? ================="
Write-Output ""

# 1. AvatarStudio
Report "AvatarStudio" 'C:\APPS\AvatarStudio\avatar_studio.py' `
    (Join-Path $retired 'APPS\AvatarStudio') `
    "registered path in qi_registry.json should be C:\APPS\AvatarStudio"

# 2. Python
Report "Python 3.11" 'C:\Program Files\Python311\python.exe' `
    (Join-Path $retired 'APPS\PYTHON\python.exe') ''

# 3. VSCode
$vsLocations = @(
    'C:\Program Files\Microsoft VS Code\Code.exe',
    'C:\Users\renne\AppData\Local\Programs\Microsoft VS Code\Code.exe',
    'C:\1-AI\APPS\VSCode\Microsoft VS Code\Code.exe'
)
Write-Output "--- VSCode ---"
$vsFound = $false
foreach ($p in $vsLocations) {
    $e = Test-Path $p
    Write-Output ("  " + $p + " : " + $e)
    if ($e) { $vsFound = $true }
}
Write-Output ("  in retired : " + (Test-Path (Join-Path $retired 'APPS\VSCode')))
if ($vsFound) { Write-Output "  VERDICT    : a copy exists outside the retired tree" }
else          { Write-Output "  VERDICT    : *** NOT SAFE - no VSCode outside the retired tree ***" }
Write-Output ""

# 4. LM Studio
$lmLocations = @(
    'C:\Program Files\LM Studio\LM Studio.exe',
    'C:\Users\renne\AppData\Local\Programs\LM Studio\LM Studio.exe',
    'C:\Users\renne\AppData\Local\LM-Studio\LM Studio.exe',
    'C:\1-AI\APPS\LMStudio\LM Studio\LM Studio.exe'
)
Write-Output "--- LM Studio ---"
$lmFound = $false
foreach ($p in $lmLocations) {
    $e = Test-Path $p
    Write-Output ("  " + $p + " : " + $e)
    if ($e) { $lmFound = $true }
}
Write-Output ("  models dir (survives regardless): " + (Test-Path 'C:\Users\renne\.lmstudio'))
Write-Output ("  in retired : " + (Test-Path (Join-Path $retired 'APPS\LMStudio')))
if ($lmFound) { Write-Output "  VERDICT    : a copy exists outside the retired tree" }
else          { Write-Output "  VERDICT    : *** NOT SAFE - no LM Studio outside the retired tree ***" }
Write-Output ""

Write-Output "================= WHAT IS ACTUALLY IN THE RETIRED TREE ================="
Get-ChildItem $retired -Recurse -Depth 2 -Directory -ErrorAction SilentlyContinue |
    ForEach-Object { Write-Output ("  " + $_.FullName.Substring($retired.Length)) }

Write-Output ""
Write-Output "================= WHAT IS IN C:\1-AI (the stub) ================="
Get-ChildItem 'C:\1-AI' -Recurse -Depth 2 -Force -ErrorAction SilentlyContinue |
    ForEach-Object { Write-Output ("  " + $_.FullName + "   " + $_.Attributes) }

Write-Output ""
Write-Output "================= ANYTHING STILL POINTING AT THE RETIRED TREE ================="
$n = 0
foreach ($scope in @('Machine','User')) {
    $vars = [Environment]::GetEnvironmentVariables($scope)
    foreach ($k in $vars.Keys) {
        $v = "" + $vars[$k]
        if ($v -match '1-AI') {
            foreach ($bit in ($v -split ';')) {
                if ($bit -match '1-AI') {
                    Write-Output ("  " + $scope + " " + $k + " : " + $bit + "   resolves=" + (Test-Path $bit))
                    $n++
                }
            }
        }
    }
}
Write-Output ("  environment entries naming 1-AI: " + $n)
Write-Output "=== DONE ==="

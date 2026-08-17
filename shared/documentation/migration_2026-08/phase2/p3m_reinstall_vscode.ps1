# Phase 3m - reinstall VSCode to a standard location.
#
# First attempt failed the same way the Python install did: winget found the
# existing registration (pointing into C:\1-AI\APPS\VSCode), switched to
# upgrade mode, ignored --scope machine, and reinstalled to the OLD path -
# recreating C:\1-AI\APPS\VSCode underneath the junction directory.
#
# The fix is identical: remove the registration first, so the fresh install has
# nothing to "upgrade" and honours the requested target.
#
# User data is untouched throughout: settings live in %APPDATA%\Code and
# extensions in %USERPROFILE%\.vscode, neither of which is inside the install
# directory.
# Pure ASCII only.
$ErrorActionPreference = 'Continue'

$strays = @('C:\1-AI\APPS\VSCode')
$target = 'C:\Program Files\Microsoft VS Code'

Write-Output "=== BEFORE ==="
Write-Output ("  C:\1-AI\APPS\VSCode exists : " + (Test-Path 'C:\1-AI\APPS\VSCode'))
Write-Output ("  Program Files install      : " + (Test-Path (Join-Path $target 'Code.exe')))
Write-Output ("  user settings preserved    : " + (Test-Path 'C:\Users\renne\AppData\Roaming\Code'))
Write-Output ("  extensions preserved       : " + (Test-Path 'C:\Users\renne\.vscode'))

Write-Output ""
Write-Output "=== STEP 1: uninstall the existing registration ==="
& winget uninstall --id Microsoft.VisualStudioCode --silent --disable-interactivity 2>&1 |
    ForEach-Object { Write-Output ("  " + $_) }

Start-Sleep -Seconds 5

Write-Output ""
Write-Output "=== STEP 2: remove leftover program files ==="
foreach ($s in $strays) {
    if (Test-Path $s) {
        try {
            Remove-Item $s -Recurse -Force -ErrorAction Stop
            Write-Output ("  removed " + $s)
        } catch {
            Write-Output ("  could not remove " + $s + " : " + $_.Exception.Message)
        }
    } else {
        Write-Output ("  already gone: " + $s)
    }
}

Write-Output ""
Write-Output "=== STEP 3: confirm C:\1-AI holds ONLY the junction again ==="
Get-ChildItem 'C:\1-AI' -Recurse -Depth 1 -Force -ErrorAction SilentlyContinue |
    ForEach-Object { Write-Output ("  " + $_.FullName + "   " + $_.Attributes) }

Write-Output ""
Write-Output "=== STEP 4: install to Program Files ==="
& winget install --id Microsoft.VisualStudioCode --scope machine --silent `
    --accept-package-agreements --accept-source-agreements --disable-interactivity 2>&1 |
    ForEach-Object { Write-Output ("  " + $_) }

Write-Output ""
Write-Output "=== STEP 5: verify ==="
$exe = Join-Path $target 'Code.exe'
Write-Output ("  " + $target + "\Code.exe : " + (Test-Path $exe))
Write-Output ("  bin dir                  : " + (Test-Path (Join-Path $target 'bin')))
Write-Output ("  C:\1-AI\APPS\VSCode back?: " + (Test-Path 'C:\1-AI\APPS\VSCode'))
if (Test-Path $exe) {
    Write-Output ("  version: " + ((& $exe --version 2>&1) -join ' | '))
}
Write-Output ("  settings still present   : " + (Test-Path 'C:\Users\renne\AppData\Roaming\Code'))
Write-Output ("  extensions still present : " + (Test-Path 'C:\Users\renne\.vscode'))
Write-Output "=== DONE ==="

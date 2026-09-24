@echo off
setlocal
:: QI rename wave 1 - NEXUS - ROLLBACK. Restores QI_NEXUS, QI_NEXUSTunnel and
:: QI_NexusMCP from the saved configs and puts the 42 files back as they were.
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  Requesting Administrator privileges...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)
cd /d "%~dp0"
set "GO="
set /p GO=Type ROLLBACK to restore the old NEXUS service names:
if /i not "%GO%"=="ROLLBACK" (
    echo  Cancelled - nothing changed.
    pause
    exit /b 0
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0QI_Rename_NEXUS.ps1" -Rollback
echo.
pause
exit /b 0

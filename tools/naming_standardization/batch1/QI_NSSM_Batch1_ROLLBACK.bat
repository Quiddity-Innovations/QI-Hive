@echo off
setlocal
:: QI NSSM Batch 1 - ROLLBACK. Restores every service's previous NSSM binary,
:: display name and dependencies from the newest batch1_rollback_*.json.
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  Requesting Administrator privileges...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)
cd /d "%~dp0"
set "GO="
set /p GO=Type ROLLBACK to restore the previous state:
if /i not "%GO%"=="ROLLBACK" (
    echo  Cancelled - nothing changed.
    pause
    exit /b 0
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0QI_NSSM_Batch1.ps1" -Rollback
echo.
pause
exit /b 0

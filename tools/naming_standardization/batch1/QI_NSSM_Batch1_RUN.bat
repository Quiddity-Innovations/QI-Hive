@echo off
setlocal
:: QI NSSM Batch 1 - run tonight (Renne, 2026-09-24). Double-click, approve UAC.
:: Moves 58 QI services onto their own app's NSSM copy, cleans display names,
:: drops the NEXUS/Maia/Naya boot dependency on QI_BrainAPI. No renames.
:: Running services restart one at a time (~5-15 s outage each, ~15 min total).
:: Each failure rolls back that one service. Undo everything: QI_NSSM_Batch1_ROLLBACK.bat

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  Requesting Administrator privileges...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)
cd /d "%~dp0"
echo.
echo  =====================================================
echo    QI NSSM Batch 1 - per-app NSSM + display names
echo  =====================================================
echo.
echo  Step 1/2: dry run (changes nothing)
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0QI_NSSM_Batch1.ps1"
if errorlevel 1 (
    echo.
    echo  Dry run failed - nothing was changed. See logs\ in this folder.
    pause
    exit /b 1
)
echo.
echo  About 47 running services will restart one by one (short outages).
set "GO="
set /p GO=Type YES to apply, anything else to cancel:
if /i not "%GO%"=="YES" (
    echo  Cancelled - nothing changed.
    pause
    exit /b 0
)
echo.
echo  Step 2/2: applying...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0QI_NSSM_Batch1.ps1" -Execute
echo.
echo  Done. Result: %~dp0batch1_result.json
echo  Tell Claude "Batch 1 ran" next session - it will verify every service.
echo.
pause
exit /b 0

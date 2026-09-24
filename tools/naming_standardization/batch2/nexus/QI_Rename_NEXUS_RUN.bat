@echo off
setlocal
:: QI rename wave 1 - NEXUS (Renne, 2026-09-24). Double-click, approve UAC.
::   QI_NEXUS -> QI_NEXUS_Server, QI_NEXUSTunnel -> QI_NEXUS_Tunnel,
::   QI_NexusMCP -> QI_NEXUS_MCP, plus the 42 files that use those names.
:: NEXUS is down for about 30-60 s. Any failure restores everything.
:: Close the Windows "Services" window first. Undo: QI_Rename_NEXUS_ROLLBACK.bat

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  Requesting Administrator privileges...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)
cd /d "%~dp0"
echo.
echo  =====================================================
echo    QI rename wave 1 - NEXUS services
echo  =====================================================
echo.
echo  Step 1/2: dry run (changes nothing)
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0QI_Rename_NEXUS.ps1"
if errorlevel 1 (
    echo.
    echo  Dry run failed - nothing was changed. See logs\ in this folder.
    pause
    exit /b 1
)
echo.
echo  NEXUS will be down for about a minute while its 3 services are rebuilt.
set "GO="
set /p GO=Type YES to apply, anything else to cancel:
if /i not "%GO%"=="YES" (
    echo  Cancelled - nothing changed.
    pause
    exit /b 0
)
echo.
echo  Step 2/2: applying...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0QI_Rename_NEXUS.ps1" -Execute
echo.
echo  Done. Tell Claude "NEXUS rename ran" - it will verify and commit.
echo.
pause
exit /b 0

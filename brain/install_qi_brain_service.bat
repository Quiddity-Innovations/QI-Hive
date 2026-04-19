@echo off
:: ─────────────────────────────────────────────────────────────────────────────
:: QI Brain API — NSSM Service Installer
:: Service name: QI_BrainAPI  (was: QIBrainAPI — renamed 2026-04-19)
:: Location: C:\UNIVERSAL\qi_brain\install_qi_brain_service.bat
::
:: Run this as Administrator ONCE to register QI_BrainAPI as a Windows service.
:: After that:
::   - Brain API auto-starts on boot at port 9010
::   - No CMD window, runs silently as LOCAL SYSTEM account
::   - Manageable from QI Orchestrator Dashboard > QI Brain tab
::   - Restartable via: nssm restart QI_BrainAPI
::
:: Registry: C:\UNIVERSAL\ECOSYSTEM\QI_Service_Registry.md
::
:: Requirements:
::   nssm.exe in C:\UNIVERSAL\dashboard\
::   Python at C:\1-AI\APPS\PYTHON\python.exe (update after migration)
::   qi_brain_api.py at C:\UNIVERSAL\qi_brain\qi_brain_api.py
:: ─────────────────────────────────────────────────────────────────────────────
setlocal

set NSSM=C:\UNIVERSAL\dashboard\nssm.exe
set SVC=QI_BrainAPI
set PYTHON=C:\1-AI\APPS\PYTHON\python.exe
set SCRIPT=C:\UNIVERSAL\qi_brain\qi_brain_api.py
set DIR=C:\UNIVERSAL\qi_brain
set LOG=C:\UNIVERSAL\qi_brain\LOGS\qi_brain_api.log

echo ============================================================
echo  QI Brain API — NSSM Service Installer
echo ============================================================
echo.

echo [1/6] Checking for existing service...
%NSSM% status %SVC% >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo     Existing service found — stopping and removing...
    %NSSM% stop %SVC% >nul 2>&1
    timeout /t 3 /nobreak >nul
    %NSSM% remove %SVC% confirm >nul 2>&1
    echo     Removed.
) else (
    echo     No existing service. Fresh install.
)

echo [2/6] Installing %SVC% service...
%NSSM% install %SVC% %PYTHON% %SCRIPT%
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: NSSM install failed. Is nssm.exe at %NSSM%?
    pause
    exit /b 1
)

echo [3/6] Configuring service settings...
%NSSM% set %SVC% AppDirectory %DIR%
%NSSM% set %SVC% DisplayName "QI — Brain API"
%NSSM% set %SVC% Description "QI Brain shared knowledge substrate. FastAPI on port 9010. Provides 12 MCP tools for ecosystem-wide memory, decisions, features, and session logging."
%NSSM% set %SVC% Start SERVICE_AUTO_START
%NSSM% set %SVC% AppStdout %LOG%
%NSSM% set %SVC% AppStderr %LOG%
%NSSM% set %SVC% AppRotateFiles 1
%NSSM% set %SVC% AppRotateBytes 10485760
%NSSM% set %SVC% AppRestartDelay 5000
%NSSM% set %SVC% ObjectName LocalSystem

echo [4/6] Starting service...
%NSSM% start %SVC%

echo [5/6] Verifying...
timeout /t 5 /nobreak >nul
%NSSM% status %SVC%

echo [6/6] Testing health endpoint...
timeout /t 3 /nobreak >nul
curl -s http://localhost:9010/health 2>nul && echo. || echo     (curl not available — check manually)

echo.
echo ============================================================
echo  Done! QI_BrainAPI service installed.
echo ============================================================
echo.
echo  Service name:  %SVC%
echo  Port:          9010
echo  Log file:      %LOG%
echo  Health check:  http://localhost:9010/health
echo.
echo  To manage:
echo    %NSSM% start   %SVC%
echo    %NSSM% stop    %SVC%
echo    %NSSM% restart %SVC%
echo    %NSSM% status  %SVC%
echo.
echo  After Python migration to C:\Python311\ update Python path with:
echo    %NSSM% set %SVC% Application C:\Python311\python.exe
echo    %NSSM% restart %SVC%
echo.
pause

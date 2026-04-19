@echo off
REM ============================================================
REM  QI Elevation Broker — one-time installer
REM  Installs QI_Elevate as a LocalSystem NSSM service so that
REM  non-admin agents can request whitelisted admin operations
REM  via C:\QIH\commands\pending\*.json drops.
REM
REM  MUST BE RUN AS ADMINISTRATOR.
REM ============================================================
setlocal
set NSSM=C:\QIH\engine\bin\nssm.exe
set PYTHON=C:\1-AI\APPS\PYTHON\python.exe
set SCRIPT=C:\QIH\engine\common\qi_elevate.py
set SVC=QI_Elevate
set APPDIR=C:\QIH\engine\common

echo.
echo === QI Elevation Broker Installer ===
echo Service : %SVC%
echo Python  : %PYTHON%
echo Script  : %SCRIPT%
echo.

REM Verify prerequisites
if not exist "%NSSM%" (
    echo [ERROR] NSSM not found at %NSSM%
    goto :end
)
if not exist "%PYTHON%" (
    echo [ERROR] Python not found at %PYTHON%
    goto :end
)
if not exist "%SCRIPT%" (
    echo [ERROR] Broker script not found at %SCRIPT%
    goto :end
)

REM Stop + remove existing service if present (idempotent re-install)
"%NSSM%" status %SVC% >nul 2>&1
if %ERRORLEVEL%==0 (
    echo [INFO] Existing %SVC% found — stopping and removing for clean install...
    "%NSSM%" stop %SVC% >nul 2>&1
    "%NSSM%" remove %SVC% confirm >nul 2>&1
)

REM Ensure log folder exists BEFORE nssm opens AppStdout/AppStderr
if not exist "C:\QIH\logs\elevation" mkdir "C:\QIH\logs\elevation"

echo [INFO] Installing %SVC%...
"%NSSM%" install %SVC% "%PYTHON%" "%SCRIPT%"
"%NSSM%" set %SVC% AppDirectory "%APPDIR%"
"%NSSM%" set %SVC% Description "QI Elevation Broker — executes whitelisted commands as SYSTEM on behalf of QI agents (see C:\QIH\docs\QI_Elevation_Broker.md)"
"%NSSM%" set %SVC% Start SERVICE_AUTO_START
"%NSSM%" set %SVC% ObjectName LocalSystem
"%NSSM%" set %SVC% AppStdout C:\QIH\logs\elevation\broker_stdout.log
"%NSSM%" set %SVC% AppStderr C:\QIH\logs\elevation\broker_stderr.log
"%NSSM%" set %SVC% AppRotateFiles 1
"%NSSM%" set %SVC% AppRotateBytes 5242880

echo [INFO] Starting %SVC%...
"%NSSM%" start %SVC%

echo.
echo [INFO] Status:
"%NSSM%" status %SVC%

echo.
echo === Done ===
echo Broker log : C:\QIH\logs\elevation\broker.log
echo Whitelist  : C:\QIH\commands\whitelist.json
echo Submit a command via: python C:\QIH\engine\common\qi_elevate_client.py
echo.

:end
pause
endlocal

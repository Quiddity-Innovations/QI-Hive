@echo off
REM ============================================================
REM  QI Hive Ingester — one-time installer
REM  Installs QI_HiveIngest NSSM service that absorbs project
REM  reports from C:\QIH\shared\reports\inbox\ into status.json.
REM
REM  MUST BE RUN AS ADMINISTRATOR (one time).
REM ============================================================
setlocal
set NSSM=C:\QIH\engine\bin\nssm.exe
set PYTHON=C:\1-AI\APPS\PYTHON\python.exe
set SCRIPT=C:\QIH\engine\hive\ingest\hive_ingest.py
set SVC=QI_HiveIngest
set APPDIR=C:\QIH\engine\hive\ingest

echo.
echo === QI Hive Ingester Installer ===
echo Service : %SVC%
echo Python  : %PYTHON%
echo Script  : %SCRIPT%
echo.

if not exist "%NSSM%"   ( echo [ERROR] NSSM missing & goto :end )
if not exist "%PYTHON%" ( echo [ERROR] Python missing & goto :end )
if not exist "%SCRIPT%" ( echo [ERROR] Script missing & goto :end )

if not exist "C:\QIH\logs\hive" mkdir "C:\QIH\logs\hive"

"%NSSM%" status %SVC% >nul 2>&1
if %ERRORLEVEL%==0 (
    echo [INFO] Existing %SVC% — stopping + removing for clean install
    "%NSSM%" stop %SVC% >nul 2>&1
    "%NSSM%" remove %SVC% confirm >nul 2>&1
)

echo [INFO] Installing %SVC%...
"%NSSM%" install %SVC% "%PYTHON%" "%SCRIPT%"
"%NSSM%" set %SVC% AppDirectory "%APPDIR%"
"%NSSM%" set %SVC% Description "QI Hive Ingester — absorbs agent reports from shared\reports\inbox into status.json (see C:\QIH\docs\QI_Hive_Reporting.md)"
"%NSSM%" set %SVC% Start SERVICE_AUTO_START
"%NSSM%" set %SVC% AppStdout C:\QIH\logs\hive\ingest_stdout.log
"%NSSM%" set %SVC% AppStderr C:\QIH\logs\hive\ingest_stderr.log
"%NSSM%" set %SVC% AppRotateFiles 1
"%NSSM%" set %SVC% AppRotateBytes 5242880

echo [INFO] Starting %SVC%...
"%NSSM%" start %SVC%

echo.
echo [INFO] Status:
"%NSSM%" status %SVC%
echo.
echo === Done ===
echo Log        : C:\QIH\logs\hive\ingest.log
echo Inbox      : C:\QIH\shared\reports\inbox\
echo Archive    : C:\QIH\shared\reports\archive\
echo Status file: C:\QIH\data\status.json (hive_reports array)
echo.

:end
pause
endlocal

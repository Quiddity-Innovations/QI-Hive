@echo off
REM ============================================================================
REM  4_RESTART_HIVE.bat
REM  Makes the Hive dashboard SHOW the corrected (permanent) tunnel addresses.
REM
REM  The dashboard code (server.py / link_collector.py) was already updated to
REM  resolve static quiddityinnovations.com URLs from tunnels.json, but the
REM  running QI_Dashboard service still holds the OLD code in memory. This:
REM    - regenerates links.json with the static URLs
REM    - restarts QI_Dashboard so it loads the new code
REM
REM  Requires Administrator (service control). This file self-elevates.
REM  Run this AFTER 1_PROVISION_TUNNELS.bat.
REM ============================================================================

REM --- self-elevate (UAC) ---
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo Requesting Administrator access...
  powershell -Command "Start-Process '%~f0' -Verb RunAs"
  exit /b
)

setlocal
set NSSM=C:\QIH\engine\bin\nssm.exe
set PY=C:\Program Files\Python311\python.exe
if not exist "%PY%" set PY=python

echo.
echo ======================================================================
echo   REFRESH + RESTART HIVE DASHBOARD
echo ======================================================================
echo.

echo --- regenerating links.json (static URLs) ---
"%PY%" "C:\QIH\engine\hive\dashboard\link_collector.py"
echo.

echo --- restarting QI_Dashboard ---
"%NSSM%" restart QI_Dashboard
echo.
echo --- status ---
"%NSSM%" status QI_Dashboard
echo.
echo Done. Open https://hive.quiddityinnovations.com (or http://localhost:8600)
echo and confirm every tile shows a *.quiddityinnovations.com address.
echo.
pause
endlocal

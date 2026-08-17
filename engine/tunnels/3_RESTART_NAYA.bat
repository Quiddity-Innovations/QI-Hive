@echo off
REM ============================================================================
REM  3_RESTART_NAYA.bat
REM  Restarts QI_NayaBot so naya_server.py re-registers its LINE webhook at boot
REM  with the permanent URL https://naya-line.quiddityinnovations.com/webhook/line
REM  (the old 90-second trycloudflare log-poll was removed).
REM
REM  Requires Administrator (service control). This file self-elevates.
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

echo.
echo ======================================================================
echo   RESTART QI_NayaBot
echo ======================================================================
echo.
echo --- restarting ---
"%NSSM%" restart QI_NayaBot
echo.
echo --- status ---
"%NSSM%" status QI_NayaBot
echo.
echo Done. Check C:\APPS\NAYA\LOGS for a line like:
echo   "LINE webhook auto-registered: https://naya-line.quiddityinnovations.com/webhook/line"
echo.
pause
endlocal

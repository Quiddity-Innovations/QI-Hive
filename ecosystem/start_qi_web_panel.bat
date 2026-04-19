@echo off
REM ============================================================
REM QI Universal Web Control Panel — launcher
REM Runs on http://localhost:8651
REM ============================================================
title QI Universal Web Control Panel (port 8651)
cd /d "%~dp0"
echo.
echo  ============================================================
echo     QI UNIVERSAL WEB CONTROL PANEL
echo  ============================================================
echo.
echo  Opening http://localhost:8651 in your browser in ~3 seconds...
echo  Close this window to shut the panel down.
echo.
start "" "http://localhost:8651"
python qi_web_panel.py
pause

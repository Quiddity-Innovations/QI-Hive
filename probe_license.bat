@echo off
title OnBase Licensing Probe
echo Starting the OnBase licensing probe runner...
echo.
cd /d "%~dp0"
python "%~dp0probe_license_server.py"
if errorlevel 1 (
  echo.
  echo Failed to start. Check that Python and pyodbc are installed.
  pause
)

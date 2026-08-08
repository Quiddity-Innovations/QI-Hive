@echo off
REM QI Launchpad - one-click opener
REM Refresh live tunnel URLs first (quick tunnels get a new URL each restart),
REM then open the page so the tunnel buttons point at the current URLs.
python "%~dp0refresh-tunnels.py" >nul 2>&1
if errorlevel 1 py "%~dp0refresh-tunnels.py" >nul 2>&1
start "" "%~dp0index.html"

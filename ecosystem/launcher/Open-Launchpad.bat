@echo off
REM QI Launchpad - convenience opener (delegates to the canonical launcher).
REM Canonical launcher lives in C:\QIH\landing (QI-Hive = source of truth).
REM This avoids a second copy that could drift. Refresh live tunnel URLs in
REM the canonical folder, then open the canonical page.
python "%~dp0..\..\landing\refresh-tunnels.py" >nul 2>&1
if errorlevel 1 py "%~dp0..\..\landing\refresh-tunnels.py" >nul 2>&1
start "" "%~dp0..\..\landing\index.html"

@echo off
REM ============================================================
REM  QI Static Named-Tunnel Migration — self-elevating runner
REM  Step 1 (do ONCE, as yourself, NOT elevated):
REM       cloudflared tunnel login
REM  Step 2: double-click this file (it will request admin).
REM ============================================================
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)
cd /d "%~dp0"
echo Running QI named-tunnel migration (elevated)...
python migrate_named_tunnels.py %*
echo.
echo --- verification ---
python verify_named_tunnels.py
pause

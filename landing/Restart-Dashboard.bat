@echo off
REM ============================================================
REM  Restart-Dashboard.bat - one-click restart of QI_Dashboard
REM  Self-elevating: prompts for admin (UAC) automatically.
REM  Use after editing the dashboard so it picks up new code
REM  (Launcher, Agents, Tunnels page, etc.).
REM ============================================================
setlocal
set "NSSM=C:\QIH\engine\bin\nssm.exe"
set "SVC=QI_Dashboard"

REM --- elevate if not already admin ---
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo Requesting administrator rights...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

echo.
echo Restarting %SVC% ...
"%NSSM%" restart %SVC%
echo.

echo Waiting for the dashboard to come back up...
timeout /t 3 /nobreak >nul

echo.
echo Service status:
"%NSSM%" status %SVC%
echo.

echo Checking routes:
powershell -NoProfile -Command "foreach($p in '/','/launcher','/tunnels'){ try { $c=(Invoke-WebRequest -UseBasicParsing -Uri ('http://localhost:8600'+$p) -TimeoutSec 6).StatusCode } catch { $c=$_.Exception.Message }; Write-Host ('  http://localhost:8600'+$p+'  ->  '+$c) }"
echo.
echo Done. If /tunnels shows 200, open:  http://localhost:8600/tunnels
echo.
pause

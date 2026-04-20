@echo off
REM install_broker_resilience.bat
REM Run elevated (or via gsudo). Installs BOTH:
REM   1. NSSM auto-restart on any exit (fast recovery, seconds)
REM   2. A 1-minute scheduled task watchdog (safety net)
REM Idempotent — safe to re-run.

setlocal
set NSSM=C:\QIH\engine\bin\nssm.exe
set PS=powershell -NoProfile -ExecutionPolicy Bypass -File C:\QIH\tools\broker_watchdog.ps1

echo [1/4] Configuring NSSM exit actions for QI_Elevate...
%NSSM% set QI_Elevate AppExit Default Restart
%NSSM% set QI_Elevate AppRestartDelay 3000
%NSSM% set QI_Elevate AppThrottle      1500

echo [2/4] Same treatment for QI_Dashboard and QI_HiveIngest (so they never silently die)...
%NSSM% set QI_Dashboard  AppExit Default Restart
%NSSM% set QI_Dashboard  AppRestartDelay 3000
%NSSM% set QI_HiveIngest AppExit Default Restart
%NSSM% set QI_HiveIngest AppRestartDelay 3000

echo [3/4] Registering QI_ElevateWatchdog scheduled task (SYSTEM, every 1 min)...
schtasks /Create /TN QI_ElevateWatchdog /TR "%PS%" /SC MINUTE /MO 1 /RU SYSTEM /RL HIGHEST /F

echo [4/4] Verifying...
%NSSM% get QI_Elevate AppExit Default
schtasks /Query /TN QI_ElevateWatchdog /FO LIST | findstr /i "TaskName Status Next"

echo.
echo DONE. QI_Elevate now auto-restarts via NSSM on any exit, and the
echo watchdog task checks it every minute as a safety net.
endlocal

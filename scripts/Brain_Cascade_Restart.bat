@echo off
:: QI Brain cascade restart — 2026-07-02
:: Reloads QI_BrainAPI (loads the new openai_hub provider code) by stopping
:: its four Windows-service dependents first, then bringing everything back.
:: Self-elevating: double-click it and accept the UAC prompt.

:: If not running elevated, relaunch ourselves with admin rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator rights...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

set NSSM=C:\QIH\engine\bin\nssm.exe

echo [1/3] Stopping dependents...
%NSSM% stop QI_Dashboard
%NSSM% stop QI_MaiaBot
%NSSM% stop QI_NayaBot
%NSSM% stop QI_NEXUS

echo [2/3] Restarting QI_BrainAPI...
%NSSM% restart QI_BrainAPI
timeout /t 8 /nobreak >nul

echo [3/3] Starting dependents...
%NSSM% start QI_NEXUS
%NSSM% start QI_NayaBot
%NSSM% start QI_MaiaBot
%NSSM% start QI_Dashboard

echo.
echo Done. Tell Claude "verify the cascade" to run all health checks.
pause

@echo off
REM ============================================================
REM  Install QI_Caddy as an NSSM Windows service
REM  RIGHT-CLICK THIS FILE -> "Run as administrator"
REM
REM  Before running: close the foreground Caddy window
REM  (Ctrl+C in the cmd window where caddy is running),
REM  otherwise the service can't bind ports 80/443.
REM ============================================================

set NSSM=C:\QIH\engine\bin\nssm.exe
set CADDY=C:\QIH\engine\bin\caddy.exe
set CFG=C:\QIH\engine\proxy\Caddyfile
set LOG=C:\QIH\logs\qi_caddy.log

echo Installing QI_Caddy ...
"%NSSM%" install QI_Caddy "%CADDY%" run --config "%CFG%"
"%NSSM%" set QI_Caddy AppDirectory C:\QIH\engine\proxy
"%NSSM%" set QI_Caddy DisplayName QI_Caddy
"%NSSM%" set QI_Caddy Description "QI Hive local reverse proxy (qi.local front door for all QI apps)"
"%NSSM%" set QI_Caddy Start SERVICE_AUTO_START
"%NSSM%" set QI_Caddy AppStdout "%LOG%"
"%NSSM%" set QI_Caddy AppStderr "%LOG%"
"%NSSM%" set QI_Caddy AppRotateFiles 1
"%NSSM%" set QI_Caddy AppRotateBytes 10485760

echo Starting QI_Caddy ...
"%NSSM%" start QI_Caddy

echo.
"%NSSM%" status QI_Caddy
echo.
echo Done. Test: https://lottery.qi.local
pause

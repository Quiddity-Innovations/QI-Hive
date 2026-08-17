@echo off
REM ============================================================================
REM  RUN_ALL.bat  -  one-click full tunnel cutover (elevate once)
REM  Runs the whole sequence in order:
REM     1) provision named tunnels + verify        (was 1_PROVISION_TUNNELS.bat)
REM     2) refresh + restart Hive dashboard        (was 4_RESTART_HIVE.bat)
REM     3) restart QI_NayaBot                       (was 3_RESTART_NAYA.bat)
REM     4) re-register webhooks (Maia + Naya TG)    (was 2_REGISTER_WEBHOOKS.bat)
REM
REM  The individual 1/2/3/4 files still exist for running steps on their own.
REM  This self-elevates once; you are already authenticated (cert.pem present).
REM ============================================================================

REM --- self-elevate (UAC) ---
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo Requesting Administrator access...
  powershell -Command "Start-Process '%~f0' -Verb RunAs"
  exit /b
)

setlocal
set TUN=C:\QIH\engine\tunnels
set NSSM=C:\QIH\engine\bin\nssm.exe
set PY=C:\Program Files\Python311\python.exe
if not exist "%PY%" set PY=python
set CERT=%USERPROFILE%\.cloudflared\cert.pem
cd /d "%TUN%"

echo.
echo ######################################################################
echo #  QI TUNNEL CUTOVER - FULL SEQUENCE                                  #
echo ######################################################################

if not exist "%CERT%" (
  echo.
  echo [!] cloudflared cert.pem NOT found for this user (%CERT%).
  echo     Open a NORMAL (non-admin) terminal and run:  cloudflared tunnel login
  echo     Pick quiddityinnovations.com, then re-run this file.
  echo.
  pause
  exit /b 1
)

echo.
echo ====================================================================
echo  STEP 1/4  Provision named tunnels + DNS + services, then verify
echo ====================================================================
"%PY%" migrate_named_tunnels.py
echo.
"%PY%" verify_named_tunnels.py

echo.
echo ====================================================================
echo  STEP 2/4  Refresh links.json + restart Hive dashboard (QI_Dashboard)
echo ====================================================================
"%PY%" "C:\QIH\engine\hive\dashboard\link_collector.py"
"%NSSM%" restart QI_Dashboard
"%NSSM%" status  QI_Dashboard

echo.
echo ====================================================================
echo  STEP 3/4  Restart QI_NayaBot (re-registers LINE webhook on boot)
echo ====================================================================
"%NSSM%" restart QI_NayaBot
"%NSSM%" status  QI_NayaBot

echo.
echo ====================================================================
echo  STEP 4/4  Re-register webhooks (automated: Maia LINE+TG, Naya TG)
echo ====================================================================
if exist "C:\APPS\QI\webhook_updater.py" ("%PY%" "C:\APPS\QI\webhook_updater.py") else (echo   [skip] C:\APPS\QI\webhook_updater.py not found)
echo.
if exist "C:\APPS\NAYA\tools\setup_telegram_webhook.py" ("%PY%" "C:\APPS\NAYA\tools\setup_telegram_webhook.py") else (echo   [skip] setup_telegram_webhook.py not found)

echo.
echo ######################################################################
echo #  AUTOMATED STEPS DONE. NOW DO THESE MANUALLY IN THE CONSOLES:      #
echo ######################################################################
echo   LINE  (developers.line.biz):
echo     Maia         -^> https://maia.quiddityinnovations.com/maia/webhook
echo     Naya         -^> https://naya-line.quiddityinnovations.com/webhook/line
echo     Tasuke       -^> https://oc-line.quiddityinnovations.com/line/webhook
echo     Kaze         -^> https://oc-line.quiddityinnovations.com/line/webhook
echo     Claude Voice -^> https://claudevoice.quiddityinnovations.com/line/webhook
echo.
echo   Meta  (developers.facebook.com):
echo     Maia FB      -^> https://maia.quiddityinnovations.com/maia/fb-webhook
echo     Maia WhatsApp-^> https://maia.quiddityinnovations.com/maia/wa-webhook
echo     Maia Quiddam -^> https://api.quiddam.com
echo.
echo   If STEP 1 showed any 502 for a hostname, that app is not listening on
echo   its port yet - start the app and re-run verify_named_tunnels.py.
echo ######################################################################
echo.
pause
endlocal

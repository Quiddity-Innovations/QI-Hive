@echo off
REM ============================================================================
REM  2_REGISTER_WEBHOOKS.bat
REM  Re-points the bot webhooks at the new permanent quiddityinnovations.com /
REM  quiddam.com URLs.
REM
REM  AUTOMATED here (no admin needed):
REM    - Maia : webhook_updater.py  -> registers LINE + Telegram to maia.quiddityinnovations.com
REM    - Naya : setup_telegram_webhook.py -> registers Telegram to naya-line.quiddityinnovations.com
REM
REM  MANUAL (platform consoles - only you can do these) are printed at the end.
REM  Run AFTER 1_PROVISION_TUNNELS.bat and after the bot apps/tunnels are up.
REM ============================================================================

setlocal
set PY=C:\1-AI\APPS\PYTHON\python.exe
if not exist "%PY%" set PY=python

echo.
echo ======================================================================
echo   QI WEBHOOK RE-REGISTRATION
echo ======================================================================
echo.

echo --- Maia: LINE + Telegram (webhook_updater.py) ---
if exist "C:\QI\webhook_updater.py" (
  "%PY%" "C:\QI\webhook_updater.py"
) else (
  echo   [skip] C:\QI\webhook_updater.py not found
)
echo.

echo --- Naya: Telegram (setup_telegram_webhook.py) ---
if exist "C:\NAYA\tools\setup_telegram_webhook.py" (
  "%PY%" "C:\NAYA\tools\setup_telegram_webhook.py"
) else (
  echo   [skip] C:\NAYA\tools\setup_telegram_webhook.py not found
)
echo.

echo ======================================================================
echo   MANUAL STEPS - update these in the platform consoles (cannot script):
echo ----------------------------------------------------------------------
echo   LINE Developers Console  (developers.line.biz):
echo     Maia channel        webhook -^> https://maia.quiddityinnovations.com/maia/webhook
echo     Naya channel        webhook -^> https://naya-line.quiddityinnovations.com/webhook/line
echo     Tasuke channel      webhook -^> https://oc-line.quiddityinnovations.com/line/webhook
echo     Kaze channel        webhook -^> https://oc-line.quiddityinnovations.com/line/webhook
echo     Claude Voice channel webhook -^> https://claudevoice.quiddityinnovations.com/line/webhook
echo.
echo   Meta for Developers  (developers.facebook.com):
echo     Maia Messenger/FB   callback -^> https://maia.quiddityinnovations.com/maia/fb-webhook
echo     Maia WhatsApp       callback -^> https://maia.quiddityinnovations.com/maia/wa-webhook
echo     Maia Quiddam (MQ)   callback -^> https://api.quiddam.com  (FB/IG/WhatsApp)
echo.
echo   (Naya + Claude Voice also auto-register their LINE webhook on service
echo    boot, but verify in the console to be safe. Naya: run 3_RESTART_NAYA.bat)
echo ======================================================================
echo.
pause
endlocal

@echo off
REM ============================================================
REM  QI demo fixes — RIGHT-CLICK -> "Run as administrator"
REM  1) Restart Hive Dashboard so the new /brain proxy loads
REM  2) Install CypherMiner API as a permanent service (:8502)
REM  3) Restart AutoPDF service (:6969)
REM ============================================================
set NSSM=C:\QIH\engine\bin\nssm.exe
set PY=C:\Program Files\Python311\python.exe

echo [1/3] Restarting QI_Dashboard ...
"%NSSM%" restart QI_Dashboard

echo.
echo [2/3] Installing/refreshing QI_CypherMinerAPI ...
"%NSSM%" install QI_CypherMinerAPI "%PY%" "run_api.py"  2>nul
"%NSSM%" set QI_CypherMinerAPI AppDirectory C:\APPS\CypherMiner
"%NSSM%" set QI_CypherMinerAPI AppStdout C:\APPS\CypherMiner\LOGS\api_out.log
"%NSSM%" set QI_CypherMinerAPI AppStderr C:\APPS\CypherMiner\LOGS\api_err.log
"%NSSM%" set QI_CypherMinerAPI Start SERVICE_AUTO_START
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8502" ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
"%NSSM%" start QI_CypherMinerAPI  2>nul
"%NSSM%" restart QI_CypherMinerAPI 2>nul

echo.
echo [3/3] Restarting AutoPDF ...
net start QI_AutoPDF 2>nul

echo.
echo ===== Verifying =====
timeout /t 8 >nul
powershell -NoProfile -Command "foreach($u in 'http://localhost:8600/brain/api/poll/status','http://localhost:8502/health'){try{$r=Invoke-WebRequest $u -UseBasicParsing -TimeoutSec 6; Write-Host ('OK  '+$r.StatusCode+'  '+$u)}catch{Write-Host ('ERR '+$u)}}"
echo.
echo Done. Open http://localhost:8600 (or the tunnel) and check the Brain Poller card.
pause

@echo off
REM ============================================================================
REM  1_PROVISION_TUNNELS.bat
REM  Provisions every QI static NAMED Cloudflare tunnel on quiddityinnovations.com
REM  (and quiddam.com) from C:\QIH\engine\tunnels\tunnels.json, then verifies.
REM
REM  What it does:
REM    - creates each named tunnel (idempotent - skips existing)
REM    - routes DNS for every hostname
REM    - writes the per-tunnel cloudflared config
REM    - reconfigures each QI_*Tunnel NSSM service to run its named tunnel
REM    - runs verify_named_tunnels.py at the end
REM
REM  Requires Administrator (NSSM service edits). This file self-elevates.
REM  You are already authenticated (cert.pem present), so no browser login needed.
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
set PY=C:\1-AI\APPS\PYTHON\python.exe
if not exist "%PY%" set PY=python
set CERT=%USERPROFILE%\.cloudflared\cert.pem

echo.
echo ======================================================================
echo   QI NAMED-TUNNEL PROVISIONING
echo ======================================================================
echo   Toolchain : %TUN%
echo   Python    : %PY%
echo   Cert      : %CERT%
echo.

if not exist "%CERT%" (
  echo [!] cloudflared cert.pem NOT found for this user.
  echo     Open a NORMAL (non-admin) terminal and run:  cloudflared tunnel login
  echo     Pick quiddityinnovations.com, then re-run this file.
  echo.
  pause
  exit /b 1
)

cd /d "%TUN%"

echo --- Step 1/2: migrate_named_tunnels.py (provision) ---
"%PY%" migrate_named_tunnels.py
echo.
echo --- Step 2/2: verify_named_tunnels.py (health check) ---
"%PY%" verify_named_tunnels.py
echo.
echo ======================================================================
echo   DONE. Review the SUMMARY above. Any 502 = the app on that port
echo   is not running yet (start the app, then re-check that hostname).
echo ======================================================================
echo.
pause
endlocal

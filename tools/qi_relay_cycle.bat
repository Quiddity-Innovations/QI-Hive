@echo off
REM QI Relay - one full cycle. Invoked by scheduled task QI_RelaySync at :00 and :30.
REM Step 1 is pure transport (safe, no AI). Step 2 is the L2 drafting step and is
REM allowed to fail without failing the cycle - transport must never depend on a model.
setlocal
set PY=C:\Program Files\Python311\python.exe
if not exist "%PY%" set PY=python

"%PY%" "C:\QIH\tools\qi_relay_sync.py"
if errorlevel 1 (
  echo [QI_RelaySync] transport step failed - skipping drafting step
  exit /b 1
)

"%PY%" "C:\QIH\tools\qi_relay_draft.py" --budget 0.40
exit /b 0

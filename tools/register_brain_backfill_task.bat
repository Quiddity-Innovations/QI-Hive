@echo off
REM Register QI_BrainBackfill scheduled task — runs brain_backfill_tick.py
REM every 30 minutes under the current user. No admin required.
schtasks /Create /TN "QI_BrainBackfill" /TR "\"C:\1-AI\APPS\PYTHON\python.exe\" \"C:\QIH\tools\brain_backfill_tick.py\"" /SC MINUTE /MO 30 /RL LIMITED /F
echo.
echo Status:
schtasks /Query /TN "QI_BrainBackfill" /FO LIST 2>nul | findstr /R "TaskName Status Next"

@echo off
REM QI_TrinityCheck_Daily — inspection-only Trinity health check (no assistant calls).
REM Marker for QI_TaskHealth: 'overall=PASS' in C:\QIH\LOGS\trinity_daily\trinity_check_YYYYMMDD.log (written by the script itself).
cd /d C:\QIH
"C:\Program Files\Python311\python.exe" C:\QIH\engine\tools\qi_trinity_check.py >> C:\QIH\LOGS\trinity_check_daily.out 2>&1

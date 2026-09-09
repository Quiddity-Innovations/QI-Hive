@echo off
REM QI_BrainDriftCheck_Daily — flags projects whose git history has outrun their QI Brain
REM project_state row by more than 14 days (see qi_brain_drift_check.py header).
REM Marker for QI_TaskHealth: 'overall=PASS' in C:\QIH\LOGS\brain_drift\brain_drift_YYYYMMDD.log
REM (written by the script itself — a NEW file every day, never a rolling log).
cd /d C:\QIH
"C:\Program Files\Python311\python.exe" C:\QIH\engine\hive\tools\qi_brain_drift_check.py >> C:\QIH\LOGS\brain_drift_check_daily.out 2>&1

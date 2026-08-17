@echo off
REM QI Effort Ledger - daily incremental collection + sealed ledger entry.
REM Registered as scheduled task QI_EffortLedger_Daily (see README).
cd /d "C:\QIH\engine\effort"
python qi_effort_ledger.py --daily >> "C:\QIH\logs\effort_ledger_task.log" 2>&1
exit /b %ERRORLEVEL%

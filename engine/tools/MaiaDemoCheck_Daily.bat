@echo off
REM QI_MaiaDemoCheck_Daily — Maia demo readiness (services + local ports + public tunnel + db).
REM Replaces the old MaiaNightlySync `check: git` health entry, which measured commit
REM recency and therefore went permanently STALE once Maia development paused.
REM
REM Marker for QI_TaskHealth: 'demo=READY' in
REM   C:\QIH\LOGS\maia_demo\maia_demo_check_YYYYMMDD.log   (written by the script itself)
REM The script withholds that marker on any failure, which is what fires the alert.
REM Do NOT trust this task's exit code — conhost --headless always returns 0.
cd /d C:\QIH
"C:\Program Files\Python311\python.exe" C:\QIH\engine\tools\qi_maia_demo_check.py >> C:\QIH\LOGS\maia_demo_check.out 2>&1

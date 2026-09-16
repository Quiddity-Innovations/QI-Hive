@echo off
rem install_backup_task.bat - (re)register the QI_NightlyBackup scheduled task
rem v2 2026-09-16: paths moved off the deleted C:\UNIVERSAL tree.
rem Run from an elevated prompt. Pure ASCII, CRLF.

set TASK_NAME=QI_NightlyBackup
set PYTHON="C:\Program Files\Python311\python.exe"
set SCRIPT=C:\QIH\engine\brain\tools\backup.py
set LOGDIR=C:\QIH\LOGS\nightly_backup

if not exist %LOGDIR% mkdir %LOGDIR%

schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

schtasks /create ^
  /tn "%TASK_NAME%" ^
  /tr "%PYTHON% \"%SCRIPT%\"" ^
  /sc DAILY ^
  /st 01:00 ^
  /ru SYSTEM ^
  /rl HIGHEST ^
  /f

if errorlevel 1 (
  echo FAILED to create %TASK_NAME%
  exit /b 1
)

schtasks /query /tn "%TASK_NAME%" /fo LIST

echo.
echo %TASK_NAME% registered: daily 01:00, %SCRIPT%
echo Backups: C:\QIH\shared\backups\db\YYYY-MM-DD\
echo Log:     %LOGDIR%\backup_YYYYMMDD.log  (success marker "backup OK")
exit /b 0

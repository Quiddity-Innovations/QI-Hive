@echo off
:: install_backup_task.bat — Register QI Nightly Backup in Windows Task Scheduler
:: Run as Administrator

net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -command "Start-Process -FilePath '%~f0' -Verb RunAs -WindowStyle Normal"
    exit /b
)

call C:\UNIVERSAL\qi_python.bat
set PYTHON=%QI_PYTHON%
set SCRIPT=C:\UNIVERSAL\qi_brain\tools\backup.py
set TASK_NAME=QI_NightlyBackup
set LOG=C:\UNIVERSAL\BACKUPS\task_install.log

echo.
echo === Installing QI Nightly Backup Task ===
echo.

:: Remove existing task if present
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

:: Create new task — runs at 1:00 AM daily as SYSTEM
schtasks /create ^
  /tn "%TASK_NAME%" ^
  /tr "\"%PYTHON%\" \"%SCRIPT%\"" ^
  /sc DAILY ^
  /st 01:00 ^
  /ru SYSTEM ^
  /rl HIGHEST ^
  /f

if %errorlevel% neq 0 (
    echo ERROR: Failed to create scheduled task.
    pause
    exit /b 1
)

echo.
echo [OK] Task "%TASK_NAME%" created — runs daily at 1:00 AM as SYSTEM
echo.

:: Verify it registered correctly
echo === Task details ===
schtasks /query /tn "%TASK_NAME%" /fo LIST

echo.
echo === Running a test backup now ===
"%PYTHON%" "%SCRIPT%"
echo.

echo === Done ===
echo Backups will be saved to: C:\UNIVERSAL\BACKUPS\YYYY-MM-DD\
echo Log file: C:\UNIVERSAL\BACKUPS\backup.log
echo Retention: 30 days
pause

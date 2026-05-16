@echo off
:: QI Avatar Pipeline — Windows entry point
:: Usage:  run_avatar.bat <agent> "script text"
:: Usage:  run_avatar.bat <agent> @C:\path\to\script.txt
:: Usage:  run_avatar.bat <agent> "text" --no-tts
::
:: Agents: tasuke  maia  naya  kaze

if "%~1"=="" (
    echo.
    echo  Usage: run_avatar.bat ^<agent^> "script text"
    echo         run_avatar.bat ^<agent^> @script.txt
    echo.
    echo  Agents: tasuke  maia  naya  kaze
    exit /b 1
)

echo.
echo  QI Avatar Pipeline
echo  Agent : %1
echo  Script: %2
echo.

"%~dp0.venv\Scripts\python.exe" "%~dp0avatar_pipeline.py" %*

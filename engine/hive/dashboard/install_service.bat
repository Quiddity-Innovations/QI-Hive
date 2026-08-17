@echo off
:: Run this as Administrator to install ClaudeManager as a Windows service
echo Installing ClaudeManager service...

C:\APPS\QI\nssm.exe install ClaudeManager "C:\Program Files\Python311\python.exe" "C:\Claude\Dashboard\server.py"
C:\APPS\QI\nssm.exe set ClaudeManager AppDirectory "C:\Claude\Dashboard"
C:\APPS\QI\nssm.exe set ClaudeManager Description "Claude Manager Dashboard - port 8600"
C:\APPS\QI\nssm.exe set ClaudeManager Start SERVICE_AUTO_START
C:\APPS\QI\nssm.exe set ClaudeManager AppStdout "C:\Claude\Dashboard\logs\stdout.log"
C:\APPS\QI\nssm.exe set ClaudeManager AppStderr "C:\Claude\Dashboard\logs\stderr.log"

mkdir "C:\Claude\Dashboard\logs" 2>nul

sc start ClaudeManager
echo.
echo Done. Dashboard at http://localhost:8600
pause

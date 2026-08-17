@echo off
REM ONE-CLICK installer for all missing QI app services + tunnels. Approve the single UAC prompt.
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo Requesting Administrator access...
  powershell -Command "Start-Process '%~f0' -Verb RunAs"
  exit /b
)
echo. & echo === QI_FidelityAnalyzer === & call "C:\FidelityAnalyzer\install_service.bat"
echo. & echo === QI_AvatarStudio === & call "C:\1-AI\APPS\AvatarStudio\install_service.bat"
echo. & echo === QI_PersonalSong === & call "C:\APPS\PersonalSong\install_service.bat"
echo. & echo === QI_M2V === & call "C:\APPS\M2V\install_service.bat"
echo. & echo === QI_M2VTunnel === & call "C:\APPS\M2V\install_tunnel.bat"
echo. & echo === TubeScout (service + tunnel, existing script) === & call "C:\APPS\TUBESCOUT\install_service_admin.bat"
"C:\QIH\engine\bin\nssm.exe" set QI_TubeScout Start SERVICE_DEMAND_START
echo. & echo === ALL DONE === & pause

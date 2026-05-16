@echo off
:: QI Avatar Studio — Gradio UI launcher
:: Opens at http://localhost:7862

echo.
echo  ==========================================
echo   QI Avatar Studio
echo   http://localhost:7862
echo  ==========================================
echo.

:: Open browser after 3 seconds in background
start /b cmd /c "timeout /t 3 >nul && start http://localhost:7862"

:: Launch Gradio app
"%~dp0.venv\Scripts\python.exe" "%~dp0avatar_studio.py"

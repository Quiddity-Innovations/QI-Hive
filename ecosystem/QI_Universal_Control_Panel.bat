@echo off
REM ============================================================
REM  QI Universal Control Panel
REM  Auto-elevates, then relaunches itself in Windows Terminal.
REM  Each menu choice opens the chosen control panel as a NEW
REM  TAB in this same wt window. Children inherit admin so they
REM  run inline in the tab instead of popping a new window.
REM ============================================================

REM If not already inside Windows Terminal, relaunch ourselves via wt
REM using the Command Prompt profile (which has elevate:true set in
REM settings.json). wt will trigger ONE UAC prompt and create an
REM elevated wt window. All tabs in that window inherit admin, so
REM child control bats skip their own elevation and run inline.
if not defined WT_SESSION (
    where wt.exe >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Windows Terminal ^(wt.exe^) not found. Install from Microsoft Store.
        pause
        exit /b 1
    )
    wt.exe new-tab -p "Command Prompt" --title "QI Control" -d "C:\UNIVERSAL\ECOSYSTEM" "%~f0"
    exit /b 0
)

title QI Universal Control Panel

:menu
cls
echo.
echo  =====================================================
echo            QI UNIVERSAL CONTROL PANEL
echo  =====================================================
echo.
echo.
echo   [1] Maia     ^(C:\QI^)
echo   [2] Naya     ^(C:\NAYA^)
echo   [3] NEXUS    ^(C:\NEXUS^)
echo   [4] OC       ^(C:\OC^)
echo   [5] ALL      ^(open all four^)
echo.
echo   [6] WEB PANEL ^(one browser tab for everything - recommended^)
echo.
echo   [Q] Quit
echo.
echo  -----------------------------------------------------
set "choice="
set /p "choice=Select an application: "

if /i "%choice%"=="1" goto maia
if /i "%choice%"=="2" goto naya
if /i "%choice%"=="3" goto nexus
if /i "%choice%"=="4" goto oc
if /i "%choice%"=="5" goto all
if /i "%choice%"=="6" goto webpanel
if /i "%choice%"=="q" exit /b 0
goto menu

:maia
wt.exe -w 0 new-tab -p "Command Prompt" --title "Maia"  -d "C:\QI"    "C:\QI\maia_control.bat"
goto menu

:naya
wt.exe -w 0 new-tab -p "Command Prompt" --title "Naya"  -d "C:\NAYA"  "C:\NAYA\naya_control.bat"
goto menu

:nexus
wt.exe -w 0 new-tab -p "Command Prompt" --title "NEXUS" -d "C:\NEXUS" "C:\NEXUS\nexus_control.bat"
goto menu

:oc
wt.exe -w 0 new-tab -p "Command Prompt" --title "OC"    -d "C:\OC"    "C:\OC\OC_Control_Panel_v6.bat"
goto menu

:all
wt.exe -w 0 new-tab -p "Command Prompt" --title "Maia"  -d "C:\QI"    "C:\QI\maia_control.bat"
wt.exe -w 0 new-tab -p "Command Prompt" --title "Naya"  -d "C:\NAYA"  "C:\NAYA\naya_control.bat"
wt.exe -w 0 new-tab -p "Command Prompt" --title "NEXUS" -d "C:\NEXUS" "C:\NEXUS\nexus_control.bat"
wt.exe -w 0 new-tab -p "Command Prompt" --title "OC"    -d "C:\OC"    "C:\OC\OC_Control_Panel_v6.bat"
goto menu

:webpanel
REM Launch the web control panel in a background tab - page auto-opens in browser.
wt.exe -w 0 new-tab -p "Command Prompt" --title "QI Web Panel" -d "C:\UNIVERSAL\ECOSYSTEM" "C:\UNIVERSAL\ECOSYSTEM\start_qi_web_panel.bat"
goto menu

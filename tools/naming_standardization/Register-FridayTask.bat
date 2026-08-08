@echo off
REM ==========================================================================
REM  One-click registration of the Friday naming-standardization task.
REM  Double-click this and approve the single UAC prompt. It registers a
REM  one-time SYSTEM task (QI_NamingStandardize_Friday) for 2026-06-27 00:05 (Sat)
REM  that re-points all QI_ services to per-product NSSM copies and renames
REM  the Tier-1 control batch files. After registration, NOTHING else needs
REM  your approval -- the Friday run executes silently as SYSTEM (no UAC).
REM ==========================================================================
echo Requesting administrator rights to register QI_NamingStandardize_Friday ...
echo (An elevated window will open and STAY open so you can read the result.)
powershell -NoProfile -Command "Start-Process powershell -Verb RunAs -ArgumentList '-NoExit','-NoProfile','-ExecutionPolicy','Bypass','-File','C:\QIH\tools\naming_standardization\register_task.ps1'"
echo.
echo Read the elevated window. Result is also logged to:
echo   C:\QIH\tools\naming_standardization\logs\register_result.txt
echo.
echo Verify with:  schtasks /query /tn QI_NamingStandardize_Friday
pause

@echo off
rem ===============================================================
rem  RESTORE God's Eye View to the pre-flight-search restore point
rem  Restore point tag: qi-restore-2026-09-14
rem  Pure ASCII + CRLF per QI batch rules. No timeout /t.
rem ===============================================================
setlocal
set REPO=C:\APPS\Godseye
set TAG=qi-restore-2026-09-14

echo.
echo  God's Eye View - RESTORE
echo  Repo: %REPO%
echo  Tag : %TAG%
echo.
echo  Current state:
git -C "%REPO%" --no-pager log --oneline -1
echo.
echo  Uncommitted changes that WILL BE LOST:
git -C "%REPO%" status --short
echo.
echo  This rewinds the working tree to %TAG%.
set /p ANSWER=Type RESTORE to proceed (anything else cancels): 
if /i not "%ANSWER%"=="RESTORE" goto :cancelled

git -C "%REPO%" reset --hard %TAG%
if errorlevel 1 goto :failed
echo.
echo  Restored. Current state:
git -C "%REPO%" --no-pager log --oneline -1
echo.
echo  Restart the dev server to pick it up:  npm run dev
goto :done

:cancelled
echo.
echo  Cancelled. Nothing changed.
goto :done

:failed
echo.
echo  RESTORE FAILED. Nothing was changed by this script.
echo  Fall back to the zip snapshot in this folder.
goto :done

:done
echo.
pause
endlocal

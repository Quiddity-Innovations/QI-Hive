@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM  Free Webhook-Bot Cloud Kit — scoped IAM role-management grant
REM
REM  Grants the CLI IAM user permission to manage only <BOT_NAME>-*
REM  roles, using TEMPORARY admin credentials obtained via
REM  'aws login' (browser sign-in, auto-expiring). Nothing is
REM  stored permanently.
REM
REM  Run this as a normal user. A browser window will open:
REM  sign in as the ACCOUNT ROOT USER (the email the AWS account
REM  was created with).
REM
REM  Reads AWS_ACCOUNT_ID, BOT_NAME, CLI_USER_NAME from config.env
REM  in this folder (copy config.env.example -> config.env first).
REM  If any value is missing, you'll be prompted for it.
REM ============================================================

set AWSEXE=aws
set HEREDIR=%~dp0
set CONFIGFILE=%HEREDIR%config.env
set TEMPLATE=%HEREDIR%role_policy.json.template
set POLICYFILE=%HEREDIR%role_policy.generated.json
set PROFILE=cli-admin-temp

if not exist "%TEMPLATE%" (
    echo [ERROR] Template not found: %TEMPLATE%
    pause & exit /b 1
)

REM --- load config.env (KEY=VALUE lines, ignore # comments) ---
if exist "%CONFIGFILE%" (
    for /f "usebackq tokens=1,* delims== eol=#" %%A in ("%CONFIGFILE%") do (
        set "%%A=%%B"
    )
)

if not defined AWS_ACCOUNT_ID set /p AWS_ACCOUNT_ID="AWS account ID: "
if not defined BOT_NAME set /p BOT_NAME="Bot name (resource prefix): "
if not defined CLI_USER_NAME set /p CLI_USER_NAME="IAM CLI user name: "

if "%AWS_ACCOUNT_ID:~0,1%"=="<" (
    set /p AWS_ACCOUNT_ID="AWS account ID (config.env still has a placeholder): "
)

echo.
echo Generating scoped policy for role prefix "%BOT_NAME%-*" on account %AWS_ACCOUNT_ID%...

REM --- substitute placeholders in the template ---
set "LINE="
> "%POLICYFILE%" (
    for /f "usebackq delims=" %%L in ("%TEMPLATE%") do (
        set "LINE=%%L"
        set "LINE=!LINE:<ACCOUNT_ID>=%AWS_ACCOUNT_ID%!"
        set "LINE=!LINE:<BOT_NAME>=%BOT_NAME%!"
        echo(!LINE!
    )
)

echo.
REM Pre-set the region so 'aws login' doesn't prompt for it
"%AWSEXE%" configure set region %AWS_REGION% --profile %PROFILE% >nul 2>&1

echo [1/3] Opening browser for temporary admin sign-in...
echo       Sign in as the ROOT user when prompted.
echo.
"%AWSEXE%" login --profile %PROFILE%
if errorlevel 1 (
    echo.
    echo [ERROR] aws login failed. Fallback: add the inline policy
    echo         manually in the IAM console — see GUIDE.md step 1.7.
    pause & exit /b 1
)

echo.
echo [2/3] Attaching inline policy to user %CLI_USER_NAME%...
"%AWSEXE%" iam put-user-policy ^
    --user-name %CLI_USER_NAME% ^
    --policy-name RoleManagement-Scoped ^
    --policy-document file://%POLICYFILE% ^
    --profile %PROFILE%
if errorlevel 1 (
    echo.
    echo [ERROR] Policy attach failed. Most common cause: you signed in
    echo         as a user without IAM rights. Re-run and sign in as ROOT,
    echo         or add the policy manually in the console (GUIDE.md 1.7).
    pause & exit /b 1
)

echo.
echo [3/3] Verifying...
"%AWSEXE%" iam get-user-policy --user-name %CLI_USER_NAME% --policy-name RoleManagement-Scoped --profile %PROFILE% --output table
if errorlevel 1 (
    echo [WARN] Verification call failed - check the console manually.
) else (
    echo.
    echo [SUCCESS] %CLI_USER_NAME% can now manage %BOT_NAME%-* roles.
    echo The temporary admin credentials expire on their own.
)
echo.
pause

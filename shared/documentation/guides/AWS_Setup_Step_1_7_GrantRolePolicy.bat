@echo off
setlocal
REM ============================================================
REM  AWS Setup Guide - Step 1.7
REM  Grants qi-claude-cli the scoped role-management policy
REM  (QI-RoleManagement-Scoped) using TEMPORARY admin credentials
REM  obtained via 'aws login' (browser sign-in, auto-expiring).
REM
REM  Run this as a normal user. A browser window will open:
REM  sign in as the ACCOUNT ROOT USER (the email you created
REM  the AWS account with). Nothing is stored permanently.
REM ============================================================

set AWSEXE=C:\Program Files\Amazon\AWSCLIV2\aws.exe
set POLICYFILE=%~dp0qi_role_policy.json
set PROFILE=qi-admin-temp

if not exist "%POLICYFILE%" (
    echo [ERROR] Policy file not found: %POLICYFILE%
    pause & exit /b 1
)

echo.
REM Pre-set the region so 'aws login' doesn't prompt for it
"%AWSEXE%" configure set region us-east-1 --profile %PROFILE% >nul 2>&1

echo [1/3] Opening browser for temporary admin sign-in...
echo       Sign in as the ROOT user when prompted.
echo.
"%AWSEXE%" login --profile %PROFILE%
if errorlevel 1 (
    echo.
    echo [ERROR] aws login failed. Fallback: add the inline policy
    echo         manually in the console - see guide step 1.7.
    pause & exit /b 1
)

echo.
echo [2/3] Attaching inline policy QI-RoleManagement-Scoped to user qi-claude-cli...
"%AWSEXE%" iam put-user-policy ^
    --user-name qi-claude-cli ^
    --policy-name QI-RoleManagement-Scoped ^
    --policy-document file://%POLICYFILE% ^
    --profile %PROFILE%
if errorlevel 1 (
    echo.
    echo [ERROR] Policy attach failed. Most common cause: you signed in
    echo         as a user without IAM rights. Re-run and sign in as ROOT,
    echo         or add the policy manually in the console (guide 1.7).
    pause & exit /b 1
)

echo.
echo [3/3] Verifying...
"%AWSEXE%" iam get-user-policy --user-name qi-claude-cli --policy-name QI-RoleManagement-Scoped --profile %PROFILE% --output table
if errorlevel 1 (
    echo [WARN] Verification call failed - check the console manually.
) else (
    echo.
    echo [SUCCESS] qi-claude-cli can now manage qi-* roles.
    echo The temporary admin credentials expire on their own.
)
echo.
pause

@echo off
setlocal
REM ============================================================
REM  Security hardening (deferred from guide step 1.3):
REM  Replaces qi-claude-cli's broad PowerUserAccess with a policy
REM  scoped to the services the QI Free Cloud program actually
REM  uses (Lambda/SQS/SSM/DynamoDB/logs/CloudWatch/events/SNS/
REM  S3/budgets + read-own-IAM). The QI-RoleManagement-Scoped
REM  inline policy (qi-* roles) stays untouched.
REM  Uses temporary admin credentials via 'aws login' (browser,
REM  sign in as ROOT). Nothing permanent stored.
REM  ROLLBACK: re-attach PowerUserAccess in IAM console.
REM ============================================================
set AWSEXE=C:\Program Files\Amazon\AWSCLIV2\aws.exe
set POLICYFILE=%~dp0qi_cli_scoped_policy.json
set PROFILE=qi-admin-temp

"%AWSEXE%" configure set region us-east-1 --profile %PROFILE% >nul 2>&1
echo [1/3] Browser sign-in as ROOT...
"%AWSEXE%" login --profile %PROFILE%
if errorlevel 1 ( echo [ERROR] aws login failed. & pause & exit /b 1 )

echo [2/3] Attaching scoped inline policy + detaching PowerUserAccess...
"%AWSEXE%" iam put-user-policy --user-name qi-claude-cli --policy-name QI-Program-Scoped --policy-document file://%POLICYFILE% --profile %PROFILE%
if errorlevel 1 ( echo [ERROR] policy attach failed - NOT detaching PowerUser. & pause & exit /b 1 )
"%AWSEXE%" iam detach-user-policy --user-name qi-claude-cli --policy-arn arn:aws:iam::aws:policy/PowerUserAccess --profile %PROFILE%

echo [3/3] Verifying...
"%AWSEXE%" iam list-attached-user-policies --user-name qi-claude-cli --profile %PROFILE% --output table
"%AWSEXE%" iam list-user-policies --user-name qi-claude-cli --profile %PROFILE% --output table
echo [DONE] qi-claude-cli now runs least-privilege for the program scope.
pause

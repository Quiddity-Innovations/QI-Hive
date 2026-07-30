@echo off
setlocal
REM ============================================================
REM  AWS Setup Guide - Part 2 (one-shot)
REM  Creates/updates the entire cloud side of the webhook relay:
REM    - SQS FIFO queue        qi-maia-events.fifo
REM    - checks SSM secret     /qi/maia/line_channel_secret
REM    - IAM execution role    qi-maia-webhook-role
REM    - Lambda function       qi-maia-webhook + public Function URL
REM
REM  Prerequisites: guide steps 1.1-1.7 complete
REM  (aws configure done + QI-RoleManagement-Scoped policy attached).
REM  Idempotent - safe to re-run anytime; re-running updates the
REM  Lambda code from lambda_function.py.
REM
REM  If the secret is not yet in SSM, store it first (step 2.2):
REM    aws ssm put-parameter --name /qi/maia/line_channel_secret ^
REM        --type SecureString --value <SECRET> --overwrite
REM ============================================================

set DEPLOY=C:\QI\TOOLS\aws_relay\deploy_lambda.py

if not exist "%DEPLOY%" (
    echo [ERROR] Deploy script not found: %DEPLOY%
    pause & exit /b 1
)

echo Running Part 2 deployment...
echo.
python "%DEPLOY%"
if errorlevel 1 (
    echo.
    echo [ERROR] Deployment failed - see message above.
    echo         Each step is documented in the guide, Part 2,
    echo         so it can also be done manually via CLI/console.
) else (
    echo.
    echo [SUCCESS] Cloud side deployed. The WEBHOOK URL printed above
    echo           is what goes into the LINE Developers console
    echo           (only after Part 3 shadow-testing - see guide).
)
echo.
pause

# -*- coding: utf-8 -*-
"""Free Webhook-Bot Cloud Kit — deploy.py

Idempotent deploy: SQS FIFO queue -> IAM execution role -> Lambda ->
public Function URL. Safe to re-run; updates the Lambda code in place
if the function already exists.

All names/IDs come from config.env (copy config.env.example ->
config.env and fill it in first). No values are hardcoded here.

Prereqs:
  - AWS CLI v2 installed and on PATH (or set AWS_CLI_PATH below)
  - `aws configure` already run with an IAM user that has
    PowerUserAccess plus the scoped role-management policy from
    grant_role_policy.bat (see GUIDE.md Part 1)
  - The webhook secret already stored in SSM (GUIDE.md Part 2.2)
"""
import json
import subprocess
import sys
import time
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).parent
CONFIG_FILE = HERE / "config.env"

# Override if the AWS CLI isn't on PATH under this name.
AWS_CLI_PATH = "aws"


def load_config(path: Path) -> dict:
    if not path.exists():
        print(f"MISSING: {path}\n"
              f"Copy config.env.example to config.env and fill in your "
              f"values first.")
        sys.exit(1)
    cfg = {}
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            cfg[key.strip()] = value.strip()
    return cfg


CFG = load_config(CONFIG_FILE)


def require(key: str) -> str:
    val = CFG.get(key, "")
    if not val or val.startswith("<"):
        print(f"MISSING or placeholder value in config.env: {key}")
        sys.exit(1)
    return val


ACCOUNT = require("AWS_ACCOUNT_ID")
REGION = require("AWS_REGION")
QUEUE_NAME = require("QUEUE_NAME")
LAMBDA_NAME = require("LAMBDA_NAME")
ROLE_NAME = require("ROLE_NAME")
SECRET_PARAM = require("SECRET_PARAM_PATH")
RUNTIME = CFG.get("LAMBDA_RUNTIME", "python3.12")
TIMEOUT = CFG.get("LAMBDA_TIMEOUT_SECONDS", "10")
MEMORY = CFG.get("LAMBDA_MEMORY_MB", "128")
RETENTION = CFG.get("QUEUE_RETENTION_SECONDS", "345600")
SIG_HEADER = CFG.get("SIGNATURE_HEADER_NAME", "X-Line-Signature")

QUEUE_ARN = f"arn:aws:sqs:{REGION}:{ACCOUNT}:{QUEUE_NAME}"
QUEUE_URL = f"https://sqs.{REGION}.amazonaws.com/{ACCOUNT}/{QUEUE_NAME}"

TRUST = {"Version": "2012-10-17", "Statement": [{
    "Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"}]}

POLICY = {"Version": "2012-10-17", "Statement": [
    {"Sid": "Enqueue", "Effect": "Allow", "Action": "sqs:SendMessage",
     "Resource": QUEUE_ARN},
    {"Sid": "ReadSecret", "Effect": "Allow",
     "Action": ["ssm:GetParameter"],
     "Resource": f"arn:aws:ssm:{REGION}:{ACCOUNT}:parameter{SECRET_PARAM}"},
    {"Sid": "Logs", "Effect": "Allow",
     "Action": ["logs:CreateLogGroup", "logs:CreateLogStream",
                "logs:PutLogEvents"],
     "Resource": f"arn:aws:logs:{REGION}:{ACCOUNT}:*"},
]}


def aws(*args, ok_codes=(0,), quiet=False):
    r = subprocess.run([AWS_CLI_PATH, *args], capture_output=True, text=True)
    if r.returncode not in ok_codes:
        print("FAILED:", " ".join(args[:4]), "\n", r.stderr[-600:])
        sys.exit(1)
    if not quiet and r.stdout.strip():
        return r.stdout
    return r.stdout


def main():
    # 0. Queue + secret (idempotent; queue create returns the same URL
    #    if it already exists).
    aws("sqs", "create-queue", "--queue-name", QUEUE_NAME,
        "--attributes",
        json.dumps({"FifoQueue": "true",
                    "ContentBasedDeduplication": "true",
                    "MessageRetentionPeriod": RETENTION}),
        quiet=True)
    print(f"queue ready: {QUEUE_URL}")

    r = subprocess.run(
        [AWS_CLI_PATH, "ssm", "get-parameter", "--name", SECRET_PARAM],
        capture_output=True, text=True)
    if r.returncode != 0:
        print(f"MISSING: SSM parameter {SECRET_PARAM} — store the webhook "
              f"platform's signing secret first (GUIDE.md step 2.2), then "
              f"re-run.")
        sys.exit(1)
    print(f"secret present: {SECRET_PARAM}")

    # 1. Role (create if missing)
    r = subprocess.run(
        [AWS_CLI_PATH, "iam", "get-role", "--role-name", ROLE_NAME],
        capture_output=True, text=True)
    if r.returncode != 0:
        aws("iam", "create-role", "--role-name", ROLE_NAME,
            "--assume-role-policy-document", json.dumps(TRUST),
            "--description", f"Execution role for {LAMBDA_NAME} Lambda",
            quiet=True)
        print(f"role created: {ROLE_NAME}")
        time.sleep(10)  # IAM propagation before Lambda can assume it
    aws("iam", "put-role-policy", "--role-name", ROLE_NAME,
        "--policy-name", f"{ROLE_NAME}-permissions",
        "--policy-document", json.dumps(POLICY), quiet=True)
    print("role policy attached (SQS send + SSM read + logs only)")

    # 2. Zip the code
    zip_path = HERE / "lambda.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(HERE / "lambda_function.py", "lambda_function.py")

    # 3. Create or update the function
    role_arn = f"arn:aws:iam::{ACCOUNT}:role/{ROLE_NAME}"
    exists = subprocess.run(
        [AWS_CLI_PATH, "lambda", "get-function", "--function-name",
         LAMBDA_NAME], capture_output=True, text=True).returncode == 0
    if exists:
        aws("lambda", "update-function-code", "--function-name",
            LAMBDA_NAME, "--zip-file", f"fileb://{zip_path}", quiet=True)
        print(f"function code updated: {LAMBDA_NAME}")
    else:
        env_vars = (f"Variables={{QUEUE_URL={QUEUE_URL},"
                    f"SECRET_PARAM={SECRET_PARAM},SIG_HEADER={SIG_HEADER}}}")
        for attempt in range(6):  # retry while IAM role propagates
            r = subprocess.run(
                [AWS_CLI_PATH, "lambda", "create-function",
                 "--function-name", LAMBDA_NAME, "--runtime", RUNTIME,
                 "--role", role_arn,
                 "--handler", "lambda_function.lambda_handler",
                 "--zip-file", f"fileb://{zip_path}",
                 "--timeout", TIMEOUT, "--memory-size", MEMORY,
                 "--environment", env_vars],
                capture_output=True, text=True)
            if r.returncode == 0:
                break
            if "role defined for the function cannot be assumed" in r.stderr:
                time.sleep(10)
                continue
            print("FAILED: lambda create-function\n", r.stderr[-600:])
            sys.exit(1)
        else:
            print("FAILED: role never became assumable")
            sys.exit(1)
        print(f"function created: {LAMBDA_NAME} ({RUNTIME}, {MEMORY} MB, "
              f"{TIMEOUT}s timeout)")

    # 4. Function URL (public; the platform's signature check in
    #    lambda_function.py is the actual auth layer).
    r = subprocess.run(
        [AWS_CLI_PATH, "lambda", "get-function-url-config",
         "--function-name", LAMBDA_NAME],
        capture_output=True, text=True)
    if r.returncode != 0:
        out = aws("lambda", "create-function-url-config",
                  "--function-name", LAMBDA_NAME, "--auth-type", "NONE")
    else:
        out = r.stdout

    # Public access needs BOTH grants since Oct 2025 (older docs/tutorials
    # list only the first) — missing the second yields a bare 403 at the
    # Function URL edge, before the function ever runs.
    subprocess.run(
        [AWS_CLI_PATH, "lambda", "add-permission", "--function-name",
         LAMBDA_NAME, "--statement-id", "public-url", "--action",
         "lambda:InvokeFunctionUrl", "--principal", "*",
         "--function-url-auth-type", "NONE"],
        capture_output=True, text=True)  # ok if already exists
    subprocess.run(
        [AWS_CLI_PATH, "lambda", "add-permission", "--function-name",
         LAMBDA_NAME, "--statement-id", "public-invoke", "--action",
         "lambda:InvokeFunction", "--principal", "*"],
        capture_output=True, text=True)  # ok if already exists

    url = json.loads(out)["FunctionUrl"]
    print("\nWEBHOOK URL:", url)
    print("\nDone. Next: run the verification tests in GUIDE.md Part 2.5, "
          "then point your webhook platform's console at this URL.")


if __name__ == "__main__":
    main()

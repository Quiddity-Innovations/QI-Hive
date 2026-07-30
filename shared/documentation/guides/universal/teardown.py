# -*- coding: utf-8 -*-
"""Teardown — removes everything deploy.py created, in dependency order.
Reads the same config.env. Safe to re-run; missing resources are skipped.
Added after the 2026-07-30 clean-room certification (QA finding: a kit that
can build a stack must also be able to remove it cleanly).
"""
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).parent


def load_config():
    cfg = {}
    for raw in (HERE / "config.env").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip()
    return cfg


def aws(*args):
    r = subprocess.run(["aws", *args], capture_output=True, text=True)
    return r.returncode == 0, (r.stderr or r.stdout).strip()[:160]


def main():
    cfg = load_config()
    region, account = cfg["AWS_REGION"], cfg["AWS_ACCOUNT_ID"]
    fn, role = cfg["LAMBDA_NAME"], cfg["ROLE_NAME"]
    queue_url = f"https://sqs.{region}.amazonaws.com/{account}/{cfg['QUEUE_NAME']}"

    ok, msg = aws("lambda", "delete-function", "--function-name", fn)
    print(f"lambda {fn}: {'deleted' if ok else 'skip (' + msg + ')'}")

    ok, out = aws("iam", "list-role-policies", "--role-name", role,
                  "--query", "PolicyNames", "--output", "text")
    if ok and out:
        for p in out.split():
            aws("iam", "delete-role-policy", "--role-name", role,
                "--policy-name", p)
            print(f"role policy {p}: deleted")
    ok, msg = aws("iam", "delete-role", "--role-name", role)
    print(f"role {role}: {'deleted' if ok else 'skip (' + msg + ')'}")

    ok, msg = aws("sqs", "delete-queue", "--queue-url", queue_url)
    print(f"queue {cfg['QUEUE_NAME']}: {'deleted' if ok else 'skip (' + msg + ')'}")

    ok, msg = aws("ssm", "delete-parameter", "--name", cfg["SECRET_PARAM_PATH"])
    print(f"secret {cfg['SECRET_PARAM_PATH']}: {'deleted' if ok else 'skip (' + msg + ')'}")

    print("\nTeardown complete. (IAM user, budget, and account-level items "
          "are intentionally not touched.)")


if __name__ == "__main__":
    main()

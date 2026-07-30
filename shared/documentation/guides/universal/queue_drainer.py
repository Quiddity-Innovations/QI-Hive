# -*- coding: utf-8 -*-
"""Free Webhook-Bot Cloud Kit — queue_drainer.py

Home-side consumer of the AWS webhook relay. Long-polls the SQS FIFO
queue, reconstructs each queued event as a signed webhook POST to your
local bot server (loopback), and deletes the message on success.

Flow:  platform -> Lambda -> SQS -> this drainer -> your local server

Nothing here knows about any specific bot's business logic — it only
replays the original webhook shape over loopback so your existing
webhook handler processes relayed events through its normal code path.

All configuration is via environment variables (see config.env.example
for the canonical list and defaults); this script has no hardcoded
paths, hostnames, or account details. A service wrapper (NSSM,
systemd, or docker-compose) is expected to set these before launch.
"""
import base64
import hashlib
import hmac
import json
import os
import sys
import time
from datetime import datetime

# If this script runs as a Windows service under LocalSystem (or any
# account other than the one that ran `aws configure`), boto3 won't
# find that user's credentials automatically. Set
# AWS_SHARED_CREDENTIALS_FILE / AWS_CONFIG_FILE as environment
# variables on the service itself (NSSM AppEnvironmentExtra, systemd
# Environment=, or docker-compose environment:) to point at the right
# credentials/config files — must be set before boto3 is imported,
# which is why this comment lives above the import rather than below.

import boto3  # noqa: E402
import requests  # noqa: E402

QUEUE_URL = os.environ["QUEUE_URL"]
LOCAL_WEBHOOK = os.environ["LOCAL_WEBHOOK_URL"]
SECRET_ENV_FILE = os.environ["CHANNEL_SECRET_ENV_FILE"]
SECRET_ENV_KEY = os.environ.get("CHANNEL_SECRET_ENV_KEY", "CHANNEL_SECRET")
LOG_FILE = os.environ["DRAIN_LOG_FILE"]
SIG_HEADER = os.environ.get("SIGNATURE_HEADER_NAME", "X-Line-Signature")
RELAY_HEADER_NAME = os.environ.get("RELAY_HEADER_NAME", "X-Relay")
RELAY_HEADER_VALUE = os.environ.get("RELAY_HEADER_VALUE", "1")

LOG_MAX_BYTES = 5 * 1024 * 1024
POLL_WAIT_S = 20          # SQS long-poll duration
LOCAL_TIMEOUT_S = 180     # bot servers doing inline LLM calls can be slow
IDLE_LOG_EVERY_S = 600    # heartbeat line when the queue is quiet


def log(msg):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    try:
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > LOG_MAX_BYTES:
            os.replace(LOG_FILE, LOG_FILE + ".old")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def load_secret():
    with open(SECRET_ENV_FILE, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if line.startswith(f"{SECRET_ENV_KEY}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError(f"{SECRET_ENV_KEY} not found in {SECRET_ENV_FILE}")


def sign(secret: bytes, body: bytes) -> str:
    return base64.b64encode(hmac.new(secret, body, hashlib.sha256).digest()).decode()


def deliver(secret: bytes, message_body: str) -> str:
    """Forward one queued event to the local server. Returns: 'ok' | 'retry' | 'drop'."""
    try:
        payload = json.loads(message_body)
    except ValueError:
        log("DROP  malformed queue message (not JSON)")
        return "drop"
    body = json.dumps(
        {"destination": payload.get("destination"),
         "events": [payload.get("event", {})]},
        ensure_ascii=False).encode("utf-8")
    try:
        r = requests.post(
            LOCAL_WEBHOOK, data=body, timeout=LOCAL_TIMEOUT_S,
            headers={"Content-Type": "application/json",
                     SIG_HEADER: sign(secret, body),
                     RELAY_HEADER_NAME: RELAY_HEADER_VALUE})
    except requests.RequestException as e:
        log(f"RETRY local server unreachable ({e.__class__.__name__}) — will retry")
        return "retry"
    if r.status_code == 200:
        return "ok"
    if 400 <= r.status_code < 500:
        log(f"DROP  local server rejected event HTTP {r.status_code}: {r.text[:200]}")
        return "drop"
    log(f"RETRY local server HTTP {r.status_code} — will retry")
    return "retry"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    secret = load_secret().encode("utf-8")
    sqs = boto3.client("sqs")
    log(f"START queue drainer — queue={QUEUE_URL.rsplit('/', 1)[-1]} "
        f"target={LOCAL_WEBHOOK}")
    last_activity = time.monotonic()
    while True:
        try:
            resp = sqs.receive_message(
                QueueUrl=QUEUE_URL, MaxNumberOfMessages=10,
                WaitTimeSeconds=POLL_WAIT_S)
        except Exception as e:
            log(f"ERROR SQS receive failed: {e} — backing off 60 s")
            time.sleep(60)
            continue
        msgs = resp.get("Messages", [])
        if not msgs:
            if time.monotonic() - last_activity > IDLE_LOG_EVERY_S:
                log("IDLE  heartbeat — queue empty, drainer healthy")
                last_activity = time.monotonic()
            continue
        for m in msgs:
            verdict = deliver(secret, m["Body"])
            if verdict in ("ok", "drop"):
                sqs.delete_message(QueueUrl=QUEUE_URL,
                                   ReceiptHandle=m["ReceiptHandle"])
            if verdict == "ok":
                log("OK    event delivered")
            if verdict == "retry":
                time.sleep(10)  # don't hammer a down/failing local server
        last_activity = time.monotonic()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("STOP  drainer shut down")

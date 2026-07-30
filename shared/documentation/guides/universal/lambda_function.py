# -*- coding: utf-8 -*-
"""Free Webhook-Bot Cloud Kit — Lambda front door.

Receives a webhook POST via a Lambda Function URL, verifies its
signature (HMAC-SHA256 against a secret held in SSM Parameter Store),
and enqueues each event onto an SQS FIFO queue. A home-side drainer
(queue_drainer.py) consumes the queue and forwards events to your bot
server over loopback.

Runtime: python3.12 (or any Python 3.9+ Lambda runtime)
Deps: stdlib + boto3 (boto3 is bundled in every standard Lambda runtime)

Env vars (set by deploy.py from config.env):
  QUEUE_URL      — full SQS queue URL to enqueue into
  SECRET_PARAM   — SSM parameter name holding the signing secret
  SIG_HEADER     — request header name carrying the signature
                   (default: x-line-signature)

--------------------------------------------------------------------
PLATFORM NOTES — this file ships wired for LINE's signature scheme.
Swap the verification block in lambda_handler() for your platform:

  LINE (default here):
    Header "X-Line-Signature" = base64(HMAC-SHA256(channel_secret, raw_body))
    Verify with hmac.compare_digest against a freshly computed digest.

  Telegram:
    No signature header — instead the bot token is embedded in the
    webhook URL path itself (Telegram calls
    https://.../<your-bot-token>). Compare the path segment to the
    secret instead of computing an HMAC; still fetch the token from
    SSM, never hardcode it. Optionally also check the
    "X-Telegram-Bot-Api-Secret-Token" header if you set one via
    setWebhook's secret_token param — that IS a genuine HMAC-free
    shared-secret comparison (constant-time string compare).

  Meta (WhatsApp Cloud API / Messenger / Instagram):
    Header "X-Hub-Signature-256" = "sha256=" + hex(HMAC-SHA256(app_secret,
    raw_body)). Same shape as LINE but hex instead of base64, and the
    header value has a "sha256=" prefix to strip before compare_digest.
--------------------------------------------------------------------
"""
import base64
import hashlib
import hmac
import json
import os

import boto3

QUEUE_URL = os.environ["QUEUE_URL"]
SECRET_PARAM = os.environ["SECRET_PARAM"]
SIG_HEADER = os.environ.get("SIG_HEADER", "x-line-signature").lower()

_ssm = boto3.client("ssm")
_sqs = boto3.client("sqs")

# Fetched once per warm container, not per request.
_SECRET = _ssm.get_parameter(Name=SECRET_PARAM, WithDecryption=True)[
    "Parameter"]["Value"].encode("utf-8")


def _resp(status, body=""):
    return {"statusCode": status, "body": body}


def lambda_handler(event, context):
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    signature = headers.get(SIG_HEADER)
    if not signature:
        return _resp(403, "missing signature")

    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(body)
    else:
        raw = body.encode("utf-8")

    # LINE-style verification (base64 HMAC-SHA256). See platform notes
    # above the imports for Telegram/Meta variants.
    expected = base64.b64encode(
        hmac.new(_SECRET, raw, hashlib.sha256).digest()).decode()
    if not hmac.compare_digest(expected, signature):
        return _resp(403, "bad signature")

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return _resp(400, "bad body")

    # Most chat webhook platforms batch multiple events per request;
    # enqueue individually, keyed by conversation so each user/group
    # keeps strict message order in the FIFO queue.
    for ev in payload.get("events", []):
        src = ev.get("source", {})
        group_id = (src.get("userId") or src.get("groupId")
                    or src.get("roomId") or "default")
        _sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageGroupId=group_id,
            MessageBody=json.dumps(
                {"destination": payload.get("destination"), "event": ev},
                ensure_ascii=False),
        )
    # Always 200 so the platform doesn't retry (verify-button pings
    # send 0 events — that's fine, still 200).
    return _resp(200, "ok")

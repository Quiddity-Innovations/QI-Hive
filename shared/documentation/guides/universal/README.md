# Free Webhook-Bot Cloud Kit

Connect any home-hosted webhook bot (LINE, Telegram, Meta/WhatsApp, or
anything else that POSTs signed JSON to a URL) to a permanently-free
AWS front door — no cloud bill, no dropped messages when your home
machine reboots.

## Architecture

```
Webhook source (LINE / Telegram / Meta / etc.)
   │  signed POST
   ▼
AWS Lambda  "<bot-name>-webhook"        ← always-free, always up
   │  1. verify signature (secret from SSM Parameter Store)
   │  2. enqueue raw event JSON
   ▼
AWS SQS FIFO  "<bot-name>-events.fifo"  ← durable buffer, survives home outages
   ▼
Home machine — queue_drainer.py         ← long-polls the queue
   │  reconstructs the original webhook shape, POSTs to loopback
   ▼
Your existing bot server (unchanged webhook handler, LLM chain, DB, whatever)
```

Nothing about your bot's intelligence moves to the cloud. Only its
front door does. Cutover is a single URL change in your platform's
webhook console, and it's instantly reversible.

## Why this exists

The full step-by-step story — including the exact gotchas that cost
real debugging time — is generalized in **[GUIDE.md](GUIDE.md)**.
This kit is the parameterized, platform-agnostic extraction of a
working implementation (a LINE bot relay); every QI-specific name,
account ID, and path has been replaced with config-driven values.

## What's parameterized

Every AWS resource name, account ID, region, local path, and platform
signature header lives in **one file**: `config.env` (copy it from
`config.env.example`). Nothing else in this kit needs editing for a
normal deployment — `deploy.py`, `grant_role_policy.bat`, and
`queue_drainer.py` all read their configuration from it or from
environment variables set from it.

| File | Role |
|---|---|
| [`config.env.example`](config.env.example) | Every parameter in one place — copy to `config.env` and fill in |
| [`lambda_function.py`](lambda_function.py) | Cloud-side signature verification + SQS enqueue |
| [`deploy.py`](deploy.py) | Idempotent deploy: queue + IAM role + Lambda + public Function URL |
| [`queue_drainer.py`](queue_drainer.py) | Home-side long-poll consumer, forwards events to your bot over loopback |
| [`Dockerfile`](Dockerfile) + [`docker-compose.yml`](docker-compose.yml) | Optional containerized drainer deployment |
| [`grant_role_policy.bat`](grant_role_policy.bat) + [`role_policy.json.template`](role_policy.json.template) | One-time scoped IAM grant so your CLI user can create the Lambda's execution role without full IAM access |
| [`GUIDE.md`](GUIDE.md) | Full step-by-step: account setup through cutover, plus a GOTCHAS section |

## Quick-start order

1. Read [GUIDE.md](GUIDE.md) Part 1 — create/secure the AWS account, install the CLI, `aws configure`.
2. Copy `config.env.example` → `config.env`, fill in your values.
3. Store your webhook platform's signing secret in SSM (GUIDE.md 2.2).
4. Run `grant_role_policy.bat` once (needs a one-time root sign-in).
5. Run `python deploy.py` — creates the queue, role, Lambda, and public Function URL.
6. Verify with the three tests in GUIDE.md 2.5 (forged sig → 403, valid sig → 200, message lands in queue).
7. Install `queue_drainer.py` as a service (NSSM on Windows, systemd on Linux, or the provided Dockerfile) pointed at your bot's local webhook endpoint.
8. Shadow-test end-to-end, then cut your platform's webhook console over to the Function URL.

## Cost

$0/month at personal-use volume — every AWS service this kit touches
(Lambda, SQS, SSM Parameter Store, CloudWatch Logs basics, IAM) sits
inside the permanent always-free tier, independent of the newer
account's 6-month credit window. See GUIDE.md Part 0 for the reasoning
and GUIDE.md's Lessons/Gotchas section for the account-model details.

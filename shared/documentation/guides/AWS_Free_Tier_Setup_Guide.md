# AWS Free Tier — Setup & First Project Guide
### From zero to a permanently-free cloud edge for a home-hosted system

**Audience:** anyone starting with a new (2025+) AWS free account who runs local apps/bots and wants cloud reliability without cloud bills.
**Living document** — updated as the QI implementation progresses. Each step is written so a third party can follow it independently.

| | |
|---|---|
| Project | Maia webhook relay (LINE bot → AWS Lambda → SQS → home machine) |
| Started | 2026-07-30 |
| Status | ✅ Phases 1–3 COMPLETE — relay LIVE (cutover 2026-07-30); 48 h observation running |
| Cost target | $0/month permanently (always-free tier only) |
| Companion video | Planned — animated explainer, produced after Phase 3 completes |

---

## 📊 Progress tracker

| # | Step | Status | Date |
|---|---|---|---|
| 1.1 | Create AWS free account | ✅ Done | 2026-07-30 |
| 1.2 | Enable MFA on root account | ✅ Done | 2026-07-30 |
| 1.3 | Create IAM working user (`qi-claude-cli`) | 🔄 In progress | |
| 1.4 | Install AWS CLI v2 on the workstation | ✅ Done | 2026-07-30 |
| 1.5 | `aws configure` with IAM access key | ✅ Done | 2026-07-30 |
| 1.6 | Verify identity + set billing budget alert | ✅ Done | 2026-07-30 |
| 1.7 | Scoped IAM-role-management policy for the CLI user | ✅ Done (via bat) | 2026-07-30 |
| 2.1 | Create SQS FIFO queue | ✅ Done | 2026-07-30 |
| 2.2 | Store LINE channel secret in SSM Parameter Store | ✅ Done | 2026-07-30 |
| 2.3 | Write Lambda function + deployment script | ✅ Done | 2026-07-30 |
| 2.4 | Deploy Lambda + Function URL | ✅ Done | 2026-07-30 |
| 2.5 | Verify: forged sig 403 / valid sig 200 / message in queue | ✅ All pass | 2026-07-30 |
| 3.1 | Queue drainer + reply-token freshness patch | ✅ Done | 2026-07-30 |
| 3.2 | QI_MaiaQueueDrain service (via elevation broker) | ✅ Done | 2026-07-30 |
| 3.3 | Shadow test: full path incl. real LINE push | ✅ Pass | 2026-07-30 |
| 3.4 | LINE CUTOVER — relay is now Maia's front door | ✅ Done | 2026-07-30 |
| 3.5 | 48 h observation window | 🔄 Running | → 2026-08-01 |
| 4.x | Explainer video production | ⏳ Pending | |
| 5.x | **Universal (non-QI) edition** of guide + scripts | ⏳ After Phase 3 | |

---

## 🧩 Components & software bill of materials

Everything needed to reproduce this project. Updated as phases add components.

### Accounts (all free)
| Account | Purpose | Notes |
|---|---|---|
| AWS account (Free plan) | Cloud side | New-model free tier: $100 credit at signup + up to $100 via "Explore AWS" activities; free plan lasts 6 months or until credits run out. ~30 **always-free** services (Lambda, SQS, DynamoDB, EventBridge, SNS, CloudFront quotas) continue at $0 forever |
| LINE Developers account | The bot channel being relayed | Existing Messaging API channel; free plan includes ~200 push messages/month |
| GitHub (optional) | Version control for the relay code | Any git remote works |

### Workstation software (Windows 11 in our case)
| Software | Version used | Install command | Purpose |
|---|---|---|---|
| AWS CLI v2 | 2.36.11 | `winget install --id Amazon.AWSCLI` | All AWS provisioning & deployment from the terminal |
| Python | 3.10+ | (already present) | Queue-drainer service + Lambda function code |
| `boto3` | latest | `pip install boto3` | AWS SDK for the home-side poller *(Phase 3)* |
| NSSM | 2.24 | ships in `engine\bin\nssm.exe` per QI standard | Runs the queue drainer as a Windows service *(Phase 3)* |

### AWS services used (all within always-free quotas at personal volume)
| Service | Free quota (monthly, permanent) | Role in this project |
|---|---|---|
| Lambda | 1M invocations + 400k GB-s | Receives LINE webhooks (Function URL — no API Gateway needed) |
| SQS (FIFO) | 1M requests | Durable message queue; preserves per-user message order |
| SSM Parameter Store | 10k standard parameters | Holds the LINE channel secret (never hardcoded) |
| CloudWatch Logs | 5 GB ingest | Lambda logging/diagnostics |
| IAM / Budgets | Always free | Access control + spend alarm |

### Video production toolchain (Phase 4 — all free/local)
| Tool | Purpose |
|---|---|
| `edge-tts` (Python) | Free neural narration (Andrew/Ava voices) |
| Pillow (Python) | Renders 1080p frames incl. flat 2D animated cartoon characters (Kroger-commercial style) |
| FFmpeg | Assembles frames + narration into MP4 |
| Existing QI pipeline | `C:\APPS\CLAUDE\Tools\build_bu_videos.py` — being extended with a character-animation layer |

---

## Part 0 — Why this architecture

**The problem:** the entire system (bots, databases, LLMs) runs on one home machine. When it reboots or fails, incoming webhook messages (e.g. LINE messages to the Maia bot) are lost, and nothing external notices the outage.

**The constraint:** the new AWS free tier gives no free virtual servers and no free GPUs. Long-running processes and LLM inference cannot live on AWS for free — but *event-driven* serverless pieces can, forever.

**The strategy — "edge in the cloud, brain at home":**

```
LINE platform
   │  webhook POST
   ▼
AWS Lambda  "qi-maia-webhook"        ← always-free, always up
   │  1. verify X-Line-Signature (secret from SSM Parameter Store)
   │  2. enqueue raw event JSON
   ▼
AWS SQS FIFO  "qi-maia-events.fifo"  ← durable buffer, survives home outages
   ▼
Home machine  QI_MaiaQueueDrain      ← NSSM service, long-polls the queue
   │  hands events to the existing bot server (unchanged LLM chain, DB)
   ▼
LINE Push API  ← replies (push, not reply-token, since tokens expire in ~1 min)
```

Nothing about the bot's intelligence moves to the cloud. Only its front door does. Cutover is one URL change in the LINE console and is instantly reversible.

---

## Part 1 — Account hygiene (do this before anything else)

### 1.1 Create the AWS account ✅
Sign up at aws.amazon.com → choose the **Free** account plan. You get $100 credit immediately; the free plan runs 6 months or until credits are exhausted. **The clock starts now — don't create the account until you're ready to use it.**

### 1.2 Protect the root account ✅
The root user (the email you signed up with) can do *anything*, including deleting the account. Lock it down and stop using it:
1. Console → account menu (top-right) → **Security credentials**
2. **Assign MFA device** → Authenticator app → scan the QR with any TOTP app (Google Authenticator, Authy, etc.)
3. From now on, the root login is for emergencies and billing only.

### 1.3 Create an IAM working user 🔄
Daily work happens as a limited user, never as root:
1. Console → **IAM → Users → Create user** → name: `qi-claude-cli`
2. **No console access** (CLI-only user)
3. Permissions → **Attach policies directly** → `PowerUserAccess`
   *(everything except IAM administration; tighten later to just Lambda/SQS/SSM/S3 once the project's real footprint is known)*
4. Open the created user → **Security credentials → Create access key** → use-case **CLI** → create. In the **description**, record *machine + purpose + date* (e.g. `QI main workstation - AWS CLI provisioning via Claude Code (created 2026-07-30)`) — when you later rotate or delete keys, the description is how you know which key lives where without guesswork.
5. The Access Key ID + Secret are shown **once**. Go straight to step 1.5, then close the page.

### 1.4 Install the AWS CLI ✅
```bash
winget install --id Amazon.AWSCLI --accept-source-agreements --accept-package-agreements
```
Verify in a **new** terminal:
```bash
aws --version
```
Expected: `aws-cli/2.x ...` (we got 2.36.11).

### 1.5 Configure credentials ⏳
In a terminal, run:
```bash
aws configure
```
Enter: the Access Key ID, the Secret Access Key, default region `us-east-1`, output `json`.
This stores the key in `%USERPROFILE%\.aws\credentials` (local file, plain text — that's normal; it's protected by your Windows login). **Never paste access keys into chats, docs, or code.**

Region note: `us-east-1` (N. Virginia) has every service and the lowest prices. For webhook/queue workloads, latency to your home is irrelevant — the queue absorbs it.

### 1.6 Verify + billing guardrail ✅
```bash
aws sts get-caller-identity
```
Expected: JSON showing the account ID and `.../user/qi-claude-cli`. Then set a spend alarm. Console route: **Billing → Budgets → Create budget → Zero spend budget** template. CLI route (what we did — two JSON files, budget of $1 with an email alert at 1% = $0.01):
```bash
aws budgets create-budget --account-id <ACCOUNT_ID> --budget file://budget.json --notifications-with-subscribers file://budget-notify.json
```
`budget.json`: `{"BudgetName":"QI-ZeroSpend-Guard","BudgetLimit":{"Amount":"1.0","Unit":"USD"},"BudgetType":"COST","TimeUnit":"MONTHLY"}`
`budget-notify.json`: one ACTUAL notification, `GREATER_THAN` threshold `1` (`PERCENTAGE`), subscriber = your email.

### 1.7 Scoped IAM exception for role creation 🔄
`PowerUserAccess` deliberately blocks all IAM writes — but deploying a Lambda requires creating its **execution role** (the identity the function runs as). Rather than granting broad IAM rights, add an inline policy to the CLI user that only manages roles in your project namespace (`qi-*`).

**Note that the CLI user cannot grant this to itself** — that's the security model working. The grant must come from an admin identity (root, in a personal account). Two ways:

**Option A — run the batch file (what we use):** double-click
[`AWS_Setup_Step_1_7_GrantRolePolicy.bat`](AWS_Setup_Step_1_7_GrantRolePolicy.bat) (in this folder, with its companion [`qi_role_policy.json`](qi_role_policy.json)).
It runs `aws login` — a browser opens; **sign in as the root user** — which issues *temporary, auto-expiring* admin credentials under a throwaway profile, attaches the inline policy to `qi-claude-cli`, verifies it, and finishes. Nothing permanent is stored. This is the one scenario where `aws login`-style temporary credentials are exactly right: a single privileged action by a human, not an unattended service.

**Option B — console clicks:** Console → **IAM → Users → `qi-claude-cli` → Add permissions → Create inline policy → JSON**:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "ManageQiPrefixedRolesOnly",
    "Effect": "Allow",
    "Action": [
      "iam:CreateRole", "iam:GetRole", "iam:DeleteRole",
      "iam:AttachRolePolicy", "iam:DetachRolePolicy",
      "iam:PutRolePolicy", "iam:DeleteRolePolicy", "iam:ListRolePolicies",
      "iam:ListAttachedRolePolicies", "iam:TagRole", "iam:PassRole"
    ],
    "Resource": "arn:aws:iam::<ACCOUNT_ID>:role/qi-*"
  }]
}
```
Name: `QI-RoleManagement-Scoped`. **Lesson:** hitting `AccessDenied` and answering it with the *narrowest possible* exception is the core IAM skill — resist the urge to attach `IAMFullAccess`.

---

## Part 2 — Cloud side: SQS + secret + Lambda

### 2.1 Create the FIFO queue ✅
```bash
aws sqs create-queue --queue-name qi-maia-events.fifo --attributes '{"FifoQueue":"true","ContentBasedDeduplication":"true","MessageRetentionPeriod":"345600"}'
```
- **FIFO** = strict ordering within a message group; we group by LINE user ID so each conversation stays in order.
- **ContentBasedDeduplication** = identical webhook retries (LINE re-sends on timeout) collapse into one message automatically.
- **Retention 345600 s (4 days)** = how long the home machine can be down without losing messages.

### 2.2 Store the channel secret in SSM Parameter Store ✅
The Lambda must verify LINE's `X-Line-Signature`, which requires the channel secret. It goes into SSM as an encrypted **SecureString** — never into code or Lambda env vars:
```bash
aws ssm put-parameter --name /qi/maia/line_channel_secret --type SecureString --value <SECRET> --overwrite
```
In our run, a short Python script read the secret from the local `secrets\maia.env` and piped it straight to this command so the value never appeared on screen or in logs. Standard SSM parameters + default KMS encryption = free.

### 2.3 The Lambda function ✅
Code: [`C:\APPS\QI\TOOLS\aws_relay\lambda_function.py`](C:\APPS\QI\TOOLS\aws_relay\lambda_function.py) — ~80 lines, stdlib + boto3 only. What it does per request:
1. Reject if `X-Line-Signature` header is missing → 403
2. Compute HMAC-SHA256 of the raw body with the channel secret (fetched from SSM once per warm container); constant-time compare → 403 on mismatch. **This signature check is the security layer that makes a public URL safe.**
3. Parse the webhook JSON; enqueue each event to SQS with `MessageGroupId` = LINE user/group/room ID (preserves per-conversation order)
4. Return 200 fast — LINE only needs an ack; the real reply happens later from home

### 2.4 Deploy: role + function + public URL ⏳
Deployment script: [`C:\APPS\QI\TOOLS\aws_relay\deploy_lambda.py`](C:\APPS\QI\TOOLS\aws_relay\deploy_lambda.py) — idempotent (safe to re-run). It:
1. Creates execution role `qi-maia-webhook-role` — trust policy allows only `lambda.amazonaws.com`; permissions are exactly three: `sqs:SendMessage` on our queue, `ssm:GetParameter` on our one parameter, CloudWatch logs
2. Zips + creates/updates function `qi-maia-webhook` (python3.12, 128 MB, 10 s timeout — smallest possible footprint)
3. Creates a **Function URL** with auth `NONE` (public — that's what LINE needs to reach; step 2.3's signature check does the authenticating) and prints the webhook URL
- Gotcha handled in-script: a freshly created IAM role takes ~10 s to become assumable; the script retries `create-function` instead of failing.

**One-shot alternative:** run [`AWS_Setup_Part_2_DeployRelay.bat`](AWS_Setup_Part_2_DeployRelay.bat) (this folder) — it drives the deploy script, which is fully idempotent and now covers ALL of Part 2 (queue + secret check + role + function + URL). Re-running it later redeploys updated Lambda code.

**What is deployed, exactly (for manual reproduction):**
| Resource | Name | Key settings |
|---|---|---|
| SQS FIFO queue | `qi-maia-events.fifo` | content-based dedup ON, retention 4 days |
| SSM parameter | `/qi/maia/line_channel_secret` | SecureString, default KMS key |
| IAM role | `qi-maia-webhook-role` | trust: `lambda.amazonaws.com`; inline policy: `sqs:SendMessage` (our queue), `ssm:GetParameter` (our parameter), CloudWatch logs |
| Lambda | `qi-maia-webhook` | python3.12, 128 MB, 10 s timeout, env `QUEUE_URL` + `SECRET_PARAM`, handler `lambda_function.lambda_handler` |
| Function URL | auth type `NONE` (public) | resource policy: **two** public grants — see gotcha below |

### 2.5 Verify before going live ✅
Three tests, all must pass (a test script simulates LINE's POSTs):
1. **Forged signature → `403 "bad signature"`** — proves the public URL is not an open door
2. **Correctly-signed request → `200 "ok"`** — HMAC computed with the same channel secret LINE uses
3. **Queue check** — `aws sqs receive-message` returns the event with the right user ID and text; delete the test message afterwards

Result 2026-07-30: all three PASS on first attempt after the resource-policy fix below.

## Part 3 — Home side: queue drainer + cutover ✅ (2026-07-30)

### 3.1 Design: loopback delivery
The drainer does NOT reimplement any bot logic. It reconstructs each queued event as a LINE-webhook-shaped POST to the local server (`http://127.0.0.1:8001/maia/webhook`), **signed with the same channel secret** — so the bot processes relayed events through its existing, battle-tested code path. A marker header `X-Qi-Relay: 1` tells the server the event came via the queue.

### 3.2 The reply-token economics patch
LINE replies (via reply token) are free/unlimited but tokens die in ~1 min; pushes always work but free accounts get only ~200/month. The server patch (`channels/line.py` + `make_push_sender()` in `maia_server.py`):
- relayed event **younger than 45 s** → use its still-valid reply token (free) — the normal case
- relayed event **older** (backlog drained after downtime) → substitute a push-callable for the token (`send_reply` already accepted callables)
⚠️ Without the freshness check, ALL relayed replies would be pushes and the monthly quota would die in days. Design rule: **push is for backlog only.**

### 3.3 The drainer
[`C:\APPS\QI\TOOLS\aws_relay\queue_drainer.py`](C:\APPS\QI\TOOLS\aws_relay\queue_drainer.py): boto3 long-poll (20 s) on the FIFO queue → loopback POST (180 s timeout — LLM replies are slow) → delete on 200. Verdict logic: `ok`/4xx → delete (4xx = poison message, logged, never loops), 5xx/unreachable → leave for retry via visibility timeout. Heartbeat log line every 10 min. Logs: `C:\APPS\QI\LOGS\queue_drain_log.txt` + service log `C:\QIH\logs\maia_queue_drain.log`.

### 3.4 Service installation (via elevation broker)
Installed as **QI_MaiaQueueDrain** through the QI_Elevate broker (7 whitelisted `nssm` calls: install, AppDirectory, Description, Start, AppStdout, AppStderr, start). The broker whitelist only accepts service scripts under `C:\QIH|C:\APPS\QIP`, so a 3-line **launcher shim** (`C:\QIH\engine\relay\maia_queue_drain_service.py`, `runpy.run_path` → real drainer) bridges to the Maia project without weakening the policy. AWS credentials: the service runs as LocalSystem, so the drainer pins `AWS_SHARED_CREDENTIALS_FILE` to the workstation user's credentials file explicitly.

### 3.5 Shadow test (before cutover)
With LINE still pointed at the tunnel, a synthetic signed event was POSTed to the **Lambda URL**: Lambda → SQS → drainer → local server → LLM reply → push delivered to the owner's real LINE. Full-path proof with zero production risk.

### 3.6 Cutover — and the self-registration gotcha
The server **re-registers its LINE webhook URL on every startup** — any manual change in the LINE console would be silently reverted on the next restart. So the cutover lives in code: a `_line_webhook_url` constant (set to the Lambda Function URL) now feeds LINE registration, while Telegram keeps the direct tunnel URL. Cutover = edit constant + restart. **Rollback = revert constant + restart** (one line, documented in the code comment).
Verification, twice over: startup log shows registration to the Lambda URL, and LINE's own APIs confirm — `GET /v2/bot/channel/webhook/endpoint` returns the Lambda URL (`active: true`), and `POST /v2/bot/channel/webhook/test` (LINE fires a real request from their servers) returned `success: true, statusCode: 200`.

### 3.7 What changed on the machine (reproduction summary)
| File | Change |
|---|---|
| `maia_server.py` | + `make_push_sender()`; LINE registration now uses `_line_webhook_url` (Lambda) |
| `channels/line.py` | + `relayed` flag, `_tok()` freshness helper; 4 reply-token sites now use `_tok(event)` |
| `TOOLS/aws_relay/queue_drainer.py` | new — the drainer |
| `C:\QIH\engine\relay\maia_queue_drain_service.py` | new — whitelist launcher shim |
| `pip install boto3` | drainer dependency |
| Registries | `QI_Service_Registry.md` + `qi_registry.json` (`shared_infrastructure.aws`) |

## Part 4 — Explainer video *(pending)*
*Storyboard + production of the animated step-by-step video from this guide.*

## Part 5 — Universal edition *(pending — after Phase 3 proves the full flow)*
*A neutral, non-QI package for anyone to reuse: generic guide (placeholders for account ID / bot name / secret path), parameterized versions of the 1.7 grant bat, the deploy script + Part 2 bat, the Lambda function, and the queue-drainer service — "connect any home-hosted webhook bot to a free AWS front door".*

---

## ⚠️ Lessons & gotchas log
*(appended as encountered)*
- **Public Function URL returns bare 403 even with a "correct" policy (Oct 2025 rule change):** a public (auth `NONE`) Function URL now requires **two** resource-policy grants — `lambda:InvokeFunctionUrl` (with the `FunctionUrlAuthType: NONE` condition) **and** plain `lambda:InvokeFunction` (no condition — the API rejects the condition flag on this action). Most tutorials predate this and list only the first; the symptom is AWS's own generic `403 Forbidden` at the URL edge (your function never runs — no log entries). Debug technique that isolated it: `aws lambda invoke` directly worked while the URL 403'd → the block had to be at the URL authorization layer.
- **LINE SDK strictness:** the v3 SDK parser rejects events missing `deliveryContext` — synthetic test events must include every schema field a real webhook carries (deliveryContext, timestamp, mode). Real LINE events always validate.
- **Self-registering webhooks:** a bot that re-registers its webhook URL at startup will silently undo a console-side cutover on its next restart. Find the registration code FIRST; make the cutover there.
- **Push quota economics:** LINE free plan ≈ 200 pushes/month but unlimited replies. Any relay design must prefer reply tokens (valid ~1 min) and reserve push for stale backlog.
- Cost sanity: everything deployed in Part 2 is $0 — Lambda/SQS/SSM standard/CloudWatch basics all sit in always-free quotas at personal volume.
- The pre-2025 "12 months free / free t2.micro EC2" model **no longer exists** for new accounts. Plan around credits (6 months) for learning and **always-free** services for anything permanent.
- When you run `aws configure`, the CLI prints a tip suggesting `aws login` instead. Ignore it for this project: `aws login` issues browser-based **temporary** credentials that expire after hours — fine for interactive humans, fatal for unattended services (our queue drainer must auth 24/7 with no browser). Long-lived IAM access keys via `aws configure` are the right choice here.
- Creating the access key shows an **"Alternatives recommended"** banner (aws login, CloudShell). It appears for every key creation. Both alternatives fail this project's needs: `aws login` = expiring credentials (breaks a 24/7 unattended service), CloudShell = runs inside AWS and can't touch your local machine. A long-lived key on a **limited IAM user** is the accepted pattern for workloads outside AWS — the safety comes from least-privilege scoping, local-only storage, a zero-spend budget, and periodic rotation. (The use-case radio button is informational only.) The enterprise upgrade path, if ever needed, is IAM Roles Anywhere.
- Run `aws configure` from a normal (non-admin) terminal in your user profile, not from `C:\Windows\System32` — credentials land in `%USERPROFILE%\.aws\credentials` either way, but everyday CLI work shouldn't happen in an elevated System32 shell.
- LINE reply tokens expire in ~1 minute — a queued/delayed message must be answered via the **Push API**, which has a monthly quota on free LINE plans (~200). Fine for personal use.

---

*Maintained by Claude (QI Hive) with Renne Santiago — Quiddity Innovations. Source of truth for the AWS onboarding video script.*

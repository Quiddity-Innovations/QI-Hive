# Free Webhook-Bot Cloud Kit — Setup Guide

### From zero to a permanently-free cloud front door for a home-hosted webhook bot

**Audience:** anyone with a new AWS free account who runs a local bot
(LINE, Telegram, Meta/WhatsApp, or anything else that receives signed
webhook POSTs) and wants cloud reliability without cloud bills.

**Companion files:** this guide references [`config.env.example`](config.env.example),
[`lambda_function.py`](lambda_function.py), [`deploy.py`](deploy.py),
[`queue_drainer.py`](queue_drainer.py), [`grant_role_policy.bat`](grant_role_policy.bat)
and [`role_policy.json.template`](role_policy.json.template), all in this folder.

---

## Part 0 — Why this architecture

**The problem:** your bot (webhook handler, database, LLM calls, whatever)
runs on one machine. When it reboots or fails, incoming webhook events
are lost, and nothing external notices the outage.

**The constraint:** the modern AWS free tier gives no free virtual
servers and no free GPUs. Long-running processes and heavy compute
can't live on AWS for free — but *event-driven* serverless pieces can,
forever.

**The strategy — "edge in the cloud, brain at home":**

```
Webhook platform (LINE / Telegram / Meta / etc.)
   │  webhook POST
   ▼
AWS Lambda  "<bot-name>-webhook"        ← always-free, always up
   │  1. verify signature (secret from SSM Parameter Store)
   │  2. enqueue raw event JSON
   ▼
AWS SQS FIFO  "<bot-name>-events.fifo"  ← durable buffer, survives home outages
   ▼
Home machine  queue_drainer.py          ← long-polls the queue
   │  hands events to your existing bot server (unchanged logic, DB)
   ▼
Your bot's normal reply mechanism (reply token / push API / whatever the platform offers)
```

Nothing about your bot's intelligence moves to the cloud. Only its
front door does. Cutover is one URL change in your platform's console
and is instantly reversible.

---

## Part 1 — Account hygiene (do this before anything else)

### 1.1 Create the AWS account
Sign up at aws.amazon.com → choose the **Free** account plan. Under
the current (2025+) free-account model you get an initial credit
(commonly $100) at signup plus up to another $100 through guided
"Explore AWS" activities; the free-credit plan runs for 6 months or
until credits are exhausted — whichever comes first. Separately,
~30 **always-free** services (Lambda, SQS, DynamoDB, EventBridge, SNS,
CloudFront quotas, and more) continue at $0/month forever, independent
of the credit window. **The 6-month clock starts at account creation —
don't create the account until you're ready to use it.**

### 1.2 Protect the root account
The root user (the email you signed up with) can do *anything*,
including deleting the account. Lock it down and stop using it:
1. Console → account menu (top-right) → **Security credentials**
2. **Assign MFA device** → Authenticator app → scan the QR with any TOTP app
3. From now on, the root login is for emergencies and billing only.

### 1.3 Create an IAM working user
Daily work happens as a limited user, never as root:
1. Console → **IAM → Users → Create user** → name it (e.g. `<bot-name>-cli` — this is `CLI_USER_NAME` in `config.env`)
2. **No console access** (CLI-only user)
3. Permissions → **Attach policies directly** → `PowerUserAccess`
   *(everything except IAM administration; tighten later to just Lambda/SQS/SSM once your real footprint is known)*
4. Open the created user → **Security credentials → Create access key** → use-case **CLI** → create. In the **description**, record *machine + purpose + date* — when you later rotate or delete keys, the description tells you which key lives where without guesswork.
5. The Access Key ID + Secret are shown **once**. Go straight to step 1.5, then close the page.

### 1.4 Install the AWS CLI
```bash
winget install --id Amazon.AWSCLI --accept-source-agreements --accept-package-agreements
```
Verify in a **new** terminal:
```bash
aws --version
```
Expected: `aws-cli/2.x ...`

### 1.5 Configure credentials
```bash
aws configure
```
Enter: the Access Key ID, the Secret Access Key, your default region
(e.g. `us-east-1`), output `json`. This stores the key in
`%USERPROFILE%\.aws\credentials` on Windows or `$HOME/.aws/credentials`
on Linux/macOS (a local plaintext file — that's normal; it's protected
by your OS login). **Never paste access keys into chats, docs, or code.**

Region note: `us-east-1` (N. Virginia) has every service and the
lowest prices. For webhook/queue workloads, latency to your home
machine is irrelevant — the queue absorbs it.

> **Ignore the "aws login" suggestion here.** When you run `aws configure`,
> the CLI prints a tip suggesting `aws login` instead, and the access-key
> creation page shows an "Alternatives recommended" banner (`aws login`,
> CloudShell). Both alternatives are wrong for this project:
> `aws login` issues browser-based **temporary** credentials that expire
> after hours — fine for an interactive human, fatal for an unattended
> 24/7 service (your queue drainer must authenticate with no browser
> available). CloudShell runs inside AWS and can't touch your local
> machine at all. A long-lived key on a **limited IAM user** is the
> accepted pattern for workloads that live outside AWS — the safety
> comes from least-privilege scoping, local-only storage, a zero-spend
> budget alarm, and periodic rotation, not from the credential type.
> (If you ever need the enterprise-grade version of this, the answer
> is IAM Roles Anywhere — out of scope for a personal project.)

Run `aws configure` from a normal (non-admin) terminal in your user
profile — credentials land in the same place either way, but everyday
CLI work shouldn't happen from an elevated system shell.

### 1.6 Verify + billing guardrail
```bash
aws sts get-caller-identity
```
Expected: JSON showing your account ID and the CLI user's ARN. Then
set a spend alarm. Console route: **Billing → Budgets → Create budget
→ Zero spend budget** template. CLI route (two JSON files, e.g. a
budget of $1 with an alert at 1% = $0.01):
```bash
aws budgets create-budget --account-id <ACCOUNT_ID> --budget file://budget.json --notifications-with-subscribers file://budget-notify.json
```
`budget.json`: `{"BudgetName":"ZeroSpend-Guard","BudgetLimit":{"Amount":"1.0","Unit":"USD"},"BudgetType":"COST","TimeUnit":"MONTHLY"}`
`budget-notify.json`: one ACTUAL notification, `GREATER_THAN` threshold `1` (`PERCENTAGE`), subscriber = your email.

### 1.7 Scoped IAM exception for role creation
`PowerUserAccess` deliberately blocks all IAM writes — but deploying a
Lambda requires creating its **execution role** (the identity the
function runs as). Rather than granting broad IAM rights, add an
inline policy to the CLI user that only manages roles in your own
namespace (`<bot-name>-*`).

**Note the CLI user cannot grant this to itself** — that's the
security model working. The grant must come from an admin identity
(root, in a personal account). Two ways:

**Option A — run the batch file (recommended):**
1. Copy `config.env.example` → `config.env` and fill in `AWS_ACCOUNT_ID`, `BOT_NAME`, `CLI_USER_NAME`, `AWS_REGION`.
2. Double-click [`grant_role_policy.bat`](grant_role_policy.bat).

It substitutes your account ID and bot-name prefix into
`role_policy.json.template`, runs `aws login` (a browser opens — **sign
in as the root user**, which issues *temporary, auto-expiring* admin
credentials under a throwaway profile), attaches the inline policy to
your CLI user, verifies it, and finishes. Nothing permanent is stored.
This is the one legitimate use of `aws login`-style temporary
credentials in this whole kit: a single privileged action performed by
a human, not something an unattended service depends on.

**Option B — console clicks:** Console → **IAM → Users →
`<CLI_USER_NAME>` → Add permissions → Create inline policy → JSON**,
paste the contents of `role_policy.json.template` with `<ACCOUNT_ID>`
and `<BOT_NAME>` filled in. Name it `RoleManagement-Scoped`.

**Lesson:** hitting `AccessDenied` and answering it with the
*narrowest possible* exception is the core IAM skill — resist the urge
to attach `IAMFullAccess`.

---

## Part 2 — Cloud side: SQS + secret + Lambda

### 2.1 The FIFO queue
`deploy.py` creates this for you, but for reference the equivalent CLI
call is:
```bash
aws sqs create-queue --queue-name <BOT_NAME>-events.fifo --attributes '{"FifoQueue":"true","ContentBasedDeduplication":"true","MessageRetentionPeriod":"345600"}'
```
- **FIFO** = strict ordering within a message group; events are grouped by user/conversation ID so each conversation stays in order.
- **ContentBasedDeduplication** = identical webhook retries (most platforms re-send on timeout) collapse into one message automatically.
- **Retention 345600 s (4 days)** = how long your home machine can be down without losing messages. Tune via `QUEUE_RETENTION_SECONDS` in `config.env`.

### 2.2 Store the signing secret in SSM Parameter Store
The Lambda must verify the platform's request signature, which
requires your webhook secret (LINE channel secret, Telegram bot token,
Meta app secret, etc.). It goes into SSM as an encrypted **SecureString**
— never into code or plain Lambda environment variables:
```bash
aws ssm put-parameter --name <SECRET_PARAM_PATH> --type SecureString --value <YOUR_SECRET> --overwrite
```
Pipe the value in from a local file rather than typing it on the
command line if you want it to never appear in your shell history.
Standard SSM parameters with the default KMS key are free.

### 2.3 The Lambda function
Code: [`lambda_function.py`](lambda_function.py) — stdlib + boto3
only. Per request:
1. Reject if the signature header is missing → 403
2. Compute HMAC-SHA256 of the raw body with the secret (fetched from SSM once per warm container); constant-time compare → 403 on mismatch. **This signature check is the security layer that makes a public URL safe.**
3. Parse the webhook JSON; enqueue each event to SQS with a group ID derived from the sender (preserves per-conversation order)
4. Return 200 fast — most platforms only need a quick ack; the real reply happens later from home

See the platform-notes comment block at the top of the file for how to
adapt the signature check to Telegram or Meta instead of LINE's scheme.

### 2.4 Deploy: role + function + public URL
```bash
python deploy.py
```
Idempotent — safe to re-run any time you change `lambda_function.py`
or `config.env`. It:
1. Creates the execution role (`ROLE_NAME` in config.env) — trust policy allows only `lambda.amazonaws.com`; permissions are exactly three: `sqs:SendMessage` on your queue, `ssm:GetParameter` on your one parameter, CloudWatch logs.
2. Zips + creates/updates the function (small footprint: 128 MB / 10 s timeout by default — tune via config.env).
3. Creates a **Function URL** with auth `NONE` (public — that's what your webhook platform needs to reach; step 2.3's signature check does the actual authenticating) and prints the webhook URL.

Gotcha handled in-script: a freshly created IAM role takes ~10 s to
become assumable; the script retries `create-function` instead of
failing outright.

**What gets deployed, for manual reproduction:**

| Resource | Name (from config.env) | Key settings |
|---|---|---|
| SQS FIFO queue | `QUEUE_NAME` | content-based dedup ON, configurable retention |
| SSM parameter | `SECRET_PARAM_PATH` | SecureString, default KMS key |
| IAM role | `ROLE_NAME` | trust: `lambda.amazonaws.com`; inline policy: `sqs:SendMessage` (your queue), `ssm:GetParameter` (your parameter), CloudWatch logs |
| Lambda | `LAMBDA_NAME` | configurable runtime/memory/timeout, env `QUEUE_URL` + `SECRET_PARAM` + `SIG_HEADER`, handler `lambda_function.lambda_handler` |
| Function URL | auth type `NONE` (public) | resource policy: **two** public grants — see GOTCHAS |

### 2.5 Verify before going live
Three tests, all must pass, before you ever point a real webhook
console at the URL:
1. **Forged signature → `403 "bad signature"`** — proves the public URL is not an open door. `curl -X POST <function-url> -H "X-Line-Signature: forged" -d '{}'`
2. **Correctly-signed request → `200 "ok"`** — compute the HMAC yourself with the same secret your platform uses, and POST a minimal valid event payload for your platform.
3. **Queue check** — `aws sqs receive-message --queue-url <QUEUE_URL>` returns the event you just sent; delete the test message afterward with `aws sqs delete-message`.

---

## Part 3 — Home side: queue drainer + cutover

### 3.1 Design: loopback delivery
The drainer does NOT reimplement any bot logic. It reconstructs each
queued event as a webhook-shaped POST to your local server
(`LOCAL_WEBHOOK_URL` in config.env), **signed with the same secret**
your platform uses — so your bot processes relayed events through its
existing, already-tested code path. A marker header (`RELAY_HEADER_NAME`,
default `X-Relay: 1`) tells your server the event arrived via the
queue rather than directly, if your reply logic needs to know that
(see 3.2 below for why it might).

### 3.2 The reply-token / push economics pattern (platform-dependent)
Several chat platforms (LINE is the canonical example) give you two
ways to reply: a short-lived **reply token** bundled with the webhook
event (free, unlimited, but expires in roughly a minute) and a
**push API** (works any time, but rate-limited/quota-limited on free
tiers — LINE's free plan allows around 200 pushes/month).

Because a relayed event has already spent time traveling through
Lambda → SQS → your drainer, its reply token may have expired by the
time your bot handles it — especially for messages that backed up
during a home-machine outage. The pattern used in the reference
implementation:
- relayed event **younger than ~45 s** → use its still-valid reply token (free) — the normal case, since Lambda + SQS + drainer round-trip is usually well under a second
- relayed event **older** (backlog drained after downtime) → fall back to the push API for that one message

⚠️ **Without a freshness check, every relayed reply would use push,**
and a monthly push quota can be exhausted in days even at modest
traffic. If your platform doesn't have this reply-token/push
distinction (Telegram and Meta's APIs don't expire tokens the same
way), you can skip this pattern entirely.

### 3.3 The drainer
[`queue_drainer.py`](queue_drainer.py): boto3 long-poll (20 s) on the
FIFO queue → loopback POST (180 s timeout — LLM-backed bots can be
slow) → delete on success. Verdict logic: `ok` or a 4xx response →
delete the message (4xx means the payload itself is bad — a poison
message that would never succeed on retry, so it's logged and
dropped, never looped forever); 5xx or unreachable → leave the message
for automatic retry via SQS's visibility timeout. A heartbeat log line
fires every 10 minutes when the queue is idle so you can tell "quiet"
apart from "dead" at a glance.

### 3.4 Service installation

**Windows (NSSM):**
```bat
nssm install <ServiceName> "C:\Path\To\python.exe" "C:\path\to\queue_drainer.py"
nssm set <ServiceName> AppDirectory "C:\path\to\universal"
nssm set <ServiceName> AppEnvironmentExtra ^
    QUEUE_URL=https://sqs.<region>.amazonaws.com/<account>/<queue> ^
    LOCAL_WEBHOOK_URL=http://127.0.0.1:8000/webhook ^
    CHANNEL_SECRET_ENV_FILE=%USERPROFILE%\secrets\<bot>.env ^
    CHANNEL_SECRET_ENV_KEY=CHANNEL_SECRET ^
    DRAIN_LOG_FILE=%USERPROFILE%\logs\<bot>_queue_drain.log
nssm set <ServiceName> Description "Webhook relay queue drainer for <bot-name>"
nssm start <ServiceName>
```
If the service runs as `LocalSystem` rather than your own Windows
account, also set `AWS_SHARED_CREDENTIALS_FILE` and `AWS_CONFIG_FILE`
in `AppEnvironmentExtra` pointing at the credentials file created by
`aws configure` in Part 1.5 — LocalSystem has no `%USERPROFILE%\.aws`
of its own.

**Linux (systemd) — sample unit file:**
```ini
# /etc/systemd/system/<bot-name>-queue-drain.service
[Unit]
Description=Webhook relay queue drainer for <bot-name>
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=<your-linux-user>
WorkingDirectory=/path/to/universal
Environment=QUEUE_URL=https://sqs.<region>.amazonaws.com/<account>/<queue>
Environment=LOCAL_WEBHOOK_URL=http://127.0.0.1:8000/webhook
Environment=CHANNEL_SECRET_ENV_FILE=%h/secrets/<bot>.env
Environment=CHANNEL_SECRET_ENV_KEY=CHANNEL_SECRET
Environment=DRAIN_LOG_FILE=%h/logs/<bot>_queue_drain.log
ExecStart=/usr/bin/python3 /path/to/universal/queue_drainer.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now <bot-name>-queue-drain.service
journalctl -u <bot-name>-queue-drain.service -f
```

**Docker (either OS):** see [`Dockerfile`](Dockerfile) and
[`docker-compose.yml`](docker-compose.yml) — fill in the placeholders,
then `docker compose up -d --build`.

### 3.5 Shadow test (before cutover)
With your platform's console still pointed at your old direct
endpoint (tunnel, port-forward, whatever you use today), POST a
synthetic signed event straight at the **Lambda Function URL**. Full
path: Lambda → SQS → drainer → local server → your bot's normal reply
mechanism → delivered to your real test account. This proves the
whole relay end-to-end with zero production risk, since your live
webhook registration hasn't changed yet.

### 3.6 Cutover — watch for self-registering webhooks
Some bot frameworks **re-register their webhook URL on every startup**
(the reference LINE implementation does this). If yours does, any
manual change you make in the platform's console will be silently
reverted the next time your bot server restarts. Find the
registration code first; make the cutover *there* — e.g. a single
constant holding the active webhook URL, feeding the registration
call — not just in the console. Cutover = edit the constant + restart.
**Rollback = revert the constant + restart** (keep this one-liner
documented right next to the constant).

Verify the cutover twice: (1) your bot's own startup log should show
it registering the new (Lambda) URL, and (2) most platforms expose an
API to read back the currently registered webhook URL and to fire a
test request — use both to confirm independently of your own logs.

### 3.7 What you'll have changed on your machine, for reference
| File | Change |
|---|---|
| your bot's webhook-registration code | now points at the Lambda Function URL instead of the direct endpoint |
| your bot's reply-sending code | (only if your platform has the reply-token/push split) branches on event age per 3.2 |
| `queue_drainer.py` | new — the drainer, running as a service |
| your bot's dependency list | `+ boto3` |

---

## GOTCHAS

*(carried over from the reference implementation — read this before you debug the same things again)*

- **Public Function URL returns a bare 403 even with a "correct" policy (Oct 2025 AWS rule change):** a public (auth `NONE`) Lambda Function URL now requires **two** resource-policy grants — `lambda:InvokeFunctionUrl` (with the `FunctionUrlAuthType: NONE` condition) **and** plain `lambda:InvokeFunction` (no condition — the API rejects a condition flag on this particular action). Most tutorials predate this and list only the first grant; the symptom is AWS's own generic `403 Forbidden` at the URL edge — your function never even runs, so there's no CloudWatch log entry to chase. Debug technique that isolates it: `aws lambda invoke` directly succeeds while the public URL 403s → the block is at the URL authorization layer, not inside your function. `deploy.py` already applies both grants.
- **LINE SDK strictness (LINE-specific, but the general lesson applies to any strict-schema platform):** the v3 LINE SDK parser rejects events missing `deliveryContext`. Synthetic test events must include every schema field a real webhook carries (`deliveryContext`, `timestamp`, `mode`, etc.) — real platform-generated events always validate; only hand-built test payloads tend to miss fields.
- **Self-registering webhooks:** a bot that re-registers its webhook URL at startup will silently undo a console-side cutover on its next restart. See 3.6.
- **Push/reply-token quota economics (platforms that have this split):** prefer the free reply mechanism when the event is fresh, and reserve the rate-limited push mechanism for stale backlog only. See 3.2.
- **WSL2 Docker DNS resolution:** if containers can't resolve external hostnames (including AWS endpoints) under WSL2, the fix is usually adding a `daemon.json` with explicit DNS servers, e.g. `{"dns": ["8.8.8.8", "1.1.1.1"]}` in `%USERPROFILE%\.docker\daemon.json` (Docker Desktop) or `/etc/docker/daemon.json`, then restarting the Docker service/daemon.
- **Container-to-Windows-host networking:** a containerized drainer often cannot reach `127.0.0.1:<port>` on the Windows host directly under WSL2 (no NAT gateway route + firewall rule by default). Workaround used in the reference deployment: point `LOCAL_WEBHOOK_URL` at your bot's own public tunnel URL (Cloudflare Tunnel, ngrok, etc.) instead of a loopback address — see the comment in `docker-compose.yml`. A cleaner in-cluster host route is possible with k3s/host-gateway setups but is out of scope for a personal single-machine deployment.
- **The pre-2025 "12 months free / free t2.micro EC2" model no longer exists** for new AWS accounts. Plan around the initial credits (a matter of months) for experimentation, and the **always-free** service tier (Lambda, SQS, SSM, CloudWatch basics, IAM/Budgets) for anything you want to run forever at $0.
- **Creating an access key shows an "Alternatives recommended" banner** every time (`aws login`, CloudShell). See the callout in Part 1.5 for why both alternatives are wrong for a 24/7 unattended service.
- Cost sanity: everything this kit deploys is $0 at personal-use volume — Lambda, SQS, SSM standard parameters, and basic CloudWatch logging all sit comfortably inside the permanent always-free quotas.

---

*This is a generalized extraction of a working QI (Quiddity Innovations) implementation. Platform-specific names, account IDs, and paths have been replaced with config-driven placeholders — see `config.env.example`.*

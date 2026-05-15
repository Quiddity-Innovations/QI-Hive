# Wire OpenClaw (Tasuke + Kaze) to Cloudflare Workers AI

This requires a TTY-interactive flow OpenClaw enforces. Run these commands
in a real Windows Terminal / WSL bash window (NOT through Claude).

## Step 1 — Tasuke (main agent on `~/.openclaw/`)

```bash
# In WSL Ubuntu-24.04:
openclaw models auth login --provider cloudflare-ai-gateway

# When prompted, paste the values from C:/QIH/secrets/cloudflare_workers_ai.env:
#   Account ID: (CLOUDFLARE_ACCOUNT_ID)
#   API Key   : (CLOUDFLARE_API_TOKEN)
```

Then set Tasuke's primary model:

```bash
openclaw models set --agent main "cloudflare-ai-gateway/@cf/meta/llama-3.3-70b-instruct-fp8-fast"
openclaw models fallbacks add --agent main "ollama/gemma4:26b"
```

## Step 2 — Kaze (in the `kaze` profile on `~/.openclaw-kaze/`)

```bash
openclaw --profile kaze models auth login --provider cloudflare-ai-gateway
# same account ID + token

openclaw --profile kaze models set --agent kaze "cloudflare-ai-gateway/@cf/meta/llama-3.1-8b-instruct"
openclaw --profile kaze models fallbacks add --agent kaze "ollama/gemma4:26b"
```

## Step 3 — Restart both gateways

```bash
systemctl --user restart openclaw-gateway openclaw-gateway-kaze
```

## Step 4 — Verify

```bash
openclaw channels status            # Tasuke
openclaw --profile kaze channels status   # Kaze
```

Both should show `running, connected` for Telegram.

## Credentials source of truth

`C:/QIH/secrets/cloudflare_workers_ai.env` — sourced by Maia/Naya too.
Account ID + token + base URL are all there.

# Wire OpenClaw (Tasuke + Kaze) to Cloudflare Workers AI via AI Gateway

OpenClaw's `cloudflare-ai-gateway` plugin requires **three** values:
1. Account ID
2. AI Gateway slug (Cloudflare auto-creates one named `default` on first call)
3. API token with **both `Workers AI` AND `AI Gateway` permissions**

The existing `Workers AI` template-only token does NOT have `AI Gateway` perm.
We need to create or edit the token to add `AI Gateway: Read`.

## Step 0 — Update token to include AI Gateway permission

Easiest: on the AI Gateway dashboard page Renne is on, click **"Create authentication token"** — it creates a token with both perms pre-selected. Or:

1. Cloudflare dashboard → **My Profile** → **API Tokens**
2. Click the existing `Workers AI` token → **Edit**
3. **Add** another row: `Account` → `AI Gateway` → `Read`
4. **Continue to summary** → **Save**
5. Token value is unchanged — no need to re-paste

## Step 1 — In WSL Ubuntu, run for Tasuke

```bash
openclaw models auth login --provider cloudflare-ai-gateway
```

Three prompts will appear. Paste values from `C:/QIH/secrets/cloudflare_workers_ai.env`:

| Prompt | Paste |
|---|---|
| **Cloudflare Account ID** | `dfcfb986eed5be15a84257de2ae454da` |
| **Cloudflare AI Gateway ID** | `default` |
| **Cloudflare AI Gateway API key** | `$CLOUDFLARE_API_TOKEN` (from the env file) |

Then set model + fallback:

```bash
openclaw models set --agent main "cloudflare-ai-gateway/workers-ai/@cf/meta/llama-3.3-70b-instruct-fp8-fast"
openclaw models fallbacks add --agent main "ollama/gemma4:26b"
```

## Step 2 — Same for Kaze (different profile)

```bash
openclaw --profile kaze models auth login --provider cloudflare-ai-gateway
# Same 3 prompts, SAME values

openclaw --profile kaze models set --agent kaze "cloudflare-ai-gateway/workers-ai/@cf/meta/llama-3.1-8b-instruct"
openclaw --profile kaze models fallbacks add --agent kaze "ollama/gemma4:26b"
```

## Step 3 — Restart both gateways

```bash
systemctl --user restart openclaw-gateway openclaw-gateway-kaze
```

## Step 4 — Verify

```bash
openclaw channels status                  # Tasuke side
openclaw --profile kaze channels status   # Kaze side
```

Both should show `Telegram ... running, connected`. Post a message in Bot
Perspective to Tasuke or Kaze — they reply from Cloudflare's llama models.

## All-in-one (copy-paste into WSL after Step 0 is done)

```bash
echo "── Tasuke (default profile) ──"
openclaw models auth login --provider cloudflare-ai-gateway   # paste 3 values
openclaw models set --agent main "cloudflare-ai-gateway/workers-ai/@cf/meta/llama-3.3-70b-instruct-fp8-fast"
openclaw models fallbacks add --agent main "ollama/gemma4:26b" || true

echo "── Kaze (--profile kaze) ──"
openclaw --profile kaze models auth login --provider cloudflare-ai-gateway   # paste 3 values
openclaw --profile kaze models set --agent kaze "cloudflare-ai-gateway/workers-ai/@cf/meta/llama-3.1-8b-instruct"
openclaw --profile kaze models fallbacks add --agent kaze "ollama/gemma4:26b" || true

echo "── Restart ──"
systemctl --user restart openclaw-gateway openclaw-gateway-kaze
sleep 5
systemctl --user is-active openclaw-gateway openclaw-gateway-kaze
openclaw channels status | grep Telegram
openclaw --profile kaze channels status | grep Telegram
```

## What if it goes wrong

| Problem | Fix |
|---|---|
| Prompts hang / nothing happens | Run in a real Windows Terminal → Ubuntu-24.04 tab, NOT through Claude Code |
| `auth login` reports 401/forbidden | Token doesn't have AI Gateway perm yet (Step 0 missed) |
| `openclaw models set` rejects model name | Run `openclaw models list --provider cloudflare-ai-gateway` to see canonical IDs the plugin expects |
| Gateway won't restart | Restore `~/.openclaw/openclaw.json.bak-split-20260515`, run patch script, restart |

## Bottom line

The bots **work today** on local `gpt-oss-20b` with the QI wire filter catching leaks. Moving Tasuke + Kaze to Cloudflare's 70B/8B is an *upgrade*, not a fix — they're functional either way. So this is a "nice when you have 3 minutes at a real terminal" task, not "urgent."

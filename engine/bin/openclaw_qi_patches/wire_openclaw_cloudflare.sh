#!/usr/bin/env bash
# Wire Tasuke + Kaze (OpenClaw agents) to Cloudflare Workers AI.
# One-shot script — reads credentials, drives openclaw's interactive auth
# via expect, sets models + fallbacks for both profiles, restarts gateways.
#
# Run from WSL Ubuntu:
#   bash /mnt/c/QIH/engine/bin/openclaw_qi_patches/wire_openclaw_cloudflare.sh
# Or via the Windows wrapper:
#   C:\QIH\engine\bin\openclaw_qi_patches\wire_openclaw_cloudflare.bat

set -euo pipefail

ENV_FILE="/mnt/c/QIH/secrets/cloudflare_workers_ai.env"

# -------- Step 1: source credentials --------
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: credentials file not found: $ENV_FILE"
  exit 1
fi
# shellcheck disable=SC1090
source "$ENV_FILE"
: "${CLOUDFLARE_ACCOUNT_ID:?missing CLOUDFLARE_ACCOUNT_ID in $ENV_FILE}"
: "${CLOUDFLARE_API_TOKEN:?missing CLOUDFLARE_API_TOKEN in $ENV_FILE}"
echo "✓ credentials loaded (account ${CLOUDFLARE_ACCOUNT_ID:0:8}…)"

# -------- Step 2: ensure 'expect' is installed (silent if already there) --------
if ! command -v expect >/dev/null 2>&1; then
  echo "Installing 'expect' (needed to drive openclaw's interactive prompt)…"
  sudo apt-get install -y expect >/dev/null 2>&1 || {
    echo "WARN: couldn't install expect via apt. Falling back to direct auth-profile write."
    USE_EXPECT=0
  }
fi
: "${USE_EXPECT:=1}"

# -------- Helper: drive `openclaw models auth login` for a given profile --------
auth_login() {
  local profile_flag="$1"      # "" for default, "--profile kaze" for kaze
  if [[ "$USE_EXPECT" == "1" ]]; then
    expect <<EOF
log_user 0
set timeout 60
spawn -noecho bash -c "openclaw $profile_flag models auth login --provider cloudflare-ai-gateway"
expect {
  -re "(?i)account.?id" { send -- "${CLOUDFLARE_ACCOUNT_ID}\r"; exp_continue }
  -re "(?i)(token|api.?key)" { send -- "${CLOUDFLARE_API_TOKEN}\r"; exp_continue }
  eof { exit 0 }
  timeout { puts stderr "expect timeout"; exit 1 }
}
EOF
  else
    # Last-resort: paste-token via piped here-doc (less reliable)
    echo "Falling back to paste-token (no expect)…"
    echo "$CLOUDFLARE_API_TOKEN" | openclaw $profile_flag models auth paste-token \
        --provider cloudflare-ai-gateway || return 1
  fi
}

# -------- Step 3: Tasuke (default profile, `main` agent) --------
echo
echo "── Tasuke (default profile) ─────────────────────────────"
auth_login ""
echo "✓ Tasuke auth saved"
openclaw models set --agent main "cloudflare-ai-gateway/@cf/meta/llama-3.3-70b-instruct-fp8-fast"
echo "✓ Tasuke primary = llama-3.3-70b"
openclaw models fallbacks add --agent main "ollama/gemma4:26b" 2>/dev/null || true
echo "✓ Tasuke fallback = gemma4:26b"

# -------- Step 4: Kaze (kaze profile, `kaze` agent) --------
echo
echo "── Kaze (--profile kaze) ─────────────────────────────────"
auth_login "--profile kaze"
echo "✓ Kaze auth saved"
openclaw --profile kaze models set --agent kaze "cloudflare-ai-gateway/@cf/meta/llama-3.1-8b-instruct"
echo "✓ Kaze primary = llama-3.1-8b"
openclaw --profile kaze models fallbacks add --agent kaze "ollama/gemma4:26b" 2>/dev/null || true
echo "✓ Kaze fallback = gemma4:26b"

# -------- Step 5: restart both gateways --------
echo
echo "── Restarting gateways ───────────────────────────────────"
systemctl --user restart openclaw-gateway openclaw-gateway-kaze
sleep 6
echo "  openclaw-gateway:      $(systemctl --user is-active openclaw-gateway)"
echo "  openclaw-gateway-kaze: $(systemctl --user is-active openclaw-gateway-kaze)"

# -------- Step 6: verify --------
echo
echo "── Channel status ────────────────────────────────────────"
echo "[Tasuke 18789]"
openclaw channels status 2>&1 | grep -E "Telegram|LINE" | sed 's/^/  /'
echo "[Kaze 18790]"
openclaw --profile kaze channels status 2>&1 | grep -E "Telegram|LINE" | sed 's/^/  /'

echo
echo "✅ Done. Test now: post a message in Bot Perspective addressing Tasuke or Kaze."
echo "   They should respond from Cloudflare (llama-3.3-70b / llama-3.1-8b)."
echo "   If Cloudflare is unreachable, they auto-fallback to gemma4:26b local."

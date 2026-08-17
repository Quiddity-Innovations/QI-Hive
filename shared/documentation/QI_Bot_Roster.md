# QI Bot Roster — Roles, Channels, Providers

Last updated: 2026-05-14

This is the canonical roster of every Quiddity Innovations conversational bot — what each one does, where it lives, how to reach it, and who runs it under the hood.

---

## At a glance

| Bot | LINE OA | LINE Provider | Telegram | Brain | Owner |
|---|---|---|---|---|---|
| **Maia Quiddam** | `@c5gj…` (channel 2009508879) | **MAIA** | `@Maia_The_Assistant_Bot` (8610731233) | Maia FastAPI server (port 8001) | Renne |
| **Naya Patel** | `@914violz` (channel 2010090652) | **QUIDDAM** | `@Naya_qi_bot` (8667837858) | Naya Flask server (port 8002) | Renne |
| **Tasuke** | `@968uytdh` (channel 2009508884) | **QUIDDAM** | `@hyosukebot` (8271413034) | OpenClaw `tasuke-line` agent (LINE) + `main` agent (Telegram) | Renne |
| **Kaze Fujimori** | `@259zcsqp` (channel 2010092396) | **QUIDDAM** | `@KAZE_QI_BOT` (8760042185) | OpenClaw `kaze` agent (Telegram + LINE, dual-bound) | Renne |

> "Is she all under QUIDDAM?" → **Three of four are.** Maia Quiddam pre-dates the family and lives under the MAIA provider. That's fine — LINE providers are organizational, not functional. Migration would be a hassle for zero operational gain.

---

## 🌸 Maia Quiddam — the original

**Original role:** Multi-channel AI assistant for Quiddity Innovations. Started life as a LINE bot, expanded to Telegram, then Facebook Messenger / Instagram / WhatsApp planned. The flagship "named bot" of the QI template engine vision.

**Current responsibilities:**
- Handles user-facing chat across LINE + Telegram (and FB/IG/WhatsApp later)
- Multi-LLM chain: MiniMax → GPT-OSS → Qwen3 → Gemma3:27b → DeepSeek-R1 → Qwen3:4b
- Persona: warm, helpful, language-aware (Portuguese / English / Japanese / Spanish / French)
- Independence rewrite landed 2026-05-14 (commit `c98dc88`) — no more "boss" / "working for him" framing; Maia speaks as a peer with her own voice
- Admin firewall: only Renne (sender ID 260811037) can give DO commands; others get TALK only
- Group-chat awareness: cheer probability, chatter probability, approval workflow

**Where she lives:**
- Code: `C:/APPS/QI/maia_server.py` (FastAPI) — 8000+ lines
- DB: `C:/APPS/QI/maia.db` (config, sessions, group approvals, multi-channel state)
- Service: `QI_MaiaBot` (NSSM, port 8001)
- LINE webhook: `/maia/webhook` on the existing tunnel
- Telegram: webhook auto-registered on startup

**Notes:**
- ⚠️ **Independence rewrite still unloaded** — needs `nssm restart QI_MaiaBot` (elevated PowerShell) to take effect. The QI_Elevate broker can't reach the elevated service from the headless context.

---

## 📂 Naya Patel — the personal organizer

**Original role:** Renne's *private* personal AI assistant. Naya is **not** customer-facing — she runs operations on Renne's machine and his data.

**Current responsibilities:**
- File operations: scan drives, find duplicates (SHA-256 + fuzzy name match), USB cross-reference
- Cleanup planning + execution (advisor + executor modules) with safe-delete + undo
- Disk monitor, USB watcher, off-hours scheduler
- FileHQ integration (port 8200 internal) for file inventory
- Memory: folder insights, intent capture, relationships
- Reports: PDF / Word / Markdown generation
- Deferral: chat-driven task scheduling via Windows Task Scheduler
- Domains of expertise (in conversation): AI/ML, Physics, Programming, Networking, VMs/Docker, Languages
- Telegram polling (not webhook): `@Naya_qi_bot`
- LINE: NEW — Naya Patel `@914violz`, wired via `naya_line.py` module (~190 lines)

**Where she lives:**
- Code: `C:/APPS/NAYA/naya_server.py` (Flask) + `C:/APPS/NAYA/naya_line.py` (LINE handler)
- DB: `C:/APPS/NAYA/naya.db` + `naya_brain.db`
- Service: `QI_NayaBot` (NSSM, port 8002)
- LINE webhook: `/webhook/line` via STATIC NAMED tunnel → **https://naya-line.quiddityinnovations.com/webhook/line** (qi-naya ingress, port 8002). ⚠️ Re-register this URL in the LINE Developer Console.
- Secrets: `C:/APPS/NAYA/secrets/naya-line.env` (Win) + `~/.openclaw/secrets/naya-line.env` (WSL mirror, 0600)

**Persona:**
- Direct, precise, intellectually curious. Renne is technical — Naya never dumbs things down.
- No sycophantic filler ("Great question!", "Of course!"). Just answers.
- Concise by default, depth on request.

---

## 🎯 Tasuke — the senior operator

**Original role:** Operations + ops automation specialist. The "right hand" agent that takes commands from Renne and runs them through OpenClaw skills (npm-driven). Identity literally means "助" — *help / assist*.

**Current responsibilities:**
- The OpenClaw `main` agent (default agent for Telegram polling on `@hyosukebot`)
- Multi-bot interaction in groups: respects TALK / DO / PRIVATE permission tiers
- Open group access for news requests + URL-smart site management
- Cross-bot bridge participant (peer-bridge HMAC) — talks to Maia, Naya, and Kaze in shared chats
- Now: ALSO runs as `tasuke-line` agent on LINE (separate isolation, same identity files mirrored from `main`)

**Why two agents (main + tasuke-line)?**
Per Renne's "identity-as-feature" call (2026-05-14): a separate OpenClaw agent that "wears" the Tasuke identity for LINE. Same persona, same tool access, but isolated session state — so a garbled LINE conversation can't pollute the Telegram one. Both share the IDENTITY/TOOLS/SOUL files.

**Where he lives:**
- Telegram brain: `~/.openclaw/agents/main/` + workspace `~/.openclaw/workspace/` (shared workspace)
- LINE brain: `~/.openclaw/agents/tasuke-line/agent/` + workspace `~/.openclaw/agents/tasuke-line/workspace/` (mirrored from main)
- LINE webhook: routed by OpenClaw gateway at `127.0.0.1:18789/line/webhook` (account `tasuke-line`)
- Tunnel: STATIC NAMED → **https://oc-line.quiddityinnovations.com/line/webhook** (qi-kaze ingress, port 18789; shared with Kaze). ⚠️ Re-register in LINE console.
- Secrets: `C:/APPS/OC/secrets/tasuke-line.env` + WSL mirror

**Notes:**
- LINE display name is currently **"Tasuke"** (no surname). Rename to "Tasuke Hattori" available **on/after 2026-05-21** (LINE's 7-day rename cooldown blocks earlier change).
- Status message can carry "Hattori" subtitle in the meantime.

---

## 💨✨ Kaze Fujimori — the news prodigy

**Original role:** AI news specialist. Bubbly, hippie-streaked young journalist. Curates Renne's daily news digest twice a day, cross-cultural folklore mapping, mystery-and-wonder beat reporting.

**Updated bio (2026-05-14):**
- Surname: **Fujimori** (Japanese-Brazilian)
- Age: **19**
- Education: Harvard journalism graduate (finished at 15)
- Lives in: **New York City**
- Multilingual: Portuguese, English, Spanish, Japanese, French
- Vibe: Bubbly, light, curious, hippie streak. Sharp mind dressed in wonder, peace-and-love at heart.

**Current responsibilities:**
- Twice-daily news digests delivered to Renne via Telegram (and now LINE)
- Translation of news into the requester's language
- Q&A against the digest archive
- Member of the cross-bot bridge (peer-bridge) — converses with Tasuke, Maia, Naya in shared groups
- Handles news-related questions in groups; defers to siblings when others are addressed by name
- **Same agent on both channels** — Telegram `kaze` agent is now dual-bound: `Telegram kaze` + `LINE kaze-line` route to the same brain. No memory split.

**Where she lives:**
- Brain: `~/.openclaw/agents/kaze/` + workspace `~/.openclaw/agents/kaze/workspace/`
- IDENTITY: `~/.openclaw/agents/kaze/workspace/IDENTITY.md` (updated 2026-05-14 with new bio)
- LINE webhook: same OpenClaw gateway as Tasuke (`/line/webhook`, account `kaze-line`)
- Tunnel: shared with Tasuke → STATIC NAMED **https://oc-line.quiddityinnovations.com/line/webhook** (qi-kaze ingress, port 18789).
- Secrets: `C:/APPS/OC/secrets/kaze-line.env` + WSL mirror

---

## OpenClaw architecture in plain English

Both **Tasuke** and **Kaze** run inside OpenClaw (a Node.js agent runtime in WSL Ubuntu).

```
LINE phone app
   │
   │  HTTPS POST {events: [...]}
   ▼
Cloudflare named tunnel (oc-line.quiddityinnovations.com → qi-kaze, port 18789)
   │
   ▼
OpenClaw gateway (127.0.0.1:18789, /line/webhook)
   │  ── verify HMAC by trying every configured account secret
   │  ── routes Tasuke events → tasuke-line agent
   │  ── routes Kaze events → kaze agent
   ▼
Agent thinks (gemma4:26b via ollama, with IDENTITY/TOOLS/SOUL prompts)
   │
   ▼
Reply sent via LINE Messaging API (using the right channel's token)
```

**Naya** doesn't go through OpenClaw — she has her own Flask process and her own webhook handler (`naya_line.py`) inside `naya_server.py`.

**Maia** is the same architectural pattern as Naya — her own FastAPI process with built-in LINE handling.

---

## Reach them on LINE

Open LINE on your phone, search by basic ID, add as friend, message:

| Bot | LINE ID |
|---|---|
| Maia Quiddam | search the existing OA you already use |
| Naya Patel | `@914violz` |
| Tasuke | `@968uytdh` |
| Kaze Fujimori | `@259zcsqp` |

All four now in `chatMode=bot` (verified 2026-05-14 22:50 EDT) with webhook routing live.

---

## Tunnels (migrated to static named tunnels — 2026-06-20/23)

The quick (`*.trycloudflare.com`) tunnels are **retired**. All LINE webhooks now run on STATIC NAMED tunnels under `quiddityinnovations.com`, defined in `C:\QIH\engine\tunnels\tunnels.json` and provisioned by `migrate_named_tunnels.py`:

| Webhook | Permanent URL | tunnels.json entry → port |
|---|---|---|
| Naya LINE | `https://naya-line.quiddityinnovations.com/webhook/line` | qi-naya → 8002 |
| Tasuke + Kaze LINE | `https://oc-line.quiddityinnovations.com/line/webhook` | qi-kaze → 18789 |
| Maia LINE | `https://maia.quiddityinnovations.com` (+ `maia.quiddam.com`) | qi-maia → 8001 |

⚠️ **Action required (LINE platform, only Renne can do):** after `migrate_named_tunnels.py` provisions these, update each bot's **Webhook URL** in the LINE Developer Console to the permanent URL above. Until then the bots still answer on the old quick-tunnel URL only while that process happens to be alive.

# QI LLM Hub — User Guide

*Created 2026-07-02 · Lives on NEXUS (`C:\NEXUS`, service `QI_NEXUS`, port 8010) · Status: POC, LAN-only*

The QI LLM Hub is the **single gateway for every QI tool that talks to an LLM**.
Tools hold **zero API keys** — all keys live in `C:\NEXUS\secrets\nexus.env` (gitignored).
The hub fronts NEXUS's **13-provider free fleet** (Cerebras, Groq ×2, Cloudflare ×3,
Gemini, Mistral, OpenRouter, NVIDIA NIM ×2, local gemma4, OpenAI) with automatic fallback.

---

## 1. Endpoints

| Endpoint | Protocol | Use from |
|---|---|---|
| `POST http://127.0.0.1:8010/v1/chat/completions` | OpenAI-compatible | Anything that speaks OpenAI (openai SDK, LangChain, custom code) |
| `GET  http://127.0.0.1:8010/v1/models` | OpenAI-compatible | List routable model ids |
| `POST http://127.0.0.1:8010/api/chat` | **Ollama-native** | Tools built for Ollama — point their Ollama URL at `:8010`, done |
| `POST http://127.0.0.1:8010/api/generate` | **Ollama-native** | Same |
| `GET  http://127.0.0.1:8010/api/tags` | **Ollama-native** | Model dropdowns populate with hub providers |
| `GET  http://127.0.0.1:8010/hub/usage` | JSON | Per-app usage stats (who called, how much, how fast) |

**Connecting a new tool (OpenAI style):**
```
base_url = http://127.0.0.1:8010/v1
api_key  = anything (e.g. "qi-internal" — the hub ignores it)
model    = "auto"  (or a provider id: cerebras, groq, gemma4, cf_kimi, ...)
header   X-QI-App: <your-project-id>   ← so /hub/usage attributes your calls
```

**Connecting an Ollama-based tool:** change its Ollama URL from
`http://localhost:11434` to `http://127.0.0.1:8010`. Nothing else.

**Model routing rules:** a known provider id → that provider only. `auto` → the
fastest-first chain (order in `C:\NEXUS\api\hub.py` `DEFAULT_AUTO_ORDER`, override
via `nexus.json → hub.auto_order`). **Any unknown model string → routed as `auto`**
(so tools can keep sending their own model names like `qwen3:8b` or
`deepseek/deepseek-r1:free`).

---

## 2. Per-tool adoption status (2026-07-02)

| Tool | Status | How it connects | Toggle location |
|---|---|---|---|
| **Maia** (C:\QI) | ✅ **LIVE** | Hub-first in `llm_chat`, falls back to own chain | Maia Settings UI → "QI LLM Hub Mode" (or `system.llm_hub_enabled` in maia.db) |
| **Naya** (C:\NAYA) | ✅ **LIVE** | Hub-first in `_llm_call` (skipped for force_sonnet) | `system.llm_hub_enabled` in naya.db (not yet in its Settings UI) |
| **TUBESCOUT** | ✅ LIVE (pre-dates hub) | Calls NEXUS `/synthesize` directly | `config/tubescout.json → integration.nexus_base` |
| **Gamez / WC2026** | ✅ **LIVE** | AI analyst proxy → hub | `proxy/config.json → openrouter_base` (delete the line to revert) |
| **EasyFlow** | ✅ Ready (flip in UI) | Hub-first in extension chat + AI triage, falls back to configured provider | Extension Options → Settings → **"QI LLM Hub"** card → select "QI LLM Hub first" (reload extension once after update) |
| **QIH Brain** | ✅ **LIVE** (cascade restart 2026-07-02 14:19) | `openai_hub` provider (`qi_llm_hub` row, active) — verified generating via hub | `qi_brain.db → llm_providers` (role ordering still prefers local ollama for 'general'; the hub provider is selectable by id) |
| **CogniBase** | 🟡 Vendor available | `qi_llm_hub` vendor (openai_compatible) added to settings.json | CogniBase UI vendor selector, or `defaults.chat = "qi_llm_hub"` |
| **Retirement Analyzer** | 🟡 Provider available | `qi_llm_hub` entry in `config/ai_providers.json` | Set `"active": "qi_llm_hub"` |
| **M2V** | ⬜ Config-only flip | Ollama-native shim | `config/m2v.json → ollama.url` → `http://127.0.0.1:8010/api/generate` |
| **PersonalSong** | ⬜ Config-only flip | Ollama-native shim | `OLLAMA_BASE_URL` → `http://127.0.0.1:8010` |
| **Lottery Wiz** | ⬜ Config-only flip | Ollama-native shim | `OLLAMA_URL` env → `http://127.0.0.1:8010` |
| **MQ** | ⬜ Config-only flip (fallback path) | Ollama-native shim | `secrets/mq.env → OLLAMA_URL` → `http://127.0.0.1:8010` (Cloudflare stays primary) |
| **MailBrain** | ⬜ Config-only flip | Its "Custom" provider OR Ollama URL | Extension options → Custom API → base URL `http://127.0.0.1:8010/v1` |
| **MapSnap** | ⬜ Config-only flip | Ollama URL in its settings | Settings UI → Ollama URL → `http://127.0.0.1:8010` |
| **AutoPDF** | ⬜ Config-only flip | Ollama-native shim (`/api/tags` + `/api/generate`) | `PP-OCRv6/settings.json → ollamaHost` → `http://127.0.0.1:8010` |
| **Claude Voice** | ⬜ Config-only flip (ollama backend) | Ollama-native shim | `config.json → backends.ollama.host` → `http://127.0.0.1:8010` |
| CypherMiner, AkiyaScout, AvatarStudio, FileHQ, EasyFlow dashboard, claude_manager, QIB, QIP | — | No LLM calls | — |
| OpenClaw | Excluded | Claude-only (owner decision: Claude stays direct) | — |

⬜ = ready to flip whenever you want — one URL change, revert by changing it back.
The adoption pattern for anything new: **try hub first, fall back to the tool's
direct path** — hub mode must never make a tool less reliable.

---

## 3. Caveats & rules

- **LAN-only. Never tunnel port 8010.** The hub has no auth (POC). Adding a token
  check is the prerequisite for any external exposure.
- **Shared quotas:** every tool draws from the same free tiers. Watch
  `GET /hub/usage` — if one app dominates, throttle it or pin it to a provider.
- **OpenRouter cap:** ~50 req/day free. **Gemini:** enabling billing on the Google
  account kills the free tier. **NVIDIA NIM:** the trial API logs prompts/outputs —
  keep confidential content on local `gemma4` or other channels.
- **Streaming is emulated** (single chunk). Fine for chat UIs; not true token streaming.
- **Key rotation:** edit `C:\NEXUS\secrets\nexus.env`, restart `QI_NEXUS`. That's it —
  no tool needs touching.

## 4. Troubleshooting

| Symptom | Check |
|---|---|
| Tool gets connection refused | `curl http://127.0.0.1:8010/health` → restart `QI_NEXUS` (elevated) |
| 502 "All candidate providers failed" | `GET /hub/usage` recent errors; `C:\NEXUS\LOGS\nexus_service.log` |
| Slow responses | A provider in the auto chain is degraded; check dispatcher log; providers fall back automatically |
| Who is burning quota? | `GET http://127.0.0.1:8010/hub/usage` → `per_app` |

*Related: `C:\QIH\ecosystem\QI_Ecosystem_Map.md` (integration contracts) ·
NEXUS commits 5e81237, fdcfc7a · Session summaries 2026-07-02 in
`C:\QIH\shared\documentation\session_summaries\`*

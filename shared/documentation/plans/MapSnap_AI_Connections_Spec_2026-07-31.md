# MapSnap — AI Connections: Agreed Design Spec

**Date:** 2026-07-31 · **Decided by:** Renne · **Status:** Agreed, implementation deferred until the BU-edition merge
**Implements after:** Renne delivers the laptop-fixed BU edition → three-way compare (laptop vs `C:\APPS\MapSnap` main vs BU kit) → these features are built on the merged latest, then shipped to BOTH editions.

---

## Governing principle (Renne, 2026-07-31)

Every AI connection is **independent**:
1. If a connection is **configured**, it shows as **active** — regardless of whether any other connection (especially Ollama) exists or is running.
2. An active connection is only **available in chat if Renne says so** — per-connection `show_in_chat` discretion (already implemented; keep).
3. A connection that exposes **multiple LLMs** must **list its available models** and let the admin pick which ones appear in the chat dropdown (per-model allowlist).

The known picker bug (everything gated on `/api/ollama/status` at `build_browser.py:~7945`, secondary picker ~6446) violates rule 1 and is being fixed by Renne on the laptop BU copy — not part of this spec, but this spec assumes that fix is in.

---

## Feature 1 — Direct API provider catalog ("Add provider" picker)

**Today:** `_DAPI_DEFS` has 5 entries (Anthropic, OpenAI, Google, xAI, Custom); named providers replace-on-add; each entry stores ONE model.

**Agreed design:**
- Under Settings → AI → Direct API providers: an **Add** button opens a picker of the common major providers. Selecting one **prefills label, default base URL, wire format, and an example model id** — only the API key (and optional overrides) are left blank for the user to fill in and save.
- A **Custom** option remains for anything not in the catalog (OpenAI-compatible endpoint: user supplies label + base URL + key).
- Catalog to include US majors **and** major non-US providers (Renne explicitly wants e.g. Chinese models available):

| Provider | Default base URL | Wire format | Example model |
|---|---|---|---|
| Anthropic (Claude) | https://api.anthropic.com | anthropic | claude-opus-4-8 |
| OpenAI (GPT) | https://api.openai.com/v1 | openai | gpt-4o |
| Google (Gemini) | https://generativelanguage.googleapis.com/v1beta | gemini | gemini-2.5-pro |
| xAI (Grok) | https://api.x.ai/v1 | openai | grok-2-latest |
| Mistral | https://api.mistral.ai/v1 | openai | mistral-large-latest |
| Groq (fast inference) | https://api.groq.com/openai/v1 | openai | llama-3.3-70b-versatile |
| DeepSeek | https://api.deepseek.com | openai | deepseek-chat |
| Alibaba Qwen (DashScope) | https://dashscope.aliyuncs.com/compatible-mode/v1 | openai | qwen-max |
| Moonshot (Kimi) | https://api.moonshot.cn/v1 | openai | moonshot-v1-8k |
| Zhipu (GLM) | https://open.bigmodel.cn/api/paas/v4 | openai | glm-4-plus |
| MiniMax | https://api.minimax.chat/v1 | openai | MiniMax-Text-01 |
| Custom (OpenAI-compatible) | — (user supplies) | openai | — |

  *Catalog list is a starting point — verify current URLs/models at build time; most non-US providers speak the OpenAI wire format, so the existing one-adapter design holds.*
- **Multi-model per provider** (closes the single-model gap): each provider entry stores a `models: []` list instead of one `model` string. UI = pinned-model list with add/remove (same pattern as OpenRouter pinned models), and where the provider exposes a `/models` endpoint, a **Browse** action fetches the live list to pick from. Each pinned model appears as its own chat-picker entry (`direct/<provider>/<model>`), still governed by the entry's `show_in_chat`.
- Back-compat: existing single-`model` entries migrate to `models:[model]` on load; server routing `direct/<provider>/<model>` already carries the model id, so no server-side wire change.

## Feature 2 — Unified AI Connections screen

One screen (Settings → AI → **Connections**, top of the AI section) listing **every possible connection** with live status — the single place to see and control the whole AI stack:

| Column | Content |
|---|---|
| Connection | Ollama (local) · OpenRouter · each Direct API provider · Claude (subscription CLI) · [discuss: NEXUS LLM Hub — see note] |
| Configured | key/URL present (masked) |
| Status | live probe, green/amber/red dot + Test button: Ollama `/api/tags` · OpenRouter key/account check (exists today) · Direct `/models` ping (or 1-token no-op where no models endpoint) · Claude CLI version check |
| Active | per-connection enable toggle |
| Show in chat | the existing `show_in_chat` switch, surfaced here |
| Models in chat | count of allowlisted models, click-through to the per-connection model picker |
| Last checked | timestamp of last probe |

Behaviors:
- Probes are **non-blocking and independent** — one connection timing out never delays or hides the others (same principle as the picker fix).
- The chat dropdown becomes a pure **projection of this screen**: union of (active ∧ show_in_chat ∧ per-model allowlist) across all connections. One source of truth ends the class of "configured but invisible" bugs.
- The status dot in the chat header goes red only when **zero** connections are available; Ollama-down with cloud providers active = amber note, not a dead picker.
- BU edition inherits the same screen; egress guardrail continues to govern which connections may actually receive regulated data (a connection can be chat-visible yet blocked by policy at send time, exactly as today).

**Discussion point for the merge session (not decided):** whether the NEXUS LLM Hub (`http://127.0.0.1:8010/v1`, MapSnap is on the ready-to-flip list) appears here as one more connection type — it fits the model (one URL, many models) and would make MapSnap consistent with the ecosystem hub standard. Main-edition only; BU edition ships without it.

---

## Sequencing

1. **Now:** nothing changes in `C:\APPS\MapSnap` (freeze holds while Renne fixes the picker on the laptop).
2. **BU version delivered:** three-way compare → merge latest into main + BU kit (picker independence fix lands here).
3. **Then:** implement Feature 1 + Feature 2 on the merged base → rebuild browser HTML → ship to both editions.

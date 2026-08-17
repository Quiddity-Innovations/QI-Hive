# NEXUS — Neural Exchange and Unified Synthesis

## What is NEXUS?

NEXUS is the **AI orchestration backbone** of the Quiddity Innovations ecosystem. It takes a single
prompt, fans it out to multiple AI providers **at the same time**, then synthesises every response
into one superior, unified answer. Where Maia and Naya each run a sequential failover chain
(try model 1, fall back to model 2…), NEXUS does the opposite — it asks everyone at once and
combines the best of all of them.

NEXUS is not a user-facing chatbot. It is a **shared intelligence service**: a FastAPI backbone
(port 8010) with a full Gradio operator console (port 7880) that any QI project can call when a
question deserves more than one model's opinion. Its tagline — *Neural Exchange and Unified
Synthesis* — is exactly what it does: exchange neural perspectives, then unify them.

## The Problem We Solve

- **Single-model bias.** Every model has blind spots. Picking one (GPT, Claude, Gemini, a local
  Llama) means discarding the perspective of all the others. NEXUS keeps all of them on the table.
- **No systematic way to compare AIs.** Judging which model is best for a given task — reasoning,
  code, summarisation — used to be manual and anecdotal. NEXUS's Judge and Bench modules make it
  measurable and repeatable.
- **Every project reinventing provider plumbing.** Without a shared backbone, each QI app would
  re-implement provider management, timeouts, failover, and key handling. NEXUS centralises all of
  it behind one REST contract.
- **Staying current with a fast-moving field.** AI news moves daily. Scout turns that firehose into
  a deduplicated, AI-synthesised daily digest so the team never falls behind.

## Our Approach

NEXUS is built from four modules around a config-driven core. **No model name or key is ever
hardcoded** — providers, topics, thresholds, and synthesis settings all live in JSON config and the
SQLite DB, hot-reloadable from the Settings UI.

### 1. Core — the orchestrator

The **Dispatcher** (`core/dispatcher.py`) sends the prompt to every enabled provider concurrently
with Python `asyncio`, respecting a per-provider timeout, and collects each `ProviderResponse` as it
lands. One misbehaving adapter can never abort the whole run. Three routing modes:

- **Parallel** (default) — all providers answer at once; the synthesiser merges them.
- **Chain** — provider 1 answers, provider 2 improves it, and so on down the line.
- **Iterative** — multiple synthesis rounds (capped at 3) that critique and refine the answer.

The **Synthesizer** (`core/synthesizer.py`) feeds all successful responses to a configured synthesis
model and returns one answer, under strict rules that preserve every table and code block. The
primary synthesiser is the **local Gemma 4 26B** (via Ollama, kept warm to avoid cold starts), with
**ChatGPT** as fallback.

### 2. Scout — autonomous AI research daemon

Scout crawls configured **topics** (RSS, Reddit, Hacker News) on an APScheduler interval (default 6
hours, per-topic overridable), deduplicates with `rapidfuzz`, and writes an AI-synthesised daily
digest to the DB and a `.docx`. It currently holds **13,000+ collected news items** across multiple
topics, and feeds the TubeScout project's YouTube tracking.

### 3. Judge / Scorer — quality evaluation

After dispatch, an optional **Judge** scores each response 1–10 on Clarity, Accuracy and Depth. Two
modes: **simple** (one LLM-as-judge call returning a markdown table) and **deepeval** (DeepEval
G-Eval — three structured metrics per response with reasons). The judge model is any registered
provider; the default judge is **Groq**.

### 4. Bench — LLM regression suites

Bench runs a fixed battery of prompts (a "suite") against any set of providers, optionally scores
each response, persists the run, and tracks scores over time — so when a model is swapped or
upgraded you can catch regressions. `GET /bench/recommend` returns the best provider for a use case
by aggregate historical score.

## The LLM Provider Chain

Providers are defined in `config/providers.json` and loaded at runtime. Current state:

| Provider | Adapter | Model | Status |
|---|---|---|---|
| **ChatGPT** | `openai_codex` | gpt-4o-mini | ✅ Enabled — dispatch + synthesis fallback |
| **Groq** | `groq_provider` | llama-3.3-70b-versatile | ✅ Enabled — also default judge |
| **Mistral** | `mistral_provider` | mistral-small-latest | ✅ Enabled |
| **Ollama (local)** | `ollama` | qwen3:4b | ✅ Enabled — fast local, Scout synthesis |
| **Gemma 4 26B (local)** | `ollama` | gemma4:26b | ✅ Enabled — **primary synthesiser** |
| **Cloudflare AI** | `cloudflare` | llama-3.3-70b-fp8-fast | ✅ Enabled |
| **Gemini** | `gemini` | gemini-2.0-flash | ⚠️ Disabled — free quota exhausted; replaced by local Gemma 4 |
| **Grok** | `grok_provider` | grok-3-mini | ⚠️ Disabled — needs xAI key |
| Anthropic, Azure, Bedrock, Cohere, Together, Fireworks, NVIDIA NIM, OpenRouter, Perplexity | various | — | 🗓️ Pre-wired — add key + enable |

A four-tier **inference-mode** system (Fast / Balanced / Thinking / Deep Reasoning) maps onto each
model's real reasoning capability, with mode-aware timeout multipliers (`core/inference_modes.py`).

## Who Uses NEXUS?

| Role | How they interact |
|---|---|
| **Developers / researchers** | `POST /synthesize` on the API (8010), or the Gradio console (7880) |
| **Operators (the owner)** | Gradio UI: Orchestrator, Scout, Batch & Schedule, Expert Panel, Curate & Export, Bench, Settings, Help |
| **QI ecosystem projects** | Maia, Naya, FileHQ, OpenClaw call `/synthesize`, `/scout/digest`, `/bench/recommend` |
| **TubeScout** | Reuses Scout's topic engine to track YouTube channels (726+ and 1,365+ items in two topics) |
| **Scout scheduler** | Autonomous — runs per-topic crawl→dedup→digest cycles on APScheduler intervals |
| **Synthesis keep-warm** | Background job re-pings the local 26B synthesiser every 20 min so it never cold-starts |

## Current Build Status (June 2026)

NEXUS is in **active development / deployed** — running as the `QI_NEXUS` NSSM service
(API 8010, UI 7880), publicly reachable via the `QI_NEXUSTunnel` Cloudflare tunnel.

| Area | Status |
|---|---|
| Multi-AI parallel dispatch (Dispatcher) | ✅ Live |
| Routing modes: Parallel / Chain / Iterative | ✅ Live |
| Response synthesis (local Gemma 4 26B primary, ChatGPT fallback) | ✅ Live |
| Streaming synthesis (Server-Sent Events) | ✅ Live |
| Inference modes (Fast / Balanced / Thinking / Deep) | ✅ Live |
| Judge — simple LLM-as-judge mode | ✅ Live |
| Scorer — DeepEval G-Eval mode (default) | ✅ Live |
| Bench — LLM regression suites + recommendation | ✅ Live |
| Scout — autonomous multi-topic AI digest (13k+ items) | ✅ Live |
| Expert Panel — 26 expert personas | ✅ Live |
| Batch & Schedule — prompt batches + recurring jobs | ✅ Live |
| Curate & Export + RAG knowledge base (ChromaDB) | ✅ Live |
| FastAPI REST API (60+ endpoints) on 8010 | ✅ Live |
| Gradio operator console (8 top-level tabs) on 7880 | ✅ Live |
| QI ecosystem integration (CORS via qi_registry) | ✅ Live |
| `QI_NEXUS` NSSM service + Cloudflare tunnel | ✅ Live |
| Gemini cloud provider | ⚠️ Disabled — free quota exhausted (re-enable on key renewal) |
| QI Brain session/decision logging | 🗓️ Planned |
| API auth + rate limiting (multi-user release) | 🗓️ Planned |

## The Vision

NEXUS is the **AI engine module** of the eventual unified QI platform. Today it is a standalone
backbone; tomorrow it is the layer every QI product calls whenever a task needs frontier-grade
reasoning, cross-model consensus, measured model selection, or fresh field awareness. The roadmap
points at three things: **cost-aware adaptive routing** (send each task to the cheapest competent
model), **deeper Brain integration** (every synthesis logged for cross-project memory), and a
**hardened multi-user release** (auth, rate limits, session isolation) so NEXUS can serve beyond the
local machine.

---
*This page is editable at `C:\APPS\NEXUS\INTRO\status_intro.md` — save and click Refresh to update.*

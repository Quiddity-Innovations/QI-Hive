# The Free Poly-Cloud Blueprint
### Recreating a desktop-hosted app ecosystem across free cloud tiers — AWS + Cloudflare + OpenRouter + friends

**Purpose:** master plan for running QI-style applications at $0/month by combining the free tiers of multiple providers, with LLM inference deliberately kept OUT of AWS (no paid storage/compute) via external free LLM sources and the home desktop as a first-class provider.
**Companion to:** [AWS_Free_Tier_Setup_Guide.md](AWS_Free_Tier_Setup_Guide.md) (the hands-on implementation track)
**Status:** vision/roadmap — drafted 2026-07-30, preliminary conversation with Renne.

---

## Core principle

> **Every provider's free tier is a budget. Place each workload on the platform whose free tier fits it best.**

No single provider gives away a full desktop-equivalent. The combination does. The architecture that emerges is event-driven (nothing idles), multi-provider (nothing depends on one company's generosity), and hybrid (the home GPU remains the best-quality, most-private compute — reached via tunnel, treated as "just another provider").

## The LLM answer: a 5-rung fallback chain

Any cloud-hosted app (e.g., AWS-Maia) queries LLMs in quality order, falling through on timeout/rate-limit:

| Rung | Provider | Free allowance | Role |
|---|---|---|---|
| 1 | **Home desktop GPU** via Cloudflare Tunnel + auth token (Ollama/NEXUS: Gemma3-27B etc.) | Own hardware | Best quality + privacy; primary when machine is up |
| 2 | **Cloudflare Workers AI** | ~10,000 neurons/day | Free GPU inference (Llama family), no new account needed |
| 3 | **OpenRouter `:free` models** | Daily request caps | Model variety (DeepSeek, Qwen, Llama) |
| 4 | **Google Gemini Flash / Groq** free tiers | ~1,500 req/day (Gemini) | High-ceiling safety net |
| 5 | **Tiny CPU model inside AWS Lambda** (1–2B quantized, llama.cpp) | ~1,000–1,500 replies/mo within Lambda free compute | Last resort — the bot is never fully down |

Design consequences: per-user conversation state must live in a cloud DB (any rung can serve the next message); provider adapters share one interface so rungs are pluggable; secrets (API keys, tunnel token) live in SSM Parameter Store.
⚠️ Privacy trade-off (owner decision, flagged 2026-07-30): rungs 2–4 send conversation content to third parties. Rung 1 first = most traffic stays private; a "local-only" policy flag can restrict sensitive bots to rung 1 + rung 5.

## Desktop-to-cloud mapping table

| Desktop component | Free cloud home | Notes |
|---|---|---|
| FastAPI services / bot logic | AWS Lambda (1M req/mo) + Cloudflare Workers (100k req/day) | Event-driven rewrite; nothing idles |
| Dashboards / UIs / demos | Cloudflare Pages or S3+CloudFront (1 TB/mo) | Static + API calls; Pages has git-push deploys |
| SQLite databases | **Cloudflare D1** (IS SQLite, 5 GB free) · DynamoDB (25 GB) | D1 = smallest mental migration from local SQLite |
| File/media storage | Cloudflare R2 (10 GB, zero egress) · S3 | R2 for frequently-downloaded assets |
| ChromaDB / RAG | Cloudflare Vectorize free tier · MiniLM embeddings inside Lambda + DynamoDB | Personal corpus sizes fit easily |
| Task Scheduler jobs | EventBridge · CF Cron Triggers · GitHub Actions schedules | Three independent free cron systems |
| NSSM always-on services | ❌ no free equivalent — reshape into event-driven, or keep at home | The one structural exclusion |
| Ollama / NEXUS LLM chain | The 5-rung chain above | LLM weights never stored in AWS |
| Cloudflare Tunnels | Keep; add **Cloudflare Access** (free ≤50 users) for auth on private endpoints | Already in use at QI |
| Git + CI/CD | GitHub + Actions (2,000 min/mo) | Auto-deploy Workers/Pages/Lambda on push |
| Monitoring | Lambda watchdog (external eye) + UptimeRobot free | Never monitor a machine only from itself |
| Email in/out | Cloudflare Email Routing (free) · SES | For bot notifications |

## Honest costs (not dollars)

1. **Complexity:** five consoles, five auth systems, five sets of quirks — this is the tuition of the learning goal.
2. **Provider risk:** free tiers change/vanish. Antidote = the chain/adapter pattern everywhere: no capability may depend on exactly one provider.
3. **Rewrite effort:** always-on server code must become event-driven handlers. That rewrite IS the curriculum.

## Learning roadmap (each phase ⇒ guide + bat files + universal pack + video)

| Phase | Deliverable | Skills unlocked |
|---|---|---|
| **3 (current)** | Maia relay home-side drainer + LINE cutover | SQS consumers, cloud↔home bridging, NSSM+AWS |
| **4** | Cloud-brain Lambda: 5-rung chain as Maia's degraded mode | Multi-provider APIs, adapters, secrets, graceful degradation |
| **5** | Cloudflare pillar: port one small app (dashboard or TubeScout fetch) to Workers/Pages/D1/R2 | The entire second ecosystem |
| **6** | Reference poly-cloud app: one chosen app rebuilt across AWS+CF+GitHub free tiers | The reusable template for all future ambitious projects |

## Track C — Containers & Kubernetes (added 2026-07-30)

**Cost reality:** Docker is free everywhere (Docker Desktop personal / WSL2). Kubernetes is NOT free on AWS (EKS control plane ≈ $73/mo) — AWS is where container *skills* get used (Lambda container images, free), not where a cluster runs. Free clusters live in exactly two places: **the desktop** (k3s or kind inside WSL2 — full real cluster, $0) and **Oracle Cloud always-free** (4 ARM cores / 24 GB RAM, permanent — the industry's one genuinely free cloud VM deal, big enough for an internet-facing k3s cluster).

**Why it makes the environment dynamic:** replaces the static NSSM model with declarative, self-healing infrastructure — crashed pods restart in seconds; the entire environment is YAML in git (GitOps: push → cluster converges); machine rebuilds become "install k3s, point at repo." **Strategic alignment:** the QI template-engine vision (one codebase → infinite named bots) IS the Helm-chart model — one chart = "a bot," each instance parameterized by values.yaml (name, personality, LLM chain, secrets). New bot = one command.

| Stage | Deliverable | Skills |
|---|---|---|
| C1 | WSL2 + Docker; containerize the Phase-3 queue drainer (first QI container) | images, Dockerfiles, volumes, secrets |
| C2 | docker compose for a small QI stack | multi-container networking |
| C3 | k3s in WSL2; drainer + dashboard run in parallel with NSSM (prod untouched until proven) | pods, deployments, services, CronJobs |
| C4 | Helm chart "QI bot" — Maia instance #1 + a second named bot as proof | templating; the multi-bot engine realized |
| C5 | GitOps: GitHub Actions builds images → cluster auto-syncs from repo | CI/CD, the "dynamic" payoff |
| C6 | Oracle always-free ARM k3s = free cloud cluster in the poly-cloud | real ops, ARM builds, multi-cloud |

Guardrails: cluster = parallel learning env first (existing NSSM production stays authoritative until a service is proven); GPU/Ollama containerization last (WSL2 GPU passthrough exists); Track C interleaves with Phases 3–6 without delaying the AWS relay. Each stage gets the standard treatment: guide + bat files + universal pack + video.

## Accounts to create when we get there (all free)

- Cloudflare: already exists (tunnels) — Workers/Pages/D1/R2/Workers AI are toggles on the same account
- OpenRouter: free account + API key
- Google AI Studio (Gemini API key) · Groq Cloud: free accounts
- GitHub: already exists
- UptimeRobot (optional): free account

---
*Drafted by Claude (QI Hive) with Renne Santiago — Quiddity Innovations, 2026-07-30. Living document; revise as free tiers and providers evolve.*

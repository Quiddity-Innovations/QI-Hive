# QI Free Cloud — Master Implementation Plan
### Rebuilding the desktop environment as a learning-first, automation-first, $0/month poly-cloud

**Owner:** Renne Santiago · **Executor:** Claude (QI Hive) · **Drafted:** 2026-07-30
**Dual mandate:** (1) hands-on learning of every technology touched; (2) every deployment fully scripted so it can be replicated for future projects, clients, or rebuilds.
**Companion documents:** [AWS_Free_Tier_Setup_Guide.md](AWS_Free_Tier_Setup_Guide.md) (hands-on track, Parts 1–2 complete) · [Free_PolyCloud_Blueprint.md](Free_PolyCloud_Blueprint.md) (architecture & rationale)

---

## 1. Banked assets (M0 — complete, 2026-07-30)

Everything below is built, verified, committed to git, and idle-safe at $0. Reusable at any time.

| Asset | Location | State |
|---|---|---|
| AWS account, hardened (root MFA, IAM user, scoped policies, $0.01 budget alarm) | account 103140669477, us-east-1 | ✅ live |
| SQS FIFO queue `qi-maia-events.fifo` (4-day retention, dedup) | AWS | ✅ live, $0 idle |
| Lambda `qi-maia-webhook` + public Function URL (LINE signature verification) | AWS | ✅ live, verified 3/3 tests |
| Secret `/qi/maia/line_channel_secret` | AWS SSM (SecureString) | ✅ stored |
| IAM role `qi-maia-webhook-role` (3-permission least privilege) | AWS | ✅ live |
| Relay code + idempotent full-Part-2 deploy script | `C:\QI\TOOLS\aws_relay\` | ✅ committed (QI repo) |
| Setup guide Parts 0–2 + gotchas log + component BOM | `guides\AWS_Free_Tier_Setup_Guide.md` | ✅ committed (QIH repo) |
| Automation bats: step 1.7 admin grant, Part 2 one-shot deploy | `guides\AWS_Setup_*.bat` + `qi_role_policy.json` | ✅ committed |
| Vision docs: poly-cloud blueprint incl. Track C | `guides\Free_PolyCloud_Blueprint.md` | ✅ committed |

**Key dates:** AWS free-plan window ≈ 2026-07-30 → **≈ 2027-01-30** (6 months / credits). Everything *permanent* uses always-free services only; the credit window is reserved for disposable learning experiments (EC2/VPC exploration, Bedrock tasting).

---

## 2. The deliverables standard ("the treatment")

Every milestone below ships all five of these — no exceptions. This is what makes the plan a curriculum and a product at once:

1. **Guide chapter** — appended to the relevant guide: exact steps, component BOM updates, and every gotcha hit (the gotchas are the tutorial gold).
2. **Automation scripts** — idempotent, re-runnable (`deploy_*.py` pattern) + a double-clickable `.bat` wrapper. Manual console steps allowed only where AWS/vendor security requires a human (and then documented click-by-click).
3. **Universal pack contribution** — parameterized, non-QI version of the milestone's scripts/config (placeholders: account ID, bot name, secret paths) accumulated in a `universal\` folder; consolidated at M8.
4. **Verification script** — automated pass/fail tests proving the milestone works (the Part 2.5 pattern: prove it, don't hope it).
5. **Video segment** — storyboard notes captured at milestone completion; videos produced at the three video gates (see §6).

**Automation principles:** scripts over clicks; idempotent always; secrets only in env files/SSM (never code, never chat); every resource named with the `qi-` prefix and registered in `qi_registry.json` (`aws` section — created at M1); every milestone ends with a git commit in the owning repo.

---

## 3. Milestone roadmap

Two interleaved tracks — AWS/poly-cloud (M1, M3, M5, M8) and containers (M2, M4, M6, M7, M9) — ordered so each skill feeds the next. One milestone ≈ 1–3 working sessions.

### M1 — Maia relay goes live (AWS Phase 3) 🎯 NEXT
The home machine learns to drain the cloud mailbox; Maia stops losing messages.
- **Steps:** study `maia_server.py` event handling → build `queue_drainer.py` (boto3 long-poll → hand events to Maia's existing handler → reply via LINE Push API) → install as `QI_MaiaQueueDrain` (NSSM, per-project nssm.exe, registered in QI_Service_Registry.md) → shadow test (tunnel stays primary; drainer processes synthetic + real queued events) → LINE console cutover → 48 h observation → rollback procedure documented.
- **New components:** boto3 on desktop. **Cloud cost:** $0.
- **Done when:** a LINE message sent while `maia_server` is stopped is answered after it restarts; cutover + rollback both proven.
- **Skills:** SQS consumers, visibility timeouts, push-vs-reply APIs, cloud↔home bridging.

### M2 — First container (Track C1–C2)
- **Steps:** enable WSL2 → install Docker (Desktop personal or engine-in-WSL2) → write Dockerfile for the M1 drainer → run it as a container (secrets via env-file, logs to mounted volume) → `docker compose` adding a second service (e.g., a log-viewer or healthcheck sidecar) → side-by-side soak vs NSSM version → decide which stays primary.
- **Done when:** containerized drainer processes a real queued message end-to-end.
- **Skills:** images, layers, volumes, env/secret injection, compose networking. **Guide:** new `Docker_Foundations_Guide.md`.

### M3 — Cloud brain: the 5-rung LLM chain (AWS Phase 4)
Maia gains a degraded-but-alive mode when the desktop is offline.
- **Steps:** create free accounts (OpenRouter, Google AI Studio, Groq; Workers AI on existing CF account) → store keys in SSM → expose desktop Ollama/NEXUS via authenticated CF tunnel (rung 1) → build provider-adapter module (one interface, five implementations) → `qi-maia-brain-cloud` Lambda: consume queue when drainer is absent OR be called by it → conversation state to DynamoDB → chain testing (kill rungs one by one, watch fallback) → per-bot `local_only` privacy flag (Renne's pending decision, implemented as config).
- **Done when:** with the desktop fully off, a LINE message gets an answer from a cloud rung; with desktop on, rung 1 answers.
- **Skills:** multi-provider LLM APIs, adapter pattern, DynamoDB, graceful degradation.

### M4 — Local Kubernetes (Track C3)
- **Steps:** k3s (or kind) in WSL2 → deploy the M2 containers as Deployments with Services → convert one Task-Scheduler job to a CronJob → break things on purpose (kill pods, kill node) and watch self-healing → cluster runs PARALLEL to NSSM production (standing rule: existing infra stays authoritative until proven).
- **Done when:** drainer pod survives a forced kill with zero lost messages; one CronJob runs on schedule for a week.
- **Skills:** pods/deployments/services, kubectl, manifests-as-code, CronJobs.

### M5 — Cloudflare pillar (AWS Phase 5)
- **Steps:** port one small app end-to-end — candidate: TubeScout fetch layer or a QI status dashboard — UI to CF Pages, logic to a Worker, data to D1 (it IS SQLite — near-zero schema migration), assets to R2 → wire into the existing tunnel/DNS estate → compare DX notes vs AWS in the guide (that comparison IS the tutorial).
- **Done when:** the ported app serves publicly from Cloudflare with its data in D1, $0.
- **Skills:** Workers, Pages, D1, R2, wrangler CLI — the second ecosystem.

### M6 — The "QI bot" Helm chart (Track C4) — the template engine realized
- **Steps:** Helm chart wrapping the bot runtime (drainer + config + secrets) → Maia = instance #1 via `values-maia.yaml` → spin up bot #2 (test personality) with one command → document "new bot in 5 minutes" procedure.
- **Done when:** two named bots run from one chart, differing only in values files.
- **Skills:** Helm templating, releases, upgrades/rollbacks. **Strategic:** this IS the one-codebase→infinite-bots product vision.

### M7 — GitOps (Track C5) — the "dynamic environment" payoff
- **Steps:** GitHub Actions workflow: build drainer image on push → push to registry (ghcr) → k3s auto-syncs (Flux or Argo CD) → extend to Lambda deploys (Actions running `deploy_lambda.py`) and CF Workers (wrangler action) → one `git push` updates home cluster + AWS + Cloudflare together.
- **Done when:** a one-line code change reaches all three environments with zero manual commands.
- **Skills:** CI/CD, GitOps, registries, deployment automation — the replication engine for everything.

### M8 — Universal packs + reference app (AWS Phase 6)
- **Steps:** consolidate all `universal\` contributions → standalone neutral repo: "Free Webhook-Bot Cloud Kit" (generic guide with placeholders, parameterized scripts/bats, Lambda, drainer, Dockerfile, Helm chart, Actions workflows) → prove it by deploying a from-scratch demo bot using ONLY the kit → this satisfies the standing "universal, non-QI edition" requirement in full.
- **Done when:** a clean-room deploy from the kit works without touching QI-specific anything.

### M9 — Free cloud cluster (Track C6, optional)
- **Steps:** Oracle Cloud always-free ARM VM (4 OCPU/24 GB) → k3s → deploy the Helm bot chart → now the bot runtime itself is cloud-hosted and free, desktop remains rung-1 brain only.
- **Done when:** a bot serves entirely from the free cloud cluster.
- **Skills:** ARM builds, real-world cluster ops, multi-cloud.

---

## 4. Decisions pending (owner)
| Decision | Needed by | Default if unset |
|---|---|---|
| Privacy: allow rungs 2–4 (third-party LLMs) for Maia? | M3 | rung 1 + rung 5 only (`local_only: true`) |
| M5 port candidate (TubeScout fetch vs status dashboard) | M5 | status dashboard (smaller) |
| Docker Desktop vs engine-in-WSL2 | M2 | Docker Desktop (easier GUI learning) |
| Produce M9 (Oracle) at all | M8 | yes, if account approval sails through |

## 5. Component & account acquisition timeline (all free)
- **M1:** boto3 (pip) — nothing else
- **M2:** WSL2 + Docker
- **M3:** OpenRouter, Google AI Studio, Groq accounts; Workers AI toggle; one new CF tunnel (Ollama, authenticated)
- **M4:** k3s/kind, kubectl
- **M5:** wrangler CLI
- **M6:** Helm
- **M7:** Flux or Argo CD; ghcr.io (existing GitHub)
- **M9:** Oracle Cloud account

## 6. Video gates (Kroger-style animated explainers)
Produced at natural story boundaries, from the guides' proven content, via the extended `build_bu_videos.py` pipeline (edge-tts + Pillow character animation + FFmpeg):
1. **After M1:** "Your Bot Never Misses a Message" — account setup → relay live (guide Parts 1–3)
2. **After M3:** "A Brain in Five Places" — the LLM fallback chain
3. **After M7:** "Push Once, Deploy Everywhere" — containers → cluster → GitOps
4. **After M8:** "Do It Yourself" — the universal kit walkthrough (the shareable one)

## 7. Standing cadence (every session in this program)
1. Work the current milestone; scripts-first.
2. Update the guide + gotchas log the moment anything is learned.
3. Run/extend the verification script.
4. Git commit (owning repo) + session summary .docx + memory update.
5. At milestone completion: universal-pack contribution + storyboard notes + registry updates (`qi_registry.json`, `QI_Service_Registry.md`).

---
*The plan is living: milestones may resequence as free tiers, providers, or priorities shift — changes get logged here with date + reason.*

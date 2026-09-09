# QI Trinity — Tri-Platform AI Orchestration (Claude as spearhead)

> **Name:** "Trinity" — owner's name (2026-09-08) for the arrangement between Claude, ChatGPT and Google AI Studio, with Claude as the spearhead. The Gemini API key in AI Studio carries the same name.

**Date:** 2026-09-08 · **Owner:** Renne Santiago · **Author:** Claude (Fable 5.1, flight-deck session)
**Status:** v2 (2026-09-08 17:05) — owner rulings applied: **Claude is the top; ChatGPT and Gemini are on-demand assistants reached over MCP; NEXUS is not in the mix; zero pay-per-use API spend.** No running system changed yet.
**Canonical location:** `C:\QIH\shared\documentation\plans\QI_TriPlatform_AI_Orchestration_Plan_2026-09-08.md`
**Parent plan:** [QI_Hive_Architecture_Plan.md](C:\QIH\QI_Hive_Architecture_Plan.md) — this document is a *track* inside that plan, not a competitor to it.

---

## 0. Executive verdict

The goal is sound. Three parts of the premise are wrong, and two things you asked for already exist. Correcting these before building saves the most money and risk.

| # | Premise in the ask | What the audit found | Consequence |
|---|---|---|---|
| P1 | "ChatGPT Plus … running Fable 5.1" | Fable 5.1 is Anthropic's model — it is the engine of this session. ChatGPT Plus runs OpenAI's GPT-5.1 family. | Harmless naming slip, but the resume story must be accurate: three vendors, three model families. |
| P2 | "Gemini to run cross-app automations … test Google integrations" via the subscription | Google **retired the standalone Gemini CLI for individual and AI Pro accounts on 2026-06-18** (successor: Antigravity CLI). Google's terms **explicitly prohibit driving its CLI OAuth from third-party software, naming OpenClaw as the example**. | Gemini participates in *automation* only through the **paid Gemini API** (keys already exist in NEXUS, NoosOrbis and MailBrain) or **Apps Script**. The $20 subscription buys the *human* surfaces: Gemini app, Workspace side panels, Gems, Scheduled Actions (≈10), NotebookLM. |
| P3 | "Mail Brain … runs on the Google platform" | MailBrain is a **Chrome MV3 extension + local Flask backend**, not a cloud app. It already has a **four-provider AI adapter** (Gemini, OpenAI, Anthropic, Ollama). It is **unregistered in the QI registry, has no repo of its own** (it is a clone of the EasyFlow repo), and carries 13 abandoned worktrees. | It is the most mature multi-vendor integration in the ecosystem. Register and repo it first (already Wave 0.1/0.9 of the architecture plan); extend its adapter, do not build a new one. |
| P4 | "I need a way to pass payloads between the three" | Both assistants can be reached as **MCP servers from Claude Code** with no API billing: Codex CLI has a first-party `codex mcp-server` mode that runs on the ChatGPT Plus login; Gemini has no subscription-side programmatic channel, but its **free-tier API key** (no billing account) can sit behind a tiny QI MCP server. NEXUS is explicitly **out of the mix** (owner ruling 2026-09-08). | Orchestration = Claude Code's own Agent/MCP loop. Two MCP servers, zero spend, no new port, no new service. |
| P5 | "Gemini should summarize communications, manage schedules, watch YouTube" | Five in-house agents already do this: **Yubin** (Gmail classify + digest), **Kaze** (daily digest), **Asa** (morning briefing), **Kakei** (finance from mail), **TubeScout** (YouTube subscriptions). Claude also has **Gmail, Calendar and Drive MCP connectors attached right now**. | Gemini becomes a *second opinion and the Workspace-native UI*, not a replacement. Rebuilding Yubin/Kaze inside Gemini would couple a working pipeline to a vendor you may cancel. |

**Bottom line:** the right build is small. Two MCP server registrations (Codex, Gemini free tier), one delegation rubric, one handoff-packet convention for app-only features, one governance document (Vendor Exit Contract), and three daily practice workflows. NEXUS, Maia, OpenClaw and every other QI app stay exactly as they are.

---

## 1. Environment audit (read-only, 2026-09-08 ~10:10)

### 1.1 Hardware

| Item | Value | Note |
|---|---|---|
| CPU | Intel Core i9-14900KF, 24C/32T | Ample for parallel sub-agents and local models |
| RAM | 64 GB | |
| GPU | RTX 5080, 16.3 GB VRAM, driver 591.86 | **15.6 GB in use at scan time.** Known contention (see memory: free VRAM is a misleading health signal). Any plan that adds local-model load must check `nvidia-smi` utilisation and the ComfyUI `/queue` first. |
| C: | 1.86 TB, 253 GB free | Gold tier (`C:\APPS`) |
| D: (DEV) | 1.86 TB, 446 GB free | Package tier (`D:\Dev`), ComfyUI at `D:\AI` |
| F: (My Book Duo) | 18.6 TB, 6.35 TB free | Bulk/archive — the natural landing zone for the file-organisation work |
| OS | Windows 11 Enterprise 26200.9278 | |

### 1.2 Runtimes and AI tooling

| Tool | State | Relevance |
|---|---|---|
| Python | 3.11 (Program Files) + 3.12 (uv, SynVox). `C:\1-AI\APPS\PYTHON\python.exe` **no longer exists** — the user-profile memory pointing at it is stale. | Fix the memory entry. |
| Node / npm | v24.14.1 / 11.11.0 — but `%APPDATA%\npm` is missing, so `npm ls -g` fails | Global npm store misconfigured on Windows; matters if Codex CLI is installed natively. |
| WSL | Ubuntu-24.04 (stopped at scan — consistent with the OC 07:30–17:30 GPU pause), docker-desktop | Codex CLI **is installed in WSL** (`~/.npm-global/bin/codex`, `~/.codex` present). |
| Codex / Gemini / Antigravity CLI (Windows) | none | Only WSL Codex exists. No `~/.gemini`, no `~/.antigravity`, no `gcloud`. |
| ChatGPT desktop app | not installed | Optional; its "Work" mode gives folder-scoped local access. |
| Ollama | 0.33.3, 23 models incl. qwen3.8:27b, gemma4:31b, qwen3-vl:32b, gpt-oss-20b | The **local fallback** for anything a cancelled vendor used to do. |
| Docker | 29.7.2 | Available for sandboxing Codex if wanted. |
| gh | 2.89.0 | Repo creation for MailBrain. |

### 1.3 QI Hive

| Measure | Value |
|---|---|
| Registered projects | 36 |
| `QI_*` Windows services | 58 — 46 running, 12 stopped (Claude Voice ×4 and Naya ×3 stopped **by decision D5 of the architecture plan**; `QI_RetirementAnalyzer` has a known AppDirectory bug) |
| `QI_*` scheduled tasks | 19 (4 disabled, incl. the `QI_TaskHealth` task — a same-named service is running; see §8) |
| Listening QI ports | 30+ in the 6969–9876 range, all python except Caddy :9040 and Ollama :11434 |
| Vendor keys on disk (names only) | NEXUS: `GEMINI_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY` · NoosOrbis: `GEMINI_API_KEY` · SynVox/Baguapp: `OPENROUTER_API_KEY` · **no `ANTHROPIC_API_KEY` anywhere** (Claude runs on the Max subscription) |
| Google OAuth artifacts | MailBrain and EasyFlow **share one OAuth client ID** and token files; TubeScout has its own (7-day refresh-token expiry noted in code — the 66-day TubeScout outage of 2026-08 was this). |
| Handoff infrastructure | JSON file drops (`C:\QIH\inbox\relay`, `C:\QIH\dispatch\jobs`), HTTP peer-bridge (`C:\QIH\shared\bridge\shared-chats.json`). **Bus v1 (SQLite journal) is designed but not built** (Wave 0.7). |
| MCP servers Claude uses | QI-owned: qi-brain, qi-registry, qi-comfy, mapsnap, autopdf, sqlite-maia/naya, headroom · third-party: git, claude-peers (both failing to connect this session) · claude.ai connectors: Gmail, Calendar, Drive, Hugging Face, Vercel, Chrome, computer-use |

### 1.4 LLM-bearing tools and the role each keeps

| Tool | Backend today | Role in the tri-platform design |
|---|---|---|
| **NEXUS** (:8010, :7880, MCP :8310) | 22-provider router, judge = `claude_max` | **Not in the mix** (owner ruling 2026-09-08). Keeps serving the QI apps that already use it; carries no assistant traffic. |
| **Claude Code / Claude Manager** | Max subscription, 7 hive-* agents, Agent HR | **Flight deck.** |
| **OpenClaw** (WSL :18789) | Local models via Ollama; browser-session automation for ChatGPT/NotebookLM cookies | Keeps LINE + the five digest agents. ⚠️ Its cookie-driven NotebookLM/ChatGPT automation sits in the same ToS grey zone Google now polices — see D6. |
| **MailBrain** (ext + Flask :8550) | Gemini / OpenAI / Anthropic / Ollama adapter | **Gemini's real automation surface** (API key, not OAuth). Register + repo first. |
| **Maia / Naya** | Ollama → Anthropic (→ OpenAI) chains, config in SQLite | Unchanged. |
| **MapSnap, CogniBase, Retirement Analyzer, Baguapp, Lottery Wiz, Claude Voice, MediaStudio** | Per-app multi-provider adapters | Unchanged; candidates for a shared `qi-spine` LLM adapter later (Wave 2+). |
| **TubeScout, Yubin, Kaze, Asa, Kakei** | YouTube Data API / Gmail API + local LLM | The **local Google-life pipeline**. Gemini cross-checks it; never replaces it. |
| **ComfyUI, VoiceStudio, PersonalSong, FilmForge, MediaStudio** | GPU generators | Out of scope except for VRAM contention (§1.1). |
| **QI Brain (:9011), Connector (:9030), Gate/Caddy (:9040/41)** | Memory, remote MCP, auth wall | Unchanged. Brain logs every cross-vendor decision. |

---

## 2. Target architecture — Trinity: "Claude as spearhead, two assistants on call"

```
                 ┌──────────────────────────────────────────────┐
                 │  CLAUDE CODE  — the top (Max subscription)   │
                 │  triage → delegate → verify → merge          │
                 │  hive-* sub-agents · QI MCP servers · Brain  │
                 └───────┬──────────────────┬───────────────────┘
                         │ MCP (stdio)      │ MCP (stdio)
                         ▼                  ▼
            ┌────────────────────┐   ┌───────────────────────────┐
            │ ASSISTANT 1        │   │ ASSISTANT 2               │
            │ ChatGPT Plus       │   │ Gemini                    │
            │ `codex mcp-server` │   │ `qi_gemini_mcp.py`        │
            │ tools: codex,      │   │ over the FREE-TIER key    │
            │        codex_reply │   │ tools: gemini_generate,   │
            │ auth: codex login  │   │  gemini_read_long,        │
            │ sandbox: read-only │   │  gemini_ground_search     │
            │  or worktree-write │   │ auth: AI Studio key, $0   │
            └─────────┬──────────┘   └─────────────┬─────────────┘
                      │ app-only features           │ app-only features
                      ▼                             ▼
            handoff packet → ChatGPT app     handoff packet → Gemini app
            (Deep Research, voice, GPTs)     (Workspace panels, Gems,
                                              Scheduled Actions, NotebookLM)

   Reverse direction (assistants reading QI): ChatGPT Developer-Mode connector
   and Antigravity CLI → QI Connector :9030 (already a remote MCP server).
   Local fallback for either assistant: Ollama models via hive-* sub-agents.
```

### 2.1 The four layers

| Layer | What | Cancel-safety rule |
|---|---|---|
| **A — The top** | Claude Code. Every ask lands here first. Claude triages with the rubric in §3, delegates, verifies the result, merges. Reasoning that spans the task never leaves this layer. | n/a (primary) |
| **B — Assistant MCP servers** | `codex` (stdio, ChatGPT Plus login) and `qi_gemini_mcp` (stdio, free-tier key). Registered in Claude Code's MCP config like qi-brain or qi-comfy. Sub-agents can call them too, so a Sonnet sub-agent may drive Codex on a worktree. | Cancel = remove one MCP entry. Zero code changes. The Gemini key is free tier; **never attach a billing account** to that Google Cloud project. |
| **C — App-only features** | Deep Research, ChatGPT voice, Custom GPTs, Gemini Workspace side panels, Gems, Scheduled Actions, NotebookLM. Reached only by Renne, fed and drained by handoff packets in `C:\QIH\shared\handoff\`. | Cancel = stop pasting. Every Custom GPT / Gem instruction is mirrored in `C:\QIH\config\vendors\`. |
| **D — Reverse MCP** | ChatGPT (Developer Mode connector) and Antigravity CLI (run by Renne) connect to QI Connector so the assistants can read Brain, registry and health when Renne works inside them directly. The Gemini consumer app cannot do this (Enterprise only). | Already exists; nothing to cancel. |

**Not in the mix:** NEXUS. It keeps running for the QI apps that use it, but no assistant traffic goes through it (owner ruling 2026-09-08).

### 2.2 The Vendor Exit Contract (governance, applies to all three)

Every vendor integration must satisfy all five before it is considered "in":

1. **One-flag disable** — an MCP entry removed or `enabled:false`, never a code change.
2. **No orphaned knowledge** — Custom GPT instructions, Gem instructions, ChatGPT memory and Gemini "saved info" are exported monthly to `C:\QIH\config\vendors\<vendor>\` and committed. (ChatGPT has no memory export button — copy by hand or via the data export ZIP; Custom GPT configs must be pasted manually.)
3. **Named local fallback** — the Ollama model or hive-* agent that takes the job if the vendor disappears (table in §7).
4. **No vendor in the critical path** — no scheduled task, NSSM service or QI app *requires* an assistant to run. Assistants are called by Claude during sessions, not by unattended jobs.
5. **Exit checklist filed** — `C:\QIH\config\vendors\<vendor>\EXIT.md`: what to export, what to flip, what to revoke (OAuth grants, keys), in that order.

---

## 3. Answer 1 — Orchestration: the delegation rubric Claude applies to every ask

Claude is the top. On every ask it triages once, states the assignment in one line, and delegates by default. It keeps only what fails the rubric or what an assistant returns wrong.

### 3.1 Who gets what

| Task shape | Assignee | Why |
|---|---|---|
| Feature code in an isolated worktree, unit tests, refactors, PowerShell/Bash scripts, front-end polish, "review this diff" | **ChatGPT via Codex MCP** | Strong agentic coder with its own sandbox; runs on the Plus quota, not tokens. Sandbox `read-only` for review, `workspace-write` only inside `C:\QIH\worktrees\` or a project worktree. |
| Reading very long inputs (logs, transcripts, 500-page PDFs), web-grounded research, Google-flavoured work (Apps Script, Workspace API code, Sheets formulas), image/video understanding, JP/PT translation, bulk classification | **Gemini via free-tier MCP** | 1M-token context and search grounding at $0; free-tier daily caps mean **batch, do not chat**. |
| Architecture, cross-system tracing, anything touching `C:\QIH\ecosystem`, NSSM services, secrets, ports, security boundaries; final verification and merge; anything both assistants failed | **Claude (the top)** | The blast-radius and ecosystem rules live here. |
| Mechanical single-file edits, log greps, summaries of one file | **Haiku / Sonnet hive-* sub-agent** | Already the cheapest competent tier; keeps assistant quota for real work. |
| Bulk or private data that must not leave the machine | **Ollama via sub-agent** | Local fallback for both assistants. |
| Deep Research, voice brainstorming, Custom GPTs, Gemini Workspace panels, Gems, Scheduled Actions, NotebookLM | **Renne, via handoff packet** | App-only; no MCP exists for these. |

### 3.2 The loop, every time

1. **Triage** — pick the assignee from 3.1; say it in one line ("→ Codex, worktree-write, acceptance = tests green").
2. **Packet** — goal, constraints, files, acceptance test. Secrets never included; the packet script refuses if a secret pattern matches.
3. **Run** — MCP call (or handoff packet for app-only work). Sub-agents may make the MCP call so the main thread stays light.
4. **Verify** — tests, `hive-inspector`, or a second assistant's review when the change is risky. An assistant's claim of success is not evidence.
5. **Merge and log** — Agent HR row with vendor, model, tokens/quota, outcome; Brain decision when a choice was made.

### 3.3 Rules that do not bend

- Gemini is **never** driven through its CLI or Antigravity login by Claude or any tool (Google's terms; account-suspension risk). The free-tier API key is the only programmatic channel, and its project **never** gets a billing account.
- Codex runs read-only unless the packet names a worktree; it never gets `danger-full-access`.
- Nothing unattended calls an assistant. Scheduled jobs use local models only, so a cancelled subscription can never break a nightly task.
- Escalation goes one step at a time: sub-agent → assistant → Claude, with a one-line note on each bump.

---

## 4. Answer 2 — Local file management with ChatGPT, safely

**Principle: the LLM proposes, a QI script disposes.** No vendor agent ever gets write access to `C:\APPS`, `C:\QIH`, `D:\Dev`, the `C:\OC` junction, or any path named in `qi_registry.json` or a scheduled task.

| Phase | Who | What | Safety |
|---|---|---|---|
| **A · Inventory** | QI script `qi_fs_inventory.py` (Sonnet builds it) | Walks the *personal* zones only — `Downloads` (105 GB, 28 files + 52 folders at top level), `Documents`, `Desktop`, `Pictures`, `F:\` — and emits `inventory.csv` (path, size, mtime, ext, sha1-prefix, guessed category) + a summary. | Read-only. Excludes every registry path and junction. |
| **B · Proposal** | ChatGPT — a **Project** with `inventory.csv` uploaded, or Codex CLI `--sandbox read-only` on the inventory folder | Proposes a taxonomy and a `moves.csv` (src, dst, action ∈ {move, archive-to-F, delete-candidate, keep}, reason, confidence). | Sees a manifest, not the disk. Deletion is *never* an action it can execute — only a flag for Renne's Tier-1 approval list. |
| **C · Apply** | QI script `qi_fs_apply.py` | `--dry-run` first, prints blast radius (greps `C:\APPS`, `C:\QIH`, scheduled tasks and the registry for every source path), then applies with an undo journal (`undo.jsonl`, reversible in one command). Delete-candidates go to a quarantine folder for 30 days, never to the recycle bin directly. | Tier 2 change with a one-line rollback. Verified durably (NTFS flush check, per memory) when moving to F:. |
| **D · Steward** | Custom GPT "QI File Steward" (instructions mirrored at `C:\QIH\config\vendors\chatgpt\QI_File_Steward.md`) | Recurring monthly pass: new inventory → new proposal. | If ChatGPT is cancelled, the same prompt runs against `gemma4:31b` locally through a hive-* sub-agent. |

**ChatGPT desktop "Work" mode:** acceptable *only* pointed at a staging folder (`C:\Users\renne\Staging\`) you copy things into. Do not grant it the user profile root.

**Voice brainstorming / UI-UX polish / agentic validation:** ChatGPT voice → export transcript → `qi_handoff.py ingest`; UI/UX critiques arrive as packets with screenshots that a **Haiku sub-agent** (not the main thread) converts to text first, per the images-to-text rule.

---

## 5. Answer 3 — Unlocking Gemini over Gmail, Calendar, YouTube

Two tiers, and it matters which is which.

**Tier 1 — Interactive (subscription, human-driven):**
1. Gemini app → Settings → Apps: enable Gmail, Calendar, Drive, Keep, Tasks, YouTube (off by default).
2. Three Gems, instructions mirrored in `C:\QIH\config\vendors\gemini\`: **Inbox Triage** (mirrors Yubin's label taxonomy so results are comparable), **Week Planner** (reads Calendar, proposes blocks; Renne accepts), **YouTube Researcher** (summaries by interest list from TubeScout's config so the two stay in sync).
3. Scheduled Actions (limit ≈10): a 07:00 inbox+calendar summary and a Sunday YouTube digest. These are **cross-checks** against Asa/Kaze/TubeScout, feeding workflow W3 in §6.
4. NotebookLM: one notebook seeded from `C:\QIH\shared\documentation` exports (the Documentation Brain harvester already indexes 937 docs — export a curated subset, do not point cookies at it).
5. Gemini side panels in Gmail/Docs/Sheets for drafting — no setup.

**Tier 2 — Automation (API / Apps Script, cancel-independent):**
1. Register `qi_gemini_mcp` in Claude Code on a **free-tier** AI Studio key stored at `C:\QIH\secrets\trinity_gemini.env`. No billing account, ever (D1 as ruled).
2. MailBrain: register in `qi_registry.json`, create `Quiddity-Innovations/MailBrain`, re-point the clone, sweep the 13 worktrees (this is architecture-plan Wave 0.1/0.8/0.9 — do it there, once). Then Gemini API is already selectable in its Options page.
3. Apps Script for anything that must run *inside* Google (label rules, calendar hygiene). MailBrain already ships `MailBrain_AppsScript.js`; treat it as the reference.
4. Claude keeps its Gmail/Calendar/Drive connectors for flight-deck queries. Gemini is not needed for Claude to read your mail.

**Google AI Pro's Cloud credits** reportedly apply only inside the AI Studio web UI, not to external API keys — verify on the subscription page before assuming the NEXUS calls are covered.

---

## 6. Answer 4 — Three daily multi-AI workflows (resume evidence)

| # | Workflow | Loop | What it proves | Evidence trail |
|---|---|---|---|---|
| **W1 · Triad Code Review** | Claude writes the change → Codex MCP (read-only) returns findings → Gemini MCP *judges* Claude's vs Codex's findings → Claude applies what survives, records dissent | every PR / feature | Cross-platform LLM orchestration; adversarial review | Agent HR run rows, PR description with a "Triad" block, Brain `qi_log_decision` |
| **W2 · Research Triangulation** | Claude frames the question → Gemini MCP (search-grounded) + Codex MCP (web-enabled) answer in parallel, Deep Research by packet when depth is needed → Claude synthesises consensus / disagreement / unknowns → decision logged | weekly (e.g. AWS edge design, BU server, model pricing refresh) | Multi-agent workflow design; synthesis with provenance | `RETURN-*.md` pair + NEXUS synthesis + Brain decision |
| **W3 · Digest Cross-Check** | Asa/Kaze/Yubin (local) vs Gemini Scheduled Action summary vs Claude Gmail MCP → `qi_digest_diff.py` scores agreement, flags what only one caught | daily, 2 minutes | Multi-agent evaluation; precision measurement; vendor-independence | 30-day agreement chart — decides keep/cancel with data |

**Resume phrasing you will have earned after 30 days:** "Designed and operated a three-vendor LLM orchestration layer (Anthropic on top, OpenAI and Google as MCP-attached assistants) inside a self-hosted 36-project ecosystem; implemented adversarial multi-agent code review and research triangulation with full provenance logging; ran vendor-independence drills proving zero-downtime provider removal." Every clause maps to a log you can show.

---

## 7. Cancel-safety matrix

| Capability | Vendor that provides it | Fallback if cancelled | Data that must be exported first |
|---|---|---|---|
| Second-opinion code review | ChatGPT Plus (Codex) | `gemma4:31b` / `qwen3-coder` via a hive-* sub-agent; Claude Sonnet sub-agent | none |
| File taxonomy proposals | ChatGPT (Custom GPT) | same prompt to a local Ollama model | Custom GPT instructions (mirrored) |
| Voice brainstorming | ChatGPT voice | Claude Voice (:8720, currently stopped by decision) or OpenClaw Koe (planned) | transcripts (already saved as packets) |
| Deep Research (OpenAI) | ChatGPT | Gemini Deep Research, or hive-scout + WebSearch | reports (saved as RETURN packets) |
| Workspace side-panel drafting | Google AI Pro | Claude Gmail/Drive connectors | none |
| Inbox / calendar summaries | Google AI Pro (Scheduled Actions) | Asa / Kaze / Yubin — **already primary** | Gem instructions (mirrored) |
| YouTube digest | Google AI Pro | TubeScout — **already primary** | interest list (already in TubeScout config) |
| NotebookLM corpus | Google AI Pro | Documentation Brain (:8600) | source docs are local already |
| Gemini model as an assistant | Gemini API **free tier** (no billing) | `gemma4:31b` locally | none |
| 2 TB+ Drive storage | Google AI Pro | F:\ has 6.35 TB free | anything stored only in Drive |

Cancelling **any** of the two new subscriptions requires zero code changes and breaks no QI service. That is the design goal and it is testable: a quarterly "vendor blackout drill" (flip both `enabled:false`, run W1–W3 for a day) proves it.

---

## 8. Findings outside the ask that you should know about

| Severity | Finding | Recommendation |
|---|---|---|
| 🟠 | The `QI_TaskHealth` **scheduled task** is disabled while a `QI_TaskHealth` **service** is running. Which one is the live freshness monitor is unverified. | Confirm the service produces today's output before adding any new unattended job (W3 is one); retire the dead twin. |
| 🟠 | GPU at 15.6/16.3 GB during the scan. | Identify the holder before any local-model fallback is relied upon. |
| 🟠 | MailBrain and EasyFlow share one Google OAuth client and duplicate seven Gmail scripts. | Resolve ownership when MailBrain gets its repo (Wave 0.9). |
| 🟠 | TubeScout's refresh token expires every 7 days (test-mode OAuth app). | Publish the OAuth consent screen or move to a service account; otherwise the 66-day outage recurs. |
| 🟠 | OpenClaw drives ChatGPT/NotebookLM via browser cookies. | Same ToS class Google is now enforcing. Decide under D6. |
| 🟡 | `%APPDATA%\npm` missing → global npm broken on Windows. | Fix before installing Codex natively. |
| 🟡 | Stale memory: Python at `C:\1-AI\APPS\PYTHON` no longer exists. | Corrected in this session's memory update. |
| 🟡 | Two MCP servers (`git`, `claude-peers`) failed to connect this session. | Not blocking; note for the next Claude Manager ops pass. |

---

## 9. Decisions needed before any change (owner gate)

| # | Decision | Recommendation | Tier when executed |
|---|---|---|---|
| D1 | ~~Fund API budgets for a NEXUS lane~~ | ✅ **DECIDED by owner 2026-09-08 — rejected.** Assistants are reached over **MCP** only: Codex on the ChatGPT Plus login, Gemini on the **free-tier** key. **NEXUS is not in the mix.** Zero pay-per-use spend. | — |
| D2 | Codex CLI location | **Keep WSL** (0.118.0 already installed, Linux sandbox is what the model was trained against); Claude Code's MCP entry launches `wsl.exe … codex mcp-server`. Native Windows only if WSL start-up latency annoys. | 🟢 |
| D3 | Scope ChatGPT is allowed to *see* for file organisation | `Downloads`, `Documents`, `Desktop`, `Pictures`, `F:\` — as a manifest, never live. Project trees stay under the architecture plan's hygiene manifest. | 🟠 when applying moves |
| D4 | ToS posture | Accept Codex-via-Plus for personal coding (documented as normal use); **refuse** any tool-driven Gemini/Antigravity OAuth. | policy |
| D5 | MailBrain repo + registration now (pulls Wave 0.1/0.9 forward for one app) | Yes — it is the Google-side anchor of this plan | 🟠 registry edit + 🟠 new private org repo |
| D6 | OpenClaw's cookie-based ChatGPT/NotebookLM automation | Keep for now, add to the vendor risk register, replace NotebookLM use with Documentation Brain over 60 days | policy |
| D7 | Install ChatGPT desktop app | Optional; only with a staging folder | 🟢 |
| D8 | Start date for the 30-day evaluation window | Proposed **2026-09-15 → 2026-10-15**, review on 2026-10-16 | calendar |

---

## 10. Phased plan (nothing starts before D1–D8 are answered)

| Phase | Window | Work | Tier / blast radius | Model |
|---|---|---|---|---|
| **0 · Foundations** | week of 09-08 | Write Vendor Exit Contract + three `EXIT.md` stubs · create `C:\QIH\shared\handoff\` + packet template + `qi_handoff.py` (new, redact, ingest) · fix npm global dir · verify which `QI_TaskHealth` (task vs service) is live · correct stale memory | 🟢 new files; 🟢 verification only | Sonnet |
| **1 · Assistant 1 — Codex MCP** | as soon as Renne runs `codex login` | Add `codex` stdio MCP entry to Claude Code (`wsl.exe -d Ubuntu-24.04 -u hyosuke -- codex mcp-server`), restart Claude, prove `codex` + `codex_reply` tools answer on the Plus login, first read-only review on a real diff, Agent HR logging | 🟢 one MCP entry (rollback: remove it) | Sonnet builds, Opus reviews sandbox flags |
| **2 · Assistant 2 — Gemini MCP** | after Renne drops a free-tier AI Studio key in `C:\QIH\secrets\trinity_gemini.env` | Build `C:\QIH\engine\mcp\qi_gemini_mcp.py` (stdio; tools `gemini_generate`, `gemini_read_long`, `gemini_ground_search`; daily-quota guard; never logs prompts with secrets), register in Claude Code, first W1 judge run | 🟢 new script + one MCP entry | Sonnet |
| **3 · MailBrain anchor** | 09-19 → 09-24 | Register in registry · create `Quiddity-Innovations/MailBrain` (private) · re-point clone · sweep 13 worktrees · resolve shared OAuth client with EasyFlow | 🟠 registry + repo (rollback: registry backup, clone stays) | Sonnet + hive-inspector |
| **4 · Files** | 09-22 → 09-29 | `qi_fs_inventory.py` → ChatGPT Project proposal → `qi_fs_apply.py --dry-run` → Renne approves the delete-candidate list (Tier 1) → apply moves to F:\ with durable verify | 🟠 moves (undo journal); 🔴 deletes need approval list | Sonnet |
| **5 · Gemini surfaces** | 09-24 → 09-30 | Enable Workspace apps, three Gems, two Scheduled Actions, NotebookLM seed, mirror all instructions to git | 🟢 vendor-side only | Renne + Sonnet for mirroring |
| **6 · Practice + measure** | 09-30 → 10-15 | W1 on every PR, W2 weekly, W3 daily; `qi_digest_diff.py`; monthly vendor export | 🟢 | Sonnet, Haiku for digest diff |
| **7 · Verdict** | 10-16 | Vendor blackout drill · keep/cancel decision per vendor with the W3 chart · update this plan's §9 | policy | Opus |

**Blast radius statement for the whole plan:** no existing port, path, service name or scheduled task changes. The only shared files touched are `qi_registry.json` (one added project, MailBrain) and Claude Code's MCP config (two stdio entries). Both have dated backups and one-line rollbacks. Silent-failure surfaces added: W3 daily job — it ships with its own freshness check under `QI_TaskHealth`, which is why re-enabling that monitor is in Phase 0.

---

## 11. Relationship to the architecture plan

- This is track **"V — Vendor adapters"** running alongside Wave 0/1 of [QI_Hive_Architecture_Plan.md](C:\QIH\QI_Hive_Architecture_Plan.md).
- Phase 3 here **is** items 0.1 (register MailBrain), 0.8 (its 13 worktrees) and 0.9 (its repo) of Wave 0 — executed early for one app, not duplicated.
- Handoff packets publish to Bus v1 once 0.7 ships; until then they are plain files, which the bus design explicitly tolerates.
- No new ports and no new services: both assistant MCP servers are stdio processes spawned by Claude Code on demand, exactly like `qi-brain` and `qi-comfy`.
- NEXUS is untouched by this track (owner ruling 2026-09-08).

---

## 11a. Test protocol for the arrangement (owner ruling 2026-09-08)

The arrangement is a **trial**. It continues and grows if it works; if not, it is reviewed, revised, and either assistant may be terminated. "Works" is judged on evidence, not impressions.

| Check | Pass condition | Fail condition |
|---|---|---|
| **Command works** | Claude issues a task to each assistant over MCP and receives a usable result without Renne touching the vendor UI. | Any manual step needed for a normal delegation. |
| **Delegation is real** | Over the trial, at least half of code/scripting tasks Claude receives are delegated to Codex, and at least half of long-reading/research tasks to Gemini, with the assignment stated each time. | Claude keeps the work by habit, or delegations are mostly re-done by Claude. |
| **Quality** | Delegated output passes verification (tests, hive-inspector, or the other assistant's review) at least 70% of the time on first return. | Below 50%, or an assistant fabricates results. |
| **Quota** | Plus and free-tier limits are not hit on normal days; when hit, the fallback (local model / sub-agent) takes over automatically. | Quota blocks routine work more than twice a week. |
| **Zero spend** | No API bill from either vendor. | Any charge. |
| **Independence** | A one-day blackout drill (both MCP entries removed) breaks no QI service, task or app. | Anything QI-side depends on an assistant. |

**Window:** first 30 days after both MCP servers answer (target 2026-09-15 → 2026-10-15). **Review:** 2026-10-16, with the Agent HR log as the evidence. **Outcomes:** continue and enhance · revise the rubric · terminate ChatGPT · terminate Gemini · terminate both.

---

## 12. Change log

| When | What |
|---|---|
| 2026-09-08 10:30 | v1 — proposal with a NEXUS API lane and paid API budgets (D1). |
| 2026-09-08 18:45 | Both assistants proven over MCP after restart (Codex direct command verified by grep; L3 live registry lookup from inside Codex after `default_tools_approval_mode`). Hive currency pass: registry 36→42, Trinity registered. Assistant onboarding built (L1/L2/L3, `qi_trinity_onboarding.py`, AGENTS.md auto-load proven) — see `QI_Trinity_Onboarding_Design_2026-09-08.md` §6a. Gemini MCP gained a model ladder + bench. Lesson: never `approval-policy: on-request` over MCP. |
| 2026-09-08 17:40 | Assistant 2 (Gemini) live on the Trinity key, model `gemini-3.6-flash`; both MCP entries added to Claude Code (backup `.claude.json.bak-2026-09-08-triplatform`). Codex awaiting `codex login`. |
| 2026-09-08 17:40 | Trinity check (Fable session): Codex CLI upgraded, both legs verified + obedience-tested, `qi_trinity_check.py` + model guide + config.toml added, Agent HR onboarded; §14. |
| 2026-09-08 17:05 | v2 — owner rulings: NEXUS out, MCP only, zero spend, Claude on top with two on-demand assistants. §2, §3, §9 D1/D2, §10 phases 1–2 rewritten. Verified locally: `codex mcp-server` exists in Codex 0.118.0 (WSL), not yet logged in. Verified by research: ChatGPT Plus supports custom MCP connectors (Developer Mode); Gemini consumer app does not; Antigravity CLI may consume QI Connector when run by Renne. |

## 13. Sources verified for this plan (2026-09-08)

- OpenAI Codex: auth via ChatGPT plans · non-interactive `codex exec` · sandbox/approval flags · MCP client — developers.openai.com/codex (auth, noninteractive, agent-approvals-security, mcp)
- Google: "Transitioning Gemini CLI to Antigravity CLI" — developers.googleblog.com (2026-06) · Gemini CLI ToS/privacy page and discussion #22970 (third-party OAuth use prohibited, OpenClaw named)
- Google AI Pro inclusions — gemini.google/subscriptions · ai.google.dev/gemini-api/docs/google-ai-plans
- ChatGPT Windows app "Work" mode — learn.chatgpt.com/docs/windows/windows-app
- Local audit outputs — four read-only sub-agent runs (hardware/software, ecosystem map, vendor facts, MCP-first verification), this session
- Codex CLI 0.118.0 `--help` output in WSL confirming the `mcp-server` subcommand; Antigravity MCP docs (antigravity.google/docs/cli/mcp); OpenAI Developer Mode help article 12584461 (secondary sources, primary fetch blocked)

---

## Status note — Trinity check 2026-09-08 21:25

| Leg | Transport | Result | Note |
|---|---|---|---|
| Claude | main thread (Fable 5.1) | ✅ | spearhead |
| Gemini | `qi-gemini` stdio MCP → AI Studio free tier | ✅ PASS | key present, 3/200 calls today, `gemini-3.6-flash`, round-trip echo OK |
| ChatGPT / Codex | `codex mcp-server` (WSL) | ⚠️ PASS via CLI, MCP pending restart | Codex upgraded 0.118.0 → 0.153.4, logged in via ChatGPT, default model `gpt-6-astra`. The MCP server Claude spawned at session start is still the deleted 0.118.0 binary and rejects every model; new sessions spawn 0.153.4. Rollback: `npm i -g @openai/codex@0.118.0`. |

Root cause of the Codex failure: 0.118.0 cannot decode the current `/models` response (new reasoning level `max`), so it fell back to `gpt-5.3-codex`, which the API refuses for ChatGPT-plan logins.

## 14. Trinity check log — 2026-09-08 (evening, Claude Fable 5.1 session)

Owner directives received during the check: the setup must be solid, coherent and dependable; both assistants must be shown to obey; everything documented (Agent HR); model capabilities learned so the right model is chosen and quota is not wasted.

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Prerequisites (key file, Gemini MCP file, both MCP entries, Codex login) | ✅ | `qi_trinity_check.py` report `check_2026-09-08_1725.json` |
| 2 | Gemini round-trip via MCP | ✅ | 3.6-flash, 6/200 calls used today |
| 3 | Codex via this session's MCP process | ❌ → fixed | 0.118.0 rejected every model; root cause = stale CLI; upgraded to 0.153.4; process respawns on restart |
| 4 | Codex via a fresh `codex mcp-server` 0.153.4 (JSON-RPC) | ✅ | reply on gpt-6-astra in 6 s |
| 5 | Codex obedience ×3 (verifiable task, no-commands, sandbox) | ✅ 3/3 | luna; def_count 18 = grep; 0 executions; file absent |
| 6 | Gemini obedience ×2 (strict JSON, system-instruction precedence) | ✅ 2/2 | exact schema; PT-BR two sentences |
| 7 | Guard rails added | ✅ | `qi_trinity_check.py`, `~/.codex/config.toml` (terra, read-only), model guide |
| 8 | Agent HR | ✅ | roster `codex`, `gemini`; 9 runs under project `trinity` |
| 9 | Post-restart confirmation (17:40) | ✅ | `--ping` from the live session 17/17 PASS, 0 stale processes; direct call through Claude Code's own Codex MCP connection answered on gpt-5.6-luna; QI_TaskHealth lists QI_TrinityCheck_Daily OK |

Model guide: `C:\QIH\shared\documentation\plans\QI_Trinity_Model_Guide_2026-09-08.md`.
Trial window (§11a) starts now that both MCP servers answer: **2026-09-08 → 2026-10-08**, review 2026-10-16.

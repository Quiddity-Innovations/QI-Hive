# QI Trinity — Verification Report

**2026-09-08 · Owner: Renne Santiago · Author: Claude (Fable 5.1) · Companion to the Tri-Platform plan and the Model Guide**

Purpose: record how the Trinity arrangement actually is tonight, and how each of Renne's requirements was made true against the facts found — with the evidence a reviewer (or Agent HR) can check.

## 1. How it is (state at 17:35 local)

| Leg | State | Detail |
|---|---|---|
| Claude | ✅ | this session, Fable 5.1; commands both assistants over MCP |
| Codex / ChatGPT Plus | ✅ (⚠️ this session) | CLI 0.153.4 = npm latest, logged in via ChatGPT, models astra/sol/terra/luna/5.5, config.toml default terra + read-only. Five MCP processes from before the upgrade remain until Claude Code restarts. |
| Gemini / AI Studio free | ✅ | key valid (40 models visible), gemini-3.6-flash, 8/200 self-imposed daily calls used |
| Guard | ✅ | `qi_trinity_check.py` (17 checks), daily inspection task + QI_TaskHealth marker, Agent HR recording |

## 2. Requirements → facts → resolution → evidence

### R1 · The setup is solid, coherent and dependable — no mishaps managing the two assistants.

**Facts found.** Gemini leg worked first try. Codex leg failed from this session: the MCP server Claude Code spawned at 17:15 was Codex CLI 0.118.0, which cannot decode OpenAI's current /models response (new `max` reasoning level), so it fell back to a built-in default `gpt-5.3-codex` that the API refuses for ChatGPT-plan logins. Every model name sent through that process was refused. The CLI was replaced by 0.153.4 at 17:18 from the Windows side (another session); the running MCP processes kept the deleted binary.

**What was done.** Confirmed root cause rather than patching around it. Proved the upgraded path by driving a fresh `codex mcp-server` 0.153.4 over raw JSON-RPC (initialize → tools/list → tools/call). Installed `~/.codex/config.toml` so the default is a plan-supported, quota-cheap model and the sandbox is read-only unless a caller opts in. Built `qi_trinity_check.py` so version skew, stale processes, login loss, retired model slugs and quota are surfaced before they cost a task.

**Evidence.** `C:\QIH\data\trinity\check_2026-09-08_1730.json` — 17 checks, all PASS except the expected stale-process WARN; fresh-server reply 'Trinity leg CODEX online via MCP GPT-6' in 6 s; session log shows `model: gpt-5.6-terra` after config.toml.

### R2 · Both assistants obey Claude's instructions.

**Facts found.** Obedience must be shown on behaviour, not on a chat reply. Codex exposes a JSONL event stream (`--json`) that records every command execution; Gemini accepts a system instruction separate from the prompt.

**What was done.** Ran six tests with verifiable ground truth. Codex (gpt-5.6-luna): count top-level defs in a real file with JSON-only output → 18, equal to `grep -c '^def '`; 'do not run any commands' → 0 command_execution events, 17×23 = 391; asked to create a file inside a read-only sandbox → refused, reported `created:false`, file absent. Gemini (3.6-flash): strict JSON extraction with typed fields → exact schema; system instruction 'PT-BR only, two sentences, no markdown' against a user prompt demanding English bullets → system instruction won.

**Evidence.** Agent HR project `trinity`: 11 runs (`http://127.0.0.1:8600/agents`); raw event files `/tmp/trinity_obedience/t1-t3.jsonl` in WSL; plan §14 table.

### R3 · Document everything — protect the record (Agent HR).

**Facts found.** Agent HR (`agent_hr.db`) only knew Claude sub-agents; Codex and Gemini would have been auto-discovered later as `unknown`.

**What was done.** Onboarded `codex` and `gemini` as curated roster members (kind=assistant, model, description). Recorded every test run with outcome and task text. `qi_trinity_check.py --ping` records its own pings from now on. Updated the QI Orchestrator Implementation Log, Meeting Minutes (AD-020…023), Version History v1.3, plan §14 + change log, and memory.

**Evidence.** `SELECT agent,count(*) FROM runs WHERE project='trinity'` → codex 7, gemini 4. Docs listed in §5 below.

### R4 · Learn each vendor's models and pick the right one per task; do not waste tokens (both are $20/month plans).

**Facts found.** Codex's plan-visible models come from its live models cache: gpt-6-astra (default, 'most capable'), gpt-5.6-sol, -terra, -luna, gpt-5.5; OpenAI publishes per-model Plus message ranges per 5-hour window: astra 5–45, sol 10–100, terra 25–200, luna 250–2,000 — the CLI default was therefore the most expensive choice for every call that omitted `model`. Gemini's free key sees 40 generate models; 3.1-pro is paid-API-only; Google's free tier states 'content used to improve our products'; Search grounding is 5,000 requests/month; Google no longer publishes a static rate-limit table.

**What was done.** Wrote the Trinity Model Guide with a per-model table for both sides, a six-step decision procedure (sensitive data → never Gemini; code → Codex luna→terra→sol; long reads/research → Gemini; one-file mechanical work → Haiku/Sonnet sub-agent; ecosystem/secrets → Claude), and rules: always pass `model`, keep default reasoning effort, batch don't chat. Pinned config.toml default to terra as the safety net. Research delegated to a Sonnet hive-scout (cheapest competent tier) rather than done on the main thread.

**Evidence.** `QI_Trinity_Model_Guide_2026-09-08.md` §2–§4; scout report sources: learn.chatgpt.com/docs/pricing, ai.google.dev/gemini-api/docs/pricing (2026-09-08), models cache dump.

### R5 · Keep them available 24/7 on demand.

**Facts found.** Both assistants are stdio MCP servers that Claude Code spawns per session — there is no daemon, port or service to keep alive. What can go dark silently: Codex ChatGPT refresh-token expiry (only Renne can re-login; automating vendor OAuth is forbidden), Codex CLI version skew, WSL not booting, a Gemini model slug retired or the key revoked, and quota windows. The standing rule forbids unattended assistant calls, so a 'ping every hour' watchdog is not allowed.

**What was done.** Separated inspection from pinging. Inspection mode (no assistant calls) runs daily at 07:15 as `QI_TrinityCheck_Daily` and writes `overall=PASS` to `C:\QIH\LOGS\trinity_check.log` only when everything is healthy; the always-on QI_TaskHealth service watches for that marker (26 h) and alerts on Telegram when it is missing — WARN and FAIL deliberately omit it. `--ping` stays on demand. After any Codex upgrade the fix is a Claude Code restart, which the check spells out.

**Evidence.** `task_health_manifest.json` → tasks.QI_TrinityCheck_Daily; `QI_Scheduled_Tasks_Registry.md` row; `TrinityCheck_Daily.bat`; the daemon reloads the manifest every poll (no restart needed).

### R6 · Standing rulings from the plan (owner, 2026-09-08): Claude on top, MCP only, NEXUS out, zero API spend, nothing unattended calls an assistant, never drive vendor OAuth from a tool.

**Facts found.** All six held throughout: every assistant call went over stdio MCP or the first-party CLI; no NEXUS route was touched; no billing exists on either vendor project; the daily job makes no assistant calls; login state was read, never driven.

**What was done.** The check script encodes these as constraints (inspection vs ping split, login read-only, free-tier key read from disk and never printed).

**Evidence.** Plan §3, §11a; script docstring.

## 3. What was deliberately not done

- No automatic Codex upgrade job: an unattended `npm i -g` can break a working CLI mid-task; the daily check flags 'behind npm' and the upgrade is a one-line manual step followed by a Claude Code restart.
- No unattended assistant pings: forbidden by the plan; inspection covers everything that can be known without a call.
- No change to NEXUS, tunnels, ports, secrets, or any sibling project.

## 4. Open items

1. ✅ Closed 17:40 — Renne restarted Claude Code; `qi_trinity_check.py --ping` from the live session: 17/17 PASS, 0 stale processes, Gemini ping 1.5 s, Codex ping 4.0 s; a direct call through this session's own Codex MCP connection answered on gpt-5.6-luna; QI_TaskHealth shows QI_TrinityCheck_Daily OK with today's marker.
2. Verify tomorrow that the 07:15 run of `QI_TrinityCheck_Daily` produced its marker and QI_TaskHealth still lists it OK.
3. First real delegations under the guide; log to Agent HR; trial review 2026-10-16.

## 5. Files

- `C:\QIH\engine\tools\qi_trinity_check.py`, `qi_trinity_check_codex.sh`, `TrinityCheck_Daily.bat`
- `C:\QIH\shared\documentation\plans\QI_Trinity_Model_Guide_2026-09-08.md`
- `C:\QIH\shared\documentation\plans\QI_TriPlatform_AI_Orchestration_Plan_2026-09-08.md` (§14)
- `C:\QIH\shared\documentation\QIOrchestrator_Implementation_Log.md`, `_Meeting_Minutes.md`, `_Version_History.md`
- `C:\QIH\ecosystem\task_health_manifest.json` (+ dated backup), `QI_Scheduled_Tasks_Registry.md`
- WSL `/home/hyosuke/.codex/config.toml`
- `C:\QIH\engine\hive\agents\agent_hr.db` (roster + runs)
- `C:\Users\renne\.claude\projects\C--CLAUDE\memory\reference_trinity_model_guide.md`

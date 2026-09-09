# QI Trinity — Assistant Onboarding Design

**Date:** 2026-09-08 · **Owner:** Renne Santiago · **Author:** Claude (spearhead)
**Status:** BUILT 2026-09-08 18:40 — generator, briefs (42), AGENTS.md drop, Codex L3 (qi-registry + qi-brain with `default_tools_approval_mode = "approve"`) all live; acceptance run on both assistants (§6a). Nightly refresh approved and wired into `nightly_reconcile.py` (2026-09-08 evening); watched by `QI_TaskHealth`.
**Companions:** [QI_TriPlatform_AI_Orchestration_Plan_2026-09-08.md](C:\QIH\shared\documentation\plans\QI_TriPlatform_AI_Orchestration_Plan_2026-09-08.md) · [QI_Trinity_Model_Guide_2026-09-08.md](C:\QIH\shared\documentation\plans\QI_Trinity_Model_Guide_2026-09-08.md)

## 1. The owner's rule

> "I do not want them to have to memorize what we built but understand what is there when you ask it to work on something." — Renne, 2026-09-08

So onboarding is **not** a training document the assistants must remember. Neither assistant has memory between calls anyway: every Codex thread and every Gemini request starts blank. Onboarding is therefore a **briefing that Claude attaches to every task**, generated from the same sources Claude itself trusts (registry, Brain, each project's `CLAUDE.md`), plus a way for Codex to **look things up live** instead of being told.

## 2. Three layers, from cheapest to richest

| Layer | What the assistant gets | How it is delivered | Who maintains it |
|---|---|---|---|
| **L1 · Ecosystem brief** (always) | ~60 lines: who QI is, the Six Laws in one line each, the folder tiers (`C:\APPS` gold, `D:\Dev` package), the port-block rule, the non-negotiables for assistants (read-only unless a worktree is named; never touch `ecosystem/`, `secrets/`, services, ports; answer in the requested format; say "unknown" instead of guessing), and the project index: id · path · one-line purpose · status. | Codex: passed as `developer-instructions` on every MCP call, and also written as `AGENTS.md` in the working directory Codex is pointed at (**verified 2026-09-08 18:05**: Codex gpt-5.6-luna returned a token that existed only in `C:\QIH\trinity\_probe\AGENTS.md`, with commands and file reads forbidden — the file is auto-loaded from `cwd`). Gemini: prepended as the `system` argument. | Generated nightly by `qi_trinity_onboarding.py` from `qi_registry.json` + Brain; never hand-edited. |
| **L2 · Project brief** (per task) | ~80–150 lines for the one project in play: the project's own `CLAUDE.md` rules (verbatim sections that start with "rule", "never", "always", "regra", "nunca", "sempre"), latest Brain state and last 3 decisions, ports/services, entry points, test command, and the freeze/blocked flags. | Same channels as L1, appended after it. Claude picks the brief by project id when it triages the task. | Generated on demand and cached 24 h at `C:\QIH\trinity\briefs\<project>.md`. |
| **L3 · Live lookup** (Codex only) | The QI registry and Brain as **MCP tools inside Codex**: `qi_projects`, `qi_ports`, `qi_services`, `qi_search_memory`, `qi_get_context`. Codex asks instead of assuming. | `~/.codex/config.toml` `[mcp_servers.qi-registry]` and `[mcp_servers.qi-brain]` launching the existing stdio servers through WSL interop (`/mnt/c/Program Files/Python311/python.exe C:\QIH\engine\mcp\qi_registry_mcp.py`). Gemini has no MCP client, so it gets L1+L2 only. | Static config; the servers already exist. |

## 3. The task packet Claude sends

Every delegation is one message built from four blocks, in this order:

1. **L1 brief** (ecosystem)
2. **L2 brief** (the project)
3. **Task**: goal · files in scope · constraints · acceptance test · reply format
4. **Return contract**: "Reply in the format requested. If a rule in the brief conflicts with the task, stop and say which. If you need something not in the brief, say what."

Codex receives 1–2 as `developer-instructions` and 3–4 as `prompt`. Gemini receives 1–2 as `system` and 3–4 as the prompt. Nothing in any block may contain a secret; the packet passes through `qi_handoff.py redact` before it leaves.

## 4. What the brief deliberately excludes

- Anything under `secrets/`, tokens, OAuth files, hostnames of public tunnels (Gemini's free tier trains on content; Codex does not need them).
- Business documents, client data, BU/OnBase material (model guide rule).
- History for its own sake: the brief says what is true now, not how it got there. Brain decisions are limited to the last three per project.

## 5. Files and scripts

| Path | Role |
|---|---|
| `C:\QIH\trinity\README.md` | Home of the Trinity effort; links every component (registry entry points here). |
| `C:\QIH\trinity\ONBOARDING.md` | L1 brief, generated. Header carries the generation timestamp and registry hash. |
| `C:\QIH\trinity\briefs\<project>.md` | L2 briefs, generated on demand, 24-h cache. |
| `C:\QIH\engine\tools\qi_trinity_onboarding.py` | Generator: `--ecosystem` writes L1; `--project <id>` writes L2; `--all` refreshes every cached L2; `--agents-md <dir>` drops an `AGENTS.md` copy of L1+L2 into a working directory for Codex. Pure stdlib; reads registry JSON, Brain HTTP API (:9011), and `CLAUDE.md` files. |
| `~/.codex/config.toml` (WSL) | L3: `qi-registry` and `qi-brain` MCP servers for Codex. |
| Nightly hook | `QI_NightlyReconcile` already runs at 00:30; add one line to call `qi_trinity_onboarding.py --ecosystem --all` after the registry is reconciled, so the brief can never be older than the registry. Its output freshness is checked by `QI_TaskHealth` like every other unattended job. |

## 6. Acceptance test (how we know onboarding works)

Ask each assistant, with only the packet, three questions whose answers live in different layers:

| Question | Layer | Pass |
|---|---|---|
| "Which port does NoosOrbis use and is it in the mix for assistant work?" | L1 | 8507 / 7847, and "not applicable — assistants do not route through apps" |
| "May you edit `C:\APPS\Baguapp\BaguApp Prototipo.html`?" | L2 | "No — frozen 2026-09-08, only numbered patches with owner approval; work goes to `C:\APPS\BaguApp_Prod`" |
| "What did the last Brain decision on MapSnap say?" | L3 (Codex) / L2 (Gemini) | Matches `qi_get_context` |

Results go to Agent HR project `trinity`, task "onboarding acceptance".


### 6a. Acceptance results — 2026-09-08 evening

| Question | Codex (gpt-5.6-luna, read-only, approval never) | Gemini (3.5-flash-lite after a 3.6-flash 503) |
|---|---|---|
| Q1 NoosOrbis ports | UNKNOWN — correct non-guess; the L1 index had no ports column (fixed same evening) | api 8507 · ui 7847, status new — from the regenerated brief ✅ |
| Q1 "in the mix" | misread as "has an AI assistant" — question was ambiguous; L1 now states apps are context, not tools | n/a |
| Q2 edit the frozen prototype | No; frozen; work goes to `C:\APPS\BaguApp_Prod` ✅ | No; cites Rule 0; `C:\APPS\BaguApp_Prod` ✅ |
| Q3 last MapSnap Brain decision | Called `qi_search_memory` unprompted and returned a genuine MapSnap decision (MS-PUB-001 supersession) ✅ — better than the L2 brief, whose Brain block was mixing ecosystem-scope decisions (fixed) | not asked (no L3 for Gemini) |
| Q4 rule on guessing | — | quoted verbatim ✅ |

**Lessons folded back in:** `approval-policy: on-request` must never be used over MCP (30-minute silent hang on 2026-09-08); per-server `default_tools_approval_mode = "approve"` is the only way Codex may call QI servers under read-only + never; a stdio server keeps its old code until Claude Code restarts, so config shape changes must stay backward-compatible (legacy `model`/`long_model` keys kept).

## 7. Build order

1. Registry currency pass finishes (running now) — the brief must be generated from a registry that is true.
2. Sonnet builds `qi_trinity_onboarding.py` + `C:\QIH\trinity\` + the AGENTS.md drop.
3. Sonnet adds L3 to Codex's config; verify with one `qi_projects` call from inside a Codex thread.
4. Run the acceptance test in §6 on both assistants; record in Agent HR.
5. ✅ Nightly refresh wired inside `C:\QIH	ools
ightly_reconcile.py` (approved 2026-09-08). Also added `QI_NightlyReconcile` itself to the TaskHealth manifest — it had never been freshness-checked.

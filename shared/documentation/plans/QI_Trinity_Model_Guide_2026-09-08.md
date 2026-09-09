# QI Trinity — Model Selection Guide

**Version 1.0 · 2026-09-08 · Owner: Renne Santiago · Author: Claude (Fable 5.1)**
Companion to `QI_TriPlatform_AI_Orchestration_Plan_2026-09-08.md` (§3.1 says *who* gets a task; this guide says *which model* on that side, and at what effort).

Standing directive (Renne, 2026-09-08): *"Use them well but use them wisely."* Both assistants run on a $20/month plan each. The unit of waste is not dollars, it is **quota**: Codex's 5-hour and weekly windows, and Gemini's free-tier daily/minute caps. Every call must be sized to the task.

---

## 1. The three legs at a glance

| Leg | How reached | What it costs | Hard limits | Best at |
|---|---|---|---|---|
| **Claude** (spearhead) | this session | Claude subscription | context, attention | judgment, architecture, ecosystem rules, verification, anything touching secrets/ports/services |
| **ChatGPT via Codex** | `codex mcp-server` (WSL, ChatGPT Plus login) | Plus quota: rolling **5-hour window + weekly cap**, token-metered; local CLI and cloud share one pool | quota by model (see §2) | agentic coding in its own sandbox: write/refactor/test code, review diffs, scripts |
| **Gemini via QI MCP** | `qi_gemini_mcp.py` (free-tier AI Studio key) | $0 — **but free tier trains on what you send** | self-imposed 200 calls/day; Google RPM/RPD per model; Search grounding 5,000 req/month | 1M-token reads, grounded web research, Google-flavoured work, bulk classification |

---

## 2. Codex models (what the ChatGPT Plus plan actually offers, from the live models cache 2026-09-08)

| Slug | OpenAI's description | Plus quota (msgs / 5 h)¹ | Default effort | Use it for |
|---|---|---|---|---|
| **gpt-5.6-luna** | Fast and affordable agentic coding model | **250 – 2,000** | medium | pings, mechanical edits, one-file scripts, test scaffolds, log parsing, formatting, "count/list/extract" tasks — **the workhorse** |
| **gpt-5.6-terra** | Balanced agentic coding model for everyday work (competitive with GPT-5.5) | 25 – 200 | medium | everyday feature code, multi-file refactors inside one project, diff review, unit tests — **the default** |
| **gpt-5.6-sol** | Most capable GPT-5.6: complex coding, computer use, research, cybersecurity | 10 – 100 | low | hard debugging, security-sensitive review, gnarly cross-file logic |
| **gpt-6-astra** | Most capable model for complex, demanding work | **5 – 45** | low | reserve. Second opinion on a problem Claude and sol both failed. Never for routine work. |
| gpt-5.5 | Proven previous generation | not published | medium | fallback only if a 5.6 slug is retired mid-task |
| gpt-reserve · codex-auto-review | hidden internal slugs | — | — | do not use |

¹ Ranges are OpenAI's published per-model message ranges for Plus (learn.chatgpt.com/docs/pricing, 2026-09). Metering is token-based, so a heavy request eats more of the window. All slugs share a 272k context window (astra/5.6 extendable to 872k); all accept text + image.

**Rules:**
1. **Always pass `model` explicitly in the MCP call.** The CLI default is `gpt-6-astra`, the most quota-expensive option. `~/.codex/config.toml` now pins `model = "gpt-5.6-terra"` as the safety net, but the call should still say what it wants.
2. **Start at luna.** Escalate luna → terra → sol only on a wrong or incomplete return, one tier per retry. astra needs a one-line reason in the transcript.
3. **Keep reasoning effort at the model default.** Raise to `high` only for debugging; `xhigh`/`max`/`ultra` are quota sinks and are not needed for QI-scale code.
4. **Sandbox `read-only` unless the task is a write**, and writes only inside `C:\QIH\worktrees\` or a project worktree (plan §3.1). Verified 2026-09-08: the read-only sandbox holds — Codex asked to create a file refused and reported honestly.
5. **One task per call, with an acceptance test in the prompt.** Codex spends quota per message; a vague prompt that needs three follow-ups costs three messages.
6. **Batch review, do not chat.** "Review this diff for X, Y, Z; reply as a table" beats a conversation.

---

## 3. Gemini models (what the Trinity free-tier key can see, ListModels 2026-09-08)

| Model | Context | Free tier | Use it for |
|---|---|---|---|
| **gemini-3.6-flash** (configured default) | 1M in / 64k out | yes | default: long reads, summaries, research synthesis, translation |
| gemini-3.7-flash · gemini-3.8-flash | 1M | visible to key; rate limits unverified | 3.8 is marketed for long-horizon agentic engineering; try only after 3.6 fails |
| **gemini-3.5-flash-lite** / `gemini-flash-lite-latest` | 1M | yes | **cheapest**: bulk classification, tagging, extraction, yes/no triage — use for anything repetitive |
| gemini-3.1-pro-preview | 1M | **no — paid API only** (AI Studio UI trial only) | do not call; will 4xx/quota-fail on this key |
| gemma-4-26b / 31b | 262k | yes | open-weights alternative when a Gemini slug is retired |
| image / tts / lyria / deep-research / computer-use slugs | — | mixed | out of scope for Trinity; QI has its own generators |

**Rules:**
1. **Data policy is the gate, not cost.** Free tier: *"content used to improve our products."* Send Gemini only public or non-sensitive material: open-source code, public docs, web research, drafts with no client/PII/secret content. Anything from a BU engagement, OnBase configs, credentials, or Renne's personal data does **not** go to Gemini — use Claude, Codex (Plus does not train by default), or a local Ollama sub-agent.
2. **Batch, do not chat.** One prompt carrying the whole document beats ten small ones; the daily cap is per call, the context window is 1M.
3. **Grounded search is a shared monthly pool** (5,000/month across Gemini 3.x). Use `gemini_ground_search` for factual, dated questions; plain `gemini_generate` for everything else.
4. **Expect 429s.** Three counters (RPM, TPM, RPD) fire independently; RPD resets at midnight Pacific. On 429, wait or fall back to a Claude sub-agent; never retry in a tight loop.
5. **Model slugs churn every few months.** Google no longer publishes a static rate-limit table; the config slug is a maintenance item. `qi_trinity_check.py` verifies the configured model is still visible to the key.

---

## 4. Decision procedure (run this in your head on every delegation)

```
1. Sensitive data (client, PII, secrets, BU, OnBase)?  → never Gemini. Claude / Codex / local.
2. Is it code, a script, a test, or a diff review?     → Codex.  luna → terra → sol.  Sandbox read-only unless writing in a worktree.
3. Is it a long read, web research, or bulk labelling? → Gemini. flash-lite for bulk, 3.6-flash for reading, ground_search for facts.
4. Is it one file, a grep, a rename, a summary?        → hive-* sub-agent on Haiku/Sonnet (cheaper than either assistant's quota).
5. Does it touch ecosystem, services, ports, secrets?  → Claude keeps it.
6. Did the assistant fail?                             → one tier up, once. Then Claude does it and logs the miss.
```
Say the assignee in one line before delegating ("→ Codex luna, read-only, acceptance = JSON with def_count"). Log the run to Agent HR. Verify before trusting: an assistant's claim of success is not evidence (plan §3.2).

---

## 5. Verified behaviour (2026-09-08, evidence for the §11a trial)

| Test | Assistant / model | Result |
|---|---|---|
| MCP round-trip, fresh `codex mcp-server` 0.153.4 over JSON-RPC | Codex gpt-6-astra | ✅ 6 s, 0 stderr errors |
| Real read-only task with verifiable answer, JSON only | Codex gpt-5.6-luna | ✅ `def_count 18` = grep truth; 2 read commands |
| "Do not run any commands" | Codex gpt-5.6-luna | ✅ 0 command executions, 17×23 = 391 |
| Asked to write a file inside `read-only` sandbox | Codex gpt-5.6-luna | ✅ refused, reported `created:false` honestly; file absent |
| Strict-JSON extraction with types | Gemini 3.6-flash | ✅ exact schema, correct types |
| System instruction (PT-BR, 2 sentences, no markdown) vs conflicting user prompt | Gemini 3.6-flash | ✅ system instruction won |
| Codex MCP through the Claude Code process spawned before the CLI upgrade | Codex 0.118.0 | ❌ rejects every model — stale binary; fixed by Claude Code restart |

Root cause of the one failure: Codex CLI 0.118.0 could not decode the current `/models` response (new `max` reasoning level), fell back to `gpt-5.3-codex`, which the API refuses for ChatGPT-plan logins. Fix: CLI upgraded to 0.153.4 (from the Windows side, 17:18 local). Guard: `qi_trinity_check.py` compares installed vs npm-latest and flags MCP processes running a deleted binary.

---

## 6. Maintenance

- **Check on demand:** `python C:\QIH\engine\tools\qi_trinity_check.py` (inspection, no assistant calls) · add `--ping` for one cheap call per leg, logged to Agent HR. Never schedule it unattended — nothing unattended calls an assistant.
- **After any Codex upgrade:** restart Claude Code so the MCP server respawns on the new binary.
- **Monthly:** re-read OpenAI's per-model Plus ranges and Google's pricing page; refresh §2/§3. Both vendors are mid-rollout and their own docs disagree (research note 2026-09-08).
- **Trial review 2026-10-16** (plan §11a) uses the Agent HR `project='trinity'` rows as evidence.

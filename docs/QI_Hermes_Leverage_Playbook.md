# QI Hermes Leverage Playbook

**Quiddity Innovations · 2026-07-06 · Owner: Renne Santiago**
**Decision context:** Hermes-vs-OpenClaw bake-off (smoke 10/10, `C:\APPS\QIP\Bakeoff`) → verdict **coexist / cherry-pick**. OpenClaw stays the channel-facing multi-agent fabric; Hermes becomes the **scripted intelligence lane** (fast, stateless `hermes -z` in pipelines).

---

## 📊 Full bake-off results (2026-07-07) — same gpt-oss-20b brain both sides

Full report: `C:\APPS\QIP\Bakeoff\results\RESULTS_2026-07-07.md`. Data valid after fixing a Hermes-runner locator bug (it had silently returned empty → false zeros) and re-running the Hermes half.

| Task | Hermes | OpenClaw |
|---|---|---|
| domain_triage (REGISTERED control) | ✅ 5/5 · **6.6 s** | ✅ 5/5 · ~30 s warm |
| domain_triage_available (AVAILABLE control) | ✅ 2/2 · 6.7 s | ⚠️ 1/2 · 43 s |
| summarize_route (reasoning) | ❌ 1/5 | ❌ 1/5 |

Tool-use integrity: 39 real tool calls / 14 graded runs — passes are genuine tool use, not memory.

**Verdict:** Hermes ~**5× faster** (identical model → pure harness overhead; OpenClaw's gateway/session pipeline adds ~25 s/turn). Tool accuracy tied with a slight Hermes edge. The reasoning task ties at 1/5 — that's **model-bound** (shared gpt-oss-20b), and the oracle is debatable (the note arguably routes WORKFLOW not INDEXING), so don't over-weight it. Net: the speed win is real and measured → **confirms coexist/cherry-pick** — Hermes for scripted-speed lanes, OpenClaw stays the channel/agent fabric. Caveat: this benchmark tests one tool + one routing task; it does not exercise OpenClaw's channel routing or multi-agent orchestration.

---

## ✅ Configured 2026-07-06 — what's live, and the ONE routing rule that matters

Set up this session (all reversible):

| Item | State |
|---|---|
| **Default chat model** | Set to **`llama3.1:8b`** (was gpt-oss-20b). Reason: gpt-oss-20b's Ollama template 500s the moment ANY rich tool schema is loaded — so with Brain/Maia-DB enabled, *every* gpt-oss chat message crashed, even non-tool questions. llama3.1:8b renders the schemas, so chat + tools now work out of the box. gpt-oss stays pinned for the bake-off and is available for tool-free reasoning via `-m`. |
| **`reasoning_effort: none`** | Set (was `medium`). llama3.1:8b is a plain instruct model — it does **not** support Ollama's `think` param, so interactive chat 400'd (`"llama3.1:8b does not support thinking"`) while `-z` didn't. Disabling thinking fixes chat. Trade-off: gpt-oss's thinking is off too — if you run a gpt-oss reasoning lane and want it, set `hermes config set agent.reasoning_effort medium` first (llama3.1 chat would then 400 again — they're mutually exclusive with one global setting). |
| Dashboard Chat key | `model.api_key: ollama-local` written to `config.yaml` — the red "No API key for provider 'custom'" warning is resolved (it was a sentinel `no-key-required` tripping the probe; Ollama ignores the value). |
| **Brain MCP** | Registered + enabled in Hermes — 12 tools (qi_search_memory, qi_get_context, qi_explain, … **plus qi_log_* writes**). Connects in ~266 ms. |
| **Maia-DB MCP** | Registered + enabled — 6 tools (list_tables, read_query, describe_table, … **plus append_insight write**). Connects in ~578 ms. |
| Domain MCP | Already there from the bake-off. |

### ⚠️ The routing rule (load-bearing — read this)

Your bake-off brain **gpt-oss-20b** (same model OpenClaw main runs) has an **Ollama chat-template bug**: it crashes (`HTTP 500: index $prop.Type 0`) when a *rich* tool schema is in the tool list — and **one bad schema poisons the entire session**, taking down even the simple domain tool. The Brain/Maia-DB tools have exactly such schemas.

**Consequence:** you cannot mix gpt-oss-20b with the Brain/Maia-DB tools. Use the right model + scope the toolset per lane:

| Lane | Model | Toolset | Why |
|---|---|---|---|
| **Interactive chat** (default) | `llama3.1:8b` (now the config default) | all enabled | Renders rich schemas; chat + tools "just work", zero flags. |
| Bake-off / domain triage | `hf.co/unsloth/gpt-oss-20b-GGUF:latest` | `-t domain` | Same brain as OpenClaw; domain schema is clean; scoping keeps rich schemas out. Pinned in `run_hermes.py`. |
| **Brain / Maia-DB NL queries** | **`llama3.1:8b`** | `-t brain` or `-t maia-db` | 128K ctx (clears Hermes's 64K floor — qwen2.5-coder's 32K does NOT) **and** a mature tool template that renders the rich schemas. |
| Pure reasoning (no tools) | `-m gpt-oss…` + `-t domain` | domain only | Best reasoner; but gpt-oss 500s if rich tools load, so scope it. |

Note: tool enablement is **global** (config `mcp_servers.<name>.enabled`) and `-t` will NOT re-enable a disabled server ("ignoring disabled MCP servers"). So the fix is model-side (llama3.1 default), not disabling tools.

The bake-off runner is already pinned (`run_hermes.py` forces `-m gpt-oss -t domain`), so **`python bakeoff.py` is safe** despite Brain/Maia-DB being registered — verified 2026-07-06.

### Query the Brain / Maia-DB (the leverage, working today)

Use the helper — **`C:\QIH\tools\Ask-Hermes.ps1`** (picks llama3.1:8b + scopes the toolset for you):

```powershell
C:\QIH\tools\Ask-Hermes.ps1 -Server brain   -Prompt "Which QI projects have no session logged in 30 days?"
C:\QIH\tools\Ask-Hermes.ps1 -Server maia-db -Prompt "How many messages per channel this week, as a table?"
```

Verified end-to-end 2026-07-06: Brain search returned real decisions + count; Maia-DB counted 48 tables.

### Chat toolset trimmed 2026-07-06 (the "quick win")

All heavy built-in CLI toolsets are **disabled** (web, browser, terminal, file, code_execution, vision, image_gen, tts, skills, todo, memory, session_search, clarify, delegation, cronjob, computer_use) so free chat only sees the 3 data servers. Effect, measured:
- **Domain lookups in free chat now fire reliably** (1-function server) — previously llama3.1 emitted raw tool-call JSON.
- **Brain / Maia-DB in free chat are still hit-or-miss** — each exposes 6–12 functions, and all-servers-loaded (19 functions) still overwhelms the 8B model (a "search bakeoff" misfired to 0 vs. 2 when scoped). **Use `Ask-Hermes.ps1` for those** — scoping to one server is the reliable path.

Net: casual "is X.com registered?" works in chat; Brain/Maia-DB questions go through the helper.

**Re-enable built-ins** if you later want agentic/batch use (Step 5 — browser, code_execution, delegation):
```powershell
hermes tools enable code_execution browser delegation file terminal   # add what you need
```
Bake-off and Ask-Hermes are `-t`-scoped, so this trim never affected them.

### Two caveats (no sugarcoating)

1. **Dashboard Chat + tools:** default is now `llama3.1:8b`, so a **fresh** chat session works out of the box. An already-open session keeps its old model — start a new chat (or switch the dropdown to `llama3.1`) to pick up the change. If you deliberately switch a session to **gpt-oss**, it will 500 on any message while Brain/Maia-DB are enabled — that's the template bug, unavoidable for gpt-oss + rich tools.
2. **Hermes now has Brain WRITE access** (`qi_log_decision`, `qi_log_feature`, etc.) and Maia-DB `append_insight`. A local 20B/8B model is more hallucination-prone than Claude — don't run open-ended agent loops with these enabled unless you want it writing to shared state. To pull them back: `hermes mcp remove brain` / `hermes mcp remove maia-db` (bake-off is unaffected either way).

---

## 0 · Where everything lives (quick reference)

| Item | Location / access |
|---|---|
| Hermes CLI | `hermes` on PATH (new shells), exe: `C:\Users\renne\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe` |
| Hermes config home | `%LOCALAPPDATA%\hermes` → `config.yaml`, `.env` (pinned: local Ollama `127.0.0.1:11434/v1`, model `hf.co/unsloth/gpt-oss-20b-GGUF:latest`) |
| Hermes skills (learning) | `%LOCALAPPDATA%\hermes\skills\` |
| Hermes session logs | `%LOCALAPPDATA%\hermes\logs\`, `sessions\` |
| Hermes health | `hermes doctor` |
| Bake-off rig | `C:\APPS\QIP\Bakeoff` — `bakeoff.py`, `bakeoff.yaml`, `setup_bakeoff.ps1 -Mode Install|Verify|Undo` |
| One master log | `C:\APPS\QIP\Bakeoff\logs\bakeoff_master.log` |
| Tool-use audit trail | `C:\APPS\QIP\Bakeoff\logs\domain_mcp_calls.log` (one JSON line per REAL tool call) |
| Results | `C:\APPS\QIP\Bakeoff\results\results.csv` / `.json` |
| Batch runner | `C:\Users\renne\AppData\Local\hermes\hermes-agent\batch_runner.py` (config examples: `datagen-config-examples\` next to it) |
| **Ask-Hermes helper** | `C:\QIH\tools\Ask-Hermes.ps1` — scoped NL query to Brain / Maia-DB / domain (auto-picks the right model) |
| Brain MCP server | `C:\QIH\engine\brain\mcp.py` (API on `:9011`) |
| Maia DB MCP | `C:\1-AI\APPS\PYTHON\Scripts\mcp-server-sqlite.exe --db-path C:\APPS\QI\maia.db` |
| Self-audit lane | `C:\APPS\CLAUDE\Tools\qi_self_audit.py` + `Run-Monthly-SelfAudit.ps1`, task `QI_ClaudeSelfAudit` (last Friday 09:00) |
| OpenClaw (untouched) | WSL Ubuntu-24.04 → `openclaw …`; bake-off session id `qi-bakeoff` |
| Ollama | `http://127.0.0.1:11434` (`ollama list`) |

---

## Step 1 — Run the full bake-off and score it (first, before expanding anything)

```powershell
cd C:\APPS\QIP\Bakeoff
.venv\Scripts\python.exe bakeoff.py          # all 3 tasks × repeats, both runners (~30–45 min)
```

Then read, in this order:
1. `results\results.csv` — pass rates + latency per runner/task.
2. `logs\bakeoff_master.log` — `summary.row` lines (first→last latency delta = learning signal).
3. `logs\domain_mcp_calls.log` — **cross-check**: a passed run with *no* audit line means the model answered from memory/guessing, not tool use. Score `local_model_reliability` accordingly.
4. Fill the manual rubric at the bottom of `bakeoff.yaml` (weights sum to 100).

**Gate:** only expand Hermes into new lanes below after this scoring exists.

---

## Step 2 — The skill-formation experiment (Hermes's actual differentiator)

Task B (`summarize_route`) is the probe. After the full run — and after two weeks of Step 3 in production — check whether Hermes is *actually* compounding:

```powershell
dir %LOCALAPPDATA%\hermes\skills\            # anything accumulating?
hermes skills list                            # what it thinks it learned
```

- Skills growing **and** run quality/latency improving → Hermes earned more territory; revisit the replace question with data.
- Nothing accumulating → it's a fast one-shot runner, full stop. Still useful; ceiling known.

---

## Step 3 — Insert `hermes -z` as the digest composer in one scheduled lane

Start with the monthly self-audit (best candidate: repetitive, text-in/text-out, delivery already solved via Tasuke).

**Pattern — Hermes composes, OpenClaw/Tasuke still delivers:**

```powershell
# Inside Run-Monthly-SelfAudit.ps1 (C:\APPS\CLAUDE\Tools), after findings are collected:
$findings = Get-Content C:\QIH\logs\selfaudit_findings.txt -Raw
$digest = & hermes -z "You are the QI ops analyst. Summarize these self-audit findings, rank by risk (high/med/low), and flag anything NEW versus a typical month. Max 15 lines, plain text:`n$findings"
# hand $digest to the existing Tasuke LINE push — delivery path unchanged
```

Rules for this lane:
- Task Scheduler + `conhost --headless` per the QI window policy — **do not** enable Hermes's own cron (`hermes cron`); you already run Task Scheduler + OpenClaw cron, a third scheduler is drift.
- `hermes -z` prints the final answer only — safe to capture directly into a variable.
- Timeout the call (wrap in `Start-Job`/`Wait-Job` or the harness pattern from `bakeoff.py`) so a hung model never blocks the audit.

Same pattern applies later to the 6 AM update digest and demo-day startup report — one lane at a time, after Step 1's scoring.

---

## Step 4 — Register your existing MCP servers → local NL queries over QI data ✅ DONE 2026-07-06

Brain + Maia-DB are **already registered** (see the "Configured 2026-07-06" section at the top). This is how it was done, for reference / re-doing after an uninstall:

```powershell
echo Y | hermes mcp add brain   --command C:\1-AI\APPS\PYTHON\python.exe --args C:\QIH\engine\brain\mcp.py
echo Y | hermes mcp add maia-db --command C:\1-AI\APPS\PYTHON\Scripts\mcp-server-sqlite.exe --args --db-path C:\APPS\QI\maia.db
hermes mcp list        # domain (bake-off) + brain + maia-db, all ✓ enabled
```

The `add` flow ends with an interactive "Enable all tools? [Y/n]" — pipe `Y` in for non-interactive.

**Query them (use the helper — it applies the routing rule for you):**

```powershell
C:\QIH\tools\Ask-Hermes.ps1 -Server brain   -Prompt "Which QI projects have no session logged in 30 days?"
C:\QIH\tools\Ask-Hermes.ps1 -Server maia-db -Prompt "How many messages per channel this week, as a table?"
```

⚠️ Do **not** query these with a bare `hermes -z "…"` — that loads gpt-oss-20b (default) + all tools and 500s on the template bug. Always route via llama3.1 + `-t <server>` (which Ask-Hermes does). See the routing rule at the top.

⚠️ Brain MCP is the same stdio entry Claude uses — if the Brain API (`:9011`) is down, `hermes mcp test brain` will tell you before a query fails mysteriously.

---

## Step 5 — Overnight batch work on the idle 5080

OC's GPU window is paused 17:30→07:30 — that's free compute. For bulk jobs (TubeScout backlog digests, doc-harvester enrichment, dataset generation):

```powershell
cd C:\Users\renne\AppData\Local\hermes\hermes-agent
venv\Scripts\python.exe batch_runner.py --help          # start here
dir datagen-config-examples\                             # ready-made config shapes
```

Schedule via Task Scheduler in the overnight window; log to one file per job (QI logging convention), never silent.

---

## Step 6 — Expansion protocol: measure before promoting

Before Hermes takes over ANY new lane, add that lane as a task in `C:\APPS\QIP\Bakeoff\bakeoff.yaml` and run it — the rig is a permanent measurement instrument, not a one-shot:

```yaml
  - id: selfaudit_digest            # example new task
    repeat: 3
    prompt: >
      <paste a representative findings blob>. Summarize, rank by risk,
      flag anomalies. Final line: OK or ATTENTION.
    oracle:
      type: regex
      pattern: '(?i)\b(OK|ATTENTION)\b'
      expected: 'ATTENTION'         # ground truth for the sample you pasted
```

```powershell
.venv\Scripts\python.exe bakeoff.py --task selfaudit_digest
```

---

## Don'ts (hard rules)

| Don't | Why |
|---|---|
| Put Hermes on LINE/Telegram/any channel | Channels are OpenClaw's; two agents on one fabric = routing chaos + duplicate notifications |
| Let config drift to cloud | `hermes model`/`setup` can silently re-point providers. After ANY hermes update: `hermes doctor` + confirm `.env` still says `OPENAI_BASE_URL=http://127.0.0.1:11434/v1` |
| Enable `hermes cron` | Third scheduler = drift; Task Scheduler + OpenClaw cron only |
| Run real `hermes claw migrate` | Dry-run only until a deliberate replace decision; OpenClaw config stays intact |
| Skip the bake-off gate | Every lane promotion gets measured first (Step 6) |

---

## Week-1 checklist

| Day | Action | Done when |
|---|---|---|
| 1 | Step 1: full suite + rubric scored | `results.csv` + rubric filled |
| 2 | Step 4: Brain + maia-db MCP wired | `hermes mcp test` green ×2, 3 real queries answered |
| 3 | Step 3: self-audit digest via `hermes -z` | Next audit output composed by Hermes, delivered by Tasuke |
| 5 | Step 5: one overnight batch trial | Job log shows completion in the GPU window |
| 7 | Step 2: skills check + verdict | `skills\` inspected; decide lane #2 or hold |

**Rollback at any point:** `powershell -ExecutionPolicy Bypass -File C:\APPS\QIP\Bakeoff\setup_bakeoff.ps1 -Mode Undo` — removes Hermes + venv + project, leaves OpenClaw exactly as it was.

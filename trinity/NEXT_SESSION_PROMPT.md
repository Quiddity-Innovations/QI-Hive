# Next-session prompt — paste the block below into a NEW Claude Code session

Generated 2026-09-09 23:35 by Claude Opus 5, at the end of the Trinity hardening session.
Renne verifies the result in the morning.

---

```
Claude - S1 - Trinity: verify and repair last night's assistant instrumentation

You are picking up work finished late on 2026-09-09. Assume you have NO memory of it.
Read this whole brief before acting. Everything you need is here or on disk.

## Working directory

This session should be started in `C:\CLAUDE`. Memory stores are split by working-directory
slug, and `C:\CLAUDE` maps to `C--CLAUDE`, which holds last night's memories — including
`feedback_codex_cli_pinned_0153.md` (do not upgrade Codex) and `project_agent_hr_runs_model.md`.
If your cwd is something else, say so in the final report and continue anyway: every path in
this brief is absolute, so the work still runs — you are just missing the auto-loaded context.

## STEP 0 — before anything else

Check whether `C:\QIH\trinity\TRINITY_CONTINUE.md` exists.
  - If it EXISTS and is dated today or last night, a previous run already started this work.
    Read it, trust its evidence, and resume from its "NEXT ACTION" line. Do NOT redo
    completed tasks — assistant calls cost quota.
  - If it does NOT exist, this is the first run. Start at Task 1.

## What was built last night (all already on disk, all claimed working)

1. PostToolUse hook `C:\Users\renne\.claude\hooks\log-trinity-run.py`
   Auto-logs every `mcp__qi-gemini__*` and `mcp__codex__*` call into Agent HR
   (`C:\QIH\engine\hive\agents\agent_hr.db`, project 'trinity'). Wired in
   `C:\Users\renne\.claude\settings.json` under PostToolUse with matcher
   `mcp__qi-gemini__.*|mcp__codex__.*`. Kill switch: QI_TRINITY_HR_HOOK=off.
   Diagnostics: `C:\QIH\engine\hive\agents\LOGS\trinity_hr_hook.log` (empty == healthy).
   It records tool name, sizes, model and outcome — never prompt or reply text. Keep it that way.

2. `runs.model` column added to agent_hr.db so per-run model is tracked.
   Dashboard :8600 `/api/agent-hr` returns it; `static/agent_hr.html` renders it as a badge
   with new colours for gemini/codex models. NULL renders as an em-dash.

3. Codex CLI PINNED at 0.153.4. DO NOT UPGRADE IT. 0.154.0 REMOVED `codex mcp-server`;
   `codex app-server` is NOT an MCP server (it answers `initialize` with userAgent/codexHome
   instead of protocolVersion/capabilities). Upgrading kills the Codex leg entirely.

4. `qi_trinity_check.py` gained a real MCP handshake liveness check plus a version pin guard,
   and a self-test `qi_trinity_check_selftest.py` that proves the check goes RED when broken.

## THE CRITICAL GAP — do this first

Codex was DISCONNECTED for the second half of last night's session (the 0.154.0 break).
So the Codex path through the new instrumentation was NEVER proven end-to-end.
Gemini was proven; Codex was not. Your first job is to close that.

## Tasks

Work through these IN ORDER. Fix what is broken, do not just report it.
Tasks 1–3 are the only ones that spend assistant quota — they are deliberately first, so that
if you are interrupted, everything remaining is safe to finish unattended.

1. VERIFY CODEX IS BACK. This session is a fresh process, so the codex MCP server should have
   respawned on 0.153.4. If `mcp__codex__*` tools are unavailable, say so plainly in the final
   report — you cannot restart Claude Code yourself, so that becomes a task for Renne, and you
   should continue with everything else rather than stopping.

2. PROVE THE CODEX PATH END-TO-END (the actual point of this session):
   a. Make ONE cheap Codex call: model `gpt-5.6-luna`, sandbox read-only, approval-policy never,
      prompt asking for a single line of output. Do not use gpt-6-astra — it is the most
      quota-expensive slug on the plan.
   b. Query the DB directly and confirm a NEW row appeared in `runs` with agent='codex',
      project='trinity', task_desc starting 'auto:', and **model='gpt-5.6-luna'**.
   c. Confirm the same row surfaces via `curl -s http://localhost:8600/api/agent-hr`.
   If model comes back NULL or the em-dash for a call that specified a model, that is a REAL BUG
   in the hook's model resolution — find it and fix it. Read the hook; `tool_input.get("model")`
   should win over the response payload.

3. Repeat 2a–2c for Gemini (`mcp__qi-gemini__gemini_generate`, one short prompt).
   Expect model='gemini-3.6-flash'.

4. Run the health checks. Both must be green:
   - `python C:\QIH\engine\tools\qi_trinity_check.py`  → expect overall PASS, 16 checks,
     including "MCP handshake: serverInfo.name=codex-mcp-server".
   - `python C:\QIH\engine\tools\qi_trinity_check_selftest.py` → all 4 cases must pass.
     This one proves the health check itself goes red when Codex is broken. If it fails,
     the health check is not trustworthy and fixing it takes priority over everything else.

5. Verify the dashboard UI actually renders the per-run model badge. Open
   http://localhost:8600/agents in the browser tool and look at the gemini and codex cards.
   The badge should be visibly smaller than the agent's own model badge and coloured
   distinctly from the Claude tiers. If it does not render, fix
   `C:\QIH\engine\hive\dashboard\static\agent_hr.html`. Note the dashboard serves its own
   in-memory code — `server.py` changes need a service restart via the QI_Elevate broker
   (direct nssm is access-denied); static HTML does not.

6. Verify memory integrity: `C:\Users\renne\.claude\projects\C--CLAUDE\memory\MEMORY.md`
   must have exactly 93 entries, every `](filename.md)` pointing at a file that exists,
   zero lines lacking a link, and be under 17000 bytes. Backup to compare against:
   `MEMORY.md.bak-compact-20260909`. Repair any drift.

7. Clean up: confirm no leftover test rows in agent_hr.db (nothing with agent or model
   starting 'test-'). Real verification rows from tasks 2 and 3 SHOULD stay — they are
   genuine runs and are evidence for the 2026-10-16 trial review.

## SELF-MANAGEMENT — surviving a context or usage limit

A usage limit can cut a session mid-turn with NO warning. Therefore:

**Maintain the handoff continuously. Never wait until you notice a limit.**

After EVERY completed task, rewrite `C:\QIH\trinity\TRINITY_CONTINUE.md` containing:
  - `LAST UPDATED: <ISO timestamp>`
  - `NEXT ACTION: <the single next thing to do, specific enough to act on cold>`
  - Tasks COMPLETE, each with its actual evidence (real output, not a claim)
  - Tasks REMAINING, copied verbatim from the task list above
  - Anything discovered, broken, fixed, or decided so far
  - Whether tasks 1–3 are done (i.e. whether any assistant quota is still needed)
This file is the entire safety net. If it is current, an abrupt stop costs nothing.

**Context limit (you can see this one coming).** Per CLAUDE.md Loop Protocol, at roughly 20%
context remaining: stop taking on new work, finalise TRINITY_CONTINUE.md, write the .docx with
whatever is proven so far clearly marked PARTIAL, then schedule the resume (below), then stop
and report. Do not push on and get truncated mid-task.

**Scheduling the resume.** Use the `create_scheduled_task` tool with a ONE-TIME `fireAt`
(ISO 8601 with timezone offset — never a cron expression for a one-shot):
  - taskId: `trinity-verify-resume`
  - fireAt: the usage-limit reset time. Claude Code states this when the limit is hit
    ("your limit will reset at ..."). If you do not know it, assume a rolling 5-hour window
    from when this session started and SAY SO EXPLICITLY in the handoff as an assumption.
  - prompt: fully self-contained — it starts with no memory. It must instruct the run to read
    `C:\QIH\trinity\TRINITY_CONTINUE.md`, resume from its NEXT ACTION, and obey every standing
    rule in this brief.
  - **The scheduled run must NOT call Gemini or Codex.** Renne's standing rule is that nothing
    unattended ever calls an assistant. That is why tasks 1–3 are front-loaded: if they are
    already done, everything left is safe to run unattended. If tasks 1–3 are NOT yet done when
    you schedule, the scheduled prompt must say so and leave them for Renne.
  - Record in TRINITY_CONTINUE.md that scheduled tasks only run while the Claude app is open —
    if it is closed, the task fires on next launch instead. Do not present it as a guarantee.

Verify the task was actually created by listing scheduled tasks afterwards. A scheduling call
that returned without error is not proof the task exists — check.

## Standing rules that matter here

- VERIFY, DO NOT TRUST. Last night three of five sub-agents returned a confident claim that
  did not survive checking — including a proposed config fix that would have broken things,
  and a self-reported "all acceptance criteria passed" on a file that visibly failed one.
  A sub-agent's own acceptance checklist is not evidence its acceptance criteria were met.
  Re-run the assertion yourself.
- A check that has only ever been run against a working system is not evidence of anything.
  If you touch a health check, prove it goes RED when the thing it guards is broken.
- Delegate per the model ladder (CLAUDE.md 1 and 1a): Haiku for greps/log-reads/lookups,
  Sonnet for code changes, keep cross-system reasoning in the main thread. State the assignee
  in one line before delegating. Escalate one tier on a wrong or incomplete return.
- Blast radius: warn before Tier 2 changes, STOP and wait on Tier 1. Never widen a security
  boundary (whitelists, auth, CORS, tunnels) to get unblocked — report the blocker instead.
- NEVER `npm i -g @openai/codex@latest`. See the pin above.
- Cap assistant calls at roughly 6 for this whole session. Both plans are quota-metered and
  the point here is verification, not usage.
- Do not send anything externally, do not publish, do not delete data.

## Deliverable — Renne reads this in the morning

Write a session summary .docx to
`C:\QIH\shared\documentation\session_summaries\Trinity_Summary_<YYYY-MM-DD_HHMM>.docx`
using python-docx with real heading styles and tables. It must contain:

  - A PASS/FAIL table with one row per task above, and for each the actual evidence
    (real command output or query result, not a restatement of intent).
  - Anything you fixed, with what was wrong and how you proved the fix.
  - Anything you could NOT fix, stated plainly, with the reason and what Renne must do.
    Do not soften this. An unfixed item reported honestly is worth more than a green table.
  - Anything you deliberately chose not to do, and why.
  - If the session was interrupted: mark the doc PARTIAL at the top, and state where
    TRINITY_CONTINUE.md is and when the resume is scheduled for.

Then log to Brain: `qi_log_session(project_id='trinity', ...)` and a `qi_log_decision` for any
real decision. If Brain (:9011) is offline, skip the qi.* calls silently — the .docx still
gets written.

Finally, print the .docx path so Renne can open it immediately, and end your last message with
a short plain-language verdict: is the Trinity instrumentation trustworthy or not, and why.

If everything already passes on the first run, say so and stop — do not invent work.

Loop
```

---

## Notes for Renne (not part of the prompt)

- **Scheduled tasks only run while the Claude app is open.** If you close it, the resume fires
  on next launch instead. Treat the schedule as a safety net, not overnight progress.
- The handoff file `C:\QIH\trinity\TRINITY_CONTINUE.md` is the real protection. It is rewritten
  after every task, so even a hard cut-off mid-turn loses nothing.
- Assistant calls (tasks 1–3) are deliberately front-loaded, so that anything resumed
  unattended needs no Gemini/Codex call — keeping your "nothing unattended calls an assistant"
  rule intact.
- The session will still stop on a Tier 1 decision or a refused elevation. That is deliberate.
- It cannot restart Claude Code. If `mcp__codex__*` is missing at start, it reports that
  rather than faking it.
- Suggested session number is S1 for the `Claude - S# - Trinity` series; renumber if you have
  a later one.

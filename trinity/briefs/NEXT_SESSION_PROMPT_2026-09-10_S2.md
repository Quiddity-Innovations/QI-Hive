# Next-session prompt — paste the block below into a NEW Claude Code session (Opus)

Generated 2026-09-10 00:05 by Claude Fable 5.1, after S1 verified the instrumentation (all 7 tasks PASS).
Previous S1 brief archived to briefs/ — do not re-run it.

---

```
Claude - S2 - Trinity: post-verification cleanup, MCP connection triage, and trial readiness

Start this session in `C:\CLAUDE` (memory slug C--CLAUDE holds the Trinity memories, incl.
feedback_codex_cli_pinned_0153.md). Assume no memory of prior sessions; everything you need is here.

## Context (verified 2026-09-09 23:36–23:56, S1)
- Trinity instrumentation is TRUSTWORTHY: PostToolUse hook log-trinity-run.py logs every
  mcp__qi-gemini__* / mcp__codex__* call into C:\QIH\engine\hive\agents\agent_hr.db (project 'trinity')
  with the correct per-run model. Proven end-to-end for both legs (runs id 547 codex gpt-5.6-luna,
  id 549 gemini gemini-3.6-flash), surfaced by :8600/api/agent-hr and rendered on :8600/agents.
- qi_trinity_check.py PASS 16/16; its selftest proves it goes RED when Codex is broken.
- Codex CLI is PINNED at 0.153.4 in WSL. NEVER `npm i -g @openai/codex@latest`. 0.154.0 removed
  `codex mcp-server`; `app-server` is not MCP. Forward path = Codex plugin for Claude Code.
- Evidence: C:\QIH\trinity\TRINITY_CONTINUE.md and
  C:\QIH\shared\documentation\session_summaries\Trinity_Summary_2026-09-09_2340.docx

## Tasks — in order. Tasks 1–3 spend NO assistant quota. Task 4 spends at most 2 calls.

1. REGISTRY CLEANUP (Tier 3, contained)
   a. In agent_hr.db, the `agents` row name='codex' has model='gpt-6-astra' — the most expensive slug,
      contradicting the luna-first policy. Change it to 'gpt-5.6-luna'. Query before and after; show both.
      Confirm :8600/api/agent-hr reflects it (static data — no service restart needed; if the API
      caches, say so rather than restarting anything).
   b. Move C:\QIH\trinity\NEXT_SESSION_PROMPT.md (this file) to briefs/ with a date suffix once you've
      read it, so no future session re-runs a completed brief.

2. MCP CONNECTION TRIAGE (read-only first)
   At S1 start, two MCP servers reported CONNECTION_CLOSED: `git` and `claude-peers`.
   Check whether they connect in THIS session (ToolSearch for mcp__git__* / mcp__claude-peers__*).
   If either still fails: find its entry in C:/Users/renne/.claude.json (or settings.json), run its
   command by hand, capture the real stderr, and state the root cause. Fix it only if the fix is
   Tier 3 (e.g. a wrong path). Anything touching secrets, whitelists or the QI_Elevate broker is
   Tier 1 — report, do not fix. `git` matters: "Update all" depends on it.

3. FRESHNESS FOR THE TRINITY CHECK (decision needed — do the analysis, then ASK)
   qi_trinity_check.py is manual-only. Every other QI unattended job ships with a freshness check
   (CLAUDE.md "Unattended jobs lie"). Propose a daily scheduled task that runs the check and writes
   C:\QIH\data\trinity\check_<date>.json, with a freshness probe modelled on
   check_digest_freshness() in C:\APPS\OC\tools\oc-keepalive-daemon.py.
   Constraints to state explicitly in the proposal:
     - The check spawns the Codex MCP process (handshake only) and calls Gemini ListModels with the
       real key. It does NOT generate with either model. Renne's rule is "nothing unattended ever
       calls an assistant" — argue whether a handshake/ListModels counts, and let Renne decide.
     - Never wrap it in `conhost --headless` without an outcome check — that masks exit codes.
   Do NOT create the task until Renne answers.

4. TRIAL READINESS (max 2 assistant calls, attended only)
   The 2026-10-16 trial review needs real rows, not smoke tests. If there is a genuine small task in
   this session (a script, a diff review, a long read), route ONE to Codex (model gpt-5.6-luna,
   sandbox read-only, approval-policy never) and/or ONE to Gemini per CLAUDE.md §1a. Say the assignee
   in one line first. Verify the row landed with the right model. If no genuine task exists, skip —
   do not invent work to generate rows.

5. SCOUT (Haiku sub-agent, web only): what is the current state of the official Codex plugin for
   Claude Code — does it exist, does it replace `codex mcp-server`, does it need >0.153.4? Return
   sources. This is research only; change nothing.

## Standing rules
- VERIFY, DO NOT TRUST. Re-run every assertion yourself; a sub-agent's checklist is not evidence.
- MCP discipline: one MCP tool call per turn (parallel MCP calls crash the session on Windows).
- Blast radius: warn before Tier 2, STOP on Tier 1. Never widen a security boundary to get unblocked.
- Delegate per the model ladder; keep cross-system reasoning in the main thread.
- Do not send anything externally, publish, or delete data.

## Deliverable
Session summary .docx to C:\QIH\shared\documentation\session_summaries\Trinity_Summary_<YYYY-MM-DD_HHMM>.docx
(python-docx, real headings, a PASS/FAIL table per task with actual output). State plainly anything
not fixed and why. Log to Brain with qi_log_session(project_id='trinity', ...) — skip silently if
:9011 is offline. Print the .docx path. End with the answer to task 3's question and whether Renne
needs to decide anything else.
```

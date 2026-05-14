# QI Hive - Two Design Decisions (2026-05-13)

Author: hive-architect (Opus 4.7)
Status: DRAFT for hive-inspector review before hive-builder pickup

---

## TASK 1 - War Room Agent Cards

### Decision: Option (b) - dedicated agent_heartbeats table in qi_brain.db

### Rationale (5 sentences)
The War Room is the operational console; showing four identical timestamps is worse than showing unknown because it lies. Option (a) is passive and indefinite - the SubagentStop hook has been supposedly wired for weeks and session_log.agent_id is still mostly NULL, so waiting is not a plan. Option (c) collapses real architectural distinctions (Claude Code vs Claude Work vs CoWork vs Claude Chat are genuinely different surfaces with different cost and trust profiles) and would have to be un-done as soon as per-agent routing matters for billing or dispatch fan-out. Option (b) gives us an explicit, cheap write target that any client (hook, dashboard ping, CoWork webhook, manual heartbeat) can hit without depending on the fragile SubagentStop path. It also normalises the heartbeat concept so future agents (hive-builder, hive-inspector, hive-architect runs) drop into the same table.

### Schema - agent_heartbeats

    CREATE TABLE IF NOT EXISTS agent_heartbeats (
      id              INTEGER PRIMARY KEY AUTOINCREMENT,
      agent_id        TEXT    NOT NULL,
      agent_kind      TEXT    NOT NULL,
      project_id      TEXT,
      event           TEXT    NOT NULL,
      session_ref     TEXT,
      model           TEXT,
      ts              TEXT    NOT NULL DEFAULT (datetime(NOW)),
      meta_json       TEXT
    );
    CREATE INDEX IF NOT EXISTS ix_heartbeat_agent_ts   ON agent_heartbeats(agent_id, ts DESC);
    CREATE INDEX IF NOT EXISTS ix_heartbeat_project_ts ON agent_heartbeats(project_id, ts DESC);

Note: ts DEFAULT clause uses sqlite datetime() with NOW shown here as placeholder; builder should restore the standard sqlite literal.

- agent_id values: claude_code | claude_work | cowork | claude_chat | hive-*
- agent_kind values: interactive | subagent | service
- event values: start | tool_call | stop | heartbeat

### Write path

| Writer | When | Endpoint |
|---|---|---|
| SessionStart / SubagentStop hooks | every Claude Code subagent start/stop | POST /api/agent/heartbeat (new) |
| Hive Dashboard CoWork approve route | on dispatch approve | same endpoint, agent_id=cowork |
| Claude Work integration (future) | session boundary | same endpoint |
| Claude Chat | manual /qi.ping from the chat surface | same endpoint |

Endpoint contract: {agent_id, agent_kind, project_id?, event, model?, session_ref?, meta?} -> 201.

### Read query for render_warroom()

    SELECT agent_id, MAX(ts) AS last_ts,
      (SELECT project_id FROM agent_heartbeats h2 WHERE h2.agent_id=h1.agent_id ORDER BY ts DESC LIMIT 1) AS last_project,
      (SELECT model FROM agent_heartbeats h2 WHERE h2.agent_id=h1.agent_id ORDER BY ts DESC LIMIT 1) AS last_model
    FROM agent_heartbeats h1
    WHERE agent_id IN (claude_code, claude_work, cowork, claude_chat)
    GROUP BY agent_id;

Exposed as GET /api/agents/last_seen. render_warroom() replaces the current most-recent-project-for-everyone loop with a per-agent lookup; cards missing from the response display never.

### Migration note
Pure additive - CREATE TABLE IF NOT EXISTS + two indexes. No rewrites of session_log. Optional one-time backfill from session_log rows where agent_id IS NOT NULL. Roll back by dropping the table.

---

## TASK 2 - CoWork Dispatch Auto-Apply Pipeline

### 1. Trigger
Event-driven from the existing Approve route, NOT a polling worker for the user-facing trigger.
- POST /cowork/dispatch/{id}/approve writes approved_at, then inserts a row into dispatch_runs with state=queued.
- Route returns 202 immediately.
- NSSM service QI_HiveApply tails dispatch_runs WHERE state=queued every 10s. Cheap, restartable, observable.

### 2. Dispatcher
New module: C:\QIH\engine\hive\apply\dispatcher.py + C:\QIH\engine\hive\apply\runner.py.
- Sibling of hive\ingest, not a sub-module - different lifecycle, must be independently stoppable.
- NSSM service QI_HiveApply, AppDirectory C:\QIH\engine\hive\apply, log C:\QIH\logs\hive_apply.log. Registered in QI_Service_Registry.md.

### 3. Builder spawn - headless Claude Code subprocess
- claude code --headless --agent hive-builder --prompt-file <dispatch.json> --cwd <project_root> --json-output <out.json> (exact CLI flags TBC - see Decisions A).
- Prompt envelope: {dispatch_id, project_id, suggested_fix, rationale, allowed_paths, max_diff_lines}.
- Logs -> C:\QIH\logs\dispatch_runs\<dispatch_id>\builder.log.
- Wall-clock timeout 10 min -> kill -> state failed.
- Phase 0 fallback: runner writes prompt to C:\QIH\inbox\hive_builder\<id>.json; a human-triggered Claude Code session picks it up. Same state machine.

### 4. Review gate - hive-inspector
- Runner applies the diff to a throwaway worktree at C:\QIH\worktrees\apply-<dispatch_id> (not the live project).
- Spawns hive-inspector headlessly with {dispatch, diff_path} -> expects {verdict: pass|fail, reasons:[], severity}.
- Pass -> commit in worktree, then either open PR or fast-forward master per project policy (see Decisions C) -> state applied.
- Fail -> state review (NOT failed). Worktree retained, Brain inbox notification.

| Outcome | State | Side effects |
|---|---|---|
| builder error / timeout | failed | worktree discarded, log retained, notification |
| inspector fail | review | worktree retained, notification, no commit |
| commit/push error | failed | worktree retained, log retained, notification |
| guardrail breach | rejected_auto | worktree never created, dispatch flagged |

### 5. State machine + schema delta

    ALTER TABLE dispatches ADD COLUMN apply_state    TEXT;
    ALTER TABLE dispatches ADD COLUMN apply_run_id   INTEGER;
    ALTER TABLE dispatches ADD COLUMN applied_at     TEXT;
    ALTER TABLE dispatches ADD COLUMN applied_commit TEXT;

    CREATE TABLE dispatch_runs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      dispatch_id TEXT NOT NULL,
      state TEXT NOT NULL,
      builder_log TEXT, inspector_verdict TEXT, inspector_reasons TEXT,
      diff_path TEXT, worktree_path TEXT, commit_sha TEXT,
      started_at TEXT DEFAULT (datetime(NOW)),
      finished_at TEXT, error TEXT
    );
    CREATE INDEX ix_runs_state    ON dispatch_runs(state);
    CREATE INDEX ix_runs_dispatch ON dispatch_runs(dispatch_id);

Transitions: approved -> queued -> in_progress -> (review | applied | failed | rejected_auto). review and failed are terminal for the automatic loop; humans can re-queue.

### 6. Guardrails (enforced in runner.py, before AND after builder runs)
- max_files_changed = 1 (Phase 1)
- max_lines_added + max_lines_removed = 40
- forbidden_paths: .env*, *.db, qi_registry.json, QI_Standards.md, QI_Architecture_Principles.md, QI_Service_Registry.md, C:\Windows, C:\Program Files*
- forbidden_ops: deletes, renames, mode changes, binary writes, NSSM/service config edits
- allowlist_categories (must match dispatch.fix_category): typo_fix | doc_link_correction | missing_init_py | gitignore_addition | dead_import_removal
- max_concurrent_runs = 1 global mutex via dispatch_runs.state=in_progress
- Kill switch: C:\QIH\engine\hive\apply\HALT file -> runner short-circuits all queued items to rejected_auto. Renne can also nssm stop QI_HiveApply via gsudo.

### 7. Audit trail
- Every state transition writes to existing compliance_log with actor=QI_HiveApply, event=dispatch.<state>, ref=dispatch_id.
- dispatch_runs is the operational ledger (one row per attempt).
- Raw builder + inspector logs at C:\QIH\logs\dispatch_runs\<dispatch_id>\, referenced by path.
- Hive Dashboard /cowork adds an Apply status column wired to dispatches.apply_state.

### Riskiest part
Headless Claude Code invocation (Section 3). Everything else is plumbing we control; headless mode depends on Anthropic CLI capabilities we have not verified. The whole design is structured so the only difference between headless and fallback is which subprocess runner.py calls - state machine, guardrails, and audit trail are identical.

### Decisions needed from Renne before Phase 1 starts
- A. Headless Claude Code CLI - confirm exact invocation, or ship Phase 0 (inbox-fallback) first and add headless in Phase 2.
- B. Worktree root - C:\QIH\worktrees proposed; confirm no collision with existing worktree workflow.
- C. Commit/push policy per project - PR-only by default; opt-in fast-forward via qi_registry.json flag auto_merge_approved_fixes: true?
- D. Allowlist of fix categories - ratify or trim the five listed in Section 6.
- E. NSSM service name + account - confirm QI_HiveApply and the run-as account.
- F. Notification channel - Hive Dashboard inbox default; escalate to Maia/LINE for production-impacting fixes?

---

## Cross-cutting compliance check (The Five Laws)
- Registry-first: no new HTTP port; service name registered in QI_Service_Registry.md before code lands.
- Single source of truth: state lives in qi_brain.db; no parallel JSON state files.
- Naming: QI_HiveApply, lowercase project_ids in all rows.
- Reversibility: schema changes are additive, worktrees throwaway, HALT flag stops the loop without code changes.
- Audit completeness: every transition double-written (compliance_log + dispatch_runs).

---

## Decisions Resolved (2026-05-13)

- A. Headless Claude Code: DEFERRED to Phase 2. Phase 1 ships inbox-fallback only.
- B. Worktree root: C:\QIH\worktrees\apply\<dispatch_id> (namespaced subfolder, avoids collision with C:\CLAUDE\.claude\worktrees\).
- C. Commit policy: PR-only default. Per-project opt-in via qi_registry.json flag `auto_merge_approved_fixes: true`.
- D. Allowlist trimmed to THREE for Phase 1: typo_fix, doc_link_correction, gitignore_addition. (Dropped dead_import_removal and missing_init_py - re-add after clean Phase 1 baseline.)
- E. NSSM service: QI_HiveApply, runs as user account (parity with QI_HiveIngest, not SYSTEM).
- F. Notifications: Hive Dashboard inbox only for Phase 1. LINE/Maia escalation deferred until 20+ clean runs observed.

---

## Handoff
- To hive-inspector: review for Five Laws compliance, schema collisions, naming.
- To hive-builder (Renne resolved A-F on 2026-05-13 - hive-builder cleared to start Phase 1): Phase 1 = schema migrations + QI_HiveApply skeleton in inbox-fallback mode + dashboard wiring. Headless invocation is Phase 2.

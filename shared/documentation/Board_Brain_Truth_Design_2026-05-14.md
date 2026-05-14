# Board -> Brain-as-Source-of-Truth Design (Option C)

**Date:** 2026-05-14  **Author:** QI Hive Architect  **Status:** Proposed (Phase 2)
**Supersedes:** tasks.json static-file model (commit 2012ba4, Phase 1)
**Linked docs:**
- [C:\QIH\engine\brain\core\schema.sql](C:\QIH\engine\brain\core\schema.sql)
- [C:\QIH\engine\hive\dashboard\server.py](C:\QIH\engine\hive\dashboard\server.py)
- [C:\QIH\ecosystem\QI_Architecture_Principles.md](C:\QIH\ecosystem\QI_Architecture_Principles.md)

---

## 1. Goal
Move the Hive Task Board from a file-backed cache (tasks.json) to Brain SQLite as the canonical store, so every task is queryable, auditable, and join-able with decisions, sessions, dispatches, and compliance issues. Match industry practice (Jira/Linear/GitHub Projects) where the issue store is a relational DB and the UI is a thin projection.

## 2. Constraints
- Five Laws: Law 1 (single source of truth), Law 3 (no hardcoded state outside Brain/registry), Law 6 (match best practice).
- Brain API on :9010 already exists - extend it, do not bypass it.
- WAL-mode SQLite, busy_timeout 5000 ms - multi-writer safe today (dashboard, health_check.py, dispatcher).
- Cannot lose the 48 existing tasks.json entries, including manual ones Renne typed.
- Phase 1 scheduler must keep working through the cutover (no downtime).

## 3. Brain schema - kanban_tasks
New table (single, not extension; decisions/sessions are events, tasks are mutable state - different lifecycles):

| Column | Type | Notes |
|---|---|---|
| task_id | INTEGER PK AUTOINCREMENT | internal id |
| task_code | TEXT UNIQUE | human key TASK-0001 (auto-gen) |
| project_id | TEXT FK projects | nullable |
| agent_id | TEXT FK agents DEFAULT claude | who/what created it |
| title | TEXT NOT NULL | one-liner |
| body | TEXT | markdown |
| status | TEXT CHECK IN (backlog,todo,in_progress,blocked,review,done,cancelled) | |
| priority | TEXT CHECK IN (p0,p1,p2,p3) DEFAULT p2 | |
| origin | TEXT CHECK IN (manual,dispatch,session,decision,feature,compliance,health,dependency) | |
| origin_ref | TEXT | dispatch:42, compliance:CHECK-12, decision:AD-017 |
| assignee_agent | TEXT FK agents | nullable |
| labels | TEXT | JSON array |
| due_at | TEXT | ISO8601 nullable |
| created_at | TEXT DEFAULT now | |
| updated_at | TEXT | trigger-maintained |
| closed_at | TEXT | set when status -> done/cancelled |

Indexes: (status, priority); (project_id, status); UNIQUE PARTIAL on (origin, origin_ref) WHERE origin != 'manual' - prevents duplicate auto-tasks.

Companion table kanban_task_events (audit trail): (event_id, task_id, agent_id, from_status, to_status, note, at). Inserted on every status change. This is the Jira-style activity log.

*State machine:** backlog->todo->in_progress->review->done; in_progress<->blocked; any->cancelled; done->todo (reopen, logged). Enforced in API layer, not DB triggers (clearer errors).

## 4. Sources of truth -> auto-task mapping

| Brain table | Trigger | origin | Maps to |
|---|---|---|---|
| dispatch_log | new row status=pending | dispatch | title=summary, body=instructions |
| session_log | next_steps non-empty | session | one task per parsed bullet |
| decisions | impact_scope in (ecosystem,global) | decision | title=Implement: {title}, p1 |
| feature_evaluations | recommendation=adopt AND decided=1 | feature | one task per target_project |
| compliance issues | severity >= medium | compliance | priority by severity |
| health_check | service healthy->unhealthy | health | p0, auto-close on recovery |
| dependency scanner | CVE or outdated package | dependency | p1/p2 by CVSS |

Mapping happens in **Brain-side writers** (poller.py extensions), not dashboard. Dashboard is read-only on Brain.

## 5. Migration plan
1. Add kanban_tasks + kanban_task_events via migrations/002_kanban.sql.
2. One-shot tools/migrate_tasks_json.py: read C:\QIH\data\tasks.json; detect origin (dispatch_id field=>dispatch; health_check title pattern=>health; else=>manual); insert preserving created_at.
3. Verify counts (48 in->48 out, grouped by origin printed). Renne confirms before activation.
4. Rename tasks.json->tasks.json.archive_2026-05-14.
5. Flip dashboard render_board() to Brain read path via feature flag BOARD_SOURCE=brain in brain_config.
6. After 7 days stable, repoint health_check.py scheduler to Brain.

Rollback: flip flag back to file, restore archive. Mirror writes during cutover (section 9) mean no data loss.

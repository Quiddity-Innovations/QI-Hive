# Inspector Inbox Auto-Drain - Design

**Author:** QI Hive Architect (Opus 4.7)  
**Date:** 2026-05-14  
**Status:** Proposed - pending Renne approval, then hive-inspector review, then hive-builder  
**Related:** Auto-Apply Phase 2 (deterministic builder, live); Hive Inspector standards enforcer (live)  
**Inbox path:** `C:\QIH\inbox\hive_inspector\<dispatch_id>.json`  
**Verdict endpoint:** `POST http://127.0.0.1:9011/api/dispatch/<dispatch_id>/inspector_verdict`

---

## 1. Goal

Make inspector verdicts autonomous for the three Phase-2 allowlisted categories (`typo_fix`, `doc_link_correction`, `gitignore_addition`) so the deterministic builder pending_review queue drains without a human in the loop, while keeping cost near zero and preserving auditability.

## 2. Constraints

- The Five Laws. Especially Law 6 (best-practice check) and the registry-first rule.
- Port block. Brain API owns 9010-9019. Verdict endpoint already on 9011.
- No new ports. Drain is a worker, not a server.
- Cost discipline. Renne is POC-budget; LLM calls are taxed.
- Pattern parity. `QI_HiveApply` deterministic worker already exists - the drain mirrors that shape.
- NSSM naming. New service must be `QI_HiveInspectorDrain`, AppDirectory `C:\QIH\engine\hive\inspector_drain`, log `C:\QIH\logs\hive_inspector_drain.log`, NSSM binary `C:\QIH\engine\bin\nssm.exe`, registered in `QI_Service_Registry.md`.
- Inspector remains the auditor of record. Automated artifact must be schema-identical to a real inspector verdict so downstream consumers (dashboard, brain, audit log) do not branch.

---

## 3. Options considered

### 3.1 Scheduling vehicle

| Option | Pro | Con | Verdict |
|---|---|---|---|
| (a) Asyncio loop inside `QI_Dashboard` startup | Zero new service; reuses 5-min board-sync pattern | Conflates UI with autonomous compute; a crash kills the dashboard; harder to pause independently | Reject |
| (b) New NSSM service `QI_HiveInspectorDrain` | Pattern parity with `QI_HiveApply`; independent lifecycle; clean logs | One more service in the tray | Accept |
| (c) Claude Code `ScheduleWakeup` MCP | Free if it works | Requires Claude Code session running; unsuitable for 24/7 autonomy | Reject |

**Pick: (b).** Same shape as `QI_HiveApply`, same operator mental model.

### 3.2 How does the drain invoke the inspector? (the real question)

| Option | Description | Cost | Risk |
|---|---|---|---|
| (a) Headless Claude Code subprocess | `claude code --headless --agent hive-inspector ...` | LLM tokens per dispatch | UNVERIFIED CLI surface - same trap that pushed builder to deterministic |
| (b) Direct Anthropic API call from Python with inspector system prompt + tool harness | Tokens + re-implement the agent loop | Reproduce Read/Glob/Grep/Bash inside Python; ongoing drift between SDK subagent and Python re-host | Significant build cost |
| (c) Hybrid: mechanical pass first; LLM only when mechanical is ambiguous | Mostly free; LLM as exception | Need to define ambiguous precisely; still depends on (a) or (b) for fallback | Best of both if ambiguity rate is low |
| (d) Deterministic auto-verdict for mechanical-green allowlisted categories; no LLM inspector at all for Phase 2; LLM reserved for Phase 3 | $0 marginal | Requires we trust mechanical inspector + the allowlist | Lowest risk - symmetrical to the deterministic-builder argument |

**Pick: (d), with (c) as the Phase 3 escalation path.**

### 3.3 Rationale for (d) - the honest parallel argument

Phase 2 builder is deterministic-not-LLM because the three allowlisted categories have unambiguous mechanical specs: typo edit-distance <= 2, doc-link path resolution, gitignore line append. If those edits are deterministic to produce, they are also deterministic to verify. `mechanical_inspector.py` already checks: diff bounds, file allowlist, line count, no out-of-scope changes, category invariants. An LLM inspector reading the same diff would, in the overwhelming majority of cases, be paraphrasing the mechanical inspector at three cents a pop.

This is the Law-6 lesson: do not pay an LLM to re-derive what a deterministic check already proved.

---

## 4. Recommendation

Build `QI_HiveInspectorDrain` as a deterministic auto-verdict worker.

### 4.1 Per-tick algorithm

For each `*.json` in `C:/QIH/inbox/hive_inspector/`:

1. Read `dispatch_id` from filename.
2. `GET /api/dispatch/<id>` from Brain. If `inspector_verdict` already set, move envelope to `done/` and continue (idempotency).
3. If `category` not in ALLOWLIST, log `skip_phase3` and continue (leave envelope for human / Phase 3).
4. Call `mechanical_inspector.verify(dispatch_id)` -> `{status, confidence, summary, findings}`.
5. If `status==green` and `confidence>=0.95`: build approved verdict with `inspector=deterministic_auto_v1`.
6. Else if `status==red`: build rejected verdict with same shape.
7. Else (yellow / 0.40 < conf < 0.95): `flag_for_human(dispatch_id, reason=...)`, leave envelope, continue.
8. POST verdict to `/api/dispatch/<id>/inspector_verdict`. On 2xx: move envelope to `done/`. On 4xx: quarantine. On 5xx: leave for retry.

### 4.2 Confidence model

`mechanical_inspector.verify()` returns `confidence in [0,1]` derived from:

- diff size within bound x 0.25
- all touched files in allowlist x 0.25
- category invariants pass (e.g. for `gitignore_addition`: only appended lines, no deletions) x 0.30
- no secondary-effect signatures (no imports changed, no schema changes, no service config changes) x 0.20

`>= 0.95` auto-approve. `<= 0.40` and any red flag auto-reject. Anything in between escalates to human (Phase 2.5) or LLM inspector (Phase 3, when wired). Thresholds in `C:\QIH\engine\hive\inspector_drain\config.json`, configurable without redeploy.

### 4.3 Pacing

- Tick interval: 60 seconds. Filesystem-cheap scan; not an LLM cost.
- Per-tick cap: 20 envelopes, then yield.
- Daily LLM call ceiling (Phase 3 only): 50/day, hard stop with `BUDGET_EXHAUSTED` log line until 00:00 local.
- For Phase 2 deterministic-only mode, LLM ceiling is 0. Renne pays nothing.

### 4.4 Failure modes and state transitions

| Failure | Behaviour |
|---|---|
| Envelope JSON malformed | Move to `quarantine/`, log, continue |
| `brain.get_dispatch_run` 404 | Quarantine; orphan envelope |
| `mechanical_inspector.verify` raises | Log, leave in place, retry next tick; after 3 failures quarantine |
| Verdict POST 4xx | Quarantine (schema mismatch needs investigation) |
| Verdict POST 5xx / network error | Leave envelope; retry next tick. Brain API restart is recovery |
| POST 200 but dispatch already resolved | Move to `done/` silently |
| Drain process crashes | NSSM restarts it; idempotency guard prevents double-verdict |
| Inbox grows unbounded | Dashboard `/compliance` surfaces depth; alarm at >100 |

All transitions logged to `C:\QIH\logs\hive_inspector_drain.log` (daily rotation) and mirrored to Brain as `hive_inspector_drain` events so the dashboard timeline shows them.

### 4.5 Audit and schema parity

Auto-verdict body MUST be schema-identical to a human inspector verdict, with `inspector` field set to `deterministic_auto_v1` (versioned). The dashboard verdict viewer should render the `mechanical_findings` block prominently so a reader can see exactly why it was auto-approved. No silent green checks.

---

## 5. Law 6 - best-practice flag

Pre-merge automation in the wider industry:

- GitHub Auto-Review apps / CodeRabbit / Sourcegraph Cody PR review - run on PRs, post review comments, do not auto-merge. Humans click merge.
- Renovate / Dependabot auto-merge - auto-merges only when CI is green AND the change is on an allowlisted update type (patch versions, lockfile-only).
- Atlantis / Terraform auto-apply - auto-applies only on allowlisted directories with mandatory plan output review.

Pattern: deterministic + allowlist + CI-green => auto-merge. Anything ambiguous => human review on a PR surface.

This validates option (d). It also surfaces a real alternative worth naming honestly:

Alternative: route every auto-applied change through a real GitHub PR and let GitHub branch protection + a deterministic CI check be the inspector. Pros: industry-standard, transparent, reviewable from phone. Cons: significantly more plumbing (PR creation, branch management, CI runner); Hive lives in a single working tree per project; PR-per-fix would slow the loop from seconds to minutes and require GitHub Actions credits.

Recommendation: stay with the inbox/verdict pattern (option d) for Phase 2. Revisit the PR-based pattern when Phase 3 categories arrive (refactors, multi-file edits, dep updates) where the cost of PR plumbing is justified.

---

## 6. Implementation plan (for hive-builder)

1. Scaffold service folder `C:\QIH\engine\hive\inspector_drain\` with the QI 7-folder shape. Mirror `C:\QIH\engine\hive\apply\` exactly.
2. Create `drain.py` implementing the per-tick algorithm in section 4.1. Import `mechanical_inspector.py` as a library - do not copy.
3. Create `config.json`: `tick_seconds=60`, `per_tick_cap=20`, `confidence_approve_threshold=0.95`, `confidence_reject_threshold=0.40`, `daily_llm_ceiling=0`, `allowlist_categories=[typo_fix, doc_link_correction, gitignore_addition]`.
4. Idempotency: `GET /api/dispatch/<id>` from Brain before acting.
5. Ensure `C:\QIH\inbox\hive_inspector\quarantine\` and `done\` exist on first tick (mkdir -p).
6. Logging to `C:\QIH\logs\hive_inspector_drain.log` (daily rotation); emit `hive_inspector_drain.tick` and `.verdict` events to Brain.
7. NSSM service `QI_HiveInspectorDrain`, AppDirectory `C:\QIH\engine\hive\inspector_drain`, Description set, registered in `C:\QIH\ecosystem\QI_Service_Registry.md`. Use `gsudo` for install.
8. Tests in `engine/hive/inspector_drain/tests/`: approve-happy-path, reject-out-of-allowlist, escalate-on-yellow-confidence, idempotency, malformed-JSON quarantine, 5xx retry.
9. Dashboard: extend `/compliance` panel with drain status, inbox depth, last 10 verdicts (category + confidence + inspector field).
10. Add `qi_hive_inspector_drain` entry to `qi_registry.json` (no port - worker only).
11. Confirm Brain accepts `inspector=deterministic_auto_v1`; add to enum if needed.
12. Run `python C:\QIH\ecosystem\qi_validator.py --project qi_hive` after install.
13. Smoke test: synthetic approved-shape envelope to inbox; confirm drain + POST + move to `done/` + dashboard surfaces within 90 s.

---

## 7. Risks and rollback

| Risk | Mitigation |
|---|---|
| Auto-approval of a bad edit that mechanical inspector mis-scored | 0.95 threshold; quarantine on any red flag; every auto-verdict carries `mechanical_findings`; nightly hive-inspector LLM deep-run samples `deterministic_auto_v1` verdicts |
| Drift between builder mechanical inspector and drain verify | Both import the same `mechanical_inspector.py` - single source of truth |
| Renne wants to pause autonomy | `nssm stop QI_HiveInspectorDrain`; envelopes accumulate harmlessly; humans can drain manually as before |
| Schema drift on POST | Versioned via `deterministic_auto_v1`; Brain side validates |
| Runaway builder floods inbox | `per_tick_cap=20` bounds churn; dashboard alarm at >100 |

Rollback: stop `QI_HiveInspectorDrain`. Reverts to manual-inspector status quo with zero data loss. Idempotency means any replay is a no-op on the Brain side.

---

## 8. Escalation to Renne

- Approve skipping LLM inspector for Phase 2 entirely (option d). Cost-and-honesty call only Renne can sign off on.
- Confirm confidence thresholds (0.95 / 0.40) before code is written.
- Decide whether Phase 3 LLM fallback should be designed now (separate ADR) or deferred until Phase 3 categories are actually proposed.

## 9. Handoff

- Next: hive-inspector reviews this design for Law-6 compliance and verdict-schema parity.
- Then: hive-builder executes section 6.

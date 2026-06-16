# Auto-Apply Phase 2 -- Deterministic Worker (Re-Evaluation)

Author: hive-architect (Opus 4.7)
Date: 2026-05-14
Supersedes: Section 3 of C:\QIH\shared\documentation\Auto_Apply_Pipeline_Design_2026-05-13.md
Status: DRAFT for hive-inspector review; one fork (item 5) needs Renne

---

## 1. Verdict -- Deterministic worker IS superior for the current allowlist

Yes, unambiguously. The Phase 1 allowlist (typo_fix, doc_link_correction, gitignore_addition) is three pure string-transform categories. None require natural-language reasoning; each is fully specified by {file, old, new} or {file, line} tuples already present in dispatch.suggested_fix. Sending these to an LLM is paying Opus/Sonnet tokens to perform str.replace().

Concrete wins over headless Claude Code:

| Axis | Deterministic worker | Headless Claude Code |
|---|---|---|
| Cost per run | $0 | ~$0.05-0.30 (Sonnet) |
| Latency | <1s | 30-120s |
| Determinism | bit-exact | non-deterministic |
| Testability | pytest with fixtures | requires live API or mock |
| Failure mode | exception -> state=failed | hallucinated edits -> review |
| Dependency | stdlib + git | unverified Anthropic CLI |
| Audit | regex applied at line N | model said so |

The headless path was already flagged in the original design as the riskiest part. For an allowlist this narrow, the risk is unjustified.

## 2. Coverage of the three categories

Estimated from compliance_log + inspector dispatch patterns since 2026-05-09:

- typo_fix: ~25-35% of inspector-generated dispatches
- doc_link_correction: ~15-20% (broken relative links, common after lowercase-id finding)
- gitignore_addition: ~10-15% (chroma/, *.db, __pycache__/ drift)

Combined coverage: ~50-65% of current dispatches. The remainder (lowercase project_id rename, missing __init__.py, dead imports, schema additions) routes to manual inbox handling under Phase 1 -- the intended Phase 1 contract. Coverage is acceptable; we are not blocking real automation by deferring LLM-class categories.

## 3. When we WANT an LLM in the loop (Phase 3)

LLM judgment is warranted when the transform is NOT pre-specifiable at dispatch time:

- refactor_function -- must find call sites, preserve semantics
- add_test -- must understand the function under test
- semantic_rename -- symbol-aware; identical strings in unrelated contexts must NOT change
- multi_file_consistent_edit -- must verify each site is genuinely the same pattern
- lowercase_project_id_migration -- surface is regex, but DB rows, JSON keys, file paths, NSSM service names all need coordinated change

Phase 3 should gate these behind a separate registry flag llm_apply_enabled: true (per-project), a separate NSSM service QI_HiveApplyLLM, and a separate allowlist. Deterministic remains default; LLM is an escalation.

## 4. Inspector handoff for deterministic transforms

Three options:

- (a) Inbox-fallback -- write {dispatch_id, diff_path, worktree_path} to C:\QIH\inbox\hive_inspector\<id>.json; state becomes pending_review. A future interactive Claude Code session dispatches hive-inspector via Agent tool. Pros: zero new infra, mirrors Phase 1 builder fallback, free. Cons: applies can sit hours.
- (b) Headless Claude Code for inspector only -- same risk we just rejected for builder.
- (c) Skip inspector for deterministic transforms -- removes the second-pair-of-eyes Renne explicitly wanted.

Recommendation: (a) inbox-fallback PLUS in-process mechanical inspector as belt-and-braces. The deterministic worker runs ast.parse for .py touches, link-resolution recheck for .md, git diff --check for whitespace, and guardrail re-verification post-diff. If mechanical-pass succeeds, state goes to pending_review and the inbox file is created. Mechanical pass catches ~80% of what hive-inspector would catch for these three categories; the inbox keeps the human-in-the-loop guarantee. State advances to applied only when hive-inspector lands a verdict.

## 5. Decision needed from Renne -- the single fork

Question: Should applied state require hive-inspector verdict (inbox-fallback, possibly hours of latency), or should mechanical-pass + guardrails auto-commit, with hive-inspector running post-commit as audit-only?

- Strict (inspector-gated commit) -- safer, slower; matches original design intent. No commits without subagent verdict.
- Fast (mechanical-pass commit, inspector audits after) -- closes the loop in seconds. Inspector can still flag bad commits -> opens a revert dispatch.

Everything else (worktree path, service name, allowlist, notification, schema delta) is already resolved in the 2026-05-13 doc. This is the only real fork left for Phase 2.

## 6. Implementation plan for hive-builder

1. Create C:\QIH\engine\hive\apply\transforms\ with one module per category: typo_fix.py, doc_link_correction.py, gitignore_addition.py. Each exports apply(target_path, spec) -> Diff and validate(spec) -> list[str].
2. Extend runner.py (already scaffolded in Phase 1) with dispatch_to_transform(fix_category) registry. Unknown category -> state=rejected_auto, reason category_not_in_allowlist.
3. Add mechanical_inspector.py: post-diff checks (ast.parse for .py, link-resolves for .md, dedup for .gitignore, git diff --check, re-run guardrails on actual diff not just spec).
4. Worktree flow: git worktree add C:\QIH\worktrees\apply\<dispatch_id> <project_branch>, apply transform, commit with message qi-apply: <category> <dispatch_id> plus Co-Authored-By: hive-builder trailer.
5. Write C:\QIH\inbox\hive_inspector\<dispatch_id>.json with {dispatch_id, worktree_path, diff_text, category, mechanical_pass: true}. Dispatch_run state -> pending_review.
6. Inspector resolution: when verdict lands in dispatch_runs.inspector_verdict, state advances to applied (PR open or fast-forward per project policy) or review (worktree retained, notify).
7. Tests at C:\QIH\engine\hive\apply\tests\ -- one fixture per category with before/, after/, spec.json. Pytest gates service start via PYTEST_GATE=1 env.
8. NSSM: reuse QI_HiveApply from Phase 1; no new service.
9. Dashboard: extend /cowork Apply column to show sub-state (pending_review distinct from queued).
10. Update QI_Service_Registry.md and qi_registry.json (Phase 2 flip planned -> live).

## 7. Law 6 best-practice check -- industry precedent

Strong precedent for deterministic-over-LLM in auto-apply:

- Dependabot (GitHub) -- pure deterministic; parses lockfiles, bumps versions, opens PRs. No LLM.
- Renovate -- same, deterministic config-driven.
- pre-commit.ci / autofix.ci -- runs deterministic formatters (black, prettier, ruff --fix) and commits diff. No LLM.
- Sourcery, Codiga, Sider -- rule-based auto-apply; LLM tiers exist but separate.
- GitHub Copilot Autofix (2024+) -- IS LLM-based, but only for security-class fixes where the patch space is genuinely open-ended. Coexists with Dependabot; does not replace it.

Industry pattern is exactly what we are converging on: deterministic auto-apply for mechanical categories, LLM auto-apply as a separate higher-trust tier. Diverging from the original headless-Claude design is alignment with best practice, not a deviation.

---

## Risks & rollback

- Risk: Transform module bug corrupts a file. Mitigation: worktree isolation + mechanical inspector + git diff --check + pytest gate. Rollback: git worktree remove; live branch never touched.
- Risk: Coverage stalls at 50% and Phase 3 LLM drags. Mitigation: Phase 3 design starts only after 20 clean Phase 2 runs (parity with notification escalation gate).
- Risk: Inbox-fallback inspector latency frustrates Renne. Mitigation: section 5 fork -- if Renne picks Fast, inspector becomes audit-only.
- Full Phase 2 rollback: nssm stop QI_HiveApply (via gsudo), drop transform modules, revert to Phase 1 inbox-only builder fallback. No schema changes (already landed in Phase 1).

## Handoff
- To hive-inspector: review for Five Laws compliance, transform module boundary, mechanical-pass scope.
- To Renne: resolve section 5 fork (strict vs fast).
- To hive-builder: cleared to start sections 1-4 of Implementation Plan regardless of fork; sections 5-6 depend on Renne's answer.

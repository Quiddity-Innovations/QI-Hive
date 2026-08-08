# AR — Agent Resources for BU Hive · Buildout Prompt

> **To Renne:** copy this file to the BU laptop (e.g. `C:\AI\Documentation\AR_Buildout_Prompt.md`),
> open a Claude Code session there, and say: *"Read AR_Buildout_Prompt.md and bring AR to life."*
> Everything below this line is addressed to the BU Claude.

---

## What you are building, and why

Renne runs an **agent workforce model**: the main Claude session is the *manager* — it designs,
orchestrates, reviews — and delegates everything that doesn't need frontier reasoning to
sub-agents on cheaper models. Every sub-agent is treated like a named employee with a personnel
file: what they worked on, how long it took, what it cost in tokens.

On his personal machine this system is called **Agent HR** and lives on his QI Hive. On THIS
machine it is called **AR — "Agent Resources"** — deliberately different name, page, and labels
so the two setups are never confused. **Never call it "HR" or "Agent HR" here. It is AR.**

## Ground rules for this machine (do not skip)

1. **BU governance applies**: low-risk local-only work → proceed; anything risky or unclear →
   route to the /approvals board. This build is local-only, single-user (Renne is the only user
   and the admin), loopback-bound — it qualifies as proceed-directly.
2. **The git guardrails on this machine stay exactly as they are** (PreToolUse hook + commit/push
   approval policy). Work within them.
3. **No student/staff/PII data** flows through anything you build. Agent metrics are about
   Claude sub-agents, not people.
4. **Runtime is authoritative**: `C:\AI\BU Hive` is the live app (the build-kit copy under
   claude-env-setup has diverged — ignore it). Verify every path I name below against reality
   before using it; this spec was written from a snapshot dated 2026-08-08 and the machine may
   have moved on.

## What already exists here (build ON it, don't duplicate it)

- **BU Hive control plane**: FastAPI on `127.0.0.1:8730`, vendored Bootstrap + hive theme,
  auth, nav'd pages (Discussion/Members, CogniBase Workbench, Docs health). App modules under
  `C:\AI\BU Hive\app\`. SQLite at `C:\AI\BU Hive\data\bu_hive.db`.
- **`app\hooks\session_capture.py`**: already parses Claude Code transcripts into SQLite —
  tool-call histograms, files touched, git commands, and **subagent outcome tracking
  (ok/error/incomplete + duration_ms)**. This is your ingest foundation — extend it, never
  re-implement it.
- **Named agents**: `C:\Users\rennesan\.claude\agents\bu-*.md` — bu-architect, bu-builder,
  bu-inspector, bu-ops, bu-scout, bu-scribe, bu-tester. These are the roster's founding staff.
- **Capture hooks** wired in `~/.claude/settings.json` (SessionStart/SessionEnd →
  `capture-hook.ps1`).

## The build

### 1. Roster + metrics store (extend `bu_hive.db`)
- Table `ar_agents(name PK, kind, model, description, source, first_seen, last_active, status)`.
  Seed from the `bu-*.md` frontmatter (kind='bu'), plus built-ins: general-purpose, Explore,
  Plan (kind='builtin'). Unknown agent names discovered in data auto-insert with
  kind='discovered' — that is AR's "onboarding".
- Table `ar_runs(id PK, agent, project, task_desc, started_at, duration_ms, tokens, tool_uses,
  outcome, session_id, UNIQUE(agent, session_id, started_at, task_desc))`.
- **Backfill**: (a) migrate whatever subagent runs `session_capture.py` has already recorded;
  (b) scan `C:\Users\rennesan\.claude\projects\*\*.jsonl` for sub-agent tool calls
  (tool name `Task` or `Agent`; fields subagent_type/description/model) and their results —
  usage appears as `<usage>subagent_tokens: N / tool_uses: N / duration_ms: N</usage>` or
  separate tags; parse tolerantly, record NULL when absent rather than dropping the run.

### 2. Live capture
- Add a **SubagentStop** hook (alongside the existing hooks, additive) that records each
  finished sub-agent run into `ar_runs`. The hook must be fail-safe: always exit 0, swallow
  every exception, never print to stdout, timeout its own work — a broken hook must never
  disrupt a session.

### 3. The AR page on BU Hive (`/ar`) — INTEGRATED, not bolted on
AR must be a first-class BU Hive citizen, indistinguishable in look, feel, and wiring from the
pages that were born there. Before writing any UI, read how the existing pages (Members,
CogniBase Workbench, Docs health) are registered, rendered, and gated — then do exactly what
they do:

- **Same skeleton**: new module following the existing `app\*.py` conventions; render through
  the same shared layout/base template the other pages use (header, nav, footer, flash
  messages) — never a standalone HTML file with its own boilerplate.
- **Same auth**: behind the same session/auth gate as every other BU Hive page. If an
  unauthenticated visitor hits `/ar`, they get the same login flow, not an open page.
- **Same theme**: the vendored Bootstrap + hive theme's own components (cards, tables, badges,
  status dots) — no new CSS frameworks, no CDNs, no divergent styling.
- **Nav placement with meaning**: add "Agent Resources (AR)" to the shared nav next to
  **Members** — Members is the human staff page, AR is its digital-staff counterpart. Add a
  small cross-link on the Members page ("Digital staff → AR") and on the AR page back to
  Members, so the pairing is visible.
- **Home/overview tile**: if BU Hive's landing page has summary tiles/cards, add an AR tile
  (active agents · runs this week · tokens this week) that links to `/ar` — same pattern as
  the existing tiles.
- **Registry-aware**: `ar_runs.project` values should map to the projects in `bu_registry.json`
  where possible; when a project exists in the registry, render it as a link to that project's
  existing BU Hive view rather than plain text.
- **Docs-health participation**: AR ships with its own doc (per the Documentation Standard —
  user guide + technical note) registered wherever the Docs-health page discovers docs, so AR
  itself shows up as a documented, freshness-tracked component and not an undocumented stowaway.
- **Roster view**: name, kind badge (bu/builtin/discovered), model badge, status dot (active =
  last 7 days), lifetime metrics (runs / tokens / hours), recent assignments per agent
  (task, project link, when, duration, tokens, outcome — session_capture's ok/error/incomplete
  makes a real outcome column possible here; show it).
- **APIs**: `/api/ar/agents` and `/api/ar/runs?agent=<name>`, read-only, same response
  conventions (envelope/error shape) as the existing `/api/*` endpoints.
- **Empty-state friendly**: missing DB/tables → the theme's "no data yet" card, never a 500.

### 4. Standing delegation policy (append to this machine's `~/.claude/CLAUDE.md`)
Add a section titled **"AR — Agent Resources & delegation ladder"**:
- Triage every task to the cheapest competent tier: **Haiku → Sonnet → Opus** (escalate one
  tier on failure; note the bump in one line). The main session reserves top-tier reasoning
  for design/orchestration/review and delegates implementation, research, and mechanical work.
- Prefer the NAMED bu-* agents when a role fits; anonymous general-purpose spawns only when
  none does.
- Every new agent type spun up gets added to the AR roster (auto-onboarding covers this; name
  and promote "discovered" agents when noticed).
- For deletions or anything irreversible: exact enumerated paths only, approval list first.

### 5. Verify, then report
- Seed + backfill, then print a roster report (agent / model / runs / tokens / minutes /
  last_active).
- Restart BU Hive the way it is normally run here (it is manual-start — check how, don't
  assume a service). `curl http://127.0.0.1:8730/ar` → 200; `/api/ar/agents` → JSON; existing
  pages still 200; app log clean.
- Test the SubagentStop hook with valid, empty, and malformed stdin — exit 0 every time.
- Finish with a summary: files created/modified, roster report, verification evidence, and
  anything you deviated on with reasons. Save it per this machine's documentation standard.

## Success criteria

Renne opens `http://127.0.0.1:8730/ar` and sees his BU agent workforce — the seven bu-* staff
plus anything discovered — each with model tier, history, outcomes, and costs; the page is
indistinguishable in look/auth/nav from BU Hive's native pages (nav beside Members, tile on the
home page, project links resolving through the registry, its own docs in Docs health); and from
that session forward every sub-agent run on this machine files itself into AR automatically.

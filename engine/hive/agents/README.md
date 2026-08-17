# Agent HR — roster and metrics for QI Hive / Claude Code sub-agents

**Location:** `C:\QIH\engine\hive\agents\`
**Dashboard pages:** [`/agents`](https://hive.quiddityinnovations.com/agents) (roster + recent assignments), Agent HR tile on `/` (landing page), cross-linked from `/mission-control`
**Built:** 2026-08-08
**Database:** `agent_hr.db` (stdlib `sqlite3`, two tables: `agents`, `runs`)

---

## What it is (user guide)

Every sub-agent QI Hive dispatches — the Hive roles (`hive-architect`,
`hive-builder`, `hive-inspector`, `hive-ops`, `hive-scout`, `hive-scribe`,
`hive-tester`), Claude Code's built-ins (`general-purpose`, `Explore`,
`Plan`), and anything auto-discovered — gets a personnel file: what it is,
what model it runs, when it last worked, and a full history of runs (task,
project, duration, tokens, outcome).

Think of it as the **personnel-records counterpart to Mission Control**:
Mission Control shows who's active *right now* (live heartbeats); Agent HR
shows the *history* — lifetime roster + every completed assignment. Both
pages cross-link to each other.

### Where to look

| Question | Where |
|---|---|
| "Who's on the roster, what model do they run, how active are they?" | `/agents` — card grid, sorted by most-recently-active |
| "What has agent X actually worked on?" | Click any agent card on `/agents` → recent assignments table below the grid |
| "How busy has the Hive been this week?" | Agent HR tile on the dashboard landing page (`/`) — active agents, runs this week, tokens this week |
| "Who's active right now, this second?" | `/mission-control` (live heartbeats, not history) |

New agents **onboard themselves automatically** the first time they run —
no manual registration step. An agent that finishes a run without an
existing roster row gets one created on the spot (`kind: discovered`).

---

## Where the data comes from (technical note)

### Schema (`agent_hr.db`)

```
agents(name PK, kind, model, description, source, first_seen, last_active, status)
runs(id PK, agent, project, task_desc, started_at, duration_ms, tokens,
     tool_uses, outcome, session_id, UNIQUE(agent, session_id, started_at, task_desc))
```

`kind` is one of `hive` (from `.claude/agents/*.md` frontmatter), `builtin`
(Claude Code's own agents), or `discovered` (auto-onboarded from a run the
roster didn't already know about).

### Three ways data gets in

1. **`--seed`** — reads `C:\APPS\CLAUDE\.claude\agents\*.md` frontmatter (`name`,
   `model`, `description`) plus a small `BUILTIN_AGENTS` list, and
   `INSERT OR IGNORE`s each into `agents`. Never overwrites a curated row
   with noisy discovery data (that's why runs use `INSERT OR IGNORE` too —
   `upsert_agent` is intentionally non-destructive).
2. **`--backfill`** — walks every Claude Code transcript
   (`C:\Users\renne\.claude\projects\*\*.jsonl`), pairs each `Task`/`Agent`
   tool_use block with its matching tool_result, and records one `runs` row
   per completed sub-agent dispatch. Skips any transcript over 50MB.
3. **`--ingest-hook`** (live path) — wired into the **SubagentStop hook**.
   `C:\Users\renne\.claude\subagent_stop.py` fires after every sub-agent
   finishes and, alongside its existing Hive-inbox stub, best-effort shells
   out to:

   ```
   python C:\QIH\engine\hive\agents\agent_hr.py --ingest-hook
   ```

   piping the hook's JSON payload on stdin. `cmd_ingest_hook` reads only the
   **tail** of the (possibly huge, still-growing) transcript
   (`TAIL_BYTES = 2MB`) to stay cheap, extracts the most recently resolved
   run, and records it. This call is wrapped in a bare `try/except: pass` in
   the hook — a failure here can never break the session that triggered it,
   and `agent_hr.py --ingest-hook` itself always `sys.exit(0)`s regardless of
   what happened internally.

### Dashboard integration (`server.py`, read-only)

The dashboard (`QI_Dashboard`, :8600) never writes to `agent_hr.db` — it's
owned entirely by `agent_hr.py` and the hook above. The dashboard opens it
read-only (`?mode=ro` sqlite URI) from three places:

- `GET /api/agent-hr` — full roster + lifetime aggregates + 3 most recent
  tasks per agent (used to populate `/agents`' card grid)
- `GET /api/agent-hr/runs?agent=<name>` — last 50 runs for one agent (the
  "recent assignments" table below the grid)
- Landing-page (`/`) tile — a small inline query (active-agent count + this
  week's run/token totals) in `render_dashboard()`

Named `/api/agent-hr*` deliberately, to avoid colliding with the
**pre-existing, unrelated** `/api/agents` endpoint (the Brain agent-team
roster consumed by Mission Control / the landing page's "Agent team" card).
Do not merge these two — they answer different questions (live heartbeats
vs. historical HR record) from different databases (`qi_brain.db` vs.
`agent_hr.db`).

### Registry-aware project links

`runs.project` is a raw filesystem path (e.g. `C:\APPS\CLAUDE`, `C:\QIH`) — the
`cwd` the sub-agent was dispatched from. Both API endpoints resolve that
path against `C:\QIH\ecosystem\qi_registry.json` (`_resolve_registry_project`
in `server.py`, longest-prefix match — same technique `doc_harvester.py` and
`subagent_stop.py` already use) and attach a `project_id`. The frontend
(`agent_hr.html`) renders the project as a link to `/project/<id>` when
resolved, plain text otherwise — so an unrecognized path never produces a
dead link.

### Auth / exposure

`/agents` and `/api/agent-hr*` are ordinary routes on the same FastAPI app
as every other dashboard page — they inherit whatever QI Gate does for
`hive.quiddityinnovations.com` (`mode: protected` in
`C:\QIH\engine\gate\config\gate.json`) automatically. No new tunnel, host,
or exemption was added for this feature.

### CLI reference

```
python C:\QIH\engine\hive\agents\agent_hr.py --seed          # load .claude/agents/*.md + built-ins
python C:\QIH\engine\hive\agents\agent_hr.py --backfill      # scan transcripts for past runs
python C:\QIH\engine\hive\agents\agent_hr.py --ingest-hook   # (used by the SubagentStop hook, not run by hand)
python C:\QIH\engine\hive\agents\agent_hr.py --report        # print a roster summary table to stdout
```

---

## Known gaps / next steps

- `--backfill` has not been scheduled to run periodically — today it's a
  manual catch-up tool. Consider a nightly task if the SubagentStop hook
  ever misses runs (e.g. hook file locked, process killed mid-run).
- No retention/pruning policy on `runs` yet — fine at current volume.
- Registry project resolution is exact path-prefix only; a sub-agent
  dispatched from an unregistered folder (e.g. a scratch/temp dir) will
  correctly render as plain text, not a broken link — this is by design,
  not a gap, but worth knowing if a project's runs don't link.

# QI Hive Dashboard — Full Panel Audit

**Date:** 2026-05-13
**Auditor:** Claude Code (this session, before sub-agents loaded)
**Method:** HTTP probe of every page-level route → heuristic empty-state scan → source code dive on flagged routes.
**Status:** Audit complete. Two critical bugs fixed inline. Remaining items listed below with severity + suggested owner.

---

## Heat-map (HTTP probe summary)

| Route | Bytes | Rows | Empty hits | Verdict |
|---|---:|---:|---:|---|
| `/` Dashboard | 49,019 | 48 | 9 | ✅ healthy |
| `/launcher` | 32,084 | 0 | 0 | ✅ (uses card layout, not rows) |
| `/hive` | 35,810 | 4 | 2 | ⚠️ partial (alerts present) |
| `/health` | 65 | 0 | 0 | ✅ JSON probe (correct) |
| `/board` | 75,597 | 0 | 3 | ⚠️ check Kanban cards |
| `/guide` | 24,782 | 0 | 2 | ✅ markdown viewer |
| `/tests` | 28,024 | 26 | 1 | ✅ healthy |
| `/config` | 37,282 | 5 | 7 | ⚠️ several mock toggles |
| `/logs` | 28,577 | 6 | 1 | ✅ healthy |
| `/projects/status` | 14,797 | 6 | 0 | ✅ healthy |
| `/services` | 20,219 | 22 | 1 | ✅ healthy |
| `/tasks` | 19,700 | 12 | 0 | ✅ healthy |
| `/usage` | 46,164 | 16 | 0 | ✅ healthy |
| `/activity` | 46,338 | 72 | 1 | ✅ healthy |
| `/news` | 262,265 | 0 | 7 | ⚠️ card layout, but "never" indicators |
| `/dispatch` | 166,569 | 0 | 9 | 🔧 **FIXED** (was null IDs) |
| `/brain` | 32,830 | 6 | 6 | 🔧 **FIXED** (was field mismatch) |
| `/warroom` | 27,089 | 29 | 4 | ⚠️ alerts present |
| `/compliance` | 6,948 | 0 | 0 | ⚠️ tiny, likely mostly mock |

---

## ✅ Fixed in this session

### 1. Brain page Decisions/Features tabs — field mismatch
- **Was**: rendered `p.get('recent_decisions',[])` per project — but `/api/ecosystem_snapshot` doesn't include nested arrays
- **Now**: reads `decisions` and `features` tables directly from `qi_brain.db` (466 + 298 rows respectively), ordered by recorded_at, LIMIT 30 each
- **Commit**: `19ab21f`

### 2. Brain page Overview project cards — field mismatch
- **Was**: rendered `phase` / `status` / `last_updated` — but API returns `last_phase` / `last_status` / `last_active`
- **Now**: reads correct fields + surfaces `decisions` count and `last_summary` excerpt
- **Commit**: `b7418fd`

### 3. CoWork Dispatch Approve/Decline — null IDs
- **Was**: hive_inspector inserted dispatches without `dispatch_id` column; 364 rows had NULL IDs; Approve PATCH to `/api/dispatch/None` always failed silently
- **Now**:
  - `inspector.py:file_dispatch()` generates UUID per insert
  - Backfilled UUIDs into existing 364 null rows
  - Approve/Decline now persists to Brain
- **Commit**: `19ab21f`

---

## ⚠️ Needs Investigation (audit findings, not yet fixed)

### 4. `/hive` page — 2 alert banners present
- 4 data rows + 2 alert-warning/danger banners
- **Suspect**: Brain status or agent loading warnings
- **Owner**: `hive-inspector` (next session)
- **Severity**: minor

### 5. `/compliance` page — ✅ FALSE NEGATIVE
- Audit probe initially flagged this as broken (7K bytes, 0 rows)
- **Actual state**: page is a JS-rendered SPA. `/api/compliance/recent` returns
  3,812 log entries fine. Static HTTP probe couldn't see JS-populated rows.
- **No fix needed** — verified working at API layer
- **Audit lesson**: the heat-map's `<tr>` row count is a false signal for SPA pages.
  Same likely applies to `/news` (262K bytes, JS-rendered) and parts of `/board`.

### 6. `/news` (Headlines) — 262K bytes, but 7 empty-state indicators
- Page renders but many cells say "never" / "no recent"
- Source: `/api/headlines` endpoint (just added by recent uncommitted Brain api.py change)
- **Suspect**: UNION query in `/api/headlines` may have correct shape but empty branches
- **Owner**: investigate which UNION branches return rows vs not
- **Severity**: low (cosmetic; data fills as projects log)

### 7. `/board` (Task Board) — Kanban cards
- 0 `<tr>` rows is expected (uses div cards, not tables)
- 3 empty-hits suggest some columns are empty
- **Tasks data source**: `data/tasks.json` (status.json sibling)
- **Quick check**: confirm `tasks.json` has rows and column field matches Kanban column IDs
- **Owner**: spot-check end-to-end
- **Severity**: low

### 8. `/config` page — 7 empty hits
- 5 data rows visible but multiple panels show "—"
- **Suspect**: `gsudo_profiles` empty / logging level not surfaced
- Some toggles (per earlier audit) are display-only without backend wiring
- **Owner**: walk every toggle, confirm endpoint, remove or wire each
- **Severity**: low (operational nuisance, not data corruption)

### 9. `/warroom` page — 29 rows + 4 alerts
- Renders agent cards but production agent activity (Maia, Naya, NEXUS, OC) may need same override pattern I added to the main Dashboard's Agent Team panel
- Sub-agent live status will populate once SubagentStop hooks fire from real sessions (settings.json fix already in place)
- **Owner**: verify after next session generates sub-agent activity
- **Severity**: low

---

## 🔍 How to resume this audit

Next session should dispatch a `hive-inspector` sub-agent with this exact brief:

```
You are hive-inspector. Continue the dashboard audit from
C:\QIH\shared\documentation\Dashboard_Audit_2026-05-13.md.

For each item under "⚠️ Needs Investigation" (numbered 4-9):
1. Read the relevant render function in server.py
2. Identify what data it expects vs. what it actually receives
3. Either fix it or write a one-paragraph finding explaining what to do

Output a follow-up audit doc named Dashboard_Audit_<today>.md with:
- Items closed (with commit refs)
- Items deferred (with reason + suggested owner)
- Any NEW bugs discovered

Do NOT mock fixes. If a panel needs a Brain-side change, hand off to
hive-builder. If it needs design decisions, hand off to hive-architect.
```

That sub-agent invocation will also test the agentic system end-to-end —
it should populate `hive_inspector` rows in the Agent Team panel.

---

## What is NOT a bug (cleared by this audit)

- `/health` returning 65 bytes — that's the JSON liveness probe (correct behavior for `Accept: */*`)
- Hive sub-agent rows showing "never" for Builder/Inspector/Ops/etc — accurate, they haven't been used yet
- "Local LLMs by Project" panel — was already verified live & correct in earlier work
- Agent Team panel showing real production numbers for Maia/Naya/NEXUS/OpenClaw — verified working with per-project overrides

---

## Open question for Renne

The CoWork Dispatch fix means Approve/Decline buttons will now persist
to Brain. **But:** what should "Approve" actually DO downstream?
Currently it just sets `status='approved'` in the dispatches row.
There's no plumbing that takes an approved compliance dispatch and
actually runs the suggested fix. So the buttons "work" in the sense
of persisting state, but no automation acts on the approval.

If you want approval to trigger the suggested_fix automatically, that's
a follow-up: `hive-architect` designs the auto-apply flow, `hive-builder`
implements, `hive-inspector` reviews.

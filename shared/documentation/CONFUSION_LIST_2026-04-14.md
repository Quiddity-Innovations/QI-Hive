# Confusion & Action List — compiled 2026-04-14 evening

**Goal for tomorrow:** consolidate everything behind the **QI Orchestration Dashboard at `http://localhost:9000`**, give each project its own tab with actions (start / stop / logs / open UI / open API / git status), retire the duplicates, keep Maia + NEXUS running for the demo.

**Guardrail:** Maia (8001/7860) and NEXUS (8010/7880) are healthy right now. Do NOT touch their code, NSSM services, or configs until after the demo.

---

## 🔴 Duplicate / overlapping dashboards — PICK ONE

| Port | Name | Folder | Keep? | Notes |
|---|---|---|---|---|
| **9000** | **QI Orchestration Dashboard** | `C:\UNIVERSAL\dashboard\qi_dashboard.py` | ✅ **KEEP — front end** | Already has tabs (Tasks, Delegations, Tests, Projects, Agents, Calendar, Chat, Audit). Missing: per-project tabs with actions. |
| 8651 | QI Web Panel | `C:\UNIVERSAL\ECOSYSTEM\qi_web_panel.py` | ❌ Retire | Duplicates the "Projects" tab of the 9000 dashboard. Move its port-link info into the 9000 dashboard and archive. |
| 8600 | Claude Manager Dashboard | `C:\APPS\CLAUDE\Dashboard\` | 🤔 Decide | Meant for Claude-agent orchestration. 9000 already has an "Agent Delegations" tab. Either: (a) merge into 9000, or (b) keep as the "internal" agent view and iframe it into 9000. |

**Tomorrow's first decision:** merge 8600 into 9000, or iframe it?

---

## 🟠 Per-project tabs — what each project needs

Current 9000 tabs are global (Tasks, Agents, Calendar…). What you asked for: **one tab per project** with actions. Proposed design:

For each of `Maia · Naya · NEXUS · OpenClaw · EasyFlow · FileHQ`:
- **Status header:** API health · UI health · git dirty/clean · NSSM service state
- **Actions:** Start / Stop / Restart · Open UI · Open API docs · Tail logs · `git status` · Open folder
- **Recent tasks:** last 5 tasks from `qi_orchestration.db` filtered by project_id
- **Recent delegations:** last 5 agent runs on that project
- **Session summaries:** list of `.docx` in `C:\UNIVERSAL\DOCUMENTATION\Session_Summaries\` prefixed with project name

Implementation note: the registry + DB already know all this — it's a frontend job, not a backend one. Expect `static/js/app.js` edits + new `/api/projects/<id>/actions` endpoints.

---

## 🟡 Uncommitted work scattered across repos (review tomorrow)

Found uncommitted modifications in three repos as of 2026-04-14 evening:

### `C:\APPS\QI` (Maia) — ⚠️ DO NOT COMMIT BEFORE DEMO
Modified files:
- `maia_auth.py`, `maia_content.py`, `maia_context.py`, `maia_server.py`
- `maia_soul.py`, `maia_status_page.py`, `maia_test.py`
- `tunnel_watchdog.py`, `webhook_updater.py`
- Many `.claude/worktrees/*` entries (nested git state)

**Action:** after demo, diff each file → decide keep/revert/commit. Don't touch before demo.

### `C:\APPS\NEXUS` — ⚠️ DO NOT COMMIT BEFORE DEMO
Modified: `install.py`, `main.py`, `regression_test.py`, `save_session_summary.py`, `save_session_summary_2.py`, `smoke_test.py`, `uninstall.py`

Note: `save_session_summary.py` AND `save_session_summary_2.py` — duplicate. Pick one.

### `C:\UNIVERSAL` — safer to commit
- Modified: `ECOSYSTEM/QI_Ecosystem_Map.md`, `ECOSYSTEM/QI_Universal_Control_Panel.bat`, `ECOSYSTEM/launcher/index.html`, `ECOSYSTEM/qi_new_project.py`, `ECOSYSTEM/qi_registry.json`, `ECOSYSTEM/qi_validator.py`
- Untracked: `dashboard/` (entire 9000 dashboard — NOT IN GIT), `DOCUMENTATION/`, `TRAINING/`, `session_context.py`

**⚠️ The 9000 dashboard is not version-controlled.** First action tomorrow: `git init` or add to existing repo and commit it.

---

## 🟢 Registry drift — `qi_registry.json` is out of date

Compared the registry to what's actually running:

| Thing | Registry says | Reality | Fix |
|---|---|---|---|
| QI Dashboard (9000) | **not listed** | Running, it IS the front end | Add entry: `qi-dashboard`, port 9000, path `C:\UNIVERSAL\dashboard` |
| qi_web_panel (8651) | Listed as universal panel | Running but should be retired | Change status to `deprecated` |
| Claude Manager (8600) | Not in `C:\UNIVERSAL` registry | Running, has own repo | Add as cross-project service |
| FileHQ | Registered as active | Dashboard DB says `deprecated, merged into Naya` | Sync status |

---

## 🔵 Session summaries scattered / duplicated

`C:\UNIVERSAL\DOCUMENTATION\Session_Summaries\` currently holds summaries from EasyFlow, QI-Dashboard, Maia, Naya, OpenClaw, GMAIL. Good — one shared folder. **But:**

- `~$syFlow_Summary_2026-04-13_1500.docx` is a stale Word lock file — delete.
- `_build_easyflow_strategy_docx.py` is a build script in the summaries folder — should live in `C:\APPS\EasyFlow\TOOLS\`.
- No summary yet for today's 9000-dashboard work on top of the 2028 summary from yesterday — tomorrow's session should generate one.

Also: Claude Manager has its own `C:\APPS\CLAUDE\Session Summaries\` folder. **Decision needed:** collapse into the universal folder, or keep Claude Manager separate?

---

## 🟣 MCP instability (from `status.json` pending actions)

Per `C:\APPS\CLAUDE\status.json`:
- OpenSpace / sqlite-maia / sqlite-naya / git MCPs are **unstable in worktree sessions**
- Fix documented: "run Claude from `C:\Claude` root, not a worktree"
- **Still open.** Flagged in Meeting 04, pushed to Meeting 05.

**Action:** verify today whether this is still true, or if it's been fixed and we just didn't close the ticket.

---

## ⚪ Quick wins for tomorrow (safe, no demo risk)

1. Update `qi_registry.json` — add qi-dashboard@9000, mark qi_web_panel@8651 deprecated. **Safe, doc-only.**
2. Delete `~$syFlow_Summary_2026-04-13_1500.docx` lock file.
3. Commit all `C:\UNIVERSAL\ECOSYSTEM\` doc changes (they're just docs).
4. `git init` `C:\UNIVERSAL\dashboard\` and do a first commit — **critical**, it has no backup.
5. Move `_build_easyflow_strategy_docx.py` out of `Session_Summaries\` into `C:\APPS\EasyFlow\TOOLS\`.

---

## 🔥 Demo-day checklist (run first thing tomorrow morning)

```
1. curl http://localhost:8001/health   → expect {"status":"ok"}   [Maia API]
2. curl http://localhost:7860          → expect HTTP 200          [Maia UI]
3. curl http://localhost:8010/health   → expect {"status":"ok"}   [NEXUS API]
4. curl http://localhost:7880          → expect HTTP 200          [NEXUS UI]
5. curl http://localhost:9000          → expect HTTP 200          [Orchestrator]
6. Open http://localhost:9000 — verify it loads and shows Maia + NEXUS green
```

If any fail: **restart via existing scripts, don't modify code.**

---

## 📋 Tomorrow's proposed order

1. Demo-day health check (5 min)
2. Decide: 8600 merge vs iframe (10 min)
3. Safe quick wins #1–#5 above (20 min)
4. Design per-project tab layout in 9000 dashboard — sketch + review with Renne (30 min)
5. Implement per-project tabs (rest of the day)
6. After demo: decide what to commit in Maia + NEXUS from today's uncommitted changes

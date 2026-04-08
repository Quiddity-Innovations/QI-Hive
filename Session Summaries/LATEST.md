# Claude Meeting 05 — Handoff Brief
# Date: 2026-04-08 | Status: READY TO START

---

## AGENT PRE-TASK BRIEF
> Every agent MUST read this before starting any task.
> Check status.json at C:\Claude\status.json for live project state.

---

## Current System State (Verified 2026-04-08)

### All Services LIVE
| Service | Port | Status |
|---|---|---|
| Maia | 8001 | ✅ Running |
| Naya | 8002 | ✅ Running |
| NEXUS | 8010 | ✅ Running |
| Dashboard | 8600 | ✅ Running (ClaudeManager NSSM RUNNING — confirmed) |

### All Repos Clean
| Repo | Branch | Status |
|---|---|---|
| Quiddity-Innovations/MAIA | main | ✅ Pushed (4b4d881) |
| Quiddity-Innovations/NEXUS | master | ✅ Pushed (4100d75) |
| rennesan/OC-Orchestrator | master | ✅ Pushed (f782e4a) |
| Quiddity-Innovations/CLAUDE-MANAGER | master | ✅ Pushed (f0f8a12) — NEW REPO |

---

## What Was Proven (Do Not Re-debate)

- **ClaudeManager NSSM** — RUNNING (self-resolved from PAUSED state in Meeting 03)
- **CLAUDE-MANAGER GitHub** — Created + pushed: Quiddity-Innovations/CLAUDE-MANAGER
- **/api/ping test** — 10/10 tests passing in test_dashboard_api.py
- **maia.db** — 38 tables, 6 bots (Maia=active), 30 people, 903 conversations
- **NEXUS .gitignore** — API key files, LOGS/, data/ all ignored
- **All repos** — Maia (8 files), NEXUS (6 files), OC (11 files), CLAUDE-MANAGER (4 files) — all clean

---

## ⚠️ Known Issue: MCPs Don't Load in Worktree Sessions

MCPs registered in `C:\Users\renne\.claude.json` do **NOT** appear as tools when Claude Code
opens a session inside a git worktree (e.g., `claude/funny-margulis`).

**Evidence:** `search_skills` (openspace), `list_tables` (sqlite-maia), `git_log` (git) all
returned "No matching deferred tools found" during Meeting 04 worktree session.

**Fix to attempt in Meeting 05:**
Option A: Add MCP config to `C:\QI\.claude\settings.json` (project-level)
Option B: Start Claude Code from `C:\Claude` root (not a worktree) before running MCP tasks
Option C: Register MCPs in global `C:\Users\renne\.claude\settings.json` instead of `.claude.json`

---

## C:\Claude\ Structure (Current)

```
C:\Claude\
├── Agents\        architect, builder, scout, scribe, ops, inspector, tester
├── Dashboard\     server.py (7 endpoints), start_dashboard.bat, install_service.bat
├── OpenSpace\     cloned + .venv installed
├── Skills\        session-summary, git-commit, doc-generator, delegate-task,
│                  skill-discovery, fetch-ai-news
├── Tests\         10/10 passing (includes /api/ping test added in Meeting 04)
├── Tools\         patch_mcp_config.py, gen_meeting03_docx.js
├── Session Summaries\  Meetings 01-04 .docx + this LATEST.md
├── status.json    ← live state
└── tasks.json     ← kanban tasks
```

---

## Meeting 05 Agenda (In Order)

1. **Fix MCP session context** — diagnose why openspace/sqlite-maia/git MCPs don't load in worktrees; implement fix; verify all 5 MCPs appear as tools
2. **Run OpenSpace search_skills** — search for `fetch-ai-news`, `git-commit`, `session-summary`; import any cloud improvements
3. **First sqlite-maia MCP query** — `list_tables` then explore bots, config, conversations
4. **First git MCP use** — `git_log` on C:\QI via mcp__git__git_log
5. **NEXUS installer weekend test prep** — review wizard, note what to wipe before test (~2026-04-12)

---

## Known Issues

| Issue | Status |
|---|---|
| MCPs not loading in worktree sessions | ⚠️ OPEN — Meeting 05 Item 1 |
| NEXUS installer weekend test | ⏳ PENDING ~2026-04-12 |
| OC watchdog (oc-watchdog.sh) | ⏳ Needs testing in WSL |

---

## How to Start Meeting 05

Open a new Claude Code session and say:

```
Start Meeting 05. Read LATEST.md at C:\Claude\Session Summaries\LATEST.md
and status.json at C:\Claude\status.json. Then begin the agenda.
```

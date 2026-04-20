# QI Hive — Ecosystem Orchestration Dashboard

## What is QI Hive?

QI Hive is the command-and-control layer of the **Quiddity Innovations** ecosystem. It is a FastAPI
web application (port 8600) that gives the developer a single pane of glass across all QI projects:
live health checks, a kanban task board, service management, scheduled tasks, LLM usage tracking,
agent team status, and access to the QI Brain intelligence layer.

Think of it as the mission control for the machine running Maia, Naya, NEXUS, EasyFlow, and
all other QI projects simultaneously.

## The Problem We Solve

- Managing 9+ projects (each with NSSM services, git repos, ports, logs, and documentation)
  across one Windows machine is cognitive overload. Remembering what is running, what is broken,
  and what is next requires constant context-switching.
- Claude Code sessions are expensive. Without visibility into token spend per project and per model,
  costs accumulate invisibly. There is no native tool that parses Claude Code session JSONL files
  and produces cost breakdowns.
- Services crash. When they do, there needs to be an autonomous path to restart them — without UAC
  prompts blocking the loop. The elevation broker solves this.
- Cross-project task coordination had no single home — tasks lived in individual project backlogs
  with no unified view.

## Our Approach

QI Hive is built in three layers:

1. **Dashboard (FastAPI + AdminLTE)** — server-rendered HTML pages (no React, no SPA). Each page
   is a Python function returning HTML. Bootstrap 5 + AdminLTE v4 for layout; SortableJS for the
   kanban board. Dark mode. 12 navigation tabs.

2. **QI Brain client** — the dashboard queries QI Brain API (port 9010) for ecosystem snapshots,
   agent profiles, session logs, and feature/decision counts. Falls back to local JSON files
   (status.json, tasks.json) when Brain is offline.

3. **Elevation broker** — an autonomous service (QI_Elevate) that accepts whitelisted JSON commands
   from any Claude session and executes them as LocalSystem (NSSM restarts, process kills). Solves
   the UAC-in-the-loop problem. Protected by QI_ElevateWatchdog (Task Scheduler, 1-minute cadence).

## Who Uses QI Hive?

| Role | How they interact |
|---|---|
| **Developer (Renne)** | Browser at http://localhost:8600 — dashboard, health, board, usage, logs |
| **Claude Code sessions** | `from engine.common.qi_service import restart, start, stop` — autonomous service control |
| **QI Brain** | QI Hive is the primary consumer of the Brain API (port 9010) |
| **QI_ElevateWatchdog** | Task Scheduler polls NSSM every 1 minute — revives broker if stopped |

## Current Build Status (April 2026)

QI Hive is at **v3.0.0** (dashboard server). Active production — all core services running.

| Area | Status |
|---|---|
| FastAPI dashboard on port 8600 (QI_Dashboard) | ✅ Live |
| Health check page — 11 projects monitored | ✅ Live |
| Kanban task board (SortableJS, CRUD) | ✅ Live |
| LLM usage page — daily/project/model breakdowns | ✅ Live |
| Hive page — Brain stats, agent team, session log | ✅ Live |
| Services page | ✅ Live |
| Scheduled Tasks page | ✅ Live |
| Activity page | ✅ Live |
| Logs page | ✅ Live |
| Config page | ✅ Live |
| Guide page | ✅ Live |
| QI Brain client (port 9010 integration) | ✅ Live |
| Elevation broker (QI_Elevate, NSSM auto-restart) | ✅ Live |
| Elevation watchdog (Task Scheduler, 1-min cadence) | ✅ Live |
| gsudo — 8h credential cache (one UAC per workday) | ✅ Live |
| qi_service.py — autonomous service control for all Claude sessions | ✅ Live |
| usage_stats.py — parses Claude Code JSONL for cost tracking | ✅ Live |
| Brain backfill (80 sessions, 57 decisions) | 🔄 In progress |
| SessionEnd hook for automatic Brain logging | 🔄 In progress |

---
*This page is editable at `C:\QIH\INTRO\status_intro.md` — save and click Refresh to update.*

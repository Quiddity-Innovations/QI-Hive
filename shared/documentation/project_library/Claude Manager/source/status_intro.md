# Claude Manager — QI Hive Orchestration Workspace

## What is Claude Manager?

Claude Manager is the **Claude-Code management workspace** for **Quiddity Innovations** — the orchestration and
automation layer that *drives* the QI ecosystem from the Claude side. It is a meta-project: it does not serve users
or run on a port. Instead it is the place from which every other QI project is governed, reconciled, audited, and
remembered.

It lives at `C:\APPS\CLAUDE` and is registered in the ecosystem as `claude_manager`, family tier **backbone**, with the
explicit note: *"Management/meta workspace that operates ON the ecosystem rather than being a deployed app."*

This is deliberately distinct from **QI Hive** (`C:\QIH`) — the Hive's engine, dashboard (port 8600) and Brain API
(port 9011) are the *served* infrastructure. Claude Manager is the **Claude-side cockpit**: the sub-agent fabric,
the supervisor, the session hooks, the reconciliation scripts, and the automation tooling that keep the whole
ecosystem coherent.

## What problem it solves

The owner runs a dozen-plus parallel QI projects that share a machine, ports, git, and a Brain. Left alone they drift:
services stop, worktrees pile up, git goes uncommitted, sessions go unlogged, the Brain's memory falls out of sync
with reality. Claude Manager is the antidote — it is where the watching, reconciling, and dispatching happen.

- **Drift detection** — the supervisor walks every registered project and flags red/yellow/green.
- **Orchestration discipline** — a 8-agent Hive fabric turns Claude from a single doer into a dispatcher.
- **Memory guarantees** — session/sub-agent hooks ensure every session leaves a trace in the Brain.
- **Environment hygiene** — a monthly self-audit kills orphaned MCP processes, prunes worktrees, and clears the
  "file in use" lock that used to force full reboots of Claude Desktop.

## How it works (the four layers)

| Layer | What it is | Where |
|---|---|---|
| **Agent fabric** | 8 `hive-*` sub-agent definitions + the Dispatch Protocol | `C:\APPS\CLAUDE\.claude\agents\` |
| **Supervisor** | Cross-project drift scanner → DASHBOARD.md + report.json + Hive status.json | `C:\APPS\CLAUDE\supervisor\supervisor.py` |
| **Hooks** | SessionEnd + SubagentStop wired in project settings; SessionStart context injection (global) | `C:\APPS\CLAUDE\.claude\settings.json` + `~\.claude\*.py` |
| **Automation / Tools** | Restart guard, monthly self-audit, Brain reconciliation, Tasuke notify, migrations | `C:\APPS\CLAUDE\Tools\` |

## Who uses it

| Role | How they interact |
|---|---|
| **Owner** | Owner. Runs sessions here; receives Tasuke LINE alerts; decides on audit gates |
| **Claude Code (main thread)** | The dispatcher — routes work to `hive-*` sub-agents per the Dispatch Protocol |
| **Hive sub-agents** | architect / builder / inspector / ops / scout / scribe / tester / librarian |
| **QI Brain & QI Hive** | Consumers — Manager writes reconciliation, sessions, and status into them |

## Current Build Status (June 2026)

Claude Manager is **operational**. The ecosystem was fully booted + reconciled across 2026-06-10..12 and a
drift watchdog is live.

| Area | Status |
|---|---|
| 8 `hive-*` sub-agent definitions (architect, builder, inspector, ops, scout, scribe, tester, librarian) | ✅ Live |
| Dispatch Protocol (standing routing rule) | ✅ Live |
| Supervisor — cross-project drift scan → DASHBOARD.md + report.json + Hive status.json | ✅ Live |
| SessionEnd hook (auto-stub every session to the Hive inbox → Brain) | ✅ Live |
| SubagentStop hook (attribute sub-agent work to the right Hive role) | ✅ Live |
| SessionStart context injection (global hook — ecosystem briefing + Brain probe + dispatch reminder) | ✅ Live |
| Claude restart guard + Clean-Restart tool (kills orphaned MCP trees / clears install locks) | ✅ Live |
| Monthly self-audit (`QI_ClaudeSelfAudit`, last Friday) + Tasuke LINE notify + decision gate | ✅ Live |
| Brain reconciliation / backfill scripts | ✅ Live — run-on-demand |
| Secrets + env migration tooling | ✅ Live — run-on-demand |
| Supervisor as a scheduled/continuous watchdog service | 🗓️ Planned — currently run-on-demand |
| Auto-dispatch (harness-level routing, not manual discipline) | 🗓️ Planned — not supported by the harness |
| Per-product NSSM naming standardization batch | ⚠️ Staged — armed for a Friday window, not yet applied |

## The orchestration principle

> *"I am the dispatcher, not the doer of everything."* — `DISPATCH_PROTOCOL.md`

Claude Code does not auto-route. The protocol is a **discipline the main thread follows**: if a sub-task fits a
role, dispatch it via the `Agent` tool with `subagent_type=hive-<role>`. Design → architect, implement → builder,
review → inspector, ops → ops, research → scout, docs → scribe, tests → tester, find/curate docs → librarian.
The main thread orchestrates; the agents do.

---
*This page is editable at `C:\APPS\CLAUDE\INTRO\status_intro.md` — save and click Refresh to update.*

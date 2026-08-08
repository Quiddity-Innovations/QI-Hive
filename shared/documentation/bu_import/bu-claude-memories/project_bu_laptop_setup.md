---
name: project-bu-laptop-setup
description: "BU laptop dev environment setup — QI Hive context, IP separation, OnBase/CogniBase architecture, hybrid plan"
metadata: 
  node_type: memory
  type: project
  originSessionId: 815d365b-c45b-41b0-8e56-d6310c70b7a6
---

BU laptop (IST-APP-WL-0436) is being set up as a compliance-first, IP-clean subset of the user's personal QI Hive ecosystem on their personal GPU workstation.

**Why:** User works at Boston University AND runs Quiddity Innovations (QI). The BU laptop is a separate, BU-owned machine where all work must be BU-owned content only.

**Key constraints:**
- All BU work lives under `C:\BU\` — IP-clean by structure
- Quiddity IP (QI Hive, QI Brain, QI memory, MapSnap/AutoPDF) must NOT come onto this machine
- No local LLMs (Intel integrated GPU only) — cloud API required
- Manual service starts only (battery + monitored machine)
- BU IT confirmation needed: "Claude Desktop" approval must be verified to cover Claude Code CLI

**Core architecture:**
- OnBase: REST API only (no DB access), Postman-first, read-only by default, typed Python client (httpx + pydantic)
- CogniBase: BU analog of QI Brain, FastAPI + SQLite → Postgres, cloud embeddings/reasoning
- 5 sub-agents: bu-architect, bu-builder, bu-inspector, bu-scout, bu-scribe
- MCP servers scoped to `C:\BU\` only

**Validated component list (~9.4 GB, or ~5.5 GB deferring VS Build Tools):**
- Scoop, Git, Python+uv, pyenv-win, nvm-windows+Node LTS, pnpm, Windows Terminal, PowerShell 7+, VS Code, jq, mkcert, dotenv
- PostgreSQL, Redis (via WSL), Rancher Desktop (not Docker Desktop — BU exceeds 250-employee threshold)
- VS Build Tools: deferred until a native Python package requires C++ workload
- Postman: already installed

**Key documents:** `C:\AI\Documentation\dev-environment-components.docx` (component list + hybrid plan); `C:\AI\Documentation\AI-Workspace-Framework.md` (master living framework); `C:\AI\Documentation\Project-Structure-Standard.md` (folder standard v1.2); `C:\AI\Documentation\Setup-Phases-and-Prompts.md` (Table A + Table B + the two reusable copy-paste session prompts for Claude-env setup and BU Hive build).

**Setup prompt:** Section 9 of `BU-Laptop-Replication-Report_2026-06-19.docx` (on \\powerspec) contains the ready-to-paste Phase 0–5 Claude Code setup prompt.

**BU Hive dashboard (designed 2026-06-19, build DEFERRED until user triggers):**
- Local FastAPI + SQLite + Jinja2 dashboard under C:\BU\bu-hive, 127.0.0.1:8730, manual launch, no service.
- 4-tier project lifecycle ACCEPTED: Tier 1 POC -> Tier 2 Dev & Test -> Tier 3 Beta (Super Users) -> Tier 4 Production (4a targeted / 4b BU-wide).
- Promotion gates: ENFORCED with override option; overrides recorded as audit events.
- Control panel: tier pipeline board + per-project profile (tier history, gate checklist, linked activity), register/promote/demote flow.
- 7 sub-agents: bu-architect, bu-builder, bu-inspector, bu-scout, bu-scribe, bu-ops, bu-tester.
- Auto-logging via Claude Code hooks (SubagentStop/SessionStart/Stop), MERGED into existing settings.json (never overwrite the git-guardrail PreToolUse hook).
- Phase 0 detection done: guardrail hook PRESENT, no managed policy, Python is stub + uv missing (must install both as prereq), port 8730 free, C:\BU empty.

**Session minutes (set up 2026-06-19):** C:\AI\Sessions\{chat,cowork,code}\ holds meeting-minutes records (distilled, end-of-session). Only "code" (Claude Code) is auto-capturable from this machine via a proposed Stop hook (not yet wired). See README + TEMPLATE there.

**Logs / heartbeat (folder + spec set up 2026-06-19, automation deferred):** C:\AI\Logs\ holds raw heartbeat logs — every 5 min appends new session content. Filename: <SessionName>_<YYYY-MM-DD>_<HH-MM-SS>.txt (24H, hyphens since colons illegal in filenames). In-content timestamps: [YYYY-MM-DD HH:MM:SS], ISO 8601, TZ America/New_York declared in header. Interval configurable via .env HEARTBEAT_MINUTES=5. Hooks are event-driven not timer-driven, so heartbeat needs either a manual per-session Start-Heartbeat.ps1 (default, battery-friendly) or a Task Scheduler job (always-on alt). Logs = verbatim/continuous; Sessions = distilled summary. See C:\AI\Logs\README.md.

**Install kit (prepared 2026-06-19, NOT yet run):** C:\AI\Projects\claude-env-setup\ is a modular, shareable installer kit (follows the project standard, kind=automation). Two separate script groups:
- scripts\claude-env\ — PORTABLE Claude environment kit. Master menu Install-ClaudeEnv.ps1 (+ .cmd bootstrap) auto-discovers installers\NN_*.ps1 by numeric prefix, builds menu from each file's "# DESC:" line, offers "[A] Install everything" last. Steps: 00 detect, 10 Scoop, 20 Git, 30 Python+uv, 40 Node+pnpm, 50 core tools, 60 VS Code, 70 Claude Code, 80 git guardrails (merge), 90 dev services (optional). To add a tool: drop a new NN_*.ps1 — no master edit.
- scripts\bu-hive\ — BU-only build (Build-BUHive.ps1 + steps\ + schema.sql). Steps 10 scaffold/20 init-db/30 seed-agents are ready; 40 hooks + 50 dashboard are placeholders pending build trigger.
All 18 .ps1 parse-validated. Scripts wrapped with AI-GENERATED markers per global policy. Detection confirms: git present (2.54), python=stub, uv/node/pnpm/scoop/code/claude absent, guardrail hook present.

**Project _template:** C:\AI\Projects\_template\ holds the standard skeleton (README, PROJECT.md, .gitignore, docs/src/tests/examples/config with .gitkeep) to copy for new projects.

**How to apply:** When helping with BU work, assume C:\BU\ workspace, no QI IP references, cloud-only LLM, OnBase is production/read-only, and guardrails are in place. BU Hive build is on hold until the user explicitly triggers it. Nothing in the install kit has been RUN yet — only prepared.

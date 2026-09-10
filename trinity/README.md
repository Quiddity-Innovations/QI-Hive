# Trinity — Tri-Platform AI Orchestration

Claude (spearhead) + ChatGPT via `codex mcp-server` + Gemini via `qi_gemini_mcp.py`.
30-day trial started 2026-09-08 — review 2026-10-16. No ports, no services, nothing unattended.

## Components

- `C:\QIH\engine\mcp\qi_gemini_mcp.py` — Gemini MCP server
- `C:\QIH\engine\tools\qi_trinity_check.py` — Trinity health check ("Trinity check")
- `C:\QIH\engine\tools\qi_trinity_check_selftest.py` — **proves the Codex MCP handshake check
  actually goes RED** when Codex cannot serve MCP (missing binary, 0.154.0-style app-server,
  silent binary). Run it after touching `check_codex_handshake`. Added 2026-09-09 because the
  previous liveness signal was a process count that reported PASS with zero servers running.
- `C:\QIH\engine\tools\qi_trinity_check_codex.sh` — Codex-side health check
- `C:\QIH\engine\tools\qi_trinity_hr_log.py` — Agent HR logging for Trinity runs (manual/CLI)
- `C:\Users\renne\.claude\hooks\log-trinity-run.py` — **PostToolUse hook, auto-logs every
  `mcp__qi-gemini__*` / `mcp__codex__*` call to Agent HR** (added 2026-09-09; kill switch
  `QI_TRINITY_HR_HOOK=off`; diagnostics in `C:\QIH\engine\hive\agents\LOGS\trinity_hr_hook.log`)
- `C:\QIH\config\gemini_mcp.json` — Gemini MCP config
- `C:\QIH\config\vendors\` — vendor-specific config
- `C:\QIH\shared\handoff\` — cross-platform handoff files
- `C:\QIH\data\trinity\` — Trinity data store
- `C:\QIH\secrets\trinity_gemini.env` — Gemini credentials (name only — never print contents)

## Plans and guides

- `C:\QIH\shared\documentation\plans\QI_TriPlatform_AI_Orchestration_Plan_2026-09-08.md`
- `QI_Trinity_Model_Guide_2026-09-08.md`
- `QI_Trinity_Onboarding_Design_2026-09-08.md`

## Claude Code integration

- MCP entries `codex` and `qi-gemini` registered in `C:\Users\renne\.claude.json`
- 🔴 **Codex CLI PINNED at 0.153.4 — do NOT upgrade.** `codex mcp-server` was deprecated in
  0.149.1 and **removed in 0.154.0**. `codex app-server` is NOT an MCP server (it speaks
  OpenAI's own JSON-RPC app-server protocol; probed 2026-09-09 — answers `initialize` with
  `userAgent`/`codexHome`, not `protocolVersion`/`capabilities`). Upgrading kills the Codex
  leg entirely. Broke on 2026-09-09, rolled back same day; 0.153.4 verified serving MCP
  (`serverInfo.name = "codex-mcp-server"`, `protocolVersion 2024-11-05`).
  `qi_trinity_check.py` now FAILS on >= 0.154.0 and no longer recommends upgrading.
  Forward path when the pin becomes untenable: the **Codex plugin for Claude Code**.
- Agent HR project: `trinity`
- Routing policy lives in `C:\Users\renne\.claude\CLAUDE.md` §1a (added 2026-09-09) — the
  model ladder used to be Claude-only and did not name either assistant
- Runs auto-log: `PostToolUse` matcher `mcp__qi-gemini__.*|mcp__codex__.*` in
  `C:\Users\renne\.claude\settings.json`. Verified firing live 2026-09-09.
  Never records prompt or reply text — sizes, model and outcome only.

Do not delete `C:\QIH\trinity\_probe\`.

## Nightly refresh (approved 2026-09-08 — wired)

`QI_NightlyReconcile` runs at 00:30 and should call the onboarding generator
after the registry reconciliation step, so the brief can never be older than
the registry (design doc §5, §7 step 5). Owner approved 2026-09-08 evening; the call
lives inside `C:\QIH	ools
ightly_reconcile.py` (the script the SYSTEM task runs, so no
task edit or elevation was needed), isolated in its own try/except. Freshness of
`ONBOARDING.md` is watched by `QI_TaskHealth` entry `QI_TrinityOnboarding` (26 h).
Equivalent manual command:

    python C:\QIH\engine\tools\qi_trinity_onboarding.py --ecosystem --all

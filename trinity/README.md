# Trinity — Tri-Platform AI Orchestration

Claude (spearhead) + ChatGPT via `codex mcp-server` + Gemini via `qi_gemini_mcp.py`.
30-day trial started 2026-09-08 — review 2026-10-16. No ports, no services, nothing unattended.

## Components

- `C:\QIH\engine\mcp\qi_gemini_mcp.py` — Gemini MCP server
- `C:\QIH\engine\tools\qi_trinity_check.py` — Trinity health check ("Trinity check")
- `C:\QIH\engine\tools\qi_trinity_check_codex.sh` — Codex-side health check
- `C:\QIH\engine\tools\qi_trinity_hr_log.py` — Agent HR logging for Trinity runs
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
- Agent HR project: `trinity`

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

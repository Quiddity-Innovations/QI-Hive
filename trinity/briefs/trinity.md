# Trinity (trinity) — L2 brief

_Generated 2026-09-10 02:35:09_

## Registry facts
- Path: `C:\QIH\trinity`
- Status: active
- Phase: 30-day assistant trial → review 2026-10-16
- Notes: Claude (spearhead) + ChatGPT via codex mcp-server + Gemini via qi_gemini_mcp.py. Components listed in C:\QIH\trinity\README.md. No ports, no services, nothing unattended.

## Brain
- Current state: status=active, phase=30-day assistant trial → review 2026-10-16
  Claude (spearhead) + ChatGPT via codex mcp-server + Gemini via qi_gemini_mcp.py. Components documented in C:\QIH\trinity\README.md. No ports, no services, nothing unattended.
- Last decisions:
  - Codex MCP liveness is now a real handshake, not a process count â€” and the check has a self-test (2026-09-10)
  - Codex CLI PINNED at 0.153.4 â€” 0.154.0 removed `codex mcp-server` and took the Codex leg offline (2026-09-10)

## CLAUDE.md rules
# Trinity — CLAUDE.md
## The rule
triggered by a human or by Claude acting on a live task — never by a
scheduled task, cron job, or background daemon. Health checks poll status
only; they never place a model call on their own.

## References
## Commands

## Entry points
- none found

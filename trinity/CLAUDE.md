# Trinity — CLAUDE.md

Trinity is QI's tri-platform AI orchestration effort: Claude (spearhead) +
ChatGPT via `codex mcp-server` + Gemini via `qi_gemini_mcp.py`. It is a
30-day assistant trial (started 2026-09-08, review 2026-10-16) with no
ports and no services of its own — see `C:\QIH\trinity\README.md` for the
component list.

## The rule

**Nothing unattended calls an assistant.** Every Codex/Gemini call is
triggered by a human or by Claude acting on a live task — never by a
scheduled task, cron job, or background daemon. Health checks poll status
only; they never place a model call on their own.

## References

- `C:\QIH\ecosystem\QI_Standards.md` — naming, folder, docs, code conventions.
- `C:\QIH\ecosystem\qi_registry.json` — ports, services, project relationships
  (this project has none registered; Brain API is `qi_brain` at :9011).

## Commands

- `python C:\QIH\engine\tools\qi_trinity_check.py --ping` — Trinity health check.
- `python C:\QIH\engine\tools\qi_trinity_onboarding.py --all` — regenerate the
  L1 ecosystem brief and every L2 project brief.
- `python C:\QIH\engine\tools\qi_trinity_hr_log.py` — Agent HR logging for
  Trinity runs.

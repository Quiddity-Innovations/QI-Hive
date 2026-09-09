# AutoPDF (autopdf) — L2 brief

_Generated 2026-09-09 02:38:45_

## Registry facts
- Path: `C:\APPS\AutoPDF`
- Status: Active Dev
- Phase: 2c
- Ports: http:6969, mcp:8701
- Services: QI_AutoPDFMCP

## Brain
- Current state: status=active, phase=Hardening + MCP integration
  Six weeks of accumulated work committed and pushed to GitHub (0a367e5, master) - the first commit since 2026-06-29. Three bodies of work landed together: (1) regex-library corruption root-caused to regression test 5*.10 and fixed durably with a server-side integrity guard on POST /api/regex-library-save plus a .prev generation backup; library reseeded to 30 built-ins. (2) MCP gateway - AutoPDF is an MCP server on 127.0.0.1:8701 running as QI_AutoPDFMCP, nine independently switchable tools, disabled tools never registered. (3) Settings reorganization - AI config split into its own "AI & Connections" section, every group given an explicit id. Regression suite is 28 PASS / 0 FAIL / 1 SKIP. Documentation regenerated (Technical Documentation, Technical Guide, User Guide, Test Guide, Cheatsheet) with the regex-library endpoints, the guard's rationale, and new test-guide rows 5*.11/5*.12. .gitignore corrected: live config/mcp_gateway.json now stays local (per-install, same rule as autopdf-settings.json) while the template ships, and Application/_register_mcp_service.ps1 was un-ignored - the _*.ps1 scratch rule had been swallowing a real deliverable. Version backup at _backups/2026-08-07_1527_before-commit-regexguard.
- No project-scoped decisions recorded.

## CLAUDE.md rules
# AutoPDF — Claude Session Instructions
*Project-specific instructions. The global QI standards in `C:\Users\renne\.claude\CLAUDE.md` and `C:\QIH\ecosystem\QI_Standards.md` always apply on top of these.*

*Registry entry: `C:\QIH\ecosystem\qi_registry.json` → projects → autopdf*
## Project at a glance
## Tech stack reminders
## Key conventions specific to AutoPDF
- **Web responses**: every `Send-Json` call MUST allow `-Depth 10` (set globally in the helper). Default depth-2 silently truncates nested arrays.
- **Frontend hooks**: when preview-panel-aware, every Edit on `AutoPDFTool.html` triggers a hook reminding the assistant the file is visible. Don't re-acknowledge each one — say it once per major HTML change pass.
- **Hard-refresh required**: after any `.html` / `.js` / `.css` change, the user must Ctrl+F5. After any `.ps1` change, the user must restart the service via the ↻ button. Always remind them.

## Templates and the regex library
These are the Phase 2 architectural concepts. Don't reinvent them:

- **Three field kinds** — `zone` (fixed rect), `regex_match` (page-text scan), `ai_extract` (LLM at run-time)
## Things the user has explicitly asked for
## Things the user does NOT want
## Test suites — when to run which
- **Manual `.docx` checklist** (`Documentation/AutoPDF_Test_Guide.docx`) — only items the automated tiers don't reach (zone drawing, modal animations, visual judgment).

## Documentation regeneration
## Session end protocol
## Common pitfalls Claude has hit before
## Where the user is in their journey

## Entry points
`AutoPDFTool.html`, `zone-mapper.html`

# AutoPDF (autopdf) — L2 brief

_Generated 2026-09-12 02:35:04_

## Registry facts
- Path: `C:\APPS\AutoPDF`
- Status: Active Dev
- Phase: 2c
- Ports: http:6969, mcp:8701
- Services: QI_AutoPDFMCP

## Brain
- Current state: status=active, phase=Hardening + MCP integration; feature-tour videos delivered 2026-08-11
  Backfilled 2026-09-09 from QI_Project_Status_Report_2026-09-09.docx (Claude Fable 5.1). QI_AutoPDF :6969 and QI_AutoPDFMCP :8701 RUNNING. 2026-08-07 landed the regex-library integrity guard and the MCP gateway (9 tools); 2026-08-11 delivered 6 feature-tour video cuts and fixed /api/workflow-list returning a bare string. 2026-09-09: root CLAUDE.md / NEXT_SESSION_PROMPT.md brought current (they had said "no git").
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
- **Manual `.docx` checklist** (`docs/AutoPDF_Test_Guide.docx`) — only items the automated tiers don't reach (zone drawing, modal animations, visual judgment).

## Documentation regeneration
## Session end protocol
## Common pitfalls Claude has hit before
## Where the user is in their journey

## Entry points
`AutoPDFTool.html`, `zone-mapper.html`

# NEXUS (nexus) — L2 brief

_Generated 2026-09-09 02:38:45_

## Registry facts
- Path: `C:\APPS\NEXUS`
- Status: active_development
- Ports: api:8010, ui:7880, mcp:8310
- Services: nexus_api, nexus_ui, QI_NexusMCP
- Notes: The AI intelligence layer. Not a user-facing product — it serves all other projects. In the unified app, NEXUS becomes the AI engine module that powers everything.

## Brain
- Current state: status=active, phase=Phase 2 — NSSM-supervised
  API :8010 + UI :7880 + tunnel live. 7 providers wired, Scout digest live.
- No project-scoped decisions recorded.

## CLAUDE.md rules
# NEXUS — Claude Project Instructions
## SESSION START PROTOCOL (Mandatory — Every Session)
4. **Silently internalize** — do NOT summarize back to Renne unless asked
5. **Only then** respond to the first message

## QI Standards
## Role
## What NEXUS Is
## QI Ecosystem Position
## Tech Stack
## AI Provider Channels
## Design Principles (Never Violate)
4. **Schema-versioned** — DB has a `schema_version` table, always migrate cleanly
5. **Future-proof** — new AI tech should slot in without rearchitecting

## File Structure
## Secrets
Never hardcode keys. Never commit secrets.

## Documentation
## Ports (verified against all QI projects)

## Entry points
`CLEANUP_Old_NEXUS_Folder.bat`, `NEXUS_Control.bat`, `NEXUS_Install.bat`, `NEXUS_Install_Tunnel.bat`, `NEXUS_MCP_Register.bat`, `NEXUS_MCP_Test.py`, `NEXUS_Restart.bat`, `NEXUS_Setup.bat`, `NEXUS_Start.bat`, `NEXUS_Start_ScoutOnly.bat`, `VERIFY_ClaudeMax.bat`, `VERIFY_ClaudeMax.py`, `fix_service_path.bat`, `install.py`, `main.py`, `nexus_mcp.py`, `regression_test.py`, `save_session_summary.py`, `save_session_summary_2.py`, `smoke_test.py`, `uninstall.py`

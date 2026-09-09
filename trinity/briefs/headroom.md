# Headroom (headroom) — L2 brief

_Generated 2026-09-09 02:38:45_

## Registry facts
- Path: `C:\APPS\CLAUDE\Tools`
- Status: pilot
- Ports: proxy:9020, mcp:stdio
- Notes: Pilot 2026-07: proxy in front of Ollama first (OPENAI_API_BASE=http://localhost:11434/v1), then NEXUS providers if savings hold. Do NOT re-point Claude Code's own endpoint through the proxy — subscription OAuth path stays untouched; Claude Code uses the MCP mode instead.

## Brain
- Current state: status=active, phase=Pilot -- proxy fronting Ollama, not yet promoted to NSSM service
  Open-source context/token compression proxy + MCP server, shared ecosystem infrastructure. No dedicated CLAUDE.md/docs folder exists under its registered path (C:\APPS\CLAUDE\Tools, a shared tools dir); per the registry's own family_notes, piloted in front of Ollama first (OPENAI_API_BASE localhost:11434) before NEXUS providers, promotion to QI_Headroom NSSM service pending adoption decision.
- No project-scoped decisions recorded.

## CLAUDE.md rules
- No CLAUDE.md found (or no matching rule/heading lines).

## Entry points
`Claude-Clean-Restart.bat`, `Install_QI_Headroom_Service.bat`, `QI_DomainDropWatch.bat`, `Register-ClaudeUpdateTask.bat`, `brain_reconcile_2026_06_10.py`, `bu_video_scripts.py`, `build_bu_videos.py`, `claude_session_restore.py`, `claude_update_launch.bat`, `domain_drop_watch.py`, `gen_app_it_docs.py`, `gen_bu_assessment.py`, `gen_bu_dev_env_request.py`, `gen_claude_update_summary.py`, `gen_component_inventory.py`, `gen_inventory_pdf.py`, `gen_meeting03_docx.js`, `gen_meeting04_docx.py`, `gen_session_summary_20260808.py`, `gen_session_summary_20260808_final.py`, `gen_session_summary_20260809_voicestudio.py`, `gen_session_summary_20260810_mediastudio.py`, `gen_session_summary_20260810_voicestudio_panel.py`, `gen_techstack_doc.py`, `gen_video_script_docs.py`

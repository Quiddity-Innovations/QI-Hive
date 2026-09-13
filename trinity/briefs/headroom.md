# Headroom (headroom) — L2 brief

_Generated 2026-09-12 02:35:04_

## Registry facts
- Path: `C:\APPS\CLAUDE\Tools`
- Status: pilot
- Ports: proxy:9020, mcp:stdio
- Notes: Pilot 2026-07: proxy in front of Ollama first (OPENAI_API_BASE=http://localhost:11434/v1), then NEXUS providers if savings hold. Do NOT re-point Claude Code's own endpoint through the proxy — subscription OAuth path stays untouched; Claude Code uses the MCP mode instead.

## Brain
- Current state: status=active, phase=Promoted — QI_Headroom NSSM service live on :9020 fronting api.anthropic.com
  Backfilled 2026-09-09 from QI_Project_Status_Report_2026-09-09.docx (Claude Fable 5.1). Contrary to the registry ("pilot, not yet promoted"), QI_Headroom is SERVICE_RUNNING (headroom-proxy 0.32.1, ~3.6 days uptime on 2026-09-09) via Tools/headroom_env; upstream is https://api.anthropic.com, not Ollama as documented. Internal kompress backend reports unhealthy while overall status is healthy. Stale 2.0 GB headroom_env.old deleted 2026-09-09; venv untracked from git.
- No project-scoped decisions recorded.

## CLAUDE.md rules
- No CLAUDE.md found (or no matching rule/heading lines).

## Entry points
`Claude-Clean-Restart.bat`, `Install_QI_Headroom_Service.bat`, `QI_DomainDropWatch.bat`, `Register-ClaudeUpdateTask.bat`, `brain_reconcile_2026_06_10.py`, `bu_video_scripts.py`, `build_bu_videos.py`, `claude_session_restore.py`, `claude_update_launch.bat`, `domain_drop_watch.py`, `gen_app_it_docs.py`, `gen_bu_assessment.py`, `gen_bu_dev_env_request.py`, `gen_claude_update_summary.py`, `gen_component_inventory.py`, `gen_inventory_pdf.py`, `gen_meeting03_docx.js`, `gen_meeting04_docx.py`, `gen_session_summary_20260808.py`, `gen_session_summary_20260808_final.py`, `gen_session_summary_20260809_voicestudio.py`, `gen_session_summary_20260810_mediastudio.py`, `gen_session_summary_20260810_voicestudio_panel.py`, `gen_techstack_doc.py`, `gen_video_script_docs.py`

# MapSnap (mapsnap) — L2 brief

_Generated 2026-09-11 02:36:20_

## Registry facts
- Path: `C:\APPS\MapSnap`
- Status: active_stable
- Ports: api:9876, mcp:8651
- Services: QI_MapSnapMCP
- Notes: Sibling of cognibase (same DNA, different scope). MapSnap = engine-agnostic schema intelligence over any structured system of record (proposes canonical-key mappings for the BU federation); cognibase = live OnBase + cross-source correlation/governance. Kept separate intentionally to insulate the stable discovery tool from the integration product's churn.

## Brain
- Current state: status=active, phase=Active stable — secret-reference migration done 2026-08-17; Unity API buttons pending verification
  Backfilled 2026-09-09 from QI_Project_Status_Report_2026-09-09.docx (Claude Fable 5.1). QI_MapSnap :9876 and QI_MapSnapMCP :8651 healthy. 2026-08-17 closed a live OpenRouter-key exposure (GET /api/settings served the key over the public tunnel): qi_secrets.py resolver, key moved to an ACL-locked env file, backups redacted. 2026-08-14 shipped login-race fix, 6 OnBase Unity common-elements collections, environment profiles, 39-table Setup Guide + installer. The previous "OnBase DNA Tier C" phase label belongs to project onbase_dna.
- No project-scoped decisions recorded.

## CLAUDE.md rules
- No CLAUDE.md found (or no matching rule/heading lines).

## Entry points
`Install_MapSnap.bat`, `install_tunnel_service.bat`, `refresh.bat`, `save_session_summary_20260503d.py`, `save_session_summary_20260503e.py`, `save_session_summary_20260504a.py`, `save_session_summary_20260623.py`, `save_session_summary_20260624.py`, `schema_browser.html`, `start.bat`

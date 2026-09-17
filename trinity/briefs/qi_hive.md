# QI Hive (qi_hive) — L2 brief

_Generated 2026-09-17 02:35:37_

## Registry facts
- Path: `C:\QIH`
- Status: active_development
- Ports: dashboard:8600
- Services: QI_Dashboard, QI_BrainAPI
- Notes: The nervous system and operational layer. Absorbs Claude Manager. QI Brain is the hive mind. Agents are the bees.

## Brain
- Current state: status=active, phase=Operational â€” audit remediation verified
  [auto:state_file] The 2026-09-16 audit remediation is verified end to end. Backups, task health, usage snapshots and all five scheduled ops actions pass; the full section-5 dashboard checklist was confirmed independently. Three defects found during verification were fixed: a supervisor KeyError that had silently froz
- Last decisions:
  - Health checks assert on the artifact, not on a tool's exit code (2026-09-17)
  - Per-day success markers are the Hive's task-health standard; services with dependents restart by relaunching the NSSM child, never sc stop (2026-09-16)
  - LLM Usage figures are ~6x overstated; remediation (dedup + per-model pricing + ledger re-snapshot) delegated to Opus 5, backup fix first (2026-09-16)

## CLAUDE.md rules
- No CLAUDE.md found (or no matching rule/heading lines).

## Entry points
`APPLY_DEMO_FIXES_admin.bat`, `probe_license.bat`, `probe_license.html`, `probe_license.py`, `probe_license2.py`, `probe_license_api.py`, `probe_license_server.py`, `update_services.bat`

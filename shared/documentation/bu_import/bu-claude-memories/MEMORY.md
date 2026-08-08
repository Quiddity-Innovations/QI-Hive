# Memory Index

- [Directory Policy](project_directory_policy.md) — Root dirs: C:\AI (projects), C:\AI Temp (scratch), C:\AI\Projects (project folders), C:\AI\Documentation (Claude docs)
- [BU Laptop Setup](project_bu_laptop_setup.md) — Phase 0–5 hybrid plan: OnBase/CogniBase arch, IP separation, validated component list, setup prompt location
- [User: QI + BU Context](user_qi_bu_context.md) — User runs Quiddity Innovations (QI Hive/GPU workstation) AND works at BU IT; strict IP separation between them
- [Project Structure Standard](project_structure_standard.md) — Binding folder/naming standard (v1.3): canonical names (src/docs/tests/examples...), required docs/ contents, override via PROJECT.md, projects under C:\AI\Projects or C:\BU
- [Documentation Standard](project_documentation_standard.md) — v1.0 (2026-06-20): every product keeps a living User Guide + Technical Documentation, updated with the product, gated by tier, freshness on BU Hive /docs
- [Claude Env Setup](project_claude_env_setup.md) — 2026-06-19 BU laptop: toolchain via winget (Scoop blocked), node via C:\nvm4w\nodejs on User PATH, control panel + LLM harness built, all approval-gated items disabled (Claude CLI pending BU IT)
- [Claude Voice](project_claude_voice.md) — Claude has REAL voice I/O on this laptop via ClaudeVoice (C:\AI\Products\ClaudeVoice): edge-tts male "Claude" voice + Whisper STT + file-bus bridge; speak via `.venv\Scripts\python.exe speak.py "..."` — NOT text-only
- [Data Compliance](project_data_compliance.md) — No student/staff/PII data flows through BU Hive, ClaudeVoice, or any project; don't raise reflexive FERPA caveats; user will fully comply if that ever changes
- [Claude Connector Guard](project_claude_connector_guard.md) — Claude Desktop drops mcpServers on every save; C:\AI\tools\ClaudeConnectorGuard (Install.bat / -Status) restores BUHive+MapSnap, supersedes BU Hive's setup_desktop_connector.ps1
- [OnBase Note Type Decoder](project_onbase_notetype_decoder.md) — genotype→phenotype decode of hsi.notetype: notetypenum NOT portable across envs, notecolor is BGR, bit 2 = redaction confirmed, 8 bits open; Hyland never publishes bit values
- [No Loose Scripts — Use Ops Tab](feedback_no_loose_scripts_ops_tab.md) — never hand over `python foo.py` CLI one-liners for ops actions; build them as controls in the BU Hive Ops tab
- [BU Hive](project_bu_hive.md) — BU Hive v0.2.0 control plane (FastAPI 127.0.0.1:8730, auth + Discussion/Members + CogniBase Workbench + Docs-health page, vendored Bootstrap + custom hive theme, manual start) + capture hooks live; runtime C:\AI\BU Hive is AUTHORITATIVE (build kit claude-env-setup\scripts\bu-hive has DIVERGED behind it)

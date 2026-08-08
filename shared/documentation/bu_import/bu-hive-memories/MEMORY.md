# Memory index

- [BU Hive governance workflow](bu-hive-governance-workflow.md) — proceed on low-risk; route risky/unclear tasks to the /approvals board; never deploy or activate until BU approves.
- [BU Hive is single-user](bu-hive-single-user-scope.md) — Renne is the only user and is admin of the tool and the laptop; skip approvals/security ceremony for local-only changes.
- [Voice architecture](voice-architecture.md) — shared ClaudeVoice HTTP service (:8735) reused by BU Hive (/api/voice/* proxy) and a global Claude Code Stop hook that speaks replies.
- [BU Hive MCP → Desktop](bu-hive-mcp-desktop.md) — stdio MCP server (scripts/bu_hive_mcp.py) exposes the registry to Claude Desktop; Desktop keeps wiping `mcpServers`, so each product re-registers itself with its own script.
- [MapSnap can query OnBase TEST/DEV](mapsnap-onbase-query-capability.md) — MCP gateway on :8651 reaches live OnBase config; check it before claiming no OnBase access.
- [Verify BU Hive without a password](bu-hive-verify-without-password.md) — mint a session token server-side to test gated pages; always restart explicitly and re-check the live port.

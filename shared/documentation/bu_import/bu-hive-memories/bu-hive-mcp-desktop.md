---
name: bu-hive-mcp-desktop
description: BU Hive exposes its project registry to Claude Desktop/Code via a zero-dep stdio MCP server; Desktop config also carries MapSnap MCP.
metadata: 
  node_type: memory
  type: project
  originSessionId: 68cb6f84-f2ca-4172-84c2-e7a809e6fd03
  modified: 2026-08-03T23:42:02.179Z
---

BU Hive surfaces its registry (data/bu_registry.json — 5 projects) to Claude Desktop over MCP via a zero-dependency **stdio** server at `C:/AI/BU Hive/scripts/bu_hive_mcp.py` (launched by the venv python). Tools: `bu_hive_projects`, `bu_hive_project`, `bu_hive_data_sources`, `bu_hive_health` (loopback TCP liveness only). Read-only, no network egress, reuses `app.registry`. Chosen over an in-FastAPI HTTP endpoint to avoid touching the governed web app's CSRF/auth middleware.

Registered in `%APPDATA%/Claude/claude_desktop_config.json` under `mcpServers` alongside `MapSnap` (mcp-remote → http://127.0.0.1:8651/c/<path-token>/mcp). That file is Epitaxy-mode preferences + mcpServers; the sidebar folder list is NOT config-editable (manual "Open folder" only). Timestamped backups sit next to it.

**Claude Desktop keeps deleting the whole `mcpServers` block — expect it to recur.** Desktop owns this file and rewrites it from its own in-memory model whenever it saves a preference; that serialization keeps only the keys it knows (`coworkUserFilesPath`, `preferences`) and silently drops everything else. Observed rewrites that wiped both entries: 2026-08-01 21:55, 2026-08-02 13:04, 2026-08-03 16:23. Symptom: MapSnap and/or BUHive vanish from Settings → Connectors. **Diagnose** by checking `mcpServers` in that JSON and, for what Desktop actually loaded, `%APPDATA%/Claude/logs/main.log` → `[replaceRemoteMcpServers] Calling SDK with N total servers`. Beware two false positives in that log: `bu-hive` on port 8730 is a *launch.json preview server*, not MCP, and `C:\APPS\MapSnap` in `preferences` is only a trusted-folder path.

**Each product re-registers itself — never one combined script** (rennesan does not want MapSnap and BU Hive mingling):
- BU Hive → `scripts/setup_desktop_connector.ps1` (stdio; `-Name BUHive`, `-Remove`) — created 2026-08-03.
- MapSnap → `C:/APPS/MapSnap/kit/setup_desktop_connector.ps1` (needs gateway `auth.mode` = `capability` or `both`, plus npx).

Both back up first, preserve unrelated keys, write UTF-8 **without** BOM, and verify by re-reading. Desktop must be fully quit and reopened afterwards — **which also kills any Claude Code session running inside Desktop, so never restart it mid-session; hand that step to the user.**

**Task Scheduler is NOT available for this: `Register-ScheduledTask` fails with Access denied (HRESULT 0x80070005) at every TaskPath**, root and subfolders alike — `AD\rennesan` is non-elevated on a GPO-managed BU machine. (A root task `Claude Voice (daily 8AM)` does exist, so elevated creation has happened before; `-Persist` works from an elevated shell.) The admin-free route that works: **`scripts/setup_desktop_connector.ps1 -PersistStartup`** drops a shortcut in the Startup folder (writable) launching `connector_watch.ps1` via `Watch-Connector-Hidden.vbs` — hidden, single-instance via a `Global\BUHiveConnectorWatch` mutex, re-checking every 5 min. Remove with `-UnpersistStartup`. This covers the real window, since Desktop only wipes while logged in.

**A self-heal loop REQUIRES the registration script to be idempotent** — write nothing when the entry is already correct. BU Hive's is; **MapSnap's kit script is not** (it backs up and rewrites every run), so looping it unmodified would produce ~288 backup files/day. That is why MapSnap's fix is gated behind approvals item **#18** rather than just scheduled. Also note a SessionStart hook CANNOT fix this — Desktop reads the config at *its own* launch, before any Claude Code session exists.

A `SessionStart` hook in `.claude/settings.local.json` (project-scoped) injects the environment digest via `scripts/session_digest.py --hook`; bare stdout is not reliably injected, the `hookSpecificOutput.additionalContext` envelope is. Use the schema's `args` exec form for Windows exe paths — a quoted path in `command` breaks under PowerShell.

Also created 5 **claude.ai cloud Projects** (all Private, org BU) — one per registry entry, named "BU Hive — <name>", each with a description + custom instructions carrying the governance rule: Claude Voice, CogniBase, Control Plane, OnBase API Client, MapSnap (BU Edition). Sidebar folders are still manual "Open folder" (CogniBase + onbase-client were the two not yet pinned).

**Why:** answered "populate Claude Desktop with BU Hive projects." **How to apply:** edit this JSON only via a script FILE (never a bash heredoc — heredoc collapses `\\`→`\`, turning Windows paths' `\n`/`\b` into control chars); prefer forward-slash paths. Relates to [[bu-hive-governance-workflow]] and [[voice-architecture]].

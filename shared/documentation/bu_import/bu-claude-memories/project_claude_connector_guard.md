---
name: project-claude-connector-guard
description: Claude Desktop drops the mcpServers block on every save; C:\AI\tools\ClaudeConnectorGuard is the manifest-driven guard that restores BUHive + MapSnap. Desktop is MSIX-packaged, so the config lives at the LocalCache physical path, NOT %APPDATA%\Claude
metadata: 
  node_type: memory
  type: project
  originSessionId: 286c2d96-3158-4452-a051-e5714448e806
  modified: 2026-08-06T20:19:34.184Z
---

Claude Desktop (1.24012.9) rewrites its `claude_desktop_config.json` from its own
in-memory model every ~20 min of active use and **silently drops the entire
`mcpServers` block**. Local MCP connectors therefore need a repeating re-register;
writing the config once is never a fix. Claude Code's `~/.claude.json` and
account-level cloud connectors are unaffected — only local `mcpServers` entries.

The authoritative tool is **`C:\AI\tools\ClaudeConnectorGuard`** (`Install.bat` =
one-run install; `Install-ClaudeConnectors.ps1 -Status` = health). It is
manifest-driven via `connectors.json` and covers BUHive **and** MapSnap together.
Adding a connector = editing that JSON; `{file:<path>}` args are expanded at
register time so tokens/capability URLs stay in one place on disk. Entries in the
live config that are NOT in the manifest are left strictly alone.

It **supersedes** BU Hive's `scripts\setup_desktop_connector.ps1` +
`connector_watch.ps1`, now legacy — don't reach for them first. They lost MapSnap
because they were hardcoded to `-Name BUHive`. The legacy Startup shortcut is gone
(the guard's installer removes it); persistence is now the **Scheduled Task
"Claude Connector Guard"** (every 5 min, as the interactive user, RunLevel Limited),
installed 2026-08-05 17:45.

**CRITICAL — where the config actually lives (root cause of a 2-day outage).**
Claude Desktop is an **MSIX-packaged app** (`Claude_pzs8sxrjxfjjc`, packaged since
2026-06-18). So `%APPDATA%\Claude` is a package-**virtualized view**, not a real
directory. That view resolves for a non-elevated, session-attached shell but
**NOT for a Scheduled Task and NOT for an elevated shell** — in those contexts
both `Test-Path` and `[IO.Directory]::Exists` return false, so the guard's
pre-flight declared the folder unreachable and `exit 2`'d on **275 consecutive
cycles** (2026-08-05 17:45 → 2026-08-06 16:14) while the same path opened fine by
hand. The physical backing store is:

    C:\Users\<you>\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json

Byte-identical to the virtualized view (same SHA-256 and mtime, verified
2026-08-06) and readable from **every** context. Fixed 2026-08-06 by
`Get-ClaudeConfigPath` in `Install-ClaudeConnectors.ps1`, which globs
`AppData\Local\Packages\Claude_*\LocalCache\Roaming\Claude` first and falls back
to the classic location for a non-packaged install. Verified end-to-end: BUHive
deleted from the live config → task triggered → `RESTORED BUHive` logged,
MapSnap and `coworkUserFilesPath`/`preferences` untouched, `LastTaskResult 0`.
**Any future tool that touches Desktop's config must use the physical path** —
`%APPDATA%\Claude` will silently fail from a task or an elevated context.

**Why persistence was fragile:** on this GPO-managed BU laptop, Task Scheduler
registration is denied to non-elevated users (HRESULT 0x80070005), so the strong
form needs elevation and the admin-free fallback (Startup-shortcut watcher) is
inherently unsupervised — one died 2026-08-03 without a trace.

**Accepted exception (do not "fix"):** MapSnap's `mcp_gateway.json` sets
`tools.table_data: true`, overriding both the shipped template and the gateway
code default (`on('table_data', default=False)`). So `mapsnap_table_data` CAN
return real row values over MCP. This is deliberate — confirmed by the user
2026-08-05: loopback-only gateway, single developer workstation, dev/test
profiles. Rationale is recorded in the config's `_doc`. Don't flag it as a
finding again or offer to disable it; revisit only if the gateway binds beyond
loopback, gains a second consumer, or a production profile is added.

**How to apply:** if a connector disappears from Desktop's Connectors list, run
`-Status` first — it distinguishes "entry missing" from "gateway down" from
"persistence not installed", and prints the config path it resolved (check that
it is the LocalCache one). `logs\guard.log` is the liveness signal, **not**
`logs\heartbeat.txt` — heartbeat is only written by the watcher fallback, so it
is permanently stale under Scheduled-Task persistence. Restarting Claude Desktop
is always required for a restored entry to take effect. Related:
[[project-bu-hive]], [[project-directory-policy]].

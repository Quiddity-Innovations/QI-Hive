# QI Hive — MCP Connector Audit
**BU Laptop vs. Home Machine · OnBase 13 Query Path · 2026-08-06**

> Audit was report-only: no configuration was changed. All statements verified against live configs, the BU reverse-sync reports (Downloads\home-sync\reports\MCP-PLAN.md), and open ports on 2026-08-06.

## TL;DR
The BU laptop and the home machine differ by deliberate architecture, not drift. BU has two locally registered Desktop connectors (BUHive + MapSnap) because it had no other option. Home routes everything through the QI Connector remote MCP — one front door carrying QI Hive AND MapSnap tools — so separate connectors were never created here on purpose. `rennesan/mapsnap` is the private GitHub repo, not an MCP connector.

## 1. What exists where
| Surface | BU Laptop | Home Machine (this PC) |
|---|---|---|
| Claude Desktop local MCP | BUHive + MapSnap (stdio entries in claude_desktop_config.json, kept alive by ConnectorGuard watcher) | qi-registry only — added 2026-08-06 20:24 (C:\QIH\engine\mcp\qi_registry_mcp.py; ConnectorGuard rebuilt at C:\QIH\engine\tools\ConnectorGuard; pre-change backup taken) |
| claude.ai remote connector | None | QI Connector (connector.quiddityinnovations.com -> :9030) serving qi_*, maia_*, naya_*, nexus_* AND mapsnap_* tools — verified live |
| Claude Code CLI (.claude.json) | None | claude-peers, git, qi-brain, mapsnap (HTTP 127.0.0.1:8651, bearer service token), qi-registry |
| Live ports (verified) | n/a | :9030 Connector OPEN · :8651 MapSnap gateway OPEN |

## 2. Why it was done differently
### 2.1 Home had a front door BU couldn't have
The QI Connector (built 2026-07-30) exists precisely so one connector replaces per-machine MCP config: any Claude surface (claude.ai web, mobile, Desktop, Code) gets QI tools without local registration. MapSnap was wired into it as an adapter rather than a second connector — one front door, one auth story. On the BU laptop there is no QI tunnel and BU Hive data is work-internal, so the only pattern available there was local stdio servers registered directly into Claude Desktop — hence two separate entries.

### 2.2 The BU entries were deliberately NOT imported home
MCP-PLAN.md (BU reverse-sync audit, 2026-08-06) quarantines the work connectors.json entries (BUHive, MapSnap), the ConnectorGuard backups (they embed a live capability URL), and bu_hive_mcp.py itself (work product built on employer time). A 'BU HIVE' connector will never appear at home — that is correct, not missing.

### 2.3 The plan minimizes local registrations on purpose
Every local Desktop entry is another thing the guard must protect (the Desktop-drops-mcpServers failure mode from the work box). Net-new local entry: exactly one — qi-registry — chosen because it reads qi_registry.json straight from disk and keeps answering when Brain, Dashboard, and tunnel are all down.

## 3. Impact on experience, system, and usage
- **Capability parity, different packaging** — On the BU laptop tools show as two connector names. At home the same MapSnap tools appear inside the QI Connector (claude.ai/Desktop/mobile) and as server 'mapsnap' in Claude Code. Nothing is missing.
- **One intentional tool difference** — The cloud path (Connector) deliberately omits mapsnap_table_data — the egress guardrail, so raw table rows never transit the tunnel. The local Claude Code entry includes table_data because it stays on 127.0.0.1.
- **Resilience improved 2026-08-06** — The Connector path depends on the service + tunnel being up; qi-registry (stdio, stdlib-only, reads the JSON from disk) works fully offline and is now guarded by the rebuilt ConnectorGuard.
- **Security posture stronger at home than at BU** — Capability URL treated as a password (rotation procedure in place); nothing secret imported from D:\; guard backups/logs gitignored because the QI-Hive repo is public.
- **Maintenance burden** — One remote connector + one guarded local entry, versus BU's two guarded local entries.

## 4. OnBase 13 query path (added same session)
- Claude never opens a SQL connection to the VM. Every query goes: MCP tool -> MapSnap MCP gateway (QI_MapSnapMCP, 127.0.0.1:8651) -> MapSnap API (127.0.0.1:9876, service-token auth). The claude.ai path is identical via the QI Connector, with table_data blocked by the egress guardrail.
- MapSnap holds the live connection. The ONBASE13_POC profile ('OnBase 13 (Live POC)') points at SQL Server 192.168.251.128:1433, database Nautilus, schema hsi, plus AppServer/Unity URLs on the same VM. Data Chat NL->SQL and table-data requests run live SQL through that stored connection.
- Schema browsing and maps are served from the schema.json snapshot in the working folder — no VM round-trip.
- Separation is deliberate: MapSnap holds the credentials and enforces the per-tool allowlist; anything talking to Claude only ever sees MapSnap's API.

**Bottom line:** queries to OnBase 13 happen via MapSnap, and MapSnap is the component connecting directly to the VM.

## 5. Findings register
| # | Finding | Detail |
|---|---|---|
| F1 | rennesan/mapsnap is NOT an MCP connector | It is the private GitHub repository for MapSnap (github.com/rennesan/mapsnap). The owner/repo format is the giveaway: it is the GitHub integration listing the repo. It grants Claude access to the repo's code only — it does not expose MapSnap's database tools. No Claude Code plugin by that name exists locally (only the official Anthropic marketplace is installed). |
| F2 | Plaintext sa password in ONBASE13_POC connection profile | C:\MapSnap\Product\ONBASE13_POC\.mapsnap_conn.json embeds the sa password in plaintext inside the dsn string (in addition to the structured fields). Local, gitignored, POC VM — low risk — but remember it is there if the folder is ever zipped or shared. Value intentionally not reproduced in this document. |
| F3 | MapSnap service bearer token in .claude.json | C:\Users\renne\.claude.json stores the MapSnap bearer service token in plaintext. Normal placement for MCP config, scoped to localhost only, revocable via the service_tokens.json hot-reload kill-switch. |
| F4 | Unpushed commits on CLAUDE-MANAGER master | At audit time, master was ahead of origin by 5 commits with a heavily modified working tree belonging to other workstreams. Left untouched — push is Renne's call. |

## 6. Open decisions (Renne)
- [ ] Optionally rename how the QI Connector presents on claude.ai so it is obvious it bundles Hive + MapSnap tools.
- [ ] Confirm where exactly 'rennesan/mapsnap' appeared (if under Settings -> Connectors on claude.ai, investigate further).
- [ ] Decide when to push the 5 unpushed commits on CLAUDE-MANAGER master.

---
*Generated 2026-08-06 by Claude (Fable 5) from session audit. Memory record: project_mcp_connector_audit_2026_08_06.md.*
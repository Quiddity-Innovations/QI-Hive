# QI Connector — Custom Claude Connector Guide

**Created:** 2026-07-30 · **Project:** [C:\QIP\Connector](C:\QIP\Connector) · **Status:** LIVE

## What it is

A **remote MCP server** ("custom connector") that gives Claude — on **claude.ai web, the mobile app, Claude Desktop and Claude Code** — live tools into the QI ecosystem, replacing per-machine, per-tool MCP configuration. A connector and a remote MCP server are the same thing: MCP over **Streamable HTTP** at a public HTTPS URL.

```
Claude (any surface) ──HTTPS──▶ connector.quiddityinnovations.com (Cloudflare named tunnel qi-connector)
                                        │
                                  QI_ConnectorTunnel (NSSM)
                                        ▼
                              127.0.0.1:9030  QI_ConnectorMCP (NSSM)
                              FastAPI + FastMCP (mcp SDK, Streamable HTTP, stateless)
                                        │
                    ┌───────────────────┼──────────────────────┐
                    ▼                   ▼                      ▼
          QI Brain API :9011   qi_registry.json      sc query / :port/health probes
```

## How to connect (Renne does this once per surface)

### claude.ai / Claude mobile / Claude Desktop
1. Open **Settings → Connectors → Add custom connector**.
2. Paste the **capability URL** from [C:\QIP\Connector\secrets\CONNECTOR_URLS.txt](C:\QIP\Connector\secrets\CONNECTOR_URLS.txt) (the `/c/<path-token>/mcp` form — the secret lives in the URL, so no headers/OAuth are needed).
3. Add — the 7 `qi_*` tools appear in the tools menu of every new chat.

### Claude Code (any machine)
```bash
claude mcp add --transport http qi-connector https://connector.quiddityinnovations.com/mcp --header "Authorization=Bearer <token from connector_token.txt>"
```
(On this machine the local stdio `qi-brain` MCP already covers most of this — the remote connector matters for *other* machines and non-Code surfaces.)

## Tools exposed

| Tool | Backing source |
|---|---|
| `qi_ecosystem_snapshot` | Brain `GET /api/ecosystem_snapshot` (falls back to registry if Brain is down) |
| `qi_search_memory(query, collection, n, project_id)` | Brain `POST /api/search_memory` — collections: `decisions`, `features`, `sessions`, `docs` (Documentation Brain, ~940 docs) |
| `qi_get_context(project_id)` | Brain `POST /api/context` |
| `qi_log_decision(project_id, title, rationale, …)` | Brain `POST /api/log_decision` (writes as agent `qi_connector`) |
| `qi_registry_lookup(project_id?)` | [C:\QIH\ecosystem\qi_registry.json](C:\QIH\ecosystem\qi_registry.json) read live |
| `qi_service_status()` | `sc query` on every registered `QI_*` service + parallel `GET /health` probes |
| `qi_headlines(project_id?, since?, limit?)` | Brain `GET /api/headlines` — ecosystem activity feed (added 2026-07-30) |
| `qi_dispatches(status?, limit?)` | Brain `GET /api/dispatches` — Hive dispatch queue, read-only (added 2026-07-30) |
| `qi_public_urls()` | Registry `static_tunnels.map` |

## Security model

- Server binds **127.0.0.1:9030** — only the tunnel reaches it.
- `/mcp` requires `Authorization: Bearer <token>`; wrong/missing token → 401.
- `/c/<path-token>/mcp` is a **capability URL** for clients that can't send custom headers (claude.ai custom connector UI). Treat the URL itself as a secret.
- `/health`, `/version`, `/info` are open (QI module interface contract; no secrets in responses).
- Tokens: [C:\QIP\Connector\secrets\](C:\QIP\Connector\secrets\) — `connector_token.txt` (bearer), `connector_path_token.txt` (URL), `CONNECTOR_URLS.txt` (ready to paste). All gitignored.
- **Rotate a token:** delete its file → `nssm restart QI_ConnectorMCP` (new token auto-generates) → update the Claude client. Rotate immediately if a URL leaks (e.g. pasted in a screenshot).
- MCP transport DNS-rebinding host check is disabled deliberately (public Host headers arrive via the tunnel); auth is the bearer/capability token, not the Host header.

## Operations

| Item | Value |
|---|---|
| Services | `QI_ConnectorMCP` (auto-start, `C:\1-AI\APPS\PYTHON\python.exe C:\QIP\Connector\api\main.py`), `QI_ConnectorTunnel` (cloudflared named tunnel `qi-connector`) |
| App log | [C:\QIP\Connector\data\logs\connector.log](C:\QIP\Connector\data\logs\connector.log) |
| Service logs | `data\logs\service_stdout.log` / `service_stderr.log` |
| Tunnel config | [C:\QIH\engine\tunnels\configs\qi-connector.yml](C:\QIH\engine\tunnels\configs\qi-connector.yml) (tunnel id d14a9bad…) |
| Restart (non-admin) | via QI_Elevate broker: `run_elevated("nssm", ["restart", "QI_ConnectorMCP"])` |
| Smoke test | `python C:\QIP\Connector\tools\smoke_test.py [https://connector.quiddityinnovations.com]` |

**Troubleshooting:** public URL dead → check `QI_ConnectorTunnel` then `QI_ConnectorMCP` (`sc query`), then `service_stderr.log`. 401 with correct token → token file was regenerated (service restarted after file deletion); re-copy from secrets. Brain-backed tools returning `Brain API unreachable` → `QI_BrainAPI` (:9011) is down; registry tools keep working.

## Adding new tools later

Add a `@mcp.tool()` function in [C:\QIP\Connector\api\main.py](C:\QIP\Connector\api\main.py) (docstring = tool description shown to Claude), restart `QI_ConnectorMCP`. Keep results under ~20k chars (`_clip`) — claude.ai truncates large tool results. Update the registry `exposes_to_ecosystem` list + this guide.

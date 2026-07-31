# QI MCP Gateway — Ecosystem Standard

**Established:** 2026-07-30 · **Module:** [C:\QIH\engine\common\qi_mcp_gateway.py](C:\QIH\engine\common\qi_mcp_gateway.py) · **Status:** Renne's standing directive — *every QI app with AI capability gets MCP access as a CONFIGURATION item, never a hardcoded upgrade.*

## What it is

One reusable module that turns any QI app's HTTP API into MCP tools for Claude. Two consumption modes, both config-driven:

1. **Adapter in the QI Connector** (personal use, all Claude surfaces): add a section to `C:\QIP\Connector\config\connector.json` named after the adapter, `"enabled": true` → tools appear on Renne's claude.ai account. Restart `QI_ConnectorMCP`.
2. **Standalone gateway service** (shipped/LAN deployments): a `config\mcp_gateway.json` in the app's folder + a tiny launcher in `C:\QIH\engine\launchers\` + an NSSM service `QI_<App>MCP` (installable via QI_Elevate broker — launcher lives under C:\QIH which the whitelist allows).

## Config contract (per app)

```json
{ "enabled": true, "name": "<App> MCP", "project_id": "<id>", "adapter": "<id>",
  "target_base": "http://127.0.0.1:<app-port>",
  "target_bearer_file": "<path to app service token, if the app has auth>",
  "bind": "127.0.0.1", "port": <from the app's registry block>,
  "auth": {"mode": "both", "secrets_dir": "<app>\\config\\secrets"},
  "tools": {"<tool>": true, "...": false},
  "generic_tools": [ {"name": "...", "method": "GET", "path": "/api/...", "description": "..."} ] }
```

Rules (Six-Laws aligned):
- **Port from the app's own registry block** — register in qi_registry.json BEFORE installing.
- **Loopback bind by default**; LAN bind is a per-deployment config choice; public exposure only via the QI Connector, never by tunneling a gateway port.
- **Data-returning tools (rows, documents, messages) default OFF** — enable per deployment where egress policy allows.
- **App-side auth**: if the app has logins, add service tokens (see MapSnap's `service_tokens.json` + `auth.service_token_from_header` pattern) — never bypass or hardcode credentials.
- **Graceful fallback**: gateway must not take the app down; tools must degrade with error strings.

## How to onboard the next app (checklist)

1. Write (or reuse) an adapter in `qi_mcp_gateway.py` — or use `generic_tools` if plain JSON endpoints suffice.
2. Registry: add `ports.mcp` + `QI_<App>MCP` service entry.
3. App auth: service token support if the app gates its API.
4. `config\mcp_gateway.json` + launcher + NSSM install via broker + smoke test (initialize/tools-list/one call).
5. Optional Phase 1: add the section to connector.json for claude.ai access.
6. Docs: app-level MCP guide + QI_Service_Registry.md entry.

## Adopters

| App | Adapter | Phase 1 (connector) | Phase 2 (gateway) | Notes |
|---|---|---|---|---|
| MapSnap | `mapsnap` | ✅ live 2026-07-30 | ✅ `QI_MapSnapMCP` :8651 | First adopter; service-token feature added to MapSnap auth |
| QI Brain/Hive | (native in connector core) | ✅ | n/a | qi_* core tools |
| NEXUS / AutoPDF / Gamez / TubeScout / CogniBase / Claude Voice / Maia | — | planned | planned | roll out per checklist above |
| OpenClaw / Hermes | — | investigate first | investigate first | check NATIVE MCP support before building (OpenClaw framework likely ships MCP; gateway only if missing). OC is non-HTTP TCP in WSL — special case |

## UI integration pattern (optional, added 2026-07-31)

Apps with a Settings UI SHOULD surface the gateway config as a panel (MapSnap reference implementation: **Settings → AI Connections & Features → Claude / MCP Access**): admin-gated `GET/POST /api/mcp/config` endpoints that read/write the SAME `mcp_gateway.json` + `service_tokens.json` files (file editing stays valid as plan B), expose only name/role/enabled for service accounts (never token values), show live gateway health, and offer Save vs Save & Apply (service restart). Renne's rule: **UI-configurable everywhere a UI exists; files remain the universal fallback.**

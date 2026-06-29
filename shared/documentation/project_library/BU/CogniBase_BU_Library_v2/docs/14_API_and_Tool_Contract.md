# CogniBase — API & Tool Contract: REST + MCP

*Document 14 of 18 · BU-Aligned Library v2 · Renne Santiago*

---

## 1. Two faces, one engine

CogniBase exposes the same governed engine through two contracts: a **REST API** (for the UI, reports, and data-plane integration) and an **MCP tool surface** (for Nexus/Regent agents). Both pass through the access model and audit trail — there is no ungoverned back door.

## 2. REST surface (representative)

| Method · Path | Purpose |
|---|---|
| `POST /schema/extract` | Extract schema from a live connection |
| `POST /metadata/import-expk` | Ingest OnBase `.expk` configuration |
| `POST /query` | RAG answer (grounded, cited) |
| `POST /federate` | Run a Federation Plan (sanctioned join) |
| `GET /anchors` / `POST /anchors/refresh` | Inspect / refresh hygiene anchors |
| `POST /reports/generate` | Templated or ad-hoc report + audit folder |
| `GET /health` · `GET /version` · `GET /info` | Ops/JSON (standard health endpoints) |

Responses stream via **SSE** (`content_delta`, `tool_call_start`, `tool_result`, `auth_required`, `done`) — matching Nexus's event contract.

## 3. MCP tool surface

`cognibase.search` · `cognibase.ask` · `cognibase.schema_explain` · `cognibase.federated_query` · `cognibase.list_doctypes` (Document 11). Each tool description is admin-managed and visibility-gated; the same Gate/Privacy-Transformer pipeline runs before any tool result returns.

## 4. Authentication & config

- **Auth:** Entra ID (MSAL PKCE) for users; APISIX consumer keys for widget/agent deployments; OnBase OAuth passthrough for source access.
- **Config API:** ETag-cached config (agents/deployments/models/tool-endpoints) the agent backend polls — no restart on change, mirroring Nexus's admin-config pattern.
- **Smart auth:** a synthetic tool lets the model request identity only when a question needs it.

## 5. Contract stability

The OnBase REST shapes are pinned to API version 1; field anomalies are documented in coordination with BU's REST POC team (Document 16). The MCP contract follows the published MCP spec, so BU's gateway treats CogniBase like any registered tool server.

> The contract is deliberately boring and standard — REST + SSE + MCP — because predictability is what makes a component safe to adopt and safe to leave.

---
*Document 14 of 18 · Frame A · CogniBase BU-Aligned Library v2 · generated 2026-06-28*

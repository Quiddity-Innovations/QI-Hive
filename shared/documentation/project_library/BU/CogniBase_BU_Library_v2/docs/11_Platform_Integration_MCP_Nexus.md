# CogniBase — Platform Integration: MCP & Nexus

*Document 11 of 18 · BU-Aligned Library v2 · Renne Santiago*

---

## 1. The change from the original design

The original library described integration via a **LibreChat gateway**. BU's platform has since standardized on **MCP (Model Context Protocol) as the architectural spine** — Nexus exposes an `mcp-gateway-registry` and a `Nexus MCP Control Plane` that route agent tool-calls. This document supersedes the LibreChat approach: **CogniBase integrates as an MCP server.** (LibreChat/OpenAI-compatible chat remains available for *local desktop* use only — Document 12.)

## 2. The integration, concretely

CogniBase exposes its capabilities as **MCP tools** and **registers in BU's `mcp-gateway-registry`**. A Nexus or Regent agent then calls them like any other Atlas tool — no bespoke connector:

| MCP tool | Backed by | Returns |
|---|---|---|
| `cognibase.search` | RAG retriever | gate-filtered passages + citations |
| `cognibase.ask` | RAG query engine | synthesized, cited answer |
| `cognibase.schema_explain` | config corpus | plain-English schema/DocType explanation |
| `cognibase.federated_query` | Query Federator | sanctioned cross-source result (Document 8) |
| `cognibase.list_doctypes` | schema/.expk | DocType inventory |

A runnable scaffold exists (`C:\CogniBase\proposals\mcp_server.py`) wrapping the live retriever/query-engine/router.

## 3. Where it runs (two-VPC)

- **AI Engineering VPC (lead):** the MCP server sits beside Nexus; the Control Plane routes to it; identity via **Entra ID**, transport behind **APISIX**, policy via **OPA**.
- **Data Engineering VPC (Phase 2):** optionally also expose an "OnBase API" behind APISIX as a peer of Person/Course API, for data-plane analytics and lake emit.

## 4. Why MCP-first is the right call

- **Native:** it is the exact interface BU's agents already speak — zero integration tax.
- **Governed:** tool calls inherit APISIX auth, OPA policy, and the audit trail.
- **Reversible:** an MCP tool is a thin, replaceable surface — it honors "freedom to leave."
- **Portable (Plan B):** the same MCP server works for any MCP-capable host, so the integration investment survives even if BU does not.

## 5. Streaming & UX parity

CogniBase supports token-by-token streaming, source-citation chips, and "searched N sources" transparency — matching the Nexus channel experience, so a CogniBase-backed assistant feels native inside BU's widget/Teams/Slack surfaces.

> Integration is not a bridge bolted onto BU's platform — it is CogniBase **speaking BU's own protocol**, registered in BU's own registry, governed by BU's own policy engine.

---
*Document 11 of 18 · Frame A · CogniBase BU-Aligned Library v2 · generated 2026-06-28*

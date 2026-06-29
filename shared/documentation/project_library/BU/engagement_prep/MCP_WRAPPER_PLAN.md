# CogniBase MCP Wrapper — Implementation Plan

**Status:** Proposal — 2026-06-27
**Owner:** Renne / Quiddity Innovations
**Why:** BU's Nexus/Regent agents call data **only** through MCP tools. An MCP face on CogniBase makes it a native citizen of BU's Atlas platform with zero bespoke integration. This is the highest-leverage item in the BU fit assessment (`C:\QIH\shared\documentation\project_library\BU\`).

---

## 1. Goal

Expose CogniBase's existing retrieval + RAG + (later) Query Federator as **MCP tools**, so any MCP client — BU's Nexus agent backend, Regent headless workflows, Claude Desktop, or the QI Hive — can call CogniBase without touching its internal HTTP API.

## 2. What already exists (reuse, don't rebuild)

| Capability | Module | Entrypoint |
|---|---|---|
| Semantic search (vector) | `Application/rag/retriever.py` | `RagRetriever.search(query, top_k, filters)` |
| Cited RAG answer | `Application/rag/query_engine.py` | `QueryEngine.answer(question, vendor, top_k)` |
| Pluggable LLM vendors | `Application/vendors/router.py` | `VendorRouter` (claude/openai/gemini/ollama/openai_compatible) |
| Three corpora | retriever `collection_name` | `cognibase_main` / `cognibase_config` / `doc_corpus` |
| Gates + Privacy Transformer | access model layers 4–5 | applied in the source/retriever layer before egress |

The MCP server is a **thin adapter** over these — see `proposals/mcp_server.py`.

## 3. Tool surface (v1)

| MCP tool | Maps to | Returns |
|---|---|---|
| `cognibase.search(query, top_k, filters)` | `RagRetriever.search` | passages: id, text, score, metadata |
| `cognibase.ask(question, vendor, top_k)` | `QueryEngine.answer` | answer + citations + vendor/token metadata |
| `cognibase.schema_explain(entity, top_k)` | RAG over `cognibase_config` | plain-English schema/DocType explanation |
| `cognibase.federated_query(logical_query, group)` *(v2)* | Query Federator + Gate | cross-DocType result joined on Normalizers |
| `cognibase.list_doctypes()` *(v2)* | schema.json / .expk | DocType inventory |

## 4. Build steps

1. **Dependency:** `pip install "mcp[cli]"` (official Python MCP SDK / FastMCP). Add to `pyproject.toml` extras as `mcp`.
2. **Wire `_build_engine()`** in `mcp_server.py` to mirror `Application/server/app.py`: load `Settings/settings.json`, pick the active vendor, set the collection per corpus.
3. **Smoke test over stdio:** `python proposals/mcp_server.py`, connect with the MCP inspector or Claude Desktop, call `search` and `ask`.
4. **BU mode (env `BU_MODE=1`):**
   - Identity: validate Entra ID (MSAL PKCE) tokens; thread the user into Gate evaluation (per-user isolation).
   - Transport: switch from stdio to streamable-HTTP behind APISIX; register as an APISIX consumer.
   - Policy: express Gates as OPA-checkable policy; confirm Privacy Transformer runs before any tool result is returned.
5. **v2:** add `federated_query` (the real differentiator) once the Query Federator entrypoint is stable; add `list_doctypes`.
6. **Register** under QI conventions only when promoted out of `proposals/`: `QI_CogniBaseMCP` NSSM service, port from `qi_registry.json` block, description set.

## 5. Acceptance criteria

- An MCP client lists `search`, `ask`, `schema_explain` and gets cited answers.
- No regulated value leaves the process un-masked (Privacy Transformer verified in the path).
- Every tool call writes an L1–L4 audit record.
- Runs over stdio locally **and** streamable-HTTP for BU, no production-code changes required.

## 6. Effort

~1–2 days for v1 (search/ask/schema_explain over stdio). BU-mode identity + transport ~1 week. v2 federated_query depends on Query Federator readiness.

## 7. Out of scope (deliberately)

No service registration, no port binding, no production wiring until promoted from `proposals/`. This keeps the change reversible and internal.

# CogniBase — Components Overview

*Document 5 of 18 · BU-Aligned Library v2 · Renne Santiago*

---

## 1. What CogniBase delivers

**Unbound but anchored.** Cross-departmental analysis OnBase cannot do natively — with every claim citing its source and every cross-source correlation backed by a sanctioned relationship (Document 2). The component set below exists to make that promise operational and auditable.

## 2. Component catalog

| Layer | Component | Purpose | Status |
|---|---|---|---|
| **Channels** | Retrieval UI | OnBase-Web-Client-like document search/preview, no client install | Live |
| | Schema browser | Navigable HTML of tables/columns/keys/relationships | Live |
| | Reports | `.docx`-templated + ad-hoc RAG-driven generation | Designed (M1x) |
| | Assist chat | Contextual NL help on schema and retrieval | Live |
| **Agent** | RAG query engine | Retrieve → synthesize with citations | Live |
| | **Query Federator** | Decompose → sanctioned sub-queries → join on Normalizers | Designed (Doc 8) |
| | Numeric verifier | Re-executes every numeric claim before it ships | Designed (M32) |
| **Knowledge** | Ontology (Normalizers/CrossLinks) | Semantic equivalence + vetted joins | Core |
| | 3-corpus indexer | Operational / Configuration / Solution Documentation | Core |
| **Access** | 5-layer access model | Constraint→Normalizer→CrossLink→Gate→Privacy Transformer | Core |
| | Privacy Transformer | k-anonymity, masking, suppression before egress | Core |
| **Sources** | OnBase clients | Unity API + REST + `.expk` config parser | Live/partial |
| | Metadata collector | DocTypes, KeywordTypes, Lifecycles, dashboards | Live (M9) |
| **Platform** | LLM vendor router | Pluggable Claude/GPT/Gemini/local | Live |
| | **MCP server** | Tool surface for Nexus/Regent | Proposed (Doc 11) |
| | Scheduler | APScheduler-driven hygiene/refresh jobs | Stub→M34 |
| **Cross-cutting** | Provenance & audit | L1–L4 trail on every record/report | Core (Doc 10) |

### Review & learning components

- **Review queue** — confidence-gated items awaiting steward ratification.
- **Feedback & learning loop** — governed capture of corrections into sanctioned items (Document 17).
- **Review agents** — Inspector (consistency/policy) and Librarian (provenance/placement) for triage at scale.

## 3. Discovery toolkit (shared with MapSnap)

The schema-extraction, soft-FK inference, and enrichment pipeline run natively in **both CogniBase and MapSnap** — the same engine-agnostic discovery layer, pointed at OnBase here and at any enterprise database in MapSnap. This is the product-family backbone and a credibility signal: the OnBase domain layer is built on a proven, reused foundation.

## 4. What is BU-new vs. carried forward

- **Carried forward (proven):** schema map, soft-FK inference, three-corpus RAG, vendor router, Privacy Transformer, audit trail.
- **BU-aligned additions (this library):** MCP tool server (Nexus-native), pgvector index, Entra ID identity, OPA-expressed Gates, lake/Iceberg emit, observability (OTLP). See Documents 11–14.

> The catalog is intentionally small and sharp. CogniBase is not a platform trying to be everything — it is the **governed OnBase knowledge layer**, and every component earns its place against that single job.

---
*Document 5 of 18 · Frame A · CogniBase BU-Aligned Library v2 · generated 2026-06-28*

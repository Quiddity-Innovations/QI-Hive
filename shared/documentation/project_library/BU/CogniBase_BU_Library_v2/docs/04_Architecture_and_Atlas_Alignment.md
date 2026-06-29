# CogniBase — Architecture & Atlas Alignment

*Document 4 of 18 · BU-Aligned Library v2 · Renne Santiago*

---

## 1. Purpose

CogniBase is a local-first, vendor-neutral system that lets BU staff (1) **see** the full OnBase schema without SQL access, (2) **search and retrieve** OnBase documents through a familiar UI without an OnBase client, (3) **ask** natural-language questions across schema, metadata, and document text, and (4) **report** on dashboards, lifecycles, and document populations. This document shows its internal architecture and how each part lands as a native citizen of **Atlas**.

## 2. The layer cake

```
┌── Channels ──────────────────────────────────────────────┐
│  Retrieval UI · Schema browser · Reports · Assist chat    │
├── Agent / Orchestration ─────────────────────────────────┤
│  RAG query engine · Query Federator · Numeric verifier    │
├── Knowledge / Trust ─────────────────────────────────────┤
│  Ontology (Normalizers·CrossLinks) · 3-corpus index       │
├── Access / Governance ───────────────────────────────────┤
│  5-layer access model · Gates(→OPA) · Privacy Transformer │
├── Sources ───────────────────────────────────────────────┤
│  OnBase (Unity/REST/.expk) · SQL · institutional APIs     │
└── Provenance & Audit (cross-cutting, L1–L4) ─────────────┘
```

Every answer flows **bottom-up through the trust layer** before it reaches a channel — never source-to-channel directly. This mirrors BU's intelligence-stack rule (*agents never reach raw systems*).

## 3. Atlas alignment

| CogniBase layer | Atlas home | Mechanism |
|---|---|---|
| Agent / RAG / Federator | **Nexus** | Registered MCP tools; Nexus/Regent agents call them |
| Ontology / knowledge | **Lexicon** | Normalizers + sanctioned relationships feed BU's knowledge graph |
| 3-corpus index | **Cortex** (+ local) | Curated entities emit to Iceberg/pgvector; Trino-queryable |
| Access / Gates | **Forge / OPA** | Gates expressed as OPA policy; deny-by-default |
| Channels / API | **Lattice / APISIX** | FastAPI behind APISIX; Entra ID auth |
| Audit | **Forge audit sinks** | L1–L4 trail ships to BU's Vector/Loki sinks |

## 4. Two-VPC fit

BU separates a **Data Engineering VPC** (lake, Trino, OPA) from an **AI Engineering VPC** (Nexus, MCP, pgvector), joined only through APISIX over Nitro-encrypted peering. CogniBase fits both faces:
- **AI-plane (lead):** an MCP server in the `mcp-gateway-registry` — agents call CogniBase tools; lightest, native.
- **Data-plane (Phase 2):** an "OnBase API" behind APISIX, peer of Person/Course API, emitting curated entities to Cortex.

(Full integration mechanics in Document 11; deployment in Document 13.)

## 5. Deployment shape

Single-process FastAPI + uvicorn; ChromaDB→**pgvector** for the index; vendor-pluggable LLM router; plain-file artefacts per profile (`schema.json`, annotations, anchors, audit folders). Local-first for the desktop edition; container + Helm (ARM64) for the enterprise/BU edition — **one codebase, edition profiles** (Document 13).

## 6. Sync vs. cache strategy

OnBase is the system of record; CogniBase holds **derived, governed** representations. Configuration (`.expk`, schema) is **synced** on change; operational data is **anchored** through the hygiene pipeline with timestamps and multi-version retention (Document 9); document binaries are fetched **on demand** and never cached beyond policy. Freshness is surfaced to the user — staleness is shown, never hidden.

> CogniBase's architecture is deliberately **Atlas-shaped**: a governed knowledge layer over OnBase that plugs into Nexus, Cortex, Lexicon, and Forge through their own interfaces, not around them.

---
*Document 4 of 18 · Frame A · CogniBase BU-Aligned Library v2 · generated 2026-06-28*

# CogniBase — OnBase-aware AI knowledge platform

*The source of your unbound data stream.*

## What is CogniBase?

CogniBase is a local desktop platform that connects to **Hyland OnBase**, lifts its data into a
local vector store and a small data lake, and lets AI correlate, infer, and report across boundaries
OnBase itself cannot query. It is **vendor-neutral** — Claude, OpenAI, Gemini, Ollama, LM Studio, and
llama.cpp are all selectable LLM backends with zero hardcoded model names — and **source-pluggable**:
the first connector is OnBase, with filesystem, email, and Jenzabar planned next.

CogniBase is the productized descendant of **MapSnap** (a passive Jenzabar EX schema browser). It shares
the schema/browser DNA but aims far beyond a mirror: where OnBase shows one silo at a time, CogniBase
un-silos the data and reasons over it. Its first real-world target is **Boston University**, whose OnBase
deployment uses a three-letter-prefix silo pattern (`ADM_`, `HR_`, `FIN_`, `IST_`, …) that CogniBase is
designed to bridge.

## The Problem We Solve

- OnBase data lives in **department silos** — the same conceptual field (a student ID, a vendor) is
  named differently in each, and OnBase has no way to query across them.
- Answering a cross-silo question ("show pending AP invoices over a threshold, by vendor") today means
  manual exports, spreadsheets, and tribal knowledge.
- Self-service BI tools (Tableau, Power BI) let anyone write any query — there is **no anchor on what the
  question is allowed to touch**, and no built-in provenance of how a number was produced.
- Letting an LLM roam freely over institutional data invites hallucination and uncontrolled data exposure.

## Our Approach

CogniBase is built around four ideas that keep AI **constrained, auditable, and safe**:

- **Anchors** — a user-defined slice of source data that materializes into the local lake (raw JSONL →
  vector index). Every agent query is scoped to its anchors; it cannot read outside them.
- **Bridges** — declared cross-silo equivalences that un-silo the BU prefix pattern, so a query can UNION
  the "same" field across departments.
- **Admin-Authored Capabilities** — an admin drafts a parameterized query, a SQL validator gates it, it
  is published as a tile, and end-users run it. Every run produces an `audit_summary.docx` with the pinned
  capability version and row-level provenance.
- **Vendor-neutral LLM router** — prefer → default → first-active fallback across any configured vendor.

## Who Uses CogniBase?

| Role | How they interact |
|---|---|
| **OnBase administrators** | Author capabilities in the Schema chat, define anchors and bridges, configure vendors, publish tiles and grant them to groups |
| **Department end-users** | Run published Retrieval and Report tiles for their group; never write SQL directly |
| **Analysts / IT** | Use the RAG chat to ask natural-language questions across anchored OnBase data |
| **Auditors / compliance** | Read the `audit_summary.docx` produced on every capability run — pinned version, bound parameters, source snapshot, rows returned |

## Current Build Status (June 2026)

CogniBase is **pre-POC**. A substantial design corpus and a Phase A/B code core exist and run locally,
but there is **no live OnBase connection yet** — the OnBase REST and Unity clients are stubs, and every
data flow currently runs against **local fixtures and synthetic records** (parsed `.expk` exports, a
sample schema, and demo capability data). Treat "Live" below as "runs locally today against fixtures",
not "in production at a customer".

| Area | Status |
|---|---|
| FastAPI server on :8650 (`Application.server.app`) | ✅ Live (local) |
| Vendor-neutral LLM router (Claude active; OpenAI/Gemini/Ollama/LM Studio/llama.cpp pre-wired) | ✅ Live |
| ChromaDB vector index + RAG retriever/query engine | ✅ Live (≈40 demo embeddings) |
| OnBase source connector — **fixture mode** (reads `.expk` / `schema.json`) | ✅ Live (fixtures only) |
| Anchors + Lake materializer (raw JSONL → per-anchor Chroma collection) | ✅ Live (3 demo anchors) |
| Heuristic Bridge suggester (BU prefix un-siloing) | ✅ Live |
| Admin-Authored Capabilities — CRUD, SQL validator, grants, run | ✅ Live (3 demo capabilities) |
| `audit_summary.docx` provenance on every run | ✅ Live |
| Lifecycle visualizer (pure-SVG, population-scaled) | ⚠️ Partial (M25-minimal) |
| Entity resolver (deterministic + fuzzy clustering) | ⚠️ Partial — built, not wired into materializer |
| OnBase REST client (live document/keyword/doc-type) | 🗓️ Planned — M2 (stub today) |
| OnBase Unity API client (.NET shim or REST overlap) | 🗓️ Planned — M3 (stub today) |
| OAuth2 PKCE auth to OnBase IdP | 🗓️ Planned — M2 |
| Live metadata + schema collector | 🗓️ Planned — M4–M9 |
| OnBase-Web-Client-style retrieval UI (real, not mockup) | 🗓️ Planned — M10 |
| `/health`, `/version`, `/info` QI contract endpoints | ⚠️ Partial — only `/health` exists |
| `QI_CogniBase` NSSM service + `QI_CogniBaseTunnel` | 🗓️ Planned — registered in service registry, not yet running 24/7 |

## The Vision

A standalone OnBase intelligence layer: an institution points CogniBase at its OnBase deployment, anchors
the data that matters, declares the bridges between its silos, and then either asks questions in natural
language or runs admin-curated capability tiles — with every answer carrying its own audit trail. Beyond
OnBase, the same anchor/bridge/capability machinery accepts any source connector, making CogniBase a
general cross-silo reasoning platform that happens to start with OnBase.

## Why It Is Different (from OnBase / Tableau / Power BI)

- **Bridges** un-silo the BU three-letter-prefix pattern that defeats single-silo tools.
- **Anchor-scoped agent** — reasoning is constrained to declared data, not free-roam over everything.
- **Admin-Authored Capabilities** — a safe authoring path (draft → validate → publish → grant) so
  end-users get curated answers, never raw SQL access.
- **Provenance by default** — every run emits an audit document pinned to the exact capability version
  and source snapshot, reproducible byte-for-byte.

## Relationship to MapSnap

CogniBase was forked from **MapSnap** on 2026-05-06 and deliberately kept a **separate product**. MapSnap
stays a stable, passive Jenzabar schema browser; CogniBase is the live, higher-risk OnBase integration
platform. They share the `schema.json` shape and browser HTML pattern but diverge in scope, audience, and
risk profile — kept apart so the stable browser is insulated from the integration product's churn.

---
*This page is editable at `C:\APPS\CogniBase\INTRO\status_intro.md` — save and click Refresh to update.*

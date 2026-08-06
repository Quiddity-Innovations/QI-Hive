# MapSnap — Understand any enterprise database, in plain English

## What is MapSnap?

MapSnap is a self-contained, local-first **schema intelligence tool**. Point it at a large enterprise database — a university ERP (Jenzabar EX), a Hyland OnBase content repository, or any SQL Server / PostgreSQL / MySQL / Oracle / SQLite instance — and it produces a fully navigable HTML browser of every table, column, key, and relationship, then layers an AI assistant on top that can **explain the schema and translate plain-English questions into working SQL**.

It runs as a small Python HTTP server (port **9876**) serving a single rich HTML application. There is no cloud dependency by default: the AI runs against a **local Ollama model**, and a fail-safe data-governance guardrail blocks any regulated data from ever leaving the machine unless an administrator explicitly raises the policy.

MapSnap is a Quiddity Innovations original product and the design ancestor of **CogniBase** — the same engine-agnostic pipeline is intended to carry, unchanged, to a Boston-University OnBase deployment.

## The Problem We Solve

- **Enterprise schemas are undocumented and cryptic.** An OnBase database has 2,300+ tables with names like `hsi.itemdata` and `hsi.keytypetable`; nobody on staff knows where "checks" or "student transcripts" actually live.
- **Vendor documentation is incomplete, scattered, or behind a paywall.** Teams reverse-engineer the same relationships over and over.
- **Foreign keys are often not declared.** OnBase enforces relationships in the application layer, so a raw schema dump shows almost no joins — the map looks like disconnected islands.
- **Writing SQL against an unfamiliar 2,000-table schema is slow and error-prone**, and getting it wrong against a production system is risky.
- **Regulated data (FERPA / GLBA / HIPAA) cannot be casually shipped to a cloud AI** — yet that is exactly what naive "chat with your database" tools do.

## Our Approach

MapSnap separates **reasoning** from **data**. A model reasons over the *schema* (names, types, relationships) and drafts SQL; the SQL executes **locally**; result rows render **locally** and never leave the box. On top of the raw structure, MapSnap builds a per-profile "knowledge bundle" of enrichment layers — semantic annotations, a business-value catalog, real data profiling, and a local vector index — so the AI understands not just the shape of the schema but its *meaning* and the *actual data in place*.

Every enrichment artifact is a plain file stored beside the schema, the whole pipeline is engine-agnostic, and the compliant posture (`local_only`) is the default from day one rather than bolted on later.

## Who Uses MapSnap?

| Role | How they interact |
| --- | --- |
| Database administrator | Connects to a live database, extracts the schema, and browses tables, columns, and inferred relationships visually. |
| Data / integration analyst | Asks the chat assistant where data lives, generates and runs read-only SQL via NL→SQL, and exports findings. |
| Application / report developer | Uses the FK-in / FK-out and diagram views to plan joins; recycles verified queries as few-shot examples. |
| Compliance / security officer | Sets each profile's data policy (`local_only` / `cloud_metadata_only` / `cloud_with_agreement`), reviews the egress audit log, and locks regulated profiles. |
| OnBase / ERP system owner | Imports OnBase `.expk` config or CSV/DDL exports to build a catalog of DocTypes and keyword definitions and confirm relationships. |
| Quiddity operator (the owner) | Runs MapSnap as the `QI_MapSnap` service behind a named Cloudflare tunnel; manages profiles, users, and AI connections. |

## Current Build Status (June 2026)

| Area | Status |
| --- | --- |
| Local HTTP server + single-page HTML browser (port 9876) | ✅ Live |
| Multi-engine live extract (SQL Server / PostgreSQL / MySQL / Oracle / SQLite) | ✅ Live |
| CSV-import and DDL-import schema paths | ✅ Live |
| Soft (inferred) foreign-key detection | ✅ Live |
| Table / column / FK-in / FK-out / diagram / data views | ✅ Live |
| Login auth, roles, and per-tab permissions | ✅ Live |
| AI chat assistant (local Ollama) | ✅ Live |
| NL→SQL generation + local read-only execution | ✅ Live |
| Layer 0 — egress guardrail + per-profile data_policy control plane | ✅ Live |
| Layer 2 — semantic annotations wired into the prompt | ✅ Live |
| Layer 3 — value catalog (OnBase live + curated .expk) | ✅ Live |
| Layer 4 — data profiling with PII auto-detection + masking | ⚠️ Partial (code shipped; awaiting elevated service restart) |
| Layer 5 — semantic / hybrid retrieval (ChromaDB + nomic-embed-text) | ⚠️ Partial (code shipped; awaiting elevated service restart) |
| Verified-query library (self-improving few-shot) | ⚠️ Partial (code shipped; awaiting elevated service restart) |
| Frontier / cloud model via AI Connections (gated by policy) | ⚠️ Partial (mechanism live; per-institution DPA/BAA per deployment) |
| Content Library document RAG index | ✅ Live |
| Schema compare / diff between profiles | ✅ Live |
| Named Cloudflare tunnel (mapsnap.quiddityinnovations.com) | ✅ Live |
| Settings UI for the data-policy + enrichment grid | ⚠️ Partial (server enforcement authoritative; UI surfacing in progress) |

## The Vision

MapSnap aims to make any enterprise database **born understood**. Connecting and extracting should automatically run the enrichment chain so that, minutes later, a non-expert can ask "where are the checks?" or "which tables hold student records?" and get a correct, join-aware answer — on any engine, with regulated data never leaving the building. The same stack, pointed at a new connection, becomes a new product: this is the genetic blueprint behind **CogniBase @ BU**.

I see companies adopting MapSnap as the **onboarding tool for their systems-of-record federation** — the front door through which every new source system enters the fabric. At Boston University I've deployed it on my own system and walked a handful of people through it. They genuinely found it interesting. My hope is that it eventually serves some departments at BU. Pointed at a structured source, MapSnap reads the schema and **proposes canonical-key mappings**. Those proposals become **candidate Normalizers** that CogniBase consumes and a steward ratifies: MapSnap builds the ontology CogniBase governs. Together with AutoPDF the three form one governed pipeline — **capture (AutoPDF) → understand (MapSnap) → align → correlate (CogniBase).**

## How the Knowledge Bundle Works

Each database is a **profile** under `Product/<name>/`. Beside its `schema.json`, MapSnap accumulates engine-agnostic *sidecar* files that the AI reads on demand: `annotations.json` (per-table purpose / role), `BU_Catalog.json` (business-name values like DocType names), `profile.json` (real, PII-masked data samples and semantic types), and a local `.index/` ChromaDB vector store. An `enrich.py` orchestrator runs the chain idempotently and best-effort, triggered by extract, document import, and config import — fast layers inline, heavy layers in the background.

## Compliance by Construction

The `guardrail.py` control plane is the single chokepoint for every cloud call. Under the default `local_only` policy nothing leaves the machine. Under `cloud_metadata_only`, schema structure and type names may reach a cloud model, but row values, profiling samples, query results, and document content are stripped or masked — enforced in code, not by convention — and every decision is logged for audit. A profile carrying regulated column classifications can be locked so raising its policy requires an admin and a recorded agreement.

*This page is editable at C:\MapSnap\INTRO\status_intro.md — save and click Refresh to update.*

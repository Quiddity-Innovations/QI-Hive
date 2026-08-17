# QI × Boston University — AI & Data-Engineering Ecosystem Fit Assessment

**Prepared for:** Renne Santiago / Quiddity Innovations  
**Role of author:** Senior IT / AI architecture consultant  
**Date:** 2026-06-27  
**Subject:** Fit of the BU AIDA / Atlas / Nexus environment against the QI toolset, with focus on MapSnap & CogniBase  
**Classification:** Quiddity Innovations **INTERNAL ONLY** — not for external distribution  
**Revision:** Rev 2 — adds a topology deep-dive from the Nexus page-3 diagram (visual detail not in the text layer).  

---
## 0.  Executive Summary

Boston University's IS&T organisation has stood up one of the most architecturally disciplined enterprise-AI programmes in higher education — the AIDA initiative, built on a single open-source, cloud-native platform (“Atlas”) that powers two product families: TerrierAI (community AI) and TerrierData (institutional data). The defining posture is a “critical embrace” of AI: architecture first, curated heterogeneity, no vendor lock-in, and a literal selection test of “strategic fit, cost, capability, and freedom to leave.” The entire stack runs at $0/yr in software licensing (97% open source).

Assessed against Quiddity Innovations' current toolset, the headline finding is unusually strong: three QI products already point directly at BU's exact technology surface, and several of QI's platform choices line up with BU's by independent convergence rather than coincidence.

### The three direct-fit products

| QI product | Targets at BU | Why it fits |
| --- | --- | --- |
| CogniBase | Hyland OnBase (BU runs it; BU has a REST POC team) | Brings the OnBase domain layer (DocType modelling, Custom Query semantics, Normalizers, Gates, Query Federator, three-corpus RAG) that BU's REST team explicitly lacks. |
| MapSnap | Jenzabar EX + OnBase + any SQL Server/Oracle/Postgres schema | BU is retiring Jenzabar and stabilising SIS — MapSnap turns an undocumented 2,000-table schema into plain-English answers and NL→SQL. A migration-archaeology tool. |
| AutoPDF | OnBase ingestion (emits OnBase XML Index DIP, Foundation 24.1) | Local-first batch convert / split / extract → records-team feeder for OnBase. Confidential docs never leave the machine — FERPA-safe by construction. |

### The convergence signals (QI and BU already chose the same things)

- OpenClaw — BU's TerrierAI Assistant is built on OpenClaw; Renne already runs OpenClaw in production (C:\APPS\OC). Renne holds operational OpenClaw experience BU is only now hardening.
- MCP (Model Context Protocol) — BU's Nexus/Regent agents call data through MCP tools; QI's Brain and tooling are already MCP-native. This is the single cleanest integration surface.
- Claude Code — BU uses a custom Claude Code skill to convert SnapLogic→Prefect pipelines; QI's entire operating model is Claude-Code-driven.
- Vector + open formats — BU uses pgvector / Iceberg / Trino; QI's tools use ChromaDB/pgvector-class stores and are designed engine-agnostic.

### The one collision to fix

BU's AI platform is named “Nexus.” Renne also has a project named NEXUS (C:\APPS\NEXUS). In any BU-facing material this will cause confusion and should be renamed or clearly differentiated.

### Bottom line

The strongest, lowest-friction wedge is CogniBase as the OnBase domain layer for BU's REST POC team, with MapSnap + AutoPDF bundled as a Jenzabar/OnBase migration toolkit. The price of entry is conformance to BU's architecture rules — open standards, MCP-native, K8s/ARM-deployable, Entra ID identity, audit-first, and no per-seat licensing. CogniBase already meets most of these by design; MapSnap and AutoPDF need a container/MCP packaging pass. Commercially, lead with a forward-deployed design partnership (the CollegeVine model) in the operational/IT-data niche CollegeVine does not touch, backed by flat-fee, no-lock-in tool licences — never per-seat.

---
## 1.  Method & Inputs

This assessment cross-reads two BU source documents against the live QI ecosystem registry (25 registered projects) and the on-disk design/intro documentation for the BU-relevant products.

### Sources analysed

| Input | What it provided |
| --- | --- |
| BU-AI-Data-Engineering-Dossier-for-Quiddity.md | Full BU site crawl: AIDA strategy, four-tier portfolio, TerrierAI/TerrierData products, the eight Atlas components, full tech stack, 2026 roadmap (4 lanes), vendors being retired. |
| nexus-platform-overview.pdf (8 pp, BU IS&T, Apr 2026) | Deep technical spec of BU's Nexus AI-chat platform: 5-layer topology, MCP server, agent loop, admin portal, LLM providers, infra/security/observability. |
| C:\QIH\ecosystem\qi_registry.json | Authoritative list of 25 QI projects, ports, status, families. |
| C:\APPS\CogniBase\DESIGN\* + README | CogniBase architecture, three-corpus model, access model, Query Federator, and the BU REST-POC coordination + beyond-OnBase strategy docs. |
| C:\APPS\MapSnap\INTRO + docs | MapSnap status, knowledge-bundle design, OnBase/Jenzabar targeting, BU video script. |
| C:\APPS\AutoPDF\INTRO | AutoPDF local-first PDF toolkit + OnBase DIP output. |

---
## 2.  The BU Target Environment (condensed)

### The four-tier AI portfolio — where a partner can land

| Tier | Name | Occupant / nature | Door for QI? |
| --- | --- | --- | --- |
| 01 | Bleeding edge | Frontier agentic design partnerships — today only CollegeVine (admissions/recruiting). | OPEN — in the operational / IT-data niche CollegeVine does not cover. |
| 02 | Homegrown | BU's own TerrierAI/TerrierData on open-source foundations. | Capability injection, not product sale. |
| 03 | Enterprise platform AI | AI inside Salesforce/SAP/ServiceNow/Blackboard. | Indirect — OnBase-adjacent. |
| 04 | Specialized applications | Niche vended tools with embedded AI, adopted case-by-case. | OPEN — natural home for MapSnap / AutoPDF / CogniBase as flat-fee tools. |

### The target “Intelligence Stack” (every agent reasons through these; never touches raw systems)

- Agent layer — reasons, plans, executes.
- Knowledge base — curated, domain-owned, one source of truth.
- Semantic layer — raw data → shared business terms.
- Ontology — the institutional map of how entities relate (BU's self-identified weakest, most strategic layer).

### The eight Atlas components (and which QI tool relates)

| Atlas component | Role / tech | QI relevance |
| --- | --- | --- |
| Forge | K8s (EKS)+Graviton/ARM, ArgoCD, Linkerd, OPA | Deployment target — QI tools must be container/ARM-friendly. |
| Cortex | Iceberg-on-S3, Spark, Dagster, Trino, dbt (Data Lake) | CogniBase's “lift OnBase into a lake” mission lands here if it emits Iceberg/Trino-queryable output. |
| Lattice | APISIX gateway, FastAPI microservices | QI tools are FastAPI — same idiom; expose via APISIX. |
| Convoy | Prefect batch + Claude Code conversion skill | AutoPDF/MapSnap pipelines could run as Prefect flows. |
| Meridian | EventBridge, SNS/SQS, Person Broker (400+ attrs) | Event consumers; CogniBase Normalizers parallel the Person CDM. |
| Nexus | AI platform: FastAPI, MCP, multi-provider (Claude/GPT/Gemini) | Primary integration host — CogniBase/MapSnap as MCP tool endpoints Nexus agents call. |
| Lexicon | Cube, Superset, OpenMetadata (semantic layer) | Ontology/knowledge-graph work — QI semantic-modelling play. |
| Regent | Headless AI workflows on Nexus agent framework + MCP (PLANNED) | Least mature → largest open frontier for agentic IP. |

### The architecture rules = the price of entry

- Open-standard native — Iceberg tables, Trino-queryable, MCP tool interfaces, OPA-enforceable. No closed formats.
- No per-seat licensing; no lock-in — “freedom to leave” is a literal selection criterion.
- Identity-aware & auditable — Entra ID SSO, per-user isolation, audit logging (requirements, not nice-to-haves).
- Data-classification guardrails — no HIPAA/PCI in the lake; FERPA-grade auditing.
- Cloud-native, ARM-friendly, K8s-deployable — to align with Forge (EKS + Graviton).
- Forward-deployed delivery — lean embedded engineers over heavy vendor relationships.

### Vendors BU is actively removing (budget is being freed)

SnapLogic (~$450K/yr being eliminated), MicroStrategy (hosting migration / re-licensing), Jenzabar (retirement), Buzz (replacement), mainframe archives. A well-priced open tool that helps these migrations can capture a slice of freed budget — and avoids looking like the legacy middleware BU is shedding.

---
## 2A.  Topology Deep-Dive — what the Nexus diagram reveals (Rev 2)

The Nexus overview's only embedded graphic — the page-3 platform-topology diagram — carries detail that the document's text never states. Reading it closely materially sharpens the integration picture and confirms several assumptions. The most important revelation is the physical two-VPC separation and the exact seam through which AI reaches data.

### The diagram (BU Nexus platform topology, page 3)

![BU Nexus — Data Engineering VPC (left) and AI Engineering VPC (right), joined only across a gated seam. Source: nexus-platform-overview.pdf p.3.](C:\Users\renne\Downloads\QI_BU_Assessment_assets\nexus_topology_page3.png)
*BU Nexus — Data Engineering VPC (left) and AI Engineering VPC (right), joined only across a gated seam. Source: nexus-platform-overview.pdf p.3.*

### Seven details the text did not give us

- TWO physically separated VPCs — a Data Engineering VPC (S3 lake, Glue, Athena, Trino, Spark, Dagster, OPA) and an AI Engineering VPC (TerrierGPT, Nexus apps, MCP, pgvector, DocumentDB). They are NOT one network.
- The AI side reaches BU data ONLY through Apache APISIX (API Gateway) across AWS VPC Peering (Nitro-encrypted, TLS), with Linkerd mTLS inside each cluster. Agents never touch the lake directly — exactly the “never reach raw systems” intelligence-stack rule, enforced at the network layer.
- Three egress paths are drawn explicitly: VPC Peering (to BU data), NAT Gateway (non-BU / cloud targets e.g. Azure OpenAI), and Transit Gateway / Internet2 (back to campus systems).
- MCP is the architectural SPINE, not a feature: there is an “MCP Gateway (mcp-gateway-registry)” plus a “Nexus MCP Control Plane.” Tools are registered in a registry and routed by a control plane.
- The concrete data services exposed across the seam today are Person API, Course API and a Cube Semantic Layer (labelled “Future Data Lake Gateway”), with Person & Course vector indices in pgvector. OnBase appears NOWHERE in the topology — a genuine white space.
- Audit is first-class infrastructure: a dedicated Vector HTTP Sink (Audit Trail) on the data side and a Vector Store (Audit Trail) on the AI side, beside the Loki/Mimir/Tempo/Alloy/Grafana observability stack on BOTH VPCs.
- Identity is Azure EntraID (OAuth2); inference is multi-cloud — Azure OpenAI (GPT/embeddings) + AWS Bedrock. OPA (Access Control) gates Trino access on the data side.

### Why this matters — OnBase is the missing node

BU's grounding corpus today is Person, Course, WordPress, ServiceNow and student systems. OnBase — the system CogniBase masters — is not yet in the Nexus data plane at all. CogniBase therefore does not displace anything on this diagram; it fills an empty slot. That is the single most encouraging detail in the document: the OnBase node BU will eventually need does not exist, and QI already has it.

### Refined integration mechanics for CogniBase (now concrete)

| Option | Where CogniBase lands | Mechanism | Verdict |
| --- | --- | --- | --- |
| A — AI-side MCP (lead) | AI Engineering VPC | Register CogniBase's MCP server in the mcp-gateway-registry; the Nexus MCP Control Plane routes agent tool-calls to it (search / ask / schema_explain / federated_query). | Lightest, MCP-native, matches the spine. DO THIS FIRST. |
| B — Data-side API | Data Engineering VPC | Deploy CogniBase as an “OnBase API” service behind APISIX, a peer of Person API / Course API, reachable across the VPC peering; emit curated OnBase entities to the S3/Iceberg lake + pgvector indices. | Heavier but lands OnBase in the durable data plane. PHASE 2. |
| C — both | Both VPCs | MCP tool surface for agents (A) backed by a governed OnBase data service (B). | End-state. The MCP face is the front door; the data service is the foundation. |

### What the diagram confirms about the price of entry

- Entra ID (Azure) identity is non-negotiable — the diagram shows it wiring every channel. CogniBase's planned Entra adapter moves from “nice” to “required for option A.”
- mTLS (Linkerd) + APISIX + OPA are the in-cluster contract — CogniBase's Gates map cleanly to OPA; its L1–L4 audit trail matches BU's dedicated audit sinks. The compliance posture is already aligned.
- Per-corpus pgvector indices (Person, Course) are the precedent — CogniBase emitting an “OnBase” pgvector index is the obvious, in-pattern Phase-2 artefact (alongside, not instead of, lake/Iceberg output).

### One correction to Rev 1

Rev 1 treated “Iceberg-on-S3” as the universal storage target. The diagram clarifies a split: the Data Engineering VPC holds the S3 lake / Glue / Trino, while the AI Engineering VPC grounds assistants on pgvector indices + DocumentDB (conversations) + Postgres (config). CogniBase's storage-emit recommendation is therefore two-pronged — pgvector index for the AI plane (fast path) and lake/Iceberg for the data plane (durable path) — not a single Iceberg target.

---
## 3.  The Quiddity Toolset (what we are fitting)

The QI ecosystem holds 25 registered projects. Most are unrelated to BU (consumer/AI apps). The BU-relevant set is small and sharp — three direct-fit products plus a supporting platform layer.

### BU-relevant QI products

| Project | Path / status | One-liner |
| --- | --- | --- |
| CogniBase | C:\APPS\CogniBase — pre_poc | Vendor-neutral local OnBase intelligence: schema map + metadata + RAG + federated retrieval, pluggable LLMs (Claude/OpenAI/Gemini/Ollama). |
| MapSnap | C:\APPS\MapSnap — active_stable | Local-first schema-intelligence tool: any enterprise DB → navigable browser + AI that explains schema and does NL→SQL, regulated data never leaves the box. |
| AutoPDF | C:\APPS\AutoPDF — active dev | Local-first PDF toolkit: bulk convert / split / extract → CSV/XLSX/OnBase DIP. No cloud, no telemetry. |

### Supporting QI platform layer (credibility & integration assets)

| Asset | Why it matters to BU |
| --- | --- |
| OpenClaw (C:\APPS\OC, active_production) | Same platform BU chose for TerrierAI Assistant — direct operational credibility and a concrete collaboration entry point. |
| QI Brain (MCP server, :9011) | Demonstrates QI is already MCP-native with a knowledge-graph/decision store — mirrors BU's ontology ambition. |
| QI Hive + 7 sub-agents | Multi-agent orchestration (architect/builder/inspector/ops/scout/scribe/tester) — parallels BU's Regent agent-runtime direction. |
| Maia (multi-channel AI assistant) | Chat/voice/LINE/Telegram delivery — parallels TerrierAI Agents' chat/voice/SMS/email channel vision. |
| NEXUS (C:\APPS\NEXUS) — NAME COLLISION | Renne's NEXUS collides with BU's Nexus platform name. Rename / differentiate before any BU contact. |

---
## 4.  Alignment Map — QI tools → BU tiers & components

### Where each QI tool lands

| QI tool | Best BU tier | Plugs into (Atlas) | Integration surface |
| --- | --- | --- | --- |
| CogniBase | Tier 01 design partner / Tier 04 tool | Nexus (MCP), Cortex (lake), Lattice (API) | Expose retrieval + Query Federator as MCP tools; emit Iceberg/Trino output to Cortex. |
| MapSnap | Tier 04 specialized tool | Cortex, Convoy | NL→SQL + schema map as an MCP tool; feed migration discovery for SIS/Jenzabar retirement. |
| AutoPDF | Tier 04 specialized tool | Convoy (Prefect), OnBase | Batch extraction as a Prefect-runnable job; OnBase DIP output for records ingestion. |
| OpenClaw expertise | Tier 02 capability injection | Nexus / Assistant | Forward-deployed hardening of the OpenClaw deployment BU is piloting. |
| Ontology/semantic methodology | Tier 02/03 | Lexicon, Regent | Knowledge-graph + Normalizer methodology onto the planned enterprise knowledge graph. |

---
## 5.  Deep Dive — CogniBase (the lead play)

CogniBase is the most strategically important QI asset for BU because it solves a problem BU has publicly and a problem BU's own team has privately. Publicly: BU runs Hyland OnBase and is building AI over institutional data. Privately (per the QI coordination doc): BU has a department exploring the OnBase REST API that has REST/HTTP skills but no deep OnBase domain experience — exactly CogniBase's moat.

### What CogniBase already does right for BU

- Vendor-neutral, pluggable LLMs (Claude/OpenAI/Gemini/Ollama) — matches BU's curated-heterogeneity, no-single-bet rule.
- Local-first with a compliance control plane — three-corpus model keeps PII out of admin chat; five-layer access model (Constraint→Normalizer→CrossLink→Gate→Privacy Transformer); k-anonymity floor; L1–L4 audit trail. This exceeds most vended tools and is a FERPA selling point.
- Query Federator solves OnBase's prefix-join problem (AP_Name vs HR_Name) that OnBase Custom Queries cannot — genuine domain IP.
- Already Docker / docker-compose deployable with bind-mounted state — a real head start on K8s.
- “Beyond OnBase” mission (lift OnBase into a vector+lake layer) is the same direction as BU's Cortex lake.

### Gap analysis — to be BU-adoptable

| Dimension | CogniBase today | BU requires | Action |
| --- | --- | --- | --- |
| Deployment | Local-first / Docker on a single host | EKS + Graviton (ARM64), ArgoCD GitOps | Publish an ARM64 image + Kustomize/Helm manifest; verify on arm64. |
| Agent interface | Internal RAG/agent loop | MCP tool endpoints Nexus/Regent call | Wrap retrieval + federation as an MCP server (nexus-mcp-server-compatible). HIGHEST LEVERAGE. |
| Storage format | ChromaDB + local schema.json | Iceberg-on-S3, Trino-queryable, pgvector | Add an Iceberg/pgvector emit path so curated OnBase entities land in Cortex. |
| Identity | CogniBase admin role / AD passthrough | Entra ID (MSAL PKCE), per-user isolation | Implement the already-planned pluggable identity against Entra ID. |
| Gateway/auth | Local login | APISIX consumer keys, OPA policy | Front with APISIX; express Gates as OPA-checkable policy. |
| Licensing | Product | No per-seat, freedom to leave | Flat institutional licence + open exit; keep schema/artefacts as plain files (already true). |

### CogniBase improvement roadmap (to reach BU)

- M1 — MCP wrapper: expose search / federated-query / schema-explain as MCP tools (days, highest impact).
- M2 — ARM64 container + Helm chart; smoke-test on Graviton-class instance.
- M3 — Entra ID identity adapter (MSAL PKCE) replacing local login for BU mode.
- M4 — Iceberg/pgvector emit path feeding Cortex; Trino-queryable curated entities.
- M5 — OPA policy export for Gates; APISIX front door.
- M6 — Joint OnBase test instance with BU REST POC team; vendor-or-share REST adapter decision.

---
## 6.  Deep Dive — MapSnap (the migration accelerator)

BU's 2026 roadmap includes Jenzabar Retirement, SIS Stabilization, mainframe archive, SAP S/4 evaluation, and dozens of source-system ingestions into the data lake. Every one of those is a schema-archaeology problem — understanding an undocumented, FK-less enterprise schema before you can migrate or ingest it. That is precisely what MapSnap does, and it already supports SQL Server, Oracle, Postgres, MySQL, SQLite, OnBase, and Jenzabar EX.

### Fit highlights

- NL→SQL over a 2,000-table schema with relationships inferred (the prior OnBase run produced 34 MRG-derived + 6,167 inferred soft FKs) — turns months of reverse-engineering into minutes.
- Local-first egress guardrail (local_only by default) — regulated data never leaves the box; directly answers BU's FERPA/GLBA concern about “chat with your database” tools.
- Engine-agnostic sidecar knowledge bundle (annotations, value catalog, profiling, vector index) — the same enrichment chain that becomes CogniBase; a coherent product family story.

### Gap analysis

| Dimension | MapSnap today | BU requires | Action |
| --- | --- | --- | --- |
| Packaging | Windows, Python HTTP server (:9876), NSSM, Cloudflare tunnel | Container/K8s or analyst laptop tool | Containerize, or position as a Tier-04 analyst desktop tool (lighter lift). |
| Agent surface | Standalone HTML app | MCP tool for Nexus agents | Expose schema-explain + NL→SQL as MCP tools Regent/Nexus can call during migration work. |
| Local LLM | Ollama only | Curated heterogeneity, cloud-gated | Use existing policy-gated AI Connections to surface Claude via Bedrock, matching BU. |

### Best framing for BU

Position MapSnap not as a product to buy but as the discovery layer of a migration engagement: “point it at Jenzabar EX / the SIS / the mainframe extract and get a plain-English, join-aware map in an afternoon.” Pair with BU's Convoy/Prefect + Claude Code conversion skill — MapSnap finds and explains; Convoy converts.

---
## 7.  Supporting — AutoPDF (the records on-ramp)

AutoPDF is the third OnBase-aligned product: a local-first toolkit that bulk-converts, splits, and extracts metadata from document piles and emits a schema-accurate OnBase XML Index DIP (Hyland Foundation 24.1). For BU's records / imaging / registrar / procurement teams it is the ingestion on-ramp that feeds OnBase — with confidential documents never leaving the machine.

### Fit & gap (brief)

- Fit: local-only, no telemetry, rule-based-first with optional local-Ollama assist — FERPA-safe; OnBase DIP output is exactly what records teams need.
- Gap: bundled GPL/AGPL engines (Ghostscript/Poppler/PDFtk/NAPS2) are kept compliant via arm's-length separate-process aggregation — document this clearly for BU's open-source governance (Apache-2.0/permissive-preferred, no-GPL-in-core-infra policy). As a standalone desktop tool the GPL aggregation is fine; do NOT embed these libraries into any BU core service.
- Best framing: a Tier-04 desktop utility for records teams during the OnBase content build-out; bundle with CogniBase (ingest → understand → retrieve).

---
## 8.  Strategic Overlaps, Collisions & Convergence

### OpenClaw — the credibility bridge

BU's TerrierAI Assistant is built on OpenClaw, currently in “deployment hardening / pilot scoping.” Renne runs OpenClaw in production today. This is the single most under-used asset: it converts QI from “outside vendor” to “practitioner who has already operated the platform BU is adopting.” Offer OpenClaw operational patterns, MCP tools, and hardening notes as a no-cost relationship opener.

### MCP + Claude Code — the technical handshake

BU's agents reach data exclusively through MCP tools, and BU uses a custom Claude Code skill for SnapLogic→Prefect conversion. QI is already MCP-native (QI Brain) and Claude-Code-operated end to end. Any QI tool exposed as an MCP server is natively callable by Nexus/Regent — making MCP wrappers the highest-leverage engineering investment across the whole portfolio.

### The NEXUS naming collision — fix before contact

BU's flagship AI platform is “Nexus.” Renne's own project C:\APPS\NEXUS shares the name. In any BU-facing document, deck, or repo this will read as either confusion or presumption. Recommendation: rename Renne's NEXUS (or give it a clear product name) for external materials, and never present a QI “NEXUS” to BU.

### Differentiation vs. CollegeVine

CollegeVine occupies the Tier-01 design-partner slot but is admissions/recruiting-focused. The operational / IT-data / records / migration domain is wide open. QI should position there — agents and tools for administrative and data-engineering workflows, not student-facing recruiting.

---
## 9.  History of Fitting QI Work into BU — and what it implies

QI has already invested in the BU relationship along three lines, captured in on-disk artefacts:

### What has happened so far

- CogniBase was conceived specifically as “CogniBase @ BU” — the OnBase descendant of MapSnap, with a full design set (architecture, access model, query federator, hygiene pipeline) and a dedicated BU-REST-POC coordination document.
- The coordination doc establishes the relationship model: “coordinate, don't integrate” — both teams hit the same Hyland REST API; QI owns the OnBase domain layer, BU owns departmental DocType inventory and credentials. Several open items remain (BU contact, joint test instance, credential issuance).
- BU IT/licensing documents and explainer videos (Andrew/Ava) were produced for MapSnap and AutoPDF (2026-06-27) — IT-facing component + open-source-licensing briefs, ready to hand to BU IT.
- An inverted, technology-first ecosystem tech-stack reference exists for all QI apps — useful for demonstrating open-standard alignment to BU's governance team.

### What the history implies

- The intellectual work is done; the missing pieces are relational and packaging, not conceptual: a named BU contact, issued credentials, a joint test instance, and MCP/container packaging.
- QI should convert the coordination doc's open placeholders into a concrete ask: one IT request for credentials usable by both teams against a shared OnBase test instance.
- The “Consulting Partner AI Landscape/Roadmap Review” line on BU's roadmap is a named, RFP-shaped opening — QI's tech-stack reference + these BU IT docs are exactly the credibility package for it.

---
## 10.  Adoption Price-of-Entry — per-tool conformance scorecard

Scored against BU's six stated architecture rules. ✓ = already meets, ◑ = partial / planned, ✗ = gap to close.

### Conformance

| BU rule | CogniBase | MapSnap | AutoPDF |
| --- | --- | --- | --- |
| Open-standard native (MCP/Iceberg/Trino/OPA) | ◑ (RAG yes; MCP/Iceberg to add) | ◑ (NL→SQL; MCP to add) | ✓ (open formats, DIP/CSV/XLSX) |
| No per-seat / freedom to leave | ✓ (plain-file artefacts) | ✓ | ✓ (copy-a-folder) |
| Identity-aware & auditable (Entra ID) | ◑ (audit ✓; Entra to add) | ◑ (roles ✓; Entra to add) | ✗ (local PIN/tunnel) |
| Data-classification guardrails (FERPA) | ✓ (Gates + Privacy Transformer) | ✓ (egress guardrail) | ✓ (local-only) |
| Cloud-native / ARM / K8s | ◑ (Docker ✓; ARM/Helm to add) | ✗ (Windows/NSSM) | ✗ (Windows desktop) |
| Forward-deployed delivery model | ✓ (engagement-ready) | ✓ | ✓ |

### Read of the scorecard

CogniBase is closest to BU-ready and carries the deepest moat — it should lead. MapSnap and AutoPDF are already compliant on the things that are hard to retrofit (open formats, FERPA posture, no-lock-in) and fall short only on cloud/identity packaging, which is acceptable if they are positioned as Tier-04 analyst/records desktop tools rather than core-platform services.

---
## 11.  Commercial & Pricing Directions

BU's stated stance — “AI has changed build vs. buy; we build in-house” — makes a pure product sale a hard sell. The winning commercial shapes are co-development, capability injection, and flat-fee tools that respect “freedom to leave.” Per-seat licensing is structurally disqualifying. The budget context is favourable: BU is actively eliminating ~$450K/yr (SnapLogic) and re-licensing MicroStrategy — freed money that an open, migration-helping tool can partly capture.

### Three commercial models (use in combination)

| Model | Shape | Indicative pricing* | Best for |
| --- | --- | --- | --- |
| Design partnership (Tier 01) | Forward-deployed co-development; QI embeds and builds the OnBase domain layer BU lacks. Reference + roadmap influence in exchange for low upfront. | Low/no licence upfront; $8–15K/mo forward-deployed engagement, or revenue-share / milestone SOW | CogniBase + the REST POC team |
| Specialized tool licence (Tier 04) | Flat institutional licence, open exit, source/artefacts as plain files. No per-seat. | $15–40K/yr per tool flat, + optional support tier | MapSnap, AutoPDF, CogniBase-as-tool |
| Consulting / capability injection | Respond to BU's named “Consulting Partner AI Landscape/Roadmap Review”; scoped advisory + accelerators. | $150–250/hr or fixed-scope $20–60K project | Roadmap review, ontology/semantic methodology |

### Pricing principles

- Anchor against what BU is removing, not against commercial SaaS list prices — “a fraction of the $450K/yr you are freeing” is the right framing.
- Never quote per-seat. Quote per-tool-flat, per-engagement, or per-outcome.
- Always include an open-exit clause and plain-file data portability — it turns BU's “freedom to leave” test from a risk into a selling point.
- Lead with a low-commitment pilot (joint OnBase test instance) before any licence — BU's culture is pilot-then-scale.
- * All figures are planning placeholders for Renne to set against actual cost and appetite — not quotes.

---
## 12.  Recommended Directions (ranked)

### Ranked plays

| # | Direction | Why now | Effort | Impact |
| --- | --- | --- | --- | --- |
| 1 | CogniBase as the OnBase domain layer for BU's REST POC team | Lowest friction — they have REST plumbing, lack OnBase domain depth; CogniBase is that exact layer. | Medium | Very High |
| 2 | Bundle MapSnap + AutoPDF as a Jenzabar/OnBase migration toolkit | BU is retiring Jenzabar & stabilising SIS now; schema archaeology + records ingestion are immediate needs. | Low–Medium | High |
| 3 | Wrap CogniBase & MapSnap as MCP servers | Makes them natively callable by BU's Nexus/Regent agents; smallest change with the largest compatibility payoff. | Low | Very High |
| 4 | Respond to the “Consulting Partner AI Landscape/Roadmap Review” | A named, RFP-shaped door; QI already has the credibility package (tech-stack ref + BU IT docs). | Low | Medium–High |
| 5 | Pursue the Tier-01 design-partner slot in the operational/IT-data niche | CollegeVine occupies admissions; the operational domain is open. | High | High |
| 6 | Offer OpenClaw operational hardening as a relationship opener | BU is hardening the exact platform Renne already runs; near-zero cost, high trust-building. | Low | Medium |

---
## 13.  30 / 60 / 90-Day Action Plan

### Next 30 days — packaging & positioning

- Build an MCP wrapper for CogniBase retrieval + Query Federator (and a thin one for MapSnap NL→SQL).
- Rename / differentiate Renne's NEXUS for all external materials.
- Assemble the BU outreach pack: 1-page CogniBase-for-BU brief + the existing MapSnap/AutoPDF IT & licensing docs + tech-stack reference.
- Draft the single IT credential request (shared OnBase test instance for both QI and the BU REST team).

### Next 60 days — pilot enablement

- Publish ARM64 container + Helm chart for CogniBase; smoke-test on a Graviton-class instance.
- Implement Entra ID (MSAL PKCE) identity adapter for CogniBase BU mode.
- Stand up a joint OnBase test instance with the BU REST POC team; fill the coordination doc's open placeholders.
- Identify a sponsoring BU team / use case (records, registrar, or data-engineering migration).

### Next 90 days — demonstrate value in BU's own terms

- Demo CogniBase answering a real cross-DocType question via the Query Federator on the test instance.
- Demo MapSnap mapping a Jenzabar/SIS schema in an afternoon, output feeding a Convoy/Prefect conversion.
- Add an Iceberg/pgvector emit path so curated OnBase entities land in Cortex (TerrierData Lake).
- Propose a scoped engagement: design partnership SOW or flat-fee migration-toolkit licence.

---
## 14.  Risks & Mitigations

### Key risks

| Risk | Mitigation |
| --- | --- |
| “We build in-house” → product sale rejected | Lead with co-development / forward-deployed capability injection, not a product pitch. |
| “Freedom to leave” → lock-in resistance | Plain-file artefacts, open formats, open-exit clause as a feature. |
| Local-first vs. cloud-native mismatch | Ship ARM64 containers + Helm; or position Windows tools explicitly as Tier-04 desktop utilities. |
| Looking like the middleware BU is removing (SnapLogic/MicroStrategy) | Emphasise open standards, MCP, no-lock-in; frame as migration *accelerator*, not new middleware. |
| CollegeVine incumbency in Tier 01 | Differentiate into operational/IT-data; do not compete on admissions. |
| FERPA / data classification | CogniBase Gates + Privacy Transformer; MapSnap/AutoPDF local-only; never ingest HIPAA/PCI. |
| NEXUS name collision | Rename / differentiate before any BU-facing material. |
| Relationship stalls (no contact/credentials) | Convert coordination-doc placeholders into one concrete IT ask; use the roadmap review as a formal entry. |

---
## 15.  Appendix — Source Index

### Documents & registries read

- C:\Users\renne\Downloads\BU-AI-Data-Engineering-Dossier-for-Quiddity.md
- C:\Users\renne\Downloads\nexus-platform-overview.pdf (8 pp)
- C:\QIH\ecosystem\qi_registry.json (25 projects)
- C:\APPS\CogniBase\README.md, DESIGN\ARCHITECTURE.md, COORDINATION_BU_TEAM.md, STRATEGY_BEYOND_ONBASE.md
- C:\APPS\MapSnap\INTRO\status_intro.md + docs
- C:\APPS\AutoPDF\INTRO
- Memory: project_bu_techdocs_videos.md (BU IT/licensing docs + explainer videos)

---
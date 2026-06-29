# CogniBase — Executive Brief & BU Vision Alignment

*Document 1 of 18 · BU-Aligned Library v2 · Renne Santiago*

---

## 1. In one paragraph

Boston University has made a deliberate architectural bet: AI and institutional data are two halves of one problem, and the answer is an owned, open, semantically-governed platform — Atlas — in which every agent reasons through an **ontology**, a **semantic layer**, and a **curated knowledge base** before it ever touches a raw system. **CogniBase brings Hyland OnBase into that discipline.** It is the OnBase-native member of the intelligence stack: it maps the schema, governs the corpus, resolves entities on sanctioned relationships rather than coincidence, and answers natural-language questions across OnBase and adjacent institutional data — with every cross-source claim auditable back to the rule that authorized it. It speaks BU's own fabric (MCP tools, OPA policy, Entra identity, an L1–L4 audit trail), so it is not a bolted-on product but a governed node BU controls.

## 2. BU's direction, stated plainly

BU's published posture is a **"critical embrace" of AI**, operationalized as three commitments and a target architecture:

| BU commitment | What it means | How CogniBase honors it |
|---|---|---|
| **Architecture first** | Build the foundation (ontology, semantic layer, owned knowledge) before scaling apps | CogniBase is a foundation layer for OnBase, not a chat skin over it |
| **Curated heterogeneity** | Many models/platforms, no single bet; each earns its place on fit, cost, capability, *freedom to leave* | Vendor-pluggable LLMs (Claude/GPT/Gemini/local); plain-file artefacts; open exit |
| **AI-native, not AI-assisted** | Rebuild workflows so AI is the core interface | OnBase content becomes *queryable as knowledge*, not navigated as documents |

BU's **target intelligence stack** — the spine of the whole program — is four layers every agent must reason through, *never reaching raw systems directly*:

> **Agent → Knowledge base → Semantic layer → Ontology**

This brief's thesis: **OnBase is the largest institutional content store not yet represented in that stack — and CogniBase is how it gets there, correctly.**

## 3. The missing node

BU's current grounding sources — Person, Course, Student Hub, WordPress, ServiceNow — are real but partial. The university's system of record for contracts, invoices, transcripts, HR files, and decades of imaged documents is **OnBase**, and OnBase is uniquely hard to bring into an AI platform:

- **2,300+ tables, cryptic names, and almost no enforced foreign keys** — relationships live in application logic and configuration packages, not in the database.
- **Regulated content** (FERPA, GLBA) that cannot be casually shipped to a cloud model.
- **A configuration domain** (DocTypes, KeywordTypes, Lifecycles, Custom Queries) whose *meaning* is invisible to a naïve "chat with your database" tool.

CogniBase was built specifically for this. It does not displace anything on BU's roadmap — it fills the empty OnBase slot with a component designed to BU's own rules.

## 4. The trust thesis (why this brief leads with ontology)

The defining risk of putting an AI over a data lake is not that it fails to find correlations — it is that **it finds too many, convincingly, that are not real.** A model with access to data but not to the *business-process model* behind it will assert that an OnBase `AP_Name` "J. Smith," an SIS student "John Smith," and an HR record are the same entity — a fluent, fully-cited analysis that an audit later proves false. A neophyte believes it; the institution acts on a fiction.

CogniBase's central design commitment is the opposite stance: **a correlation is trustworthy only if a governed ontology sanctions it.** The system traverses only declared relationships, resolves entities on vetted keys (never name or embedding similarity alone), and labels anything unsanctioned as *inferred and unverified* — excluded from authoritative claims. This is the subject of Documents 2 (Semantic & Data Ontology) and 3 (Challenges & Mitigations), and it is the single most important reason CogniBase belongs in an *institutional* — not merely a clever — AI program.

## 5. How CogniBase maps onto Atlas

CogniBase is designed to be an Atlas-native citizen, not a foreign service:

| Atlas component | CogniBase relationship |
|---|---|
| **Nexus** (AI platform, MCP spine) | CogniBase registers in the `mcp-gateway-registry`; Nexus/Regent agents call its tools (search, ask, schema-explain, federated-query) |
| **Cortex** (Iceberg/S3 lake, Trino) | Curated OnBase entities can be emitted to the lake — Trino-queryable, lineage-tracked |
| **Lattice** (APISIX, FastAPI) | CogniBase is FastAPI; deployable behind APISIX as a governed "OnBase API" |
| **Lexicon** (semantic layer, knowledge graph) | CogniBase's Normalizers/ontology feed BU's planned enterprise knowledge graph |
| **Forge** (EKS, OPA, Entra, audit) | Gates → OPA policy; identity → Entra ID; L1–L4 audit → BU's audit sinks |

The integration surface is **MCP first** (lightest, native), with a data-plane API path as the durable Phase-2 home. Detail in Documents 4, 11, and 14.

## 6. What a pilot proves

A scoped pilot against a non-production OnBase instance demonstrates, in BU's own terms:

1. **Governed correlation** — a real cross-DocType / OnBase-↔-SIS question answered through *sanctioned* relationships, with the inferred-vs-verified distinction visible to the user.
2. **Auditability** — every number traceable to its source and the rule that joined it (FERPA-grade).
3. **Atlas-native integration** — CogniBase reachable as an MCP tool from a Nexus agent.
4. **No lock-in** — artefacts as plain files; the whole profile portable; open exit demonstrated, not promised.

## 7. What we ask of BU

Consistent with BU's "Working Together" model: a **sponsoring team**, a **named technical contact**, and **one IT credential request** for a shared non-production OnBase instance usable by both CogniBase and BU's REST POC team. Coordination, scope, and roadmap are detailed in Document 16.

## 8. Reading guide to this library

- **Trust layer (read first):** Doc 2 *Semantic & Data Ontology*, Doc 3 *Challenges & Mitigations*.
- **Architecture & knowledge:** Docs 4–10 (architecture, components, corpus, access, federation, hygiene, provenance).
- **Platform, model & delivery:** Docs 11–14 (MCP/Nexus, model strategy, deployment/licensing, API & tool contract).
- **Adaptive trust & learning:** Document 17 — *Confidence, Human-in-the-Loop Review & Continuous Learning*.
- **Systems landscape:** Document 18 — *BU Systems of Record: Affinity & Extension Map*.
- **Appendices:** Appendix A — *MapSnap × CogniBase Tandem & Pre-Ingestion Augmentation*; Appendix B — *Alignment to BU's 2026 Roadmap (Four Lanes)*.
- **Strategy & engagement:** Doc 15 *Beyond OnBase*, Doc 16 *Coordination & Pilot Plan*.

> CogniBase's promise to BU is not "an AI that talks to OnBase." It is **OnBase made institution-grade knowledge** — governed, semantic, auditable, and owned — on the architecture BU has already chosen.

---
*Document 1 of 18 · Frame A (BU-vision-led) · CogniBase BU-Aligned Library v2 · generated 2026-06-28*

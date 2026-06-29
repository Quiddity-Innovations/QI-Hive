# CogniBase — Coordination & Pilot Plan

*Document 16 of 18 · BU-Aligned Library v2 · Renne Santiago*

---

## 1. Working model with BU's OnBase REST POC team

BU has a team exploring the OnBase REST API with strong REST/HTTP skills but limited OnBase domain depth. CogniBase brings the domain layer (DocType modeling, Custom Query semantics, Lifecycle/Workflow awareness, Normalizers, Gates, Hygiene) on top of plumbing both teams hit. The relationship is **coordinate, not integrate** — same upstream Hyland API, shared notes, no duplicated work.

| Concern | Owner |
|---|---|
| Hyland identity/tenant config, credentials | BU IT |
| DocType / KeywordType departmental inventory | BU REST POC team |
| OnBase domain modeling, Normalizers, Gates, Federator, hygiene, RAG, audit | **CogniBase** |
| Document Management REST client | Either (shared/vendored) |

## 2. What we ask of BU (the gating signals)

1. A **sponsoring team** and a **named technical contact**.
2. **One IT credential request** for a shared **non-production** OnBase instance usable by both teams (draft ready).
3. A **named data steward** to ratify ontology relationships (the ontology needs an owner — Document 2).

## 3. Pilot scope (3–4 weeks)

A narrow, high-value use case (e.g., FA-document lifecycle vs. SIS enrollment) demonstrating, in BU's terms:
1. **Governed correlation** — a real cross-source question answered through sanctioned relationships, inferred-vs-verified visible.
2. **Auditability** — every claim reconstructable L1–L4 (FERPA-grade).
3. **Atlas-native integration** — CogniBase reachable as an MCP tool from a Nexus agent.
4. **No lock-in** — plain-file portability demonstrated.

## 4. Critical path

| Step | Gate |
|---|---|
| Named sponsor + steward | BU |
| Credentials + non-prod instance | BU IT |
| MCP server registered in `mcp-gateway-registry` | CogniBase (scaffold exists) |
| pgvector + Entra ID identity wired (BU mode) | CogniBase |
| Seed ontology from `.expk` + Person CDM; steward-confirm Normalizers | Joint |
| Pilot use case live + audit demo | Joint |

## 5. Success criteria

- 100% of *authoritative* cross-source claims backed by a sanctioned relationship.
- Auditor reconstructs any claim from the cited rule.
- A Nexus agent answers an OnBase question via CogniBase's MCP tool.
- BU confirms the open-exit (portability) test.

## 6. Roadmap beyond pilot

GA OnBase coverage → lake/Iceberg emit into Cortex → semantic feeds into Lexicon → Regent-style agentic workflows. Sequenced **portable-core-first** so value compounds regardless of any single milestone (internal contingency plan governs pace and IP exposure).

**Roadmap fit.** CogniBase advances items already on BU's funded 2026 roadmap rather than adding a new one — **Appendix B** crosswalks it to all four lanes (strongest in AI Engineering, concrete in Data Engineering and Enterprise Architecture, supporting in Essential Services).

## 7. Co-Development Model — a governed tandem build

BU's stated posture is *"AI has changed build vs. buy — we build in-house."* CogniBase takes that seriously: the strongest engagement is **not a product sale but a governed co-development** — BU builds *with* the CogniBase team, keeping ownership and skills, on the design-partnership pattern BU already runs. Appendix B shows the shared roadmap items; this section is how the two sides build them together.

**The IP boundary (what makes co-development clean):**

| Co-built & **BU-owned** | Licensed **CogniBase core** |
|---|---|
| The BU ontology content — which DocTypes/keywords/entities relate, the canonical-key mappings, stewardship decisions | The governed-correlation engine — Normalizers/CrossLinks/Gates, Query Federator, Privacy Transformer, hygiene + discovery pipeline |
| Use-case adapters, integration wiring, the BU knowledge graph | The reusable, maintained, evolving platform (also powers MapSnap) |

The seam is the edition/adapter boundary already in Document 13: **BU owns the institution-specific knowledge; the engine stays a licensed, maintained core** — good for BU too, who get an evolving engine rather than a fork to maintain alone.

**In practice:**
- **Forward-deployed.** The CogniBase team embeds with BU's OnBase REST POC team (plumbing) and the domain stewards / AS&IR (meaning) — *coordinate* on the REST layer (§1), *co-build* the ontology/domain layer.
- **Shared backlog** tied to Appendix B (Ontology Investigation, Studio Foundation, Agent Workflow POC, facilities/work-order correlation, lake/semantic feeds).
- **BU contributes** domain knowledge + stewardship authority (Documents 17, 18); **CogniBase contributes** the engine + OnBase depth.

**Why co-development de-risks a lean vendor.** A fair sponsor concern is key-person risk. Co-development is the answer: it **transfers operating knowledge to BU as the work proceeds**, so BU is never dependent on one person — while the core engine remains licensed, supported, and portable (open exit, plain-file artefacts). The model turns the small-vendor concern from a risk into a structured strength.

> The engagement is designed to prove value in BU's own terms, on BU's own fabric, with a clean exit — the most credible posture for a partner to a "we build in-house" institution.

---
*Document 16 of 18 · Frame A · CogniBase BU-Aligned Library v2 · generated 2026-06-28*

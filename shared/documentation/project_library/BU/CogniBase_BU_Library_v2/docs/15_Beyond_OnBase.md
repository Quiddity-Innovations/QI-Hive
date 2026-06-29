# CogniBase — Beyond OnBase: Lake, Semantic Layer & Knowledge Graph

*Document 15 of 18 · BU-Aligned Library v2 · Renne Santiago*

---

## 1. The mission shift

OnBase is rigid: walled tables, hard to combine with other sources, hard to find patterns across the full content. The strategic ambition is to **exceed OnBase** — lift what it exposes into a governed vector + lake layer where AI can correlate, infer, and report across boundaries OnBase itself cannot cross. Crucially, this expansion **inherits the trust layer** (Document 2): more reach, not more fabrication.

## 2. Four additions (governed, not speculative)

1. **Lake emit** — curated OnBase entities written to **Iceberg-on-S3** (Cortex), Trino-queryable, lineage-tracked. Open table format = no lock-in.
2. **Entity layer** — canonical entities (Person, Student, Vendor, Asset…) resolved on sanctioned keys, the nodes of a knowledge graph.
3. **Semantic layer** — shared business definitions feeding BU's **Lexicon** (Cube/Superset/OpenMetadata), so "active enrollment" means one thing everywhere.
4. **Agentic reach** — Regent-style headless workflows over the governed graph (freshness monitoring, anomaly triage), each tool call gated and audited.

## 3. Alignment to BU's roadmap

BU has published an **"Ontology Investigation"** and a 12-month goal of an **enterprise knowledge graph linking metrics, data, and policy.** CogniBase's Normalizers/CrossLinks are knowledge-graph edges in waiting; its OnBase domain modeling is the hardest, most strategic input to that graph — the layer BU has self-identified as weakest. CogniBase contributes OnBase's slice of the institutional ontology, evidence-first and steward-confirmed.

## 4. Local LLM strategy (portability)

"Beyond OnBase" does not mean "cloud-only." The `openai_compatible` adapter speaks the de-facto local-server protocol (LM Studio / llama.cpp / vLLM / Ollama-compat), so regulated correlation can run entirely on-prem when policy requires — the same engine, different backend.

## 5. The `.expk` + soft-FK foundation

A system without enforced foreign keys keeps its semantics in code, conventions, and configuration. Once CogniBase extracts those (`.expk` intent + MRG annotations + inference) into a vector + graph layer, **the relationships become first-class for the AI** — OnBase cannot natively ask "all docs related to Vendor X across all DocTypes and lifecycles," but the governed graph can.

## 6. Sequencing (Plan-A/Plan-B aware)

Build the **portable core** (entity layer, semantic feeds, lake emit on open formats) first — it serves BU *and* every other OnBase customer. Keep BU-specific wiring thin and late. The "beyond OnBase" vision is therefore also the diversification hedge: the more general the knowledge layer, the less any single customer gates its value.

**Across BU’s systems of record.** The lift-into-a-lake mission naturally reaches BU’s wider federation — MyBU/Campus Solutions, SAP, the facilities cluster (CAMMS/PMWeb/25Live/FMS), Blackbaud, Kuali/Huron — but only through sanctioned relationships. **Document 18** maps that landscape and the inclusion test (natural / policy-bounded / excluded) that governs which systems CogniBase may touch.

> Beyond OnBase is not scope creep — it is the same governed discipline, extended from one content store to the institution's connected knowledge.

---
*Document 15 of 18 · Frame A · CogniBase BU-Aligned Library v2 · generated 2026-06-28*

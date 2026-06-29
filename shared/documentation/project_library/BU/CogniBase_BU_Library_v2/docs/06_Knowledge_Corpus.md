# CogniBase — Knowledge Corpus: The Three-Corpus Model

*Document 6 of 18 · BU-Aligned Library v2 · Renne Santiago*

---

## 1. Why a corpus design at all

Retrieval quality and data governance are the same problem viewed from two sides. If everything is indexed into one vector space, PII leaks into admin answers, refresh cadences collide, trust boundaries blur, and relevance degrades. CogniBase therefore separates knowledge into **three corpora with one shared engine** — each with its own audience, cadence, hygiene, and gate posture. This is the substrate the ontology (Document 2) reasons over.

## 2. The three corpora

| Corpus | Question it answers | Examples | Audience | Index |
|---|---|---|---|---|
| **Operational Data** | "What is in the system right now?" | OnBase document instances, keyword values, lifecycle states (via REST) | End user (gate-filtered) | `cognibase_main` |
| **OnBase Configuration** | "How is the system structured?" | `.expk` packages, `schema.json`, Hyland manuals | Admin / DBA | `cognibase_config` |
| **Solution Documentation** | "Why does it look like this and how should it behave?" | BU design docs, SOPs, Excel mappings, training decks | Mixed (gate-controlled) | `doc_corpus` |

## 3. Why three and not one

Putting end-user metadata (possible PII) into the same space as static reference docs would (a) leak PII into admin chat, (b) wreck retrieval relevance, (c) couple unrelated refresh cadences, and (d) collapse trust boundaries — configuration is admin-uploaded, operational data passes through hygiene, solution docs may carry PII in screenshots. Three logical corpora, one shared retriever, **gates applied at query time.**

## 4. Solution Documentation — the institutional knowledge layer

This corpus is where BU's *business meaning* lives: narratives, SOPs, mapping sheets, training materials. Materialized as `doc_corpus` anchors with **bindings to OnBase entities**, gate-pinned, and feeding **business-rule verification** — the bridge between "the data" and "how the business relates the data," which is exactly the gap that causes fabricated correlation (Document 2). An admin defines a watched folder per anchor; dropped files auto-ingest through the hygiene pipeline (Document 9).

## 5. Cross-corpus retrieval

When the agent retrieves from all three simultaneously, results are ranked with **corpus-aware weighting** and **gate filtering first** (deny-by-default): operational hits are PII-masked per policy, configuration is admin-only, solution docs cite down to paragraph/cell. Every retrieved chunk carries its corpus, source, and gate decision into the provenance trail.

## 6. Alignment to BU

- **Cortex / lake:** curated Operational anchors can emit to Iceberg/pgvector for Trino-queryable analytics.
- **Lexicon:** Solution Documentation bindings and canonical terms feed BU's semantic layer / knowledge graph.
- **FERPA:** corpus separation + Privacy Transformer is the structural guarantee that regulated content cannot cross into an unprivileged answer.

> The three-corpus model is what lets CogniBase be simultaneously **useful to end users**, **safe under FERPA**, and **truthful across sources** — without those goals fighting each other.

---
*Document 6 of 18 · Frame A · CogniBase BU-Aligned Library v2 · generated 2026-06-28*

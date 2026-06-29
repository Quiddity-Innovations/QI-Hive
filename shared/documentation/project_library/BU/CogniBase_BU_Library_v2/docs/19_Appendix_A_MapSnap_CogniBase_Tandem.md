# CogniBase — Appendix A: MapSnap × CogniBase Tandem & Pre-Ingestion Augmentation

*Appendix A · BU-Aligned Library v2 · Renne Santiago*
*How the discovery family (MapSnap, AutoPDF) can feed and strengthen CogniBase — including a forward-looking option to pre-align OnBase content at ingestion. Marked optional / exploratory; not required for the core pilot.*

---

## A.1 Why this appendix

CogniBase does not stand alone. It is the OnBase apex of a small **discovery family** that shares one engine: **MapSnap** (the schema-intelligence ancestor that understands *any* enterprise database) and **AutoPDF** (a local-first document-capture toolkit that already emits an OnBase XML Index DIP). This appendix sketches how the three evolve in tandem, and explores a deliberately speculative idea: using AutoPDF + MapSnap to **normalize and augment documents with metadata *before* they enter OnBase**, so OnBase content is born pre-aligned with the rest of BU's data.

## A.2 MapSnap × CogniBase — a division of labor

| | **MapSnap** | **CogniBase** |
|---|---|---|
| Domain | *Structured* systems of record (SAP/BUworks, MyBU/Campus Solutions, CAMMS, StarRez…) | OnBase (unstructured/document) + cross-source correlation |
| Core skill | Schema mapping, soft-FK inference, NL→SQL, value catalogs | Governed correlation, RAG, Normalizers/Gates/Federator |
| Shared engine | The same discovery + enrichment pipeline runs in both | |

**The tandem.** MapSnap is the natural **onboarding tool for the federation in Document 18.** Pointed at each structured system of record, it reads the schema and **proposes canonical-key mappings** — e.g., "SAP vendor key ≡ canonical `PersonTaxID`," "CAMMS asset key ≡ canonical `AssetID`." Those proposals become **candidate Normalizers** that CogniBase consumes and a steward ratifies (Document 17). MapSnap accelerates building the ontology that CogniBase governs; CogniBase brings OnBase and the correlation discipline MapSnap doesn't have. They are two ends of one pipeline: *understand the structured sources → correlate them with the documents.*

## A.3 The anterior phase — AutoPDF + MapSnap pre-ingestion normalization

Today, documents enter OnBase and CogniBase reconstructs their canonical keys *after the fact*. The proposal is to move some of that work **upstream, to capture time, where context is richest:**

```
Incoming documents
   → AutoPDF        : split · OCR/extract fields · anchor-relative mapping → metadata index
   → MapSnap map    : resolve extracted fields to canonical entities/keys using the
                      value catalogs MapSnap built from the structured systems of record
   → Normalized, entity-tagged metadata (canonical keys + confidence + provenance)
   → OnBase ingestion (DIP)
```

**Net effect:** a document enters OnBase already carrying, where evidence supports it, a resolved `BUID`, a canonical entity tag, a confidence score, and a provenance stamp — so downstream CogniBase correlation is *pre-aligned* rather than rebuilt. AutoPDF already produces OnBase-ready DIP output; MapSnap supplies the canonical vocabulary; CogniBase later consumes the result under governance.

## A.4 The augmentation-keyword idea (the long shot) — two variants

**Goal:** attach extra metadata to OnBase documents that is *invisible to standard OnBase retrieval* but *accessible to CogniBase*, pre-aligning OnBase with other sources. Two ways to do it:

**Variant 1 — CogniBase overlay (RECOMMENDED).** Store the augmentation (canonical keys, confidence, provenance) in a **CogniBase-side store keyed by the OnBase Document Handle.** OnBase stays pristine — no config change, read-mostly preserved, fully reversible — and CogniBase joins augmentation to documents on the handle. Cleanest, lowest-risk, no OnBase-governance friction.

**Variant 2 — dedicated "augmentation" KeywordTypes (OPTIONAL).** Add purpose-built KeywordTypes (e.g., `CB_CanonicalEntity`, `CB_BUID`, `CB_Confidence`, `CB_Provenance`) to DocTypes, assigned but kept **out of the standard retrieval / Custom Query surfaces** via display and security configuration. The keys then travel *inside* OnBase; CogniBase reads them via the API. Requires OnBase configuration **and write access** — a deliberate expansion of CogniBase's normally read-mostly posture.

**Plausibility (honest read).** Variant 1 is straightforwardly plausible and low-risk — do this first. Variant 2 is technically feasible (OnBase lets you add KeywordTypes and limit their exposure), but **"invisible" is a configuration/security posture, not a truly hidden field**: OnBase admins and auditors can still see these keywords — which is *correct* (nothing should be genuinely secret), but it means the value is "kept out of the everyday retrieval UI," not "undetectable." It also touches OnBase indexing and config and needs write access. Use Variant 2 only if BU specifically wants the metadata embedded in OnBase and accepts that cost.

## A.5 Guardrails (non-negotiable)

1. **Augmentation is a *claim*, not a fact.** A resolved `BUID` on an invoice is an entity-resolution assertion — it must carry **confidence + provenance**, and a low-confidence resolution stays *inferred* and queued for a steward (Documents 2, 17). **Never pre-assert a join you cannot evidence** — baking a false correlation into the system of record at ingestion is worse than producing one at query time.
2. **No ACL / privacy bypass.** "Invisible to OnBase retrieval but visible to CogniBase" must **not** become a channel that smuggles data past OnBase access controls. Augmentation keywords carry only **non-sensitive canonical tags/keys/confidence — never new PII** — and CogniBase access to them still honors identity and Gates. *(A security reviewer will probe exactly this; the honest answer is the overlay variant and a strict no-new-PII rule.)*
3. **Reversibility.** The overlay is trivially reversible; any in-OnBase keyword must be removable.
4. **Read-mostly stays the default.** Writing to OnBase is an explicit, governed exception — never the standing posture.

## A.6 Phasing & value

This is **Phase 0 / optional** — it accelerates the later federation (Document 18) but is **not** required for the OnBase pilot. Start with the overlay (Variant 1); consider in-OnBase augmentation keywords only on explicit BU request. The value is twofold: it turns the discovery family into one coherent pipeline — **capture (AutoPDF) → understand (MapSnap) → align (augmentation) → correlate (CogniBase)** — and it pre-pays the entity-resolution cost at ingestion, where the document's own context makes resolution most reliable.

## A.7 Summary

MapSnap and AutoPDF are not separate products bolted onto CogniBase — they are the **front half of the same governed pipeline.** MapSnap onboards the structured systems of record and proposes the canonical keys CogniBase governs; AutoPDF can pre-normalize documents at capture; and, optionally, a thin augmentation layer can let OnBase content arrive pre-aligned with the rest of BU's data — provided every augmentation is evidenced, privacy-safe, and reversible. It is the discovery family doing at ingestion, under governance, what CogniBase otherwise does at query time.

> Cross-references: Document 2 (governed correlation), Document 17 (confidence & stewardship), Document 18 (the systems-of-record federation).

---
*Appendix A · Frame A · CogniBase BU-Aligned Library v2 · generated 2026-06-28*

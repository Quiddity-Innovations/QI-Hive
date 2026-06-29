# CogniBase — Semantic & Data Ontology

*Document 2 of 18 · BU-Aligned Library v2 · Renne Santiago*
*The trust layer: how cross-source correlation is made governed, not inferred.*

---

## 1. The problem, stated precisely

Put a capable model over a data lake and the danger is **not** that it fails to find relationships — it is that it finds **too many, too convincingly, that are not real.**

Three things get silently conflated:

- **Co-location** — two datasets sit in the same lake.
- **Correlation** — two fields look statistically or semantically similar.
- **Real relationship** — two records describe the same business entity, joined on a key the business actually uses.

An AI that has the **data** but not the **business-process model** behind it treats co-location as correlation, and correlation as real relationship. The result is a **fluent, fully-cited, and wrong** analysis. It reads as authoritative because the language model is good at language — not because the join is valid.

> **Why this is dangerous, not merely imperfect.** A specialist sees the error in seconds ("those aren't the same Smith"). A neophyte — or an executive reading a dashboard — cannot. They act on a fiction. Months later an audit reconstructs the join, finds no real connection, and the institution's confidence in *every* AI output collapses. One convincing-but-false correlation costs more trust than ten honest "I don't knows."

## 1a. What this failure mode is called

This is not a novel risk — it is a **recognized failure mode** with established names across disciplines. Naming it precisely matters for a technical audience:

- **Spurious correlation** — an association that looks real but reflects no genuine relationship *(statistics)*.
- **Conflation** (entity conflation / over-merging) — treating two distinct real-world entities as one *(identity & records management)*; the "two Smiths" merge.
- **Fan trap / chasm trap** — a join path that returns plausible but **wrong** results because the data model does not reflect the real relationship *(data modeling)*.
- **Conflating correlation with causation** — mistaking association for a real or causal link *(causal inference)*.
- **Ungrounded inference / the symbol-grounding problem** — manipulating symbols without connecting them to real-world referents *(AI / cognitive science)* — the root cause.
- **Confabulation** — fluent, confident, unfounded output *(as applied to LLMs)*.

CogniBase's working term **fabricated correlation** is the umbrella for these. The deeper framing: **semantics and ontology supply the *"what"* and *"what it is called"*; what is missing is *pragmatics* — meaning in real-world context — and the *business-process / causal model* that licenses a relationship.** An ontology says a Vendor and an Employee *can* both be a Person; only the process and grounding establish that *this* vendor **is** — or, crucially, **is not** — *this* employee. As Korzybski put it, *the map is not the territory*: the model must never be mistaken for the institution it represents.

## 2. Root cause

The model is missing the layer that gives data meaning: **the ontology and the business process that produced the data.** A lake stores *what is*; it does not store *what relates to what, on which key, within which boundary, and why.* OnBase makes this especially acute — it has **almost no enforced foreign keys**, so even the database itself does not assert how its data connects. The relationships live in configuration, conventions, and human knowledge that the AI never sees.

So the AI improvises the missing layer — and improvisation, dressed in confident prose, is indistinguishable from knowledge to a non-expert.

## 3. The governing principle

> **A correlation is trustworthy only if a governed ontology sanctions it.**

Everything below follows from this one stance. The system may **traverse only declared relationships**, must **resolve entities on vetted keys**, and must **label anything else as inferred and unverified** — visibly, and excluded from authoritative claims. Joins are **deny-by-default**: silence in the ontology means "not connected," not "connect them anyway."

## 4. The discipline — eight best practices (and how CogniBase implements each)

| # | Best practice (industry) | What it prevents | CogniBase mechanism |
|---|---|---|---|
| 1 | **Ontology as a contract** — typed entities + explicitly sanctioned relationships (edges), each with keys, cardinality, and boundary | Free-form "everything can join everything" | The relationship layer + CrossLinks (admin-vetted joins) |
| 2 | **Entity resolution on vetted keys with recorded confidence** — never string/embedding similarity alone | "J. Smith" = "John Smith" = employee | Normalizers (declared semantic equivalence, e.g. `AP_Name ≡ HR_Name → canonical:PersonName`) + match-confidence |
| 3 | **Semantic layer** — one documented definition per business term | "Which 'active enrollment' did you mean?" | Shared definitions surfaced to the agent; aligns to BU's Lexicon/Cube |
| 4 | **Business-process binding** — encode the workflow that gives data meaning | Treating a document's existence as its significance | Lifecycle/Custom-Query awareness from OnBase `.expk` configuration |
| 5 | **Provenance on every cross-source claim** — cite the sanctioned rule that permits the join | Unaccountable, unreproducible answers | L1–L4 audit; every correlation cites its CrossLink/Normalizer |
| 6 | **Confidence ≠ correctness guardrail** — surface evidence and boundaries; mark sanctioned vs inferred | The neophyte over-trusting fluent output | Inferred results visibly labeled, withheld from numeric/authoritative claims |
| 7 | **Human-in-the-loop stewardship** — a domain owner ratifies relationships | Auto-discovered joins becoming silent fact | Auto-discover → **admin-confirm** workflow; steward sign-off |
| 8 | **Data contracts** — each source declares schema, semantics, keys; changes are versioned | Silent drift breaking joins | Per-source contracts + multi-version anchors in the hygiene pipeline |

The throughline: **the ontology is the allow-list.** The AI's creativity is welcome in *language* and *hypothesis generation* — never in *asserting that two records are the same thing.*

## 5. Pragmatic BU examples (OnBase + the institutional sources)

Each example shows the **seductive-but-wrong** path, the **governed** path, and **what the audit sees.**

### Example 1 — "Which vendors are also employees?" (conflict-of-interest)
*Sources: OnBase AP DocTypes ⇄ HR/Finance (SIS/SAP).*
- **Wrong:** match `AP_VendorName` to `HR_EmployeeName` on string/fuzzy similarity → "47 vendors are employees." Several are coincidental name matches; at least one merges two different people. Convincing, cited, **false.**
- **Governed:** the only sanctioned key is a **validated person identifier** (tax ID / BU person ID via the Person CDM). A Normalizer declares `AP_TaxID ≡ HR_TaxID → canonical:PersonTaxID`; the CrossLink authorizes the AP⇄HR join *only on that key*. Name is used to *display*, never to *join*. If a record lacks the key, it is returned as **inferred — unverified**, explicitly flagged, and excluded from the count.
- **Audit sees:** N matches on PersonTaxID (CrossLink #12), K inferred-only candidates listed separately with the reason "no shared validated key."

### Example 2 — "Students with financial-aid documents stuck > 7 days, and their enrollment status"
*Sources: OnBase FA DocType + Lifecycle ⇄ SIS.*
- **Wrong:** join OnBase docs to SIS students on name or on an OnBase keyword that *looks* like a student ID but is a legacy applicant number → wrong students, wrong status.
- **Governed:** sanctioned key = **BU student ID** (Normalizer maps the OnBase keyword to `canonical:StudentID`); **boundary** = current term; **business-process binding** = the FA Lifecycle state ("In Review") defines "stuck," not the mere existence of a document. The Query Federator runs one sub-query per source and joins on StudentID only.
- **Audit sees:** the lifecycle state used, the term boundary, and the StudentID join — reproducible.

### Example 3 — "Donors who are alumni and have transcripts on file" (multi-hop, FERPA)
*Sources: Advancement ⇄ SIS ⇄ OnBase transcript DocType.*
- **Wrong:** a 3-way fuzzy join across donor name, alumni name, and transcript keyword → a privacy incident waiting to happen and likely mis-linked people.
- **Governed:** each **edge** must be independently sanctioned — Advancement⇄SIS on `canonical:PersonID`, SIS⇄OnBase on `canonical:StudentID` — and a **Gate** enforces that **transcript *content*** never enters the answer (FERPA): the system may confirm *existence* and *count*, not disclose contents, unless policy is explicitly raised with a recorded agreement.
- **Audit sees:** two sanctioned edges, a privacy Gate decision, and a content-suppression record.

### Example 4 — "HVAC service tickets vs. open facilities work orders for a building"
*Sources: ServiceNow ⇄ OnBase Facilities DocType.*
- **Wrong:** join on the free-text **building name** ("Photonics" vs "Photonics Center" vs "8 St Mary's") → split or merged buildings.
- **Governed:** the entity is the **asset/building**, resolved on a **facilities asset ID**; a Normalizer maps both sources' identifiers to `canonical:AssetID`. Building name is display-only.
- **Audit sees:** the AssetID join and the assets that had no sanctioned ID (reported, not guessed).

## 6. A pragmatic ontology approach for BU (don't boil the ocean)

BU's roadmap already lists an **"Ontology Investigation"** and a 12-month goal of an **enterprise knowledge graph**. CogniBase makes that incremental and evidence-driven for OnBase:

1. **Seed entities from what already encodes meaning** — the OnBase **`.expk` configuration** (DocTypes, KeywordTypes, Lifecycles) and the **Person CDM** (400+ attributes). These are pre-vetted semantic anchors, not guesses.
2. **Auto-discover candidate Normalizers** — propose `KeywordType ≡ KeywordType → canonical:X` equivalences; present them to a **steward to confirm or reject.** Nothing becomes fact without sign-off.
3. **Build the graph edge by edge** — each CrossLink is a deliberate, owned decision with a key and a boundary. Coverage grows where there's a real question to answer, not speculatively.
4. **Bind the process** — attach Lifecycle/Custom-Query semantics so the graph knows *why* entities relate.
5. **Feed Lexicon** — sanctioned relationships and canonical terms flow into BU's semantic layer / knowledge graph, so the discipline compounds across the institution, not just OnBase.

This is **architecture-first** applied to meaning: build the ontology before scaling the analytics on top of it.

## 7. How you know it's working (governance metrics)

- **Sanctioned-vs-inferred ratio** — share of correlations in answers backed by a sanctioned relationship (target: 100% of *authoritative* claims).
- **Audit pass rate** — % of cross-source claims an auditor can reproduce from the cited rule.
- **Steward coverage** — % of active Normalizers/CrossLinks with a named owner and a confirmation date.
- **False-join catch rate** — candidate joins rejected at the admin-confirm step (a healthy, non-zero number means the guardrail is doing work).
- **Boundary discipline** — % of queries with an explicit term/scope boundary applied.

**Confidence, calibration & learning metrics** (added per review — operationalized in Document 17):

- **Calibration error** per area — is a confidence band as accurate as it claims?
- **Human-agreement rate** — % of auto/agent decisions a steward upholds.
- **Learned items ratified vs. rejected** — governed corrections entering the ontology.
- **Threshold-by-area & drift alerts** — current autonomy per domain.

## 8. Summary

The institutional value of AI over OnBase and BU's data is unlocked **only** when the system knows not just the data but **how the business relates that data.** CogniBase encodes that knowledge as a governed ontology — typed entities, sanctioned relationships, vetted keys, bound to process, provenance on every claim, and a steward in the loop. The AI is then free to be brilliant at language and hypothesis, while being **forbidden from inventing the one thing it must never invent: that two records are the same.** That is the difference between an *incredible* analysis and an *auditable* one — and it is the reason CogniBase belongs in an institutional program rather than a demo.

> See Document 3 (*Challenges & Mitigations*) for the broader risk register, Document 6 (*Knowledge Corpus*) for corpus separation, Document 7 (*Access Model*) for Gates→OPA, and Document 8 (*Query Federator*) for the join mechanics.

---
*Document 2 of 18 · Frame A (BU-vision-led) · CogniBase BU-Aligned Library v2 · generated 2026-06-28*

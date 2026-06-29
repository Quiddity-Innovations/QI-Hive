# CogniBase — Query Federator: Sanctioned Cross-Source Joins

*Document 8 of 18 · BU-Aligned Library v2 · Renne Santiago*

---

## 1. The problem the Federator solves

OnBase Custom Queries cannot join across keyword types that BU has aliased with prefixes (`AP_Name` vs `HR_Name` vs `OAD_Name`). More deeply: an AI must never join sources on *similarity*. The Query Federator is the engine that makes every cross-source join **sanctioned, keyed, and auditable** — it is Document 2's discipline turned into execution.

## 2. Pipeline

```
Agent intent
  → Logical Query (canonical entity names)
  → Logical Query Planner (resolve Normalizers · find CrossLink · check Gate)
  → Federation Plan (N sub-queries + a join recipe)
  → Per-source dispatch (lake anchor / live REST / hybrid)
  → Join inside CogniBase on the Normalizer key (never on name/embedding)
  → Privacy Transformer → cited result
```

The planner's first act is **authorization**: if no CrossLink sanctions the join, or a Gate denies it, the plan **fails closed** — the agent returns an *inferred/unverified* note, not a fabricated join.

## 3. Federation Plan — worked shape

For "students with stuck FA documents and their enrollment status":
1. Sub-query A — OnBase FA DocType where Lifecycle = "In Review" > 7 days → returns `canonical:StudentID` set.
2. Sub-query B — SIS enrollment for those StudentIDs (current term boundary).
3. Join on `canonical:StudentID` only (CrossLink #N), Gate-checked, term-bounded.
4. Result cites the CrossLink, the Lifecycle state, and the boundary.

## 4. Reusing existing OnBase Custom Queries

Where OnBase already encodes a join, the Federator **issues that Custom Query by ID** (one round-trip — OnBase did the join) rather than re-implementing it. This respects BU's existing investment and avoids duplicate logic.

## 5. Open design choices (for BU discussion)

- **live_rest ⨝ lake** in one plan — allowed, with freshness disclosed per source.
- **Plan materialization** — repeated plans can be cached as reusable, versioned artefacts (with the same Gate re-evaluated on each run).
- **Trino as substrate** — for the SQL-source portion, BU's Trino could execute federated sub-queries; CogniBase contributes the Normalizer-aware join recipe and the OnBase domain semantics Trino lacks. A natural division of labor with Cortex.

## 6. Why it belongs at BU

The Federator is the concrete answer to "how do we get cross-departmental insight from OnBase + institutional data **without** the fluent-but-false analysis?" Every join it performs is one a named admin authorized, on a key the business actually uses, within a stated boundary, recorded for audit. It is the operational heart of governed correlation.

> The Federator's golden rule: **it would rather return less than assert a join no one sanctioned.**

---
*Document 8 of 18 · Frame A · CogniBase BU-Aligned Library v2 · generated 2026-06-28*

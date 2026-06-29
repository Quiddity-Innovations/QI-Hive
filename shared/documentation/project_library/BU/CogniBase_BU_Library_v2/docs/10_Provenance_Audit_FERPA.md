# CogniBase — Provenance, Verification, Audit & FERPA

*Document 10 of 18 · BU-Aligned Library v2 · Renne Santiago*

---

## 1. The promise

Every number CogniBase reports can answer three questions: **Where did this come from? How was it computed? Who was allowed to see it?** An auditor must be able to reconstruct any claim without the original author present. This is the difference between an analysis BU can act on and one it merely admires.

## 2. The mechanisms

| Mechanism | What it does |
|---|---|
| **Provenance tagging** | Every record carries "where did this number come from" — source, anchor, version, retrieval id |
| **Sanctioned-join citation** | Every cross-source claim cites the CrossLink/Normalizer that authorized it (Document 2/8) |
| **Numeric verifier** | Re-executes every numeric claim before it ships; mismatch → flag, not publish |
| **Audit trail** | Every report ships with an audit folder an auditor can replay |
| **Gate decision log** | Every allow/deny/transform recorded with the policy that decided it |

## 3. Audit levels (L1–L4)

| Level | Scope | Example |
|---|---|---|
| **L1** | The answer | Final text + citations |
| **L2** | The retrieval | Which chunks/anchors, which scores |
| **L3** | The computation | Sub-queries, joins, the verifier's recomputation |
| **L4** | The policy | Gate decisions, identity, transforms applied |

An auditor descends from L1 to L4 to fully reconstruct *why the system said what it said.*

## 4. Audit folder layout

Each report writes a self-contained folder: the answer, the cited sources, the federation plan, the verifier's recomputation, and the gate/identity record — a portable, plain-file evidence package (no lock-in).

## 5. FERPA & data classification (folded in)

- **No HIPAA/PCI ingestion**, by policy.
- **FERPA-classified access is audit-trailed**; transcript/education-record *content* is gated — existence/counts may be returned, content only under explicitly raised policy with a recorded agreement.
- **Privacy Transformer** (k-anonymity floor, masking, suppression) runs before any result reaches the model or user.
- Identity is **Entra ID**; CogniBase honors OnBase ACLs (cannot over-disclose).

### Provenance of corrections & confidence calibration

Every learned item records **who proposed it, who ratified it, when, and on what evidence** — corrections are first-class audited events. Audit also tracks **confidence calibration per area** (does a band mean what it claims?) and **threshold-change events**, so raising an area’s autonomy is itself an auditable, reversible decision (Document 17).

## 6. Open choices (for BU)

- **Tolerance bands** for numeric verification — exact / ±0.01 / ±1% tiers vs. BU's audit context.
- **Retention** — how long audit folders live (tied to report / compliance period / indefinite).
- **Cross-report audit search** — "show every 2026 report that used anchor X" (future).
- **Audit-sink integration** — ship L1–L4 events to BU's **Vector → Loki/Mimir/Tempo** stack via OTLP for institution-wide observability.

> Provenance is not paperwork — it is the mechanism that makes a *believable* answer also a *verifiable* one, which is the whole point at an institution under FERPA.

---
*Document 10 of 18 · Frame A · CogniBase BU-Aligned Library v2 · generated 2026-06-28*

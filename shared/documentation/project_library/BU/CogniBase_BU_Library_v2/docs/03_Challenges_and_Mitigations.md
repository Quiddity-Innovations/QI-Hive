# CogniBase — Challenges & Mitigations

*Document 3 of 18 · BU-Aligned Library v2 · Renne Santiago*
*An honest risk register for bringing OnBase into BU's intelligence stack — and how each risk is resolved.*

---

## 1. Why this document exists

A credible institutional program names its risks before a sponsor does. This document is the consolidated risk register for CogniBase at BU. Each entry states the **challenge**, its **impact**, the **mitigation** (mapped to a CogniBase mechanism and/or BU's own stack), and the **residual risk** that remains for the pilot to retire. The headline risk — fabricated correlation — is summarized here and treated in depth in Document 2.

## 2. Risk register

### R1 — Fabricated correlation ("convincing but false"; formally *spurious correlation* / *conflation* / *ungrounded inference* — see Document 2 §1a)
- **Impact:** Critical. A fluent, cited, wrong cross-source analysis that a non-expert believes; collapses trust in all AI output when audited.
- **Mitigation:** Governed ontology; deny-by-default joins; entity resolution on vetted keys; inferred-vs-verified labeling; provenance on every claim. **Full treatment in Document 2.**
- **Residual:** Coverage gaps where no ontology edge exists yet — handled honestly by returning *inferred/unverified*, never a guess.

### R2 — Entity-resolution ambiguity (no clean shared key)
- **Impact:** High. Sources that *should* join have no reliable common identifier (legacy applicant numbers vs. student IDs; free-text names).
- **Mitigation:** Normalizers declare canonical keys; match-confidence scoring; a record without a sanctioned key is never silently joined — it is surfaced for stewardship or returned inferred-only.
- **Residual:** Manual steward effort to ratify keys for high-value joins; deliberately bounded to where a real question exists.

### R3 — OnBase soft/undeclared foreign keys
- **Impact:** High. OnBase enforces relationships in the application layer; a raw schema shows disconnected islands.
- **Mitigation:** Three fused sources — live metadata, Module-Reference-Guide annotations, and `.expk` configuration — with every inferred relationship tagged `confidence` + `source`. (Prior run: 34 MRG-derived + 6,167 inferred soft FKs, each weighted.)
- **Residual:** Inference confidence varies; low-confidence edges are advisory, not authoritative.

### R4 — PII leakage across corpora (FERPA)
- **Impact:** Critical. Mixing end-user metadata (possible PII) with reference docs leaks PII into admin answers and blows retrieval relevance.
- **Mitigation:** **Three-corpus separation** (Operational / Configuration / Solution Documentation); Privacy Transformer (k-anonymity floor, pseudonymization, suppression) before any result reaches LLM context; Gates per group/perimeter. **No HIPAA/PCI ingestion**, by policy.
- **Residual:** Solution docs may contain PII in screenshots → their own hygiene pass.

### R5 — Identity, access & OnBase ACLs
- **Impact:** High. Institutional AI must be identity-aware; CogniBase must not let a user see what OnBase would deny them.
- **Mitigation:** **Entra ID (MSAL PKCE)** SSO; per-user isolation; **OnBase OAuth/AD identity passthrough — CogniBase cannot bypass OnBase ACLs**; audit logging on every access.
- **Residual:** Mapping CogniBase Groups to BU's identity model is a pilot task (Document 13/16).

### R6 — Deployment mismatch (local-first vs. EKS/ARM)
- **Impact:** Medium. CogniBase is local-first; BU runs EKS + Graviton (ARM64) + ArgoCD.
- **Mitigation:** Already Docker/compose; publish **ARM64 image + Helm chart**; front with APISIX. Dual packaging keeps the local-first edition (a differentiator) and adds the enterprise edition. (Documents 13.)
- **Residual:** ARM smoke-testing + Helm hardening — scoped, low-risk engineering.

### R7 — Open-source licensing (AGPL / SSPL) hygiene
- **Impact:** Medium. Some "open" components (Grafana/Loki = AGPL; MongoDB = SSPL) are unsafe to bundle into a product.
- **Mitigation:** **Two-edition design.** Bundle only permissive deps; keep AGPL backends **arm's-length/customer-provided** (emit OTLP, BYO dashboard); use **Postgres/JSONB** instead of MongoDB. (Document 13.)
- **Residual:** Counsel review of LICENSE/NOTICE manifests before any commercial release.

### R8 — Vendor lock-in vs. "freedom to leave"
- **Impact:** Medium. BU rejects lock-in as a selection criterion.
- **Mitigation:** Plain-file artefacts (schema.json, annotations, anchors as files); open table formats for lake emit; open exit demonstrated in the pilot. Portability is a *feature*, not a concession.
- **Residual:** None material — this is a design strength.

### R9 — Hallucinated answers / grounding gaps
- **Impact:** High. The model answers beyond its evidence.
- **Mitigation:** Retrieval-grounded prompts ("use ONLY provided context; cite sources; if insufficient, say so"); source-citation chips; numeric verifier re-executes calculations; refusal on insufficient context.
- **Residual:** Prompt/grounding tuning per corpus — ongoing, measured by audit pass rate.

### R10 — Data freshness / staleness
- **Impact:** Medium. Answers grounded on stale anchors mislead.
- **Mitigation:** Hygiene Pipeline with scheduled refresh, health probes (skip + alert on slow OnBase), multi-version anchors with timestamps; freshness surfaced to the user. (Document 9.)
- **Residual:** Cadence tuning per source against OnBase load.

### R11 — Scale & performance (2,300+ tables, large corpora)
- **Impact:** Medium. Index build and retrieval latency at institutional scale.
- **Mitigation:** pgvector with SQL filtering; per-corpus collections; caching/rate-limiting (Valkey pattern); incremental updates; nightly publisher to cut source load.
- **Residual:** Capacity sizing during the pilot.

### R12 — Neophyte over-trust (the human factor)
- **Impact:** High and often overlooked. The most dangerous failure is a *believable* wrong answer.
- **Mitigation:** UI makes **sanctioned vs inferred visible**; confidence and boundaries shown; "searched N sources" transparency; every claim links to provenance. The product is designed to *protect the non-expert*, not impress them.
- **Residual:** Training/onboarding for end users; an explicit "how to read an answer" guide.

### R13 — Coordination & credentials with BU's REST POC team
- **Impact:** Medium. Two teams on the same Hyland API; no contact/credentials = stall.
- **Mitigation:** "Coordinate, don't integrate" model; one shared IT credential request; clear ownership split (BU owns DocType inventory + credentials; CogniBase owns the OnBase domain layer). (Document 16.)
- **Residual:** Depends on BU naming a sponsor and issuing credentials — the gating signal.

### R14 — LLM cost governance
- **Impact:** Low–Medium. Uncontrolled model spend.
- **Mitigation:** Curated heterogeneity — route cheap/local models for routine work, frontier only when needed; token/latency metrics per conversation; cost transparency. (Document 12.)
- **Residual:** Budget thresholds set with BU.

### R15 — Miscalibrated confidence & feedback poisoning
- **Impact:** High. Using the model’s self-confidence as a review gate (it is uncalibrated), or letting user corrections auto-learn, can teach the system falsehoods at scale.
- **Mitigation:** Evidence-based confidence (not LLM self-confidence); corrections are **steward-ratified proposals**, not auto-absorbed; feedback authority tracks stewardship; thresholds change only on measured calibration and auto-tighten on drift. **Full treatment in Document 17.**
- **Residual:** Calibration must be measured per area before autonomy is raised.

## 3. Risk posture summary

| Severity | Risks | Net position |
|---|---|---|
| **Critical** | R1 (false correlation), R4 (FERPA PII) | Addressed by the trust layer (Doc 2) + corpus separation/Privacy Transformer — the core of the design |
| **High** | R2, R3, R5, R9, R12, R15 | Mechanisms exist; pilot retires the residuals |
| **Medium** | R6, R7, R8, R10, R11, R13, R14 | Engineering + coordination, low conceptual risk |

The pattern is deliberate: **the two Critical risks are exactly the two CogniBase was architected to solve** (governed correlation and corpus/PII separation). The remaining risks are the ordinary work of taking a capable system to institutional grade — which is what the pilot is for.

## 4. What would make us pause

Honest engagement means naming the conditions under which CogniBase should *not* proceed: no named data steward (the ontology needs an owner); a mandate to ingest HIPAA/PCI into the lake (out of policy); or a requirement to assert cross-source relationships without sanctioned keys (the one thing the design refuses to do). Each of these is a conversation, not a workaround.

> Cross-references: Document 2 (ontology), Document 6 (corpus), Document 7 (access/Gates→OPA), Document 8 (federation), Document 10 (provenance/audit/FERPA), Document 13 (deployment/licensing), Document 16 (coordination/pilot).

---
*Document 3 of 18 · Frame A (BU-vision-led) · CogniBase BU-Aligned Library v2 · generated 2026-06-28*

# CogniBase — Hygiene Pipeline & Scheduled Jobs

*Document 9 of 18 · BU-Aligned Library v2 · Renne Santiago*

---

## 1. What a hygiene job does

A scheduled job:
1. **Pulls** targeted data from OnBase via REST (one or more sub-queries — possibly federated).
2. **Runs** it through a configurable **Hygiene Pipeline** of steps.
3. **Materializes** the result as a versioned, gate-pinned **anchor**.
4. **Records** everything to the audit trail and run log.

Anchors — not live queries — are what the agent reasons over for operational data, so answers are reproducible and policy-bounded.

## 2. Why per-job hygiene + multi-version anchors

Different data needs different treatment, and the same source may appear at different transformation levels (raw / hybrid / fully anonymized) pinned to different Gates. Multi-version anchors let an admin question see masked data while an aggregate dashboard sees suppressed data — from one source, governed differently, each version timestamped.

## 3. Hygiene step library (representative)

| Step | Purpose |
|---|---|
| Normalize keys | Map source keywords to canonical entities (Normalizers) |
| PII detect + mask | Find and transform regulated fields before indexing |
| Deduplicate | Collapse repeated records on the sanctioned key |
| Validate / integrity-check | Reject malformed or out-of-contract rows |
| Embed | Vectorize for retrieval (pgvector) |
| Profile | Sample + classify for the value catalog |

Steps are admin-configurable per job; heavy steps run in the background, fast steps inline.

## 4. Scheduling & safety

- **Cadence** per job (cron via the scheduler), tuned to source volatility.
- **Health probe** → `GET /onbase/.../healthcheck`; if p95 latency exceeds threshold, **skip with a recorded reason and alert the admin** — never hammer a stressed OnBase.
- **Sequential job execution** (parallelism is *within* a job via `max_concurrent_rest`, not across jobs) to bound OnBase load; a nightly publisher cuts source load by ~90%.
- **Per-step timeout** to catch a hanging step (e.g., a flaky embed vendor).
- Hygiene runs on **every ingestion path**, not just scheduled — drag-drop imports get the same treatment.

### Learned items re-enter through hygiene

Steward-ratified corrections (Document 17) re-enter as versioned anchors through this same pipeline — a learned item is just a new sanctioned input with provenance, subject to the same hygiene, gating, and audit. Nothing is “learned” outside the governed path.

## 5. Alignment to BU

- **Dagster fit.** Each hygiene job maps cleanly onto a Dagster asset (BU's orchestrator in Cortex) — observable, retryable, lineage-tracked — should BU prefer to run pipelines on its own platform.
- **Freshness contract.** Anchor timestamps surface to the user; staleness is shown.
- **Audit.** Every run, skip, and transform is in the L1–L4 trail (Document 10).

> The hygiene pipeline is what keeps governed data **fresh without becoming unsafe** — the operational complement to the trust layer.

---
*Document 9 of 18 · Frame A · CogniBase BU-Aligned Library v2 · generated 2026-06-28*

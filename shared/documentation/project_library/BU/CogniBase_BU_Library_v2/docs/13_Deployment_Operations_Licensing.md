# CogniBase — Deployment, Operations & Licensing

*Document 13 of 18 · BU-Aligned Library v2 · Renne Santiago*

---

## 1. Two editions, one codebase

CogniBase ships as **edition profiles of a single codebase**, not two forks. Edition-variable seams (vector store, identity, telemetry, policy, gateway) use the same pluggable-adapter pattern as the LLM router:

| Edition | Target | Vector | Identity | Edge | Observability | Deploy |
|---|---|---|---|---|---|---|
| **Enterprise (Atlas)** | BU / institutions | pgvector | Entra ID (OIDC) | APISIX + OPA | OTLP → customer Grafana | Helm / EKS / ARM64 |
| **Neutral / Core** | commercial or free | pgvector/SQLite | OIDC/local | optional | OTLP only (BYO dashboard) | Desktop / Docker |

## 2. BU-grade hardening (the commercial-grade uplift)

Adopting BU's own permissively-licensed stack moves CogniBase from local POC to institutional product:
- **pgvector** (replaces ChromaDB) — ACID, concurrency, SQL filtering, backups; matches BU's Person/Course indices.
- **OpenTelemetry + Prometheus** instrumentation → traces/metrics/structured logs.
- **OIDC / Entra ID** (`authlib` already a dependency) — enterprise SSO.
- **APISIX** gateway (TLS, rate-limit, API-key consumers) + **OPA** for Gates.
- **External Secrets** — keys out of `settings.json`.
- **Helm + ARM64** image for Forge/Graviton.

## 3. Licensing hygiene (open-source done safely)

CogniBase follows BU's own rule — **permissive only, no copyleft bundled into the product**:
- **Bundle freely (permissive):** pgvector/Postgres, OpenTelemetry SDK, Prometheus client, APISIX, OPA, authlib, Valkey, Dagster/Prefect, Iceberg/Trino.
- **Arm's-length / customer-provided (AGPL):** Grafana/Loki/Tempo/Mimir — emit OTLP, BYO dashboard; never vendored. (Same separate-process discipline AutoPDF uses for GPL engines.)
- **Avoid (SSPL):** MongoDB → use **Postgres/JSONB** (which pgvector already brings in).

> The two-edition design lets BU's edition use the full open stack while the public edition stays legally headache-free — with no GPL/AGPL/SSPL in the shipped artefact.

## 4. Operations

- **GitOps** deploy (ArgoCD-compatible Kustomize/Helm); rollback via revision history.
- **Health probes** (liveness/readiness), HPA autoscaling, per-conversation metrics.
- **Secrets** via External Secrets Operator / Vault; no embedded credentials.
- **Backups** — pgvector + plain-file profile artefacts; portable by construction (freedom to leave).

> *Licensing note: counsel should confirm the LICENSE/NOTICE manifests before any commercial release. The internal contingency plan governs which deep IP is exposed.*

---
*Document 13 of 18 · Frame A · CogniBase BU-Aligned Library v2 · generated 2026-06-28*

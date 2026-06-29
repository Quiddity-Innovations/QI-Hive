# CogniBase — Access Model: Deny-by-Default & Gates → OPA

*Document 7 of 18 · BU-Aligned Library v2 · Renne Santiago*

---

## 1. Principle

Every layer adds intent, and **deny-by-default** is the rule whenever a layer is silent. The model is stacked so that "not explicitly allowed" always means "denied" — the posture BU enforces platform-wide with OPA.

```
Layer 5 — Privacy Transformer    (what the output may look like)
Layer 4 — Cross-Reference Gate   (who, where, how — policy)
Layer 3 — CrossLink              (which DocTypes may join — admin intent)
Layer 2 — Normalizer             (which keywords are the same — equivalence)
Layer 1 — DocType Constraint     (respect the .expk grouping — default)
```

## 2. The five layers

1. **DocType Constraint** — on `.expk` import, OnBase's grouping is honored as-is; no cross-cuts unless authorized above.
2. **Normalizer** — declares semantic equivalence (`AP_Name ≡ HR_Name ≡ OAD_Name → canonical:PersonName`); auto-discovered, **admin-confirmed**, or Excel-uploaded. This is where "are these the same entity?" is answered by a vetted rule, not a guess (Document 2).
3. **CrossLink** — admin-vetted joins between DocTypes (CogniBase's Normalizer-aware Custom Query); may reuse existing OnBase Custom Queries by ID.
4. **Cross-Reference Gate** — per CogniBase Group, per perimeter (User vs AI), declaring `source` (lake / live_rest / hybrid / deny) and `transform` (raw / anonymize / aggregate_only / deny), with field-level overrides.
5. **Privacy Transformer** — k-anonymity (k≥5 floor), pseudonymization, generalization, suppression on results **before** they reach LLM context or the user.

## 3. Mapping to BU: Gates → OPA, Groups → Entra

- **Gates as OPA policy.** Each Gate is expressible as a declarative Rego policy, so access decisions are externally auditable and enforced by BU's own engine rather than bespoke code — policy decoupled from application.
- **CogniBase Groups ↔ Entra ID.** Groups are decoupled from AD and bound to **Entra ID** identities (MSAL PKCE), giving per-user isolation and identity-aware access. CogniBase **cannot bypass OnBase ACLs** — OnBase OAuth/identity passthrough is authoritative.
- **Audit.** Every layer decision (allow/deny/transform) is written to the L1–L4 trail (Document 10) and can ship to BU's audit sinks.

### Feedback authority & learned items

Corrections enter the access model as **governed proposals**: anyone with access to an area’s data may **flag**, but only a designated **domain steward** may **ratify** a correction into a sanctioned Normalizer/CrossLink. Ratified items carry provenance and re-enter via the Hygiene Pipeline (Document 9). Authority tracks **stewardship, not mere data access** — the operational rule behind the learning loop (Document 17).

## 4. Why this matters for trust

The access model is not only a security control — it is half of the **anti-fabrication** design. Layers 2–3 decide *whether two things may be related at all*; Layers 4–5 decide *what may be shown*. Together they ensure the agent can neither invent a relationship nor over-disclose one. Security and truthfulness are enforced by the same stack.

> Deny-by-default is the quiet backbone of institutional trust: the system's default answer to "can these connect / can this be shown?" is **no**, until a named owner says yes.

---
*Document 7 of 18 · Frame A · CogniBase BU-Aligned Library v2 · generated 2026-06-28*

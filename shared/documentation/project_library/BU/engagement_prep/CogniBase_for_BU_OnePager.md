# CogniBase for Boston University
### The OnBase domain layer for your data & AI engineering teams
*Quiddity Innovations — draft brief (internal; becomes external when you choose to engage)*

---

**The problem.** BU runs Hyland OnBase across thousands of tables with no enforced foreign keys, cryptic names (`hsi.itemdata`), and configuration locked inside `.expk` packages. A team can build REST plumbing against the Hyland API quickly — but knowing *where the checks live*, *how AP invoices link to vendors*, and *which keyword types matter for which process* takes deep OnBase domain experience. That domain layer is the hard part.

**What CogniBase is.** A vendor-neutral, local-first OnBase intelligence tool that combines:
- **Schema map** — full OnBase schema (live via Unity/REST or from `.expk`), with inferred relationships (a prior run produced 34 manual-derived + 6,167 inferred soft FKs).
- **Three-corpus RAG** — Operational Data / OnBase Configuration / Solution Documentation kept separate so PII never leaks into admin answers.
- **Query Federator** — joins across prefix-aliased keyword types (`AP_Name` vs `HR_Name`) that OnBase Custom Queries cannot.
- **Pluggable LLMs** — Claude, OpenAI, Gemini, or local Ollama; checkbox-active, zero hardcoded.
- **Compliance by construction** — five-layer access model, k-anonymity floor, Privacy Transformer, and an L1–L4 audit trail.

**Why it fits BU's architecture (the price of entry — already met or in progress):**

| BU requirement | CogniBase |
|---|---|
| Open standards, MCP-native | RAG today; **MCP tool wrapper** in progress (natively callable by Nexus/Regent) |
| No per-seat, freedom to leave | Plain-file artefacts; open exit |
| Identity-aware & auditable (Entra ID) | L1–L4 audit today; Entra ID adapter planned |
| FERPA guardrails | Gates + Privacy Transformer; regulated data never leaves the box |
| Cloud-native / ARM / K8s | Docker today; ARM64 + Helm planned |

**How we'd work together.** Coordinate, don't duplicate. Your REST POC team owns departmental DocType inventory and credentials; CogniBase brings the OnBase domain modelling, Normalizers, Gates, Query Federator, and the agent/RAG layer on top of the same Hyland API. Forward-deployed, lean, embedded.

**The shape of a first step.** One IT request issues credentials usable by both teams against a shared OnBase **test** instance. We demonstrate a real cross-DocType question answered via the Query Federator. No licence, no lock-in, pilot first.

**Differentiation.** This is the operational / IT-data / records domain — complementary to, not competing with, an admissions-focused frontier partner.

---
*Contact: Renne Santiago, Quiddity Innovations — quiddityinnovations.com*

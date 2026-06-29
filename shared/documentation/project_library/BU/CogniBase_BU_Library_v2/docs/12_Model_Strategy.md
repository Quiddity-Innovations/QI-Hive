# CogniBase — Model Strategy & Curated Heterogeneity

*Document 12 of 18 · BU-Aligned Library v2 · Renne Santiago*

---

## 1. Principle: no single bet

CogniBase shares BU's stated commitment to **curated heterogeneity** — multiple models, chosen per task on fit, cost, capability, and freedom to leave. The LLM is a **pluggable component behind a vendor router**, never hardcoded. Swapping or adding a provider is a config change.

## 2. The provider interface

A single `VendorRouter` fronts concrete adapters with a uniform `chat()` / `embed()` contract:

| Adapter | Use |
|---|---|
| `claude` | Frontier reasoning, synthesis |
| `openai` | Alternate frontier / embeddings |
| `gemini` | Alternate frontier |
| `ollama` | Local, regulated, zero-egress |
| `openai_compatible` | LM Studio / llama.cpp / vLLM / any OpenAI-compatible server |

Adapters are checkbox-active and multi-active; keys live outside code (Document 13).

## 3. Mapping to BU's providers

BU runs models through **AWS Bedrock** (Claude) and **Azure OpenAI** (GPT), with Gemini planned. CogniBase's router targets the same providers through their endpoints, so model governance stays in BU's hands:

| BU path | CogniBase adapter |
|---|---|
| Claude via Bedrock (IAM) | `claude` / `openai_compatible` to the Bedrock endpoint |
| GPT via Azure OpenAI (key) | `openai` to the Azure deployment |
| Local / regulated | `ollama` / `openai_compatible` |

## 4. Routing economics (efficiency by design)

Not every task needs a frontier model. CogniBase routes **cheap/local models for routine work** (schema explanation, classification, draft retrieval) and **frontier models only where reasoning demands it** (cross-source synthesis, ambiguous questions). Per-conversation **token + latency metrics** make cost transparent and tunable — aligning with BU's per-school cost-transparency goal.

## 5. Why this matters for trust

Model heterogeneity also reduces single-model blind spots: a sanctioned correlation can be **cross-checked across providers**, and the numeric verifier (Document 10) re-executes calculations independent of any one model's confidence. Diversity is a correctness tool, not just a procurement stance.

> The model is the most replaceable part of CogniBase by design. The durable value is the **ontology, governance, and provenance** around it — which is exactly where BU wants its institutional investment to sit.

---
*Document 12 of 18 · Frame A · CogniBase BU-Aligned Library v2 · generated 2026-06-28*

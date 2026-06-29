# CogniBase — Confidence, Human-in-the-Loop Review & Continuous Learning

*Document 17 of 18 · BU-Aligned Library v2 · Renne Santiago*
*The adaptive trust loop: confidence thresholds, governed correction, and domain-by-domain maturation.*

---

## 1. Why this document

Document 2 establishes a **static** discipline: a correlation is trustworthy only if a governed ontology sanctions it; everything else is *inferred and unverified.* This document makes that discipline **adaptive** — it adds a confidence-graded review queue and a governed learning loop so the system improves with use and **earns more autonomy in an area only after it has demonstrably learned that area's business.** The design borrows two proven precedents and corrects for where AI differs from them.

## 2. The precedents — and their limits

| Precedent | Mechanism we borrow | Where AI differs (the correction) |
|---|---|---|
| **OCR / ICR capture** | A confidence score routes low-confidence items to a human verification queue; corrections feed back | OCR confidence is calibrated against pixels; **LLM self-confidence is not calibrated** — a model can be fluently confident and wrong |
| **Translation memory / adaptive MT** | Senior-translator post-edits become reusable "learned" assets | A bad learned phrase is cheap; a wrongly **learned relationship propagates fabrication at scale** |

**Conclusion:** adopt the confidence-gated review + learning loop, but (a) gate on **evidence-based** confidence, not the model's self-assessment, and (b) make every learned item a **governed, steward-ratified proposal**, not an auto-absorbed fact.

## 3. The confidence model (evidence-based, not self-reported)

Confidence is a **composite of structural signals**, never the LLM's own "I'm sure":

- **Key strength** — was the entity resolved on a vetted canonical key, and how complete/unique is it?
- **Sanctioned-edge presence** — does a CrossLink/Normalizer authorize this join at all? (binary gate)
- **Source corroboration** — how many independent sources agree?
- **Grounding density** — citation count and retrieval score behind the claim.

These roll up into **bands**, each with a configurable threshold **per data area**:

| Band | Meaning | Default disposition |
|---|---|---|
| **Verified** | Sanctioned edge + strong key + corroboration | Auto-accept, logged |
| **Probable** | Sanctioned edge, weaker evidence | Auto-accept above area threshold; else queue |
| **Inferred** | No sanctioned edge; pattern only | Never authoritative; labeled; queue for steward |
| **Unsupported** | Fails grounding | Withheld; refusal or "insufficient evidence" |

## 4. The review queue & reviewers (tiered)

Items below an area's threshold enter a **review queue**. Reviewers are tiered so AI handles scale and humans hold ground truth:

| Reviewer | Role | Authority |
|---|---|---|
| **Inspector agent** | Consistency & policy checks — does this contradict an existing sanctioned edge? violate a Gate? | Flags / blocks; cannot ratify new truth |
| **Librarian agent** | Provenance, deduplication, and placement — where does this belong, what does it cite, is it redundant? | Annotates / routes; cannot ratify |
| **Domain steward (human)** | Ratifies, rejects, or edits the proposed item | **Sole source of ground truth** until calibration is proven |

AI agents **augment, never replace** the steward — avoiding an AI-certifies-AI loop where both are confidently wrong.

## 5. The learning loop (governed)

A correction is a **proposal**, not an immediate truth:

```
Flag/correction  →  Inspector+Librarian triage  →  Steward ratifies
   →  becomes a sanctioned item (Normalizer / CrossLink / annotation)
   →  carries provenance: who proposed, who ratified, when, on what evidence
   →  re-enters via the Hygiene Pipeline (Document 9), versioned
```

Deny-by-default is preserved: an un-ratified proposal changes nothing. This is the translation-memory idea **with governance bolted to its front** — it captures expert knowledge without letting a single mistaken or malicious correction teach the system a falsehood (**feedback-poisoning** defense).

## 6. Domain-by-domain maturation (changing the levels — safely)

Confidence thresholds are **per data area**, and they move with evidence:

1. **Cold start:** high review rate; most non-Verified items queued.
2. **Calibrate:** measure, per area, **human-agreement rate** and **audit pass rate** on reviewed items.
3. **Mature:** once an area's calibration clears a target over a sustained sample, **raise the threshold** so fewer items need review — the system has demonstrably *learned that business*.
4. **Monitor drift:** keep sampling; if agreement later drops, **auto-tighten** the threshold again. Maturation is reversible, never permanent.

This is the disciplined version of your "once the business is well-learned, change the confidence levels" — driven by measured calibration, not by feeling.

## 7. Per-area agents & scoped user feedback

- **Per-area agents** — a dedicated review agent per data domain (Financial Aid, Advancement, Facilities, HR…), each tuned to that area's entities, keys, and gates.
- **Scoped feedback** — users with **role/stewardship** in an area submit corrections that enter the governed loop. Authority is tiered, **not** equal to data access: *anyone with access may flag; a designated steward ratifies.* This mirrors the "senior translator" weighting — the people who own the business meaning are the ones whose corrections become truth.

## 8. Guardrails (the four rules)

1. **Evidence-based confidence only** — never gate on LLM self-confidence.
2. **Governed learning** — corrections are steward-ratified proposals; deny-by-default preserved.
3. **Authority by stewardship** — flag rights ≠ ratify rights.
4. **Data-driven, reversible thresholds** — raise on measured calibration; auto-tighten on drift.

## 9. Metrics (extends Document 2 §7 and Document 10)

- **Calibration error** per area — does "Probable" actually mean what its threshold claims?
- **Human-agreement rate** — % of agent/auto decisions a steward upholds.
- **Review-queue volume & SLA** — load and turnaround per area.
- **Learned items ratified vs. rejected** — and the rejection reasons (a healthy non-zero rejection rate proves the gate works).
- **Threshold-by-area + drift alerts** — current autonomy level per domain and any auto-tightening events.

## 10. Worked example (BU)

**Financial-Aid document classification + enrollment correlation.**
- *Cold start:* every non-Verified classification and every FA-doc⇄SIS correlation below threshold is queued. The Inspector agent checks each against existing sanctioned edges; the Librarian agent attaches provenance; the **FA office steward** ratifies.
- *Learning:* the steward corrects a recurring mis-classification; once ratified it becomes a sanctioned annotation with provenance and re-enters via hygiene.
- *Maturation:* after a sustained sample shows ≥ target human-agreement, CogniBase **raises the FA-area threshold** — routine items now auto-accept, freeing the steward for edge cases.
- *Drift:* a new FA form layout drops agreement; the monitor **auto-tightens** the threshold and re-queues until the steward teaches the new pattern.

## 11. Summary

Confidence-gated review turns CogniBase's trust layer from a fixed rule into a **system that learns a business and earns autonomy in it** — without ever surrendering the guarantee that a *believable* answer is also a *governed* one. It is your OCR/translation-memory instinct, corrected for the one way AI is different: **the machine's confidence is not evidence — the evidence is.**

> Cross-references: Document 2 (ontology/trust), Document 3 (R15 confidence/feedback risk), Document 7 (feedback authority), Document 9 (learned items via hygiene), Document 10 (provenance & calibration in audit).

---
*Document 17 of 18 · Frame A · CogniBase BU-Aligned Library v2 · generated 2026-06-28*

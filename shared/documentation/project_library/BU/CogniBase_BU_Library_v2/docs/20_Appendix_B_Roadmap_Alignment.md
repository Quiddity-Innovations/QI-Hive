# CogniBase — Appendix B: Alignment to BU's 2026 Roadmap (Four Lanes)

*Appendix B · BU-Aligned Library v2 · Renne Santiago*
*CogniBase is not a net-new initiative competing for budget — it advances items already on BU's funded 2026 roadmap. This appendix crosswalks CogniBase to each lane.*

---

## B.1 Why this appendix

The strongest argument to a sponsor is not "fund something new" — it is **"fund something that accelerates work you have already prioritized."** BU's 2026 roadmap is published in four lanes: **AI Engineering, Data Engineering, Enterprise Architecture, and Essential Services.** This appendix maps CogniBase onto specific line items in each, with an honest read of where the fit is strong and where it is only supporting.

> *Source note: roadmap items are taken from BU's published AI & Data Engineering roadmap (four-lane crawl, 2026-06-27). The live roadmap is a tabbed, evolving page — these mappings should be re-confirmed against it before any proposal.*

## B.2 Fit at a glance

| Lane | CogniBase fit | Why |
|---|---|---|
| **AI Engineering** | ★★★ Strongest | "Ontology Investigation" is practically a CogniBase brief; MCP-native; document AI |
| **Data Engineering** | ★★★ Strong | Lake ingestion + semantic layer + catalog + profiling all have CogniBase/MapSnap roles |
| **Enterprise Architecture** | ★★ Strong & concrete | Work-order/asset, SIS/Jenzabar/mainframe migration, Huron, OpenClaw, IAM |
| **Essential Services** | ★ Supporting only | Legacy ADW/BI/DBA ops — CogniBase assists migrations, isn't central (stated honestly) |

## B.3 Lane 1 — AI Engineering (strongest fit)

| Roadmap item | How CogniBase advances it | Library ref |
|---|---|---|
| **Ontology Investigation** | CogniBase's governed ontology — Normalizers/CrossLinks, sanctioned correlation, knowledge-graph feed — *is* an ontology investigation, grounded in OnBase + the systems federation | Docs 2, 15, 18 |
| **TerrierAI Assistant Pilot (OpenClaw)** | CogniBase registers as an MCP tool the OpenClaw-based Assistant calls for OnBase questions | Doc 11 |
| **Migrate to MCP Gateway / MCP Gateway (infra)** | CogniBase publishes to the `mcp-gateway-registry`; native, governed tool surface | Docs 11, 14 |
| **TerrierAI Studio (document/data processing)** | Document intelligence + RAG over OnBase with citations and audit | Docs 5, 10 |
| **AI Code Generation – Data Engineering / Claude Code** | MapSnap + CogniBase schema discovery accelerates pipeline/code generation | Appendix A |
| **Consulting Partner AI Landscape/Roadmap Review** | The named, RFP-shaped entry point for this engagement | Doc 16 |

## B.4 Lane 2 — Data Engineering (strong fit)

| Roadmap item | How CogniBase advances it | Library ref |
|---|---|---|
| **Lake ingestion targets** (Campus Solutions/SIS, SAP, Kuali, Huron, Blackbaud, StarRez, 25Live, Slate, Destiny One…) | CogniBase emits curated OnBase entities to Cortex; **MapSnap onboards the structured sources and proposes canonical keys** | Docs 15, 18; Appendix A |
| **Automated xForm Processing · Data Profiling · Data Validation** | AutoPDF capture/extract + CogniBase hygiene pipeline (profiling, PII detection, validation) | Doc 9; Appendix A |
| **Insights: Cube Semantic Layer POC · Strategic KPIs Layer** | CogniBase's sanctioned relationships & canonical terms feed Lexicon/Cube | Doc 15 |
| **Infrastructure: OpenMetadata Catalog** | CogniBase provenance/lineage aligns with the catalog; learned items carry source + steward | Doc 10 |
| **TerrierData Connect (move off SnapLogic) · BU Message Bus** | Not CogniBase's job — but its open-standards, event-friendly posture complements rather than competes | Docs 4, 13 |

## B.5 Lane 3 — Enterprise Architecture (strong, concrete fit)

| Roadmap item | How CogniBase advances it | Library ref |
|---|---|---|
| **Work Order & Asset Management** · **FacilitiesOS** | Governed correlation across the facilities cluster (CAMMS/PMWeb/25Live/FMS) + OnBase facilities docs | Doc 18 |
| **SIS Stabilization · Jenzabar Retirement · Mainframe Archive** | MapSnap schema archaeology turns undocumented legacy schemas into plain-English, join-aware maps for migration | Appendix A |
| **Huron IRB · Huron Grants** | Research-admin document correlation — Tier-B/C bounded (gated; IRB excluded) | Doc 18 |
| **OpenClaw AI Assistant** | CogniBase as the governed OnBase tool behind the Assistant | Doc 11 |
| **RightCrowd PIAM · SIS IAM** | Identity alignment on **BUID / Entra ID**; CogniBase honors OnBase ACLs and the persona model | Docs 7, 18 |
| **(OnBase — the ECM beneath many of these)** | CogniBase's home; the layer that makes OnBase content institutional knowledge | All |

## B.6 Lane 4 — Essential Services (supporting only — stated honestly)

This lane is traditional data-warehousing, BI-platform, and database-administration operations (ADW enhancements, MicroStrategy migration/re-licensing, *Evaluate CoPilot for Power BI*, mainframe→SQL/Coldstore archive, SQL Server upgrades). **CogniBase is not central here**, and the document should not pretend otherwise. Its only honest roles are:

- **Migration assistance** — MapSnap mapping legacy ADW / MicroStrategy / mainframe schemas during rehost and archive work.
- **A forward direction** — CogniBase's governed semantic layer is the modern, AI-native counterpart to the legacy BI stack BU is migrating — a *destination*, not a like-for-like replacement.

Claiming more than this in Lane 4 would be exactly the kind of overstated affinity the rest of this library argues against.

## B.7 Summary

CogniBase maps **most strongly to AI Engineering** (where *Ontology Investigation* is practically its charter), **concretely to Data Engineering and Enterprise Architecture** (lake ingestion, semantic layer, facilities/asset, legacy-migration archaeology, OpenClaw, IAM), and is **supporting-only in Essential Services.** The sponsor's takeaway: funding CogniBase advances roughly a dozen items *already on BU's prioritized roadmap* — it is an accelerator of the plan, not an addition to it.

## B.8 A tandem-development reading

Because these are *shared* objectives, the natural way to pursue them is **together.** The lane items above double as a **co-development backlog** — Ontology Investigation, Studio Foundation, Agent Workflow POC, the facilities/work-order correlation, and the lake/semantic feeds are all candidates for a governed tandem build in which **BU owns the institution-specific ontology and CogniBase contributes the licensed engine.** See **Document 16 §7 (Co-Development Model)** for the ownership split and how co-development de-risks a lean vendor through skills transfer.

> Cross-references: Document 1 (vision alignment), Document 16 (pilot, engagement & co-development), Document 18 (systems federation), Appendix A (MapSnap/AutoPDF tandem).

---
*Appendix B · Frame A · CogniBase BU-Aligned Library v2 · generated 2026-06-28*

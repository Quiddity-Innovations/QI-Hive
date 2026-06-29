# CogniBase — BU Systems of Record: Affinity & Extension Map

*Document 18 of 18 · BU-Aligned Library v2 · Renne Santiago*
*BU is not one database — it is a federation of domain systems of record. Where CogniBase can responsibly extend, and where it must not.*

---

## 1. Why this document

The rest of this library focuses on OnBase, because that is CogniBase's home and BU's largest unstructured content store. But OnBase is one node in a wide federation: BU runs **dozens of authoritative systems of record**, each owning a domain. A sponsor evaluating CogniBase will rightly ask, *"This is about more than OnBase — how does it relate to our other systems, and which ones should it touch at all?"* This document answers that with three things: a **map** of BU's major systems of record, an **affinity model** of the entities they share, and an **inclusion test** that decides — under the same governed-correlation discipline as Document 2 — which extensions are valuable, which are policy-bounded, and which are forbidden.

The governing rule carries straight over: **shared subject matter is not permission to join.** High affinity between two systems is a reason to *consider* a sanctioned relationship, never to *assume* one.

## 2. BU's systems of record — two layers

BU's systems of record divide into two complementary layers: an **identity & persona backbone** that masters *who someone is*, and the **domain application systems** that master *what they do* in each area. CogniBase must resolve a person against the first before it dares correlate across the second.

### 2.1 Identity & persona backbone (the master layer)

| System | Owner | Authoritative for |
|---|---|---|
| **Person Identity** | IS&T — Identity & Access Management (IAM) | The master **BU ID Number (BUID)** — the one canonical person key |
| **Person Registry** | IS&T — IAM | Person attributes synthesized across systems (including gender-affirming attributes) |
| **Affiliates Database** | IS&T — IAM | The **Affiliate persona** — uncompensated guests with validated access (vendors, volunteers, visiting researchers) |
| **Analytical Services & Institutional Research (AS&IR)** | AS&IR | The **source-of-record *rules*** — which system is authoritative for which demographic / bio-demographic attribute |

**The persona model.** One human is addressed simultaneously through several **personas** — *Student* (MyBU / Registrar), *HR* (BUworks/SAP — active faculty/staff, emeriti, retirees), and *Affiliate* (Affiliates DB) — each mastered by a different system but unified by one **BUID**. This is the real-world reason CogniBase resolves people on the BUID and never on a name: *a vendor who is also an employee is one BUID wearing an Affiliate persona and an HR persona* — provable by identity, not inferable by string match (cf. Document 2, Example 1).

**AS&IR is BU's existing source-of-record authority.** It already defines which system is authoritative for which attribute. CogniBase's Normalizers and CrossLinks should **inherit and defer to AS&IR's source-of-record rules**, and AS&IR — with domain stewards — is the natural ratifier of CogniBase's sanctioned relationships (Document 17). BU already has the governance body the trust layer needs.

### 2.2 Domain application systems of record

| Domain | System(s) of record | Role |
|---|---|---|
| **Student records / enrollment** | **MyBU Student** — Oracle PeopleSoft *Campus Solutions* (replaced the 40-year mainframe SIS / Student Link; ~11M records migrated) | Admissions, financial aid, records, curriculum, financials, advising |
| **HR / Finance / Procurement** | **BUworks** — *SAP* (Finance, HCM/HR, Procurement, Reporting); MyBUworks UI | Employee, payroll, vendor, purchasing, GL |
| **Admissions** | **Slate** (+ Salesforce applicant, Liaison) | Inquiry → matriculation |
| **Housing / residence** | **StarRez** | Housing applications, assignments |
| **Advancement / alumni / donors** | **Blackbaud CRM** (system of record) + iModules Encompass + EverTrue | 360° constituent: biographical, gifts, education, scholarships, events |
| **Research administration** | **Kuali Research** (proposals/awards; Negotiations for industry contracts); **Huron** Grants & Agreements + COI; **INSPIR II** (IRB human-subjects) | Grants, agreements, compliance — *Kuali interfaces with SAP* |
| **Facilities / campus operations** | **CAMMS** (maintenance & work-order central DB); **PMWeb** (capital projects); **25Live Pro** (room/event scheduling); **FMS: Workplace** (space) | Buildings, assets, work orders, space, projects |
| **Library / archives** | **Ex Libris Alma** (library management); **ArchivesSpace** (finding aids); **BU Digital Library**; Gotlieb Archival Research Center (University Archives) | Holdings, archival description, digitized heritage |
| **IT service management** | **ServiceNow** (primary ITSM; the TechWeb portal) | Tickets, knowledge, service catalog |
| **Document / content management (ECM)** | **Hyland OnBase** — *integrates across student, advancement, HR/finance, and research-admin systems* | The cross-cutting document layer — **CogniBase's home** |
| **Learning** | **Blackboard** (LMS); Course Catalog / Bulletin | Courses, sections, content |
| **Other domain systems** | WordPress (web/CMS), CS Gold (campus card/access), Parchment (transcripts), TerraDotta (study abroad), Handshake (careers), Accommodate (disability) | Domain-specific |
| **Research computing** | **Research Computing Infrastructure / Management Systems** (IS&T Research Computing) | HPC access, account provisioning, research-environment authorizations |
| **Professional / non-degree** | **Destiny One** (Center for Professional Education) | Independent SoR for non-degree professional enrollments & credentials |
| **Authentication** | **Entra ID** (Azure AD) / Kerberos | Sign-on — the *identity master* is **Person Identity / BUID** (see §2.1) |
| **Legal / General Counsel** | *No single contract-management system identified publicly.* Contracts appear distributed across **Kuali Negotiations** (research), **SAP** (procurement), and **OnBase** (document storage) — **to be confirmed with BU.** | Contracts, legal records (privileged) |

> *Note on accuracy: this map is compiled from BU's public IS&T/TechWeb materials and the AIDA dossier; it should be ratified against BU's own application portfolio before any pilot scopes a system. The legal/contract layer in particular is an open question to confirm with the Office of the General Counsel.*

## 3. OnBase is already the cross-cutting seam

The single most important fact for CogniBase's extension story: **OnBase is not a domain silo — BU already runs it across student, advancement, HR/finance, and research-administration systems** as the shared document layer. CogniBase, which masters OnBase, therefore *already sits at the seam* between these systems of record. Extending CogniBase to correlate across them is not a leap into unrelated territory — it is following document relationships OnBase already maintains, and making them governed, semantic, and auditable.

## 4. The affinity model — the entities these systems share

Systems of record connect through a small set of **shared entities**. These are the *only* legitimate join surfaces; everything else is coincidence.

| Shared entity | Appears in | Sanctioned join key |
|---|---|---|
| **Person** (universal) | MyBU (student), SAP (employee), Slate (applicant), Blackbaud (donor/alum), Kuali/Huron (PI), StarRez (resident), **Affiliates DB** (vendor/guest), CS Gold (cardholder) | **BUID** — mastered by **Person Identity** (IAM), distributed with 400+ attributes via the Person Broker/CDM — *never name or email* |
| **Space / Building / Asset** | CAMMS, PMWeb, 25Live, FMS: Workplace, OnBase facilities docs | Facilities asset / building / space ID |
| **Course / Curriculum / Section** | MyBU, Blackboard, Course Catalog | Course/section ID |
| **Award / Grant / Protocol** | Kuali, Huron, INSPIR, SAP | Award / protocol number |
| **Constituent / Gift / Fund** | Blackbaud, SAP financials, scholarships (→ student) | Constituent / fund ID |
| **Document** (overlay) | OnBase across all of the above | DocType + keyword → canonical entity |

Each system maintains its **own ID space.** "Person" in MyBU and "Person" in Blackbaud are the *same human* only when a validated identifier says so — the exact entity-resolution discipline of Document 2. This is why affinity is an invitation to model a relationship, not a license to assume one.

## 5. The inclusion test — which systems CogniBase should touch

Affinity is graded into three tiers, applied through the access model (Document 7) and the trust layer (Document 2):

### Tier A — Natural synergy (governed correlation is valuable)
OnBase documents ⇄ **MyBU** (student records), ⇄ **SAP** (AP/procurement), ⇄ **Kuali/Huron** (grant files); the **facilities cluster** (CAMMS ⇄ PMWeb ⇄ 25Live ⇄ FMS) ⇄ OnBase facilities docs. These share clean entities and clear business questions ("show invoices over $10k stuck in approval," "which facilities work orders have signed-off completion docs"). **Start here.**

### Tier B — Policy- and ethics-bounded (possible, but gated)
**Advancement (Blackbaud) ⇄ student records**, and **admissions ⇄ enrolled records.** The entities relate, but FERPA and ethical-fundraising boundaries apply — a donor's gift history must not leak into a student-services answer, and vice versa. Permitted *only* through an explicit Gate with a recorded agreement and a domain steward (Documents 7, 17).

### Tier C — Excluded / out of scope
**INSPIR / IRB human-subjects**, **Student Health** (HIPAA — CogniBase does not ingest HIPAA data), **Accommodate** (disability), and **privileged legal records** (attorney-client privilege). These are deliberately outside CogniBase's reach; high affinity does not override regulatory or privilege boundaries.

> The inclusion test is the federation-scale version of the trust thesis: the more systems are in play, the more tempting a fluent-but-false cross-system analysis becomes, and the more important it is that **every cross-system join is sanctioned, keyed, gated, and audited.**

## 6. Phased extension (sponsor-friendly)

1. **OnBase-centric (pilot):** prove governed correlation *within* OnBase and to one adjacent Tier-A system (e.g., MyBU).
2. **Tier-A federation:** add SAP and the facilities cluster as sanctioned, sponsored use cases arise.
3. **Semantic feed:** contribute resolved entities and sanctioned relationships into BU's Lexicon / enterprise knowledge graph (Document 15).
4. **Tier-B only on demand:** never speculatively — only with a sponsor, a steward, a Gate, and a recorded agreement.

Each phase is gated on a *named sponsor and a real question*, never on technical possibility alone.

## 7. Summary

BU is a federation of domain systems of record — MyBU/Campus Solutions for students, SAP for finance and HR, CAMMS and its siblings for facilities, Alma and ArchivesSpace for the library and archives, Kuali and Huron for research, Blackbaud for advancement, ServiceNow for IT — with **OnBase already threaded across many of them** as the document layer. CogniBase's opportunity is to turn those existing document relationships into **governed, semantic, auditable correlations** — and its discipline is knowing that **the entities these systems share are an invitation to model a relationship, never a permission to assume one.** That is what lets CogniBase scale across BU's systems without scaling the risk of fabricated insight.

> Cross-references: Document 2 (governed correlation), Document 7 (Gates/access), Document 15 (lake & knowledge graph), Document 17 (confidence & stewardship).

---
*Document 18 of 18 · Frame A · CogniBase BU-Aligned Library v2 · generated 2026-06-28*

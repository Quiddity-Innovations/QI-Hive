# Digitization Cost Comparison Tool — Document Imaging Pricing Calculator

## What is the Digitization Cost Tool?

The Digitization Cost Comparison Tool is a single-file, client-side web application built by **Quiddity Innovations** for **Boston University's Document Imaging & Services (OnBase)** team. It estimates and compares what it costs a BU department to digitize its physical records three different ways, side by side, and produces a clean, signed budgetary report.

Everything runs in the browser from one `index.html` file — no server, no database, no internet, and no installation. A department enters its records profile (boxes, pages, condition, indexing depth), and the tool instantly computes line-item costs and a calendar timeline for each of three approaches, highlights the cheapest, and generates a print-ready PDF report.

## The Problem It Solves

- Departments have no easy way to see what digitizing their records actually costs before committing budget.
- The current two-step "hybrid" practice (scan with a vendor, then index into OnBase later) hides duplicated effort and rework that make it more expensive than it looks.
- Document Imaging & Services needed defensible, source-backed evidence that scanning **directly into OnBase in-house** usually saves time and money.
- Vendor quotes are slow to obtain; a planning-level estimate is needed up front for the budget conversation.

## The Three Scenarios

| Scenario | Approach |
|---|---|
| **A — Vendor Full Service** | A commercial scanning bureau (SecureScan / Emerald / Record Nations class) performs every step off-site; BU only procures, manages, and imports into OnBase. |
| **B — Hybrid (Two-Step)** | A per-service matrix lets you assign each task (prep, scan, index, OCR, storage...) to the 3rd party or to BU students. Files land outside OnBase first, so a second project (DRIP import + indexing) is always required. Models today's two-tier PaperVision practice. |
| **C — In-House Direct-to-OnBase** | Students prep, scan, and index in a single pass directly into an OnBase scan queue — one project, no share folder, no second indexing pass. |

All three are always calculated on the identical page volume and document profile, so the comparison is apples-to-apples.

## How It Works

The tool reads a records profile and a configurable rate table, then computes each scenario as a sum of itemized line items. Vendor-assigned work is priced at per-page / per-trip market rates; BU-assigned work is priced as `student-hours x wage`, where hours are derived from page volume and throughput planning factors. Monthly items (capture software, scanner rental, hosted/box storage) are charged for the months the relevant phase runs. An effective cost-per-page and a calendar duration are derived for each scenario, with a budget check and a "best value within budget" recommendation when a budget is entered.

A key teaching point is baked in: because student labor is billed by the hour and the hours are fixed by volume, **adding students does not raise the total** — it just shortens the timeline and the per-student load. A staffing-sensitivity table (1-5 students) demonstrates this live.

## Who Uses It?

| Role | How they interact |
|---|---|
| **Departments / Requestors** | Enter their records profile and read the comparison; receive the signed PDF report. |
| **Document Imaging & Services staff** | Maintain unit rates and preparer list behind a password-gated Configuration tab; sign the report. |
| **BU IS&T** | Holds the enterprise OnBase license — shown as an explicit $0 line in every scenario. |

## Current Build Status (June 2026)

This project is **complete** — a finished, deliverable tool. It ships with three Word documents (User Guide, Technical Documentation, Deployment Guide) and a packaged distributable zip.

| Area | Status |
|---|---|
| Three-scenario cost model (A / B / C) | ✅ Live |
| Records profile inputs (boxes, pages, condition, indexing, OCR, destruction) | ✅ Live |
| Per-document and per-bundle index basis | ✅ Live |
| Hybrid per-service "who performs what" matrix | ✅ Live |
| Live results: cost cards, savings banner, comparison bars, timelines | ✅ Live |
| Staffing sensitivity (adding students shortens time, not cost) | ✅ Live |
| Budget check + best-value recommendation | ✅ Live |
| Signed, paginated, print-to-PDF report | ✅ Live |
| Editable rate table + preparers (Configuration, password-gated) | ✅ Live |
| Export / import config (JSON) and rates (CSV) | ✅ Live |
| localStorage persistence with in-memory fallback | ✅ Live |
| BU-internal vs public build toggle (presentation only) | ✅ Live |
| Embedded User Guide + Technical Reference | ✅ Live |
| Packaged distributable (index.html + docs + zip) | ✅ Live |
| Migration to a C:\ QI standard project root | 🗓️ Planned — still under Downloads |
| QI Brain / ecosystem integration | 🗓️ Planned — standalone today |

## Honest Scope Notes

- The Configuration **password is a convenience gate, not security** — the tool holds no sensitive data, and the `BU_INTERNAL_ONLY` flag is a presentation label, not authentication. Real BU-only access depends on where the file is hosted.
- Figures are a **budgetary estimate, not a quote.** Throughput, internal-effort hours, rework %, and timelines are Document Imaging & Services planning factors that should be calibrated against real project history.
- The PaperVision capture-software default ($240/mo) is an assumption — capture licensing is quote-only and should be replaced with BU's real contract cost.

---
*This page is editable at `C:\Users\renne\Downloads\DIGITIZATION COSTS\INTRO\status_intro.md` — save and click Refresh to update.*

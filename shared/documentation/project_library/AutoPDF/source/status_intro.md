# AutoPDF — Local-first PDF toolkit: convert, split, extract, catalog — no cloud

## What is AutoPDF?

AutoPDF is a self-contained, Windows-first PDF toolkit by Quiddity Innovations. It runs entirely on the local machine: a tiny PowerShell HTTP server (bound to `127.0.0.1:6969`) hosts a single-page browser UI and a JSON `/api/*` surface. Document processing is done by bundled open-source engines (Ghostscript, Poppler, Tesseract, Tabula, PDFtk, a bundled Java runtime). Optional intelligence comes from a **local** Ollama instance — there is no OpenAI, Anthropic, or Gemini integration, and no telemetry.

The deliberate design choice is "copy a folder, double-click `AutoPDF.exe`, done": no installer, no service to register, no admin elevation, no Python runtime, no front-end build step. Every path is relative, so the whole tool is portable across machines and USB sticks.

## The Problem We Solve

- Office workers and records teams need to **convert** mixed piles of Office files, images, text, and Markdown into clean PDFs — in bulk, not one file at a time.
- A scanned stack often arrives as **one giant PDF of many documents** that must be split back into individual files by rules (zones, patterns, bookmarks, page ranges).
- The same metadata (invoice number, party name, dates) must be **extracted from every document into a CSV/XLSX index** for ingestion into a records system such as Hyland OnBase.
- Confidential documents **cannot go to a cloud OCR or LLM service** — legal, HR, registrar, and procurement files must stay on the machine.
- Records teams want to **design an extraction recipe once on a sample** and reuse it across a whole folder, without writing code.

## Our Approach

- **Local-only by construction.** A PowerShell server on loopback; bundled engines invoked as separate command-line executables; AI is opt-in and runs against a local Ollama. No document content ever leaves the machine.
- **Rule-based first, AI-assisted second.** Splitting and extraction are driven by explicit rules (zones, regex, bookmarks). AI (Ollama) only *proposes* fields and disambiguates — it never silently dictates the schema.
- **Design-time vs. run-time separation.** The Smart Mapping tab is where you author and chat about a template against a sample; the Splitter / Index Creator are where those templates run unattended over a folder.
- **Tagged (anchor-relative) mapping.** A drawn box can act as a label/anchor; at run-time the server re-finds the label on every document and pulls the value beside it — so a field follows its label across documents instead of being pinned to fixed coordinates.
- **OnBase-ready output.** The index can be emitted as CSV, XLSX, and a schema-accurate OnBase XML Index DIP file (Hyland Foundation 24.1).

## Who Uses AutoPDF?

| Role | How they interact |
|---|---|
| Records / imaging team | Split scanned batches into per-document PDFs and build a metadata index for OnBase ingestion |
| Office worker | Drag Office / image / Markdown files into the input folder and bulk-convert to PDF |
| Template author | Use Smart Mapping to draw zones, set regex rules, and chat with local AI to design a reusable extraction template |
| Procurement / registrar / special collections (BU demo personas) | Run a saved recipe over a folder to produce a labelled CSV / XLSX / XML index |
| Windows admin | Deploys by copying a folder; optionally runs the launcher as a logon task and exposes a PIN-gated Cloudflare tunnel |
| Other QI projects (future) | Could call `/api/template-apply-batch` to extract fields from user-supplied PDFs |

## Current Build Status (June 2026)

| Area | Status |
|---|---|
| PDF Converter (Office / image / text / Markdown → PDF) | ✅ Live |
| PDF Splitter (zones, patterns, bookmarks, page ranges) | ✅ Live |
| Visual Zone Mapper (Modal / Tab / Window / Split-view) | ✅ Live |
| Tagged (anchor-relative) mapping — Smart Mapping + Splitter | ✅ Live |
| Smart Mapping templates (zone / regex_match / ai_extract) | ✅ Live |
| Centralized regex library (~30 builtins, user-editable) | ✅ Live |
| Index Creator (folder-tree → CSV / XLSX) | ✅ Live |
| OnBase XML Index DIP export (.xml, Foundation 24.1) | ✅ Live |
| Local AI assist via Ollama (chat, propose, ai_extract) | ✅ Live (optional) |
| Scanner capture (NAPS2 TWAIN / ESCL + native WIA) | ✅ Live |
| OCR for scanned PDFs (bundled Tesseract) | ✅ Live |
| Workflow chaining + Scheduler | ⚠️ Partial |
| PIN-gated Cloudflare public tunnel | ✅ Live |
| Tier 1/2 PowerShell + Tier 3 Playwright test suite | ⚠️ Partial |
| Second OCR engine (PP-OCRv5/v6 via ONNX / RapidOcrNet) | 🗓️ Planned |
| Index Creator date-format picker in the UI | 🗓️ Planned |
| Per-row OnBase Document Type column in the UI | 🗓️ Planned |

## The Vision

AutoPDF stays a small, portable, local-only tool — but becomes the **records-ingestion front door** for the QI ecosystem. The near-term target is a confident Boston University demo (the Index Creator scenarios and an OnBase ingestion handoff). Beyond that: a fully portable build that runs with no Ollama and no internet, a second offline OCR engine that keeps the zero-install promise, and optional integration points where Maia, NEXUS, or FileHQ can call AutoPDF's batch-extraction API to turn user-supplied PDFs into structured fields.

## Privacy posture

- **No telemetry.** AutoPDF makes no analytics calls.
- **No cloud document processing.** Conversion, OCR, splitting, and extraction all run locally.
- **Update checks are opt-in** (Settings → Updates) and only fetch VERSION strings from GitHub / GitLab / Bell-SW — never document content.
- **Loopback by default.** The server binds to `127.0.0.1`. When exposed via the Cloudflare tunnel it is **PIN-gated** (`/health` and `/version` stay open for monitoring probes only).

## How it runs (one paragraph)

`AutoPDF.exe` is an idempotent native C# launcher: it pings `:6969/api/status`, and if AutoPDF is already up it just opens the browser; otherwise it starts `Application/AutoPDF-Server.ps1` hidden, shows a splash, and opens the UI. Server version is stamped `2026.06.15`. Engines live under `Application/` (`gs/`, `poppler/`, `tesseract/`, `tabula/`, `pdftk/`, `java/`, `naps2/`). Saved recipes and templates are plain JSON under `Application/recipes/` and `Application/templates/`, so they copy cleanly between machines.

*This page is editable at C:\APPS\AutoPDF\INTRO\status_intro.md — save and click Refresh to update.*

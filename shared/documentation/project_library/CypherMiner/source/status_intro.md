# CypherMiner — Offline Crypto, Encoding, Math & Text Toolbox

## What is CypherMiner?

CypherMiner is a **local-first, bilingual (English / Portuguese), 100% offline** suite of
cryptography, encoding, mathematics and text tools built by **Quiddity Innovations**.
It runs entirely in the browser — no server call, no internet, no account, nothing ever
leaves your device. Open it once and it keeps working with the network unplugged.

It ships **59 tools** across five categories. Every tool is a small, self-registering
module: the sidebar, search, input form, live result panel, copy button and optional
visual (like the Caesar cipher wheel) are all generated automatically from a single
`Tool` object. Adding a tool is dropping one file into `src/tools/<category>/` and
importing it in `src/tools/index.ts` — no other code changes.

## The Problem We Solve

- Online cipher / encoding / hashing tools send your text to **someone else's server** — a privacy risk for anything sensitive.
- Most toolboxes are English-only; Brazilian users get no Portuguese.
- They break the moment you lose connectivity, and they bury a simple tool under ads.
- Each tool is usually a separate site, with no shared search, no "what tool do I need?" helper, and no explanation of *how* the algorithm actually works.

## Our Approach

CypherMiner is a tools suite you **own and trust**. It is a static Vite + TypeScript
build with **no UI framework** — the UI is generated from a tool registry. It installs as
a **PWA** (service worker) so it is offline and installable. Everything — the whole UI and
every tool's strings, plus the educational "How it works / History / Did you know?" content
— is fully **bilingual EN/PT**. A built-in **offline assistant** ("ask which tool you need")
runs a TF-IDF retrieval engine **on-device** with zero network calls.

The same codebase is architected to flip on public branding and deploy to Cloudflare Pages
later (each tool an SEO page) with no rework. A small **FastAPI backend** (port 8502)
implements the QI module contract (`/health`, `/version`, `/info`) and is reserved for
future heavy/data tools.

## Who Uses CypherMiner?

| Role | How they interact |
|---|---|
| **Students / hobbyists** | Learn ciphers and number theory hands-on — each tool has a "How it works", history and trivia panel |
| **Developers** | Quick offline Base64 / hex / hashing / slugify / text utilities without leaking data |
| **Puzzle & CTF solvers** | Frequency analysis, Index of Coincidence and the **Cipher Auto-Solver** to fingerprint and crack classical ciphers |
| **Privacy-conscious users** | Everything runs in-browser; no data leaves the device, works fully offline |

## Tool Categories (59 tools)

| Category | Count | Examples |
|---|---|---|
| 🔐 **Cryptography** | 19 | Caesar (cipher wheel), Vigenère, Atbash, Affine, Polybius, XOR, MD5, SHA-1/256/384/512, Frequency Analysis, Index of Coincidence, Cipher Auto-Solver |
| 🔣 **Encoding** | 13 | Base64 / URL-safe, Base32, Base58, ASCII85, Hex, Binary, Morse, URL, HTML Entities, Unicode, NATO, Tap code |
| 🔢 **Mathematics** | 14 | Base Converter, Roman Numerals, Prime & Factors, Integer Factorization (BigInt), GCD/LCM, Modular Inverse, Statistics, Number→Words, Factorial, Fibonacci, Combinatorics, Quadratic |
| 🎟️ **Lottery** | 2 | Lottery Odds (pick k from n), Covering Wheel |
| ✍️ **Text** | 11 | Case Converter, Reverse, Statistics, Word Frequency, Leet Speak, Sort Lines, Remove Duplicates, Find & Replace, Clean Whitespace, Slugify, Lorem Ipsum |

## Current Build Status (Complete)

CypherMiner is a **finished tool suite**. All core systems and all 59 tools are built and live:

| Area | Status |
|---|---|
| 59 tools across 5 categories (crypto / encoding / math / lottery / text) | ✅ Live |
| Self-registering tool registry (drop-in `Tool` modules) | ✅ Live |
| Auto-generated UI: sidebar, search, form, live result, copy | ✅ Live |
| Bilingual EN/PT — whole UI + every tool + educational content | ✅ Live |
| Dark / light theming (CSS variables, persisted) | ✅ Live |
| Favorites, About page, category browse, instant search | ✅ Live |
| Educational layer (How it works / History / Trivia / Source) | ✅ Live |
| On-device assistant ("ask which tool you need", TF-IDF, offline) | ✅ Live |
| Live visuals (Caesar wheel, Polybius grid, rail-fence zigzag, mapping strips) | ✅ Live |
| Cipher Auto-Solver (IoC + χ² Caesar candidates + format hints) | ✅ Live |
| PWA / offline / installable (service worker) | ✅ Live |
| Runtime config (`config.json`, edit without rebuild) | ✅ Live |
| FastAPI backend — QI contract `/health` `/version` `/info` (port 8502) | ✅ Live |
| NSSM services: QI_CypherMinerAPI, QI_CypherMinerUI, QI_CypherMinerTunnel | ✅ Live |
| Public static tunnel `cypher.quiddityinnovations.com` (UI :7842) | ✅ Live |
| Cloud assistant mode (hosted endpoint, config-switchable) | ⚠️ Built — endpoint not configured (local mode is default) |
| Heavy data tier (OCR / dictionaries — anagram, Scrabble) | 🗓️ Planned — needs `file` input type + on-demand asset bundling |
| Public launch (per-tool SEO pages, branding, Cloudflare Pages) | 🗓️ Planned — architecture ready, optional |

## The Architecture — the Registry

Every tool implements the `Tool` interface (`src/types.ts`): `id`, `category`, `icon`,
bilingual `name` / `blurb`, an `inputs` array (text / textarea / number / range / select,
each with bilingual labels), a `run(values, ctx)` function returning a string (or Promise),
and an optional `visual()` that renders into a container. Importing the module calls
`register()`, which pushes it into the in-memory registry. The UI shell (`core/ui.ts`)
reads that registry to build everything — so the catalog and the interface never drift apart.

## Global by Design

CypherMiner is bilingual to its core. Language is a single `Lang = 'en' | 'pt'` toggle
persisted in `localStorage`; every user-facing string is a `Loc = { en, pt }` pair —
UI labels, tool names and blurbs, input labels, select options, and the full educational
content (history paragraphs, trivia, sources). The on-device assistant indexes both
languages and de-pluralises / normalises accents so everyday Portuguese or English phrasing
reaches the right tool. Switching language re-renders instantly with no reload.

---
*This page is editable at `C:\CypherMiner\INTRO\status_intro.md` — save and click Refresh to update.*

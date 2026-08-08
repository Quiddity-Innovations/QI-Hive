# Project Structure Standard

**Status:** Active · **Version:** 1.0 · **Owner:** Renne Santiago (rennesan) · **Set:** 2026-06-19

This is the single, binding standard for how every project is laid out. Its goal
is **one canonical name per concept** — so no project ever uses `application`
while another uses `program`. It is grounded in widely adopted conventions
(see References) and tuned for Windows + cross-tool compatibility.

> You hold **override power**. Any deviation is allowed when justified, but it
> must be recorded (see [Overrides](#5-overrides)). The standard bends on the
> record; it never drifts silently.

---

## 1. Where things live (C:\AI taxonomy)

The machine is organized under `C:\AI`. The `C:\BU` root from the earlier plan
is **retired** — folder location does not change IP ownership (BU owns the
laptop, so everything on it is in scope). The real, machine-wide governance rule
stands regardless of folder: **no Quiddity Innovations source or QI memory on
this machine; never push BU code to a personal repo.**

| Root | Holds |
|------|-------|
| `C:\AI\Products\` | **Developed applications / programs** (the runnable deliverables) |
| `C:\AI\Projects\` | Development workspace — see the Projects↔Products rule below |
| `C:\AI\BU Hive\` | The BU Hive dashboard app (its own top-level home) |
| `C:\AI\Documentation\` | Standards and reference docs (this file) |
| `C:\AI\Sessions\` | Distilled session minutes |
| `C:\AI\Logs\` | Raw heartbeat session logs |
| `C:\AI Temp\` | Temp files created by developed applications (see §1.2) |
| `C:\AI\Error\` | Error logs from developed applications (see §1.2) |

Project root folder name: **kebab-case slug**, e.g. `onbase-invoice-lookup`.
The structure in §2 is **root-agnostic** — identical under `Products`, `Projects`, or `BU Hive`.

### 1.1 Projects ↔ Products rule (locked — by nature)

Split by **nature, decided once at creation** — never by lifecycle stage, so no
folder ever moves:

- **`C:\AI\Products\`** — ongoing, maintained applications/programs that have
  users and a long life (e.g. BU Hive, a kept OnBase tool).
- **`C:\AI\Projects\`** — time-boxed efforts: experiments, one-offs, research,
  analyses, tooling (e.g. the install kit).

Maturity is the project's **tier** field (a status in `PROJECT.md`), and the
Dev → Test → Beta → Prod progression is expressed through **deployment
environments**, not folder location. A POC is never relocated as it matures.

The one exception: if a *project* genuinely becomes a maintained *product*, that
is a rare, deliberate, one-time move — logged as an override (§5). Not routine
tier promotion.

This follows current practice: organizing deliverables by lifecycle stage is a
known anti-pattern; the project-vs-product split is by nature and lifespan.

### 1.2 Runtime locations for developed applications

Developed applications must not scatter temp files and errors into the user's
day-to-day space. They use dedicated, easy-to-find locations, each in a per-app
subfolder for clean troubleshooting:

| Concern | Location | Pattern |
|---------|----------|---------|
| Temp files | `C:\AI Temp\<app-slug>\` | Any scratch/intermediate files the app creates |
| Error logs | `C:\AI\Error\<app-slug>\` | `error_<YYYY-MM-DD>.log` (ISO 8601 / 24H) |

Rules:
- These paths are read from the app's `.env` (`TEMP_DIR`, `ERROR_DIR`) — never
  hardcoded — so the app stays portable.
- **Claude itself is exempt.** Claude Code's own temp/errors and its session
  artifacts (`Sessions`, `Logs`) are not governed by this convention.

---

## 2. The canonical folder set

### 2.1 Core — every project has these
| Path | Purpose |
|------|---------|
| `README.md` | What it is, how to run it, status |
| `PROJECT.md` | Project profile — kind, owner, tier, status, gates, overrides (ties to BU Hive) |
| `.gitignore` | Excludes secrets, build output, data, caches |
| `docs/` | All documentation — see **§2.1.1** for required contents |

#### 2.1.1 Required `docs/` contents (Documentation Standard)

The `docs/` folder is not free-form. Per the
[Documentation Standard](./Documentation-Standard.md), every project carries two
living doc sets, kept current as the product evolves:

| File | Doc set | Audience |
|------|---------|----------|
| `docs/user-guide.md` | **User Guide** | People who *use* it |
| `docs/technical.md` | **Technical Documentation** | People who *change* it |
| `docs/README.md` | Docs index + local maintenance contract | both |

Each carries a header block (`Last updated`) and a Changelog, and is updated in
the same unit of work as the change it documents. "Docs current" is a tier
promotion gate. See the Documentation Standard for the full contract.

### 2.2 Primary content — at least one, by project kind
| Path | Purpose | Use when |
|------|---------|----------|
| `src/` | Source code (the application itself) | Code projects |
| `content/` | Authored content (documents, pages, copy) | Content/document-centric projects |

### 2.3 Optional — use the canonical name when the concept is present
| Path | Purpose |
|------|---------|
| `tests/` | Automated tests |
| `examples/` | Samples, demos, sample data/usage |
| `scripts/` | Build / dev / utility scripts |
| `data/` | Input or reference data (gitignore large or sensitive sets) |
| `assets/` | Static assets — images, media, fonts |
| `config/` | Configuration files, `.env.example` |
| `build/` | Build / packaged output (gitignored) |
| `.github/` | CI / workflow config |

---

## 3. The naming ruling (anti-drift glossary)

One concept, one folder name. The "Never use" column lists synonyms that are
**prohibited** so two projects can never name the same thing differently.

| Concept | Canonical | Never use |
|---------|-----------|-----------|
| Source code | `src` | app, application, code, program, source, lib |
| Documentation | `docs` | doc, documentation, manual, help |
| Tests | `tests` | test, testing, qa, spec, specs |
| Samples / demos | `examples` | sample, samples, demo, demos, eg |
| Build output | `build` | dist, out, output, bin |
| Data | `data` | datasets, files, db |
| Static assets | `assets` | static, media, images, img, res |
| Configuration | `config` | configs, conf, settings, cfg |
| Scripts | `scripts` | script, tools, utils, bin |
| Authored content | `content` | pages, material, docs-content |

---

## 4. Naming rules

1. **Lowercase only.** No `Application`, no `Docs`.
2. **No spaces, ever.** They break CLIs, scripts, and URLs.
3. **Multi-word names use hyphen-case (kebab):** `invoice-lookup`, `api-client`.
4. **Canonical concept folders are single words** — no multi-word forms needed.
5. **Sanctioned exception — Python packages use snake_case** (`my_package`),
   because hyphens are illegal in Python import names. This is the only allowed
   deviation from kebab-case, and it applies only to importable package dirs.
6. **Dates and timestamps** follow ISO 8601 / 24-hour (`YYYY-MM-DD`,
   `HH:MM:SS`; filenames use `HH-MM-SS`). Matches the Logs/Sessions standard.

---

## 5. Overrides

Reality imposes structure you don't control (frameworks scaffold their own dirs,
package managers demand specific layouts). The standard accommodates this without
eroding — by **logging every deviation** in the project's `PROJECT.md`.

### 5.1 Two kinds of override
- **Beyond your control** (auto-accepted, still logged): a tool or framework
  mandates the layout. Examples: Next.js `app/` or `pages/`, Django app modules,
  `node_modules/`, Maven `src/main/java`, Terraform `.terraform/`.
- **Discretionary** (requires owner approval, logged): you choose to deviate for
  a project-specific reason.

### 5.2 How to log it — `## Structure overrides` table in `PROJECT.md`
| Deviation | Reason | Beyond control? | Approved by | Date |
|-----------|--------|-----------------|-------------|------|
| `app/` instead of `src/` | Next.js App Router requires it | Yes | — | 2026-06-19 |
| `notebooks/` added | Exploratory analysis project | No | rennesan | 2026-06-19 |

A change to the standard **itself** (not a per-project exception) is recorded in
[Section 8 changelog](#8-changelog) with a version bump.

---

## 6. `PROJECT.md` profile template

This file makes each project self-describing and feeds the BU Hive control panel.

```markdown
# <Project name>

- **Slug:** <kebab-case>
- **Kind:** application | service | library | content | automation | data
- **Owner:** rennesan
- **Root:** C:\AI\Projects\<slug>  (or C:\BU\<area>\<slug>)
- **Created:** YYYY-MM-DD

## Lifecycle
- **Tier:** 1 POC | 2 Dev & Test | 3 Beta (Super Users) | 4 Production (4a targeted / 4b BU-wide)
- **Status:** active | gate-pending | blocked | paused
- **Gates met:** N / M  (gates enforced with override; see overrides)

## Structure overrides
| Deviation | Reason | Beyond control? | Approved by | Date |
|-----------|--------|-----------------|-------------|------|

## Documentation (Documentation Standard)
- **User Guide:** ./docs/user-guide.md — current as of YYYY-MM-DD
- **Technical Documentation:** ./docs/technical.md — current as of YYYY-MM-DD
- **Docs gate (this tier):** met | pending  (see Documentation Standard §3)

## Links
- Repo: <path or url>
- Docs: ./docs/  (index: ./docs/README.md)
```

---

## 7. Reference skeletons by kind

```
# Code application
my-app/
  README.md  PROJECT.md  .gitignore
  src/  tests/  docs/  examples/  config/  scripts/  build/

# Library / package
my-lib/
  README.md  PROJECT.md  .gitignore
  src/  tests/  docs/  examples/

# Content / document project
my-content/
  README.md  PROJECT.md  .gitignore
  content/  docs/  assets/

# Automation / scripts
my-automation/
  README.md  PROJECT.md  .gitignore
  scripts/  tests/  docs/  config/

# Data / analysis
my-analysis/
  README.md  PROJECT.md  .gitignore
  data/  src/  docs/  examples/   (notebooks/ via logged override)
```

---

## 8. Changelog

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-06-19 | Initial standard set: canonical folder set, naming ruling, override mechanism, PROJECT.md profile. |
| 1.1 | 2026-06-19 | C:\AI taxonomy: Products = developed apps; retired C:\BU root (machine-wide IP rule retained). Added runtime locations: temp → C:\AI Temp\<app>, errors → C:\AI\Error\<app>, via .env; Claude exempt. BU Hive home corrected to C:\AI\BU Hive. |
| 1.2 | 2026-06-19 | Locked Projects↔Products by nature (Products = ongoing/maintained; Projects = time-boxed). Maturity = tier field; lifecycle = deployment environments, not folder moves. |
| 1.3 | 2026-06-20 | Defined required `docs/` contents (§2.1.1): mandatory `user-guide.md` + `technical.md` + `docs/README.md` per the new [Documentation Standard](./Documentation-Standard.md). Added a **Documentation** section to the `PROJECT.md` profile. |

---

## References

- [kriasoft/Folder-Structure-Conventions](https://github.com/kriasoft/Folder-Structure-Conventions) — `src` / `docs` / `test` / `build` canonical set and alternatives
- [World Bank — Folder Structure and Naming Conventions](https://worldbank.github.io/template/docs/folders-and-naming.html) — lowercase, no spaces, hyphen-separation rule
- [AlexDCode/Software-Development-Project-Structure](https://github.com/AlexDCode/Software-Development-Project-Structure) — hierarchical project template standard
- [Folder structures best practices (Medium)](https://medium.com/codeboulevard/projects-folder-structures-best-practices-706e4136aaca) — separation of concerns rationale

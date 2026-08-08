# Documentation Standard

**Status:** Active · **Version:** 1.0 · **Owner:** Renne Santiago (rennesan) · **Set:** 2026-06-20

This is the single, binding standard for **what documentation every product and
project carries and how it stays current as the thing it describes evolves**. It
sits alongside the [Project Structure Standard](./Project-Structure-Standard.md)
(which says *where files live*) and the [AI Workspace Framework](./AI-Workspace-Framework.md)
(which says *how the workspace is governed*). Where the Structure Standard mandates
a generic `docs/` folder, this standard says **what goes in it and keeps it alive**.

> **The core rule:** documentation is a *living artifact of the product, not a
> one-time deliverable.* Every product keeps two doc sets in lock-step with its
> evolution — a **User Guide** and **Technical Documentation** — and every
> meaningful change to the product updates them in the same unit of work.

---

## 1. The two mandatory doc sets

Every project and product maintains both. They have different audiences and must
not be blended into one file (the anti-pattern this standard exists to kill).

| Doc set | Audience | Answers | Canonical file |
|---------|----------|---------|----------------|
| **User Guide** | Operators / end users — people who *use* the thing | "How do I run it and do X with it?" | `docs/user-guide.md` |
| **Technical Documentation** | Developers / maintainers — people who *change* the thing | "How is it built, wired, and configured?" | `docs/technical.md` |

A third, optional file ties them together:

| Doc | Purpose | File |
|-----|---------|------|
| **Docs index** | One-screen map of the doc set + the maintenance contract (this standard, restated locally) | `docs/README.md` |

When Technical Documentation outgrows a single file, it becomes a folder
`docs/technical/` with an `index.md` and topic files (`architecture.md`,
`data-model.md`, `configuration.md`, `api.md`, `security.md`, `operations.md`).
The User Guide may likewise split into `docs/user-guide/` with task-oriented pages.
The canonical *entry* filenames (`user-guide.md` / `technical.md`, or the folder's
`index.md`) never change — tools and links depend on them.

### 1.1 What belongs in the User Guide

Task-oriented, written for someone who did not build it.

- What it is, in two sentences, and who it's for.
- Quick start: install / launch, the first thing to do, the expected result.
- A tour of the features/pages/commands the user actually touches.
- Common tasks as steps ("To do X: 1… 2… 3…").
- Accounts, roles, and permissions *as the user experiences them*.
- Troubleshooting the user can self-serve, and where to get help.
- **Not** internal architecture, schemas, or build internals.

### 1.2 What belongs in Technical Documentation

For the person who will modify, operate, or extend it.

- Architecture & stack: components, how a request flows, key modules.
- Data model: stores, schemas, registries, config files and their shape.
- Configuration & environment: every setting, env var, feature flag, and default.
- Interfaces: routes/endpoints/CLI, with auth requirements.
- Security posture & operational constraints.
- Build, run, deploy, and the runtime locations it uses (per the Structure Standard).
- Roadmap / known gaps and the source-of-truth location for the code.

---

## 2. The living-doc contract

Docs that drift are worse than no docs. Three lightweight mechanisms keep them honest.

### 2.1 Header block — every doc file starts with one

```markdown
# <Title>

**Doc:** User Guide | Technical Documentation
**Product:** <name> · **Covers version:** <product version/tier>
**Last updated:** YYYY-MM-DD · **Maintainer:** rennesan
```

`Last updated` is the machine-readable signal the BU Hive **Docs** page reads to
flag staleness. It must be bumped whenever the doc's body changes.

### 2.2 Changelog — every doc file ends with one

```markdown
## Changelog
| Date | Change |
|------|--------|
| YYYY-MM-DD | … |
```

A doc changelog records *changes to the document*, mirroring the product's own
evolution. It is the audit trail that proves the doc tracked the product.

### 2.3 The update-in-the-same-breath rule

> When you change the product, you change its docs **in the same unit of work** —
> not "later." A feature that ships without its doc update is not done.

Concretely, when a change adds/alters a user-visible feature → the **User Guide**
is updated; when it changes architecture, config, schema, or interfaces → the
**Technical Documentation** is updated. Most non-trivial changes touch both.

---

## 3. Docs as a promotion gate (tier integration)

Documentation is an **explicit exit gate** in the
[tier lifecycle](./AI-Workspace-Framework.md#3-project-lifecycle-tiers). The bar
rises with the tier:

| Tier | Documentation gate |
|------|--------------------|
| 1 · POC | A stub User Guide + Technical doc exist (header block present). Content may be thin. |
| 2 · Dev & Test | Both docs **complete and current**: every feature in the User Guide, architecture + config + data model in Technical. Changelogs live. |
| 3 · Beta (Super Users) | User Guide validated against the running product by a non-author; troubleshooting section real. |
| 4 · Production | Both docs current at release; `Last updated` ≥ last code change; doc changelog entry for the release. Ongoing per §2.3. |

Gates are enforced **with override** (recorded), consistent with the workspace
framework. "Docs current" is verifiable at a glance on the BU Hive **Docs** page
(§4).

---

## 4. Visibility — BU Hive Docs page

The BU Hive control plane surfaces doc health so staleness can't hide. For every
registered project it shows:

- Whether `docs/user-guide.md` and `docs/technical.md` exist.
- Each doc's `Last updated` (from the header block) and file mtime.
- **Freshness:** doc vs. the newest source change — `current`, `stale`
  (source changed after the doc), or `missing`.

This makes the §2.3 contract and the §3 gate observable rather than aspirational.
Route: `/docs`.

---

## 5. Authoring rules

1. **Plain Markdown**, GitHub-flavored. Tables and fenced code allowed (the BU
   Hive renderer supports `tables`, `fenced_code`, `toc`, `sane_lists`).
2. **Write for the audience of that doc set** (§1.1 / §1.2). If a paragraph serves
   the other audience, it's in the wrong file.
3. **Dates are ISO 8601** (`YYYY-MM-DD`), matching the workspace standard.
4. **No secrets, ever** — document *that* a setting exists and where it's read
   from (e.g. `.env`), never its value. Mirrors the security posture.
5. **Reference, don't duplicate** the standards: link to this file and the
   Structure Standard rather than restating them per project.
6. **Screenshots/diagrams** live in `docs/assets/` (or `docs/reference_shots/`)
   and are referenced relatively.

---

## 6. New-project checklist

When a project is created from `C:\AI\Projects\_template`:

- [ ] `docs/user-guide.md` present with header block + Changelog (from template).
- [ ] `docs/technical.md` present with header block + Changelog (from template).
- [ ] `docs/README.md` index present (from template).
- [ ] `PROJECT.md` → **Documentation** section filled (links + gate status).
- [ ] Project registered so it appears on the BU Hive **Docs** page.

---

## 7. Applying this to existing products

| Product / project | User Guide | Technical Doc | Notes |
|-------------------|-----------|---------------|-------|
| **BU Hive** | `docs/user-guide.md` | `docs/technical.md` | Reference implementation. Split from the former blended `GUIDE.md` on 2026-06-20. |
| **claude-env-setup** | `docs/user-guide.md` | `docs/technical.md` | Brought into compliance 2026-06-20; `docs/phases.md` retained as a technical sub-topic. |
| **CogniBase** | `docs/user-guide.md` | `docs/technical.md` | To be authored as it leaves MOC (tier 1 → 2). Stub at registration. |
| **onbase-client** | `docs/user-guide.md` | `docs/technical.md` | Library: User Guide = usage; Technical = API surface + client design. |

---

## 8. Changelog

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-06-20 | Initial standard: mandatory User Guide + Technical Documentation per product; living-doc contract (header block, doc changelog, update-in-same-breath); docs as a tier promotion gate; BU Hive Docs page for visibility; authoring rules; checklist; existing-product application map. |

---

## References

- [Project Structure Standard](./Project-Structure-Standard.md) — where `docs/` lives and the canonical folder set.
- [AI Workspace Framework](./AI-Workspace-Framework.md) — tier lifecycle, gates, and governance this standard plugs into.
- [Diátaxis](https://diataxis.fr/) — the tutorial/how-to/reference/explanation split underpinning the User-Guide vs Technical division.
- [Write the Docs — Docs as Code](https://www.writethedocs.org/guide/docs-as-code/) — docs versioned and changed alongside the product.

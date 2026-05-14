# Quiddity Innovations — Architecture Principles
## The Governing Law for All QI Projects

*This document is the architectural constitution of the QI platform.*
*It supersedes convenience, shortcuts, and personal preference.*
*Every project, every session, every decision must honor these principles.*
*Last updated: 2026-05-13*

---

## The Core Premise

> Every QI project is simultaneously two things:
> **an independent application today** and **a module in a unified platform tomorrow.**
>
> Build for both. Always.

This is not aspirational. It is the design constraint from day one.
The unified platform is not a future refactor — it is what you are building right now,
one module at a time.

---

## The Six Laws

### Law 1 — The Registry is the Source of Truth

The file `C:\QI\ECOSYSTEM\qi_registry.json` is authoritative.

- Before assigning a port → check the registry
- Before naming a folder → check the registry
- Before calling another project → check the registry
- After creating a project → register it in the registry

**Violation:** assigning a port that conflicts with another project. Result: broken services, broken demos, broken trust.

---

### Law 2 — Every Module Must Honor the Contract

Every QI project must expose these standard endpoints, no exceptions:

| Endpoint | Method | Returns | Purpose |
|---|---|---|---|
| `/health` | GET | `{"status": "ok"}` | Liveness check — all monitoring calls this |
| `/version` | GET | `{"project": "...", "version": "..."}` | Identity — who am I, what version |
| `/info` | GET | registry entry for this project | Full self-description |

Every QI project must follow the standard response envelope:
```json
{
  "status": "ok" | "error",
  "data": { ... },
  "error": null | "error message",
  "project": "maia",
  "version": "0.x.x"
}
```

**Why:** When the unified app assembles these modules, it must be able to health-check, version-check, and describe any module with the same call. No special-casing.

---

### Law 3 — Independence with Declared Dependencies

Every project must be runnable **completely alone**, without any other QI project running.

- If NEXUS is down, Maia must still work (degrade gracefully, don't crash)
- If Maia is down, NEXUS must still work
- Dependencies between projects are **optional enhancements**, never hard requirements

**How:** Every cross-project call must have a fallback:
```python
# CORRECT
result = nexus_client.synthesize(prompt)
if result is None:
    result = local_fallback(prompt)   # degrade gracefully

# WRONG
result = nexus_client.synthesize(prompt)  # crashes if NEXUS is down
```

**Why:** Independent deployability. Each module can be started, stopped, updated, or replaced without cascading failures across the platform.

---

### Law 4 — API Contract First, Implementation Second

The public API of a module (its endpoints, request/response shapes) is a **contract**.
Contracts are versioned and never broken without a migration path.

- Adding fields to a response = OK (backward compatible)
- Removing fields from a response = breaking change → version the endpoint
- Changing field names = breaking change → version the endpoint
- The contract lives in `qi_registry.json` under `exposes_to_ecosystem`

**Why:** When the unified app assembles modules, it calls their APIs. If a module changes its API unilaterally, the unified app breaks. The contract is the interface between independent modules.

---

### Law 5 — One Registry, Always Current

`qi_registry.json` must be updated **before** the code is written, not after.

When creating a new project or new service:
1. Run `python C:\QI\ECOSYSTEM\qi_new_project.py` → it registers first, scaffolds second
2. Or manually add the entry to `qi_registry.json` before writing any code

When changing a port or endpoint:
1. Update `qi_registry.json`
2. Then update the code

**Why:** The registry drives CORS configs, monitoring, health checks, and eventually service discovery in the unified app. A stale registry is a silent failure waiting to happen.

---

### Law 6 — Owner Override and Best-Practice Surfacing

Architectural and engineering decisions made by Claude, sub-agents, or automation are **always provisional**. Renne (the QI owner) has final, binding authority on every decision — including those already shipped, already documented, or already validated by an agent review pass. An owner override does not require justification and does not need to be reconciled against prior agent recommendations: it simply replaces them.

In exchange, agents owe Renne **proactive best-practice surfacing**:

- The `hive-architect` MUST flag when a proposed approach — whether from Renne, Claude, or another agent — diverges from established industry best practice. State the divergence in one or two sentences, cite the standard practice, and note the trade-off. Do this even when the question put to you is narrower.
- The `hive-inspector` MUST flag the same in code review (not only against QI Standards but against industry norms — testing pyramids, error handling, security defaults, observability conventions).
- Other agents (`hive-builder`, `hive-ops`, `hive-scout`, `hive-tester`, `hive-scribe`) MUST surface any best-practice concern they notice in passing, even outside their primary mandate. They are not required to research it deeply; flagging is enough.

Once Renne has heard the flag and chosen, that choice is binding. Agents do not relitigate. The next agent in the chain treats the owner's decision as the new baseline and operates from there.

**Why:** The agentic system is a thinking partner, not a committee. Best-practice surfacing protects Renne from drift and silent compromises; owner override protects velocity and aligns the system with the business context only Renne carries. Without both halves, the system either rubber-stamps or stalls.

**Violations:**
- Agent argues against an owner override after Renne has decided. Result: time lost, partnership eroded.
- Agent silently implements a sub-optimal approach because Renne didn't explicitly ask for best practice. Result: technical debt that Renne never agreed to.

---

## The Module Relationship Model

Projects relate to each other at different depths. The relationship determines integration strategy.

```
UNIFIED QI PLATFORM
│
├── CORE LAYER (user-facing)
│   ├── Maia ──────────── The flagship. Multi-channel AI assistant.
│   └── Naya ──────────── Personal AI. Sibling of Maia. Shared engine.
│
├── ACTION LAYER
│   └── OpenClaw ──────── Autonomous agents. What Maia can't do, OC does.
│
├── INTELLIGENCE LAYER (backbone — not user-facing)
│   └── NEXUS ──────────── AI dispatch, synthesis, scoring, news. Powers everything.
│
└── DATA LAYER
    └── FileHQ ─────────── File intelligence. Documents, search, extraction.
```

### Integration Depth by Relationship Type

| Type | Coupling | Communication | Shared State | Failure Impact |
|---|---|---|---|---|
| **Backbone** | Loose | REST API | None | Graceful degrade |
| **Sibling** | Tight | Shared lib or API | Shared DB (future) | Feature flags |
| **Cousin** | Moderate | REST API | No shared DB | Graceful degrade |
| **Marriage** | Deep | Merged codebase or event bus | Shared DB | Coordinated deploy |

---

## The Modular Integration Blueprint

How modules connect today vs. in the unified app:

### Today (Distributed)
```
Maia ──HTTP──► NEXUS /synthesize
Naya ──HTTP──► NEXUS /synthesize
Maia ──HTTP──► NEXUS /scout/digest
Any  ──HTTP──► NEXUS /bench/recommend
```

### Unified App (Same Process)
```
Maia module ──function call──► NexusEngine.synthesize()
Naya module ──function call──► NexusEngine.synthesize()
```

**The bridge:** Because both today and tomorrow use the same API contract,
the migration from distributed HTTP calls to in-process function calls
is a **one-line change per call site.** The contract is identical.

This is why Law 2 and Law 4 exist.

---

## Compliance Checklist (Run Before Every New Project or Major Change)

```
python C:\QI\ECOSYSTEM\qi_validator.py --project <id>
```

Manual checklist:

- [ ] Project registered in `qi_registry.json`
- [ ] Port assigned from project's allocated block
- [ ] `CLAUDE.md` exists at project root
- [ ] `QI_Standards.md` naming convention followed for all folders
- [ ] `secrets/` folder exists and is in `.gitignore`
- [ ] `GET /health` endpoint returns `{"status": "ok"}`
- [ ] `GET /version` endpoint returns project id + version
- [ ] All cross-project calls have a graceful fallback
- [ ] `qi_registry.json` updated with any new endpoints in `exposes_to_ecosystem`
- [ ] Session summary saved to `Quiddity Innovations - <P> Documentation\Session Summaries\`

---

## When a New Project Is Created

Run the wizard — it enforces everything above automatically:

```
python C:\QI\ECOSYSTEM\qi_new_project.py
```

The wizard will:
1. Ask for project name, description, path
2. Assign the next available port from the correct block
3. Register the project in `qi_registry.json`
4. Scaffold the full folder structure per `QI_Standards.md`
5. Create `CLAUDE.md` with ecosystem safety rules pre-filled
6. Create `requirements.txt`, `.gitignore`, `secrets/` template
7. Create the standard FastAPI skeleton with `/health`, `/version`, `/info`
8. Create the documentation folder structure
9. Run `qi_validator.py` to confirm compliance
10. Print the full project summary

**No project should ever be started by hand from scratch.** Use the wizard.

---

## The Pledge (Claude reads this at every session)

> I am working on one QI project right now.
> But five projects share this machine, these ports, this git, and this future.
> Before I change a port, I check the registry.
> Before I name a folder, I check the standards.
> Before I add a dependency, I check that it degrades gracefully.
> I build for today. I design for the unified platform.
> The registry is always current before the code is written.
> The contract is never broken without a migration.
> Every project I touch is ready to be a module.

---

*This document lives at `C:\QI\ECOSYSTEM\QI_Architecture_Principles.md`*
*It is referenced by the global CLAUDE.md and every project's CLAUDE.md.*
*It is the law. Update it when the law changes — never work around it.*

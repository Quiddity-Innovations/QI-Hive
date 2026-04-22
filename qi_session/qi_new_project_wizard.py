# -*- coding: utf-8 -*-
"""
qi_new_project_wizard.py — Standard QI project scaffolding.

Called when Claude detects a project name that isn't in the registry.
Creates the standard QI folder structure, memory file, CLAUDE.md stub,
and registers the project in the Brain DB.

Usage (called programmatically by Claude):
    from qi_new_project_wizard import scaffold_project
    result = scaffold_project("SuperApp", "C:\\SuperApp", api_port=8300)
    print(result)  # formatted report of what was created
"""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from pathlib import Path
from datetime import datetime
import urllib.request

BRAIN_URL   = "http://127.0.0.1:9010"
MEM_DIR     = Path(r"C:\Users\renne\.claude\projects\C--Users-renne-Downloads\memory")
ECOSYSTEM   = Path(r"C:\QIH\ecosystem")  # migrated 2026-04-22 from C:\UNIVERSAL\ECOSYSTEM
REGISTRY    = ECOSYSTEM / "qi_registry.json"

# Standard folder structure every QI project must have (QI_Standards.md §2)
STANDARD_FOLDERS = [
    "DOCUMENTATION",
    "LOGS",
    "TOOLS",
    "TESTS",
]

CLAUDE_MD_TEMPLATE = """\
# {name} — Claude Session Instructions

## Project Identity
- **Name:** {name}
- **Root:** `{path}`
- **API port:** {api_port}
- **Brain ID:** `{brain_id}`
- **Created:** {date}

## What this project does
[Describe the project here — updated each session]

## Key files
| File | Purpose |
|---|---|
| `main.py` | Entry point |
| `DOCUMENTATION/` | All docs |
| `LOGS/` | Service logs |

## QI Service (NSSM)
```
Service name: QI_{name}Bot
Binary: C:\\1-AI\\APPS\\PYTHON\\python.exe
Script: {path}\\main.py
Log: {path}\\LOGS\\service_log.txt
```

## Session start protocol
1. Read `MEMORY.md` → `project_{brain_id}.md`
2. Check Brain API context: `POST http://localhost:9010/api/context {{project_id: "{brain_id}"}}`
3. Tail `LOGS\\service_log.txt` for last errors
4. Report state and Next Up

## Standing rules
- Follow QI_Standards.md for all naming and structure
- All NSSM services must start with `QI_`
- Log to `LOGS\\` — never to project root
- Update Implementation Log after every significant change
"""

MEMORY_FILE_TEMPLATE = """\
# project_{brain_id}.md — {name} Project Memory

**Created:** {date}
**Root:** `{path}`
**API port:** {api_port}

## What this project is
[Fill in during first working session]

## Architecture
[Fill in as decisions are made]

## Key decisions
[Logged here as they are made]

## Pending work
[Track active work items here]

## Resolved issues
[Move resolved items here]
"""


def _brain_post(endpoint: str, payload: dict) -> dict | None:
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            f"{BRAIN_URL}{endpoint}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def scaffold_project(
    name: str,
    path: str,
    api_port: int = 0,
    ui_port: int = 0,
    description: str = "",
) -> str:
    """
    Create standard QI project structure.

    Returns a human-readable report of everything created.
    """
    created = []
    skipped = []
    errors  = []

    root      = Path(path)
    brain_id  = name.lower().replace(" ", "_").replace("-", "_")
    date      = datetime.now().strftime("%Y-%m-%d")

    # ── 1. Create folder structure ────────────────────────────────────────────
    root.mkdir(parents=True, exist_ok=True)
    created.append(f"📁 {root}\\")

    for folder in STANDARD_FOLDERS:
        p = root / folder
        if not p.exists():
            p.mkdir(parents=True)
            created.append(f"📁 {p}\\")
        else:
            skipped.append(f"📁 {p}\\ (exists)")

    # ── 2. Create CLAUDE.md ───────────────────────────────────────────────────
    claude_md = root / "CLAUDE.md"
    if not claude_md.exists():
        claude_md.write_text(
            CLAUDE_MD_TEMPLATE.format(
                name=name, path=path, api_port=api_port or "TBD",
                brain_id=brain_id, date=date,
            ),
            encoding='utf-8',
        )
        created.append(f"📄 {claude_md}")
    else:
        skipped.append(f"📄 {claude_md} (exists)")

    # ── 3. Create 4 standard QI documentation files ──────────────────────────
    # Every QI project must have these from day 1 — no exceptions.
    std_docs = {
        f"{name}_Implementation_Log.md": f"""\
# {name} — Implementation Log

> Chronological record of everything built, fixed, or changed.

---

## {date} — Project Bootstrap
**Session Focus:** Initial project scaffolding via qi_new_project_wizard.

### Created
- Standard QI folder structure (DOCUMENTATION/, LOGS/, TOOLS/, TESTS/)
- CLAUDE.md session instructions stub
- Memory file in Claude memory directory
- This Implementation Log (and Meeting Minutes, Version History, Master Status Report)
- Brain DB registration

---
""",
        f"{name}_Meeting_Minutes.md": f"""\
# {name} — Meeting Minutes

---

## {date} — Project Creation
**Context:** Project scaffolded from QI new project wizard.

### Decisions on record
- Port block: {api_port or "TBD — assign during first session"}
- Scaffolded by qi_new_project_wizard.py

### Next Steps (first session)
1. Define project purpose and architecture
2. Assign port block in QI_Standards.md
3. Register in qi_registry.json
4. Update CLAUDE.md with real project description

---
""",
        f"{name}_Version_History.md": f"""\
# {name} — Version History

---

## v0.1 — {date}
**Type:** Project bootstrap
### Added
- Standard QI project structure
- Standard documentation set (Implementation Log, Meeting Minutes, Version History, Master Status Report)

---
""",
        f"{name}_Master_Status_Report.md": f"""\
# {name} — Master Status Report

> Last updated: {date}

---

## Current State

| Item | Value |
|------|-------|
| Version | 0.1 |
| Status | New — not yet started |
| Phase | Scaffolding complete — first session pending |
| API Port | {api_port or "TBD"} |
| Root | `{path}` |

## What {name} Does
[Define during first session]

## Feature Status
| Feature | Status |
|---------|--------|
| Project defined | ⏳ Pending first session |

## Pending Work
1. Define project purpose and architecture
2. Assign port block and register in QI ecosystem
3. Begin implementation

---
""",
    }

    doc_dir = root / "DOCUMENTATION"
    for fname, content in std_docs.items():
        fpath = doc_dir / fname
        if not fpath.exists():
            fpath.write_text(content, encoding='utf-8')
            created.append(f"📄 {fpath.name}")
        else:
            skipped.append(f"📄 {fpath.name} (exists)")

    # ── 4. Create memory file ─────────────────────────────────────────────────
    mem_file = MEM_DIR / f"project_{brain_id}.md"
    if not mem_file.exists():
        mem_file.write_text(
            MEMORY_FILE_TEMPLATE.format(
                name=name, brain_id=brain_id, path=path,
                api_port=api_port or "TBD", date=date,
            ),
            encoding='utf-8',
        )
        created.append(f"🧠 {mem_file}")
    else:
        skipped.append(f"🧠 {mem_file} (exists)")

    # ── 5. Update MEMORY.md index ─────────────────────────────────────────────
    mem_index = MEM_DIR / "MEMORY.md"
    try:
        content = mem_index.read_text(encoding='utf-8')
        new_line = f"- [project_{brain_id}.md](project_{brain_id}.md) — {name}: [description TBD]\n"
        if f"project_{brain_id}.md" not in content:
            # Insert after the last existing project line
            lines = content.splitlines(keepends=True)
            # Find end of index section
            insert_at = len(lines)
            for i, line in enumerate(lines):
                if line.strip().startswith("# lastSession"):
                    insert_at = i
                    break
            lines.insert(insert_at, new_line)
            mem_index.write_text("".join(lines), encoding='utf-8')
            created.append(f"📝 Added to MEMORY.md index")
        else:
            skipped.append(f"📝 MEMORY.md index (already has {brain_id})")
    except Exception as e:
        errors.append(f"MEMORY.md update: {e}")

    # ── 6. Register in Brain DB ───────────────────────────────────────────────
    result = _brain_post("/api/update_project_state", {
        "project_id": brain_id,
        "phase": "Phase 0 - Setup",
        "status": "new",
        "summary": description or f"{name} — newly scaffolded project",
        "next_steps": f"Define architecture and goals for {name}",
    })
    if result and result.get("ok"):
        created.append(f"🧠 Registered in Brain DB as '{brain_id}'")
    else:
        errors.append(f"Brain DB registration failed (project may not exist in projects table)")

    # ── 7. Add to qi_context_loader registry (runtime note) ──────────────────
    # Can't auto-add to the Python dict — but we note it for Claude
    created.append(
        f"⚠️  MANUAL STEP: Add '{brain_id}' to PROJECTS dict in "
        f"C:\\UNIVERSAL\\qi_session\\qi_context_loader.py"
    )

    # ── Build report ──────────────────────────────────────────────────────────
    sep = "─" * 50
    report = [
        f"\n{'═'*50}",
        f"  🆕  NEW PROJECT SCAFFOLDED: {name}",
        f"{'═'*50}",
        "",
        "✅ CREATED:",
    ]
    for item in created:
        report.append(f"   {item}")

    if skipped:
        report.append("\n⏭️  SKIPPED (already exist):")
        for item in skipped:
            report.append(f"   {item}")

    if errors:
        report.append("\n⚠️  ERRORS:")
        for item in errors:
            report.append(f"   {item}")

    report += [
        "",
        "📋 NEXT STEPS:",
        f"   1. Define project purpose in {root}\\CLAUDE.md",
        f"   2. Add project to qi_context_loader.py PROJECTS dict (with doc_names filled in)",
        f"   3. Allocate a port block in QI_Standards.md",
        f"   4. Register in qi_registry.json",
        f"   5. Start building — log every change in {name}_Implementation_Log.md",
        f"",
        f"📄 STANDARD DOCS CREATED IN DOCUMENTATION\\:",
        f"   ✅ {name}_Implementation_Log.md",
        f"   ✅ {name}_Meeting_Minutes.md",
        f"   ✅ {name}_Version_History.md",
        f"   ✅ {name}_Master_Status_Report.md",
        f"{'═'*50}\n",
    ]

    return "\n".join(report)


if __name__ == "__main__":
    # Quick test
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else "TestProject"
    path = sys.argv[2] if len(sys.argv) > 2 else f"C:\\{name}"
    print(scaffold_project(name, path, api_port=8600))

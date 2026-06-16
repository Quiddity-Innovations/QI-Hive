# -*- coding: utf-8 -*-
"""
QI INTRO generator — creates the standard 6-file INTRO set the Hive
"Project Status" tab renders. Reusable by the new-project wizard (so new
projects are born compliant) and by the backfill driver (for existing gaps).

The 6 files (in <project>\\INTRO\\):
    status_intro.md
    status_documentation.json
    status_features_business.json
    status_features_dev.json
    status_future.json
    status_techstack.json

Content is seeded from the registry entry (+ optional Brain state + optional
per-project KNOWN extras) so each page renders real, project-specific info
instead of an "empty / not populated" card.
"""
from __future__ import annotations
import json
from pathlib import Path

# INTRO dirs that don't follow <path>\INTRO (mirror dashboard/project_status.py overrides)
INTRO_OVERRIDES = {
    "qi_brain": r"C:\QIH\engine\brain\INTRO",
    "filehq":   r"C:\NAYA\filehq\INTRO",
}

SIX_FILES = ["status_intro.md", "status_documentation.json",
             "status_features_business.json", "status_features_dev.json",
             "status_future.json", "status_techstack.json"]


def intro_dir(project: dict) -> Path:
    pid = project["id"]
    if pid in INTRO_OVERRIDES:
        return Path(INTRO_OVERRIDES[pid])
    return Path(project.get("path", rf"C:\{project.get('name', pid)}")) / "INTRO"


def is_compliant(project: dict) -> bool:
    d = intro_dir(project)
    return d.exists() and all((d / f).exists() for f in SIX_FILES)


def _ports_str(project: dict) -> str:
    out = []
    for role, info in (project.get("ports") or {}).items():
        cur = info.get("current")
        if cur:
            out.append(f"{role}:{cur}")
    return ", ".join(out) or "none (no served ports)"


def make_intro(project: dict, brain: dict | None = None,
               known: dict | None = None, force: bool = False) -> tuple[Path, list[str]]:
    """Write the 6 INTRO files for `project`. Returns (intro_dir, files_written)."""
    brain = brain or {}
    known = known or {}
    d = intro_dir(project)
    d.mkdir(parents=True, exist_ok=True)

    pid   = project["id"]
    name  = project.get("name", pid)
    desc  = project.get("description", "")
    path  = project.get("path", "")
    ports = _ports_str(project)
    phase = brain.get("phase", project.get("status", "registered"))
    status_line = brain.get("summary") or desc

    written = []

    # 1) status_intro.md
    p = d / "status_intro.md"
    if force or not p.exists():
        block = (project.get("ports") or {})
        port_lines = "\n".join(f"- **{r.title()} port:** {i.get('current')}"
                               for r, i in block.items() if i.get('current')) or "- **Ports:** none (no served HTTP port)"
        md = f"""# {name}

## What is {name}?

{desc or known.get('what', 'Quiddity Innovations project.')}

## Status

{phase} — {status_line}

## Where it lives

- **Path:** `{path}`
{port_lines}
- **Family tier:** {project.get('family_tier','')}

## Role in the QI Ecosystem

{name} is one of the projects orchestrated by QI Hive. See the QI Ecosystem Map
(`C:\\QIH\\ecosystem\\QI_Ecosystem_Map.md`) for the full port table, ownership
matrix, and integration contracts.
"""
        p.write_text(md, encoding="utf-8"); written.append(p.name)

    # 2) status_documentation.json
    p = d / "status_documentation.json"
    if force or not p.exists():
        docs = known.get("documentation") or [
            {"title": f"{name} README", "type": "Reference",
             "location": (path + "\\") if path else "", "file": "README.md",
             "description": f"Top-level overview of {name}."},
            {"title": "QI Ecosystem Map", "type": "Reference",
             "location": "C:\\QIH\\ecosystem\\", "file": "QI_Ecosystem_Map.md",
             "description": "Where this project sits in the QI port/family map."},
        ]
        p.write_text(json.dumps({"sections": [{"name": "Project Documentation", "documents": docs}]},
                                indent=2), encoding="utf-8"); written.append(p.name)

    # 3) status_features_business.json
    p = d / "status_features_business.json"
    if force or not p.exists():
        biz = known.get("features_business") or [{
            "category": "Core Capabilities",
            "features": [
                {"name": "Registered in QI ecosystem",
                 "description": "Listed in qi_registry.json with port allocation, path, and status.",
                 "status": "live"},
            ]}]
        p.write_text(json.dumps(biz, indent=2), encoding="utf-8"); written.append(p.name)

    # 4) status_features_dev.json
    p = d / "status_features_dev.json"
    if force or not p.exists():
        dev = known.get("features_dev") or [{
            "category": "Codebase",
            "features": [
                {"name": "Source tree", "file": path, "status": "live",
                 "detail": "Live source folder for the project."},
            ]}]
        p.write_text(json.dumps(dev, indent=2), encoding="utf-8"); written.append(p.name)

    # 5) status_future.json
    p = d / "status_future.json"
    if force or not p.exists():
        fut = known.get("future") or {"categories": [
            {"name": "Roadmap", "priority": "medium", "items": [
                {"title": f"Capture {name}'s roadmap", "detail": brain.get("next_steps") or "Add high/medium/low items as planning progresses."}]}]}
        p.write_text(json.dumps(fut, indent=2), encoding="utf-8"); written.append(p.name)

    # 6) status_techstack.json
    p = d / "status_techstack.json"
    if force or not p.exists():
        ts = known.get("techstack") or {
            "table": [
                {"layer": "Runtime", "technology": project.get("primary_language", "Python 3.11+"),
                 "role": "Primary language.", "license": "Open source", "version": ""},
                {"layer": "Hosting", "technology": "Local Windows",
                 "role": f"Runs on the Quiddity dev machine at {path}.", "license": "N/A", "version": ""},
            ],
            "descriptions": [{"title": "Stack", "body": f"{name} stack. Ports: {ports}."}],
        }
        p.write_text(json.dumps(ts, indent=2), encoding="utf-8"); written.append(p.name)

    return d, written

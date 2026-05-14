# -*- coding: utf-8 -*-
"""Seed minimal INTRO/ folders for QI projects so they appear 'ready' on the
QI Hive Project Status Index. Run once; idempotent (will not overwrite).
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECTS = {
    "qi_brain": {
        "name": "QI Brain",
        "path": r"C:\QIH\engine\brain",
        "tagline": "Ecosystem intelligence API",
        "status_line": "Live — FastAPI service on port 9011 backing QI Hive Dashboard.",
        "what": ("QI Brain is the intelligence layer of the QI ecosystem. It exposes a "
                 "FastAPI service on port 9011 and a SQLite-backed memory store of "
                 "decisions, features, sessions, and project state. The QI Hive Dashboard, "
                 "Claude Code sessions, and the agentic sub-agents all read from and write "
                 "to Brain via the qi.* MCP tools."),
        "port": "9011",
        "ports_block": "9011-9019",
    },
    "filehq": {
        "name": "FileHQ",
        "path": r"C:\NAYA\filehq",
        "tagline": "File intelligence engine — merged into Naya",
        "status_line": "MERGED into Naya (C:\\NAYA\\filehq\\). Original C:\\FileHQ marked for deletion.",
        "what": ("FileHQ is the file-intelligence subsystem of Naya. It indexes the user's "
                 "documents, makes them searchable, and serves them to the Naya bot as a "
                 "retrieval source. It started as a standalone POC and was folded into Naya "
                 "to share its DB, identity, and channel layer."),
        "port": "8000",
        "ports_block": "8000-8099",
    },
    "openclaw": {
        "name": "OpenClaw",
        "path": r"C:\OC",
        "tagline": "Autonomous AI agent platform",
        "status_line": "Active production — 6 custom agents on a WSL gateway.",
        "what": ("OpenClaw is an autonomous AI agent platform running on WSL. It exposes a "
                 "gateway protocol on TCP 18789 and hosts six specialised agents: Tasuke "
                 "(assistant), Kaze (orchestrator), Sentry (monitor), Seiri (organiser), "
                 "Yubin (mail), and Koe (voice). The npm-based OpenClaw gateway is the "
                 "integration point — see ~/.openclaw/workspace/TOOLS.md."),
        "port": "18789 (WSL TCP)",
        "ports_block": "8400-8499",
    },
    "mq": {
        "name": "MQ",
        "path": r"C:\MQ",
        "tagline": "Maia Quiddam — autonomous social media persona",
        "status_line": "New project — early build.",
        "what": ("MQ (Maia Quiddam) is an autonomous AI social media persona for Facebook, "
                 "Instagram, and WhatsApp. It posts, replies, and grows a presence on behalf "
                 "of Quiddity Innovations, using the same multi-LLM chain pattern as Maia."),
        "port": "8500 (api), 7840 (ui)",
        "ports_block": "8500-8509 / 7840-7849",
    },
    "autopdf": {
        "name": "AutoPDF",
        "path": r"C:\AutoPDF",
        "tagline": "Local-only PDF toolkit",
        "status_line": "Active dev — phase 2c.",
        "what": ("AutoPDF is a self-contained PDF toolkit that converts, splits, extracts "
                 "from, and catalogs PDF files entirely on the local machine. No cloud, no "
                 "telemetry. It is built as a small FastAPI app with a web UI and a CLI."),
        "port": "6969",
        "ports_block": "8700-8709 (recommended)",
    },
    "cognibase": {
        "name": "CogniBase",
        "path": r"C:\CogniBase",
        "tagline": "OnBase-aware AI knowledge platform",
        "status_line": "Pre-POC — architecture and connectors being scoped.",
        "what": ("CogniBase is a local desktop platform that connects to Hyland OnBase, "
                 "lifts its data into a vector store + data lake, and lets AI correlate, "
                 "infer, and report across boundaries OnBase itself can't query. Vendor-"
                 "neutral LLM router (Claude / OpenAI / Gemini / Ollama / LM Studio / "
                 "llama.cpp). Pluggable source connectors — first source OnBase; future "
                 "sources filesystem, email, Jenzabar."),
        "port": "8650",
        "ports_block": "8650-8659",
    },
    "mapsnap": {
        "name": "MapSnap",
        "path": r"C:\MapSnap",
        "tagline": "Local schema browser for Jenzabar EX",
        "status_line": "Active and stable.",
        "what": ("MapSnap is a standalone local schema browser for Jenzabar EX (university "
                 "ERP). It reads a schema.json built from CSV/SQL exports and renders a "
                 "navigable HTML browser with FK relationships, ERD-confirmed edges, and "
                 "module groupings. Original product; sibling of mapsnap_onbase."),
        "port": "9876",
        "ports_block": "8650-8659 (reserved)",
    },
}


def status_intro_md(p):
    return f"""# {p['name']} — {p['tagline']}

## What is {p['name']}?

{p['what']}

## Status

{p['status_line']}

## Where it lives

- **Path:** `{p['path']}`
- **Port:** {p['port']}
- **Allocated block:** {p['ports_block']}

## Role in the QI Ecosystem

{p['name']} is one of the projects orchestrated by QI Hive. See the QI Ecosystem Map
(`C:\\QIH\\ecosystem\\QI_Ecosystem_Map.md`) for the full port table, ownership matrix,
and integration contracts. This page will be expanded with the project's full feature
matrix, blueprint diagrams, and tech-stack deep-dive as the work progresses.
"""


def status_documentation_json(p):
    return {
        "sections": [
            {
                "name": "Project Documentation",
                "documents": [
                    {
                        "title": f"{p['name']} README",
                        "type": "Reference",
                        "location": p["path"] + "\\",
                        "file": "README.md",
                        "description": f"Top-level overview of {p['name']}.",
                    },
                    {
                        "title": "QI Ecosystem Map",
                        "type": "Reference",
                        "location": "C:\\QIH\\ecosystem\\",
                        "file": "QI_Ecosystem_Map.md",
                        "description": "Where this project sits in the QI port/family map.",
                    },
                ],
            }
        ]
    }


def status_features_business_json(p):
    return [
        {
            "category": "Core Capabilities",
            "features": [
                {
                    "name": "Project registered in QI ecosystem",
                    "description": "Listed in qi_registry.json with port allocation, path, and status.",
                    "status": "live",
                },
                {
                    "name": "Detailed feature matrix",
                    "description": "Per-feature business view — pending population.",
                    "status": "planned",
                    "notes": "Fill in by editing status_features_business.json in the INTRO folder.",
                },
            ],
        }
    ]


def status_features_dev_json(p):
    return [
        {
            "category": "Codebase",
            "features": [
                {
                    "name": "Source tree",
                    "file": p["path"],
                    "status": "live",
                    "detail": "Live source folder for the project.",
                },
                {
                    "name": "Component-level dev matrix",
                    "file": "INTRO/status_features_dev.json",
                    "status": "planned",
                    "detail": "Populate with module/file-level status entries.",
                },
            ],
        }
    ]


def status_future_json(p):
    return {
        "categories": [
            {
                "name": "Documentation",
                "priority": "high",
                "items": [
                    {
                        "title": "Populate full INTRO content",
                        "detail": ("Replace this seed with the real feature matrix, blueprint "
                                   "SVG, technology stack, and documentation index."),
                    }
                ],
            },
            {
                "name": "Roadmap",
                "priority": "medium",
                "items": [
                    {
                        "title": "Capture this project's roadmap here",
                        "detail": "Add high / medium / low priority items as planning progresses.",
                    }
                ],
            },
        ]
    }


def status_techstack_json(p):
    return {
        "table": [
            {
                "layer": "Runtime",
                "technology": "Python 3.11+",
                "role": "Primary language (placeholder — confirm).",
                "license": "Open source (PSF)",
                "version": "3.11",
            },
            {
                "layer": "Hosting",
                "technology": "Local Windows",
                "role": f"Runs on the Quiddity dev machine at {p['path']}.",
                "license": "N/A",
                "version": "",
            },
        ],
        "descriptions": [
            {
                "title": "Stack details pending",
                "body": ("This is a seed entry. Replace with the real technology breakdown "
                         f"once the {p['name']} stack is finalised."),
            }
        ],
    }


def write_if_missing(path: Path, content):
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, str):
        path.write_text(content, encoding="utf-8")
    else:
        path.write_text(json.dumps(content, indent=2, ensure_ascii=False), encoding="utf-8")
    return True


def main():
    created = 0
    skipped = 0
    for pid, p in PROJECTS.items():
        intro = Path(p["path"]) / "INTRO"
        files = {
            "status_intro.md": status_intro_md(p),
            "status_documentation.json": status_documentation_json(p),
            "status_features_business.json": status_features_business_json(p),
            "status_features_dev.json": status_features_dev_json(p),
            "status_future.json": status_future_json(p),
            "status_techstack.json": status_techstack_json(p),
        }
        for name, body in files.items():
            if write_if_missing(intro / name, body):
                print(f"  CREATED  {intro / name}")
                created += 1
            else:
                print(f"  exists   {intro / name}")
                skipped += 1
    print(f"\nDone — {created} files created, {skipped} skipped.")


if __name__ == "__main__":
    main()

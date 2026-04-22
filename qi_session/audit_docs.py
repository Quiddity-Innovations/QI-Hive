# -*- coding: utf-8 -*-
"""
audit_docs.py — Audit standard documentation across all QI projects.
Searches recursively within each DOCUMENTATION folder.
Matching is flexible: strips underscores/spaces, case-insensitive.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path

PROJECTS = [
    {"name": "Maia",      "path": r"C:\QI\DOCUMENTATION"},
    {"name": "Naya",      "path": r"C:\NAYA\DOCUMENTATION"},
    {"name": "NEXUS",     "path": r"C:\NEXUS"},          # search whole project (docs in subdir)
    {"name": "OpenClaw",  "path": r"C:\OC\DOCUMENTATION"},
    {"name": "FileHQ",    "path": r"C:\NAYA\filehq\DOCUMENTATION"},
    {"name": "EasyFlow",  "path": r"C:\EasyFlow\DOCUMENTATION"},
    {"name": "Universal", "path": r"C:\UNIVERSAL\DOCUMENTATION"},
]

# Canonical names — we normalise (lowercase, strip spaces/underscores) before matching
REQUIRED = {
    "impl_log":    ["implementationlog", "implementationlog"],
    "minutes":     ["meetingminutes", "meetinglog"],
    "version":     ["versionhistory"],
    "status":      ["masterstatusreport", "masterstatusreport", "masterreport"],
}

REQUIRED_LABELS = {
    "impl_log": "Implementation Log",
    "minutes":  "Meeting Minutes",
    "version":  "Version History",
    "status":   "Master Status Report",
}

def normalise(name: str) -> str:
    return name.lower().replace("_", "").replace(" ", "").replace("-", "")

def find_doc(search_root: Path, tokens: list) -> str | None:
    """Search recursively for a file whose normalised name contains any token."""
    if not search_root.exists():
        return None
    for f in search_root.rglob("*"):
        if f.is_file() and f.suffix in {".md", ".docx", ".txt", ".rst"}:
            norm = normalise(f.name)
            if any(t in norm for t in tokens):
                return str(f.relative_to(search_root.parent.parent
                           if search_root.name != "DOCUMENTATION"
                           else search_root.parent))
    return None

print("=" * 62)
print("  QI DOCUMENTATION AUDIT  (flexible, recursive)")
print("=" * 62)

all_missing = {}

for proj in PROJECTS:
    name = proj["name"]
    doc_path = Path(proj["path"])
    print(f"\n{'─'*58}")
    print(f"  {name}")
    print(f"  {proj['path']}")
    print(f"{'─'*58}")

    if not doc_path.exists():
        print(f"  ❌  ROOT PATH DOES NOT EXIST")
        all_missing[name] = list(REQUIRED_LABELS.values()) + ["__root_missing__"]
        continue

    missing_for_proj = []
    for key, tokens in REQUIRED.items():
        label = REQUIRED_LABELS[key]
        found = find_doc(doc_path, tokens)
        if found:
            short = found if len(found) < 60 else "..." + found[-56:]
            print(f"  ✅  {label:30}  →  {short}")
        else:
            print(f"  ❌  {label:30}  MISSING")
            missing_for_proj.append(label)

    if missing_for_proj:
        all_missing[name] = missing_for_proj

print(f"\n{'='*62}")
print("  SUMMARY")
print(f"{'='*62}")

if not all_missing:
    print("\n  🎉  ALL PROJECTS — FULLY DOCUMENTED")
else:
    total_missing = sum(len(v) for v in all_missing.items())
    for proj, items in all_missing.items():
        clean = [i for i in items if not i.startswith("__")]
        if clean:
            print(f"\n  {proj}:")
            for item in clean:
                print(f"    ❌ {item}")

print(f"\n{'='*62}")

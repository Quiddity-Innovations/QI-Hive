# -*- coding: utf-8 -*-
"""Audit: which INTRO status files exist for every registered QI project.

The /project/<pid>/status page renders seven tabs, each backed by one file in
the project's INTRO folder. A missing file renders as an empty tab. This
script reports the full matrix so gaps can be filled deliberately rather than
discovered one click at a time.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding="utf-8")

import project_status as PS

FILES = [
    ("status_intro.md", "Overview"),
    ("status_features_business.json", "Feat-Biz"),
    ("status_features_dev.json", "Feat-Dev"),
    ("status_code.json", "Code"),
    ("status_future.json", "Future"),
    ("status_techstack.json", "TechStack"),
    ("status_documentation.json", "Docs"),
]


def main() -> None:
    entries = PS._all_project_entries()
    print(f"{len(entries)} projects known to the registry/PROJECT_INTRO\n")
    hdr = f"{'project':<22} {'INTRO exists':<12} " + " ".join(f"{lbl:<9}" for _f, lbl in FILES)
    print(hdr)
    print("-" * len(hdr))

    missing_counts = {f: 0 for f, _ in FILES}
    rows = []
    for pid, name, intro in sorted(entries):
        exists = intro.is_dir() if str(intro) else False
        marks = []
        for f, _lbl in FILES:
            ok = (intro / f).exists() if exists else False
            marks.append("OK" if ok else "--")
            if not ok:
                missing_counts[f] += 1
        rows.append((pid, exists, marks))
        print(f"{pid:<22} {('yes' if exists else 'NO'):<12} " +
              " ".join(f"{m:<9}" for m in marks))

    print("\nmissing per file:")
    for f, lbl in FILES:
        print(f"  {lbl:<10} {f:<32} missing in {missing_counts[f]}/{len(entries)}")

    complete = sum(1 for _p, e, m in rows if e and all(x == "OK" for x in m))
    none = sum(1 for _p, e, m in rows if not e or all(x == "--" for x in m))
    print(f"\nfully populated: {complete}   completely empty: {none}   "
          f"partial: {len(rows) - complete - none}")

    out = Path(r"C:\QIH\data\usage_archive\intro_audit.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(
        {"projects": [{"pid": p, "intro": e,
                       "files": {FILES[i][0]: m[i] == "OK" for i in range(len(FILES))}}
                      for p, e, m in rows]}, indent=2), encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()

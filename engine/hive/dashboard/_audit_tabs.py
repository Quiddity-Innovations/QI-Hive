# -*- coding: utf-8 -*-
"""Audit every project x every status tab for empty renders.

_audit_intro.py checks whether the backing FILE exists. This checks what the
page actually RENDERS — a file can exist and still produce an empty tab if it
parses to nothing, holds only placeholder rows, or errors out. Hits the live
dashboard the way a user would.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding="utf-8")

import project_status as PS

BASE = "http://127.0.0.1:8600"
TABS = ["overview", "features_business", "features_dev", "code",
        "future", "techstack", "docs"]

# The renderer's _empty() helper emits exactly this alert block and nothing
# else does. Matching it is precise; matching prose substrings is not — an
# earlier version flagged "no database" in a tech-stack row as "no data" and
# reported nine perfectly healthy tabs as empty.
EMPTY_MARKER = "alert alert-warning"


def fetch(url: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, str(e)


def main() -> None:
    projects = sorted({pid for pid, _n, _i in PS._all_project_entries()})
    print(f"auditing {len(projects)} projects x {len(TABS)} tabs "
          f"= {len(projects)*len(TABS)} renders\n")

    problems: dict[str, list[str]] = {}
    errors: list[str] = []
    for pid in projects:
        bad = []
        for tab in TABS:
            code, body = fetch(f"{BASE}/project/{pid}/status?tab={tab}&embed=1")
            if code != 200:
                errors.append(f"{pid}/{tab} HTTP {code}")
                bad.append(f"{tab}(HTTP{code})")
                continue
            if EMPTY_MARKER in body:
                bad.append(tab)
        if bad:
            problems[pid] = bad
        print(f"  {pid:<22} {'OK' if not bad else 'EMPTY: ' + ', '.join(bad)}")

    print(f"\nprojects with at least one empty tab: {len(problems)}/{len(projects)}")
    if errors:
        print(f"HTTP errors: {len(errors)}")
        for e in errors[:10]:
            print("  ", e)

    tally: dict[str, int] = {}
    for bad in problems.values():
        for t in bad:
            tally[t] = tally.get(t, 0) + 1
    print("\nempty count per tab:")
    for t in TABS:
        print(f"  {t:<20} {tally.get(t, 0)}")

    out = Path(r"C:\QIH\data\usage_archive\tab_audit.json")
    out.write_text(json.dumps({"problems": problems, "errors": errors}, indent=2),
                   encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()

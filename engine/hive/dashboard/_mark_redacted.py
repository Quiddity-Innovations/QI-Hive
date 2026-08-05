# -*- coding: utf-8 -*-
"""Flag code snippets whose verbatim text was altered by the name scrub.

_scrub_names.py enforces the no-real-names rule across INTRO docs. Nine of its
replacements landed inside `status_code.json` snippets, which are supposed to
be verbatim extracts from live source. Scrubbing them silently would leave the
documentation quoting code that does not exist — the source still contains the
original identifier.

Rather than choose between the naming rule and accuracy, keep the scrub and
say so: each affected snippet gets an explicit redaction note. A reader then
knows the excerpt is sanitised and that the underlying source differs.

Changing the source itself is deliberately NOT done here — those are string
literals inside persona prompts and identity guards, where editing text can
change model behaviour. That is an owner decision, not a documentation fix.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding="utf-8")

import project_status as PS

BACKUP_ROOT = Path(r"C:\QIH\data\usage_archive\name_scrub_backup_20260805_173311")
NOTE = ("  \n\n_Note: this excerpt is sanitised — identifiers naming the owner "
        "have been replaced with a generic term, per the project rule that no "
        "real person's name appears in documentation. The underlying source is "
        "unchanged._")


def main() -> None:
    changed = 0
    for pid, _name, intro in sorted(PS._all_project_entries()):
        if not str(intro):
            continue
        cur = intro / "status_code.json"
        bak = BACKUP_ROOT / pid / "status_code.json"
        if not cur.exists() or not bak.exists():
            continue

        old = json.loads(bak.read_text(encoding="utf-8"))
        new = json.loads(cur.read_text(encoding="utf-8"))

        # Index the pre-scrub snippets so we can tell which code actually moved.
        old_code: dict[str, str] = {}
        for s in old.get("sections", []):
            for sn in s.get("snippets", []):
                old_code[sn.get("title", "")] = sn.get("code", "")

        touched = False
        for s in new.get("sections", []):
            for sn in s.get("snippets", []):
                before = old_code.get(sn.get("title", ""), "")
                if not re.search(r"\bRenne\b", before):
                    continue
                expl = sn.get("explanation", "") or ""
                if "sanitised" in expl:
                    continue
                sn["explanation"] = expl + NOTE
                touched = True
                changed += 1
                print(f"  {pid:<18} {sn.get('title','')[:52]}")

        if touched:
            cur.write_text(json.dumps(new, indent=2, ensure_ascii=False),
                           encoding="utf-8")
            json.loads(cur.read_text(encoding="utf-8"))  # parse guard

    print(f"\nsnippets marked as redacted: {changed}")


if __name__ == "__main__":
    main()

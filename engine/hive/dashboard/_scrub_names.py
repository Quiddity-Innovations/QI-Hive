# -*- coding: utf-8 -*-
"""Remove real people's names from INTRO documentation surfaced by the dashboard.

Standing QI rule: no real person's name appears in UI, docs, examples or
placeholders in any project. An audit of the rendered Project Status tabs found
113 occurrences across 46 files in 18 projects.

Deliberately case-SENSITIVE on the capitalised forms. Filesystem paths and
identifiers use the lowercase spelling (``user_renne.md``,
``C:\\Users\\renne\\...``); those are functional references that would break if
rewritten, and they are not name-as-content usage. Prose, titles and table
cells are rewritten; paths are left exactly as they are.

Writes a timestamped backup of every file it touches and re-parses every JSON
file after rewriting, restoring from backup if the result would not parse.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding="utf-8")

import project_status as PS

BACKUP = Path(r"C:\QIH\data\usage_archive") / f"name_scrub_backup_{datetime.now():%Y%m%d_%H%M%S}"

# Order matters: multi-word forms first, then possessives, then bare names.
RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\*\*Renne\*\*"), "**Owner**"),
    (re.compile(r"\bRenne Santiago\b"), "the owner"),
    (re.compile(r"\bMari\s*\+\s*Urcil\b"), "VIP contacts"),
    (re.compile(r"\bRenne['\u2019]s\b"), "the owner's"),
    # Sentence-initial: keep the sentence grammatical.
    (re.compile(r"(?<=^)Renne\b"), "The owner"),
    (re.compile(r"(?<=\n)Renne\b"), "The owner"),
    (re.compile(r"(?<=[.!?]\s)Renne\b"), "The owner"),
    (re.compile(r"(?<=\|\s)Renne\b"), "The owner"),
    (re.compile(r"\bRenne\b"), "the owner"),
    (re.compile(r"\bSantiago\b"), "the owner"),
    (re.compile(r"\bUrcil\b"), "a VIP contact"),
    (re.compile(r"\bMari\b"), "a VIP contact"),
]


def scrub(text: str) -> tuple[str, int]:
    n = 0
    for rx, repl in RULES:
        text, k = rx.subn(repl, text)
        n += k
    return text, n


def main(apply: bool = True) -> None:
    BACKUP.mkdir(parents=True, exist_ok=True)
    total_files = total_hits = 0
    failed: list[str] = []

    for pid, _name, intro in sorted(PS._all_project_entries()):
        if not str(intro) or not intro.is_dir():
            continue
        for f in sorted(intro.iterdir()):
            if not f.is_file() or f.suffix.lower() not in (".json", ".md"):
                continue
            try:
                original = f.read_text(encoding="utf-8")
            except Exception:
                continue
            new, hits = scrub(original)
            if not hits:
                continue

            if apply:
                dest = BACKUP / pid
                dest.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest / f.name)
                f.write_text(new, encoding="utf-8")
                # A doc fix must never corrupt a file the dashboard parses.
                if f.suffix.lower() == ".json":
                    try:
                        json.loads(f.read_text(encoding="utf-8"))
                    except Exception as e:
                        shutil.copy2(dest / f.name, f)
                        failed.append(f"{pid}/{f.name}: {e}")
                        print(f"  RESTORED {pid}/{f.name} — would not parse: {e}")
                        continue
            total_files += 1
            total_hits += hits
            print(f"  {pid:<18} {f.name:<34} {hits:>3} replaced")

    print(f"\nfiles changed: {total_files}   occurrences replaced: {total_hits}")
    print(f"backup: {BACKUP}")
    if failed:
        print(f"FAILED (restored): {len(failed)}")
        for x in failed:
            print("  ", x)


if __name__ == "__main__":
    main(apply="--dry-run" not in sys.argv)

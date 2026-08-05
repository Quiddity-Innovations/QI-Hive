# -*- coding: utf-8 -*-
"""Commit exactly the files the name scrub changed — nothing else.

Several project repos carry unrelated uncommitted INTRO edits that predate this
work, so `git add INTRO` would sweep them in. The scrub's backup directory is
an exact manifest of what was touched, so drive the commit from that.

Per repo: branch -> add only the manifest paths -> commit -> merge --no-ff back
to the default branch -> delete the temp branch. Repos in a detached-HEAD or
otherwise odd state are skipped and reported rather than guessed at.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding="utf-8")

import project_status as PS

BACKUP = Path(r"C:\QIH\data\usage_archive\name_scrub_backup_20260805_173311")
BRANCH = "docs/scrub-real-names"

SUBJECT = "docs(intro): remove real names from Project Status documentation"
BODY = """Standing QI rule: no real person's name appears in UI, docs, examples or
placeholders in any project. An audit of the rendered Project Status tabs found
113 occurrences across 46 files in 18 projects, all of them visible on the live
dashboard.

Replaced with generic role terms ("the owner", "a VIP contact"). Deliberately
case-sensitive on the capitalised forms: filesystem paths and identifiers use
the lowercase spelling (user_renne.md, C:\\Users\\renne\\...) and are functional
references that would break if rewritten, so they are untouched.

Where a replacement landed inside a status_code.json snippet — those are
verbatim source extracts — the snippet now carries an explicit redaction note,
so the documentation does not silently misquote code that still contains the
original identifier. The source itself is unchanged: those are string literals
inside persona prompts and identity guards where editing text can change model
behaviour, which is an owner decision rather than a docs fix.

Verified: 196 rendered project/tab views scan clean for real names and NSFW
terms, and all 196 still render non-empty."""


def git(root: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", root, *args],
                          capture_output=True, text=True)


def main(apply: bool = True) -> None:
    intro = {pid: Path(i) for pid, _n, i in PS._all_project_entries() if str(i)}
    byrepo: dict[str, set[str]] = {}

    for pd in sorted(BACKUP.iterdir()):
        if not pd.is_dir() or pd.name not in intro:
            continue
        for f in sorted(pd.iterdir()):
            live = intro[pd.name] / f.name
            root = live
            while root != root.parent and not (root / ".git").is_dir():
                root = root.parent
            if not (root / ".git").is_dir():
                continue
            rel = os.path.relpath(str(live), str(root)).replace(os.sep, "/")
            byrepo.setdefault(str(root), set()).add(rel)

    print(f"{sum(len(v) for v in byrepo.values())} scrubbed files across "
          f"{len(byrepo)} repo(s)\n")

    for root, files in sorted(byrepo.items()):
        print("=" * 62)
        print(f"REPO: {root}  ({len(files)} file(s))")
        default = git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        if default in ("HEAD", ""):
            print("  SKIP — detached HEAD or unknown branch; not guessing")
            continue
        if not apply:
            for f in sorted(files):
                print("   ", f)
            continue

        git(root, "branch", "-D", BRANCH)
        git(root, "checkout", "-q", "-b", BRANCH)
        git(root, "add", "--", *sorted(files))
        staged = [x for x in git(root, "diff", "--cached", "--name-only")
                  .stdout.splitlines() if x.strip()]
        if not staged:
            print("  nothing staged (already committed?) — reverting")
            git(root, "checkout", "-q", default)
            git(root, "branch", "-D", BRANCH)
            continue
        for s in staged:
            print("    +", s)
        git(root, "commit", "-q", "-m", SUBJECT, "-m", BODY,
            "-m", "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>")
        git(root, "checkout", "-q", default)
        m = git(root, "merge", "--no-ff", BRANCH, "-m", f"Merge {BRANCH}: {SUBJECT}")
        if m.returncode != 0:
            print("  MERGE FAILED:", (m.stderr or m.stdout).strip()[:180])
            continue
        git(root, "branch", "-d", BRANCH)
        print(f"  merged -> {default}: "
              f"{git(root, 'log', '--oneline', '-1').stdout.strip()}")

    print("=" * 62)
    print("DONE")


if __name__ == "__main__":
    main(apply="--dry-run" not in sys.argv)

# -*- coding: utf-8 -*-
"""
personalsong_remediate.py — purge the live Plex token from PersonalSong git.

Steps (history rewrite — IRREVERSIBLE, approved by owner 2026-06-16):
  0. Safety backup: full `git bundle` + copy of the live config file.
  1. Remove config/app_config.json from ALL history via git-filter-repo.
  2. Re-add origin remote (filter-repo strips remotes by design).
  3. Restore the live config file on disk (now untracked + gitignored).
  4. Append the QI baseline ignore rules + write a sanitized template.
  5. Commit the gitignore/template.

Force-push is performed by the caller AFTER this script verifies the token is
gone from history.  This script does NOT push.
"""
from __future__ import annotations
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(r"C:\PersonalSong")
CFG = REPO / "config" / "app_config.json"
BK_DIR = Path(r"C:\QIH\logs\secret_audit")
ORIGIN = "https://github.com/Quiddity-Innovations/PersonalSong.git"
TOKEN = "tMU7Gz1URMdPsdXw52it"
BASELINE = Path(r"C:\QIH\ecosystem\QI_baseline.gitignore")


def run(*args, check=True, cwd=str(REPO)):
    print(">", " ".join(str(a) for a in args))
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.stdout.strip():
        print(r.stdout.strip()[:800])
    if r.returncode != 0:
        print("  ! " + r.stderr.strip()[:800])
        if check:
            raise SystemExit(f"FAILED: {' '.join(map(str,args))}")
    return r


def token_in_history() -> bool:
    r = subprocess.run(["git", "-C", str(REPO), "log", "-p", "--all", "-S", TOKEN],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return TOKEN in r.stdout


def main():
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    BK_DIR.mkdir(parents=True, exist_ok=True)

    print("=== 0. SAFETY BACKUP ===")
    if CFG.exists():
        shutil.copy2(CFG, BK_DIR / f"personalsong_app_config_{stamp}.json")
        print(f"  config backed up -> {BK_DIR}")
    bundle = BK_DIR / f"personalsong_pre_purge_{stamp}.bundle"
    run("git", "bundle", "create", str(bundle), "--all")
    print(f"  full repo bundle -> {bundle}")

    print("\n=== pre-state ===")
    print("token in history BEFORE:", token_in_history())

    print("\n=== 1. filter-repo: drop config/app_config.json from all history ===")
    run(sys.executable, "-m", "git_filter_repo",
        "--invert-paths", "--path", "config/app_config.json", "--force")

    print("\n=== 2. re-add origin (filter-repo strips it) ===")
    run("git", "remote", "remove", "origin", check=False)
    run("git", "remote", "add", "origin", ORIGIN)

    print("\n=== 3. restore live config on disk (untracked) ===")
    src = BK_DIR / f"personalsong_app_config_{stamp}.json"
    if src.exists():
        CFG.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, CFG)
        print(f"  restored {CFG}")

    print("\n=== 4. gitignore + sanitized template ===")
    gi = REPO / ".gitignore"
    existing = gi.read_text(encoding="utf-8", errors="replace") if gi.exists() else ""
    add = []
    for line in ["", "# --- QI baseline secret guard (added 2026-06-16) ---",
                 "config/app_config.json", "*config*.json",
                 "!*config*.template.json", "secrets/", "*.env", "!*.env.template"]:
        if line and line not in existing:
            add.append(line)
    if add:
        with open(gi, "a", encoding="utf-8") as f:
            f.write("\n" + "\n".join(add) + "\n")
        print("  appended ignore rules:", [a for a in add if a])

    tmpl = REPO / "config" / "app_config.template.json"
    if CFG.exists():
        sanitized = CFG.read_text(encoding="utf-8", errors="replace").replace(
            TOKEN, "REPLACE_WITH_YOUR_PLEX_TOKEN")
        tmpl.write_text(sanitized, encoding="utf-8")
        print(f"  wrote sanitized template -> {tmpl}")

    print("\n=== 5. commit gitignore + template ===")
    run("git", "add", ".gitignore", "config/app_config.template.json")
    run("git", "commit", "-m",
        "security: purge Plex token from history; ignore config; add template\n\n"
        "config/app_config.json removed from all history via git-filter-repo.\n"
        "Live config is now gitignored + untracked. Token must be rotated.\n\n"
        "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>", check=False)

    print("\n=== verify ===")
    print("token in history AFTER:", token_in_history())
    print("config tracked AFTER:",
          subprocess.run(["git", "-C", str(REPO), "ls-files", "config/app_config.json"],
                         capture_output=True, text=True).stdout.strip() or "(untracked - good)")
    print("\nDONE (not pushed). Caller must force-push after verifying.")


if __name__ == "__main__":
    main()

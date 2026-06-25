# -*- coding: utf-8 -*-
"""
Nightly git sync for QI repos that have no per-project sync of their own.

Mirrors what MaiaNightlySync does for C:\\QI, but generic: for each repo
below, stage everything (each repo's .gitignore is the safety boundary),
commit if there are changes, and push to origin.

Runs via Windows Scheduled Task QI_NightlyGitSync (12:35 AM, after
MaiaNightlySync at 12:30). Logs to C:\\QIH\\logs\\nightly_git_sync.log.
"""
from __future__ import annotations
import subprocess, sys
from datetime import datetime
from pathlib import Path

# Secret gate — abort a repo's commit/push if a real secret is staged.
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from secret_gate import scan_staged
except Exception:  # pragma: no cover - gate must never silently vanish
    scan_staged = None

REPOS = [
    r"C:\AutoPDF",
    r"C:\PersonalSong",
    r"C:\M2V",
]

LOG = Path(r"C:\QIH\logs\nightly_git_sync.log")
LOG.parent.mkdir(parents=True, exist_ok=True)


def log(msg: str):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def git(repo: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=600,
    )


def sync(repo: str):
    if not Path(repo, ".git").exists():
        log(f"SKIP {repo}: not a git repo")
        return
    git(repo, "add", "-A")
    # --- SECRET GATE: never commit/push a staged secret ---
    if scan_staged is None:
        git(repo, "reset")
        log(f"ABORT {repo}: secret_gate unavailable — refusing to sync blind")
        return
    findings = scan_staged(repo)
    if findings:
        git(repo, "reset")  # unstage everything; commit nothing
        names = ", ".join(sorted({f["pattern"] for f in findings}))
        log(f"ABORT {repo}: staged secret(s) detected [{names}] — "
            f"{len(findings)} hit(s). Nothing committed/pushed. Fix .gitignore.")
        return
    status = git(repo, "status", "--porcelain")
    if status.stdout.strip():
        msg = f"chore: nightly auto-sync {datetime.now().strftime('%Y-%m-%d')}"
        c = git(repo, "commit", "-m", msg)
        if c.returncode != 0:
            log(f"FAIL {repo}: commit: {c.stderr.strip()[:200]}")
            return
        log(f"{repo}: committed changes")
    else:
        log(f"{repo}: clean, nothing to commit")
    if git(repo, "remote", "get-url", "origin").returncode != 0:
        log(f"SKIP push {repo}: no origin remote")
        return
    p = git(repo, "push", "origin", "HEAD")
    if p.returncode == 0:
        log(f"{repo}: pushed")
    else:
        log(f"FAIL {repo}: push: {p.stderr.strip()[:200]}")


if __name__ == "__main__":
    log("=== nightly git sync start ===")
    for r in REPOS:
        try:
            sync(r)
        except Exception as e:
            log(f"FAIL {r}: {type(e).__name__}: {e}")
    log("=== nightly git sync done ===")

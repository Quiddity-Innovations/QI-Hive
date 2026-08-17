# -*- coding: utf-8 -*-
"""
Nightly git sync for QI repos that have no per-project sync of their own.

Mirrors what MaiaNightlySync does for C:\\APPS\\QI, but generic: for each repo
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
    r"C:\QIH",            # the Hive itself — added 2026-08-17 (audit: was absent, 304 files unprotected)
    r"C:\APPS\AutoPDF",
    r"C:\APPS\PersonalSong",
    r"C:\APPS\M2V",
]

# Repos that carry their own dedicated sync task — deliberately NOT synced here,
# so we don't double-commit. Used by the coverage check below.
EXTERNALLY_SYNCED = {
    r"C:\APPS\QI",        # MaiaNightlySync (12:30 AM)
}

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


def coverage_check():
    """Warn about registry projects that are git repos but sync nowhere.

    Added 2026-08-17. The audit found C:\\QIH missing from REPOS for months while
    this task still reported success nightly. Never let that be silent again:
    compare REPOS against qi_registry.json and log anything uncovered. This only
    WARNS — it never auto-commits a repo the owner hasn't opted in.
    """
    reg = Path(r"C:\QIH\ecosystem\qi_registry.json")
    if not reg.exists():
        log("WARN coverage_check: qi_registry.json not found — skipped")
        return
    try:
        import json
        projects = json.loads(reg.read_text(encoding="utf-8")).get("projects", [])
    except Exception as e:
        log(f"WARN coverage_check: could not parse registry: {e}")
        return
    covered = {p.casefold().rstrip("\\") for p in REPOS} | {
        p.casefold().rstrip("\\") for p in EXTERNALLY_SYNCED
    }
    uncovered = []
    for p in projects:
        path = (p.get("path") or "").rstrip("\\")
        if not path or path.casefold() in covered:
            continue
        if Path(path, ".git").exists():
            uncovered.append(f"{p.get('id')} ({path})")
    if uncovered:
        log(f"WARN {len(uncovered)} registry repo(s) sync nowhere: {', '.join(sorted(uncovered))}")
    else:
        log("coverage_check: every registry git repo is covered")


if __name__ == "__main__":
    log("=== nightly git sync start ===")
    for r in REPOS:
        try:
            sync(r)
        except Exception as e:
            log(f"FAIL {r}: {type(e).__name__}: {e}")
    coverage_check()
    log("=== nightly git sync done ===")

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

    # Added 2026-08-27 (task health audit). These 16 were flagged by
    # coverage_check() as "sync nowhere" every single night and nobody acted on
    # it. Each was verified first: is a git repo, HAS an origin remote, and a
    # dry-run `git add -A` + secret_gate scan came back with zero hits.
    r"C:\APPS\AvatarStudio",
    r"C:\APPS\CogniBase",
    r"C:\APPS\QIP\Connector",
    r"C:\APPS\CypherMiner",
    r"C:\Users\renne\Downloads\DIGITIZATION COSTS",
    r"C:\APPS\EasyFlow",
    r"C:\APPS\Gamez",
    r"C:\APPS\Lottery Wiz",
    r"C:\APPS\MapSnap",
    r"C:\APPS\MQ",
    r"C:\APPS\NAYA",
    r"C:\APPS\NEXUS",
    r"C:\APPS\NoosOrbis",
    r"C:\APPS\Retirement Analyzer",
    r"C:\APPS\SynVox",
    r"C:\APPS\TUBESCOUT",
]

# Deliberately NOT synced, with the reason. Silence here would repeat the very
# problem this audit was about, so anything left out gets named.
NOT_SYNCED = {
    # 38,499 files of a vendored virtualenv (Tools/headroom_env) are already
    # COMMITTED to this repo. .gitignore was updated 2026-08-27 so nothing new
    # gets added, but untracking what is already there is a ~38.5k-deletion
    # commit and that is Renne's call, not a side effect of enabling sync.
    # To clean it up and then add this repo to REPOS above:
    #     git -C "C:\APPS\CLAUDE" rm -r --cached "Tools/headroom_env"
    r"C:\APPS\CLAUDE": "vendored venv committed (38,499 files) — needs a decided cleanup first",

    # No origin remote configured, so there is nothing to push to.
    r"C:\APPS\AkiyaScout": "no git remote; also has zero commits",

    # The parent has no remote. Its repo/ subdirectory IS a separate clone
    # (rennesan/OC-Orchestrator) and is synced there instead.
    r"C:\APPS\OC": "no git remote on the parent; repo/ is its own clone and is synced separately",
}

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


def publish_qi_apply_branches():
    """Push auto-apply branches that the QI_HiveApply service committed locally.

    Added 2026-08-17 (Renne-approved). QI_HiveApply runs as LocalSystem, which has
    no GitHub credentials. Rather than give a SYSTEM-privileged service a
    write-scoped token, the service stops at a local commit on a qi-apply/* branch
    and marks the run 'applied_local'. This job — a scheduled task running as
    Renne, with a working Git Credential Manager session — publishes them.

    The trust boundary is the whole point: the component that can write code as
    SYSTEM never holds a credential that can reach GitHub. Publishing happens
    under Renne's own identity, on his schedule.

    Content is already mechanically inspected and hive-inspector-approved before
    it reaches 'applied_local', and every branch opens a PR rather than landing on
    master — so nothing here merges without a human.
    """
    import json as _json
    import sqlite3

    db = Path(r"C:\QIH\data\qi_brain.db")
    registry = Path(r"C:\QIH\ecosystem\qi_registry.json")
    if not db.exists():
        log("publish: qi_brain.db not found — skipped")
        return

    try:
        paths = {
            p["id"]: p["path"]
            for p in _json.loads(registry.read_text(encoding="utf-8")).get("projects", [])
            if p.get("id") and p.get("path")
        }
    except Exception as e:
        log(f"publish: cannot read registry: {e}")
        return

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT r.id, r.dispatch_id, r.meta, r.commit_sha, d.project_id, d.payload
           FROM dispatch_runs r
           JOIN dispatches d ON d.dispatch_id = r.dispatch_id
           WHERE r.state='applied_local'"""
    ).fetchall()

    if not rows:
        log("publish: no auto-apply branches awaiting publication")
        conn.close()
        return

    log(f"publish: {len(rows)} branch(es) awaiting publication")
    for row in rows:
        try:
            branch = (_json.loads(row["meta"]) or {}).get("branch") if row["meta"] else None
        except Exception:
            branch = None
        if not branch:
            log(f"publish SKIP {row['dispatch_id']}: no branch recorded in meta")
            continue

        repo = paths.get(row["project_id"])
        if not repo or not Path(repo, ".git").exists():
            log(f"publish SKIP {row['dispatch_id']}: no repo for project '{row['project_id']}'")
            continue

        # Branch must still exist locally — someone may have cleaned it up.
        if git(repo, "rev-parse", "--verify", branch).returncode != 0:
            log(f"publish SKIP {row['dispatch_id']}: branch {branch} no longer exists locally")
            continue

        p = git(repo, "push", "-u", "origin", branch)
        if p.returncode != 0:
            log(f"publish FAIL {row['dispatch_id']}: push {branch}: {p.stderr.strip()[:160]}")
            continue
        log(f"publish: pushed {branch}")

        try:
            payload = _json.loads(row["payload"]) if row["payload"] else {}
        except Exception:
            payload = {}
        category = payload.get("fix_category") or payload.get("check_id") or "auto-apply"
        title = f"qi-apply: {category} ({row['dispatch_id'][:8]})"
        body = "\n".join([
            "Auto-applied by QI_HiveApply, published by nightly_git_sync.",
            "",
            f"- Category: {category}",
            f"- Dispatch: {row['dispatch_id']}",
            f"- Commit: {row['commit_sha']}",
            "- Inspector verdict: pass (mechanical checks + hive-inspector)",
            "",
            "The apply service runs as LocalSystem and holds no GitHub credentials;",
            "it committed this locally and this job published it. Review before merging.",
        ])
        pr = subprocess.run(
            ["gh", "pr", "create", "--head", branch, "--title", title, "--body", body],
            cwd=repo, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=120,
        )
        already_open = "already exists" in (pr.stderr or "").lower()
        if pr.returncode != 0 and not already_open:
            # Push succeeded but the PR did not open — e.g. a transient GitHub 503,
            # which is exactly what happened on the first live run. Do NOT mark this
            # applied: that would strand a published branch with no PR and nothing
            # to retry it. Leaving it 'applied_local' makes the next run re-push
            # (a no-op) and retry the PR, so the job is self-healing.
            log(f"publish RETRY-LATER {row['dispatch_id']}: branch pushed but "
                f"gh pr create failed: {pr.stderr.strip()[:150]}")
            continue

        log(f"publish: PR ready for {branch} — {(pr.stdout or 'already open').strip()[:120]}")
        with conn:
            conn.execute(
                "UPDATE dispatch_runs SET state='applied' WHERE id=?", (row["id"],)
            )
            conn.execute(
                "UPDATE dispatches SET apply_state='applied' WHERE dispatch_id=?",
                (row["dispatch_id"],),
            )
    conn.close()


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
    try:
        publish_qi_apply_branches()
    except Exception as e:
        log(f"FAIL publish_qi_apply_branches: {type(e).__name__}: {e}")
    coverage_check()
    log("=== nightly git sync done ===")

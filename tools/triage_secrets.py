# -*- coding: utf-8 -*-
"""
triage_secrets.py — classify each secret-bearing path by REAL exposure.

Reads audit_latest.json and, for every finding, determines:
  TRACKED_TIP        — file is tracked at HEAD (committed, in repo now)
  IN_PUSHED_HISTORY  — the secret's commit is reachable from a remote branch
  HISTORY_LOCAL      — in history but repo has NO remote (never pushed)
  IGNORED_LOCAL      — in working tree but gitignored / never committed
  FALSE_POSITIVE     — known non-secret (ffmpeg doc text, etc.)

This is what separates "rotate + purge + force-push now" from "harmless local".
"""
from __future__ import annotations
import json
import subprocess
from pathlib import Path

AUDIT = Path(r"C:\QIH\logs\secret_audit\audit_latest.json")
OUT = Path(r"C:\QIH\logs\secret_audit\triage_latest.json")

# Known false-positive substrings (the ffmpeg mailing-list phrase, etc.)
FP_MARKERS = [
    "send-a-message-to-a-mailing-list",
    "sk-a-question",
]


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace",
                          timeout=120)


def is_tracked(repo, relpath):
    # normalize backslashes to forward slashes for git
    rp = relpath.replace("\\", "/")
    r = git(repo, "ls-files", "--error-unmatch", rp)
    return r.returncode == 0


def commit_pushed(repo, commit, has_remote):
    if not has_remote:
        return False
    r = git(repo, "branch", "-r", "--contains", commit)
    return bool(r.stdout.strip())


def main():
    data = json.loads(AUDIT.read_text(encoding="utf-8"))
    triaged = []
    for rec in data:
        repo = rec["path"]
        rid = rec["id"]
        if rec.get("error"):
            continue
        has_remote = bool(rec.get("remote"))
        # de-dup worktree findings by (pattern, match, source-file-basename intent)
        seen = set()
        items = []
        for h in rec["worktree_hits"]:
            if h["pattern"] == "_truncated":
                continue
            src = h["source"]
            # collapse the many .claude/worktrees + Maia_Archive duplicates
            key = (h["pattern"], h["match"], src.split("\\")[0])
            if key in seen:
                continue
            seen.add(key)
            cls = "IGNORED_LOCAL"
            if any(fp in h["match"] for fp in FP_MARKERS):
                cls = "FALSE_POSITIVE"
            elif is_tracked(repo, src):
                cls = "TRACKED_TIP"
            items.append({**h, "exposure": cls, "first_seen": src})
        for h in rec["history_hits"]:
            if h["pattern"] == "_truncated":
                continue
            if any(fp in h["match"] for fp in FP_MARKERS):
                cls = "FALSE_POSITIVE"
            elif commit_pushed(repo, h["source"], has_remote):
                cls = "IN_PUSHED_HISTORY"
            else:
                cls = "HISTORY_LOCAL"
            items.append({**h, "exposure": cls})
        triaged.append({"id": rid, "path": repo, "visibility": rec["visibility"],
                        "has_remote": has_remote,
                        "remote_has_creds": rec["remote_has_creds"],
                        "findings": items})

    OUT.write_text(json.dumps(triaged, indent=2), encoding="utf-8")

    print("=== EXPOSURE TRIAGE (real risk only) ===\n")
    order = {"IN_PUSHED_HISTORY": 0, "TRACKED_TIP": 1, "HISTORY_LOCAL": 2,
             "IGNORED_LOCAL": 3, "FALSE_POSITIVE": 4}
    for rec in triaged:
        real = [f for f in rec["findings"]
                if f["exposure"] in ("IN_PUSHED_HISTORY", "TRACKED_TIP", "HISTORY_LOCAL")]
        if not real and not rec["remote_has_creds"]:
            continue
        print(f"### {rec['id']}  [{rec['visibility']}]  remote_creds={rec['remote_has_creds']}")
        for f in sorted(real, key=lambda x: order.get(x["exposure"], 9)):
            print(f"   {f['exposure']:18} {f['severity']:8} {f['pattern']:18} "
                  f"{f.get('first_seen', f['source'])[:46]:46} :: {f['match'][:50]}")
        print()

    print("=== COUNTS BY EXPOSURE ===")
    from collections import Counter
    c = Counter()
    for rec in triaged:
        for f in rec["findings"]:
            c[f["exposure"]] += 1
    for k, v in sorted(c.items(), key=lambda x: order.get(x[0], 9)):
        print(f"  {k:18} {v}")
    print(f"\nJSON: {OUT}")


if __name__ == "__main__":
    main()

"""After the NEXUS rename ran and was verified: commit ONLY the rename edits.

For each changed file, the staged content is HEAD's version with the rename
applied, so any other uncommitted work in the same file (e.g. another
session's edits to qi_registry.json) stays uncommitted and untouched.
"""
import subprocess, sys
from collections import defaultdict
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import apply_refs as ar  # noqa: E402

MSG = ("chore(ops): rename NEXUS services to QI_<App>_<Function> (rename wave 1)\n\n"
       "QI_NEXUS -> QI_NEXUS_Server, QI_NEXUSTunnel -> QI_NEXUS_Tunnel,\n"
       "QI_NexusMCP -> QI_NEXUS_MCP (Renne, 2026-09-24). Services were rebuilt from\n"
       "their own nssm dump; only the name references change here.\n\n"
       "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")

def git(repo, *a, inp=None):
    return subprocess.run(["git", "-C", repo, *a], input=inp, capture_output=True)

by_repo = defaultdict(list)
for f in ar.FILES:
    top = git(str(Path(f).parent), "rev-parse", "--show-toplevel").stdout.decode().strip()
    if top:
        by_repo[top].append(f)

for repo, files in by_repo.items():
    staged = 0
    for f in files:
        rel = Path(f).resolve().relative_to(Path(repo).resolve()).as_posix()
        head = git(repo, "show", f"HEAD:{rel}")
        if head.returncode:
            print(f"  untracked, skipped: {f}"); continue
        raw = head.stdout
        bom = raw.startswith(b"\xef\xbb\xbf")
        text = (raw[3:] if bom else raw).decode("utf-8")
        new, n = ar.rename_text(text)
        if not n:
            continue
        blob = git(repo, "hash-object", "-w", "--stdin", inp=(b"\xef\xbb\xbf" if bom else b"") + new.encode("utf-8"))
        sha = blob.stdout.decode().strip()
        mode = git(repo, "ls-files", "-s", "--", rel).stdout.decode().split()[0]
        git(repo, "update-index", "--cacheinfo", f"{mode},{sha},{rel}")
        staged += 1
    if staged:
        c = git(repo, "commit", "-q", "-m", MSG)
        head = git(repo, "log", "--oneline", "-1").stdout.decode().strip()
        print(f"{repo}: {staged} files -> {head if c.returncode == 0 else 'COMMIT FAILED ' + c.stderr.decode()[:200]}")

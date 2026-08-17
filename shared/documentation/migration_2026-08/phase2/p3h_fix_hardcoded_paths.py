"""Phase 3h - repoint interpreter paths hardcoded in live scripts and hooks.

Root cause of the respawning stragglers:

  .claude/settings.json hooks invoke C:\\1-AI\\APPS\\PYTHON\\python.exe directly.
  session_hook.py then spawns the Claude Voice supervisor using sys.executable -
  which is, correctly, whatever interpreter ran the hook. So the dead path
  propagates from the hook down into every helper process.

Fixing the hooks fixes the whole chain. Also repoints the Claude Voice .bat
launchers and a handful of tool scripts.

Deliberately NOT touched: archives, backups, logs, git worktrees, .old venvs,
this migration's own records, and dist/ build output. Rewriting those would
falsify history or edit artifacts that are regenerated anyway.
"""
import argparse
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")

OLD_PATTERNS = [
    ("C:\\\\1-AI\\\\APPS\\\\PYTHON", "C:\\\\Program Files\\\\Python311"),  # JSON-escaped
    ("C:\\1-AI\\APPS\\PYTHON", "C:\\Program Files\\Python311"),            # raw backslash
    ("C:/1-AI/APPS/PYTHON", "C:/Program Files/Python311"),                 # forward slash
    ("C:\\1-AI\\Apps\\Python", "C:\\Program Files\\Python311"),            # alt casing
    ("C:/1-AI/Apps/Python", "C:/Program Files/Python311"),
]

SEARCH_ROOTS = [
    r"C:\CLAUDE", r"C:\OC", r"C:\QIH", r"C:\QI", r"C:\NAYA", r"C:\NEXUS",
    r"C:\AutoPDF", r"C:\CogniBase", r"C:\EasyFlow", r"C:\MailBrain",
    r"C:\MapSnap", r"C:\MQ", r"C:\Gamez", r"C:\TUBESCOUT", r"C:\CypherMiner",
    r"C:\PlayDeck", r"C:\QIP", r"C:\M2V", r"C:\PersonalSong",
    r"C:\Users\renne\.claude",
]

EXTS = {".json", ".bat", ".cmd", ".ps1", ".py", ".ini", ".cfg", ".env", ".toml"}

SKIP = (
    "\\site-packages\\", "\\node_modules\\", "\\.git\\", "\\worktrees\\",
    "\\.venv\\", "\\venv\\", "\\dist\\", "\\build\\", "\\__pycache__\\",
    "\\migration_2026-08\\", "\\usage_archive\\", "\\commands\\archive\\",
    "\\reports\\archive\\", "\\logs\\", "\\LOGS\\", ".old\\", "_BACKUP",
    "\\project_library_BACKUP", "\\.claude\\projects\\", "\\shell-snapshots\\",
    "\\todos\\", "\\statsig\\",
    # Session bookkeeping, not executable config. These task records quote the
    # old path in their descriptions on purpose; rewriting them would corrupt
    # task state and falsify the migration's own history.
    "\\.claude\\tasks\\", "\\history\\", "\\ide\\",
)


def skip(path):
    low = path.lower() + ""
    return any(s.lower() in low for s in SKIP)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    hits = []
    for root in SEARCH_ROOTS:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            if skip(dirpath + "\\"):
                dirnames[:] = []
                continue
            for fn in filenames:
                if os.path.splitext(fn)[1].lower() not in EXTS:
                    continue
                # A venv is repointed by recreating it, not by editing its
                # config: rewriting pyvenv.cfg alone leaves every Scripts\*.exe
                # launcher still naming the old base. The junction bridge
                # covers these until they are rebuilt.
                if fn.lower() == "pyvenv.cfg":
                    continue
                full = os.path.join(dirpath, fn)
                if skip(full):
                    continue
                try:
                    if os.path.getsize(full) > 2_000_000:
                        continue
                    text = open(full, encoding="utf-8", errors="replace").read()
                except OSError:
                    continue
                if "1-AI" not in text:
                    continue
                n = sum(text.count(o) for o, _ in OLD_PATTERNS)
                if n:
                    hits.append((full, n, text))

    hits.sort(key=lambda x: -x[1])
    print("files with a hardcoded old interpreter path: %d" % len(hits))
    print()
    for full, n, _ in hits:
        print("  %2d  %s" % (n, full))

    if not args.apply:
        print()
        print("DRY RUN - re-run with --apply to rewrite.")
        return 0

    print()
    print("=== rewriting ===")
    changed = 0
    for full, n, text in hits:
        new = text
        for old, rep in OLD_PATTERNS:
            new = new.replace(old, rep)
        if new == text:
            continue
        bak = full + ".bak-phase3h"
        if not os.path.exists(bak):
            shutil.copy2(full, bak)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(new)
        changed += 1
        print("  rewrote %s" % full)

    print()
    print("files rewritten: %d" % changed)

    # verify
    print()
    print("=== verify ===")
    left = 0
    for full, _, _ in hits:
        try:
            t = open(full, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        if any(o in t for o, _ in OLD_PATTERNS):
            left += 1
            print("  STILL STALE: %s" % full)
    print("  files still stale: %d" % left)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

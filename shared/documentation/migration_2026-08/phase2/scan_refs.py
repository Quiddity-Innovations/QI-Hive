"""Count references to each C:-root project folder across config and doc files.

Feeds Phase 4: every hit is a reference that must be rewritten when the folder
moves to C:\\APPS\\<app>. Output is a compact per-folder tally plus the files
holding the most references.
"""
import collections
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

TARGETS = [
    "1-AI", "AkiyaScout", "AutoPDF", "CLAUDE", "CogniBase", "CypherMiner",
    "EasyFlow", "Gamez", "Lottery Wiz", "M2V", "MailBrain", "MapSnap", "MQ",
    "NAYA", "NEXUS", "OC", "PersonalSong", "PlayDeck", "QI", "QIB", "QIH",
    "QIP", "Retirement Analyzer", "RetirementAnalyzer", "SCRIPTS", "TUBESCOUT",
    "VLCDaemon", "GOOSE", "ARCHIVE",
]

SEARCH_ROOTS = [
    r"C:\QIH", r"C:\QI", r"C:\NAYA", r"C:\NEXUS", r"C:\OC", r"C:\MQ",
    r"C:\EasyFlow", r"C:\AutoPDF", r"C:\CogniBase", r"C:\MapSnap", r"C:\M2V",
    r"C:\CypherMiner", r"C:\Lottery Wiz", r"C:\TUBESCOUT", r"C:\Gamez",
    r"C:\PlayDeck", r"C:\AkiyaScout", r"C:\PersonalSong", r"C:\CLAUDE",
    r"C:\QIP", r"C:\Retirement Analyzer",
]

EXTS = {".md", ".json", ".yml", ".yaml", ".py", ".ps1", ".bat", ".cmd",
        ".cfg", ".ini", ".toml", ".txt", ".env"}

SKIP_PARTS = ("node_modules", "site-packages", "\\.git\\", "\\.venv\\",
              "\\venv\\", "__pycache__", "\\logs\\", "\\LOGS\\", "\\dist\\",
              "\\build\\", "\\.next\\", "\\models\\")

# Longest names first so "Retirement Analyzer" wins over "Retirement".
patterns = {
    t: re.compile(r"[Cc]:[\\/]" + re.escape(t) + r"(?![A-Za-z0-9_-])")
    for t in TARGETS
}

tally = collections.Counter()
per_file = collections.Counter()
file_targets = collections.defaultdict(set)

for root in SEARCH_ROOTS:
    if not os.path.isdir(root):
        continue
    for dirpath, dirnames, filenames in os.walk(root):
        low = dirpath.lower() + "\\"
        if any(p.lower() in low for p in SKIP_PARTS):
            dirnames[:] = []
            continue
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() not in EXTS:
                continue
            full = os.path.join(dirpath, fn)
            try:
                if os.path.getsize(full) > 3_000_000:
                    continue
                text = open(full, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            n = 0
            for t, pat in patterns.items():
                c = len(pat.findall(text))
                if c:
                    tally[t] += c
                    n += c
                    file_targets[full].add(t)
            if n:
                per_file[full] = n

print("=" * 72)
print("REFERENCES PER TARGET FOLDER")
print("=" * 72)
for t, c in tally.most_common():
    print("  %-24s %5d" % (t, c))

print()
print("=" * 72)
print("TOP 30 FILES BY REFERENCE COUNT")
print("=" * 72)
for f, c in per_file.most_common(30):
    print("  %4d  %s" % (c, f))
    print("        -> " + ", ".join(sorted(file_targets[f])[:8]))

print()
print("files with at least one reference: %d" % len(per_file))
print("total references                 : %d" % sum(tally.values()))

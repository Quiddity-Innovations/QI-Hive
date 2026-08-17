"""Find every venv on C: and report which interpreter it was built from.

Any venv whose 'home' points at C:\\1-AI\\APPS\\PYTHON must be recreated
before C:\\1-AI can be deleted.
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

SKIP_TOP = {
    "Windows", "Program Files", "Program Files (x86)", "$Recycle.Bin",
    "System Volume Information", "ProgramData", "PerfLogs", "Recovery",
}
SKIP_DIR_PARTS = ("node_modules", "site-packages", "\\.git", "\\1-ai\\apps\\python")

found = []
root = "C:\\"

for base in sorted(os.listdir(root)):
    if base in SKIP_TOP:
        continue
    top = os.path.join(root, base)
    if not os.path.isdir(top):
        continue
    for dirpath, dirnames, filenames in os.walk(top, topdown=True):
        low = dirpath.lower()
        if any(part in low for part in SKIP_DIR_PARTS):
            dirnames[:] = []
            continue
        if "pyvenv.cfg" in filenames:
            cfg = os.path.join(dirpath, "pyvenv.cfg")
            try:
                text = open(cfg, encoding="utf-8", errors="replace").read()
            except OSError as exc:
                text = "ERROR " + str(exc)
            found.append((dirpath, text))
            dirnames[:] = []   # do not descend into a venv

stale = []
print("=" * 78)
print("VENVS FOUND")
print("=" * 78)
for path, text in found:
    home = ""
    for line in text.splitlines():
        if line.lower().startswith("home"):
            home = line.split("=", 1)[-1].strip()
    old = "1-ai" in text.lower()
    if old:
        stale.append(path)
    print(("  [STALE] " if old else "  [ ok  ] ") + path)
    print("           home = " + (home or "?"))

print()
print("total venvs      : %d" % len(found))
print("pointing at 1-AI : %d" % len(stale))
print()
for p in stale:
    print("  MUST RECREATE: " + p)

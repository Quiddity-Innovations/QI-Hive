"""Make D:\\AI\\models the single physical home for every model file.

extra_model_paths.yaml only tells ComfyUI where to *look*. Anything that writes
a model — Manager's downloader, a custom node fetching its own weights — uses
the install's internal models folder, which is how duplicate copies of very
large files appear. Replacing that folder with a junction removes the second
location entirely: there is one directory, reachable by two names.
"""
import subprocess, sys, shutil
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

INTERNAL = Path(r"D:\AI\ComfyUI_windows_portable\ComfyUI\models")
CANON = Path(r"D:\AI\models")


def tally(p: Path):
    n = b = 0
    for f in p.rglob("*"):
        if f.is_file():
            n += 1
            try:
                b += f.stat().st_size
            except OSError:
                pass
    return n, b


if not INTERNAL.exists():
    print("internal models folder missing — nothing to do")
    sys.exit(0)

# Already a junction/symlink? Then this has run before.
if INTERNAL.is_symlink() or (INTERNAL.exists() and not INTERNAL.is_dir()):
    print("already linked")
    sys.exit(0)

print("merging shipped files into the canonical store:")
moved = 0
for src in INTERNAL.rglob("*"):
    if not src.is_file():
        continue
    rel = src.relative_to(INTERNAL)
    dst = CANON / rel
    if dst.exists():
        continue                      # canonical copy wins
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    moved += 1
    if src.stat().st_size > 1_000_000:
        print(f"    {rel}  ({src.stat().st_size/1e6:.1f} MB)")
print(f"  {moved} file(s) merged")

before = tally(INTERNAL)
subprocess.run(["cmd", "/c", "rd", "/s", "/q", str(INTERNAL)],
               capture_output=True, timeout=600)
if INTERNAL.exists():
    print("  FAILED to remove internal folder — aborting, nothing linked")
    sys.exit(1)

r = subprocess.run(["cmd", "/c", "mklink", "/J", str(INTERNAL), str(CANON)],
                   capture_output=True, text=True, timeout=60)
print(f"\n  junction: {r.stdout.strip() or r.stderr.strip()}")

# Prove both names now resolve to the same content.
a = tally(INTERNAL)
b = tally(CANON)
print(f"  via internal path : {a[0]} files / {a[1]/1e9:.2f} GB")
print(f"  via canonical path: {b[0]} files / {b[1]/1e9:.2f} GB")
print(f"  SAME STORE: {a == b}")

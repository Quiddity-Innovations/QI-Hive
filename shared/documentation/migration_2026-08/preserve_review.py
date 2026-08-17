"""Move everything worth keeping out of C:\\1-AI before the ComfyUI folder goes.

robocopy is invoked without a shell — Git Bash rewrites /E and /MOVE into
drive paths, which silently turned an earlier copy into a no-op.
"""
import subprocess, sys, shutil
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REVIEW = Path(r"D:\Review")
OLD = Path(r"C:\1-AI\APPS\ComfyUI")
NEW_USER = Path(r"D:\AI\ComfyUI_windows_portable\ComfyUI\user\default\workflows")

# (source, destination, move?)  — move only what is genuinely redundant on C:
JOBS = [
    (Path(r"C:\1-AI\models\huggingface"), REVIEW / "huggingface_cache", True),
    (Path(r"C:\1-AI\APPS\Easy Diffusion Tutorials Etc"), REVIEW / "EasyDiffusion_Tutorials", True),
    (OLD / "output", REVIEW / "ComfyUI_old" / "output", True),
    (OLD / "user", REVIEW / "ComfyUI_old" / "user", True),
    (OLD / "input", REVIEW / "ComfyUI_old" / "input", True),
    (OLD / "Workflows", REVIEW / "ComfyUI_old" / "Workflows", True),
]


def size_of(p: Path) -> tuple:
    if not p.exists():
        return 0, 0
    n = b = 0
    for f in p.rglob("*"):
        if f.is_file():
            n += 1
            try:
                b += f.stat().st_size
            except OSError:
                pass
    return n, b


REVIEW.mkdir(parents=True, exist_ok=True)
print(f"review folder: {REVIEW}\n")

for src, dst, move in JOBS:
    if not src.exists():
        print(f"  SKIP  {src}  (not present)")
        continue
    n, b = size_of(src)
    dst.mkdir(parents=True, exist_ok=True)
    args = ["robocopy", str(src), str(dst), "/E", "/R:1", "/W:1",
            "/NFL", "/NDL", "/NP", "/NJH", "/NJS"]
    if move:
        args.append("/MOVE")
    r = subprocess.run(args, capture_output=True, text=True, timeout=3600)
    # robocopy: <8 is success, >=8 is a real failure
    ok = r.returncode < 8
    dn, db = size_of(dst)
    print(f"  {'OK  ' if ok else 'FAIL'}  {src.name:<28} {n:>4} files / {b/1e6:8.1f} MB "
          f"-> {dn} files / {db/1e6:.1f} MB  (rc={r.returncode})")

# Carry the hand-built workflows into the new install so they are usable there.
saved = REVIEW / "ComfyUI_old" / "user" / "default" / "workflows"
if saved.is_dir():
    NEW_USER.mkdir(parents=True, exist_ok=True)
    copied = 0
    for wf in saved.glob("*.json"):
        shutil.copy2(wf, NEW_USER / wf.name)
        copied += 1
    print(f"\n  carried {copied} saved workflows into the new install:")
    for wf in sorted(NEW_USER.glob("*.json")):
        print(f"      {wf.name}")

print("\n--- what remains in C:\\1-AI\\APPS\\ComfyUI ---")
if OLD.exists():
    for child in sorted(OLD.iterdir()):
        if child.is_dir():
            n, b = size_of(child)
            if b > 1e6:
                print(f"    {child.name:<20} {b/1e9:7.2f} GB")

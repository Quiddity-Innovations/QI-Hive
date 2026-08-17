"""Install the custom nodes the enhancement pipeline needs, into the new
portable ComfyUI. Clones, then installs each pack's requirements against the
embedded Python (3.13) and reports honestly on what failed.
"""
import subprocess, sys, os
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"D:\AI\ComfyUI_windows_portable")
NODES = ROOT / "ComfyUI" / "custom_nodes"
PY = ROOT / "python_embeded" / "python.exe"

REPOS = [
    # (folder, url, why)
    ("ComfyUI-Manager", "https://github.com/Comfy-Org/ComfyUI-Manager",
     "install/manage further nodes from the UI"),
    ("ComfyUI-VideoHelperSuite", "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite",
     "load and write video files"),
    ("ComfyUI-KJNodes", "https://github.com/kijai/ComfyUI-KJNodes",
     "image/video utility nodes"),
    # Not in the 'minimal' list I quoted, but the approved RIFE checkpoint is
    # inert without it — this pack is what provides the interpolation nodes.
    ("ComfyUI-Frame-Interpolation", "https://github.com/Fannovel16/ComfyUI-Frame-Interpolation",
     "RIFE frame interpolation (required by the approved RIFE model)"),
]

NODES.mkdir(parents=True, exist_ok=True)
results = []

for folder, url, why in REPOS:
    dest = NODES / folder
    print(f"\n=== {folder} — {why}", flush=True)
    if dest.exists():
        print("   already present, skipping clone", flush=True)
        cloned = True
    else:
        r = subprocess.run(["git", "clone", "--depth", "1", url, str(dest)],
                           capture_output=True, text=True, timeout=600)
        cloned = r.returncode == 0
        print(f"   clone: {'ok' if cloned else 'FAILED'}", flush=True)
        if not cloned:
            print("   ", (r.stderr or "")[-300:], flush=True)
    if not cloned:
        results.append((folder, "clone failed", ""))
        continue

    req = dest / "requirements.txt"
    if not req.is_file():
        results.append((folder, "installed", "no requirements.txt"))
        continue
    r = subprocess.run([str(PY), "-s", "-m", "pip", "install", "-r", str(req),
                        "--no-warn-script-location"],
                       capture_output=True, text=True, timeout=1800)
    ok = r.returncode == 0
    note = ""
    if not ok:
        tail = (r.stderr or r.stdout or "").strip().splitlines()
        note = " | ".join(tail[-3:])[:220]
    print(f"   deps : {'ok' if ok else 'FAILED'}", flush=True)
    if note:
        print("   ", note, flush=True)
    results.append((folder, "installed" if ok else "deps failed", note))

print("\n" + "=" * 70)
for folder, status, note in results:
    mark = "OK  " if status == "installed" else "WARN"
    print(f"  {mark} {folder:<32} {status} {note[:80]}")

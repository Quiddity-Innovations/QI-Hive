"""Preserve the last weights, re-verify the model copy, then remove the old
ComfyUI. The verification is deliberately repeated here: this is the one step
in the whole migration that cannot be undone.
"""
import subprocess, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

OLD = Path(r"C:\1-AI\APPS\ComfyUI")
SRC_MODELS = OLD / "models"
DST_MODELS = Path(r"D:\AI\models")
REVIEW = Path(r"D:\Review\ComfyUI_old")
LATENTSYNC = OLD / "custom_nodes" / "ComfyUI-LatentSyncWrapper" / "checkpoints"


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


# 1. the lip-sync weights are re-downloadable but slow; park them for review
if LATENTSYNC.is_dir():
    dst = REVIEW / "LatentSync_checkpoints"
    dst.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["robocopy", str(LATENTSYNC), str(dst), "/E", "/MOVE",
                        "/R:1", "/W:1", "/NFL", "/NDL", "/NP", "/NJH", "/NJS"],
                       capture_output=True, text=True, timeout=3600)
    n, b = tally(dst)
    print(f"  LatentSync checkpoints -> review: {n} files / {b/1e9:.2f} GB (rc={r.returncode})")

# 2. re-verify immediately before the irreversible step.
#    The test is containment, not equality: D: legitimately holds extra files
#    (the upscaler downloaded after the copy). What matters is that nothing on
#    C: is missing from D:, at a matching size.
missing = []
for f in SRC_MODELS.rglob("*"):
    if not f.is_file():
        continue
    rel = f.relative_to(SRC_MODELS)
    target = DST_MODELS / rel
    try:
        if not target.is_file() or target.stat().st_size != f.stat().st_size:
            missing.append(str(rel))
    except OSError as exc:
        missing.append(f"{rel} ({exc})")

sn, sb = tally(SRC_MODELS)
dn, db = tally(DST_MODELS)
print(f"\n  C: models {sn} files / {sb/1e9:.2f} GB")
print(f"  D: models {dn} files / {db/1e9:.2f} GB  (extra on D: is expected)")
if missing:
    print(f"\n  ABORT — {len(missing)} file(s) on C: are missing or differ on D::")
    for m in missing[:10]:
        print(f"      {m}")
    sys.exit(1)
print(f"  every one of the {sn} source files is present on D: at the same size\n")

# 3. remove. rd is markedly faster than Remove-Item on a tree this size.
before = tally(OLD)
print(f"  deleting {OLD} ({before[1]/1e9:.1f} GB, {before[0]} files)...", flush=True)
r = subprocess.run(["cmd", "/c", "rd", "/s", "/q", str(OLD)],
                   capture_output=True, text=True, timeout=3600)
print(f"  rd exit: {r.returncode} {(r.stderr or '').strip()[:200]}")
print(f"  gone: {not OLD.exists()}")

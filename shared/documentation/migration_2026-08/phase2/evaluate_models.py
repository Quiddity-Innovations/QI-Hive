"""Evaluate whether anything under C:\\1-AI is a model asset worth keeping.

Renne asked: from the HuggingFace 'critical find', move anything usable by
ComfyUI into the right ComfyUI folder, but evaluate first.

So: inventory every model-shaped file in C:\\1-AI (not just models\\), classify
it, and compare against what ComfyUI already has under D:\\AI\\models.
"""
import os
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")

SCAN_ROOT = r"C:\1-AI"
COMFY_MODELS = r"D:\AI\models"

# Extensions that are actually model weights / usable assets.
WEIGHTS = {
    ".safetensors": "weights",
    ".ckpt": "weights",
    ".pt": "weights",
    ".pth": "weights",
    ".bin": "weights (may also be tokenizer/other)",
    ".gguf": "quantised LLM",
    ".onnx": "ONNX model",
    ".vae": "VAE",
    ".lora": "LoRA",
    ".engine": "TensorRT engine",
    ".msgpack": "flax weights",
}
# Things that look model-ish but are caches/metadata -> discardable.
NOISE_DIRS = ("__pycache__", "site-packages", "http-v2", "selfcheck",
              ".git", "node_modules")

MIN_INTERESTING = 1 * 1024 * 1024      # 1 MB - below this it is not a weight


def human(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return "%.1f %s" % (n, u)
        n /= 1024
    return "%.1f TB" % n


print("=" * 78)
print("SCANNING " + SCAN_ROOT + " FOR MODEL ASSETS")
print("=" * 78)

found = []
skipped_noise = 0
total_bytes = 0

for dirpath, dirnames, filenames in os.walk(SCAN_ROOT):
    low = dirpath.lower()
    if any(n in low for n in NOISE_DIRS):
        dirnames[:] = []
        skipped_noise += 1
        continue
    for fn in filenames:
        ext = os.path.splitext(fn)[1].lower()
        if ext not in WEIGHTS:
            continue
        full = os.path.join(dirpath, fn)
        try:
            size = os.path.getsize(full)
        except OSError:
            continue
        total_bytes += size
        if size < MIN_INTERESTING:
            continue
        found.append((size, full, WEIGHTS[ext]))

found.sort(reverse=True)

if not found:
    print()
    print("  NO model weight files >= 1 MB anywhere under C:\\1-AI.")
    print("  (noise directories skipped: %d)" % skipped_noise)
else:
    print()
    print("  %-10s %-28s %s" % ("SIZE", "KIND", "PATH"))
    for size, full, kind in found[:60]:
        print("  %-10s %-28s %s" % (human(size), kind, full))
    print()
    print("  total candidate bytes: " + human(total_bytes))

# ---- what does the pip cache actually hold -------------------------------
pipdir = os.path.join(SCAN_ROOT, "models", "huggingface", "pip")
print()
print("=" * 78)
print("WHAT IS THE 597 MB UNDER models\\huggingface?")
print("=" * 78)
if os.path.isdir(pipdir):
    n = 0
    b = 0
    for dp, _, fs in os.walk(pipdir):
        for f in fs:
            n += 1
            try:
                b += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
    print("  path : " + pipdir)
    print("  files: %d, size %s" % (n, human(b)))
    print("  kind : pip HTTP download cache (wheels/metadata pip re-fetches on demand)")
    print("  verdict: DISCARDABLE - not model data, regenerates itself")
else:
    print("  (absent)")

# ---- what ComfyUI already has --------------------------------------------
print()
print("=" * 78)
print("COMFYUI MODEL FOLDERS (destination candidates)")
print("=" * 78)
if os.path.isdir(COMFY_MODELS):
    for entry in sorted(os.listdir(COMFY_MODELS)):
        p = os.path.join(COMFY_MODELS, entry)
        if not os.path.isdir(p):
            continue
        cnt = 0
        sz = 0
        for dp, _, fs in os.walk(p):
            for f in fs:
                if os.path.splitext(f)[1].lower() in WEIGHTS:
                    cnt += 1
                    try:
                        sz += os.path.getsize(os.path.join(dp, f))
                    except OSError:
                        pass
        print("  %-24s %3d weights  %s" % (entry, cnt, human(sz)))
else:
    print("  ComfyUI models dir not found at " + COMFY_MODELS)

print()
print("=" * 78)
print("VERDICT")
print("=" * 78)
if not found:
    print("  Nothing under C:\\1-AI is a ComfyUI-usable model asset.")
    print("  Nothing to move. The 597 MB is a regenerable pip cache -> discard.")
else:
    print("  Review the list above before moving anything.")

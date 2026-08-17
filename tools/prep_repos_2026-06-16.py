# -*- coding: utf-8 -*-
"""Harden .gitignore, git init where missing, commit — report sizes. NO push here."""
import subprocess, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECTS = {
 "FidelityAnalyzer": r"C:\FidelityAnalyzer",
 "CypherMiner":      r"C:\APPS\CypherMiner",
 "LotteryWiz":       r"C:\APPS\Lottery Wiz",
 "TubeScout":        r"C:\APPS\TUBESCOUT",
 "M2V":              r"C:\APPS\M2V",
 "PersonalSong":     r"C:\APPS\PersonalSong",
 "AvatarStudio":     r"C:\1-AI\APPS\AvatarStudio",
 "DigitizationCostTool": r"C:\Users\renne\Downloads\DIGITIZATION COSTS",
}

IGNORE_MARKER = "# === QI standard ignores (auto) ==="
IGNORE_BLOCK = IGNORE_MARKER + """
.venv/
venv/
env/
__pycache__/
*.pyc
data/logs/
data/responses/
logs/
*.log
*.db
*.db-wal
*.db-shm
secrets/
*.env
outputs/
output/
node_modules/
.vscode/
.idea/
Thumbs.db
# model weights / large media (never commit)
*.pth
*.ckpt
*.safetensors
*.onnx
*.bin
*.pt
*.gguf
*.mp4
*.mov
*.wav
*.mp3
hallo2/pretrained_models/
"""

def run(args, cwd):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")

def dir_size_mb(path):
    total = 0
    for f in Path(path).rglob("*"):
        try:
            if f.is_file(): total += f.stat().st_size
        except Exception: pass
    return total / 1e6

for name, p in PROJECTS.items():
    root = Path(p)
    if not root.exists():
        print(f"  {name:22} MISSING PATH — skip"); continue
    gi = root / ".gitignore"
    txt = gi.read_text(encoding="utf-8", errors="replace") if gi.exists() else ""
    if IGNORE_MARKER not in txt:
        gi.write_text((txt.rstrip() + "\n\n" + IGNORE_BLOCK), encoding="utf-8")
    # init if needed
    if not (root / ".git").exists():
        run(["git", "init"], p)
        run(["git", "config", "user.name", "Renne Santiago"], p)
        run(["git", "config", "user.email", "renne@quiddityinnovations.com"], p)
        inited = "init"
    else:
        inited = "exists"
    # untrack any heavy dirs already tracked
    for heavy in (".venv", "venv", "__pycache__", "outputs", "hallo2/pretrained_models"):
        run(["git", "rm", "-r", "--cached", "--ignore-unmatch", heavy], p)
    run(["git", "add", "-A"], p)
    # detect accidental heavy staging
    staged = run(["git", "diff", "--cached", "--name-only"], p).stdout.splitlines()
    bad = [s for s in staged if "/.venv/" in s or s.startswith(".venv/") or "/__pycache__/" in s
           or s.endswith((".pth",".ckpt",".safetensors",".onnx",".gguf"))]
    if bad:
        print(f"  {name:22} ⚠️ HEAVY FILES STAGED ({len(bad)}) — committing skipped: {bad[:3]}")
        continue
    cm = run(["git", "-c","user.name=Renne Santiago","-c","user.email=renne@quiddityinnovations.com",
              "commit", "-q", "-m", "chore: harden .gitignore + baseline commit for private backup"], p)
    n_tracked = len(run(["git", "ls-files"], p).stdout.splitlines())
    # repo content size (working tree minus ignored heavy)
    print(f"  {name:22} {inited:6} tracked_files={n_tracked:<5} dir~{dir_size_mb(p):.0f}MB  commit:{'ok' if cm.returncode==0 else (cm.stdout+cm.stderr).strip()[:40]}")
print("DONE (no push yet)")

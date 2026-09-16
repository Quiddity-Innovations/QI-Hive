# -*- coding: utf-8 -*-
"""
Move *.bak-* clutter and known-dead files out of the live tree into
C:\\QIH\\_archive\\bak_<date>\\<relative path>, keeping a manifest so every
move is reversible (python archive_bak_files.py --undo <manifest>).

Nothing is deleted. Git-tracked files are moved with `git mv` so history is
kept; untracked files are moved on disk. Audit 2026-09-16, item 19.
"""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\QIH")
# Deliberate backup stores and the Library's indexed doc tree are left alone:
# "BU Administrative Backups" is a backup by design, and moving files under
# shared/documentation would orphan paths in the Brain docs index.
SKIP_DIRS = {"_archive", "archive", ".git", "worktrees", "node_modules", ".venv", "__pycache__",
             "BU Administrative Backups", "documentation"}
DEAD_FILES = [
    ROOT / "engine/hive/dashboard/link_collector.py",
    ROOT / "engine/hive/dashboard/static/links.json",
    ROOT / "engine/hive/dashboard/static/panel.html",
    ROOT / "engine/hive/dashboard/index.html",
]


def tracked() -> set[str]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    return set(out.splitlines())


def candidates() -> list[Path]:
    found = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if ".bak-" in fn or fn.endswith(".bak"):
                found.append(Path(dirpath) / fn)
    found += [p for p in DEAD_FILES if p.exists()]
    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--undo", help="manifest.json to reverse")
    a = ap.parse_args()
    if a.undo:
        man = json.loads(Path(a.undo).read_text(encoding="utf-8"))
        for mv in reversed(man["moves"]):
            src, dst = Path(mv["to"]), Path(mv["from"])
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.exists():
                shutil.move(str(src), str(dst))
        print("restored", len(man["moves"]), "files")
        return 0

    stamp = datetime.now().strftime("%Y-%m-%d")
    dest_root = ROOT / "_archive" / f"bak_{stamp}"
    trk = tracked()
    moves = []
    for p in candidates():
        rel = p.relative_to(ROOT)
        dest = dest_root / rel
        is_tracked = rel.as_posix() in trk
        moves.append({"from": str(p), "to": str(dest), "tracked": is_tracked})
        if a.dry_run:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if is_tracked:
            subprocess.run(["git", "mv", "-k", str(rel), str(dest.relative_to(ROOT))], cwd=ROOT,
                           capture_output=True, text=True)
            if p.exists():  # git mv refused (e.g. nested repo) -> plain move
                shutil.move(str(p), str(dest))
        else:
            shutil.move(str(p), str(dest))
    print(f"{'would move' if a.dry_run else 'moved'} {len(moves)} files "
          f"({sum(m['tracked'] for m in moves)} git-tracked) -> {dest_root}")
    if not a.dry_run:
        dest_root.mkdir(parents=True, exist_ok=True)
        (dest_root / "manifest.json").write_text(json.dumps(
            {"created": datetime.now().isoformat(timespec="seconds"), "moves": moves}, indent=2),
            encoding="utf-8")
        print("manifest", dest_root / "manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

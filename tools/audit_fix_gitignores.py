# -*- coding: utf-8 -*-
"""
One-shot repair: close the `gitignore_secrets` compliance findings.

Background (2026-08-17 audit)
----------------------------
Nine projects had .gitignore files missing coverage for one or more of
`secrets/`, `.env` and the chroma vector store. The Inspector had been filing
these as dispatches nightly with nobody consuming the queue.

Appends only the missing entries, under a dated header, preserving whatever is
already there. Also reports anything sensitive that is ALREADY TRACKED in git —
.gitignore does not untrack existing files, so that needs a human decision and
is never done automatically here.

Safe to re-run: idempotent.
"""
from __future__ import annotations
import json, subprocess, sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REGISTRY = Path(r"C:\QIH\ecosystem\qi_registry.json")
TARGETS = ["naya", "nexus", "easyflow", "mq", "cognibase",
           "mapsnap", "autopdf", "personalsong", "m2v"]

# (substring the Inspector looks for, lines to append if absent)
WANTED = [
    ("secrets/", ["secrets/"]),
    (".env",     [".env", ".env.*"]),
    ("chroma",   ["chroma/", "chroma_db/", "*.chroma"]),
]

HEADER = f"\n# --- QI compliance: secrets & vector stores (added {datetime.now():%Y-%m-%d} audit) ---\n"


def tracked_sensitive(repo: Path) -> list[str]:
    """Files already tracked by git that .gitignore can no longer protect."""
    try:
        out = subprocess.run(["git", "-C", str(repo), "ls-files"],
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=120)
    except Exception:
        return []
    hits = []
    for line in out.stdout.splitlines():
        low = line.lower()
        if low.startswith("secrets/") or "/secrets/" in low:
            hits.append(line)
        elif low.endswith(".env") or "/.env" in low or low == ".env":
            hits.append(line)
        elif "chroma" in low:
            hits.append(line)
    return hits


def main(apply: bool) -> int:
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    paths = {p["id"]: p["path"] for p in reg["projects"] if p.get("path")}

    total_added, leaks = 0, {}
    for pid in TARGETS:
        root = Path(paths.get(pid, ""))
        if not root.exists():
            print(f"  {pid:14} SKIP — path not found ({root})")
            continue
        gi = root / ".gitignore"
        text = gi.read_text(encoding="utf-8", errors="replace") if gi.exists() else ""

        missing = []
        for needle, lines in WANTED:
            if needle not in text:
                missing.extend(lines)

        already = tracked_sensitive(root)
        if already:
            leaks[pid] = already

        if not missing:
            print(f"  {pid:14} ok — already covered")
            continue

        print(f"  {pid:14} +{len(missing)}: {', '.join(missing)}")
        total_added += len(missing)
        if apply:
            with open(gi, "a", encoding="utf-8") as f:
                if not text.endswith("\n") and text:
                    f.write("\n")
                f.write(HEADER)
                f.write("\n".join(missing) + "\n")

    print(f"\n{'added' if apply else 'would add'} {total_added} line(s) across {len(TARGETS)} project(s)")

    if leaks:
        print("\n⚠ ALREADY TRACKED IN GIT — .gitignore cannot protect these. "
              "Needs a human decision (git rm --cached + rotate any real secret):")
        for pid, files in leaks.items():
            print(f"  {pid}: {len(files)} file(s)")
            for f in files[:5]:
                print(f"      {f}")
            if len(files) > 5:
                print(f"      ... and {len(files)-5} more")
    else:
        print("\nno sensitive files are currently tracked in git — clean")

    if not apply:
        print("\nDRY RUN — pass --apply to write.")
    return 0


if __name__ == "__main__":
    sys.exit(main("--apply" in sys.argv))

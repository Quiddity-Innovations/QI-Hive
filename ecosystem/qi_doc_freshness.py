# -*- coding: utf-8 -*-
"""qi_doc_freshness.py — report (and optionally enforce) documentation freshness.

Ported from the BU Hive docsmap idea (BU_Documentation-Standard.md, imported
2026-08-08): a doc is STALE when source files in its project have changed more
recently than the doc by more than `stale_after_days`.

Config: C:\\QIH\\ecosystem\\doc_freshness.json
  enforce=false (home default) -> report only, always exit 0
  enforce=true                 -> exit 1 when stale docs exist (CI/inspector gate)

Usage:  python qi_doc_freshness.py [--project <path>]
"""
import argparse
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

CFG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "doc_freshness.json")
SRC_EXT = {".py", ".js", ".ts", ".html", ".css", ".sql", ".ps1", ".bat", ".json", ".yml", ".yaml"}


def load_cfg():
    with open(CFG_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def newest_source_mtime(root, ignore):
    newest = 0.0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignore]
        for f in filenames:
            if os.path.splitext(f)[1].lower() in SRC_EXT:
                try:
                    newest = max(newest, os.path.getmtime(os.path.join(dirpath, f)))
                except OSError:
                    pass
    return newest


def project_docs(root, ignore):
    docs = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d in ("docs",) or d not in ignore and dirpath == root]
        for f in filenames:
            if f.lower().endswith(".md"):
                docs.append(os.path.join(dirpath, f))
    return docs


def check_project(root, cfg):
    ignore = set(cfg.get("ignore_dirs", []))
    lag = cfg.get("stale_after_days", 30) * 86400
    src_m = newest_source_mtime(root, ignore)
    if not src_m:
        return []
    stale = []
    for doc in project_docs(root, ignore):
        try:
            doc_m = os.path.getmtime(doc)
        except OSError:
            continue
        if src_m - doc_m > lag:
            stale.append((doc, int((src_m - doc_m) / 86400)))
    return stale


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", help="Check one project root instead of the configured scan_roots")
    a = ap.parse_args()
    cfg = load_cfg()

    roots = [a.project] if a.project else []
    if not roots:
        for base in cfg.get("scan_roots", []):
            if os.path.isdir(base):
                roots += [os.path.join(base, d) for d in sorted(os.listdir(base))
                          if os.path.isdir(os.path.join(base, d))
                          and d not in cfg.get("ignore_dirs", [])]

    total_stale = 0
    for root in roots:
        stale = check_project(root, cfg)
        if stale:
            total_stale += len(stale)
            print(f"[STALE] {root}")
            for doc, days in sorted(stale, key=lambda x: -x[1])[:5]:
                print(f"    {os.path.relpath(doc, root)} — {days}d behind the newest source change")

    mode = "ENFORCE" if cfg.get("enforce") else "observe"
    print(f"\n{total_stale} stale doc(s) across {len(roots)} project(s)  [mode={mode}]")
    if cfg.get("enforce") and total_stale:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Phase 3f - repoint the MCP servers off C:\\1-AI. LAST STEP: restarts Claude Code.

Fixes four stale entries and removes two duplicates:

  global  qi-brain      C:/1-AI/APPS/PYTHON/python.exe
  global  qi-registry   C:\\1-AI\\APPS\\PYTHON\\python.exe
  C:\\QI    sqlite-maia   C:/1-AI/APPS/PYTHON/Scripts/mcp-server-sqlite.exe
  C:\\NAYA  sqlite-naya   C:/1-AI/APPS/PYTHON/Scripts/mcp-server-sqlite.exe

  C:/QI and C:/NAYA hold byte-identical duplicates of the two project-scoped
  entries - path-separator drift, only one spelling ever takes effect. The
  forward-slash spellings are removed.

Run with --apply. A timestamped backup is written first.
"""
import argparse
import json
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")

CFG = r"C:\Users\renne\.claude.json"
BACKUP = (r"C:\QIH\shared\documentation\migration_2026-08\phase2\rollback"
          r"\claude.json.bak-phase3f")

OLD_VARIANTS = [
    "C:/1-AI/APPS/PYTHON",
    "C:\\1-AI\\APPS\\PYTHON",
    "C:/1-AI/Apps/Python",
    "C:\\1-AI\\Apps\\Python",
]
NEW_FWD = "C:/Program Files/Python311"
NEW_BACK = "C:\\Program Files\\Python311"

# Project keys that are duplicates of a backslash-spelled sibling.
DUPLICATE_KEYS = ["C:/QI", "C:/NAYA"]


def repoint(value):
    """Return (new_value, changed) for a string that may name the old tree."""
    if not isinstance(value, str):
        return value, False
    out = value
    for old in OLD_VARIANTS:
        if old in out:
            new = NEW_FWD if "/" in old else NEW_BACK
            out = out.replace(old, new)
    return out, out != value


def walk(obj, path=""):
    """Yield (container, key, value) for every string leaf."""
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if isinstance(v, (dict, list)):
                yield from walk(v, path + "/" + str(k))
            else:
                yield obj, k, v, path + "/" + str(k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, (dict, list)):
                yield from walk(v, path + "/" + str(i))
            else:
                yield obj, i, v, path + "/" + str(i)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    raw = open(CFG, encoding="utf-8").read()
    cfg = json.loads(raw)
    print("loaded %s (%.1f KB)" % (CFG, len(raw) / 1024))

    # ---- 1. repoint every string naming the old interpreter ---------------
    print()
    print("=== stale interpreter references ===")
    changes = 0
    for container, key, value, where in walk(cfg):
        new, changed = repoint(value)
        if changed:
            changes += 1
            print("  %s" % where)
            print("     old: %s" % value)
            print("     new: %s" % new)
            if args.apply:
                container[key] = new
    if not changes:
        print("  none found")

    # ---- 2. drop the duplicate project-scoped entries ---------------------
    print()
    print("=== duplicate project-scoped MCP entries ===")
    projects = cfg.get("projects", {})
    removed = 0
    for dup in DUPLICATE_KEYS:
        keep = dup.replace("/", "\\")
        if dup in projects and keep in projects:
            dms = (projects[dup].get("mcpServers") or {})
            kms = (projects[keep].get("mcpServers") or {})
            print("  %-10s duplicates %-10s  (servers: %s vs %s)"
                  % (dup, keep, list(dms), list(kms)))
            if set(dms) == set(kms):
                print("     -> identical server set; removing %s" % dup)
                if args.apply:
                    del projects[dup]
                removed += 1
            else:
                print("     -> server sets DIFFER; leaving both alone")
        elif dup in projects:
            print("  %-10s has no backslash sibling; leaving alone" % dup)
    if not removed:
        print("  nothing removed")

    # ---- 3. write ---------------------------------------------------------
    print()
    if args.apply and (changes or removed):
        os.makedirs(os.path.dirname(BACKUP), exist_ok=True)
        if not os.path.exists(BACKUP):
            shutil.copy2(CFG, BACKUP)
            print("backup: " + BACKUP)
        tmp = CFG + ".tmp-phase3f"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, CFG)
        print("WROTE %s  (%d repoints, %d duplicates removed)"
              % (CFG, changes, removed))

        # verify
        v = json.load(open(CFG, encoding="utf-8"))
        left = [w for _, _, val, w in walk(v)
                if isinstance(val, str) and "1-AI" in val]
        print("strings still naming 1-AI: %d" % len(left))
        for w in left[:10]:
            print("   " + w)
        print()
        print("=== resulting MCP servers ===")
        for name, s in (v.get("mcpServers") or {}).items():
            print("  %-14s %s" % (name, s.get("command") or s.get("url", "")))
        for pk, pv in (v.get("projects") or {}).items():
            ms = pv.get("mcpServers") or {}
            if ms:
                for n, s in ms.items():
                    print("  [%s] %-12s %s" % (pk, n, s.get("command") or s.get("url", "")))
    elif not args.apply:
        print("DRY RUN - re-run with --apply to write.")
    else:
        print("nothing to do")


if __name__ == "__main__":
    raise SystemExit(main())

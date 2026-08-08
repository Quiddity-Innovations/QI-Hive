# -*- coding: utf-8 -*-
"""QI batch-file standardization executor (Tier-1: collision-free launchers).
Renames primary control/launch .bat files to <Product>_<Role>.bat and rewrites
references PROJECT-SCOPED ONLY (generic basenames like install_service.bat exist
in several projects, so a blind global replace would corrupt siblings).

  python standardize_batch.py --dry-run
  python standardize_batch.py --execute

Writes a rollback manifest so every rename + edit can be reversed. 2026-06-23.
"""
import os, re, json, shutil, sys, argparse
sys.stdout.reconfigure(encoding="utf-8")

ROOT = r"C:\QIH\tools\naming_standardization"
SCAN_EXT = (".py", ".ps1", ".bat", ".cmd", ".md", ".json", ".txt")
EXCLUDE  = ("\\.git", "worktree", "maia_archive", "node_modules", "\\.venv",
            "site-packages", "\\dist\\", "portable")

def project_root(path):
    p = path.lower()
    for r in (r"c:\claude\claude voice", r"c:\claude\dashboard", r"c:\qi",
              r"c:\naya", r"c:\nexus", r"c:\tubescout", r"c:\personalsong",
              r"c:\easyflow", r"c:\qih"):
        if p.startswith(r):
            return r
    return os.path.dirname(p)

def excluded(p):
    pl = p.lower()
    return any(x in pl for x in EXCLUDE)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--map", default="batch_rename_tier1.json",
                    help="rename map filename under the tool dir")
    a = ap.parse_args()
    if not (a.dry_run or a.execute):
        print("specify --dry-run or --execute"); sys.exit(2)

    mapfile = a.map if os.path.isabs(a.map) else os.path.join(ROOT, a.map)
    tier_tag = os.path.splitext(os.path.basename(mapfile))[0].replace("batch_rename_", "")
    data = json.load(open(mapfile, encoding="utf-8"))
    renames = data["renames"]
    rollback = {"renames": [], "edits": []}
    from datetime import datetime  # only for naming log; allowed in normal python
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    logp = os.path.join(ROOT, "logs", f"batch_{tier_tag}_{'EXEC' if a.execute else 'DRY'}_{stamp}.log")
    lines = []
    def log(m): print(m); lines.append(m)

    log(f"=== batch standardization  mode={'EXECUTE' if a.execute else 'DRYRUN'} ===")
    for r in renames:
        old = r["path"]
        new = os.path.join(os.path.dirname(old), r["new"])
        if not os.path.exists(old):
            log(f"[skip] missing: {old}"); continue
        case_only = os.path.normcase(os.path.abspath(old)) == os.path.normcase(os.path.abspath(new))
        if os.path.exists(new) and not case_only:
            log(f"[skip] target exists: {new}"); continue
        if case_only and os.path.basename(old) == os.path.basename(new):
            log(f"[ok] already conforms (case): {os.path.basename(new)}"); continue
        proot = project_root(old)
        oldbn, newbn = os.path.basename(old), r["new"]

        # find project-scoped references (same project root only)
        refs = []
        for dp, dns, fns in os.walk(proot):
            if excluded(dp):
                dns[:] = []; continue
            for fn in fns:
                if not fn.lower().endswith(SCAN_EXT): continue
                fp = os.path.join(dp, fn)
                if os.path.samefile(fp, old) if os.path.exists(fp) else False:
                    pass
                try:
                    txt = open(fp, encoding="utf-8", errors="ignore").read()
                except Exception:
                    continue
                if re.search(re.escape(oldbn), txt, re.I):
                    refs.append(fp)

        log(f"\n{oldbn}  ->  {newbn}")
        log(f"   dir: {os.path.dirname(old)}")
        log(f"   refs in {proot}: {len(refs)}")
        for fp in refs:
            log(f"      ref: {fp}")

        if a.execute:
            # rewrite references (case-insensitive, basename only, scoped to project)
            for fp in refs:
                txt = open(fp, encoding="utf-8", errors="ignore").read()
                new_txt = re.sub(re.escape(oldbn), newbn, txt, flags=re.I)
                if new_txt != txt:
                    open(fp, "w", encoding="utf-8").write(new_txt)
                    rollback["edits"].append({"file": fp, "from": newbn, "to": oldbn})
            # rename the file (two-step for case-only changes on Windows)
            if case_only:
                tmp = old + ".casetmp"
                shutil.move(old, tmp); shutil.move(tmp, new)
            else:
                shutil.move(old, new)
            rollback["renames"].append({"from": new, "to": old})
            log(f"   RENAMED + rewrote {len(refs)} ref-file(s)")

    if a.execute:
        rbname = f"batch_rollback_{tier_tag}.json"
        json.dump(rollback, open(os.path.join(ROOT, rbname),
                  "w", encoding="utf-8"), indent=2)
        log(f"\nrollback manifest: {rbname}")
    open(logp, "w", encoding="utf-8").write("\n".join(lines))
    log(f"log: {logp}")

if __name__ == "__main__":
    main()

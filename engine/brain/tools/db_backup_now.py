# -*- coding: utf-8 -*-
"""One-shot, safe SQLite backup using the online backup API.

Usage: python db_backup_now.py [--label pre-remediation]
Writes C:\\QIH\\shared\\backups\\db\\YYYY-MM-DD[_label]\\<name>.db for every
known QI SQLite database that exists, verifies each copy with an integrity
check and a row count on one table, and prints a manifest line per file.
Never deletes anything.
"""
from __future__ import annotations
import argparse, sqlite3, sys, json
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\QIH\shared\backups\db")
TARGETS = [
    (Path(r"C:\QIH\data\qi_brain.db"), "qi_brain"),
    (Path(r"C:\QIH\data\effort\effort_ledger.db"), "effort_ledger"),
    (Path(r"C:\QIH\engine\hive\agents\agent_hr.db"), "agent_hr"),
    (Path(r"C:\APPS\QI\maia.db"), "maia"),
    (Path(r"C:\APPS\NAYA\naya.db"), "naya"),
    (Path(r"C:\APPS\NEXUS\nexus.db"), "nexus"),
]

def backup_one(src: Path, dest: Path) -> dict:
    con = sqlite3.connect(f"file:{src}?mode=ro", uri=True, timeout=30)
    try:
        out = sqlite3.connect(dest)
        try:
            con.backup(out)
            ok = out.execute("PRAGMA integrity_check").fetchone()[0]
            tables = [r[0] for r in out.execute("select name from sqlite_master where type='table'")]
            sample = {}
            for t in tables[:3]:
                try:
                    sample[t] = out.execute(f'select count(*) from "{t}"').fetchone()[0]
                except Exception:
                    pass
        finally:
            out.close()
    finally:
        con.close()
    return {"src": str(src), "dest": str(dest), "bytes": dest.stat().st_size,
            "integrity": ok, "tables": len(tables), "sample_counts": sample}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="")
    a = ap.parse_args()
    day = datetime.now().strftime("%Y-%m-%d") + (f"_{a.label}" if a.label else "")
    dest_dir = ROOT / day
    dest_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    rc = 0
    for src, name in TARGETS:
        if not src.exists():
            print(f"skip   {name}: {src} not present")
            continue
        try:
            m = backup_one(src, dest_dir / f"{name}.db")
            manifest.append(m)
            print(f"ok     {name}: {m['bytes']:,} bytes integrity={m['integrity']} {m['sample_counts']}")
        except Exception as e:
            rc = 1
            print(f"FAILED {name}: {e!r}")
    (dest_dir / "manifest.json").write_text(json.dumps(
        {"created": datetime.now().isoformat(timespec="seconds"), "files": manifest}, indent=2),
        encoding="utf-8")
    print("manifest", dest_dir / "manifest.json")
    return rc

if __name__ == "__main__":
    raise SystemExit(main())

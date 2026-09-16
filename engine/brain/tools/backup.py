# -*- coding: utf-8 -*-
"""
QI Nightly Backup — backup.py  (v2, 2026-09-16)
================================================
Backs up every QI SQLite database that exists to
    C:\\QIH\\shared\\backups\\db\\YYYY-MM-DD\\<name>.db
using the SQLite online-backup API (safe while the owning service is writing),
verifies each copy with PRAGMA integrity_check, keeps 30 days, and writes a
per-day log C:\\QIH\\LOGS\\nightly_backup\\backup_YYYYMMDD.log whose last line
is "backup OK" ONLY when every present target succeeded. QI_TaskHealth checks
that marker (task_health_manifest.json), so a failing night trips an alert
instead of a Task Scheduler "0".

History: v1 wrote to C:\\UNIVERSAL\\BACKUPS and read qi_brain.db from
C:\\UNIVERSAL\\qi_brain — both deleted on 2026-04-22 — so the scheduled task
QI_NightlyBackup exited 1 every night and no Brain backup existed until the
2026-09-16 audit caught it.

Runs nightly at 01:00 via Windows Task Scheduler (QI_NightlyBackup).

Usage:
  python C:\\QIH\\engine\\brain\\tools\\backup.py
  python C:\\QIH\\engine\\brain\\tools\\backup.py --dry-run
  python C:\\QIH\\engine\\brain\\tools\\backup.py --verify   (open newest set, count rows)
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

BACKUP_ROOT = Path(r"C:\QIH\shared\backups\db")
LOG_DIR = Path(r"C:\QIH\LOGS\nightly_backup")
KEEP_DAYS = 30

TARGETS: list[tuple[Path, str]] = [
    (Path(r"C:\QIH\data\qi_brain.db"),                 "qi_brain"),
    (Path(r"C:\QIH\data\effort\effort_ledger.db"),     "effort_ledger"),
    (Path(r"C:\QIH\engine\hive\agents\agent_hr.db"),   "agent_hr"),
    (Path(r"C:\APPS\QI\maia.db"),                      "maia"),
    (Path(r"C:\APPS\NAYA\naya.db"),                    "naya"),
    (Path(r"C:\APPS\NEXUS\nexus.db"),                  "nexus"),
]

_LOG_LINES: list[str] = []


def log(msg: str) -> None:
    line = f"{datetime.now().isoformat(timespec='seconds')} {msg}"
    _LOG_LINES.append(line)
    if sys.stdout is not None:
        try:
            print(line)
        except Exception:
            pass


def flush_log() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    p = LOG_DIR / f"backup_{datetime.now():%Y%m%d}.log"
    with p.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(_LOG_LINES) + "\n")


def backup_one(src: Path, dest: Path) -> dict:
    con = sqlite3.connect(f"file:{src}?mode=ro", uri=True, timeout=60)
    try:
        out = sqlite3.connect(dest)
        try:
            con.backup(out, pages=4096)
            integrity = out.execute("PRAGMA integrity_check").fetchone()[0]
            n_tables = out.execute("select count(*) from sqlite_master where type='table'").fetchone()[0]
        finally:
            out.close()
    finally:
        con.close()
    return {"src": str(src), "dest": str(dest), "bytes": dest.stat().st_size,
            "integrity": integrity, "tables": n_tables}


def purge_old(dry_run: bool) -> int:
    cutoff = datetime.now() - timedelta(days=KEEP_DAYS)
    removed = 0
    if not BACKUP_ROOT.is_dir():
        return 0
    for d in BACKUP_ROOT.iterdir():
        if not d.is_dir():
            continue
        try:
            when = datetime.strptime(d.name[:10], "%Y-%m-%d")
        except ValueError:
            continue  # labelled/manual sets (e.g. *_pre-remediation) are never purged
        if len(d.name) > 10:
            continue
        if when < cutoff:
            log(f"purge {d}")
            if not dry_run:
                shutil.rmtree(d, ignore_errors=True)
            removed += 1
    return removed


def verify_latest() -> int:
    sets = sorted(p for p in BACKUP_ROOT.iterdir() if p.is_dir()) if BACKUP_ROOT.is_dir() else []
    if not sets:
        print("no backup sets found"); return 1
    latest = sets[-1]
    rc = 0
    for db in sorted(latest.glob("*.db")):
        try:
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            ok = con.execute("PRAGMA integrity_check").fetchone()[0]
            tables = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
            counts = {t: con.execute(f'select count(*) from "{t}"').fetchone()[0] for t in tables[:4]}
            con.close()
            print(f"{db.name:20} integrity={ok} tables={len(tables)} {counts}")
            if ok != "ok":
                rc = 1
        except Exception as e:
            print(f"{db.name:20} FAILED {e!r}"); rc = 1
    return rc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    if a.verify:
        return verify_latest()

    day_dir = BACKUP_ROOT / datetime.now().strftime("%Y-%m-%d")
    log(f"nightly backup start -> {day_dir}{' (dry run)' if a.dry_run else ''}")
    if not a.dry_run:
        day_dir.mkdir(parents=True, exist_ok=True)
    manifest, failed, done = [], 0, 0
    for src, name in TARGETS:
        if not src.exists():
            log(f"skip   {name}: {src} not present")
            continue
        if a.dry_run:
            log(f"would  {name}: {src} ({src.stat().st_size:,} bytes)")
            continue
        try:
            m = backup_one(src, day_dir / f"{name}.db")
            manifest.append(m)
            done += 1
            if m["integrity"] != "ok":
                failed += 1
                log(f"BAD    {name}: integrity={m['integrity']}")
            else:
                log(f"ok     {name}: {m['bytes']:,} bytes, {m['tables']} tables")
        except Exception as e:
            failed += 1
            log(f"FAILED {name}: {e!r}")
    removed = purge_old(a.dry_run)
    if not a.dry_run:
        (day_dir / "manifest.json").write_text(json.dumps(
            {"created": datetime.now().isoformat(timespec="seconds"), "files": manifest,
             "failed": failed, "purged_sets": removed}, indent=2), encoding="utf-8")
    if failed == 0 and (done > 0 or a.dry_run):
        log(f"backup OK ({done} databases, {removed} old sets purged)")
        rc = 0
    else:
        log(f"backup FAILED ({failed} failures, {done} ok)")
        rc = 1
    flush_log()
    return rc


if __name__ == "__main__":
    if sys.stdout is not None:
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    raise SystemExit(main())

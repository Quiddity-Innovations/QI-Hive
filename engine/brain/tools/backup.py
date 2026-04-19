# -*- coding: utf-8 -*-
"""
QI Nightly Backup — backup.py
==============================
Backs up all QI SQLite databases to C:\UNIVERSAL\BACKUPS\YYYY-MM-DD\
Runs nightly at 1:00 AM via Windows Task Scheduler.
Keeps 30 days of backups; older ones are auto-purged.

Targets:
  - C:\QI\maia.db              (Maia: users, messages, config)
  - C:\NAYA\naya.db            (Naya: conversations, preferences)
  - C:\NAYA\filehq\db\filehq.db (FileHQ file index — large, use SQLite backup API)
  - C:\NEXUS\nexus.db          (NEXUS: sessions, metrics, cache)
  - C:\UNIVERSAL\qi_brain\qi_brain.db (QI Brain: decisions, features, sessions)

Usage:
  python C:\\UNIVERSAL\\qi_brain\\tools\\backup.py
  python C:\\UNIVERSAL\\qi_brain\\tools\\backup.py --dry-run
"""
from __future__ import annotations

import sys
import shutil
import sqlite3
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Configuration ──────────────────────────────────────────────────────────────

BACKUP_ROOT   = Path(r"C:\UNIVERSAL\BACKUPS")
RETENTION_DAYS = 30
LOG_FILE       = Path(r"C:\UNIVERSAL\BACKUPS\backup.log")

# Each tuple: (source_path, label)
# label is used in the filename: label_YYYY-MM-DD.db
TARGETS: list[tuple[Path, str]] = [
    (Path(r"C:\QI\maia.db"),                              "maia"),
    (Path(r"C:\NAYA\naya.db"),                            "naya"),
    (Path(r"C:\NAYA\filehq\db\filehq.db"),                "filehq"),
    (Path(r"C:\NEXUS\nexus.db"),                          "nexus"),
    (Path(r"C:\UNIVERSAL\qi_brain\qi_brain.db"),          "qi_brain"),
]

# ── Logging ────────────────────────────────────────────────────────────────────

BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("qi_backup")
_console = logging.StreamHandler(sys.stdout)
_console.setFormatter(logging.Formatter("%(asctime)s  %(levelname)s  %(message)s", "%H:%M:%S"))
log.addHandler(_console)


# ── SQLite hot backup (safe while DB is being written) ────────────────────────

def sqlite_backup(src: Path, dst: Path) -> None:
    """
    Use sqlite3.Connection.backup() — the only safe way to copy a live SQLite
    file. Works even with WAL mode; no data corruption risk.
    """
    src_conn = sqlite3.connect(str(src))
    dst_conn = sqlite3.connect(str(dst))
    try:
        src_conn.backup(dst_conn, pages=200)   # 200 pages at a time; yields between chunks
    finally:
        dst_conn.close()
        src_conn.close()


# ── Backup one target ─────────────────────────────────────────────────────────

def backup_one(src: Path, label: str, dest_dir: Path, dry_run: bool) -> bool:
    dest = dest_dir / f"{label}.db"

    if not src.exists():
        log.warning(f"SKIP {label}: source not found at {src}")
        return False

    src_mb = src.stat().st_size / (1024 * 1024)
    log.info(f"  {label}: {src} ({src_mb:.1f} MB) → {dest}")

    if dry_run:
        log.info(f"  [DRY RUN] would copy {src} → {dest}")
        return True

    try:
        sqlite_backup(src, dest)
        dest_mb = dest.stat().st_size / (1024 * 1024)
        log.info(f"  {label}: OK ({dest_mb:.1f} MB written)")
        return True
    except Exception as e:
        log.error(f"  {label}: FAILED — {e}")
        # Attempt plain copy as fallback (safe if file isn't heavily written)
        try:
            shutil.copy2(str(src), str(dest))
            log.warning(f"  {label}: fallback plain copy succeeded")
            return True
        except Exception as e2:
            log.error(f"  {label}: fallback also failed — {e2}")
            return False


# ── Purge old backups ─────────────────────────────────────────────────────────

def purge_old(dry_run: bool) -> None:
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    removed = 0
    for day_dir in BACKUP_ROOT.iterdir():
        if not day_dir.is_dir():
            continue
        try:
            # Directory names are YYYY-MM-DD
            dir_date = datetime.strptime(day_dir.name, "%Y-%m-%d")
        except ValueError:
            continue   # skip non-date directories
        if dir_date < cutoff:
            if dry_run:
                log.info(f"  [DRY RUN] would delete old backup: {day_dir}")
            else:
                shutil.rmtree(day_dir)
                log.info(f"  Purged old backup: {day_dir}")
            removed += 1
    if removed == 0:
        log.info(f"  No backups older than {RETENTION_DAYS} days to purge")
    else:
        log.info(f"  Purged {removed} old backup(s)")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="QI Nightly Database Backup")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without writing")
    args = parser.parse_args()

    ts    = datetime.now()
    label = ts.strftime("%Y-%m-%d")
    dest_dir = BACKUP_ROOT / label
    dest_dir.mkdir(parents=True, exist_ok=True)

    log.info(f"{'='*60}")
    log.info(f"QI Backup started — {ts.strftime('%Y-%m-%d %H:%M:%S')}{' [DRY RUN]' if args.dry_run else ''}")
    log.info(f"Destination: {dest_dir}")

    ok_count  = 0
    fail_count = 0

    for src_path, db_label in TARGETS:
        success = backup_one(src_path, db_label, dest_dir, args.dry_run)
        if success:
            ok_count += 1
        else:
            fail_count += 1

    log.info(f"Backup complete — {ok_count} OK / {fail_count} failed")
    log.info(f"Purging backups older than {RETENTION_DAYS} days...")
    purge_old(args.dry_run)
    log.info(f"{'='*60}")

    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()

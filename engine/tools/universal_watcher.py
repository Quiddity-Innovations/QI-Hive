# -*- coding: utf-8 -*-
"""
universal_watcher.py  —  Quarantine sentinel for C:\\UNIVERSAL.

Logs every create / modify / delete under C:\\UNIVERSAL to
C:\\QIH\\data\\logs\\universal_access.log so we can prove the folder is
dead before Renne deletes it.

Run manually:  python C:\\QIH\\engine\\tools\\universal_watcher.py
Or register as NSSM service QI_UniversalWatcher (optional).

Migration context: UNIVERSAL is being retired (see
C:\\QIH\\docs\\UNIVERSAL_MIGRATION_PLAN.md).  If this watcher logs any
writes after 2026-04-22, the migration missed a reference.
"""
import sys, os, time
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

WATCH_ROOT = Path(r"C:\UNIVERSAL")
LOG_FILE   = Path(r"C:\QIH\data\logs\universal_access.log")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAVE_WATCHDOG = True
except ImportError:
    HAVE_WATCHDOG = False


def _log(line: str) -> None:
    stamp = datetime.now().isoformat(timespec='seconds')
    with LOG_FILE.open('a', encoding='utf-8') as f:
        f.write(f"[{stamp}] {line}\n")
    print(f"[{stamp}] {line}", flush=True)


if HAVE_WATCHDOG:
    class UniversalHandler(FileSystemEventHandler):
        def on_any_event(self, event):
            # Skip __pycache__ noise
            if "__pycache__" in event.src_path:
                return
            _log(f"{event.event_type.upper():8} {event.src_path}")

    def main():
        if not WATCH_ROOT.exists():
            _log(f"GONE     {WATCH_ROOT} does not exist — watcher exiting.")
            return
        _log(f"START    Watching {WATCH_ROOT} (watchdog mode)")
        obs = Observer()
        obs.schedule(UniversalHandler(), str(WATCH_ROOT), recursive=True)
        obs.start()
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            obs.stop()
        obs.join()
        _log("STOP     Watcher stopped.")
else:
    # Fallback: 30-second mtime poll
    def _snapshot(root: Path) -> dict:
        out = {}
        for p in root.rglob("*"):
            if "__pycache__" in p.parts:
                continue
            try:
                out[str(p)] = p.stat().st_mtime
            except OSError:
                pass
        return out

    def main():
        if not WATCH_ROOT.exists():
            _log(f"GONE     {WATCH_ROOT} does not exist — watcher exiting.")
            return
        _log(f"START    Watching {WATCH_ROOT} (poll mode — install watchdog for real-time)")
        prev = _snapshot(WATCH_ROOT)
        while True:
            time.sleep(30)
            cur = _snapshot(WATCH_ROOT)
            for path, mt in cur.items():
                if path not in prev:
                    _log(f"CREATED  {path}")
                elif prev[path] != mt:
                    _log(f"MODIFIED {path}")
            for path in prev:
                if path not in cur:
                    _log(f"DELETED  {path}")
            prev = cur


if __name__ == "__main__":
    main()

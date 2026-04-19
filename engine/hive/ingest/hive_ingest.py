# -*- coding: utf-8 -*-
"""
QI Hive Ingester — reads reports from C:\\QIH\\shared\\reports\\inbox\\
and files them into the Brain (status.json + session log), then archives.

Runs in a simple loop; installable as NSSM service QI_HiveIngest.
"""
from __future__ import annotations
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\QIH")
INBOX = ROOT / "shared" / "reports" / "inbox"
ARCHIVE = ROOT / "shared" / "reports" / "archive"
STATUS = ROOT / "data" / "status.json"
LOG_DIR = ROOT / "logs" / "hive"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG = LOG_DIR / "ingest.log"

for d in [INBOX, ARCHIVE]:
    d.mkdir(parents=True, exist_ok=True)


def log(msg: str) -> None:
    line = f"{datetime.now().isoformat()}  {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_status() -> dict:
    if STATUS.exists():
        return json.loads(STATUS.read_text(encoding="utf-8"))
    return {"projects": {}, "hive_reports": []}


def save_status(s: dict) -> None:
    STATUS.write_text(json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8")


def ingest(path: Path) -> None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        log(f"[ERROR] cannot parse {path.name}: {e}")
        shutil.move(str(path), str(ARCHIVE / f"BAD_{path.name}"))
        return

    project = payload.get("project", "?")
    event = payload.get("event", "?")
    log(f"[{project}] {event} — {payload.get('summary', '')[:80]}")

    s = load_status()
    s.setdefault("hive_reports", [])
    s["hive_reports"].append(payload)
    s["hive_reports"] = s["hive_reports"][-500:]  # cap history

    if project in s.get("projects", {}):
        proj = s["projects"][project]
        proj["last_activity"] = datetime.now().strftime("%Y-%m-%d")
        if event == "session_end" and payload.get("summary"):
            proj.setdefault("recent_sessions", [])
            proj["recent_sessions"].append({
                "at": payload["timestamp"],
                "summary": payload["summary"],
                "next_steps": payload.get("next_steps", []),
            })
            proj["recent_sessions"] = proj["recent_sessions"][-20:]

    save_status(s)
    shutil.move(str(path), str(ARCHIVE / path.name))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    log("QI Hive Ingester starting")
    log(f"inbox: {INBOX}")
    while True:
        try:
            for p in sorted(INBOX.glob("*.json"), key=lambda x: x.stat().st_mtime):
                ingest(p)
            time.sleep(2)
        except KeyboardInterrupt:
            log("shutting down")
            break
        except Exception as e:
            log(f"[LOOP ERROR] {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()

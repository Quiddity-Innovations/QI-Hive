# -*- coding: utf-8 -*-
"""
QI Hive Reporter — tiny client every project's .claude uses to report
activity back to the Hive.

Drops a JSON report into C:\\QIH\\shared\\reports\\inbox\\. The Hive
ingester (qi_hive_ingest.py) picks it up, writes it to the Brain, and
archives it.

Usage (from any project):
    from hive_report import report
    report("session_end", project="Maia", summary="Fixed webhook retry",
           files_changed=["webhook.py"], next_steps=["Add metrics"])

Or CLI:
    python hive_report.py session_end --project Maia --summary "..."
"""
from __future__ import annotations
import argparse
import json
import os
import socket
import sys
import uuid
from datetime import datetime
from pathlib import Path

INBOX = Path(r"C:\QIH\shared\reports\inbox")


def report(
    event: str,
    project: str,
    summary: str = "",
    **fields,
) -> Path:
    """Write a report to the Hive inbox. Returns the file path."""
    INBOX.mkdir(parents=True, exist_ok=True)
    rid = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    payload = {
        "id": rid,
        "event": event,
        "project": project,
        "summary": summary,
        "host": socket.gethostname(),
        "user": os.environ.get("USERNAME", "?"),
        "timestamp": datetime.now().isoformat(),
        **fields,
    }
    path = INBOX / f"{project}_{event}_{rid}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("event", help="e.g. session_start, session_end, decision, error")
    ap.add_argument("--project", required=True)
    ap.add_argument("--summary", default="")
    ap.add_argument("--json", help="Extra fields as JSON string", default="{}")
    args = ap.parse_args()
    extra = json.loads(args.json) if args.json else {}
    path = report(args.event, args.project, args.summary, **extra)
    print(f"reported → {path}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

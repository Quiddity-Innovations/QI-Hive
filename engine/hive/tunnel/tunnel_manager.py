# -*- coding: utf-8 -*-
"""
QI Hive Dashboard Tunnel Manager

Starts a Cloudflare Quick Tunnel for the Hive Dashboard (port 8600), parses
the public URL from cloudflared's stderr, and writes it to status/tunnel.json
so the dashboard can display it in the header.

Relocated from C:\\UNIVERSAL\\dashboard as part of the UNIVERSAL->QIH
migration (2026-04-22). The previous version tunneled port 9000, which no
longer listens — the old standalone dashboard was retired when QI_Dashboard
was repurposed to serve the Hive UI on 8600.

The dashboard's /api/tunnel endpoint reads the same status/tunnel.json file.

Run:  python tunnel_manager.py
Stop: Ctrl+C (or kill the python process)
"""
from __future__ import annotations
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CLOUDFLARED = r"C:\Program Files (x86)\cloudflared\cloudflared.exe"
DASHBOARD_PORT = 8600  # QI Hive Dashboard (was 9000 for the retired standalone dashboard)
HERE = Path(__file__).parent
STATUS_FILE = HERE / "status" / "tunnel.json"
LOG_FILE = HERE / "LOGS" / "tunnel_manager.log"

URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def write_status(**fields):
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {"updated_at": datetime.utcnow().isoformat() + "Z", **fields}
    STATUS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def log(msg):
    stamp = datetime.utcnow().isoformat() + "Z"
    line = f"[{stamp}] {msg}"
    print(line, flush=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    if not os.path.exists(CLOUDFLARED):
        log(f"ERROR: cloudflared not found at {CLOUDFLARED}")
        write_status(status="error", error="cloudflared not installed", url=None)
        sys.exit(1)

    log(f"Starting quick tunnel to http://127.0.0.1:{DASHBOARD_PORT}")
    write_status(status="starting", url=None)

    proc = subprocess.Popen(
        [CLOUDFLARED, "tunnel", "--url", f"http://127.0.0.1:{DASHBOARD_PORT}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    url_captured = None
    try:
        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue
            log(line)
            m = URL_RE.search(line)
            if m and not url_captured:
                url_captured = m.group(0)
                write_status(status="running", url=url_captured, pid=proc.pid)
                log(f">>> TUNNEL UP: {url_captured}")
    except KeyboardInterrupt:
        log("Interrupted — shutting tunnel down")
    finally:
        if proc.poll() is None:
            proc.terminate()
        write_status(status="stopped", url=None)
        log("Tunnel stopped")


if __name__ == "__main__":
    main()

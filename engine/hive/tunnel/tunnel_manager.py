# -*- coding: utf-8 -*-
"""
QI Hive Dashboard Tunnel Manager — DEPRECATED (2026-06-23)

This used to start a Cloudflare QUICK tunnel for the Hive Dashboard (:8600),
scrape the random *.trycloudflare.com URL from stderr, and write it to
status/tunnel.json.

That model is RETIRED. The Hive Dashboard is now served by the STATIC NAMED
tunnel `qi-hive` -> https://hive.quiddityinnovations.com, run by the
QI_DashboardTunnel service (`cloudflared tunnel run qi-hive`), defined in
C:\\QIH\\engine\\tunnels\\tunnels.json. Starting a quick tunnel here would
create a SECOND, competing tunnel and clobber status/tunnel.json with an
ephemeral URL.

To preserve any caller (and the dashboard's /api/tunnel endpoint, which reads
status/tunnel.json), this script now simply writes the PERMANENT static URL to
status/tunnel.json and exits. It no longer launches cloudflared.

Run:  python tunnel_manager.py   (writes static status, exits 0)
"""
from __future__ import annotations
import json
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DASHBOARD_PORT = 8600  # QI Hive Dashboard
HERE = Path(__file__).parent
STATUS_FILE = HERE / "status" / "tunnel.json"
LOG_FILE = HERE / "LOGS" / "tunnel_manager.log"

# Resolve the permanent URL from the single source of truth (tunnels.json).
_TUN = r"C:\QIH\engine\tunnels"
if _TUN not in sys.path:
    sys.path.insert(0, _TUN)
try:
    from static_urls import url_for_port
except Exception:
    def url_for_port(_port):
        return None

# Hard fallback if the resolver is somehow unavailable.
STATIC_URL = url_for_port(DASHBOARD_PORT) or "https://hive.quiddityinnovations.com"


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
    log("DEPRECATED: quick tunnel retired. Hive Dashboard is now the static "
        f"named tunnel qi-hive -> {STATIC_URL} (service QI_DashboardTunnel).")
    write_status(status="running", url=STATIC_URL, static=True, tunnel="qi-hive")
    log(f"Wrote static URL to {STATUS_FILE}. Not launching cloudflared.")


if __name__ == "__main__":
    main()

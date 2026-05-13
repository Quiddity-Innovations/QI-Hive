# -*- coding: utf-8 -*-
"""
link_collector.py — QI Panel link aggregator
=============================================
Scans every known tunnel URL source and writes a consolidated links.json
to the dashboard's static folder. The QI Panel page fetches that JSON.

Sources scanned:
  - Hive Dashboard:  C:\\QIH\\engine\\hive\\tunnel\\status\\tunnel.json
  - Maia API/UI:     C:\\QI\\LOGS\\tunnel_log.txt
  - Maia Gradio UI:  C:\\QI\\LOGS\\Maia_Gradio_Tunnel_Log.txt
  - Naya:            C:\\NAYA\\LOGS\\naya_tunnel_log.txt

Run modes:
  python link_collector.py          # one-shot
  python link_collector.py --watch  # loop every 30s (NSSM service mode)
"""

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).parent / "static" / "links.json"
URL_RE = re.compile(r"https://[a-z0-9\-]+\.trycloudflare\.com")

SOURCES = [
    # key, label, kind, path, port_hint
    ("hive",       "QI Hive Dashboard", "json",  r"C:\QIH\engine\hive\tunnel\status\tunnel.json", 8600),
    ("maia_api",   "Maia API",          "log",   r"C:\QI\LOGS\tunnel_log.txt",                    8001),
    ("maia_ui",    "Maia UI (Gradio)",  "log",   r"C:\QI\LOGS\Maia_Gradio_Tunnel_Log.txt",        7860),
    ("naya",       "Naya",              "log",   r"C:\NAYA\LOGS\naya_tunnel_log.txt",             8002),
]


def url_from_json(path: Path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("url"), data.get("updated_at")
    except Exception:
        return None, None


def url_from_log(path: Path):
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None, None
    matches = URL_RE.findall(text)
    if not matches:
        return None, None
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    return matches[-1], mtime


def collect():
    entries = []
    for key, label, kind, path_str, port in SOURCES:
        p = Path(path_str)
        url, updated = (None, None)
        if p.exists():
            if kind == "json":
                url, updated = url_from_json(p)
            else:
                url, updated = url_from_log(p)
        entries.append({
            "key": key,
            "label": label,
            "port": port,
            "public_url": url,
            "source": str(p),
            "updated_at": updated,
        })
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tunnels": entries,
    }


def write_once():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = collect()
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    found = sum(1 for t in payload["tunnels"] if t["public_url"])
    print(f"[{datetime.now().strftime('%H:%M:%S')}] wrote {OUT.name} — {found}/{len(payload['tunnels'])} tunnels found")


def main():
    if "--watch" in sys.argv:
        while True:
            try:
                write_once()
            except Exception as e:
                print(f"collector error: {e}", file=sys.stderr)
            time.sleep(30)
    else:
        write_once()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()

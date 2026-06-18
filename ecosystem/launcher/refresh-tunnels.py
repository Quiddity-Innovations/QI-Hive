# -*- coding: utf-8 -*-
"""
QI Launchpad — Tunnel Resolver
==============================
QI Cloudflare tunnels are QUICK tunnels: their public URL is random and
changes on every restart. A file:// launcher page cannot fetch local JSON
(browser security), so we resolve the live URLs here and emit a plain
`tunnels.js` that the launcher loads via <script src> (no CORS, works from
file://).

Run automatically by Open-Launchpad.bat right before the page opens, so the
tunnel buttons always point at the current URL.

Covers every running QI_*Tunnel service (audited 2026-06-18). Add a new
tunnel = add one entry to TUNNELS below.

Sources supported:
  - "json":     read a status/tunnel.json written by a tunnel_manager ({"url","status"})
  - "log":      parse the newest matching log for the LAST trycloudflare URL
                (use "path" for one file, or "glob" for rotated logs)
  - "redirect": a static local HTML the tunnel manager rewrites (e.g. Kaze)
"""
from __future__ import annotations
import glob
import json
import os
import re
from datetime import datetime, timezone

URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com", re.I)

# --- Tunnel registry -------------------------------------------------------
# key must match data-tunnel="<key>" on the launcher buttons.
TUNNELS = {
    "maia": {
        "type": "log", "glob": r"C:\QI\LOGS\tunnel_log*.txt",
        "label": "Maia public (LINE/Telegram webhooks → :8001)",
    },
    "naya": {
        "type": "log", "path": r"C:\NAYA\LOGS\QI_NayaTunnel.stderr.log",
        "label": "Naya UI tunnel (→ :7861)",
    },
    "nexus": {
        "type": "log", "path": r"C:\NEXUS\LOGS\QI_NEXUSTunnel.stderr.log",
        "label": "NEXUS UI tunnel (→ :7880)",
    },
    "dashboard": {
        "type": "json", "path": r"C:\QIH\engine\hive\tunnel\status\tunnel.json",
        "label": "QI Hive Dashboard tunnel (→ :8600)",
    },
    "autopdf": {
        "type": "json", "path": r"C:\AutoPDF\Application\status\tunnel.json",
        "label": "AutoPDF demo tunnel (→ :6969, PIN gated)",
    },
    "cognibase": {
        "type": "log", "path": r"C:\CogniBase\LOGS\QI_CogniBaseTunnel.stderr.log",
        "label": "CogniBase tunnel (→ :8650)",
    },
    "mapsnap": {
        "type": "log", "path": r"C:\MapSnap\LOGS\QI_MapSnapTunnel.stderr.log",
        "label": "MapSnap tunnel (→ :9876)",
    },
    "cypherminer": {
        "type": "log", "path": r"C:\CypherMiner\LOGS\tunnel.log",
        "label": "CypherMiner tunnel (→ :7842)",
    },
    "lotterywiz": {
        "type": "log", "path": r"C:\Lottery Wiz\LOGS\tunnel.log",
        "label": "LotteryWiz tunnel (→ :8777)",
    },
    "tubescout": {
        "type": "log", "path": r"C:\TUBESCOUT\data\logs\tunnel.log",
        "label": "TubeScout tunnel (→ :8503)",
        "note_if_absent": "service has no logfile yet — run the elevated nssm fix, then restart",
    },
    "kaze": {
        "type": "redirect", "path": r"C:\OC\runtime\dashboard\news-tunnel.html",
        "label": "Kaze news digest (local redirect to live tunnel)",
    },
}

# tunnels.js is written to each of these folders (both launcher copies).
TARGET_DIRS = [
    r"C:\QIH\landing",
    r"C:\QIH\ecosystem\launcher",
]


def _resolve_json(cfg):
    path = cfg["path"]
    if not os.path.exists(path):
        return {"url": None, "status": "absent", "note": "no status file"}
    try:
        data = json.loads(open(path, "r", encoding="utf-8").read())
        return {
            "url": data.get("url"),
            "status": data.get("status") or ("running" if data.get("url") else "stopped"),
            "updated_at": data.get("updated_at"),
        }
    except Exception as e:  # noqa: BLE001
        return {"url": None, "status": "error", "note": str(e)}


def _resolve_log(cfg):
    if cfg.get("glob"):
        files = glob.glob(cfg["glob"])
    elif cfg.get("path"):
        files = [cfg["path"]] if os.path.exists(cfg["path"]) else []
    else:
        files = []
    if not files:
        note = cfg.get("note_if_absent", "no log file")
        return {"url": None, "status": "absent", "note": note}
    newest = max(files, key=os.path.getmtime)
    try:
        content = open(newest, "r", encoding="utf-8", errors="replace").read()
    except Exception as e:  # noqa: BLE001
        return {"url": None, "status": "error", "note": str(e)}
    matches = URL_RE.findall(content)
    if not matches:
        return {"url": None, "status": "stopped", "note": "no URL in newest log"}
    return {
        "url": matches[-1],
        "status": "running",
        "updated_at": datetime.fromtimestamp(
            os.path.getmtime(newest), tz=timezone.utc
        ).isoformat(),
    }


def _resolve_redirect(cfg):
    path = cfg["path"]
    if os.path.exists(path):
        return {"url": "file:///" + path.replace("\\", "/"), "status": "running"}
    return {"url": None, "status": "absent", "note": "no redirect file"}


def resolve_all():
    out = {}
    for key, cfg in TUNNELS.items():
        t = cfg["type"]
        if t == "json":
            r = _resolve_json(cfg)
        elif t == "log":
            r = _resolve_log(cfg)
        elif t == "redirect":
            r = _resolve_redirect(cfg)
        else:
            r = {"url": None, "status": "error", "note": "unknown type"}
        r["label"] = cfg.get("label", key)
        out[key] = r
    return out


def _add_qr(tunnels):
    """Attach an offline SVG QR code to every http(s) tunnel (for phone access)."""
    for _r in tunnels.values():
        u = _r.get("url")
        if u and u.startswith("http"):
            try:
                import io as _io, base64 as _b64, segno
                buf = _io.BytesIO()
                segno.make(u, error="m").save(buf, kind="png", scale=6, border=4,
                                              dark="#000000", light="#ffffff")
                b = _b64.b64encode(buf.getvalue()).decode("ascii")
                _r["qr"] = f'<img alt="QR code" src="data:image/png;base64,{b}">'
            except Exception:
                _r["qr"] = ""
        else:
            _r["qr"] = ""


def main():
    tunnels = resolve_all()
    _add_qr(tunnels)
    generated = datetime.now(timezone.utc).isoformat()
    payload = (
        "// Auto-generated by refresh-tunnels.py — do not edit by hand.\n"
        "// Regenerated every time you open the launcher via Open-Launchpad.bat.\n"
        f"window.QI_TUNNELS = {json.dumps(tunnels, indent=2)};\n"
        f'window.QI_TUNNELS_GENERATED = "{generated}";\n'
    )
    for d in TARGET_DIRS:
        try:
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "tunnels.js"), "w", encoding="utf-8") as f:
                f.write(payload)
            print(f"[ok] wrote {os.path.join(d, 'tunnels.js')}")
        except Exception as e:  # noqa: BLE001
            print(f"[err] {d}: {e}")
    for key, r in tunnels.items():
        print(f"  {key:12s} {r.get('status'):8s} {r.get('url') or '-'}")


if __name__ == "__main__":
    main()

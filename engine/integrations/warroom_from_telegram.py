#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QI War Room — INBOUND from Telegram (called by Tasuke / OpenClaw, runs in WSL).

When Renne sends a War Room message via Telegram, Tasuke's gateway invokes this
script with the message text. It POSTs the message to the Hive Dashboard's
/warroom/ingest endpoint on the Windows host (HTTP — NOT a direct DB write, because
SQLite WAL over the WSL /mnt boundary throws 'disk I/O error'). The dashboard writes
it tagged project_id='telegram_in'; the Windows-side responder then generates an
agent reply, which the outbound relay delivers back to Renne's Telegram DM.

Usage (from Tasuke/WSL):
    python3 warroom_from_telegram.py "the message text"

Exit 0 on success (prints the new row id), 1 on failure.
"""
import json
import subprocess
import sys
import urllib.request

DASH_PORT = 8600


def _windows_host_ips() -> list[str]:
    """Candidate IPs for the Windows host as seen from WSL2 (NAT or mirrored)."""
    ips = []
    # 1) default-route gateway = Windows host under WSL2 NAT
    try:
        out = subprocess.check_output(["ip", "route", "show", "default"], text=True, timeout=3)
        for tok in out.split():
            if tok.count(".") == 3:
                ips.append(tok); break
    except Exception:
        pass
    # 2) resolv.conf nameserver (also the host under NAT)
    try:
        for ln in open("/etc/resolv.conf"):
            if ln.startswith("nameserver"):
                ips.append(ln.split()[1]); break
    except Exception:
        pass
    # 3) mirrored-networking mode: localhost reaches Windows
    ips.append("127.0.0.1")
    # de-dupe, keep order
    seen, uniq = set(), []
    for ip in ips:
        if ip not in seen:
            seen.add(ip); uniq.append(ip)
    return uniq


def post(text: str) -> int | None:
    text = (text or "").strip()
    if not text:
        return None
    payload = json.dumps({"text": text[:8000]}).encode()
    for ip in _windows_host_ips():
        try:
            req = urllib.request.Request(
                f"http://{ip}:{DASH_PORT}/warroom/ingest", data=payload,
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=6) as r:
                out = json.loads(r.read().decode())
                if out.get("ok"):
                    return out.get("id")
        except Exception:
            continue
    return None


if __name__ == "__main__":
    rid = post(" ".join(sys.argv[1:]))
    if rid is None:
        print("error: could not reach dashboard /warroom/ingest", file=sys.stderr)
        sys.exit(1)
    print(rid)

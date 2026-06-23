#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Verify QI static named tunnels: tunnel exists, DNS resolves, service running, HTTPS responds."""
import json
import os
import socket
import subprocess
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = json.load(open(os.path.join(HERE, "tunnels.json"), encoding="utf-8"))
META = CONFIG["_meta"]
DOMAIN, CLOUDFLARED, NSSM = META["domain"], META["cloudflared"], META["nssm"]


def fqdn(entry, ing):
    h = ing["hostname"]
    d = entry.get("domain", DOMAIN)
    return d if h in ("@", "") else f"{h}.{d}"


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def tunnels_present():
    rc, out = run([CLOUDFLARED, "tunnel", "list", "--output", "json"])
    try:
        return {t["name"] for t in json.loads(out)}
    except Exception:
        return set()


def dns_ok(fqdn):
    try:
        socket.getaddrinfo(fqdn, 443)
        return True
    except Exception:
        return False


def svc_running(svc):
    rc, out = run([NSSM, "status", svc])
    return "RUNNING" in out.upper()


def https_ok(fqdn):
    try:
        req = urllib.request.Request(f"https://{fqdn}", method="HEAD")
        with urllib.request.urlopen(req, timeout=12) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code  # tunnel up, origin returned a code — still "reachable"
    except Exception:
        return None


def main():
    present = tunnels_present()
    print(f"{'TUNNEL':<16}{'SERVICE':<22}{'HOST':<40}{'TUN':<5}{'DNS':<5}{'SVC':<5}{'HTTPS'}")
    print("-" * 100)
    for e in CONFIG["tunnels"]:
        tun = "OK" if e["name"] in present else "—"
        svc = "OK" if svc_running(e["service"]) else "DOWN"
        for i, ing in enumerate(e["ingress"]):
            host = fqdn(e, ing)
            d = "OK" if dns_ok(host) else "—"
            code = https_ok(host)
            h = str(code) if code else "—"
            nm = e["name"] if i == 0 else ""
            sv = e["service"] if i == 0 else ""
            print(f"{nm:<16}{sv:<22}{host:<40}{tun:<5}{d:<5}{svc:<5}{h}")


if __name__ == "__main__":
    main()

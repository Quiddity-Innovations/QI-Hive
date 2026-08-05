# -*- coding: utf-8 -*-
"""
QI Gate — design integrity check.

Security that breaks the apps is not a win. This fetches every gated host TWICE
-- once through the public gate (signed in) and once straight at the app port --
and compares them. If the gate is transparent, the two should match closely.

Catches the class of bug that broke NEXUS: an app building absolute http://
URLs on an https:// page (mixed content, silently blocked by browsers).

    python verify_design.py --user Admin --password '...'
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

try:
    import requests
except ImportError:
    raise SystemExit("pip install requests")

GATE_DIR = Path(__file__).parent.resolve()
CFG = json.loads((GATE_DIR / "config" / "gate.json").read_text(encoding="utf-8"))
PREFIX = CFG["gate"].get("auth_prefix", "/qi-auth")
TIMEOUT = 30

ASSET_RE = re.compile(r'(?:href|src)\s*=\s*["\']([^"\']+)["\']', re.I)


def login(host, user, pw):
    s = requests.Session()
    s.post(f"https://{host}{PREFIX}/login",
           data={"username": user, "password": pw, "rd": f"https://{host}/"},
           headers={"Origin": f"https://{host}"},
           allow_redirects=False, timeout=TIMEOUT)
    return s.cookies.get("qi_gate_session")


def fetch(url, cookie=None):
    try:
        r = requests.get(url, timeout=TIMEOUT, allow_redirects=True,
                         cookies={"qi_gate_session": cookie} if cookie else {})
        return r.status_code, r.text
    except Exception as exc:
        return None, str(exc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--password", required=True)
    args = ap.parse_args()

    hosts = [h for h in CFG["hosts"] if h.get("mode") in ("protected", "mixed")]
    anchor = hosts[0]["host"]
    cookie = login(anchor, args.user, args.password)
    if not cookie:
        raise SystemExit("could not sign in — check credentials")

    print(f"{'HOST':<40} {'GATED':<12} {'DIRECT':<12} {'SIZE Δ':<10} MIXED-CONTENT")
    print("-" * 100)

    problems = []
    for h in hosts:
        host, up = h["host"], h["upstream"]
        gs, gt = fetch(f"https://{host}/", cookie)
        ds, dt = fetch(f"http://{up}/")

        if gs is None:
            print(f"{host:<40} {'ERR':<12} {'-':<12} {'-':<10} {gt[:30]}")
            problems.append(f"{host}: gated fetch failed — {gt[:60]}")
            continue
        if ds is None:
            # App itself is down — not a gate problem, but say so.
            print(f"{host:<40} {'HTTP '+str(gs):<12} {'DOWN':<12} {'-':<10} "
                  f"(app not running)")
            continue

        # Mixed content: absolute http:// links back to this same host.
        mixed = [u for u in ASSET_RE.findall(gt)
                 if u.lower().startswith(f"http://{host.lower()}")
                 or u.lower().startswith("http://127.0.0.1")
                 or u.lower().startswith("http://localhost")]
        # Gradio embeds its config as JSON too, so scan the raw body as well.
        raw_http = len(re.findall(rf'http://{re.escape(host)}', gt, re.I))

        delta = len(gt) - len(dt)
        pct = abs(delta) / max(len(dt), 1) * 100
        size_note = f"{delta:+d}" if pct < 5 else f"{delta:+d} !"

        flag = ""
        if mixed or raw_http:
            flag = f"{len(mixed) + raw_http} http:// refs"
            problems.append(f"{host}: {flag} — browsers will block these")
        if pct >= 5:
            problems.append(f"{host}: page differs {pct:.0f}% from direct fetch")

        print(f"{host:<40} {'HTTP '+str(gs):<12} {'HTTP '+str(ds):<12} "
              f"{size_note:<10} {flag or 'clean'}")

    print("\n" + "=" * 100)
    if problems:
        print(f"[!] {len(problems)} issue(s):")
        for p in problems:
            print(f"    - {p}")
        return 1
    print("[OK] Every app renders through the gate the same as it does directly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

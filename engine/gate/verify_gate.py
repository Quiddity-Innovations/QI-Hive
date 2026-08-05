# -*- coding: utf-8 -*-
"""
QI Gate — public exposure verification.

Hits every hostname in config/gate.json over the real internet and asserts the
policy actually holds:

  protected  -> anonymous request must be bounced to the login page
  mixed      -> declared public_paths must still answer; anything else bounced
  open       -> reachable (documented exception)

Also confirms an authenticated session gets through, so a false "secure" that
is really "broken" cannot pass unnoticed.

    python verify_gate.py                 # anonymous checks only
    python verify_gate.py --user Admin --password '...'    # + logged-in check
"""

import argparse
import json
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
TIMEOUT = 25


def get(url, cookies=None):
    try:
        return requests.get(url, allow_redirects=False, timeout=TIMEOUT,
                            cookies=cookies or {})
    except Exception as exc:
        return exc


def gated(resp) -> bool:
    """True if this response is the login wall."""
    if isinstance(resp, Exception):
        return False
    if resp.status_code in (301, 302, 303, 307, 308):
        return PREFIX in resp.headers.get("location", "")
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user")
    ap.add_argument("--password")
    args = ap.parse_args()

    hosts = CFG["hosts"]
    rows, failures = [], []

    for h in hosts:
        host, mode = h["host"], h.get("mode", "protected")
        url = f"https://{host}/"
        r = get(url)

        if mode == "open":
            if isinstance(r, Exception):
                verdict, detail = "UNREACHABLE", str(r)[:60]
            else:
                verdict, detail = "open", f"HTTP {r.status_code} (documented exception)"
        elif isinstance(r, Exception):
            verdict, detail = "ERROR", str(r)[:60]
            failures.append(f"{host}: unreachable — {detail}")
        elif gated(r):
            verdict, detail = "GATED", "anonymous -> login"
        else:
            code = r.status_code
            verdict, detail = "EXPOSED", f"HTTP {code} with no login!"
            failures.append(f"{host}: NOT protected (HTTP {code})")

        rows.append((host, mode, verdict, detail))

        # mixed: the declared bypass paths must still work, or webhooks break
        for p in h.get("public_paths", []) if mode == "mixed" else []:
            # A trailing '/' means "prefix and everything under it", which Caddy
            # matches as /prefix/* — that does NOT match the bare /prefix. Probe
            # a path actually under it, or every prefix rule looks like a failure.
            probe = (p.rstrip("/") + "/__gatecheck") if p.endswith("/") else p
            pr = get(f"https://{host}{probe}")
            if isinstance(pr, Exception):
                rows.append((f"  {probe}", "public", "ERROR", str(pr)[:50]))
                failures.append(f"{host}{probe}: unreachable")
            elif gated(pr):
                rows.append((f"  {probe}", "public", "BLOCKED", "bypass not working!"))
                failures.append(f"{host}{probe}: webhook path is being gated")
            else:
                rows.append((f"  {probe}", "public", "passes",
                             f"HTTP {pr.status_code}"))

    print(f"{'HOST':<46} {'MODE':<10} {'VERDICT':<12} DETAIL")
    print("-" * 108)
    for host, mode, verdict, detail in rows:
        print(f"{host:<46} {mode:<10} {verdict:<12} {detail}")

    # Prove the wall opens for a real account — "everything 302s" could also
    # mean everything is simply broken.
    if args.user and args.password:
        print("\n=== authenticated pass-through ===")
        target = next((h["host"] for h in hosts if h.get("mode") == "protected"), None)
        if target:
            s = requests.Session()
            s.post(f"https://{target}{PREFIX}/login",
                   data={"username": args.user, "password": args.password,
                         "rd": f"https://{target}/"},
                   headers={"Origin": f"https://{target}"},
                   allow_redirects=False, timeout=TIMEOUT)
            cookie = s.cookies.get("qi_gate_session")
            if not cookie:
                print("  [FAIL] login did not return a session cookie")
                failures.append("login flow broken")
            else:
                ok = 0
                for h in hosts:
                    if h.get("mode") not in ("protected", "mixed"):
                        continue
                    r = get(f"https://{h['host']}/", cookies={"qi_gate_session": cookie})
                    good = (not isinstance(r, Exception)) and not gated(r)
                    print(f"  {'OK  ' if good else 'FAIL'} {h['host']:<44} "
                          f"{'HTTP ' + str(r.status_code) if not isinstance(r, Exception) else str(r)[:40]}")
                    ok += bool(good)
                print(f"  {ok}/{sum(1 for h in hosts if h.get('mode') in ('protected','mixed'))} "
                      f"reachable when signed in")

    print("\n" + "=" * 108)
    if failures:
        print(f"[!] {len(failures)} PROBLEM(S):")
        for f in failures:
            print(f"    - {f}")
        return 1
    print("[OK] Every protected host requires a login; every declared public path still answers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

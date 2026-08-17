# -*- coding: utf-8 -*-
"""
Restart QI_BrainAPI together with its dependent services, in a safe order.

QI_BrainAPI has four dependents — QI_MaiaBot, QI_NayaBot, QI_NEXUS, QI_Dashboard —
so Windows refuses a bare `nssm restart QI_BrainAPI`. Maia serves public LINE
traffic, so the goal is the shortest possible window and a verified recovery.

Order: stop dependents (reverse priority) -> restart Brain -> start dependents
back (priority order) -> verify every health endpoint.

Everything goes through the QI elevation broker. NOTE: never ask the broker to
restart itself — it stops before it can write its own result and cannot bring
itself back. (Learned the hard way, 2026-08-17.)
"""
from __future__ import annotations
import sys, time, json, urllib.request
from pathlib import Path

sys.path.insert(0, r"C:\QIH\engine\common")
sys.stdout.reconfigure(encoding="utf-8")
from qi_elevate_client import run_elevated  # noqa: E402

BRAIN = "QI_BrainAPI"
# Stopped in this order, started back in reverse (Dashboard last to stop, first back).
DEPENDENTS = ["QI_MaiaBot", "QI_NayaBot", "QI_NEXUS", "QI_Dashboard"]

HEALTH = {
    "QI_BrainAPI":  "http://127.0.0.1:9011/health",
    "QI_Dashboard": "http://127.0.0.1:8600/health",
    "QI_MaiaBot":   "http://127.0.0.1:8001/",
    "QI_NayaBot":   "http://127.0.0.1:8002/",
    "QI_NEXUS":     "http://127.0.0.1:8010/",
}


def svc(action: str, name: str) -> bool:
    r = run_elevated("nssm", [action, name], submitted_by="audit_brain_restart", timeout=90)
    ok = r["status"] == "ok"
    detail = (r.get("stdout") or r.get("stderr") or "").strip().replace("\n", " ")[:90]
    print(f"  {action:6} {name:16} {'ok' if ok else 'FAILED'}  {detail}")
    return ok


def probe(name: str, timeout: float = 60.0) -> bool:
    url = HEALTH.get(name)
    if not url:
        return True
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=4) as r:
                if r.status < 500:
                    return True
        except Exception:
            pass
        time.sleep(2)
    return False


def main() -> int:
    print("=== stopping dependents ===")
    for s in DEPENDENTS:
        svc("stop", s)

    print("\n=== restarting Brain ===")
    svc("stop", BRAIN)
    time.sleep(2)
    svc("start", BRAIN)
    print(f"  brain health: {'UP' if probe(BRAIN) else 'DOWN'}")

    print("\n=== starting dependents back ===")
    for s in reversed(DEPENDENTS):
        svc("start", s)

    print("\n=== verifying ===")
    failed = []
    for s in [BRAIN] + DEPENDENTS:
        up = probe(s)
        print(f"  {s:16} {'UP' if up else '** DOWN **'}")
        if not up:
            failed.append(s)

    print("\n" + ("ALL SERVICES RECOVERED" if not failed else f"!! STILL DOWN: {failed}"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

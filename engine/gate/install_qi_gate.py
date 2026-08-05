# -*- coding: utf-8 -*-
"""
Install QI Gate as the NSSM service QI_Gate, via the QI_Elevate broker.

Follows the QI service convention: QI_ prefix, no spaces, Description set,
AppDirectory set, logs under C:\\QIH\\logs. Registered in
C:\\QIH\\ecosystem\\QI_Service_Registry.md.

    python C:\\QIH\\engine\\gate\\install_qi_gate.py
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\QIH\engine\common")
from qi_elevate_client import run_elevated  # noqa: E402

SERVICE = "QI_Gate"
PYTHON = r"C:\1-AI\APPS\PYTHON\python.exe"
SCRIPT = r"C:\QIH\engine\gate\qi_gate.py"
APPDIR = r"C:\QIH\engine\gate"
DESC = ("QI Gate - authentication wall in front of every internet-exposed QI "
        "application. Caddy (:9040) proxies public tunnels and asks this "
        "service (:9041) whether the caller is signed in.")

STEPS = [
    ("install",     ["install", SERVICE, PYTHON, SCRIPT]),
    ("appdir",      ["set", SERVICE, "AppDirectory", APPDIR]),
    ("stdout",      ["set", SERVICE, "AppStdout", r"C:\QIH\logs\qi_gate.log"]),
    ("stderr",      ["set", SERVICE, "AppStderr", r"C:\QIH\logs\qi_gate.err.log"]),
    ("startmode",   ["set", SERVICE, "Start", "SERVICE_AUTO_START"]),
    ("description", ["set", SERVICE, "Description", DESC]),
]


def main():
    for name, args in STEPS:
        r = run_elevated("nssm", args, submitted_by="claude:qi_gate_install", timeout=45)
        status = r.get("status")
        out = (r.get("stdout") or r.get("stderr") or "").strip()[:160]
        flag = "OK " if status == "ok" else "!! "
        print(f"[{flag}] {name:<12} {status:<8} {out}")
        if status == "denied":
            print(f"        DENIED: {r.get('error')}")
            return 1
    r = run_elevated("nssm", ["start", SERVICE],
                     submitted_by="claude:qi_gate_install", timeout=45)
    print(f"[{'OK ' if r.get('status') == 'ok' else '!! '}] start        "
          f"{r.get('status')} {(r.get('stdout') or r.get('stderr') or '').strip()[:160]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

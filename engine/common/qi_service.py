"""
QI Service helper — autonomous service control via the elevation broker.

After discovering (2026-04-19) that `nssm stop/start` fails with
OpenService: Access denied from the LocalSystem broker — but `sc.exe`
works cleanly — this module prefers `sc` for service control. nssm is
still used for config queries (AppDirectory, AppParameters, etc).

Usage:
    from engine.common.qi_service import restart, stop, start, status
    restart("QI_Dashboard")
"""
from __future__ import annotations
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from qi_elevate_client import run_elevated


def status(name: str, submitted_by: str = "qi_service") -> str:
    r = run_elevated("sc", ["query", name], submitted_by=submitted_by, timeout=15)
    out = r.get("stdout", "")
    if "RUNNING" in out:     return "RUNNING"
    if "STOP_PENDING" in out: return "STOP_PENDING"
    if "START_PENDING" in out:return "START_PENDING"
    if "STOPPED" in out:     return "STOPPED"
    return "UNKNOWN"


def stop(name: str, submitted_by: str = "qi_service", wait: float = 6.0) -> bool:
    r = run_elevated("sc", ["stop", name], submitted_by=submitted_by, timeout=15)
    if r.get("status") != "ok":
        return False
    deadline = time.time() + wait
    while time.time() < deadline:
        if status(name) == "STOPPED":
            return True
        time.sleep(0.5)
    return status(name) == "STOPPED"


def start(name: str, submitted_by: str = "qi_service", wait: float = 10.0) -> bool:
    r = run_elevated("sc", ["start", name], submitted_by=submitted_by, timeout=15)
    if r.get("status") != "ok":
        return False
    deadline = time.time() + wait
    while time.time() < deadline:
        if status(name) == "RUNNING":
            return True
        time.sleep(0.5)
    return status(name) == "RUNNING"


def restart(name: str, submitted_by: str = "qi_service") -> bool:
    stopped = stop(name, submitted_by)
    if not stopped:
        return False
    time.sleep(1.0)
    return start(name, submitted_by)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["restart", "stop", "start", "status"])
    ap.add_argument("service")
    args = ap.parse_args()
    fn = {"restart": restart, "stop": stop, "start": start, "status": status}[args.action]
    result = fn(args.service)
    print(f"{args.action} {args.service}: {result}")

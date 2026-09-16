# -*- coding: utf-8 -*-
"""
qi_restart_service.py — restart an NSSM-run QI service even when other
services depend on it.

Why: `sc stop QI_BrainAPI` fails with 1051 ("other running services are
dependent on this service") because QI_Dashboard, QI_MaiaBot, QI_NayaBot and
QI_NEXUS declare a dependency on it. The dashboard's Ops restart action
therefore never actually restarted the Brain API (audit 2026-09-16: the
process serving :9011 dated from 2026-09-05 while the code on disk was newer).

How: find the service's NSSM host PID (`sc queryex`), kill its child
process tree (the real app), and let NSSM's AppExit=Restart policy relaunch
it — the SCM never sees a stop, so dependents are untouched. Then wait for
the registered port to answer again.

Usage (must run with rights over the service's process — LocalSystem via the
dashboard Ops action, or an admin shell):
    python qi_restart_service.py QI_BrainAPI [--port 9011] [--timeout 60]
Only services whose name starts with QI_ are accepted.
"""
from __future__ import annotations
import argparse, json, re, socket, subprocess, sys, time

sys.stdout.reconfigure(encoding="utf-8")


def sh(cmd: list[str]) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (p.stdout or "") + (p.stderr or "")


def service_pid(name: str) -> int | None:
    out = sh(["sc", "queryex", name])
    m = re.search(r"PID\s*:\s*(\d+)", out)
    return int(m.group(1)) if m else None


def children(pid: int) -> list[dict]:
    ps = ("Get-CimInstance Win32_Process -Filter \"ParentProcessId=%d\" | "
          "Select ProcessId,Name,CreationDate | ConvertTo-Json -Compress") % pid
    out = sh(["powershell.exe", "-NoProfile", "-Command", ps]).strip()
    if not out:
        return []
    data = json.loads(out)
    return data if isinstance(data, list) else [data]


def port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.5):
            return True
    except OSError:
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("service")
    ap.add_argument("--port", type=int, default=0, help="port that must answer after restart")
    ap.add_argument("--timeout", type=int, default=60)
    a = ap.parse_args()
    if not a.service.startswith("QI_"):
        print("refused: only QI_* services"); return 2
    host = service_pid(a.service)
    if not host:
        print(f"{a.service}: not running or not found"); return 1
    kids = children(host)
    if not kids:
        print(f"{a.service}: NSSM host {host} has no child process — using sc restart instead")
        print(sh(["sc", "stop", a.service])); time.sleep(3); print(sh(["sc", "start", a.service]))
    else:
        for k in kids:
            print(f"{a.service}: killing app process {k['ProcessId']} ({k['Name']}, started {k.get('CreationDate')})")
            print(sh(["taskkill", "/PID", str(k["ProcessId"]), "/T", "/F"]).strip())
    deadline = time.time() + a.timeout
    while time.time() < deadline:
        time.sleep(2)
        new = children(host)
        if new and (not a.port or port_open(a.port)):
            print(f"{a.service}: relaunched by NSSM as PID {new[0]['ProcessId']}"
                  + (f", port {a.port} answering" if a.port else ""))
            return 0
    print(f"{a.service}: NOT back within {a.timeout}s — check nssm status / logs")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""
Remove the three orphaned pre-migration NSSM services found by the
2026-09-16 audit. Fixed list, no arguments accepted from the caller:

    ClaudeManager   stopped; old dashboard at C:\\APPS\\CLAUDE\\Dashboard, claims port 8600
                    (the live QI_Dashboard's port) if anyone ever starts it
    NayaTunnel      stopped; cloudflared quick tunnel (--url, random hostname) for :7861,
                    superseded by QI_NayaTunnel (named tunnel qi-naya)
    NEXUSTunnel     running; cloudflared quick tunnel for :7880, superseded by
                    QI_NEXUSTunnel (named tunnel qi-nexus). Quick tunnels get a new random
                    hostname on every start, so nothing can depend on this one.

Safety: refuses to touch any service not in the list, records every service's
Application / AppParameters / AppDirectory / Description to
C:\\QIH\\_archive\\legacy_services_<stamp>.json BEFORE removal (that file is the
rollback: `nssm install <name> <app> <params>` + `nssm set <name> AppDirectory ...`),
stops the service first, then `nssm remove <name> confirm`.
Must run elevated (LocalSystem via the dashboard Ops action, or an admin shell).
"""
from __future__ import annotations
import json, subprocess, sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
NSSM = r"C:\QIH\engine\bin\nssm.exe"
LEGACY = ["ClaudeManager", "NayaTunnel", "NEXUSTunnel"]
ARCHIVE = Path(r"C:\QIH\_archive")


def nssm(*args) -> str:
    p = subprocess.run([NSSM, *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return ((p.stdout or "") + (p.stderr or "")).replace("\x00", "").strip()


def main() -> int:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    record = {"stamp": datetime.now().isoformat(timespec="seconds"), "services": {}}
    rc = 0
    for name in LEGACY:
        status = nssm("status", name)
        if "SERVICE_" not in status:
            print(f"{name}: not installed ({status}) — nothing to do")
            continue
        record["services"][name] = {k: nssm("get", name, k) for k in
                                    ("Application", "AppParameters", "AppDirectory", "Description", "ObjectName")}
        record["services"][name]["status_before"] = status
        print(f"{name}: {status} | {record['services'][name]['Application']} {record['services'][name]['AppParameters']}")
    out = ARCHIVE / f"legacy_services_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print("rollback record ->", out)
    for name in record["services"]:
        if "RUNNING" in record["services"][name]["status_before"]:
            print(f"{name}: stopping ... {nssm('stop', name)}")
        res = nssm("remove", name, "confirm")
        print(f"{name}: remove -> {res}")
        if "removed successfully" not in res.lower():
            rc = 1
    print("done rc", rc)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

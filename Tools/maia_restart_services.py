# -*- coding: utf-8 -*-
"""
maia_restart_services.py
Restarts Maia NSSM services without requiring admin rights.
Pre-requisite: run grant_claude_service_rights.ps1 once as admin.

Usage:
    python maia_restart_services.py           # restarts MaiaTunnel + MaiaBot
    python maia_restart_services.py maiabot   # restarts only MaiaBot
    python maia_restart_services.py tunnel    # restarts only MaiaTunnel
    python maia_restart_services.py all       # restarts all three Maia services
"""

import sys, subprocess, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# MaiaTunnel must stop before MaiaBot (dependency order)
SERVICES = {
    "maiabot":  ["MaiaBot"],
    "tunnel":   ["MaiaTunnel"],
    "demo":     ["MaiaDemoTunnel"],
    "all":      ["MaiaTunnel", "MaiaBot", "MaiaDemoTunnel"],
}
DEFAULT = ["MaiaTunnel", "MaiaBot"]

def restart_service(name):
    print(f"  Stopping {name}...", end=" ", flush=True)
    r = subprocess.run(["sc.exe", "stop", name], capture_output=True, text=True)
    if r.returncode not in (0, 1062):
        print(f"warn ({r.returncode})")
    else:
        print("stopped.")
    time.sleep(2)
    print(f"  Starting {name}...", end=" ", flush=True)
    r = subprocess.run(["sc.exe", "start", name], capture_output=True, text=True)
    if r.returncode == 0:
        print("started. OK")
        return True
    else:
        print(f"FAILED ({r.returncode}) {r.stderr.strip()[:80]}")
        return False

def main():
    target = (sys.argv[1].lower() if len(sys.argv) > 1 else "default")
    svcs   = SERVICES.get(target, DEFAULT)
    print(f"\n=== Maia Service Restart: {', '.join(svcs)} ===\n")
    ok = all(restart_service(s) for s in svcs)
    print(f"\n{'All services restarted.' if ok else 'Some services failed - check logs.'}\n")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()

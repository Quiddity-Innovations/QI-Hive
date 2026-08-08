# -*- coding: utf-8 -*-
"""Collect the live QI connectivity picture: services, ports, tunnels, gate, hub."""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
OUT = {}

# ── 1. QI_* services and their state ────────────────────────────────────────
ps = subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     "Get-Service QI_* | Select-Object Name,Status | ConvertTo-Json"],
    capture_output=True, text=True, timeout=90)
try:
    svcs = json.loads(ps.stdout)
    OUT["services"] = {s["Name"]: ("Running" if s["Status"] in (4, "Running") else "Stopped")
                       for s in svcs}
except Exception as e:
    OUT["services"] = {"_error": str(e)}

# ── 2. Listening ports -> owning process ────────────────────────────────────
net = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=90)
listen = {}
for line in net.stdout.splitlines():
    m = re.match(r"\s*TCP\s+(\S+):(\d+)\s+\S+\s+LISTENING\s+(\d+)", line)
    if m:
        addr, port, pid = m.group(1), int(m.group(2)), m.group(3)
        listen.setdefault(port, {"pids": set(), "addrs": set()})
        listen[port]["pids"].add(pid)
        listen[port]["addrs"].add(addr)

tl = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True, timeout=90)
pidname = {}
for line in tl.stdout.splitlines():
    parts = [p.strip('"') for p in line.split('","')]
    if len(parts) >= 2:
        pidname[parts[1].strip('"')] = parts[0].strip('"')

OUT["ports"] = {}
for port, info in sorted(listen.items()):
    names = sorted({pidname.get(p, "?") for p in info["pids"]})
    binds = sorted(info["addrs"])
    scope = "ALL-INTERFACES" if any(a in ("0.0.0.0", "::") for a in binds) else "loopback"
    OUT["ports"][port] = {"process": ",".join(names), "scope": scope}

# ── 3. Cloudflare tunnels: config -> hostname -> upstream ───────────────────
OUT["tunnels"] = {}
cfg_dir = Path(r"C:\QIH\engine\tunnels\configs")
if cfg_dir.exists():
    for f in sorted(cfg_dir.glob("*.yml")):
        txt = f.read_text(encoding="utf-8", errors="replace")
        pairs = re.findall(r"hostname:\s*(\S+)\s*\n\s*service:\s*(\S+)", txt)
        OUT["tunnels"][f.stem] = [{"hostname": h, "service": s} for h, s in pairs]

# ── 4. QI Gate: what the internet may reach ─────────────────────────────────
gate = json.loads(Path(r"C:\QIH\engine\gate\config\gate.json").read_text(encoding="utf-8"))
OUT["gate"] = {"listen": gate["gate"]["listen_port"], "auth": gate["gate"]["auth_port"],
               "hosts": [{"host": h["host"], "upstream": h["upstream"],
                          "app": h.get("app", ""), "mode": h["mode"],
                          "public_paths": h.get("public_paths", [])}
                         for h in gate["hosts"]]}

# ── 5. Hub usage: who actually calls NEXUS ──────────────────────────────────
try:
    import urllib.request
    with urllib.request.urlopen("http://127.0.0.1:8010/hub/usage", timeout=20) as r:
        OUT["hub_usage"] = json.loads(r.read().decode("utf-8")).get("per_app", [])
except Exception as e:
    OUT["hub_usage"] = [{"_error": str(e)}]

dest = Path(sys.argv[1])
dest.write_text(json.dumps(OUT, indent=2, default=str), encoding="utf-8")
print("services :", len(OUT["services"]))
print("ports    :", len(OUT["ports"]))
print("tunnels  :", len(OUT["tunnels"]),
      "->", sum(len(v) for v in OUT["tunnels"].values()), "hostnames")
print("gate     :", len(OUT["gate"]["hosts"]), "hosts")
print("hub apps :", len(OUT["hub_usage"]))
print("written  :", dest)

"""Verify QI NSSM Batch 1 after it ran: binary, display name, state, dependencies, key health URLs.
No admin needed. Exit 1 if anything is off."""
import json, subprocess, sys, urllib.request
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
plan = [r for r in json.loads((HERE / "batch1_plan.json").read_text(encoding="utf-8")) if r["action"] == "repoint"]
mans = sorted(HERE.glob("batch1_rollback_*.json"))
before = {r["name"]: r for r in json.loads(mans[-1].read_text(encoding="utf-8-sig"))} if mans else {}

ps = ("Get-CimInstance Win32_Service | Where-Object Name -match '^QI_' | ForEach-Object { "
      "$d = (Get-Service $_.Name).ServicesDependedOn.Name -join ','; "
      "'{0}|{1}|{2}|{3}|{4}' -f $_.Name,$_.DisplayName,$_.State,$_.PathName,$d }")
live = {}
for line in subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True).stdout.splitlines():
    n, d, s, p, dep = line.split("|", 4)
    live[n] = dict(display=d, state=s, bin=p.strip().strip('"'), deps=[x for x in dep.split(",") if x])

problems = []
for r in plan:
    n, L = r["name"], live.get(r["name"])
    if not L:
        problems.append(f"{n}: service missing"); continue
    if L["bin"].lower() != r["target_bin"].lower():
        problems.append(f"{n}: binary {L['bin']} (expected {r['target_bin']})")
    if L["display"] != r["target_display"]:
        problems.append(f"{n}: display '{L['display']}'")
    if before.get(n, {}).get("was_running") and L["state"] != "Running":
        problems.append(f"{n}: was running, now {L['state']}")
for n in ("QI_NEXUS", "QI_MaiaBot", "QI_NayaBot"):
    if "QI_BrainAPI" in live.get(n, {}).get("deps", []):
        problems.append(f"{n}: still depends on QI_BrainAPI")
if "QI_MaiaDemoTunnel" in live:
    problems.append("QI_MaiaDemoTunnel: still installed")
shared = [n for n, L in live.items() if L["bin"].lower() == r"c:\qih\engine\bin\nssm.exe"]
if shared:
    problems.append("still on shared nssm.exe: " + ", ".join(shared))

for name, url in [("NEXUS API", "http://127.0.0.1:8010/health"), ("NEXUS UI", "http://127.0.0.1:7880/"),
                  ("Maia API", "http://127.0.0.1:8001/health"), ("Brain API", "http://127.0.0.1:9011/health")]:
    try:
        code = urllib.request.urlopen(url, timeout=8).status
        print(f"  {'OK ' if code == 200 else 'BAD'} {name:10} {url} -> {code}")
        if code != 200:
            problems.append(f"{name} health {code}")
    except Exception as e:
        print(f"  BAD {name:10} {url} -> {e}")
        problems.append(f"{name} health: {e}")

running = sum(1 for L in live.values() if L["state"] == "Running")
print(f"\n{len(plan)} planned | {running} QI services running | problems: {len(problems)}")
for p in problems:
    print("  !!", p)
sys.exit(1 if problems else 0)

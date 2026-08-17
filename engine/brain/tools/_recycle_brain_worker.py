# -*- coding: utf-8 -*-
"""Force-kill the QI_BrainAPI worker PID so nssm (AppExit=Restart) respawns it
fresh — reloads poller.py WITHOUT an nssm service stop, so the 4 dependent
services stay up. Then verify health + that the new inbox path is in effect."""
import sys, json, time, socket, urllib.request, subprocess
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\QIH")
from engine.common.qi_elevate_client import run_elevated

# Identify current worker PID on 9011
def pid_on_9011():
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if ":9011 " in line and "LISTENING" in line:
            return line.split()[-1]
    return None

old_pid = pid_on_9011()
print("old worker PID on 9011:", old_pid)

print("=== force-kill via QI_Elevate broker ===")
r = run_elevated("taskkill", ["/PID", str(old_pid), "/F"], submitted_by="claude_brain_cleanup", timeout=30)
print("broker status:", r.get("status"))
print("stdout:", (r.get("stdout") or "").strip())
print("stderr:", (r.get("stderr") or "").strip())

print("\n=== waiting for nssm to respawn worker (AppRestartDelay ~5s) ===")
new_pid = None
for i in range(1, 21):
    time.sleep(2)
    p = pid_on_9011()
    try:
        # 127.0.0.1, not "localhost": ::1 is dropped rather than refused on
        # this box, so a localhost URL burns the full timeout every attempt.
        with urllib.request.urlopen("http://127.0.0.1:9011/health", timeout=3) as resp:
            body = resp.read().decode("utf-8")
        if p and p != old_pid:
            new_pid = p
            print(f"attempt {i}: respawned PID {p} | {body}")
            break
        print(f"attempt {i}: PID {p} health={body}")
    except Exception as e:
        print(f"attempt {i}: not ready ({e.__class__.__name__})")

print("\nnew worker PID:", new_pid, "(changed)" if new_pid and new_pid != old_pid else "(WARN: unchanged)")

# Confirm the running process now uses the live inbox path via /api/status poller info
for ep in ("/api/status", "/health"):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:9011{ep}", timeout=4) as resp:
            print(f"\n{ep}:", resp.read().decode("utf-8")[:400])
    except Exception:
        pass

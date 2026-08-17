"""Reconcile: what is on disk vs what the registry knows vs what has a service.

Answers "there are applications missing" by showing, for every candidate app,
which of the three systems of record know about it.
"""
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

REG = r"C:\QIH\ecosystem\qi_registry.json"
NSSM = r"C:\QIH\engine\bin\nssm.exe"

NOT_APPS = {
    "inetpub", "POWERSPEC - G484 DRIVERS", "Server 2012 R2", "Plex",
    "PerfLogs", "Windows", "Program Files", "Program Files (x86)",
    "ProgramData", "Users", "Recovery", "$Recycle.Bin",
    "System Volume Information", "Documents and Settings", "temp", "Temp",
}

# ---- disk -----------------------------------------------------------------
disk = []
for name in sorted(os.listdir("C:\\")):
    p = os.path.join("C:\\", name)
    if not os.path.isdir(p) or name in NOT_APPS or name.startswith("$"):
        continue
    disk.append(name)

# ---- registry -------------------------------------------------------------
reg = json.load(open(REG, encoding="utf-8"))
projects = reg["projects"]
reg_by_path = {}
for pr in projects:
    path = (pr.get("path") or "").rstrip("\\")
    reg_by_path[path.lower()] = pr

# ---- services -------------------------------------------------------------
svc_dirs = {}
try:
    out = subprocess.run([NSSM, "list"], capture_output=True, text=True, timeout=60)
    names = [l.strip() for l in out.stdout.splitlines() if l.strip().startswith("QI_")]
except Exception:
    names = []
for s in names:
    try:
        r = subprocess.run([NSSM, "get", s, "AppDirectory"],
                           capture_output=True, timeout=30)
        d = r.stdout.decode("utf-16", errors="ignore").strip().strip("\x00")
        if not d:
            d = r.stdout.decode("utf-8", errors="ignore").strip().strip("\x00")
        svc_dirs.setdefault(d.lower().rstrip("\\"), []).append(s)
    except Exception:
        pass


def services_for(path):
    path = path.lower().rstrip("\\")
    hits = []
    for d, ss in svc_dirs.items():
        if d == path or d.startswith(path + "\\"):
            hits.extend(ss)
    return sorted(set(hits))


print("=" * 86)
print("%-26s %-10s %-22s %s" % ("FOLDER ON C:\\", "REGISTRY", "STATUS", "SERVICES"))
print("=" * 86)

unregistered = []
for name in disk:
    full = "c:\\" + name.lower()
    pr = reg_by_path.get(full)
    svcs = services_for("C:\\" + name)
    if pr:
        mark = "yes"
        status = pr.get("status", "?")
    else:
        mark = "-- NO --"
        status = ""
        unregistered.append(name)
    print("%-26s %-10s %-22s %s" % (
        name[:26], mark, status[:22],
        (", ".join(svcs)[:34] or "-")))

print()
print("=" * 86)
print("REGISTRY ENTRIES WHOSE PATH IS NOT A C:\\ ROOT FOLDER")
print("=" * 86)
for pr in sorted(projects, key=lambda x: x.get("id", "")):
    path = (pr.get("path") or "").rstrip("\\")
    top = path.split("\\")
    is_root = len(top) == 2 and top[0].lower() == "c:"
    if not is_root:
        exists = os.path.isdir(path)
        print("  %-20s %-46s exists=%s" % (
            pr.get("id"), path[:46], exists))

print()
print("=" * 86)
print("SUMMARY")
print("=" * 86)
print("  folders on C:\\ that look like apps : %d" % len(disk))
print("  registered projects                : %d" % len(projects))
print("  folders with NO registry entry     : %d" % len(unregistered))
for u in unregistered:
    print("       %s" % u)

missing_path = [pr for pr in projects
                if pr.get("path") and not os.path.isdir(pr["path"])]
print("  registry entries whose path is GONE: %d" % len(missing_path))
for pr in missing_path:
    print("       %-20s %s" % (pr.get("id"), pr.get("path")))

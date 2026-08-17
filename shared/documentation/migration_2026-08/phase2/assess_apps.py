"""Pre-move assessment: duplicates, oddities, and per-app reference counts.

Renne's rules for this pass:
  - nothing is deleted, ever
  - duplicates: keep the live one, preserve the other as <App>_Dupe
  - deletion candidates: rename <App>_for deletion, do not remove
  - ARCHIVE is left for last and paused on
"""
import json
import os
import subprocess
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

REG = r"C:\QIH\ecosystem\qi_registry.json"

APPS = [
    "AkiyaScout", "AutoPDF", "AutoPDF_Portable", "CLAUDE", "CogniBase",
    "CypherMiner", "EasyFlow", "Gamez", "Lottery Wiz", "M2V", "MailBrain",
    "MapSnap", "MQ", "NAYA", "NEXUS", "OC", "PersonalSong", "PlayDeck",
    "QI", "QIB", "QIP", "Retirement Analyzer", "RetirementAnalyzer",
    "SCRIPTS", "TUBESCOUT", "VLCDaemon", "ARCHIVE",
]


def size_of(path):
    total = 0
    files = 0
    for dp, dn, fn in os.walk(path):
        low = dp.lower()
        if "\\node_modules" in low or "\\.git\\" in low:
            dn[:] = []
            continue
        for f in fn:
            try:
                total += os.path.getsize(os.path.join(dp, f))
                files += 1
            except OSError:
                pass
    return total, files


def human(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return "%.1f %s" % (n, u)
        n /= 1024
    return "%.1f TB" % n


# registry
registered = {}
try:
    d = json.load(open(REG, encoding="utf-8"))
    for pr in d.get("projects", []):
        p = (pr.get("path") or "").rstrip("\\")
        registered[p.lower()] = pr
except Exception as exc:                                       # noqa: BLE001
    print("registry read failed: %r" % (exc,))

# services per top-level dir
svc = {}
try:
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Service | Where-Object { $_.PathName -match 'nssm' } | "
         "ForEach-Object { $k='HKLM:\\SYSTEM\\CurrentControlSet\\Services\\'+$_.Name+'\\Parameters'; "
         "$p=Get-ItemProperty $k -ErrorAction SilentlyContinue; "
         "$_.Name + '|' + $p.AppDirectory + '|' + $p.AppParameters + '|' + $_.State }"],
        capture_output=True, text=True, timeout=240)
    for line in out.stdout.splitlines():
        parts = line.strip().split("|")
        if len(parts) < 4:
            continue
        name, appdir, appparams, state = parts[0], parts[1], parts[2], parts[3]
        blob = (appdir + " " + appparams).lower()
        for a in APPS:
            if ("c:\\" + a.lower() + "\\") in blob or blob.strip().endswith("c:\\" + a.lower()):
                svc.setdefault(a, []).append("%s(%s)" % (name, state))
except Exception as exc:                                       # noqa: BLE001
    print("service scan failed: %r" % (exc,))

print("=" * 96)
print("%-24s %-9s %-8s %-11s %s" % ("FOLDER", "EXISTS", "SIZE", "REGISTERED", "SERVICES"))
print("=" * 96)

present = []
for a in APPS:
    p = os.path.join("C:\\", a)
    if not os.path.isdir(p):
        print("%-24s %-9s" % (a[:24], "absent"))
        continue
    present.append(a)
    b, f = size_of(p)
    reg = registered.get(p.lower())
    rid = reg.get("id") if reg else "-"
    print("%-24s %-9s %-8s %-11s %s" % (
        a[:24], "yes", human(b), rid, ", ".join(svc.get(a, []))[:34] or "-"))

# ---- duplicate / oddity detection ---------------------------------------
print()
print("=" * 96)
print("DUPLICATES AND ODDITIES")
print("=" * 96)

pairs = [
    ("AutoPDF", "AutoPDF_Portable"),
    ("Retirement Analyzer", "RetirementAnalyzer"),
]
for a, b in pairs:
    pa, pb = os.path.join("C:\\", a), os.path.join("C:\\", b)
    ea, eb = os.path.isdir(pa), os.path.isdir(pb)
    print("  %s  vs  %s" % (a, b))
    print("      %-28s exists=%s" % (a, ea))
    print("      %-28s exists=%s" % (b, eb))
    if ea and eb:
        sa, _ = size_of(pa)
        sb, _ = size_of(pb)
        print("      sizes: %s vs %s" % (human(sa), human(sb)))
        print("      registered: %s / %s" % (
            registered.get(pa.lower(), {}).get("id", "-") if registered.get(pa.lower()) else "-",
            registered.get(pb.lower(), {}).get("id", "-") if registered.get(pb.lower()) else "-"))
        print("      services  : %s / %s" % (svc.get(a, "-"), svc.get(b, "-")))
    print()

# registry entries whose path does not exist
print("  registry entries pointing at a missing folder:")
missing = 0
for path, pr in registered.items():
    if not os.path.isdir(path):
        print("      %-20s %s" % (pr.get("id"), pr.get("path")))
        missing += 1
if not missing:
    print("      (none)")

# git status - is anything uncommitted before we move it?
print()
print("=" * 96)
print("UNCOMMITTED WORK (move would carry it, but worth knowing)")
print("=" * 96)
for a in present:
    p = os.path.join("C:\\", a)
    if not os.path.isdir(os.path.join(p, ".git")):
        continue
    try:
        r = subprocess.run(["git", "-C", p, "status", "--porcelain"],
                           capture_output=True, text=True, timeout=90)
        n = len([x for x in r.stdout.splitlines() if x.strip()])
        if n:
            print("  %-24s %d changed file(s)" % (a, n))
    except Exception:
        pass

print()
print("assessed %d folders at %s" % (len(present), datetime.now().strftime("%Y-%m-%d %H:%M")))

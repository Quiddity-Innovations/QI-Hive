"""Classify every folder at the root of C: against Renne's target end state.

Goal: nothing self-created at the root of C:, except temp and tmp which stay.
OS and third-party installers keep their own conventions.
"""
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

REG = r"C:\QIH\ecosystem\qi_registry.json"

# Windows / vendor owned - not ours, leave alone.
OS_OWNED = {
    "Windows", "Program Files", "Program Files (x86)", "ProgramData",
    "Users", "PerfLogs", "Recovery", "$Recycle.Bin", "$WinREAgent",
    "System Volume Information", "Documents and Settings", "Config.Msi",
    "OneDriveTemp", "inetpub", "hiberfil.sys", "pagefile.sys", "swapfile.sys",
    "DumpStack.log.tmp", "bootTel.dat",
}

# Renne asked for these to remain, at least for now.
KEEP_BY_REQUEST = {"temp", "tmp", "TEMP", "TMP"}

# Vendor tools that install to C:\ root by their own default.
THIRD_PARTY = {
    "Plex": "Plex Media Server - vendor default. Reinstallable to Program Files.",
    "POWERSPEC - G484 DRIVERS": "OEM driver dump. Archive to D: or delete.",
    "Server 2012 R2": "OS media/ISO extract. Archive to D: or delete.",
    "GOOSE": "Third-party (Goose agent). Check before moving.",
}

NOTES = {
    "1-AI": "Junction stub only - holds APPS\\PYTHON -> Program Files\\Python311. "
            "Disappears once the 11 remaining venvs are rebuilt.",
    "1-AI.RETIRED_2026-08-09": "RETIRED TREE, 17.28 GB. Safe to delete: "
                               "AvatarStudio already copied to C:\\APPS, the "
                               "597 MB pip cache is regenerable, VSCode and "
                               "LM Studio get reinstalled.",
    "APPS": "The new home. STAYS.",
    "QIH": "PERMANENT EXCEPTION, decided by Renne 2026-08-09. The Hive engine "
           "stays at C:\\QIH. Rationale: ~21,700 references across the "
           "ecosystem, hosts 30 services, and is Tier C in the packaging plan "
           "- it never ships, so it gains nothing from living under C:\\APPS. "
           "Recorded as a decision rather than a deferred move so it is not "
           "re-litigated later.",
    "ARCHIVE": "Unregistered. Candidate for D:.",
    "SCRIPTS": "Unregistered loose scripts. Fold into C:\\APPS or delete.",
    "VLCDaemon": "Unregistered. Check, then move or delete.",
    "QIB": "Unregistered. Identify before moving.",
    "QIP": "Unregistered, but contains QIP\\Connector which IS registered. "
           "Move as a unit to C:\\APPS\\QIP.",
    "MailBrain": "Git project, 2,225 references, in NEITHER the registry nor "
                 "the Brain. Register it first, then move.",
    "AutoPDF_Portable": "Portable duplicate of AutoPDF. Probably deletable.",
    "CLAUDE": "Contains Claude Voice + Tools (headroom). Both registered. "
              "Move as a unit.",
}

# Load registry
registered = {}
try:
    d = json.load(open(REG, encoding="utf-8"))
    for pr in d.get("projects", []):
        p = (pr.get("path") or "").rstrip("\\")
        registered[p.lower()] = pr.get("id")
except Exception as exc:                                       # noqa: BLE001
    print("registry read failed: %r" % (exc,))

# Services by directory
svc_by_dir = {}
try:
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Service | Where-Object { $_.PathName -match 'nssm' } | "
         "ForEach-Object { $k='HKLM:\\SYSTEM\\CurrentControlSet\\Services\\'+$_.Name+'\\Parameters'; "
         "$p=Get-ItemProperty $k -ErrorAction SilentlyContinue; "
         "if ($p.AppDirectory) { $_.Name + '|' + $p.AppDirectory } }"],
        capture_output=True, text=True, timeout=180)
    for line in out.stdout.splitlines():
        if "|" in line:
            name, dirp = line.strip().split("|", 1)
            top = dirp.strip().rstrip("\\").split("\\")
            if len(top) >= 2 and top[0].lower() == "c:":
                svc_by_dir.setdefault(top[1].lower(), []).append(name)
except Exception:
    pass

rows = []
for name in sorted(os.listdir("C:\\"), key=str.lower):
    full = os.path.join("C:\\", name)
    if not os.path.isdir(full):
        continue
    if name in OS_OWNED:
        continue

    if name in KEEP_BY_REQUEST:
        verdict = "STAY (your request)"
    elif name in ("APPS",):
        verdict = "STAY (destination)"
    elif name == "QIH":
        verdict = "STAY (exception)"
    elif name in THIRD_PARTY:
        verdict = "THIRD-PARTY"
    elif name.startswith("1-AI"):
        verdict = "TRANSITIONAL"
    else:
        verdict = "MOVE -> C:\\APPS\\" + name.replace(" ", "")

    reg_id = registered.get(full.lower(), "")
    svcs = svc_by_dir.get(name.lower(), [])
    rows.append((name, verdict, reg_id, len(svcs)))

print("=" * 100)
print("%-28s %-26s %-18s %s" % ("C:\\ FOLDER", "VERDICT", "REGISTRY ID", "SVCS"))
print("=" * 100)
move = 0
for name, verdict, reg_id, n in rows:
    if verdict.startswith("MOVE"):
        move += 1
    print("%-28s %-26s %-18s %s" % (name[:28], verdict, reg_id or "-", n or "-"))

print()
print("=" * 100)
print("NOTES")
print("=" * 100)
for name, _, _, _ in rows:
    if name in NOTES:
        print("  %s" % name)
        print("      %s" % NOTES[name])
    elif name in THIRD_PARTY:
        print("  %s" % name)
        print("      %s" % THIRD_PARTY[name])

print()
print("folders to move: %d" % move)
print("target end state: C:\\APPS, C:\\QIH, temp, tmp, plus OS and Program Files only.")

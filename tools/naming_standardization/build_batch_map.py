# -*- coding: utf-8 -*-
"""Build the batch-file standardization map with per-file risk classification.
Scans QI project roots for .bat files, proposes <Product>_<Role>.bat names,
and finds every textual reference (scripts, docs, scheduled tasks, NSSM hooks).
Output: batch_map.json  (reviewed before the Friday execution).
Created 2026-06-23.
"""
import os, re, json, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")

OUT = r"C:\QIH\tools\naming_standardization\batch_map.json"

# project root -> product label
ROOTS = {
    r"C:\APPS\QI": "Maia",
    r"C:\APPS\NAYA": "Naya",
    r"C:\APPS\NEXUS": "NEXUS",
    r"C:\APPS\TUBESCOUT": "TubeScout",
    r"C:\APPS\PersonalSong": "PersonalSong",
    r"C:\APPS\CLAUDE\Claude Voice": "ClaudeVoice",
    r"C:\APPS\CLAUDE\Dashboard": "Hive",
    r"C:\APPS\EasyFlow": "EasyFlow",
}
# folders we never touch
EXCLUDE = ("\\.git", "worktree", "maia_archive", "node_modules", "\\.venv",
           "\\runtime\\tmp", "\\scripts\\", "site-packages")

ROLE_RULES = [
    (r"control", "Control"),
    (r"restart", "Restart"),
    (r"^start[_-]|^run_server|^start_server|^run_queue|^run_cycle|^run_server", "Start"),
    (r"install|setup", "Install"),
    (r"^run_", "Run"),
]

def product_for(path):
    p = path.lower()
    best = None
    for root, prod in ROOTS.items():
        if p.startswith(root.lower()):
            if best is None or len(root) > len(best[0]):
                best = (root, prod)
    return best[1] if best else None

def role_for(name):
    base = name[:-4].lower()
    for pat, role in ROLE_RULES:
        if re.search(pat, base):
            return role
    return None

def excluded(path):
    pl = path.lower()
    return any(x in pl for x in EXCLUDE)

# --- gather candidate .bat files
cands = []
for root in ROOTS:
    if not os.path.isdir(root):
        continue
    for dp, dns, fns in os.walk(root):
        if excluded(dp):
            dns[:] = []
            continue
        depth = dp[len(root):].count(os.sep)
        if depth > 2:
            continue
        for fn in fns:
            if fn.lower().endswith(".bat"):
                full = os.path.join(dp, fn)
                if excluded(full):
                    continue
                cands.append(full)

# --- scheduled-task references
task_refs = {}
try:
    ps = ('Get-ScheduledTask | ForEach-Object { $t=$_; $_.Actions | '
          'ForEach-Object { if ($_.Arguments) { "{0}|{1}" -f $t.TaskName, $_.Arguments } } }')
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                         capture_output=True, text=True, timeout=60).stdout
    for line in out.splitlines():
        if "|" in line and ".bat" in line.lower():
            tn, args = line.split("|", 1)
            for m in re.findall(r'[A-Za-z]:\\[^"]+?\.bat', args):
                task_refs.setdefault(os.path.basename(m).lower(), []).append(tn.strip())
except Exception as e:
    task_refs["_error"] = str(e)

# --- NSSM hook references (services whose AppEvents/hook params point at a .bat)
hook_bats = set()
try:
    q = subprocess.run(["powershell", "-NoProfile", "-Command",
        r"Get-ChildItem 'HKLM:\SYSTEM\CurrentControlSet\Services' | "
        r"Where-Object {$_.Name -match 'QI_'} | ForEach-Object { "
        r"$p=Join-Path $_.PSPath 'Parameters'; if(Test-Path $p){ "
        r"(Get-ItemProperty $p) | Out-String } }"],
        capture_output=True, text=True, timeout=60).stdout
    for m in re.findall(r'[A-Za-z]:\\[^\s"]+?\.bat', q):
        hook_bats.add(os.path.basename(m).lower())
except Exception:
    pass

# --- build map + reference scan
SCAN_EXT = (".py", ".ps1", ".bat", ".cmd", ".md", ".json", ".txt", ".lnk")
entries = []
for full in sorted(set(cands)):
    name = os.path.basename(full)
    prod = product_for(full)
    role = role_for(name)
    new = f"{prod}_{role}.bat" if (prod and role) else None
    risk = []
    if name.lower() in task_refs:
        risk.append("scheduled-task")
    if name.lower() in hook_bats:
        risk.append("nssm-hook")
    if "backup" in name.lower():
        risk.append("backup-file")
    if new is None:
        risk.append("no-role/product")
    entries.append({
        "path": full, "current": name, "product": prod, "role": role,
        "proposed": new,
        "tasks": task_refs.get(name.lower(), []),
        "risk": risk,
        "auto_safe": (new is not None and not risk),
    })

data = {
    "generated": "2026-06-23",
    "note": "auto_safe=true -> rename + reference-rewrite automatically. "
            "risk!=[] -> needs explicit handling (task/hook/backup updated or skipped).",
    "scheduled_task_bat_refs": task_refs,
    "nssm_hook_bats": sorted(hook_bats),
    "count_total": len(entries),
    "count_auto_safe": sum(1 for e in entries if e["auto_safe"]),
    "entries": entries,
}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print(f"total bat candidates: {len(entries)}")
print(f"auto-safe renames   : {data['count_auto_safe']}")
print(f"with risk flags     : {sum(1 for e in entries if e['risk'])}")
print(f"scheduled-task bats : {list(task_refs.keys())}")
print(f"nssm-hook bats      : {sorted(hook_bats)[:10]}")
print(f"written: {OUT}")

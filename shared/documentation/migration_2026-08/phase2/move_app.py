"""Move one app from C:\\<App> to C:\\APPS\\<App>, updating every live reference.

Renne's constraints for this pass:
  - NO junction or pointer left behind. C:\\<App> must not exist afterwards.
  - NOTHING is ever deleted. The original is relocated to the hold area on D:,
    which is off C: as required but fully recoverable.
  - The application must not break.

Order of operations is chosen so a failure at any point is recoverable:

  1. inventory  - what references this app
  2. stop       - its services
  3. copy       - robocopy, source untouched
  4. verify     - file counts must match, or abort and restart services
  5. repoint    - services, tasks, registry, configs, docs, source
  6. start      - services, health check
  7. retire     - move the original to D:\\_PREMOVE_2026-08-09\\<App>
  8. confirm    - C:\\<App> gone, no stale references anywhere

Usage:
    python move_app.py --app AkiyaScout            # dry run
    python move_app.py --app AkiyaScout --apply
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

APPS_ROOT = r"C:\APPS"
HOLD = r"D:\_PREMOVE_2026-08-09"
REG = r"C:\QIH\ecosystem\qi_registry.json"
CLAUDE_JSON = r"C:\Users\renne\.claude.json"
TUNNEL_CFG = r"C:\QIH\engine\tunnels\configs"

# Files we rewrite as text. Anything not listed here is left alone.
TEXT_EXTS = {".md", ".json", ".yml", ".yaml", ".py", ".ps1", ".bat", ".cmd",
             ".ini", ".cfg", ".toml", ".txt", ".env"}

# Never rewrite: history, snapshots, regenerated artifacts, build output.
SKIP_PARTS = (
    "\\node_modules\\", "\\site-packages\\", "\\.git\\", "\\worktrees\\",
    "\\__pycache__\\", "\\dist\\", "\\build\\", "\\.next\\",
    "\\migration_2026-08\\", "\\usage_archive\\", "\\reports\\archive\\",
    "\\commands\\archive\\", "\\project_library_BACKUP", "\\_BACKUP",
    "\\.claude\\tasks\\", "\\shell-snapshots\\", "\\statsig\\", "\\todos\\",
    "\\logs\\", "\\LOGS\\", "\\data\\status.json", "\\.venv\\", "\\venv\\",
    "\\_PREMOVE", "\\1-AI.RETIRED",
    # Point-in-time records. Rewriting these would make them claim a layout
    # that did not exist on the date they describe.
    "\\self_audits\\", "\\data\\ops_history.json", "\\session_summaries\\",
)

# Where to look for references. Deliberately bounded.
REF_ROOTS = [
    r"C:\QIH", r"C:\Users\renne\.claude", APPS_ROOT,
]


def ps(cmd, timeout=300):
    return subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                          capture_output=True, text=True, timeout=timeout)


def skip(path):
    low = path.lower()
    return any(s.lower() in low for s in SKIP_PARTS)


def count_files(path):
    n = 0
    b = 0
    for dp, dn, fn in os.walk(path):
        for f in fn:
            try:
                b += os.path.getsize(os.path.join(dp, f))
                n += 1
            except OSError:
                pass
    return n, b


# ---------------------------------------------------------------- services
def services_for(app):
    """NSSM services whose config mentions C:\\<app>."""
    cmd = (
        "Get-CimInstance Win32_Service | Where-Object { $_.PathName -match 'nssm' } | "
        "ForEach-Object { $k='HKLM:\\SYSTEM\\CurrentControlSet\\Services\\'+$_.Name+'\\Parameters'; "
        "$p=Get-ItemProperty $k -ErrorAction SilentlyContinue; "
        "[PSCustomObject]@{Name=$_.Name;State=$_.State;"
        "Application=$p.Application;AppDirectory=$p.AppDirectory;"
        "AppParameters=$p.AppParameters;AppStdout=$p.AppStdout;AppStderr=$p.AppStderr} } | "
        "ConvertTo-Json -Depth 3"
    )
    r = ps(cmd)
    try:
        data = json.loads(r.stdout or "[]")
    except Exception:
        return []
    if isinstance(data, dict):
        data = [data]
    needle = ("c:\\" + app + "\\").lower()
    exact = ("c:\\" + app).lower()
    hits = []
    for s in data:
        blob = " ".join(str(s.get(f) or "") for f in
                        ("Application", "AppDirectory", "AppParameters",
                         "AppStdout", "AppStderr")).lower()
        if needle in blob or re.search(re.escape(exact) + r'(?![a-z0-9_\- ])', blob):
            hits.append(s)
    return hits


def set_service_field(name, field, value):
    """Write straight to the registry.

    'nssm set' fails SILENTLY against services registered by a different nssm
    binary - it reports success while the registry keeps the old value. That
    was observed on OC-Keepalive-Service earlier in this migration.
    """
    key = r"HKLM:\SYSTEM\CurrentControlSet\Services\%s\Parameters" % name
    val = value.replace("'", "''")
    ps("Set-ItemProperty -Path '%s' -Name '%s' -Value '%s'" % (key, field, val))


# ---------------------------------------------------------------- tasks
def tasks_for(app):
    cmd = (
        "Get-ScheduledTask | ForEach-Object { $t=$_; $t.Actions | ForEach-Object { "
        "[PSCustomObject]@{Path=$t.TaskPath;Name=$t.TaskName;"
        "Execute=$_.Execute;Arguments=$_.Arguments;WD=$_.WorkingDirectory} } } | "
        "ConvertTo-Json -Depth 3"
    )
    r = ps(cmd)
    try:
        data = json.loads(r.stdout or "[]")
    except Exception:
        return []
    if isinstance(data, dict):
        data = [data]
    needle = ("c:\\" + app).lower()
    return [t for t in data
            if needle in (str(t.get("Execute") or "") + " " +
                          str(t.get("Arguments") or "") + " " +
                          str(t.get("WD") or "")).lower()]


# ---------------------------------------------------------------- text refs
def text_refs(app):
    old = "C:\\" + app
    old_fwd = "C:/" + app
    hits = []
    roots = list(REF_ROOTS)
    for r in roots:
        if not os.path.isdir(r):
            continue
        for dp, dn, fn in os.walk(r):
            if skip(dp + "\\"):
                dn[:] = []
                continue
            for f in fn:
                if os.path.splitext(f)[1].lower() not in TEXT_EXTS:
                    continue
                full = os.path.join(dp, f)
                if skip(full):
                    continue
                try:
                    if os.path.getsize(full) > 3_000_000:
                        continue
                    t = open(full, encoding="utf-8", errors="replace").read()
                except OSError:
                    continue
                n = (len(re.findall(re.escape(old) + r'(?![A-Za-z0-9_\-])', t, re.I)) +
                     len(re.findall(re.escape(old_fwd) + r'(?![A-Za-z0-9_\-])', t, re.I)) +
                     t.count(old.replace("\\", "\\\\")))
                if n:
                    hits.append((full, n))
    return hits


def rewrite_text(path, app, apply):
    old = "C:\\" + app
    new = APPS_ROOT + "\\" + app
    subs = [
        (old.replace("\\", "\\\\"), new.replace("\\", "\\\\")),   # JSON-escaped
        (old, new),
        ("C:/" + app, APPS_ROOT.replace("\\", "/") + "/" + app),
    ]
    try:
        t = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return 0
    out = t
    for o, n in subs:
        # Do not match a longer sibling name: C:\QI must not hit C:\QIH.
        out = re.sub(re.escape(o) + r'(?![A-Za-z0-9_\-])', n.replace("\\", "\\\\"), out)
    if out == t:
        return 0
    if apply:
        bak = path + ".bak-move"
        if not os.path.exists(bak):
            shutil.copy2(path, bak)
        open(path, "w", encoding="utf-8").write(out)
    return 1


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    app = args.app
    src = os.path.join("C:\\", app)
    dst = os.path.join(APPS_ROOT, app)
    hold = os.path.join(HOLD, app)

    print("=" * 78)
    print("MOVE  %s  ->  %s" % (src, dst))
    print("=" * 78)

    if not os.path.isdir(src):
        print("FATAL: source does not exist")
        return 1
    if os.path.isdir(dst):
        print("FATAL: destination already exists: " + dst)
        return 1

    n_src, b_src = count_files(src)
    print("source: %d files, %.2f GB" % (n_src, b_src / 1024**3))

    # ---- 1. inventory ----------------------------------------------------
    svcs = services_for(app)
    tsks = tasks_for(app)
    refs = text_refs(app)
    print()
    print("services referencing it : %d" % len(svcs))
    for s in svcs:
        print("   %-26s [%s]" % (s["Name"], s["State"]))
    print("scheduled tasks         : %d" % len(tsks))
    for t in tsks:
        print("   %s%s" % (t["Path"], t["Name"]))
    print("text files with refs    : %d  (%d refs)" % (len(refs), sum(n for _, n in refs)))
    for f, n in refs[:12]:
        print("   %2d  %s" % (n, f))
    if len(refs) > 12:
        print("   ... and %d more files" % (len(refs) - 12))

    if not args.apply:
        print()
        print("DRY RUN - nothing changed. Re-run with --apply.")
        return 0

    was_running = [s["Name"] for s in svcs if s["State"] == "Running"]

    # ---- 2. stop ---------------------------------------------------------
    if svcs:
        print()
        print("=== stopping services ===")
        for s in svcs:
            ps("Stop-Service -Name '%s' -Force -ErrorAction SilentlyContinue" % s["Name"])
            print("   %s stopped" % s["Name"])
        ps("Start-Sleep -Seconds 3")

    # ---- 3. copy ---------------------------------------------------------
    print()
    print("=== copying ===")
    os.makedirs(APPS_ROOT, exist_ok=True)
    r = subprocess.run(["robocopy", src, dst, "/E", "/MT:16", "/R:1", "/W:1",
                        "/NFL", "/NDL", "/NP", "/NJH", "/NJS"],
                       capture_output=True, text=True)
    print("   robocopy exit %d (0-7 ok)" % r.returncode)
    if r.returncode >= 8:
        print("FATAL: copy failed. Restarting services, source untouched.")
        for n in was_running:
            ps("Start-Service -Name '%s' -ErrorAction SilentlyContinue" % n)
        return 1

    # ---- 4. verify -------------------------------------------------------
    n_dst, b_dst = count_files(dst)
    print("   dest: %d files, %.2f GB" % (n_dst, b_dst / 1024**3))
    if n_dst != n_src:
        print("FATAL: file count mismatch (%d vs %d). Restarting services." % (n_dst, n_src))
        for n in was_running:
            ps("Start-Service -Name '%s' -ErrorAction SilentlyContinue" % n)
        return 1
    print("   file count matches")

    # ---- 5. repoint ------------------------------------------------------
    print()
    print("=== repointing services ===")
    for s in svcs:
        for f in ("Application", "AppDirectory", "AppParameters", "AppStdout", "AppStderr"):
            v = s.get(f)
            if not v:
                continue
            nv = re.sub(re.escape("C:\\" + app) + r'(?![A-Za-z0-9_\-])',
                        (APPS_ROOT + "\\" + app).replace("\\", "\\\\"), v, flags=re.I)
            if nv != v:
                set_service_field(s["Name"], f, nv)
                print("   %s.%s -> %s" % (s["Name"], f, nv))

    print()
    print("=== repointing scheduled tasks ===")
    for t in tsks:
        newx = re.sub(re.escape("C:\\" + app) + r'(?![A-Za-z0-9_\-])',
                      (APPS_ROOT + "\\" + app).replace("\\", "\\\\"),
                      str(t.get("Execute") or ""), flags=re.I)
        newa = re.sub(re.escape("C:\\" + app) + r'(?![A-Za-z0-9_\-])',
                      (APPS_ROOT + "\\" + app).replace("\\", "\\\\"),
                      str(t.get("Arguments") or ""), flags=re.I)
        neww = re.sub(re.escape("C:\\" + app) + r'(?![A-Za-z0-9_\-])',
                      (APPS_ROOT + "\\" + app).replace("\\", "\\\\"),
                      str(t.get("WD") or ""), flags=re.I)
        parts = ["$a = New-ScheduledTaskAction -Execute '%s'" % newx.replace("'", "''")]
        if newa:
            parts[0] += " -Argument '%s'" % newa.replace("'", "''")
        if neww:
            parts[0] += " -WorkingDirectory '%s'" % neww.replace("'", "''")
        parts.append("Set-ScheduledTask -TaskPath '%s' -TaskName '%s' -Action $a | Out-Null"
                     % (t["Path"], t["Name"]))
        ps("; ".join(parts))
        print("   %s%s updated" % (t["Path"], t["Name"]))

    print()
    print("=== rewriting text references ===")
    # Re-scan now that the copy exists: the app's own files may reference its
    # old path, and those live under C:\APPS\<App> which did not exist when the
    # first inventory ran.
    refs2 = text_refs(app)
    print("   files to rewrite (post-copy rescan): %d" % len(refs2))
    done = 0
    for f, _ in refs2:
        done += rewrite_text(f, app, True)
    print("   files rewritten: %d" % done)

    # ---- 6. start --------------------------------------------------------
    if was_running:
        print()
        print("=== restarting services ===")
        for n in was_running:
            ps("Start-Service -Name '%s' -ErrorAction SilentlyContinue" % n)
        ps("Start-Sleep -Seconds 8")
        for n in was_running:
            r2 = ps("(Get-Service -Name '%s').Status" % n)
            print("   %-26s %s" % (n, r2.stdout.strip()))

    # ---- 7. retire the original -----------------------------------------
    print()
    print("=== retiring the original ===")
    os.makedirs(HOLD, exist_ok=True)
    if os.path.isdir(hold):
        print("   hold path already exists: " + hold)
        return 1
    r3 = subprocess.run(["robocopy", src, hold, "/E", "/MOVE", "/MT:16",
                         "/R:1", "/W:1", "/NFL", "/NDL", "/NP", "/NJH", "/NJS"],
                        capture_output=True, text=True)
    print("   robocopy /MOVE exit %d" % r3.returncode)
    if os.path.isdir(src):
        try:
            os.rmdir(src)
        except OSError as exc:
            print("   NOTE: %s still present: %s" % (src, exc))

    # ---- 8. confirm ------------------------------------------------------
    print()
    print("=== confirm ===")
    print("   C:\\%s exists : %s   (must be False)" % (app, os.path.isdir(src)))
    print("   %s exists : %s" % (dst, os.path.isdir(dst)))
    print("   held at %s : %s" % (hold, os.path.isdir(hold)))
    left = text_refs(app)
    print("   stale text references: %d" % sum(n for _, n in left))
    for f, n in left[:5]:
        print("      %2d  %s" % (n, f))
    print("=== DONE ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Repoint the interpreter baked into a venv's console-script .exe launchers.

When a folder containing a venv is moved, the venv's own python.exe still works
(it is a copy), but every pip-generated console script in Scripts\\ carries the
OLD absolute interpreter path inside its binary and breaks.

That is why moving C:\\CLAUDE naively would kill QI_Headroom: the service runs
headroom_env\\Scripts\\headroom.exe, not python.exe.

Locating the shebang:
    Do NOT scan forward for b'#!'. The t64 launcher stub embeds its own error
    strings, one of which is literally "Expected to find '!' following '#' in
    shebang line". A forward scan hits that first, and rewriting there produces
    a launcher that dies with 0xC0000005. This was reproduced and fixed earlier
    in this migration. Anchor on the appended zip's PK\\x03\\x04 magic and scan
    BACKWARDS.

Each rewrite is verified by reopening the result with zipfile; a failure is
rolled back from the .bak automatically.

Usage:
    python fix_venv_scripts.py --scripts "C:\\APPS\\CLAUDE\\Tools\\headroom_env\\Scripts" \
        --old "C:\\CLAUDE" --new "C:\\APPS\\CLAUDE" [--apply]
"""
import argparse
import glob
import os
import shutil
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8")


def read_shebang(blob):
    z = blob.find(b"PK\x03\x04")
    if z < 0:
        return None
    i = blob.rfind(b"#!", 0, z)
    if i < 0:
        return None
    j = blob.find(b"\n", i, z)
    if j < 0:
        return None
    return i, j + 1, blob[i:j + 1]


def verify(path):
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
        return any(n.endswith("__main__.py") for n in names)
    except Exception:                                          # noqa: BLE001
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scripts", required=True)
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    old_b = args.old.encode()
    new_b = args.new.encode()

    exes = sorted(glob.glob(os.path.join(args.scripts, "*.exe")))
    if not exes:
        print("no .exe found in " + args.scripts)
        return 1

    stale, fixed, failed, clean = [], [], [], 0
    for exe in exes:
        blob = open(exe, "rb").read()
        hit = read_shebang(blob)
        if not hit or old_b.lower() not in hit[2].lower():
            clean += 1
            continue
        stale.append(exe)
        if not args.apply:
            continue

        start, end, line = hit
        path = line[2:].rstrip(b"\r\n").strip(b'"')
        # case-insensitive replace of the old prefix
        low = path.lower()
        idx = low.find(old_b.lower())
        newpath = path[:idx] + new_b + path[idx + len(old_b):]
        new_line = b'#!"' + newpath + b'"\r\n'

        bak = exe + ".bak-venvmove"
        if not os.path.exists(bak):
            shutil.copy2(exe, bak)
        with open(exe, "wb") as fh:
            fh.write(blob[:start] + new_line + blob[end:])

        if verify(exe):
            fixed.append(exe)
        else:
            shutil.copy2(bak, exe)
            failed.append(exe)

    print("scanned : %d" % len(exes))
    print("clean   : %d" % clean)
    print("stale   : %d" % len(stale))
    if args.apply:
        print("fixed   : %d" % len(fixed))
        print("failed  : %d" % len(failed))
        for f in failed:
            print("   FAIL (rolled back) " + os.path.basename(f))
    else:
        for e in stale[:15]:
            print("   stale " + os.path.basename(e))
        if len(stale) > 15:
            print("   ... and %d more" % (len(stale) - 15))
        print()
        print("DRY RUN - re-run with --apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

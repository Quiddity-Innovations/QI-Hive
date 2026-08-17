"""Rewrite the interpreter path baked into pip console-script .exe launchers.

A pip/distlib console script on Windows is:

    <launcher stub .exe>  +  b"#!<path to python.exe>\r\n"  +  <zip of __main__>

The stub reads the shebang line and execs that interpreter. Copying the file
does not change the shebang, so a copied Scripts\\ directory keeps invoking the
old interpreter.

The replacement path is longer than the original, which shifts the zip payload.
That is safe: zipfile locates the end-of-central-directory by scanning from the
end and compensates for arbitrary prepended data. This script verifies that
claim on every file it rewrites by re-opening the result with zipfile.

Usage:
    python fix_console_scripts.py --check          # report only
    python fix_console_scripts.py --apply          # rewrite in place (.bak kept)
"""
import argparse
import glob
import io
import os
import shutil
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8")

OLD = rb"C:\1-AI\APPS\PYTHON"
NEW = rb"C:\Program Files\Python311"
SCRIPTS = r"C:\Program Files\Python311\Scripts"


def read_shebang(blob):
    """Return (start, end, text) of the real shebang line, or None.

    Do NOT scan forward for b'#!'. The t64 launcher stub embeds its own error
    strings, one of which is "Expected to find '!' following '#' in shebang
    line" -- a forward scan hits that first and rewriting there produces a
    launcher that dies with 0xC0000005. The genuine shebang is the line
    immediately preceding the appended zip payload, so anchor on the zip
    local-file-header magic and scan backwards.
    """
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


def rewrite(blob):
    hit = read_shebang(blob)
    if not hit:
        return None
    start, end, line = hit
    if OLD not in line:
        return None
    new_path = line.replace(OLD, NEW)
    # The new path contains a space, so it must be quoted for the launcher.
    body = new_path[2:].rstrip(b"\r\n")
    body = body.strip(b'"')
    new_line = b'#!"' + body + b'"\r\n'
    return blob[:start] + new_line + blob[end:]


def verify(path):
    """The rewritten file must still be a readable zip with a __main__."""
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
        return any(n.endswith("__main__.py") for n in names), names[:3]
    except Exception as exc:                                  # noqa: BLE001
        return False, repr(exc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--scripts", default=SCRIPTS)
    args = ap.parse_args()

    exes = sorted(glob.glob(os.path.join(args.scripts, "*.exe")))
    if not exes:
        print("No .exe found in " + args.scripts)
        return 1

    stale, clean, failed, fixed = [], [], [], []

    for exe in exes:
        blob = open(exe, "rb").read()
        if OLD not in blob:
            clean.append(exe)
            continue
        stale.append(exe)
        if not args.apply:
            continue

        new_blob = rewrite(blob)
        if new_blob is None:
            failed.append((exe, "old path present but not in shebang"))
            continue

        bak = exe + ".bak"
        if not os.path.exists(bak):
            shutil.copy2(exe, bak)
        with open(exe, "wb") as fh:
            fh.write(new_blob)

        ok, detail = verify(exe)
        if ok:
            fixed.append(exe)
        else:
            shutil.copy2(bak, exe)          # roll this one back
            failed.append((exe, "zip verify failed: %r -> restored" % (detail,)))

    print("scanned : %d" % len(exes))
    print("clean   : %d" % len(clean))
    print("stale   : %d" % len(stale))
    if args.apply:
        print("fixed   : %d" % len(fixed))
        print("failed  : %d" % len(failed))
        for exe, why in failed:
            print("   FAIL " + os.path.basename(exe) + " : " + why)
    else:
        for exe in stale[:10]:
            print("   stale " + os.path.basename(exe))
        if len(stale) > 10:
            print("   ... and %d more" % (len(stale) - 10))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

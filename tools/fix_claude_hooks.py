#!/usr/bin/env python3
"""
Fix Claude Code hook commands that are mangled by the bash launcher.

Two compounding bugs in the existing config:
  1. Windows backslash paths (C:\\Program Files\\...) are passed to bash, which treats
     backslashes as escape characters — "C:\\Users\\renne" collapses to "C:Usersrenne".
  2. The interpreter path contains a space and is unquoted, so bash splits it at
     "C:/Program" and reports "command not found".

Fix: normalize every path to forward slashes and quote any token containing a space.

Usage:
    python fix_claude_hooks.py            # dry run - show the diff
    python fix_claude_hooks.py --apply    # write it (backs up first)
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SETTINGS = Path(r"C:\Users\renne\.claude\settings.json")

# Matches a leading executable path ending in .exe, quoted or bare, possibly with spaces.
EXE_RE = re.compile(r'^\s*(?:"([^"]+\.exe)"|((?:[A-Za-z]:)?[^"]*?\.exe))(\s|$)', re.IGNORECASE)


def q(path: str) -> str:
    """Normalize slashes; quote if the path contains a space."""
    p = path.replace("\\", "/")
    return f'"{p}"' if " " in p else p


def fix_command(cmd: str) -> str:
    m = EXE_RE.match(cmd)
    if not m:
        return cmd  # e.g. bare "python ..." or "powershell ..." - leave alone
    exe = m.group(1) or m.group(2)
    rest = cmd[m.end(0) - len(m.group(3)):].strip()

    # Normalize slashes BEFORE tokenizing: shlex in posix mode treats backslashes as
    # escapes and would silently eat them, turning C:\Users\renne into C:Usersrenne.
    rest = rest.replace("\\", "/")

    # Re-quote remaining tokens. Only rewrite things that look like Windows paths;
    # leave flags and plain words untouched.
    out_tokens = []
    for tok in shlex.split(rest, posix=True) if rest else []:
        if re.match(r"^[A-Za-z]:[\\/]", tok):
            out_tokens.append(q(tok))
        elif " " in tok:
            out_tokens.append(f'"{tok}"')
        else:
            out_tokens.append(tok)

    return " ".join([q(exe), *out_tokens])


def verify(cmd: str) -> tuple[bool, str]:
    """Tokenize the way bash will and confirm the first two tokens exist on disk."""
    try:
        toks = shlex.split(cmd, posix=True)
    except ValueError as exc:
        return False, f"unparseable: {exc}"
    if not toks:
        return False, "empty"
    exe = Path(toks[0])
    if exe.name.lower() in ("python", "powershell", "pwsh", "cmd"):
        pass  # resolved via PATH
    elif not exe.is_file():
        return False, f"interpreter not found: {toks[0]}"
    for tok in toks[1:]:
        if tok.lower().endswith((".py", ".ps1")):
            if not Path(tok).is_file():
                return False, f"script not found: {tok}"
            break
    return True, "ok"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    hooks = data.get("hooks", {})

    changed = 0
    problems = []
    for event, groups in hooks.items():
        for gi, group in enumerate(groups):
            for hi, hook in enumerate(group.get("hooks", [])):
                old = hook.get("command", "")
                new = fix_command(old)
                ok, why = verify(new)
                label = f"{event}[{gi}][{hi}]"
                if new != old:
                    changed += 1
                    print(f"\n{label}")
                    print(f"  - {old}")
                    print(f"  + {new}")
                    print(f"    verify: {'PASS' if ok else 'FAIL - ' + why}")
                    if args.apply:
                        hook["command"] = new
                else:
                    print(f"\n{label}  (unchanged)  verify: {'PASS' if ok else 'FAIL - ' + why}")
                if not ok:
                    problems.append((label, why))

    print(f"\n{'=' * 60}\n{changed} command(s) rewritten.")
    if problems:
        print(f"⚠️  {len(problems)} hook(s) still fail verification:")
        for label, why in problems:
            print(f"   {label}: {why}")

    if not args.apply:
        print("\nDry run — nothing written. Re-run with --apply.")
        return 0

    backup = SETTINGS.with_suffix(f".json.bak-hooks-{datetime.now():%Y%m%d-%H%M%S}")
    shutil.copy2(SETTINGS, backup)
    SETTINGS.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nBacked up to: {backup}\nWrote: {SETTINGS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

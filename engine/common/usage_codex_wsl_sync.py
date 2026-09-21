# -*- coding: utf-8 -*-
"""
Mirror the WSL-side Codex rollout transcripts onto a Windows path (2026-09-20).

WHY THIS EXISTS
---------------
`codex mcp-server` — the binary Claude delegates to — runs under WSL, so every
MCP delegation's rollout lands in /home/<user>/.codex/sessions. Codex Desktop,
by contrast, writes to the Windows profile. The LLM Usage tab needs both or the
ChatGPT column is half blind, counting the sessions Renne drives himself and
dropping the ones Claude drove.

Reading the WSL files in place does not work:
  - `\\\\wsl.localhost\\<distro>\\...` is not enumerable from Python here, and
    `is_dir()` on a known-good path returns False (verified 2026-09-20);
  - QI_Dashboard runs as LocalSystem, which has no WSL session at all.
So we copy instead. The mirror lives on C:, where the service can always read
it, and `config/usage_assistants.json` registers it as an extra Codex root.

Rollout files are append-only, so the copy is incremental: a file is re-copied
only when its size changes. Nothing is ever deleted from the mirror — a
transcript that ages out of WSL keeps its history on the dashboard.

FRESHNESS (CLAUDE.md, "Unattended jobs lie")
--------------------------------------------
Every run writes `_sync_state.json` with a UTC timestamp and the counts.
`usage_assistants.available()` reports that timestamp so a silently-stopped
mirror shows up on the tab as a stale age, not as a quietly shrinking number.
Exit code is NOT the health signal — the state file is.

Usage:
    python C:\\QIH\\engine\\common\\usage_codex_wsl_sync.py [--distro Ubuntu-24.04] [--quiet]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

MIRROR_ROOT = Path(r"C:\QIH\data\codex_wsl\sessions")
STATE_FILE = Path(r"C:\QIH\data\codex_wsl\_sync_state.json")
DEFAULT_DISTRO = "Ubuntu-24.04"
DEFAULT_USER = "hyosuke"


def _wsl(distro: str, user: str, script: str, timeout: int = 120) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["wsl.exe", "-d", distro, "-u", user, "--", "bash", "-lc", script],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=timeout,
    )
    return proc.returncode, proc.stdout or "", proc.stderr or ""


# NO SHELL VARIABLES IN THESE SCRIPTS — deliberately.
#
# Two things are broken about `wsl.exe -d <d> -u <u> -- bash -lc "<script>"`,
# both found the hard way on 2026-09-20 and both of which fail SILENTLY:
#   1. $HOME is empty. WSL hands the shell the Windows environment and the
#      login shell does not repopulate it, so "$HOME/.codex" resolves to
#      "/.codex" and a -d guard reports "nothing here" with exit code 0.
#   2. Variable assignment does not survive the round trip. Measured:
#      `x="$(echo hi)"; echo "[$x]"` prints `[]`, while the inline form
#      `echo "[$(echo hi)]"` prints `[hi]`. Something between Python's argv,
#      wsl.exe's command-line parsing and bash eats the assignment.
# `~` is expanded by bash from /etc/passwd and ignores HOME entirely, so using
# it inline — with no variables anywhere — is the one form that works.
#
# Rollout paths are matched against _SAFE_REL before interpolation, so nothing
# from the filesystem can inject shell syntax here.
_SAFE_REL = re.compile(r"^[0-9]{4}/[0-9]{2}/[0-9]{2}/rollout-[A-Za-z0-9._:\-]+\.jsonl$")


def list_remote(distro: str, user: str) -> list[tuple[str, int]]:
    """[(path relative to sessions/, size), ...] for every rollout in WSL."""
    script = (
        'if [ ! -d ~/.codex/sessions ]; then echo NOROOT >&2; exit 3; fi; '
        'find ~/.codex/sessions -name "rollout-*.jsonl" -printf "%s\\t%P\\n"'
    )
    code, out, err = _wsl(distro, user, script)
    if code != 0:
        raise RuntimeError(f"wsl find failed ({code}): {err.strip()[:300] or 'no stderr'}")
    rows = []
    for line in out.splitlines():
        if "\t" not in line:
            continue
        size, rel = line.split("\t", 1)
        try:
            rows.append((rel.strip(), int(size)))
        except ValueError:
            continue
    return rows


def copy_one(distro: str, user: str, rel: str, dest: Path) -> bool:
    """Stream one file out of WSL. Written to a .part first so a killed sync
    can never leave a half-file that parses as a short transcript."""
    if not _SAFE_REL.match(rel):
        return False                      # refuse anything that isn't a plain rollout path
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    proc = subprocess.run(
        ["wsl.exe", "-d", distro, "-u", user, "--", "bash", "-lc",
         f"cat ~/.codex/sessions/{rel}"],
        capture_output=True, timeout=300,
    )
    if proc.returncode != 0:
        return False
    tmp.write_bytes(proc.stdout)
    tmp.replace(dest)
    return True


def sync(distro: str = DEFAULT_DISTRO, user: str = DEFAULT_USER,
         quiet: bool = False) -> dict:
    started = datetime.now(timezone.utc)
    result = {"started": started.isoformat(timespec="seconds"), "distro": distro,
              "user": user, "mirror": str(MIRROR_ROOT),
              "remote_files": 0, "copied": 0, "skipped": 0, "failed": 0, "error": None}
    try:
        remote = list_remote(distro, user)
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        _write_state(result)
        if not quiet:
            print(f"FAILED: {result['error']}", file=sys.stderr)
        return result

    result["remote_files"] = len(remote)
    for rel, size in remote:
        dest = MIRROR_ROOT / rel.replace("/", "\\")
        if dest.exists() and dest.stat().st_size == size:
            result["skipped"] += 1          # append-only: same size means same file
            continue
        if copy_one(distro, user, rel, dest):
            result["copied"] += 1
        else:
            result["failed"] += 1

    result["finished"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _write_state(result)
    if not quiet:
        print(json.dumps(result, indent=2))
    return result


def _write_state(result: dict) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")
    except OSError:
        pass


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description="Mirror WSL Codex rollouts to Windows")
    ap.add_argument("--distro", default=DEFAULT_DISTRO)
    ap.add_argument("--user", default=DEFAULT_USER)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    r = sync(args.distro, args.user, args.quiet)
    # Exit non-zero only on a hard failure. The state file is the health signal;
    # a scheduler's exit code is not (CLAUDE.md, "Unattended jobs lie").
    return 1 if r.get("error") else 0


if __name__ == "__main__":
    sys.exit(main())

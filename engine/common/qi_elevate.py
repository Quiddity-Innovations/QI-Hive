# -*- coding: utf-8 -*-
"""
QI Elevation Broker

Runs as LocalSystem via NSSM (service QI_Elevate). Watches
C:\\QIH\\commands\\pending\\ for JSON request files and executes
whitelisted commands with full admin rights. Writes results to
C:\\QIH\\commands\\completed\\.

This lets me (and any QI agent) trigger service restarts, process
kills, and service repointing unattended — no UAC prompt — because
the broker is already SYSTEM and a whitelist bounds what it will run.

Request format (pending/*.json):
    {
        "id": "req_20260419_abc",
        "cmd": "nssm",
        "args": ["restart", "QI_Dashboard"],
        "timestamp": "2026-04-19T17:00:00",
        "submitted_by": "claude"
    }

Response format (completed/<id>.json):
    {
        "id": "req_20260419_abc",
        "status": "ok" | "error" | "denied",
        "returncode": 0,
        "stdout": "...",
        "stderr": "...",
        "rule_matched": "nssm_service_control",
        "error": null | "reason",
        "completed_at": "2026-04-19T17:00:02"
    }

Security model: ONLY commands whose cmd + args match a whitelist rule
run. Regex-bounded, no shell, no expansion. Unknown commands logged
and denied.
"""
from __future__ import annotations
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_DIR = Path(r"C:\QIH")
CMD_DIR     = PROJECT_DIR / "commands"
PENDING_DIR = CMD_DIR / "pending"
COMPLETED_DIR = CMD_DIR / "completed"
ARCHIVE_DIR = CMD_DIR / "archive"
WHITELIST   = CMD_DIR / "whitelist.json"
LOG_DIR     = PROJECT_DIR / "logs" / "elevation"
LOG_FILE    = LOG_DIR / "broker.log"

for d in [PENDING_DIR, COMPLETED_DIR, ARCHIVE_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Logging ────────────────────────────────────────────────────────────────
log = logging.getLogger("qi.elevation_broker")
log.setLevel(logging.INFO)
fh = RotatingFileHandler(str(LOG_FILE), maxBytes=5_242_880, backupCount=5, encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s"))
log.addHandler(fh)
ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s"))
log.addHandler(ch)

# ── Command resolution ────────────────────────────────────────────────────
COMMAND_RESOLVERS = {
    "nssm":     r"C:\QIH\engine\bin\nssm.exe",
    "taskkill": r"C:\Windows\System32\taskkill.exe",
    "sc":       r"C:\Windows\System32\sc.exe",
    "gsudo":    r"C:\Program Files\gsudo\Current\gsudo.exe",
}


def resolve_command(cmd: str) -> str | None:
    """Return full path to the binary for a logical command name."""
    return COMMAND_RESOLVERS.get(cmd)


# ── Whitelist ─────────────────────────────────────────────────────────────
def load_whitelist() -> list[dict]:
    if not WHITELIST.exists():
        log.error(f"whitelist missing: {WHITELIST}")
        return []
    try:
        data = json.loads(WHITELIST.read_text(encoding="utf-8"))
        return data.get("rules", [])
    except Exception as e:
        log.error(f"whitelist parse error: {e}")
        return []


def check_whitelist(cmd: str, args: list[str], rules: list[dict]) -> tuple[bool, str | None, str | None]:
    """
    Return (allowed, rule_name, reason).
    rule_name set only when allowed.
    reason set only when denied.
    """
    matching_rules = [r for r in rules if r.get("cmd") == cmd]
    if not matching_rules:
        return (False, None, f"no whitelist rule for cmd '{cmd}'")

    for rule in matching_rules:
        lo = rule.get("arg_count_min", 0)
        hi = rule.get("arg_count_max", 99)
        if not (lo <= len(args) <= hi):
            continue
        patterns = rule.get("args_regex", [])
        if len(patterns) != len(args):
            continue
        if all(re.fullmatch(p, a) for p, a in zip(patterns, args)):
            return (True, rule.get("name", "unnamed"), None)

    return (False, None, f"no rule matched for cmd='{cmd}' args={args}")


# ── Request processing ───────────────────────────────────────────────────
def process_request(req_path: Path, rules: list[dict]) -> None:
    try:
        req = json.loads(req_path.read_text(encoding="utf-8"))
    except Exception as e:
        log.error(f"{req_path.name}: cannot parse JSON: {e}")
        _write_error(req_path, None, "error", f"invalid JSON: {e}")
        return

    rid = req.get("id") or req_path.stem
    cmd = req.get("cmd")
    args = req.get("args", [])
    submitted_by = req.get("submitted_by", "?")

    if not isinstance(cmd, str) or not isinstance(args, list) or not all(isinstance(a, str) for a in args):
        _write_error(req_path, rid, "error", "cmd must be str, args must be list[str]")
        return

    log.info(f"[{rid}] from={submitted_by} cmd={cmd} args={args}")

    allowed, rule_name, reason = check_whitelist(cmd, args, rules)
    if not allowed:
        log.warning(f"[{rid}] DENIED: {reason}")
        _write_result(req_path, {
            "id": rid, "status": "denied", "returncode": None,
            "stdout": "", "stderr": "", "rule_matched": None,
            "error": reason,
            "completed_at": datetime.now().isoformat(),
        })
        return

    binary = resolve_command(cmd)
    if not binary:
        _write_error(req_path, rid, "error", f"cmd '{cmd}' has no resolver")
        return

    try:
        proc = subprocess.run(
            [binary, *args],
            capture_output=True, text=True, timeout=60, shell=False,
        )
        status = "ok" if proc.returncode == 0 else "error"
        log.info(f"[{rid}] {status} rc={proc.returncode} rule={rule_name}")
        _write_result(req_path, {
            "id": rid, "status": status, "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "rule_matched": rule_name, "error": None,
            "completed_at": datetime.now().isoformat(),
        })
    except subprocess.TimeoutExpired:
        log.error(f"[{rid}] TIMEOUT")
        _write_error(req_path, rid, "error", "timeout after 60s")
    except Exception as e:
        log.error(f"[{rid}] EXCEPTION: {e}")
        _write_error(req_path, rid, "error", str(e))


def _write_result(req_path: Path, result: dict) -> None:
    out_path = COMPLETED_DIR / f"{result['id']}.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    # Archive request
    shutil.move(str(req_path), str(ARCHIVE_DIR / req_path.name))


def _write_error(req_path: Path, rid: str | None, status: str, error: str) -> None:
    _write_result(req_path, {
        "id": rid or req_path.stem, "status": status, "returncode": None,
        "stdout": "", "stderr": "", "rule_matched": None,
        "error": error, "completed_at": datetime.now().isoformat(),
    })


# ── Single-instance lock ─────────────────────────────────────────────────
LOCK_FILE = LOG_DIR / "broker.lock"

def _acquire_lock() -> bool:
    """Write our PID to lock file. If another broker is alive, refuse to start.
    Prevents the orphan-broker scenario where two processes polled the same
    queue and answered requests with inconsistent state (caught 2026-04-19)."""
    if LOCK_FILE.exists():
        try:
            other_pid = int(LOCK_FILE.read_text().strip())
            if other_pid != os.getpid():
                # Check if the other process is still alive
                try:
                    os.kill(other_pid, 0)  # signal 0 = liveness check
                    log.error(f"Another broker is already running (PID {other_pid}). Refusing to start.")
                    return False
                except OSError:
                    log.warning(f"Stale lock from PID {other_pid}; taking over.")
        except Exception:
            pass  # unreadable lock — overwrite
    try:
        LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
        return True
    except Exception as e:
        log.error(f"Cannot write lock file: {e}")
        return False


def _release_lock() -> None:
    try:
        if LOCK_FILE.exists() and LOCK_FILE.read_text().strip() == str(os.getpid()):
            LOCK_FILE.unlink()
    except Exception:
        pass


# ── Main loop ─────────────────────────────────────────────────────────────
def main() -> None:
    log.info("QI Elevation Broker starting")
    log.info(f"pending dir: {PENDING_DIR}")
    log.info(f"whitelist:   {WHITELIST}")
    log.info(f"pid: {os.getpid()}")

    if not _acquire_lock():
        sys.exit(2)

    # Purge stale pending requests left over from a previous broker life.
    # Without this, an old `sc stop QI_Elevate` request sitting in the queue
    # will execute the instant this broker starts — killing itself (caught
    # 2026-04-19 20:51). Anything older than 5 minutes at startup is stale.
    STALE_AGE_SEC = 300
    now = time.time()
    purged = 0
    for req in PENDING_DIR.glob("*.json"):
        try:
            if (now - req.stat().st_mtime) > STALE_AGE_SEC:
                stale_out = COMPLETED_DIR / f"{req.stem}.json"
                stale_out.write_text(json.dumps({
                    "id": req.stem, "status": "denied", "returncode": None,
                    "stdout": "", "stderr": "", "rule_matched": None,
                    "error": f"stale: request older than {STALE_AGE_SEC}s at broker startup",
                    "completed_at": datetime.now().isoformat(),
                }, indent=2), encoding="utf-8")
                shutil.move(str(req), str(ARCHIVE_DIR / req.name))
                purged += 1
        except Exception as e:
            log.warning(f"could not purge stale {req.name}: {e}")
    if purged:
        log.info(f"purged {purged} stale request(s) from pending queue")

    rules = load_whitelist()
    log.info(f"loaded {len(rules)} whitelist rules")
    last_whitelist_mtime = WHITELIST.stat().st_mtime if WHITELIST.exists() else 0

    while True:
        try:
            # Hot-reload whitelist if changed
            if WHITELIST.exists():
                mtime = WHITELIST.stat().st_mtime
                if mtime != last_whitelist_mtime:
                    rules = load_whitelist()
                    last_whitelist_mtime = mtime
                    log.info(f"whitelist reloaded ({len(rules)} rules)")

            # Process pending requests (oldest first)
            requests = sorted(PENDING_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)
            for req in requests:
                process_request(req, rules)

            time.sleep(1)
        except KeyboardInterrupt:
            log.info("shutting down")
            _release_lock()
            break
        except Exception as e:
            log.exception(f"main loop error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""brain_backfill_tick.py — runs the scan+backfill pair as a single safety-net
tick. Designed to be called by Windows Task Scheduler every 30 minutes.

Scans Claude Code transcripts modified in the last 48h. For any session whose
content cannot be matched (within 12h) to any session_log row in qi_brain.db,
emits a backfill stub to the HiveIngest inbox. HiveIngest then writes it to
session_log on its next pass.

This is the BACKSTOP for SessionEnd hook reliability. If the hook fires, the
backfill scanner sees the existing session_log entry and skips it. If the
hook fails (terminal close, sleep, Ctrl+C), the backfill picks it up within
~30 minutes.
"""
from __future__ import annotations
import subprocess, sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

TOOLS = Path(r"C:\QIH\tools")
INBOX = Path(r"C:\QIH\shared\reports\inbox")
LOGS  = Path(r"C:\QIH\logs")
LOGS.mkdir(parents=True, exist_ok=True)

PYTHON = r"C:\1-AI\APPS\PYTHON\python.exe"


def main():
    since = (datetime.now() - timedelta(hours=48)).strftime("%Y-%m-%d")
    log_path = LOGS / "brain_backfill_tick.log"
    manifest = INBOX.parent / "manifests" / f"backfill_candidates_tick.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("a", encoding="utf-8") as logf:
        def w(msg):
            line = f"{datetime.now().isoformat(timespec='seconds')} {msg}"
            print(line)
            logf.write(line + "\n")
            logf.flush()

        w(f"=== tick start (since={since}) ===")

        # Step 1: scan
        try:
            r = subprocess.run(
                [PYTHON, str(TOOLS / "scan_unlogged_sessions.py"),
                 "--since", since, "--output", str(manifest)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=120,
            )
            w(f"scan rc={r.returncode}")
            tail = (r.stdout or "").splitlines()[-3:]
            for t in tail:
                w(f"  scan> {t}")
            if r.returncode != 0:
                w(f"scan stderr: {(r.stderr or '')[:500]}")
                return
        except Exception as e:
            w(f"scan FAILED: {type(e).__name__}: {e}")
            return

        # Step 2: backfill
        try:
            r = subprocess.run(
                [PYTHON, str(TOOLS / "backfill_unlogged_sessions.py"),
                 "--candidates", str(manifest)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=120,
            )
            w(f"backfill rc={r.returncode}")
            tail = (r.stdout or "").splitlines()[-6:]
            for t in tail:
                w(f"  backfill> {t}")
            if r.returncode != 0:
                w(f"backfill stderr: {(r.stderr or '')[:500]}")
        except Exception as e:
            w(f"backfill FAILED: {type(e).__name__}: {e}")

        # Step 3: dedupe — until the scanner-matcher is bulletproof, run dedupe
        # after every tick so duplicate backfill rows can't accumulate. The
        # dedupe collapses by TRANSCRIPT marker and is idempotent (no-op when
        # the matcher is doing its job correctly).
        # Wait a few seconds for HiveIngest to drain newly-written stubs first.
        import time as _t
        _t.sleep(8)
        try:
            r = subprocess.run(
                [PYTHON, str(TOOLS / "dedupe_backfill_rows.py")],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=60,
            )
            w(f"dedupe rc={r.returncode}")
            for t in (r.stdout or "").splitlines()[-3:]:
                w(f"  dedupe> {t}")
        except Exception as e:
            w(f"dedupe FAILED: {type(e).__name__}: {e}")

        w("=== tick end ===\n")


if __name__ == "__main__":
    main()

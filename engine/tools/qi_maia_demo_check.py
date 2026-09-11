# -*- coding: utf-8 -*-
"""QI Maia Demo Readiness Check.

Maia is not under active development — it exists to be demoable on demand.
So the health question is NOT "did anyone commit recently" (the old
MaiaNightlySync `check: git` entry, which went permanently STALE on
2026-08-27 because a dormant repo has nothing to commit). The health
question is "if Renne opened a demo right now, would it work?"

This probes the whole demo chain end to end:

    browser -> Cloudflare named tunnel (qi-maia)
            -> QI Gate / Caddy :9040
            -> Maia API :8001  +  Gradio UI :7860

Usage:
  python C:\\QIH\\engine\\tools\\qi_maia_demo_check.py
  python C:\\QIH\\engine\\tools\\qi_maia_demo_check.py --json

Exit code: 0 = demo ready · 1 = something in the chain is down · 2 = could not run.

The marker 'demo=READY' is written to the dated log ONLY when every check
passes. A WARN or FAIL omits it on purpose, so QI_TaskHealth's marker check
goes STALE and the alert fires. Same contract as QI_TrinityCheck_Daily.

Do NOT wrap this in `conhost --headless` and trust the exit code — conhost
always returns 0. The marker in the dated log is the outcome signal.
"""

import argparse
import json
import os
import socket
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"

REPORT_DIR = Path(r"C:\QIH\data\maia_demo")
DAILY_DIR = Path(r"C:\QIH\LOGS\maia_demo")
LOG_FILE = Path(r"C:\QIH\LOGS\maia_demo_check.log")
MAIA_DB = Path(r"C:\APPS\QI\maia.db")
MAIA_REPO = Path(r"C:\APPS\QI")
SYNC_LOG = Path(r"C:\APPS\QI\LOGS\nightly_sync.log")

MARKER = "demo=READY"
TIMEOUT = 15

# NSSM services that must be Running for a demo. QI_MaiaDemoTunnel is
# deliberately absent: it is a legacy *quick* tunnel (--url http://localhost:7860,
# random trycloudflare hostname) superseded by the named tunnel qi-maia, which
# already serves maia-demo.quiddityinnovations.com. It is Stopped+Disabled on
# purpose — do not add it here, it would produce a permanent false alarm.
SERVICES = [
    ("QI_MaiaBot", "Maia FastAPI backend (:8001)"),
    ("QI_MaiaGradio", "Gradio demo UI (:7860)"),
    ("QI_MaiaTunnel", "Cloudflare named tunnel qi-maia"),
    ("QI_MaiaQueueDrain", "AWS relay queue drain (LINE inbound)"),
]

LOCAL_ENDPOINTS = [
    ("Maia API health", "http://localhost:8001/health", '"status":"ok"'),
    ("Gradio demo UI", "http://localhost:7860/", "<!doctype html"),
]

# The real end-to-end test: the public hostnames a demo audience would open.
# Both route through the named tunnel to QI Gate :9040.
PUBLIC_ENDPOINTS = [
    ("Public maia-demo", "https://maia-demo.quiddityinnovations.com/"),
    ("Public maia", "https://maia.quiddityinnovations.com/"),
]


class Checks:
    def __init__(self):
        self.rows = []

    def add(self, area, check, status, detail=""):
        self.rows.append({"area": area, "check": check, "status": status, "detail": detail})

    # ── NSSM services ────────────────────────────────────────────
    def check_services(self):
        try:
            out = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command",
                 "Get-Service -Name 'QI_Maia*' -ErrorAction SilentlyContinue | "
                 "ConvertTo-Json -Compress"],
                capture_output=True, text=True, timeout=60,
            ).stdout.strip()
            data = json.loads(out) if out else []
            if isinstance(data, dict):
                data = [data]
            state = {d.get("Name"): d.get("Status") for d in data}
        except Exception as e:
            self.add("service", "enumerate QI_Maia* services", FAIL, str(e)[:160])
            return

        # Status may come back as an int (ServiceControllerStatus) or a string.
        def running(v):
            return str(v) in ("4", "Running")

        for name, desc in SERVICES:
            if name not in state:
                self.add("service", name, FAIL, "service not installed — %s" % desc)
            elif running(state[name]):
                self.add("service", name, PASS, desc)
            else:
                self.add("service", name, FAIL, "%s (state=%s)" % (desc, state[name]))

    # ── HTTP probes ──────────────────────────────────────────────
    def _get(self, url):
        req = urllib.request.Request(url, headers={"User-Agent": "qi-maia-demo-check"})
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as r:
            return r.status, r.read(400).decode("utf-8", "replace")

    def check_local(self):
        for label, url, expect in LOCAL_ENDPOINTS:
            try:
                status, body = self._get(url)
                ok = status == 200 and expect.lower() in body.lower()
                self.add("local", label, PASS if ok else FAIL,
                         "HTTP %s%s" % (status, "" if ok else " — missing %r" % expect))
            except Exception as e:
                self.add("local", label, FAIL, "%s: %s" % (type(e).__name__, str(e)[:120]))

    def check_public(self):
        for label, url in PUBLIC_ENDPOINTS:
            try:
                status, _ = self._get(url)
                # Any 2xx/3xx means the tunnel + gate answered. The gate may
                # serve a login wall — that is a healthy demo surface.
                ok = 200 <= status < 400
                self.add("public", label, PASS if ok else FAIL, "HTTP %s" % status)
            except urllib.error.HTTPError as e:
                # 401/403 = gate is up and challenging. Still demo-ready.
                ok = e.code in (401, 403)
                self.add("public", label, PASS if ok else FAIL,
                         "HTTP %s (%s)" % (e.code, "auth wall — edge healthy" if ok else e.reason))
            except Exception as e:
                self.add("public", label, FAIL, "%s: %s" % (type(e).__name__, str(e)[:120]))

    # ── data ─────────────────────────────────────────────────────
    def check_db(self):
        if MAIA_DB.exists():
            mb = MAIA_DB.stat().st_size / 1048576.0
            self.add("data", "maia.db present", PASS, "%.1f MB" % mb)
        else:
            self.add("data", "maia.db present", FAIL, "missing: %s" % MAIA_DB)

    # ── work-at-risk guard ───────────────────────────────────────
    def check_backup(self):
        """Detect work the nightly sync is failing to capture.

        This preserves the protection the old `check: git` entry was added for:
        MaiaNightlySync once logged 'Nothing staged - skipping commit' and exited
        0 while 86 files sat unbacked for ~2 months.

        But it does NOT assert commit recency, which is what made that entry go
        permanently STALE once development paused. A clean tree is the healthy
        state for a dormant project.

        The precise failure being detected: files that were modified BEFORE the
        last sync run are still uncommitted AFTER it. That means the sync ran and
        skipped real work. Files edited since the last run are simply pending
        tonight's run and are not an error.
        """
        if not MAIA_REPO.exists():
            self.add("backup", "Maia repo present", FAIL, "missing: %s" % MAIA_REPO)
            return
        try:
            out = subprocess.run(["git", "-C", str(MAIA_REPO), "status", "--porcelain"],
                                 capture_output=True, text=True, timeout=60).stdout
        except Exception as e:
            self.add("backup", "work captured by nightly sync", FAIL, str(e)[:140])
            return

        dirty = [l[3:].strip().strip('"') for l in out.splitlines() if l.strip()]
        if not dirty:
            self.add("backup", "work captured by nightly sync", PASS,
                     "working tree clean — nothing at risk")
            return

        if not SYNC_LOG.exists():
            self.add("backup", "work captured by nightly sync", FAIL,
                     "%d uncommitted file(s) and no sync log at %s" % (len(dirty), SYNC_LOG))
            return

        last_sync = SYNC_LOG.stat().st_mtime
        stranded = []
        for rel in dirty:
            p = MAIA_REPO / rel
            try:
                if p.is_file() and p.stat().st_mtime < last_sync:
                    stranded.append(rel)
            except OSError:
                continue

        when = datetime.fromtimestamp(last_sync).strftime("%Y-%m-%d %H:%M")
        if stranded:
            self.add("backup", "work captured by nightly sync", FAIL,
                     "%d file(s) modified before the %s sync are STILL uncommitted — "
                     "sync is skipping real work: %s"
                     % (len(stranded), when, ", ".join(stranded[:4])))
        else:
            self.add("backup", "work captured by nightly sync", PASS,
                     "%d file(s) edited since the %s sync — pending tonight's run"
                     % (len(dirty), when))


def main():
    ap = argparse.ArgumentParser(description="Maia demo readiness check")
    ap.add_argument("--json", action="store_true", help="print JSON report to stdout")
    a = ap.parse_args()

    socket.setdefaulttimeout(TIMEOUT)
    c = Checks()
    c.check_services()
    c.check_local()
    c.check_public()
    c.check_db()
    c.check_backup()

    worst = (FAIL if any(r["status"] == FAIL for r in c.rows)
             else WARN if any(r["status"] == WARN for r in c.rows) else PASS)
    ts = datetime.now()
    report = {"ts": ts.isoformat(timespec="seconds"), "overall": worst, "checks": c.rows}

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    rp = REPORT_DIR / ("check_%s.json" % ts.strftime("%Y-%m-%d_%H%M"))
    rp.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")

    n_pass = sum(r["status"] == PASS for r in c.rows)
    n_fail = sum(r["status"] == FAIL for r in c.rows)
    # The marker is written ONLY on a clean sweep. Omitting it is how the
    # QI_TaskHealth alert fires.
    line = "%s overall=%s %s pass=%d fail=%d report=%s\n" % (
        ts.isoformat(timespec="seconds"), worst,
        MARKER if worst == PASS else "demo=NOT-READY",
        n_pass, n_fail, rp.name)

    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line)
    # Per-day file: a rolling log would let yesterday's READY satisfy today's
    # check. This bit us on QI_TrinityCheck_Daily 2026-09-08 — do not "simplify".
    with (DAILY_DIR / ("maia_demo_check_%s.log" % ts.strftime("%Y%m%d"))).open("a", encoding="utf-8") as f:
        f.write(line)

    if a.json:
        print(json.dumps(report, indent=1, ensure_ascii=False))
    else:
        icon = {PASS: "OK  ", WARN: "WARN", FAIL: "FAIL"}
        print("Maia Demo Readiness — %s — overall %s" % (report["ts"], worst))
        w = max(len(r["check"]) for r in c.rows)
        for r in c.rows:
            print("  %s [%-7s] %-*s  %s" % (icon[r["status"]], r["area"], w, r["check"], r["detail"]))
        print("report: %s" % rp)

    sys.exit(0 if worst != FAIL else 1)


if __name__ == "__main__":
    main()

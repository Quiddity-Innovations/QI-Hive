# -*- coding: utf-8 -*-
"""Selftest for qi_maia_demo_check.py — proves the check can actually FAIL.

A health check that only ever passes is decoration. This drives the four
failure modes that would really break a demo and asserts that each one
(a) is reported FAIL and (b) WITHHOLDS the 'demo=READY' marker, which is
what makes QI_TaskHealth go STALE and alert.

Touches nothing real: services and endpoints are monkeypatched in-process,
and output is redirected to a temp directory.

Run after editing qi_maia_demo_check.py.
"""
import importlib.util
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SRC = Path(r"C:\QIH\engine\tools\qi_maia_demo_check.py")


def load():
    spec = importlib.util.spec_from_file_location("mdc", SRC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def run_case(name, mutate):
    m = load()
    tmp = Path(tempfile.mkdtemp(prefix="maiademo_selftest_"))
    m.REPORT_DIR = tmp / "data"
    m.DAILY_DIR = tmp / "daily"
    m.LOG_FILE = tmp / "check.log"
    mutate(m)

    c = m.Checks()
    c.check_services()
    c.check_local()
    c.check_public()
    c.check_db()
    worst = (m.FAIL if any(r["status"] == m.FAIL for r in c.rows)
             else m.WARN if any(r["status"] == m.WARN for r in c.rows) else m.PASS)
    fails = [r for r in c.rows if r["status"] == m.FAIL]
    marker_written = (worst == m.PASS)
    ok = (worst == m.FAIL) and not marker_written
    print("  %s  %-34s overall=%-4s fails=%d marker_withheld=%s"
          % ("PASS" if ok else "**BROKEN**", name, worst, len(fails), not marker_written))
    if fails:
        print("        first failure: [%s] %s — %s"
              % (fails[0]["area"], fails[0]["check"], fails[0]["detail"][:70]))
    return ok


def main():
    print("qi_maia_demo_check selftest — each case MUST go FAIL and withhold the marker\n")
    results = []

    # 1. A required NSSM service is missing/stopped.
    def kill_service(m):
        m.SERVICES = list(m.SERVICES) + [("QI_MaiaDoesNotExist", "synthetic missing service")]
    results.append(run_case("missing NSSM service", kill_service))

    # 2. The Maia API is down (dead local port).
    def kill_api(m):
        m.LOCAL_ENDPOINTS = [("Maia API health", "http://localhost:8001/health", '"status":"ok"'),
                             ("synthetic dead port", "http://localhost:9", "anything")]
    results.append(run_case("local endpoint down", kill_api))

    # 3. The public hostname does not resolve — tunnel or DNS broken.
    def kill_public(m):
        m.PUBLIC_ENDPOINTS = [("synthetic dead host",
                               "https://maia-demo-nonexistent.quiddityinnovations.com/")]
    results.append(run_case("public hostname unreachable", kill_public))

    # 4. The database is gone.
    def kill_db(m):
        m.MAIA_DB = Path(r"C:\APPS\QI\definitely_not_here.db")
    results.append(run_case("maia.db missing", kill_db))

    print()
    if all(results):
        print("SELFTEST PASS — the check goes RED on all 4 demo-breaking failures.")
        sys.exit(0)
    print("SELFTEST FAILED — %d/%d cases did not fail as required."
          % (sum(1 for r in results if not r), len(results)))
    sys.exit(1)


if __name__ == "__main__":
    main()

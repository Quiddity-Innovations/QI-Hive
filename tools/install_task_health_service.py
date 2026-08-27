# -*- coding: utf-8 -*-
"""
Install QI_TaskHealth as an NSSM service via the QI Elevation Broker.

Follows the QI service conventions: QI_ prefix, no spaces, explicit Description,
explicit AppDirectory, stdout/stderr redirected to the project's own log dir.

Deliberately its OWN service rather than a scheduled task:
  * a scheduled task would inherit the exact conhost exit-code blindness this
    monitor exists to compensate for;
  * and it must stay independent of everything it watches — a checker that
    lives inside the thing being checked dies with it, which is how Kaze went
    dark for 18 days and TubeScout for 66.

python.exe (NOT pythonw.exe) on purpose: pythonw sets sys.stdout = None and any
print() then exits 1 — a documented QI gotcha. NSSM redirects stdout to a file
and services run in session 0, so there is no console window either way.
"""
import sys

sys.path.insert(0, r"C:\QIH")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from engine.common.qi_elevate_client import run_elevated  # noqa: E402

SVC = "QI_TaskHealth"
PY = r"C:\Program Files\Python311\python.exe"
SCRIPT = r"C:\QIH\tools\qi_task_health.py"
APPDIR = r"C:\QIH"
OUT = r"C:\QIH\logs\qi_task_health.service.log"
ERR = r"C:\QIH\logs\qi_task_health.service.err.log"
DESC = ("QI-wide scheduled-task freshness monitor. Verifies every QI/OC/Maia "
        "task by its OUTPUT ARTIFACT, because conhost --headless makes "
        "LastTaskResult always 0 and a growing wrapper log does not prove "
        "success. Manifest: C:\\QIH\\ecosystem\\task_health_manifest.json")

STEPS = [
    ("install",        [SVC, PY, SCRIPT, "--daemon"]),
    ("set",            [SVC, "AppDirectory", APPDIR]),
    ("set",            [SVC, "Description", DESC]),
    ("set",            [SVC, "AppStdout", OUT]),
    ("set",            [SVC, "AppStderr", ERR]),
    ("set",            [SVC, "AppRotateFiles", "1"]),
    ("set",            [SVC, "AppRotateBytes", "10485760"]),
    ("set",            [SVC, "Start", "SERVICE_AUTO_START"]),
    ("set",            [SVC, "AppExit", "Default", "Restart"]),
    ("set",            [SVC, "AppRestartDelay", "30000"]),
    ("start",          [SVC]),
]


def main():
    for verb, args in STEPS:
        full = [verb] + args
        label = "nssm %s %s" % (verb, " ".join(args[:2]))
        try:
            r = run_elevated("nssm", full, submitted_by="task_health_install",
                             timeout=60.0)
        except Exception as e:
            print("FAILED  %-42s :: %s" % (label, e))
            return 1
        status = r.get("status", "?")
        out = (r.get("stdout") or "").strip().replace("\x00", "")
        err = (r.get("stderr") or "").strip().replace("\x00", "")
        print("%-7s %-42s %s" % (status, label, (out or err)[:90]))
        if status not in ("ok", "success", "completed") and verb == "install":
            # already-installed is fine; anything else on install is fatal
            if "already exists" not in (out + err).lower():
                print("  -> aborting: install did not succeed")
                return 1
    print("\nDone. Verify with:  nssm status %s" % SVC)
    return 0


if __name__ == "__main__":
    sys.exit(main())

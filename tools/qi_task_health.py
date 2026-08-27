# -*- coding: utf-8 -*-
"""
qi_task_health.py — QI-wide scheduled-task freshness monitor.

WHY THIS EXISTS
===============
On 2026-08-27 an estate-wide audit found SEVEN QI scheduled tasks silently dead
while Task Scheduler reported success for every one of them:

  * QI_TubeScout_AM/PM  — dead 66 days on an expired OAuth token, logging
                          "cycle done" twice a day the entire time.
  * OC-Yubin x2, OC-Asa — dead 18 days after a path move.
  * OC-Sentry, OC-Kakei — never worked at ALL since the day they were created.

Two signals failed, and this tool exists because BOTH of them failed:

  1. `LastTaskResult`. 24 of 37 QI tasks are wrapped in `conhost.exe --headless`,
     which returns exit code 0 even when the target binary does not exist.

  2. Log mtime — the fix that was already written down in the registry, and was
     itself wrong. Task actions redirect with `>> log 2>&1`, so the shell's own
     failure messages land in the very log meant to prove success. During the
     18-day OC outage, Kaze's wrapper log froze (mtime would have caught it) but
     Yubin's grew EVERY SINGLE DAY with "No such file or directory" while the
     job was stone dead (mtime would have passed it).

So: a growing log is not evidence of a successful run. Only a success MARKER or
an advancing OUTPUT ARTIFACT is.

DESIGN NOTE — why this is central, not per-task
-----------------------------------------------
A per-task health check ships inside the thing it is checking, so when the task
dies the check dies with it. A dead task cannot report itself dead. That is
precisely how Kaze stayed dark 18 days and TubeScout 66. This runs as its own
always-on service (QI_TaskHealth), independent of everything it watches.

It also alerts on ABSENCE rather than on error, because every single failure the
audit found was an absence — nothing threw, nothing was logged as broken.

USAGE
-----
    python qi_task_health.py --once            # one report to stdout, exit 1 if anything stale
    python qi_task_health.py --once --json     # machine-readable
    python qi_task_health.py --daemon          # service mode: loop + Telegram alerts
    python qi_task_health.py --once --notify   # one pass, alert if stale

Manifest: C:\\QIH\\ecosystem\\task_health_manifest.json
Status out: C:\\QIH\\data\\task_health.json  (for Mission Control / dashboards)
"""
import argparse
import glob as globmod
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MANIFEST = r"C:\QIH\ecosystem\task_health_manifest.json"
STATUS_OUT = r"C:\QIH\data\task_health.json"
LOG_FILE = r"C:\QIH\logs\qi_task_health.log"
TG_ENV = r"C:\QIH\config\warroom_telegram.env"
STATE_FILE = r"C:\QIH\data\task_health_alert_state.json"

POLL_MINUTES = 30


# ─────────────────────────────────────────────────────────────
# plumbing
# ─────────────────────────────────────────────────────────────
def log(msg):
    line = "%s  %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    # flush=True matters once this runs under NSSM: Python block-buffers stdout
    # when it is not a terminal, so the service's captured log would lag minutes
    # to hours behind reality. A monitor whose own log is stale is worse than
    # useless - it is the exact thing it exists to detect.
    print(line, flush=True)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass  # logging must never take the monitor down


def load_env(path):
    out = {}
    try:
        for ln in open(path, encoding="utf-8"):
            ln = ln.strip()
            if "=" in ln and not ln.startswith("#"):
                k, v = ln.split("=", 1)
                out[k.strip()] = v.strip()
    except Exception:
        pass
    return out


def tg_send(text):
    """Best-effort Telegram alert. Never raises — a broken notifier must not
    stop the monitor, but it IS logged, because a silent notifier is exactly
    the failure mode this whole tool exists to prevent."""
    env = load_env(TG_ENV)
    token = env.get("WARROOM_TG_BOT_TOKEN")
    chat = env.get("WARROOM_TG_RENNE_CHAT_ID")
    if not token or not chat:
        log("WARN: telegram creds unavailable (%s) — alert NOT delivered" % TG_ENV)
        return False
    try:
        import urllib.parse
        import urllib.request
        data = urllib.parse.urlencode(
            {"chat_id": chat, "text": text, "parse_mode": "HTML"}
        ).encode()
        req = urllib.request.Request(
            "https://api.telegram.org/bot%s/sendMessage" % token, data=data
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read().decode("utf-8", "replace")
        if '"ok":true' in body:
            return True
        log("WARN: telegram rejected the alert: %s" % body[:200])
        return False
    except Exception as e:
        log("WARN: telegram send failed: %s" % e)
        return False


def now():
    return datetime.now()


def to_dt(val):
    """Parse the many timestamp shapes the estate uses. Returns naive local."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return datetime.fromtimestamp(val)
    s = str(val).strip()
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d",
                "%Y%m%d-%H%M%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(s[:len(fmt) + 4], fmt)
        except Exception:
            continue
    m = re.search(r"(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})", s)
    if m:
        try:
            return datetime.fromisoformat(m.group(1).replace(" ", "T"))
        except Exception:
            return None
    return None


def expand_target(target):
    """Resolve {date:FMT} placeholders against today."""
    def sub(m):
        return now().strftime(m.group(1))
    return re.sub(r"\{date:([^}]+)\}", sub, target)


# ─────────────────────────────────────────────────────────────
# the four check types, strongest first
# ─────────────────────────────────────────────────────────────
def check_sqlite(spec):
    db = spec["target"]
    if not os.path.exists(db):
        return None, "db missing: %s" % db
    try:
        con = sqlite3.connect("file:" + db.replace("\\", "/") + "?mode=ro", uri=True)
        try:
            row = con.execute(spec["query"]).fetchone()
        finally:
            con.close()
    except Exception as e:
        return None, "query failed: %s" % e
    if not row or row[0] is None:
        return None, "query returned no rows"
    dt = to_dt(row[0])
    return dt, ("row timestamp %s" % row[0]) if dt else ("unparseable timestamp: %r" % (row[0],))


def check_marker(spec):
    """The marker must be present AND fresh.

    Subtle but load-bearing: several of these logs are append-only across days
    (asa-task.log, kakei-task.log). A marker from three weeks ago still sits in
    the file, so merely finding the string would report a long-dead task as
    healthy. We therefore date the marker — either from the filename (the
    {date:...} form) or from the file's own mtime — and let the caller compare
    that against max_age_hours.
    """
    marker = spec["marker"]

    if spec.get("glob"):
        # Newest dated log wins. This is the right shape for WEEKLY tasks
        # (Kakei, Sentry): a {date:} template would look for today's file, which
        # does not exist on the six days a week the task does not run, and would
        # report a perfectly healthy weekly task as DEAD.
        matches = globmod.glob(os.path.join(spec["target"], spec["glob"]))
        if not matches:
            return None, "no log matching %s" % spec["glob"]
        path = max(matches, key=os.path.getmtime)
        stamp = datetime.fromtimestamp(os.path.getmtime(path))
        label = "newest %s" % os.path.basename(path)
    else:
        path = expand_target(spec["target"])
        if not os.path.exists(path):
            return None, "no log for today: %s" % os.path.basename(path)
        if "{date:" in spec["target"]:
            # filename carries today's date, so the marker's presence IS today's success
            stamp = now()
            label = "marker present in today's log"
        else:
            # append-only log shared across days — the marker alone proves
            # nothing (a success line from three weeks ago still sits in the
            # file), so freshness has to come from the file itself
            stamp = datetime.fromtimestamp(os.path.getmtime(path))
            label = "marker present, log mtime used"

    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception as e:
        return None, "unreadable: %s" % e
    if marker not in text:
        return None, "log exists but never reached '%s'" % marker
    return stamp, label


def check_git(spec):
    repo = spec["target"]
    if not os.path.isdir(os.path.join(repo, ".git")):
        return None, "not a git repo: %s" % repo
    try:
        # -c safe.directory: this monitor runs as a SERVICE (LOCAL SYSTEM) while
        # the repos are owned by 'renne'. Without this, git refuses with
        # "detected dubious ownership" and the check reports a perfectly healthy
        # repo as DEAD. Observed the moment QI_TaskHealth was promoted from a
        # scheduled task to a service on 2026-08-27.
        #
        # False alarms are not a cosmetic problem here: a monitor that cries
        # wolf gets ignored, and an ignored monitor is exactly the 66-day
        # silence this tool exists to prevent. Read-only ownership relaxation,
        # scoped to the single repo being inspected.
        out = subprocess.run(
            ["git", "-c", "safe.directory=" + repo, "-C", repo,
             "log", "-1", "--format=%cI"],
            capture_output=True, text=True, timeout=60,
        )
        if out.returncode != 0:
            return None, "git failed: %s" % out.stderr.strip()[:120]
        return to_dt(out.stdout.strip()), "last commit %s" % out.stdout.strip()
    except Exception as e:
        return None, "git error: %s" % e


def check_file(spec):
    target = expand_target(spec["target"])
    if spec.get("glob"):
        matches = globmod.glob(os.path.join(target, spec["glob"]))
        if not matches:
            return None, "no file matching %s in %s" % (spec["glob"], target)
        newest = max(matches, key=os.path.getmtime)
        return datetime.fromtimestamp(os.path.getmtime(newest)), \
            "newest %s" % os.path.basename(newest)
    if not os.path.exists(target):
        return None, "missing: %s" % target
    return datetime.fromtimestamp(os.path.getmtime(target)), "mtime"


CHECKS = {
    "sqlite": check_sqlite,
    "marker": check_marker,
    "git": check_git,
    "file": check_file,
}


# ─────────────────────────────────────────────────────────────
# evaluation
# ─────────────────────────────────────────────────────────────
def evaluate(manifest):
    defaults = manifest.get("defaults", {})
    grace = float(defaults.get("grace_hours", 6))
    results = []

    for name, spec in sorted(manifest.get("tasks", {}).items()):
        kind = spec.get("check")
        fn = CHECKS.get(kind)
        entry = {
            "task": name,
            "owner": spec.get("owner", "?"),
            "check": kind,
            "severity": spec.get("severity", "medium"),
            "max_age_hours": spec.get("max_age_hours"),
        }
        if fn is None:
            entry.update(status="ERROR", detail="unknown check type %r" % kind,
                         age_hours=None, last_success=None)
            results.append(entry)
            continue
        try:
            dt, detail = fn(spec)
        except Exception as e:
            dt, detail = None, "check raised: %s" % e
        if dt is None:
            entry.update(status="DEAD", detail=detail, age_hours=None, last_success=None)
        else:
            age = (now() - dt).total_seconds() / 3600.0
            limit = float(spec.get("max_age_hours", 26)) + grace
            entry.update(
                last_success=dt.strftime("%Y-%m-%d %H:%M:%S"),
                age_hours=round(age, 1),
                detail=detail,
                status="OK" if age <= limit else "STALE",
            )
        results.append(entry)
    return results


def load_state():
    try:
        return json.load(open(STATE_FILE, encoding="utf-8"))
    except Exception:
        return {}


def save_state(state):
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        json.dump(state, open(STATE_FILE, "w", encoding="utf-8"), indent=2)
    except Exception as e:
        log("WARN: could not save alert state: %s" % e)


def notify(results, manifest):
    """One alert per task per cooldown window, so a long outage nags once a day
    rather than every poll."""
    cooldown = float(manifest.get("defaults", {}).get("alert_cooldown_hours", 20))
    state = load_state()
    bad = [r for r in results if r["status"] in ("DEAD", "STALE", "ERROR")]
    fresh = []
    for r in bad:
        last = to_dt(state.get(r["task"], {}).get("last_alert"))
        if last is None or (now() - last).total_seconds() / 3600.0 >= cooldown:
            fresh.append(r)

    # recovery notices: was alerting, now OK
    recovered = []
    for r in results:
        if r["status"] == "OK" and state.get(r["task"], {}).get("alerting"):
            recovered.append(r)

    if not fresh and not recovered:
        return 0

    lines = []
    if fresh:
        lines.append("🔴 <b>QI task health — %d task(s) not producing output</b>" % len(fresh))
        for r in sorted(fresh, key=lambda x: (x["severity"] != "high", x["task"])):
            age = "never / unknown" if r["age_hours"] is None else "%.1fh ago" % r["age_hours"]
            lines.append("• <b>%s</b> (%s) — last real output %s\n   %s"
                         % (r["task"], r["severity"], age, r["detail"]))
    if recovered:
        lines.append("")
        lines.append("✅ <b>Recovered:</b> " + ", ".join(r["task"] for r in recovered))
    lines.append("")
    lines.append("<i>Checked by outcome, not LastTaskResult.</i>")

    if tg_send("\n".join(lines)):
        stamp = now().isoformat(timespec="seconds")
        for r in fresh:
            state[r["task"]] = {"last_alert": stamp, "alerting": True}
        for r in recovered:
            state[r["task"]] = {"last_alert": stamp, "alerting": False}
        save_state(state)
        log("alert delivered: %d stale, %d recovered" % (len(fresh), len(recovered)))
    return len(fresh)


def write_status(results):
    payload = {
        "generated_at": now().isoformat(timespec="seconds"),
        "generated_by": "qi_task_health.py",
        "counts": {
            s: sum(1 for r in results if r["status"] == s)
            for s in ("OK", "STALE", "DEAD", "ERROR")
        },
        "tasks": results,
    }
    # Atomic write. The status file is itself watched (the QI_TaskHealth
    # self-entry), so a reader catching it mid-write sees a truncated file and
    # reports the monitor DEAD — a false alarm. Observed 2026-08-27 when a
    # manual run overlapped the scheduled one. A monitor that cries wolf gets
    # ignored, which would defeat the entire point of it, so write to a temp
    # file and os.replace() it into place (atomic on Windows and POSIX alike).
    try:
        os.makedirs(os.path.dirname(STATUS_OUT), exist_ok=True)
        tmp = STATUS_OUT + ".tmp.%d" % os.getpid()
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, STATUS_OUT)
    except Exception as e:
        log("WARN: could not write status file: %s" % e)
        try:
            os.remove(tmp)
        except Exception:
            pass
    return payload


def render(results):
    order = {"DEAD": 0, "ERROR": 1, "STALE": 2, "OK": 3}
    icon = {"OK": "🟢", "STALE": "🟠", "DEAD": "🔴", "ERROR": "⚠️"}
    out = []
    for r in sorted(results, key=lambda x: (order.get(x["status"], 9), x["task"])):
        age = "  never" if r["age_hours"] is None else "%6.1fh" % r["age_hours"]
        out.append("%s %-30s %-6s %s  %s"
                   % (icon.get(r["status"], "?"), r["task"], r["status"], age, r["detail"][:70]))
    return "\n".join(out)


def run_once(args):
    manifest = json.load(open(MANIFEST, encoding="utf-8"))
    results = evaluate(manifest)
    payload = write_status(results)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(render(results))
        c = payload["counts"]
        print("\n%d OK · %d STALE · %d DEAD · %d ERROR"
              % (c["OK"], c["STALE"], c["DEAD"], c["ERROR"]))
    if args.notify:
        notify(results, manifest)
    return 1 if (payload["counts"]["DEAD"] or payload["counts"]["STALE"]) else 0


def run_daemon():
    log("=== QI Task Health monitor started (poll every %d min) ===" % POLL_MINUTES)
    while True:
        try:
            manifest = json.load(open(MANIFEST, encoding="utf-8"))
            results = evaluate(manifest)
            payload = write_status(results)
            c = payload["counts"]
            log("checked %d tasks — %d OK, %d STALE, %d DEAD, %d ERROR"
                % (len(results), c["OK"], c["STALE"], c["DEAD"], c["ERROR"]))
            notify(results, manifest)
        except Exception:
            log("ERROR in poll loop:\n" + traceback.format_exc())
        time.sleep(POLL_MINUTES * 60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="single pass, print report")
    ap.add_argument("--daemon", action="store_true", help="service mode: loop forever")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--notify", action="store_true", help="send Telegram alert if stale")
    args = ap.parse_args()

    if args.daemon:
        run_daemon()
        return 0
    if not args.once:
        args.once = True
    return run_once(args)


if __name__ == "__main__":
    sys.exit(main())

# AI-GENERATED BEGIN (Claude Code, 2026-09-09)
"""QI Brain Drift Check — flags projects whose git history has outrun their QI Brain
project_state row.

Why this exists: the 2026-09-09 status-report reconciliation found six projects whose
Brain project_state was frozen at June dates while their git repos kept moving through
July/August/September. Nobody was watching for that gap — this check closes it, running
nightly so drift is caught within a day instead of months.

For every registered project that has a resolvable git repo:
  - last commit date = the first commit (of the most recent 30) whose subject does NOT
    start with a noise prefix ("nightly", "auto-sync", "chore(sync)") — those are the
    nightly auto-sync bot commits and would otherwise mask real human/agent inactivity.
  - latest Brain state date = MAX(recorded_at) from project_state for that project_id.
  - drift_days = (last commit date) - (latest Brain state date), in days.

A project whose registry status is complete/frozen/merged/retired/paused is expected to
sit idle in Brain — those are SKIPPED from the report UNLESS git is still moving newer
than the Brain state anyway (i.e. drift_days still exceeds the threshold), in which case
it is reported regardless, because someone is committing to a project Brain thinks is
dormant.

Usage:
  python C:\\QIH\\engine\\hive\\tools\\qi_brain_drift_check.py                 # table + log
  python C:\\QIH\\engine\\hive\\tools\\qi_brain_drift_check.py --threshold 21  # custom drift window
  python C:\\QIH\\engine\\hive\\tools\\qi_brain_drift_check.py --json          # machine-readable to stdout

Exit code: always 0. Unattended jobs lie when wrapped in `conhost --headless` (it masks
real exit codes — see C:\\QIH\\shared\\documentation\\QI_Task_Health_Audit_2026-08-27.md),
so QI_TaskHealth reads the per-day log's `overall=PASS` marker instead of the exit code.

Log: C:\\QIH\\LOGS\\brain_drift\\brain_drift_YYYYMMDD.log — a NEW file every day (never a
rolling log) so yesterday's PASS can never satisfy today's health check, one line per
project plus a final `overall=PASS drift_projects=0` (healthy) or
`overall=WARN drift_projects=N projects=id1,id2,...` (N projects over threshold).
"""
import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REGISTRY = Path(r"C:\QIH\ecosystem\qi_registry.json")
BRAIN_DB = r"C:\QIH\data\qi_brain.db"
LOG_DIR = Path(r"C:\QIH\LOGS\brain_drift")
DEV_FALLBACK_ROOT = Path(r"D:\Dev")

NOISE_PREFIXES = ("nightly", "auto-sync", "chore(sync)")
SKIP_STATUS_KEYWORDS = ("complete", "frozen", "merged", "retired", "paused")

DEFAULT_THRESHOLD_DAYS = 14
GIT_LOG_COUNT = 30
GIT_TIMEOUT_SEC = 15


def load_registry_projects():
    """Return list of {id, path, status} dicts from qi_registry.json."""
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    out = []
    for p in data.get("projects", []):
        out.append({
            "id": p.get("id", "?"),
            "path": p.get("path") or "",
            "status": (p.get("status") or "").strip(),
        })
    return out


def find_git_repo(path_str: str):
    """Resolve the effective git repo dir for a registry path.

    The D:\\Dev\\<name> fallback below existed because mediastudio, filmforge and
    voice_studio kept their history there while their registry `path` (C:\\APPS)
    held a copy with no .git. The tier ruling of 2026-09-10 ended that: C:\\APPS
    is the source and carries the repo, and D:\\Dev is a backup clone.

    The fallback is kept as a DETECTOR, not a convenience. If it ever fires now,
    the registry path has lost its .git and the number being reported came off a
    backup - so it is returned as a loud note rather than a silent success.

    Returns (git_dir, note) or (None, reason)."""
    if not path_str:
        return None, "no path in registry"
    candidate = Path(path_str)
    if candidate.is_dir() and (candidate / ".git").is_dir():
        return candidate, None
    # Fallback: D:\Dev\<basename of registry path>
    basename = candidate.name or Path(path_str.rstrip("\\/")).name
    if basename:
        fallback = DEV_FALLBACK_ROOT / basename
        if fallback.is_dir() and (fallback / ".git").is_dir():
            return fallback, (f"WRONG TIER: {candidate} has no .git, read the BACKUP "
                              f"clone D:\\Dev\\{basename} instead - fix the source tier")
    if not candidate.is_dir():
        return None, "path does not exist"
    return None, "no .git"


def last_meaningful_commit_date(git_dir: Path):
    """First (most recent) commit among the last GIT_LOG_COUNT whose subject does not
    start with a noise prefix. Returns (date_str YYYY-MM-DD or None, note)."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(git_dir), "log", "--format=%ad|%s", "--date=short",
             f"-{GIT_LOG_COUNT}"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=GIT_TIMEOUT_SEC,
        )
    except (OSError, subprocess.SubprocessError) as e:
        return None, f"git error: {e}"
    if proc.returncode != 0:
        err = (proc.stderr or "").strip().splitlines()
        return None, f"git log failed: {err[0] if err else proc.returncode}"
    lines = [l for l in proc.stdout.splitlines() if l.strip()]
    if not lines:
        return None, "no commits"
    first_line_date = None
    for i, line in enumerate(lines):
        date_part, _, subject = line.partition("|")
        date_part = date_part.strip()
        if i == 0:
            first_line_date = date_part
        subj_lower = subject.strip().lower()
        if not any(subj_lower.startswith(p) for p in NOISE_PREFIXES):
            return date_part, None
    # every one of the last GIT_LOG_COUNT commits was noise — fall back to the most
    # recent commit anyway (still real information) but say so.
    return first_line_date, f"all last {len(lines)} commits were noise (nightly/auto-sync)"


def load_brain_dates():
    """MAX(recorded_at) per project_id from qi_brain.db, opened read-only."""
    uri = f"file:{Path(BRAIN_DB).as_posix()}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    try:
        cur = con.cursor()
        cur.execute("SELECT project_id, MAX(recorded_at) FROM project_state GROUP BY project_id")
        return {pid: recorded for pid, recorded in cur.fetchall()}
    finally:
        con.close()


def parse_dt(s: str):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.strip())
    except ValueError:
        # last-ditch: strip anything after 19 chars of YYYY-MM-DD[ T]HH:MM:SS
        m = re.match(r"(\d{4}-\d{2}-\d{2})[ T]?(\d{2}:\d{2}:\d{2})?", s.strip())
        if not m:
            return None
        iso = m.group(1) + ("T" + m.group(2) if m.group(2) else "")
        try:
            return datetime.fromisoformat(iso)
        except ValueError:
            return None


def is_skip_status(status: str) -> bool:
    s = status.lower()
    return any(k in s for k in SKIP_STATUS_KEYWORDS)


def run_check(threshold_days: int):
    projects = load_registry_projects()
    brain_dates = load_brain_dates()

    rows = []  # every project with a resolvable git repo
    for p in projects:
        pid, path_str, status = p["id"], p["path"], p["status"]
        git_dir, note = find_git_repo(path_str)
        if git_dir is None:
            continue  # "for every project with a git repo" — no repo, nothing to check
        git_date_str, commit_note = last_meaningful_commit_date(git_dir)
        git_dt = parse_dt(git_date_str) if git_date_str else None

        brain_raw = brain_dates.get(pid)
        brain_dt = parse_dt(brain_raw) if brain_raw else None

        drift_days = None
        if git_dt is not None and brain_dt is not None:
            drift_days = (git_dt.date() - brain_dt.date()).days

        if brain_dt is None:
            flag = "NO_BRAIN_STATE"
        elif git_dt is None:
            flag = "NO_GIT_DATE"
        elif drift_days is not None and drift_days > threshold_days:
            flag = "WARN"
        else:
            flag = "OK"

        rows.append({
            "id": pid,
            "status": status,
            "git_dir": str(git_dir),
            "git_dir_note": note,
            "git_date": git_date_str,
            "commit_note": commit_note,
            "brain_date": brain_raw,
            "drift_days": drift_days,
            "flag": flag,
        })

    # Skip logic: registry status says the project is done/paused/etc — omit it from the
    # report UNLESS it's actually flagged (drift beyond threshold, or no Brain state at
    # all — both are things worth seeing even on a "paused" project).
    reported = []
    for r in rows:
        if is_skip_status(r["status"]) and r["flag"] not in ("WARN", "NO_BRAIN_STATE"):
            continue
        reported.append(r)

    flagged = [r for r in reported if r["flag"] in ("WARN", "NO_BRAIN_STATE")]

    return {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "threshold_days": threshold_days,
        "all_rows": rows,
        "reported": reported,
        "flagged": flagged,
    }


def print_table(report):
    rows = report["reported"]
    if not rows:
        print("No projects to report (nothing with a resolvable git repo).")
        return
    w_id = max(len(r["id"]) for r in rows) + 1
    w_status = max(len(r["status"]) for r in rows) + 1
    header = f"{'PROJECT':<{w_id}} {'STATUS':<{w_status}} {'GIT DATE':<10} {'BRAIN DATE':<10} {'DRIFT':>6}  FLAG"
    print(header)
    print("-" * len(header))
    for r in sorted(rows, key=lambda r: (-(r["drift_days"] or -9999), r["id"])):
        git_date = r["git_date"] or "?"
        brain_date = (r["brain_date"] or "?")[:10]
        drift = r["drift_days"]
        drift_s = f"{drift:>6}" if drift is not None else "     ?"
        icon = "⚠️ " if r["flag"] in ("WARN", "NO_BRAIN_STATE") else "✅ "
        print(f"{r['id']:<{w_id}} {r['status']:<{w_status}} {git_date:<10} {brain_date:<10} {drift_s}  {icon}{r['flag']}")
    if report["flagged"]:
        print()
        print(f"FLAGGED ({len(report['flagged'])}):")
        for r in report["flagged"]:
            print(f"  - {r['id']}: {r['flag']} (git={r['git_date']}, brain={ (r['brain_date'] or '?')[:10] }, drift={r['drift_days']})")


def write_log(report, threshold_days):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"brain_drift_{datetime.now():%Y%m%d}.log"
    lines = [f"=== QI Brain Drift Check — {report['ts']} — threshold={threshold_days}d ==="]
    for r in report["reported"]:
        lines.append(
            f"{r['id']} status={r['status'] or '?'} git_date={r['git_date'] or '?'} "
            f"brain_date={(r['brain_date'] or '?')} drift_days={r['drift_days']} flag={r['flag']}"
        )
    flagged_ids = [r["id"] for r in report["flagged"]]
    if flagged_ids:
        lines.append(f"overall=WARN drift_projects={len(flagged_ids)} projects={','.join(flagged_ids)}")
    else:
        lines.append("overall=PASS drift_projects=0")
    lines.append("")  # trailing blank line between runs
    with log_path.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return log_path


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD_DAYS,
                     help=f"drift days above which a project is flagged (default {DEFAULT_THRESHOLD_DAYS})")
    ap.add_argument("--json", action="store_true", help="print JSON report to stdout instead of the table")
    a = ap.parse_args()

    report = run_check(a.threshold)
    log_path = write_log(report, a.threshold)

    if a.json:
        out = {
            "ts": report["ts"],
            "threshold_days": report["threshold_days"],
            "projects": report["reported"],
            "flagged": [r["id"] for r in report["flagged"]],
            "overall": "WARN" if report["flagged"] else "PASS",
            "log": str(log_path),
        }
        print(json.dumps(out, indent=1, ensure_ascii=False))
    else:
        print_table(report)
        print()
        print(f"Log: {log_path}")
        if report["flagged"]:
            print(f"overall=WARN drift_projects={len(report['flagged'])}")
        else:
            print("overall=PASS drift_projects=0")

    sys.exit(0)  # always 0 — conhost --headless masks real codes anyway; QI_TaskHealth
                 # reads the log marker, not this exit code.


if __name__ == "__main__":
    main()
# AI-GENERATED END

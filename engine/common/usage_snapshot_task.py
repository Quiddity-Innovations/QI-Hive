"""
QI Hive — usage ledger snapshot runner.

Captures the currently-visible transcript window into the durable ledger in
qi_brain.db. Once a day has been snapshotted, deleting its transcript no
longer loses it. Cheap: it only touches the last ~45 days and never rewrites
measured rows that are already correct.

Three triggers, deliberately overlapping — the ledger going stale is not a
cosmetic problem, it silently truncates every 30d/QTD/YTD figure on the LLM
Usage tab (see `ensure_fresh` below and `usage_ledger.max_day`):

  1. `QI_UsageSnapshot` scheduled task — daily, the primary guarantee.
  2. `ensure_fresh()` — called by the dashboard read paths, so simply loading
     the page repairs a stale ledger.
  3. By hand at any time:

         python C:\\QIH\\engine\\common\\usage_snapshot_task.py

History: this module's docstring used to claim it was wired into the Claude
Code SessionEnd hook. It never was — `~/.claude/session_end.py` does not call
it — so between 2026-08-05 and 2026-08-13 nothing ran it and YTD froze at
$60,124 while real spend was $70,126. Hence the belt-and-braces above.
"""
from __future__ import annotations

import sys
import threading
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

WINDOW_DAYS = 45

# ── ensure_fresh throttle ───────────────────────────────────────────────────
# Guards against a burst of dashboard requests each firing its own snapshot: at
# most one snapshot per _MIN_INTERVAL per process, so a persistently failing
# snapshot cannot turn into a hot loop either.
#
# `None` rather than 0.0 because time.monotonic() is time-since-boot on
# Windows: QI_Dashboard starts at boot, so a 0.0 sentinel would read as
# "attempted <5 min ago" and skip every repair for the first _MIN_INTERVAL
# after a reboot — the exact window in which a stale ledger most needs fixing.
_MIN_INTERVAL = 300.0
_lock = threading.Lock()
_last_attempt: float | None = None


def run(days: int = WINDOW_DAYS) -> dict:
    """Snapshot the ledger and re-derive the dimension tables for the window.

    Raises on failure — callers that must not break (CLI teardown, dashboard
    render) are responsible for swallowing. Returns the counts for logging.
    """
    import usage_dimensions
    import usage_ledger

    res = usage_ledger.snapshot(days=days)
    # Keep the per-project/per-model tables in step with the days just
    # snapshotted, so the By-Project / By-Model tables never drift from
    # the day totals. Scoped to the same window to stay cheap.
    dim = usage_dimensions.backfill(
        verbose=False, since=date.today() - timedelta(days=days))
    return {
        "written": res["written"],
        "project_rows": dim["project_rows"],
        "model_rows": dim["model_rows"],
        "unreconciled_projects": dim["unreconciled_projects"],
        "unreconciled_models": dim["unreconciled_models"],
    }


def _run_quiet(days: int) -> None:
    """`run()` with logging instead of exceptions — for the background thread."""
    try:
        r = run(days=days)
        if r["written"]:
            _emit(f"[usage_ledger] background refresh: {r['written']} day(s), "
                  f"{r['project_rows']}p/{r['model_rows']}m")
    except Exception as e:
        _emit(f"[usage_ledger] background refresh FAILED: {e!r}")


def ensure_fresh(days: int = WINDOW_DAYS, force: bool = False,
                 background: bool = True) -> dict | None:
    """Keep the ledger current enough to answer a usage read truthfully.

    Snapshots at most once per `_MIN_INTERVAL`, unconditionally rather than
    probing which kind of staleness applies. Both kinds matter:

    * **A missing day** (`max_day() < today`) is the damaging one — every
      window helper that finds *any* row for a window silently truncates
      there, so 30d/QTD/YTD all understate until the day is written.
    * **A stale today row** is merely cosmetic — the figure is real, just a
      few minutes behind. Refreshing anyway is what keeps "today" ticking up
      instead of freezing at whatever the first snapshot of the day captured.

    `background=True` (the default, and what the dashboard uses) runs the
    ~2s snapshot on a daemon thread and returns immediately. It must not run
    inline: the `/` page already takes ~2.2s to render against a 3s smoke-test
    timeout, and adding the snapshot to that path pushed it over. The cost of
    deferring is that the request which *noticed* the staleness still answers
    from the stale ledger — the next one, a couple of seconds later, is
    correct. That is an acceptable trade because `QI_UsageSnapshot` is the
    real guarantee and this is only the safety net.

    Returns `{"started": True}` when a background refresh was launched, the
    `run()` result when `background=False`, and None when throttled or failed.
    Never raises.
    """
    import time

    global _last_attempt
    try:
        # Hold the lock only for the throttle bookkeeping — never across the
        # snapshot itself, or concurrent readers would serialise behind it.
        with _lock:
            now = time.monotonic()
            if (not force and _last_attempt is not None
                    and (now - _last_attempt) < _MIN_INTERVAL):
                return None
            _last_attempt = now
        if not background:
            return run(days=days)
        threading.Thread(target=_run_quiet, args=(days,),
                         name="usage-snapshot", daemon=True).start()
        return {"started": True}
    except Exception:
        return None


LOG_FILE = Path(r"C:\QIH\logs\usage_snapshot.log")


def _emit(msg: str) -> None:
    """Log a line to the task log, and to stdout when there is one.

    The scheduled task runs under pythonw.exe, where sys.stdout/stderr are
    None — a bare print() there raises and the task exits 1. So the log file
    is the real output channel and stdout is best-effort.
    """
    line = f"{datetime.now().isoformat(timespec='seconds')} {msg}"
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass
    if sys.stdout is not None:
        try:
            print(line)
        except Exception:
            pass


def main() -> int:
    try:
        import usage_ledger

        r = run()
        ytd = usage_ledger.totals_since(date(date.today().year, 1, 1))
        _emit(f"[usage_ledger] snapshotted {r['written']} day(s); "
              f"dimensions {r['project_rows']}p/{r['model_rows']}m; "
              f"YTD ${ytd['cost_usd']:,.2f} "
              f"({ytd['measured_pct']}% measured)")
        if r["unreconciled_projects"] or r["unreconciled_models"]:
            _emit(f"[usage_ledger] WARNING unreconciled days — "
                  f"projects={r['unreconciled_projects']} "
                  f"models={r['unreconciled_models']}")
        return 0
    except Exception as e:
        # Never let a bookkeeping failure break session teardown.
        _emit(f"[usage_ledger] snapshot FAILED: {e!r}")
        return 0


if __name__ == "__main__":
    # pythonw has no stdout to reconfigure; guard rather than assume.
    if sys.stdout is not None:
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    raise SystemExit(main())

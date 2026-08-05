"""
QI Hive — usage ledger snapshot runner.

Captures the currently-visible transcript window into the durable ledger in
qi_brain.db. Once a day has been snapshotted, deleting its transcript no
longer loses it.

Wired into the Claude Code SessionEnd hook so it runs after every session --
that guarantees a day is persisted while its transcript still exists, with no
dependency on a scheduler being alive. Cheap: it only touches the last ~45
days and never rewrites measured rows that are already correct.

Safe to run by hand at any time:

    python C:\\QIH\\engine\\common\\usage_snapshot_task.py
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def main() -> int:
    try:
        from datetime import timedelta

        import usage_dimensions
        import usage_ledger

        res = usage_ledger.snapshot(days=45)
        # Keep the per-project/per-model tables in step with the days just
        # snapshotted, so the By-Project / By-Model tables never drift from
        # the day totals. Scoped to the same window to stay cheap.
        dim = usage_dimensions.backfill(
            verbose=False, since=date.today() - timedelta(days=45))
        ytd = usage_ledger.totals_since(date(date.today().year, 1, 1))
        print(f"[usage_ledger] snapshotted {res['written']} day(s); "
              f"dimensions {dim['project_rows']}p/{dim['model_rows']}m; "
              f"YTD ${ytd['cost_usd']:,.2f} "
              f"({ytd['measured_pct']}% measured)")
        if dim["unreconciled_projects"] or dim["unreconciled_models"]:
            print(f"[usage_ledger] WARNING unreconciled days — "
                  f"projects={dim['unreconciled_projects']} "
                  f"models={dim['unreconciled_models']}", file=sys.stderr)
        return 0
    except Exception as e:
        # Never let a bookkeeping failure break session teardown.
        print(f"[usage_ledger] snapshot skipped: {e}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())

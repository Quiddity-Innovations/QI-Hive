# -*- coding: utf-8 -*-
"""
One-shot repair: collapse duplicate tasks on the QI Hive board.

Background (2026-08-17 audit)
----------------------------
health_check._promote_dispatches_to_tasks() keyed tasks on dispatch_id, but the
Inspector files a NEW dispatch for the same finding on every run. Each run
therefore added another copy: 233 open tasks, only 80 distinct — eighteen
identical .gitignore tasks per project. The board became unreadable, which is
why 4-month-old items sat untouched.

The promoter has been fixed to dedup on (project, check_id). This cleans up the
backlog it already produced:

  1. Tasks whose dispatch is now resolved  -> moved to done.
  2. Duplicate (project, title) groups     -> keep the OLDEST (it carries the
                                              original created_at and any manual
                                              edits), drop the rest.

Nothing is deleted from disk without a backup. Safe to re-run: idempotent.
"""
from __future__ import annotations
import json, shutil, sqlite3, sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

TASKS = Path(r"C:\QIH\data\tasks.json")
DB = Path(r"C:\QIH\data\qi_brain.db")


def main(apply: bool) -> int:
    data = json.loads(TASKS.read_text(encoding="utf-8"))
    tasks = data.get("tasks", [])
    before_open = sum(1 for t in tasks if t.get("column") != "done")

    # ── 1. close tasks whose dispatch is resolved ────────────────────────────
    resolved: set[str] = set()
    if DB.exists():
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        try:
            resolved = {
                f"disp-{r[0]}" for r in con.execute(
                    "SELECT dispatch_id FROM dispatches WHERE status='resolved'")
            }
        finally:
            con.close()

    closed = 0
    for t in tasks:
        if t.get("column") != "done" and t.get("id") in resolved:
            t["column"] = "done"
            t["description"] = (t.get("description") or "") + \
                f"  [{datetime.now():%Y-%m-%d} audit] Closed: underlying dispatch resolved."
            closed += 1

    # ── 2. collapse duplicates among the still-open tasks ────────────────────
    kept: dict[tuple, dict] = {}
    dropped: list[dict] = []
    out: list[dict] = []
    for t in tasks:
        if t.get("column") == "done":
            out.append(t)
            continue
        key = ((t.get("project") or "").lower(), (t.get("title") or "").strip().lower())
        prev = kept.get(key)
        if prev is None:
            kept[key] = t
            out.append(t)
            continue
        # Keep whichever is older — it holds the original created_at and any
        # human edits made since.
        if (t.get("created_at") or "9999") < (prev.get("created_at") or "9999"):
            out[out.index(prev)] = t
            kept[key] = t
            dropped.append(prev)
        else:
            dropped.append(t)

    after_open = sum(1 for t in out if t.get("column") != "done")
    print(f"open before   : {before_open}")
    print(f"  closed      : {closed}  (dispatch resolved)")
    print(f"  deduplicated: {len(dropped)}")
    print(f"open after    : {after_open}")
    if dropped:
        import collections
        worst = collections.Counter(
            (d.get("project"), (d.get("title") or "")[:48]) for d in dropped
        ).most_common(5)
        print("\n  largest duplicate groups removed:")
        for (proj, title), n in worst:
            print(f"    x{n:3}  {str(proj):12} {title}")

    if not apply:
        print("\nDRY RUN — pass --apply to write.")
        return 0

    bak = TASKS.with_suffix(f".json.bak-dedupe-{datetime.now():%Y%m%d-%H%M%S}")
    shutil.copy2(TASKS, bak)
    data["tasks"] = out
    TASKS.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nbackup  -> {bak}")
    print(f"written -> {TASKS}  ({len(out)} tasks, {after_open} open)")
    return 0


if __name__ == "__main__":
    sys.exit(main("--apply" in sys.argv))

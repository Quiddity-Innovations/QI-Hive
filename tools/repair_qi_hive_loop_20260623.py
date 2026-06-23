# -*- coding: utf-8 -*-
"""
One-shot repair for the qi_hive distilled-brain-memory feedback loop.

Root cause (fixed in poller.py + nightly_reconcile.py): qi_hive's state file IS
C:\\QIH\\data\\status.json, the same file the reconciler writes Brain summaries
back into. The poller stamped "[auto:state_file] " onto each summary; the
reconciler wrote it back into status.json; the next poll re-ingested and
re-prefixed it, compounding to "[auto:state_file] [auto:state_file] …" until the
real content was pushed past the 300-char cap.

This script repairs the data already corrupted by the loop:
  1. Deletes the pure-garbage compounded project_state rows for qi_hive.
  2. Inserts one clean, current project_state row.
  3. Rewrites status.json qi_hive summary/phase/next_steps to the clean value.
"""
import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DB = r"C:\QIH\data\qi_brain.db"
STATUS_JSON = Path(r"C:\QIH\data\status.json")

CLEAN_PHASE = "Dashboard UX polish"
CLEAN_STATUS = "active"
CLEAN_SUMMARY = (
    "Dashboard home, /hive and LLM Usage redesigned to a calm Bento + "
    "status-table layout; Documentation Brain UI (search + Plex graph + split "
    "view + draggable resize). Fixed a Brain feedback loop where the poller "
    "re-ingested its own [auto:state_file] marker from status.json (qi_hive's "
    "state file = status.json), compounding the summary into garbage."
)
CLEAN_NEXT = "Monitor that qi_hive summary stays clean after poll cycles."

_GARBAGE_RE = re.compile(r"\[auto:state_file\]\s*\[auto:state_file\]")

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

# 1. Delete compounded garbage rows for qi_hive.
before = cur.execute(
    "SELECT COUNT(*) FROM project_state WHERE project_id='qi_hive'"
).fetchone()[0]
cur.execute(
    "DELETE FROM project_state "
    "WHERE project_id='qi_hive' AND summary LIKE '%[auto:state_file] [auto:state_file]%'"
)
deleted = cur.rowcount

# 2. Insert one clean current row (no provenance marker — manual repair).
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
cur.execute(
    "INSERT INTO project_state (project_id, agent_id, phase, status, summary, next_steps, recorded_at) "
    "VALUES ('qi_hive', 'claude', ?, ?, ?, ?, ?)",
    (CLEAN_PHASE, CLEAN_STATUS, CLEAN_SUMMARY, CLEAN_NEXT, now),
)
con.commit()
after = cur.execute(
    "SELECT COUNT(*) FROM project_state WHERE project_id='qi_hive'"
).fetchone()[0]
con.close()

print(f"project_state qi_hive rows: {before} -> {after} (deleted {deleted} garbage rows, inserted 1 clean)")

# 3. Rewrite status.json qi_hive summary to the clean value.
doc = json.loads(STATUS_JSON.read_text(encoding="utf-8"))
p = doc.setdefault("projects", {}).setdefault("qi_hive", {})
p["summary"] = CLEAN_SUMMARY
p["phase"] = CLEAN_PHASE
p["status"] = CLEAN_STATUS
p["next_steps"] = CLEAN_NEXT
STATUS_JSON.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
print("status.json qi_hive summary cleaned.")
print("New summary:", CLEAN_SUMMARY[:80], "...")

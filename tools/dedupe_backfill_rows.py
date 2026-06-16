# -*- coding: utf-8 -*-
"""Dedupe backfill rows in session_log by TRANSCRIPT marker."""
import sys, sqlite3, re, os
sys.stdout.reconfigure(encoding="utf-8")

c = sqlite3.connect(r"C:\QIH\data\qi_brain.db")
rows = c.execute(
    "SELECT rowid, summary FROM session_log "
    "WHERE agent_id='claude_code_backfill' AND summary LIKE '%TRANSCRIPT:%' "
    "ORDER BY rowid"
).fetchall()

def canon(p):
    return os.path.normcase(os.path.normpath(p.strip())).replace("/", "\\")

seen = {}
to_delete = []
for rowid, summary in rows:
    m = re.search(r"TRANSCRIPT:\s*(.+?)$", summary, re.MULTILINE)
    if not m:
        continue
    key = canon(m.group(1))
    if key in seen:
        to_delete.append(rowid)
    else:
        seen[key] = rowid

print(f"Keeping {len(seen)} unique backfill rows; deleting {len(to_delete)} dupes")
for rid in to_delete:
    c.execute("DELETE FROM session_log WHERE rowid=?", (rid,))
c.commit()
print(f"session_log now has {c.execute('SELECT COUNT(*) FROM session_log').fetchone()[0]} rows.")

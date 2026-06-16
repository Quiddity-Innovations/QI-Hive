# -*- coding: utf-8 -*-
"""Rebuild the 'projects' + 'session_log' sections of C:\\QIH\\data\\status.json
from the LIVE Brain DB + registry, keyed by lowercase canonical id.

Fixes: stale dashboard cards (missing 7 projects + duplicate 'QI Hive'/'QI_Hive'
junk), and the project-detail page (lookup now matches /project/<lowercase-id>).
Preserves all other status.json sections (agents, infrastructure, hive_reports...).
"""
import json, sqlite3
from pathlib import Path
from datetime import datetime, timezone

STATUS = Path(r"C:\QIH\data\status.json")
DB     = r"C:\QIH\data\qi_brain.db"
REG    = json.loads(Path(r"C:\QIH\ecosystem\qi_registry.json").read_text(encoding="utf-8"))
reg_by_id = {p["id"]: p for p in REG["projects"]}

con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
cur = con.cursor()

# latest state per project
state = {}
for r in cur.execute("SELECT * FROM project_state ORDER BY recorded_at DESC"):
    state.setdefault(r["project_id"], r)
# last activity per project
last = {r[0]: r[1] for r in cur.execute(
    "SELECT project_id, MAX(COALESCE(ended_at,started_at)) FROM session_log GROUP BY project_id")}

projects = {}
for r in cur.execute("SELECT * FROM projects ORDER BY project_id"):
    pid = r["project_id"]
    st = state.get(pid)
    reg = reg_by_id.get(pid, {})
    ports = reg.get("ports", {})
    # services list for the detail page (derive from registry ports roles present)
    projects[pid] = {
        "id": pid,
        "display_name": r["display_name"] or pid,
        "status": (st["status"] if st else "active"),
        "phase": (st["phase"] if st else ""),
        "current_task": (st["next_steps"] if st and st["next_steps"] else "—"),
        "notes": (st["summary"] if st and st["summary"] else (r["tagline"] or "")),
        "path": r["path"] or reg.get("path", ""),
        "last_activity": (last.get(pid) or "")[:10],
        "api_port": r["api_port"],
        "ui_port": r["ui_port"],
        "ports": {k: v.get("current") for k, v in ports.items() if isinstance(v, dict)},
        "locked_files": [],
        "tier": reg.get("family_tier", ""),
    }

# recent global session log (used by project detail page)
sessions = []
for r in cur.execute(
    "SELECT project_id, session_title, summary, COALESCE(ended_at,started_at) AS ts "
    "FROM session_log ORDER BY ts DESC LIMIT 60"):
    sessions.append({"project": r["project_id"], "session": r["session_title"],
                     "summary": r["summary"] or "", "ts": r["ts"]})
con.close()

# merge into existing status.json (preserve other sections)
data = json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {}
data["projects"] = projects
data["session_log"] = sessions
data["_meta"] = {
    "description": "Cross-project live state - regenerated from qi_brain.db + qi_registry.json",
    "last_updated": datetime.now(timezone.utc).isoformat(),
    "last_session": "hive-audit-regen",
    "update_rule": "Regenerate via C:\\QIH\\tools\\regen_status_json_2026-06-15.py (or nightly reconcile).",
}
STATUS.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"status.json rebuilt: {len(projects)} projects (lowercase ids), {len(sessions)} recent sessions")
print("project keys:", ", ".join(sorted(projects)))

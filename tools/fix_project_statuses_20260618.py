# -*- coding: utf-8 -*-
"""One-shot: correct project statuses to owner (Renne) truth across all layers.
mq->new, universal->merged, digitization->complete, cypherminer->complete.
filehq already retired/merged (gray) — no change."""
import sys, json, sqlite3
from datetime import datetime
sys.path.insert(0, r"C:\QIH\engine\brain")
sys.stdout.reconfigure(encoding="utf-8")

CORRECTIONS = {
    "mq":          "new",
    "universal":   "merged",
    "digitization":"complete",
    "cypherminer": "complete",
}
NOTE = "Status corrected per owner (Renne) 2026-06-18 dashboard review."
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 1) Dashboard status.json (what the dashboard reads)
sp = r"C:\QIH\data\status.json"
d = json.load(open(sp, encoding="utf-8"))
projs = d.get("projects", d)
for k, v in CORRECTIONS.items():
    if k in projs:
        projs[k]["status"] = v
json.dump(d, open(sp, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("[1/3] status.json updated:", {k: projs[k]["status"] for k in CORRECTIONS if k in projs})

# 2) qi_brain.db project_state — authoritative; insert new latest rows
from core.db import open_brain_db
with open_brain_db() as c:
    for pid, st in CORRECTIONS.items():
        prev = c.execute(
            "SELECT phase, summary, blockers, next_steps FROM project_state "
            "WHERE project_id=? ORDER BY recorded_at DESC LIMIT 1", (pid,)
        ).fetchone()
        phase  = (prev["phase"] if prev else "") or ""
        summ   = ((prev["summary"] if prev else "") or "")
        summ   = (summ + "  " + NOTE).strip()
        blk    = (prev["blockers"] if prev else "") or ""
        nxt    = (prev["next_steps"] if prev else "") or ""
        c.execute(
            "INSERT INTO project_state (project_id, agent_id, phase, status, summary, blockers, next_steps, recorded_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (pid, "claude", phase, st, summ, blk, nxt, now),
        )
    c.commit()
    print("[2/3] qi_brain.db project_state rows inserted (now latest)")

# 3) qi_registry.json — ecosystem source of truth
rp = r"C:\QIH\ecosystem\qi_registry.json"
reg = json.load(open(rp, encoding="utf-8"))
changed = {}
for p in reg.get("projects", []):
    pid = p.get("id")
    if pid in CORRECTIONS and p.get("status") != CORRECTIONS[pid]:
        changed[pid] = (p.get("status"), CORRECTIONS[pid])
        p["status"] = CORRECTIONS[pid]
json.dump(reg, open(rp, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("[3/3] qi_registry.json updated:", changed)
print("DONE")

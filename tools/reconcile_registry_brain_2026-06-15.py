# -*- coding: utf-8 -*-
"""Close the last two registry<->Brain gaps:
   - tubescout: in registry, missing from Brain  -> add to Brain
   - claude_manager: in Brain, missing from registry -> add to registry
Idempotent.
"""
import json, sqlite3
from pathlib import Path

REG = Path(r"C:\QIH\ecosystem\qi_registry.json")
DB  = r"C:\QIH\data\qi_brain.db"
TS  = "2026-06-15 20:10:00"

reg = json.loads(REG.read_text(encoding="utf-8"))
reg_by_id = {p["id"]: p for p in reg["projects"]}
con = sqlite3.connect(DB); cur = con.cursor()
brain_ids = {r[0] for r in cur.execute("SELECT project_id FROM projects")}

# ── 1. tubescout -> Brain ─────────────────────────────────────────────────────
ts = reg_by_id.get("tubescout")
if ts and "tubescout" not in brain_ids:
    ports = ts.get("ports", {})
    api = ports.get("api", {}).get("current")
    ui  = ports.get("ui", {}).get("current")
    cur.execute("INSERT INTO projects (project_id,display_name,tagline,path,api_port,ui_port,tier,active,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        ("tubescout", ts.get("name", "TubeScout"),
         (ts.get("description") or "TubeScout")[:120], ts.get("path", r"C:\TUBESCOUT"),
         api, ui, "project", 1, TS))
    cur.execute("INSERT INTO project_state (project_id,agent_id,phase,status,summary,blockers,next_steps,recorded_at) VALUES (?,?,?,?,?,?,?,?)",
        ("tubescout", "claude", "registered", "active",
         f"{ts.get('description','TubeScout')} API live on :{api}. Backfilled into Brain to match registry.",
         None, "Confirm phase/state; add to nightly reconcile (done); first git commit if missing.", TS))
    cur.execute("INSERT INTO session_log (project_id,agent_id,session_title,summary,decisions_made,features_logged,files_changed,next_steps,model_used,started_at,ended_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("tubescout", "claude", "TubeScout - registered in Brain",
         "Backfilled TubeScout into the Brain projects table to match the ecosystem registry (was registry-only).",
         0,0,"[]","","opus-4.8", TS, TS))
    print("brain: added tubescout")
else:
    print("brain: tubescout already present or missing from registry")

# ── 2. claude_manager -> registry ─────────────────────────────────────────────
if "claude_manager" not in reg_by_id:
    row = cur.execute("SELECT display_name, path FROM projects WHERE project_id='claude_manager'").fetchone()
    name = (row[0] if row else "Claude Manager")
    path = (row[1] if row and row[1] else r"C:\CLAUDE")
    reg["projects"].append({
        "id": "claude_manager",
        "name": name,
        "description": "Claude Code management workspace — QI Hive orchestration, ecosystem reconciliation scripts, Brain backfills, and cross-project session management. Meta/management project (no served ports).",
        "path": path,
        "github": "TBD",
        "status": "active",
        "primary_language": "Python",
        "ports": {},
        "family_tier": "backbone",
        "family_notes": "Management/meta workspace that operates ON the ecosystem rather than being a deployed app.",
        "integrates_with": ["qi_hive", "qi_brain"],
        "exposes_to_ecosystem": ["Ecosystem reconciliation + project registration tooling"],
        "consumes_from_ecosystem": ["qi_brain", "qi_hive"]
    })
    REG.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")
    print("registry: added claude_manager")
else:
    print("registry: claude_manager already present")

con.commit()
# Final consistency check
reg2 = {p["id"] for p in json.loads(REG.read_text(encoding="utf-8"))["projects"]}
brain2 = {r[0] for r in cur.execute("SELECT project_id FROM projects")}
con.close()
print("\nregistry count:", len(reg2), "| brain count:", len(brain2))
print("registry-only:", sorted(reg2-brain2) or "none")
print("brain-only:   ", sorted(brain2-reg2) or "none")
print("DONE")

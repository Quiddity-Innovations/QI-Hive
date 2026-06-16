# -*- coding: utf-8 -*-
"""Register Fidelity Portfolio Analyzer in Brain DB + polish its registry entry."""
import json, sqlite3
from pathlib import Path

REG = Path(r"C:\QIH\ecosystem\qi_registry.json")
DB  = r"C:\QIH\data\qi_brain.db"
TS  = "2026-06-15 19:15:00"
PID = "fidelityanalyzer"

# 1) Registry: upgrade display name + description + family notes
reg = json.loads(REG.read_text(encoding="utf-8"))
for p in reg["projects"]:
    if p.get("id") == PID:
        p["name"] = "Fidelity Portfolio Analyzer"
        p["description"] = ("Ingests a Fidelity positions CSV export and computes allocation, "
                            "concentration risk (top-5 + HHI), drift vs target, and rebalancing "
                            "trade recommendations. FastAPI + Gradio.")
        p["status"] = "active"
        p["family_notes"] = ("Personal-finance utility. Automates the manual Fidelity portfolio "
                             "review/rebalancing previously done by hand (see Downloads analysis docs).")
        p["exposes_to_ecosystem"] = ["GET /health", "GET /version", "GET /info",
                                     "GET /target", "POST /analyze", "POST /analyze_text", "POST /rebalance"]
        break
REG.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")
print("registry: display name + metadata updated")

# 2) Brain DB
con = sqlite3.connect(DB); cur = con.cursor()
if not cur.execute("SELECT 1 FROM projects WHERE project_id=?", (PID,)).fetchone():
    cur.execute("INSERT INTO projects (project_id,display_name,tagline,path,api_port,ui_port,tier,active,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (PID, "Fidelity Portfolio Analyzer",
         "Fidelity positions CSV -> allocation, concentration, drift, rebalancing",
         r"C:\FidelityAnalyzer", 8504, 7844, "project", 1, TS))
    print("brain.projects: added")
else:
    print("brain.projects: already present")

if not cur.execute("SELECT 1 FROM project_state WHERE project_id=? AND recorded_at=?", (PID, TS)).fetchone():
    cur.execute("INSERT INTO project_state (project_id,agent_id,phase,status,summary,blockers,next_steps,recorded_at) VALUES (?,?,?,?,?,?,?,?)",
        (PID, "claude", "v1 - engine + API + UI live", "active",
         "Scaffolded via qi_new_project.py (19/19 compliance). Built stdlib analysis engine "
         "(allocation, concentration/HHI, drift, rebalancing), FastAPI on 8504, Gradio UI on 7844, "
         "sample dataset. Verified /analyze on sample (11 positions, $210k). Registered in registry + Brain + dashboard.",
         "Not yet an NSSM service; no public tunnel; PDF ingestion not implemented (CSV only).",
         "Install QI_FidelityAnalyzer + QI_FidelityAnalyzerTunnel services; add PDF positions parsing; "
         "configurable target allocation in UI; first git commit + GitHub.", TS))
    print("brain.project_state: added")

for title, summ, start, end in [
    ("Fidelity Portfolio Analyzer - new project build",
     "Created the project via the QI new-project wizard (registered + scaffolded + git + 19/19 validator), "
     "then built the analysis engine, FastAPI endpoints (/analyze,/analyze_text,/rebalance,/target), Gradio UI, "
     "and a sample Fidelity positions dataset. App verified running (API 8504, UI 7844).",
     "2026-06-15 18:45:00", "2026-06-15 19:15:00"),
]:
    if not cur.execute("SELECT 1 FROM session_log WHERE project_id=? AND session_title=?", (PID, title)).fetchone():
        cur.execute("INSERT INTO session_log (project_id,agent_id,session_title,summary,decisions_made,features_logged,files_changed,next_steps,model_used,started_at,ended_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (PID, "claude", title, summ, 0, 0, "[]", "", "opus-4.8", start, end))
        print("brain.session_log: added")

con.commit()
print("brain projects total:", cur.execute("SELECT COUNT(*) FROM projects").fetchone()[0])
con.close()
print("DONE")

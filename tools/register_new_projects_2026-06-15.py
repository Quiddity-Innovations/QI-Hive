# -*- coding: utf-8 -*-
"""
One-shot registration of three projects the Hive was missing:
  - lotterywiz   (Lottery Wiz)         C:\\APPS\\Lottery Wiz
  - cypherminer  (CypherMiner)         C:\\APPS\\CypherMiner   (was in registry, missing from Brain DB)
  - digitization (Digitization Cost Tool)  C:\\Users\\renne\\Downloads\\DIGITIZATION COSTS

Updates:
  1) C:\\QIH\\ecosystem\\qi_registry.json  -> add lotterywiz + digitization (launcher tiles)
  2) C:\\QIH\\data\\qi_brain.db            -> projects + project_state + session_log (activities)

Idempotent: re-running will not create duplicates.
"""
import sys, json, sqlite3
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REGISTRY = Path(r"C:\QIH\ecosystem\qi_registry.json")
DB       = r"C:\QIH\data\qi_brain.db"
TODAY    = "2026-06-15"
TS       = "2026-06-15 18:30:00"

# ── 1. Registry entries (launcher tiles) ──────────────────────────────────────
REG_NEW = {
    "lotterywiz": {
        "id": "lotterywiz",
        "name": "LotteryWiz",
        "description": "Fantasy 5 covering-design app — generates optimal play sets with guaranteed coverage. FastAPI + export to .xlsx/.csv.",
        "path": r"C:\APPS\Lottery Wiz",
        "github": "TBD",
        "status": "active",
        "primary_language": "Python",
        "ports": {"api": {"current": 8777, "block": "8770-8779",
                          "notes": "Pre-registry ad-hoc port — works, kept per migration_note. UI served from same FastAPI app."}},
        "family_tier": "sibling",
        "family_notes": "Standalone utility app. NSSM service QI_LotteryWiz + public tunnel QI_LotteryWizTunnel (installed 2026-06-15).",
        "integrates_with": [],
        "exposes_to_ecosystem": ["Fantasy 5 covering-design generator", "Play-set export API"],
        "consumes_from_ecosystem": []
    },
    "digitization": {
        "id": "digitization",
        "name": "Digitization Cost Tool",
        "description": "BU Digitization Cost Comparison Tool — client-side HTML calculator for Document Imaging & Services pricing/scenarios. Ships with technical docs + user guide.",
        "path": r"C:\Users\renne\Downloads\DIGITIZATION COSTS",
        "github": "TBD",
        "status": "active",
        "primary_language": "HTML/JS",
        "ports": {},
        "family_tier": "sibling",
        "family_notes": "Self-contained single-file HTML tool (no server). NOT YET migrated to a C:\\ project root — still under Downloads. Migration to QI standard layout pending.",
        "integrates_with": [],
        "exposes_to_ecosystem": ["Digitization cost comparison / scenario modelling (standalone)"],
        "consumes_from_ecosystem": []
    },
}

reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
existing_ids = {p.get("id") for p in reg["projects"] if isinstance(p, dict)}
added = []
for pid, entry in REG_NEW.items():
    if pid in existing_ids:
        print(f"  registry: {pid} already present — skip")
        continue
    reg["projects"].append(entry)
    added.append(pid)
if added:
    REGISTRY.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"  registry: added {added or 'nothing'} (now {len(reg['projects'])} projects)")

# ── 2. Brain DB ───────────────────────────────────────────────────────────────
# projects: project_id, display_name, tagline, path, api_port, ui_port, tier, active, created_at
PROJECTS = [
    ("lotterywiz",  "LotteryWiz",            "Fantasy 5 covering-design app (FastAPI on 8777)",
        r"C:\APPS\Lottery Wiz", 8777, 8777, "project", 1, TS),
    ("cypherminer", "CypherMiner",           "Local-first bilingual (EN/PT) offline crypto/encoding/math/text tools suite",
        r"C:\APPS\CypherMiner", 8502, 7842, "project", 1, TS),
    ("digitization","Digitization Cost Tool","Client-side HTML cost-comparison tool for Document Imaging & Services",
        r"C:\Users\renne\Downloads\DIGITIZATION COSTS", None, None, "project", 1, TS),
]

# project_state: project_id, agent_id, phase, status, summary, blockers, next_steps, recorded_at
STATE = [
    ("lotterywiz", "claude", "v1 — live + public",   "active",
     "Fantasy 5 covering-design app live on :8777 as QI_LotteryWiz; public Cloudflare tunnel QI_LotteryWizTunnel installed as a persistent service 2026-06-15.",
     None, "Add to nightly reconcile maps; consider git init + GitHub; named tunnel once domain is live.", TS),
    ("cypherminer", "claude", "Phase 1 — frontend + tunnel live", "active",
     "Bilingual offline tools suite. Static frontend served on :7842 (QI_CypherMinerUI), API on :8502, public tunnel QI_CypherMinerTunnel live (2026-06-15). Registered in ecosystem registry; now registered in Brain.",
     "API service on 8502 not yet a persistent NSSM service.",
     "Stand up a persistent API service for 8502; wire /health,/version,/info; git first commit.", TS),
    ("digitization", "claude", "v1 — tool + docs delivered", "active",
     "BU Digitization Cost Comparison Tool (client-side HTML) built with technical documentation and user guide (2026-06-15). Lives under Downloads\\DIGITIZATION COSTS.",
     "Not migrated to a C:\\ project root; no git; outside QI standard layout.",
     "Migrate to C:\\ project folder per QI standards; git init; decide if it needs hosting/tunnel.", TS),
]

# session_log: project_id, agent_id, session_title, summary, decisions_made, features_logged, files_changed, next_steps, model_used, started_at, ended_at
SESSIONS = [
    ("lotterywiz","claude","LotteryWiz — service + public tunnel",
     "Installed QI_LotteryWiz app service and QI_LotteryWizTunnel Cloudflare tunnel; verified public URL reachable.",
     0,0,"[]","",  "opus-4.8","2026-06-15 08:00:00","2026-06-15 08:30:00"),
    ("lotterywiz","claude","LotteryWiz — Fantasy 5 covering-design app",
     "Built FastAPI Fantasy 5 covering-design generator with .xlsx/.csv export; run/install/restart batch scripts.",
     0,0,"[]","",  "opus-4.8","2026-06-13 11:00:00","2026-06-14 15:30:00"),
    ("cypherminer","claude","CypherMiner — frontend build + public tunnel",
     "Static frontend (frontend/dist) served via QI_CypherMinerUI on 7842; QI_CypherMinerTunnel installed; public URL verified.",
     0,0,"[]","",  "opus-4.8","2026-06-15 09:00:00","2026-06-15 18:00:00"),
    ("cypherminer","claude","CypherMiner — initial scaffold (API + UI)",
     "Scaffolded bilingual offline tools suite: FastAPI API (8502) + Gradio/static UI (7842), config/data/secrets layout.",
     0,0,"[]","",  "opus-4.8","2026-06-14 20:58:00","2026-06-14 23:00:00"),
    ("digitization","claude","Digitization Cost Tool — tool + documentation",
     "Produced the BU Digitization Cost Comparison Tool (single-file HTML) plus Technical Documentation and User Guide (.docx) and a comparison PDF.",
     0,0,"[]","",  "opus-4.8","2026-06-12 18:00:00","2026-06-15 17:00:00"),
]

con = sqlite3.connect(DB)
cur = con.cursor()

have = {r[0] for r in cur.execute("SELECT project_id FROM projects")}
for row in PROJECTS:
    if row[0] in have:
        print(f"  brain.projects: {row[0]} already present — skip")
        continue
    cur.execute("INSERT INTO projects (project_id,display_name,tagline,path,api_port,ui_port,tier,active,created_at) VALUES (?,?,?,?,?,?,?,?,?)", row)
    print(f"  brain.projects: added {row[0]}")

# project_state — add latest state if none exists for that project at this timestamp
for row in STATE:
    pid = row[0]
    dup = cur.execute("SELECT 1 FROM project_state WHERE project_id=? AND recorded_at=?", (pid, row[7])).fetchone()
    if dup:
        print(f"  brain.project_state: {pid} @ {row[7]} exists — skip"); continue
    cur.execute("INSERT INTO project_state (project_id,agent_id,phase,status,summary,blockers,next_steps,recorded_at) VALUES (?,?,?,?,?,?,?,?)", row)
    print(f"  brain.project_state: added {pid}")

# session_log — dedup on (project_id, session_title)
for row in SESSIONS:
    pid, title = row[0], row[2]
    dup = cur.execute("SELECT 1 FROM session_log WHERE project_id=? AND session_title=?", (pid, title)).fetchone()
    if dup:
        print(f"  brain.session_log: '{title}' exists — skip"); continue
    cur.execute("INSERT INTO session_log (project_id,agent_id,session_title,summary,decisions_made,features_logged,files_changed,next_steps,model_used,started_at,ended_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)", row)
    print(f"  brain.session_log: added '{title}'")

con.commit()
print("\n  Brain projects now:", cur.execute("SELECT COUNT(*) FROM projects").fetchone()[0])
con.close()
print("DONE.")

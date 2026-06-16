# -*- coding: utf-8 -*-
"""Register AvatarStudio into the Hive (registry + Brain DB). Idempotent."""
import json, sqlite3
from pathlib import Path

REG = Path(r"C:\QIH\ecosystem\qi_registry.json")
DB  = r"C:\QIH\data\qi_brain.db"
TS  = "2026-06-15 19:45:00"
PID = "avatarstudio"
PATH = r"C:\1-AI\APPS\AvatarStudio"

# 1) Registry (UI-only Gradio app, port 7862)
reg = json.loads(REG.read_text(encoding="utf-8"))
if PID not in {p.get("id") for p in reg["projects"]}:
    reg["projects"].append({
        "id": PID,
        "name": "AvatarStudio",
        "description": "QI Avatar Studio — Gradio pipeline that turns a script into a talking-head avatar video (TTS via Kokoro/edge-tts → background removal → Hallo2/LivePortrait render in WSL2 → video-retalking lip-sync → MP4). Multi-language.",
        "path": PATH,
        "github": "TBD",
        "status": "active",
        "primary_language": "Python",
        "ports": {"ui": {"current": 7862, "block": "7840-7869",
                         "notes": "Pre-registry Gradio port. Works; keep per migration_note."}},
        "family_tier": "sibling",
        "family_notes": "Media-generation studio. Depends on WSL2 for avatar render backends. Shares the avatar/voice vision used across QI agents.",
        "integrates_with": [],
        "exposes_to_ecosystem": ["Talking-head avatar video generation (Gradio UI :7862)"],
        "consumes_from_ecosystem": []
    })
    REG.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")
    print("registry: added avatarstudio")
else:
    print("registry: already present")

# 2) Brain DB
con = sqlite3.connect(DB); cur = con.cursor()
if not cur.execute("SELECT 1 FROM projects WHERE project_id=?", (PID,)).fetchone():
    cur.execute("INSERT INTO projects (project_id,display_name,tagline,path,api_port,ui_port,tier,active,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (PID, "AvatarStudio", "Script -> voice -> talking-head avatar MP4 (Gradio, WSL2 render backends)",
         PATH, None, 7862, "project", 1, TS))
    print("brain.projects: added")
else:
    print("brain.projects: already present")

if not cur.execute("SELECT 1 FROM project_state WHERE project_id=? AND recorded_at=?", (PID, TS)).fetchone():
    cur.execute("INSERT INTO project_state (project_id,agent_id,phase,status,summary,blockers,next_steps,recorded_at) VALUES (?,?,?,?,?,?,?,?)",
        (PID, "claude", "v1 - Gradio studio operational", "active",
         "Talking-head avatar video pipeline (TTS -> background removal -> Hallo2/LivePortrait render in WSL2 "
         "-> retalking -> MP4). Gradio UI on 7862. Multi-language TTS. Now registered in registry + Brain.",
         "No git repo; D-ID API key stored in plaintext in studio_config.json (must move to secrets/ + rotate); "
         "render backends require WSL2 + conda envs.",
         "git init + .gitignore (exclude .venv, outputs, secrets); move D-ID key to secrets/ and rotate it; "
         "decide if it needs an NSSM autostart service + tunnel.", TS))
    print("brain.project_state: added")

for title, summ, start, end in [
    ("AvatarStudio - talking-head avatar pipeline build",
     "Built the QI Avatar Studio: Gradio app (avatar_studio.py, :7862), multi-language TTS (Kokoro/edge-tts), "
     "scene pipeline, Hallo2 + video-retalking render scripts (WSL2), language routing and tests.",
     "2026-05-16 09:00:00", "2026-05-19 17:18:00"),
]:
    if not cur.execute("SELECT 1 FROM session_log WHERE project_id=? AND session_title=?", (PID, title)).fetchone():
        cur.execute("INSERT INTO session_log (project_id,agent_id,session_title,summary,decisions_made,features_logged,files_changed,next_steps,model_used,started_at,ended_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (PID, "claude", title, summ, 0, 0, "[]", "", "unknown", start, end))
        print("brain.session_log: added")

con.commit()
print("brain projects total:", cur.execute("SELECT COUNT(*) FROM projects").fetchone()[0])
con.close()
print("DONE")

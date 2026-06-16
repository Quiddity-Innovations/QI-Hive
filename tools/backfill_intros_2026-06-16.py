# -*- coding: utf-8 -*-
"""Backfill the standard INTRO 6-file set for the 9 projects missing it."""
import sys, json, sqlite3
sys.path.insert(0, r"C:\QIH\ecosystem")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from qi_intro import make_intro, is_compliant

reg = json.load(open(r"C:\QIH\ecosystem\qi_registry.json", encoding="utf-8"))
by_id = {p["id"]: p for p in reg["projects"]}

con = sqlite3.connect(r"C:\QIH\data\qi_brain.db")
def brain_state(pid):
    r = con.execute("SELECT phase,status,summary,next_steps FROM project_state WHERE project_id=? ORDER BY recorded_at DESC LIMIT 1", (pid,)).fetchone()
    return {"phase": r[0], "status": r[1], "summary": r[2], "next_steps": r[3]} if r else {}

# Per-project KNOWN content (techstack + dev features) for richer pages.
def dev(cat, feats): return [{"category": cat, "features": feats}]
def f(name, detail, status="live", file=""): return {"name": name, "file": file, "status": status, "detail": detail}

KNOWN = {
 "fidelityanalyzer": {
   "techstack": {"table": [
     {"layer":"API","technology":"FastAPI","role":"REST endpoints /analyze,/rebalance,/target on :8504","license":"MIT","version":""},
     {"layer":"UI","technology":"Gradio","role":"Upload + result tables on :7844","license":"Apache-2.0","version":""},
     {"layer":"Engine","technology":"Python stdlib","role":"CSV parse, allocation, HHI concentration, rebalancing — no pandas","license":"PSF","version":"3.11"}],
     "descriptions":[{"title":"Single-process","body":"main.py runs API (8504) + UI (7844) together."}]},
   "features_dev": dev("Engine",[
     f("Fidelity CSV parser","Tolerant parse (skips disclaimer rows, $/%/() handling).",file="shared/analyzer.py"),
     f("Allocation + concentration","By asset class/account; top-5 weight + HHI rating."),
     f("Rebalancing","Trades vs target allocation (default 50/20/20/5/5, 5% drift).")]),
 },
 "cypherminer": {
   "techstack": {"table":[
     {"layer":"UI","technology":"Static frontend (dist)","role":"Served by QI_CypherMinerUI on :7842","license":"","version":""},
     {"layer":"API","technology":"FastAPI","role":"Tools API on :8502","license":"MIT","version":""}],
     "descriptions":[{"title":"Local-first","body":"Bilingual (EN/PT) offline crypto/encoding/math/text tools."}]},
   "features_dev": dev("Surface",[f("Static frontend","frontend/dist served on 7842",file="frontend/dist"),
     f("API","FastAPI on 8502",status="live")]),
 },
 "tubescout": {
   "techstack":{"table":[{"layer":"API/Page","technology":"FastAPI + uvicorn","role":"News page + API on :8503","license":"MIT","version":""}],
     "descriptions":[{"title":"Pipeline","body":"YouTube subscriptions -> NEXUS summaries -> authed news page; feeds Kaze + Brain."}]},
   "features_dev": dev("Pipeline",[f("Subscription ingest","Pulls YouTube subs."),f("NEXUS summaries","Summarizes via NEXUS chain."),f("News page","Token-gated page on 8503.")]),
 },
 "lotterywiz": {
   "techstack":{"table":[{"layer":"App","technology":"FastAPI","role":"Fantasy 5 covering-design generator on :8777","license":"MIT","version":""}],
     "descriptions":[{"title":"Exports","body":"Play-set export to .xlsx/.csv."}]},
   "features_dev": dev("App",[f("Covering-design engine","Generates optimal Fantasy 5 play sets."),f("Export","xlsx/csv export API.")]),
 },
 "m2v": {
   "techstack":{"table":[{"layer":"API","technology":"FastAPI","role":":8501","license":"MIT","version":""},
     {"layer":"UI","technology":"Gradio","role":":7841","license":"Apache-2.0","version":""}],
     "descriptions":[{"title":"Music to Video","body":"Runs from its own .venv (main.py)."}]},
   "features_dev": dev("Engine",[f("Audio analyzer","engine/audio_analyzer.py"),f("Lyric analyzer","engine/lyric_analyzer.py")]),
 },
 "personalsong": {
   "techstack":{"table":[{"layer":"Web","technology":"FastAPI (serve.py)","role":"App on :8088 from isolated .venv","license":"MIT","version":""},
     {"layer":"Model","technology":"ACE-Step","role":"Local AI song generation (sung vocals).","license":"","version":""},
     {"layer":"Voice","technology":"Demucs / Seed-VC","role":"Voice clone.","license":"","version":""}],
     "descriptions":[{"title":"Local free generator","body":"think:false + name-injection; cu128/FFmpeg gotchas."}]},
   "features_dev": dev("Pipeline",[f("Song generation","ACE-Step sung vocals."),f("Voice clone","Demucs/Seed-VC.")]),
 },
 "avatarstudio": {
   "techstack":{"table":[{"layer":"UI","technology":"Gradio","role":"Studio on :7862 (own .venv, avatar_studio.py)","license":"Apache-2.0","version":""},
     {"layer":"Render","technology":"Hallo2 / LivePortrait (WSL2)","role":"Talking-head render backends.","license":"","version":""},
     {"layer":"Voice","technology":"Kokoro / edge-tts","role":"Multi-language TTS.","license":"","version":""}],
     "descriptions":[{"title":"Pipeline","body":"Script -> TTS -> background removal -> avatar render (WSL2) -> retalking -> MP4."}]},
   "features_dev": dev("Pipeline",[f("TTS","Kokoro/edge-tts multi-language."),f("Avatar render","Hallo2/LivePortrait in WSL2."),f("Lip-sync","video-retalking.")]),
 },
 "digitization": {
   "techstack":{"table":[{"layer":"App","technology":"Single-file HTML/JS","role":"Client-side cost calculator (no server).","license":"","version":""}],
     "descriptions":[{"title":"Standalone","body":"BU Digitization Cost Comparison Tool for Document Imaging & Services. Lives under Downloads; migration to a C:\\ root pending."}]},
   "features_dev": dev("Tool",[f("Cost comparison","Client-side HTML calculator."),f("Docs","Technical doc + user guide produced.")]),
 },
 "claude_manager": {
   "techstack":{"table":[{"layer":"Tooling","technology":"Python","role":"Ecosystem reconciliation, Brain backfills, registration tooling.","license":"PSF","version":"3.11"}],
     "descriptions":[{"title":"Meta workspace","body":"Operates ON the ecosystem (no served ports)."}]},
   "features_dev": dev("Tooling",[f("Reconciliation scripts","C:\\QIH\\tools\\*"),f("Brain backfills","Project/session registration.")]),
 },
}

MISSING = ["m2v","personalsong","cypherminer","lotterywiz","digitization","tubescout","fidelityanalyzer","avatarstudio","claude_manager"]
for pid in MISSING:
    proj = by_id.get(pid)
    if not proj:
        print(f"  {pid}: not in registry — skip"); continue
    d, written = make_intro(proj, brain=brain_state(pid), known=KNOWN.get(pid))
    ok = "✓ compliant" if is_compliant(proj) else "STILL INCOMPLETE"
    print(f"  {pid:16} -> {d}  ({len(written)} files)  {ok}")
con.close()
print("DONE")

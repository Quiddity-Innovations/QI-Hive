# -*- coding: utf-8 -*-
"""Registry hygiene for the Hive audit:
   1. Remove the duplicate 'digicost' (orphan of 'digitization', not in Brain).
   2. Backfill paths.logs for every project that has a real log dir on disk
      (fixes the Logs tab hiding ~16 projects).
"""
import json
from pathlib import Path

P = Path(r"C:\QIH\ecosystem\qi_registry.json")
d = json.loads(P.read_text(encoding="utf-8"))

# 1) drop digicost duplicate
before = len(d["projects"])
d["projects"] = [p for p in d["projects"] if p.get("id") != "digicost"]
print(f"removed digicost: {before} -> {len(d['projects'])}")

# 2) candidate log dirs per project id (first existing wins)
CANDIDATES = {
    "maia": [r"C:\APPS\QI\LOGS"],
    "naya": [r"C:\APPS\NAYA\LOGS"],
    "nexus": [r"C:\APPS\NEXUS\LOGS"],
    "openclaw": [r"C:\APPS\OC\LOGS"],
    "mq": [r"C:\APPS\MQ\LOGS", r"C:\APPS\MQ\data\logs"],
    "qi_brain": [r"C:\QIH\engine\brain\LOGS"],
    "qi_hive": [r"C:\QIH\engine\hive\dashboard\LOGS", r"C:\QIH\logs"],
    "autopdf": [r"C:\APPS\AutoPDF\Application\LOGS", r"C:\APPS\AutoPDF\LOGS"],
    "cognibase": [r"C:\APPS\CogniBase\LOGS", r"C:\APPS\CogniBase\data\logs"],
    "mapsnap": [r"C:\APPS\MapSnap\LOGS", r"C:\APPS\MapSnap\data\logs"],
    "m2v": [r"C:\APPS\M2V\logs", r"C:\APPS\M2V\data\logs"],
    "personalsong": [r"C:\APPS\PersonalSong\logs", r"C:\APPS\PersonalSong\LOGS"],
    "cypherminer": [r"C:\APPS\CypherMiner\LOGS", r"C:\APPS\CypherMiner\logs"],
    "lotterywiz": [r"C:\APPS\Lottery Wiz\LOGS"],
    "tubescout": [r"C:\APPS\TUBESCOUT\data\logs", r"C:\APPS\TUBESCOUT\logs"],
    "fidelityanalyzer": [r"C:\FidelityAnalyzer\logs", r"C:\FidelityAnalyzer\data\logs"],
    "avatarstudio": [r"C:\1-AI\APPS\AvatarStudio\logs"],
    "claude_manager": [r"C:\APPS\CLAUDE\logs", r"C:\APPS\CLAUDE\LOGS"],
    "filehq": [r"C:\APPS\NAYA\filehq\LOGS"],
}

filled, skipped = [], []
for p in d["projects"]:
    pid = p.get("id")
    cands = CANDIDATES.get(pid, [])
    chosen = next((c for c in cands if Path(c).is_dir()), None)
    if chosen:
        paths = p.get("paths") if isinstance(p.get("paths"), dict) else {}
        if paths.get("logs") != chosen:
            paths["logs"] = chosen
            p["paths"] = paths
            filled.append(f"{pid} -> {chosen}")
    else:
        if cands:
            skipped.append(f"{pid} (no dir exists: {cands})")

P.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
print("\nbackfilled logs:")
for f in filled: print("  ", f)
print("\nno log dir found (left unset):")
for s in skipped: print("  ", s)
print(f"\nregistry now {len(d['projects'])} projects")

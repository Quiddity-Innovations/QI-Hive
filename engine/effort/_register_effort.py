#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Register the Effort Ledger as a QI Hive subsystem in qi_registry.json.

Additive only: adds a sub_systems key and a scheduled_tasks entry under the
existing qi_hive project. Allocates no port and touches no other project, so
sibling projects cannot be affected. Backs up before writing and re-validates.
"""
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REG = Path(r"C:\QIH\ecosystem\qi_registry.json")
BAK = REG.with_suffix(f".json.bak-{datetime.now():%Y%m%d_%H%M%S}")

before = REG.read_bytes()
shutil.copy2(REG, BAK)
print(f"backup: {BAK}")

reg = json.loads(before.decode("utf-8"))
hive = next(p for p in reg["projects"] if p.get("id") == "qi_hive")

hive.setdefault("sub_systems", {})["effort"] = (
    r"C:\QIH\engine\effort - effort ledger: forensic hours/token tracking "
    r"per project (SQLite + hash-chained daily ledger); surfaced at "
    r"/effort and /api/effort on the dashboard"
)
tasks = hive.setdefault("scheduled_tasks", [])
if not any(t.get("name") == "QI_EffortLedger_Daily" for t in tasks):
    tasks.append({
        "name": "QI_EffortLedger_Daily",
        "schedule": "daily 23:50",
        "command": r"C:\QIH\engine\effort\EffortLedger_Daily.bat",
        "purpose": "incremental effort collection + sealed ledger entry",
        "log": r"C:\QIH\logs\effort_ledger_task.log",
    })

REG.write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n",
               encoding="utf-8")

# Re-validate: must parse, and no project may have been lost or renamed.
after = json.loads(REG.read_text(encoding="utf-8"))
ids_before = [p.get("id") for p in json.loads(before.decode("utf-8"))["projects"]]
ids_after = [p.get("id") for p in after["projects"]]
assert ids_before == ids_after, "project list changed - aborting"
print(f"validated: {len(ids_after)} projects intact, JSON parses")
print("effort subsystem:", next(
    p for p in after["projects"] if p["id"] == "qi_hive")["sub_systems"]["effort"][:60] + "...")

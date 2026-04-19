# -*- coding: utf-8 -*-
"""Add missing projects to data/status.json (EasyFlow, FileHQ).
Also marks Claude_Manager as 'retired' now that QI_Hive replaces it."""
import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

STATUS = Path(r"C:\QIH\data\status.json")
s = json.loads(STATUS.read_text(encoding='utf-8'))

s['projects']['EasyFlow'] = {
    "path": "C:\\EasyFlow",
    "status": "active_development",
    "current_task": None,
    "locked_files": [],
    "last_activity": "2026-04-19",
    "notes": "EasyFlow — workflow automation. Port 8550. To migrate to C:\\QIP\\EasyFlow under QI Project Standard."
}

s['projects']['FileHQ'] = {
    "path": "C:\\FileHQ",
    "status": "active_development",
    "current_task": None,
    "locked_files": [],
    "last_activity": "2026-04-19",
    "notes": "FileHQ — file management hub. Port 8000. To migrate to C:\\QIP\\FileHQ under QI Project Standard."
}

# Claude_Manager is superseded
if 'Claude_Manager' in s['projects']:
    s['projects']['Claude_Manager']['status'] = 'retired'
    s['projects']['Claude_Manager']['notes'] = "Retired 2026-04-19 — replaced by QI_Hive. Legacy NSSM service removed. Folder C:\\CLAUDE pending archive + delete."

STATUS.write_text(json.dumps(s, indent=2, ensure_ascii=False), encoding='utf-8')
print(f"Updated {STATUS}")
print("Projects:", list(s['projects'].keys()))

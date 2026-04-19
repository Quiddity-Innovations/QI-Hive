# -*- coding: utf-8 -*-
import json, sys
sys.stdout.reconfigure(encoding='utf-8')

STATUS_SRC  = r"C:\CLAUDE\status.json"
STATUS_DEST = r"C:\QIH\hive\status.json"

with open(STATUS_SRC, encoding='utf-8') as f:
    s = json.load(f)

s['_meta']['last_updated'] = '2026-04-19T16:00:00'
s['_meta']['last_session'] = 'QIHive_Session_01_2026-04-19'

s['projects']['QI_Hive'] = {
    "path": "C:\\QIH",
    "status": "active_development",
    "current_task": None,
    "locked_files": [],
    "last_activity": "2026-04-19",
    "notes": "QI Hive created. Brain at C:\\QIH\\brain (port 9010), Dashboard at C:\\QIH\\hive (port 8600). GitHub: Quiddity-Innovations/QI-Hive. Run C:\\QIH\\update_services.bat as admin to complete NSSM migration."
}

s['projects']['Claude_Manager']['notes'] = "Superseded by QI Hive (C:\\QIH). Old code preserved at C:\\CLAUDE until NSSM migration confirmed."
s['projects']['Claude_Manager']['status'] = "migrating"

s['infrastructure']['dashboard']['note'] = "QI Hive Dashboard v3.0. New Hive page wired to QI Brain. Code at C:\\QIH\\hive\\Dashboard\\server.py. Still running from C:\\CLAUDE until admin runs update_services.bat."

s['infrastructure']['qi_brain'] = {
    "url": "http://localhost:9010",
    "status": "running_as_nssm_service",
    "note": "QI Brain — hive nervous system. Code at C:\\QIH\\brain. 12 MCP tools + 4 new growth loop endpoints. Still running from C:\\UNIVERSAL\\qi_brain until admin runs update_services.bat.",
    "endpoints": ["/api/agents", "/api/agent/{id}/profile", "/api/agent/growth", "/api/log_session", "/api/log_decision", "/api/ecosystem_snapshot"]
}

s['session_log'].append({
    "session": "QIHive_Session_01_2026-04-19",
    "doc": "TBD",
    "summary": "QI Hive created. C:\\QIH scaffolded. 7 hive agents + agent_growth_log table added to QI Brain DB. 4 growth loop API endpoints added. Dashboard rebranded v3.0 with /hive page + QI Brain client. health_check.py NSSM names fixed. Claude Manager migrated to C:\\QIH\\hive. GitHub: Quiddity-Innovations/QI-Hive. QI registry + service registry updated. Projects folder strategy agreed: C:\\QIP for projects, C:\\QIB for business (future)."
})

s['pending_actions'] = [
    "RUN AS ADMIN: C:\\QIH\\update_services.bat — redirects QI_BrainAPI and QI_Dashboard to new C:\\QIH paths",
    "Register QIH tools in Claude MCP settings (Brain growth loop available as MCP tools)",
    "First real agent growth log — have an agent complete a task and POST to /api/agent/growth",
    "Future: migrate projects to C:\\QIP one by one (Maia first)",
    "Future: rename C:\\QI to C:\\QIB after all projects moved to C:\\QIP",
]

for path in [STATUS_SRC, STATUS_DEST]:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(s, f, indent=2, ensure_ascii=False)
    print(f"Saved: {path}")

# -*- coding: utf-8 -*-
"""Add qi_brain to qi_registry.json as backbone tier."""
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

path = r'C:\UNIVERSAL\ECOSYSTEM\qi_registry.json'
d = json.load(open(path, encoding='utf-8'))

qi_brain_entry = {
    'id': 'qi_brain',
    'name': 'QI Brain',
    'description': 'Shared knowledge substrate for the QI ecosystem. SQLite + ChromaDB + 12-tool MCP server.',
    'path': r'C:\UNIVERSAL\qi_brain',
    'github': 'TBD',
    'status': 'active',
    'primary_language': 'Python',
    'tier': 'backbone',
    'ports': {
        'api': {'current': 9010, 'block': '9000-9099', 'notes': 'QI Orchestration block'},
        'mcp': {'current': 'stdio', 'block': 'N/A', 'notes': 'stdio MCP — no port'}
    },
    'family': 'orchestration',
    'services': ['QIBrainAPI'],
    'dependencies': [],
    'dependents': ['all projects via MCP'],
    'mcp_tools': [
        'qi.get_context', 'qi.log_decision', 'qi.log_feature',
        'qi.get_pending_features', 'qi.decide_on_feature',
        'qi.update_project_state', 'qi.search_memory',
        'qi.log_session', 'qi.get_ecosystem_snapshot',
        'qi.supersede_decision', 'qi.explain', 'qi.override_evaluation'
    ],
    'added': '2026-04-19'
}

existing_ids = [p.get('id') for p in d.get('projects', [])]
if 'qi_brain' not in existing_ids:
    d['projects'].append(qi_brain_entry)
    print('Added qi_brain to projects list')
else:
    print('qi_brain already in registry — updating')
    for i, p in enumerate(d['projects']):
        if p.get('id') == 'qi_brain':
            d['projects'][i] = qi_brain_entry
            break

# Update shared_infrastructure
si = d.get('shared_infrastructure', {})
si['qi_brain'] = r'C:\UNIVERSAL\qi_brain\qi_brain.db — shared knowledge DB (backbone tier, :9010)'
d['shared_infrastructure'] = si

with open(path, 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
print(f'qi_registry.json updated. Projects now: {len(d["projects"])}')
print('shared_infrastructure keys:', list(d["shared_infrastructure"].keys()))

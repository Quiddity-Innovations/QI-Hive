# -*- coding: utf-8 -*-
"""First Brain Call ceremony — log the founding session to the brain."""
import sys, asyncio, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'C:/UNIVERSAL/qi_brain')

import httpx

BRAIN = 'http://localhost:9011'

async def main():
    async with httpx.AsyncClient(timeout=30) as client:

        # Log the founding session
        r = await client.post(f'{BRAIN}/api/log_session', json={
            'project_id': 'qi_brain',
            'session_title': 'First Brain Call — QI Brain Born',
            'summary': (
                'QI Brain built from zero in a single session. '
                'Schema (11 tables, WAL mode), 5 LLM providers (qwen3:8b eval, nomic-embed-text), '
                'FastAPI :9010 with 14 endpoints, 12-tool MCP stdio server, '
                'Feature Propagation Engine with structured prompt contract, '
                'idempotent bootstrap (9 steps, 392 ecosystem docs in ChromaDB), '
                'QI Brain tab in QI Orchestrator dashboard (6 sub-tabs: Ecosystem, Decisions, '
                'Features, Memory Search, Providers, Config), '
                'NSSM service QIBrainAPI installed as LocalSystem, '
                'global MCP registration in .claude.json, '
                'qi_registry.json updated as backbone tier, '
                'CLAUDE.md updated with session-start/end brain protocol, '
                'Supplement A audit diffs locked (14 improvements).'
            ),
            'decisions_made': 5,
            'features_logged': 1,
            'files_changed': [
                r'C:\UNIVERSAL\qi_brain\core\schema.sql',
                r'C:\UNIVERSAL\qi_brain\core\db.py',
                r'C:\UNIVERSAL\qi_brain\core\memory_store.py',
                r'C:\UNIVERSAL\qi_brain\core\providers\base.py',
                r'C:\UNIVERSAL\qi_brain\core\providers\ollama.py',
                r'C:\UNIVERSAL\qi_brain\core\providers\nomic_embed.py',
                r'C:\UNIVERSAL\qi_brain\core\providers\factory.py',
                r'C:\UNIVERSAL\qi_brain\qi_brain_api.py',
                r'C:\UNIVERSAL\qi_brain\qi_brain_mcp.py',
                r'C:\UNIVERSAL\qi_brain\feature_engine.py',
                r'C:\UNIVERSAL\qi_brain\bootstrap.py',
                r'C:\UNIVERSAL\dashboard\static\index.html',
                r'C:\UNIVERSAL\dashboard\static\css\brain.css',
                r'C:\UNIVERSAL\dashboard\static\js\brain.js',
                r'C:\UNIVERSAL\ECOSYSTEM\qi_registry.json',
                r'C:\Users\renne\.claude\CLAUDE.md',
                r'C:\Users\renne\.claude.json',
            ],
            'next_steps': (
                'Run fix_services_localsystem.bat for MaiaBot/NEXUS/Naya. '
                'Python migration to C:\\Python311\\ on 2026-04-19. '
                'Register QIDashboardTunnel. '
                'Build nightly backup scheduler. '
                'Phase 6: run feature propagation on seeded decisions.'
            ),
            'model_used': 'claude-sonnet-4-6',
            'started_at': '2026-04-18T22:00:00',
        })
        d = r.json()
        print(f'Session logged: session_id={d.get("session_id")} ok={d.get("ok")}')

        # Log the explain test
        r2 = await client.post(f'{BRAIN}/api/explain', json={
            'subject_type': 'decision',
            'subject_id': 5
        })
        e = r2.json()
        print()
        print('=== EXPLAIN TEST (Decision #5) ===')
        print(e.get('markdown', 'No markdown returned'))

        # Final status
        r3 = await client.get(f'{BRAIN}/api/status')
        s = r3.json()
        print()
        print('=== FINAL BRAIN STATUS ===')
        print(f'  Active projects:  {s["active_projects"]}')
        print(f'  Active decisions: {s["active_decisions"]}')
        print(f'  Features logged:  {s["features_logged"]}')
        print(f'  Sessions logged:  {s["sessions_logged"]}')
        print(f'  Providers active: {s["providers_active"]}')
        print(f'  ChromaDB docs:    {s["chroma_counts"]}')

asyncio.run(main())

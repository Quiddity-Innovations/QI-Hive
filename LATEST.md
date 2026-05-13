# QI Hive — LATEST

_Auto-generated: 2026-05-13 02:30:02 (nightly reconciler)_

| Project | Phase | Status | Sessions | Last |
|---|---|---|---|---|
| autopdf | Phase 2c - Smart Mapping + Template Apply | active | 1 | 2026-04-29 23:46:00 |
| cognibase | Phase B core complete - pilot ready | active | 20 | 2026-05-11 18:57:00 |
| easyflow | v1.2.x tester feedback cycle - blocked | blocked | 83 | 2026-04-19T00:00:00 |
| filehq | Retired - merged into Naya | retired | 0 | — |
| maia | Phase 4 - production on :8001 + Gradio :7860 (newly registered) | active | 1 | 2026-04-13T09:09:00 |
| mapsnap | Active stable - schema browser | active | 4 | 2026-05-07 08:20:10 |
| mq | Phase 0 - Scaffolding, blocked on Meta credentials | blocked | 0 | — |
| naya | Phase 3 - Bot service on :8002, UI on :7861 | active | 2 | 2026-04-13T09:09:00 |
| nexus | Phase 2 - Service on :8010/:7880, NSSM-supervised | active | 0 | — |
| openclaw | Adjacent - Kaze daily news agent (WSL) | active_external | 1 | 2026-04-13T09:09:00 |
| qi_brain | Phase 5 - Verification + Reconciliation pass | active | 4 | 2026-04-19T11:35:00 |
| qi_hive | Phase 2 - Dashboard live but ingest gap | active | 5 | 2026-04-22 22:00:00 |
| universal | Phase 0 - MIGRATING into C:/QIH | migrating | 21 | 2026-04-19T11:22:00 |

## Per-project

### autopdf
- **Phase:** Phase 2c - Smart Mapping + Template Apply
- **Status:** active
- **Summary:** PDF toolkit on :6969. Local-only, no cloud. Smart Mapping AI via Ollama. Last summary 2026-05-01.
- **Next:** No active dev. Resume when triggered.

### cognibase
- **Phase:** Phase B core complete - pilot ready
- **Status:** active
- **Summary:** OnBase mirror + AI correlation. M18 + M25-minimal + Portability shipped. 50/50 tests passing. 7+ session summaries logged 2026-05-06 to 2026-05-07.
- **Next:** Pilot prep. Discovery+Bridges next.

### easyflow
- **Phase:** v1.2.x tester feedback cycle - blocked
- **Status:** blocked
- **Summary:** EasyFlow Chrome Extension v1.2.1 shipped. All Phase A/B/C features done. Tester package distributed.
- **Next:** Awaiting tester feedback. Then v1.3 scope: BYOK + in-tandem AI.

### filehq
- **Phase:** Retired - merged into Naya
- **Status:** retired
- **Summary:** FileHQ retired. Capabilities absorbed into Naya.
- **Next:** Archive only.

### maia
- **Phase:** Phase 4 - production on :8001 + Gradio :7860 (newly registered)
- **Status:** active
- **Summary:** Maia bot service running. QI_MaiaGradio NSSM service registered 2026-05-09. Multi-channel webhooks live.
- **Next:** RAG via ChromaDB. Multi-bot template engine. Migrate webhooks from Quick Tunnel to named tunnel once domain is purchased.

### mapsnap
- **Phase:** Active stable - schema browser
- **Status:** active
- **Summary:** Jenzabar schema browser running on :9876. Generic core shipped 2026-05-07. Tunnel install pending.
- **Next:** Run install_tunnel_service.bat as admin to register QI_MapSnapTunnel.

### mq
- **Phase:** Phase 0 - Scaffolding, blocked on Meta credentials
- **Status:** blocked
- **Summary:** MQ public persona platform reserved on :8500/:7840. No services running.
- **Next:** Awaiting Facebook Page approval + Meta Developer credentials.

### naya
- **Phase:** Phase 3 - Bot service on :8002, UI on :7861
- **Status:** active
- **Summary:** Naya bot + Gradio UI both live, LAN-only. Telegram long-poll active.
- **Next:** Avatar + voice integration.

### nexus
- **Phase:** Phase 2 - Service on :8010/:7880, NSSM-supervised
- **Status:** active
- **Summary:** NEXUS multi-AI orchestration backbone. 7 providers wired. Scout digest live.
- **Next:** Weekend installer test (carried since Meeting 05). First candidate to migrate to cloud VPS.

### openclaw
- **Phase:** Adjacent - Kaze daily news agent (WSL)
- **Status:** active_external
- **Summary:** OpenClaw QI-adjacent. Kaze runs daily news digest in WSL Ubuntu-24.04.
- **Next:** No QI integration expected.

### qi_brain
- **Phase:** Phase 5 - Verification + Reconciliation pass
- **Status:** active
- **Summary:** Brain API on :9010. 392 docs in ChromaDB. Reconciliation pass 2026-05-09 backfilled missing sessions and registered cognibase/mapsnap/autopdf.
- **Next:** Tighten Stop-hook coverage. Add scheduled compliance check.

### qi_hive
- **Phase:** Phase 2 - Dashboard live but ingest gap
- **Status:** active
- **Summary:** Hive Dashboard :8600 + Brain :9010 running. Polling alive (5,271 polls). Reconciliation pass run 2026-05-09 to backfill missed sessions.
- **Next:** Fix per-project hooks for cognibase/mapsnap/autopdf/mq/openclaw. Add scheduled reconciler as safety net. Schedule gen_latest.py hourly.

### universal
- **Phase:** Phase 0 - MIGRATING into C:/QIH
- **Status:** migrating
- **Summary:** C:/UNIVERSAL is slated to be absorbed into C:/QIH and deleted from disk. Current occupants: qi_brain service (:9010), old dashboard service (:9000), ECOSYSTEM registry, DOCUMENTATION/Session_Summaries, TRAINING, node_modules, and 8 QI_* services all reference C:/UNIVERSAL/dashboard/nssm.exe. Migration must be staged to avoid breaking any service.
- **Next:** Staged migration: 1) Documentation + Training + ECOSYSTEM (low risk). 2) Repoint services to C:/QIH/engine/bin/nssm.exe. 3) Relocate qi_brain. 4) Retire old dashboard (:9000). 5) Delete C:/UNIVERSAL.

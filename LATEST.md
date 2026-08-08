# QI Hive — LATEST

_Auto-generated: 2026-08-08 12:35:12 (nightly reconciler)_

| Project | Phase | Status | Sessions | Last |
|---|---|---|---|---|
| autopdf | Hardening + MCP integration | active | 55 | 2026-08-07 17:13:55 |
| avatarstudio | v1 — secured + backed up | active | 3 | 2026-06-16 16:10:00 |
| claude_manager | Operational | active | 52 | 2026-08-08 12:05:54 |
| claude_voice | Dual-brain routing + Hive/launcher registration | active | 11 | 2026-08-07 02:01:14 |
| cognibase | Pre-POC — Phase B core complete | active | 27 | 2026-07-29 12:23:08 |
| connector | v1.0 live | active_development | 1 | 2026-07-30 21:21:48 |
| cypherminer | Phase 1 — frontend + tunnel live | complete | 4 | 2026-06-16 11:29:45 |
| digitization | v1 — tool + docs delivered | complete | 3 | 2026-08-07 19:08:28 |
| easyflow | v1.2.x tester feedback cycle | blocked | 85 | 2026-05-22 15:24:39 |
| filehq | Retired — merged into Naya | retired | 0 | — |
| gamez | Correctness & data integrity (post-feature-complete) | active | 8 | 2026-06-29 21:42:14 |
| lotterywiz | v1 — live + public | active | 6 | 2026-06-17 21:30:15 |
| m2v | v0.1.0 — scaffold + first render | active | 6 | 2026-06-18 00:35:05 |
| maia | Phase 4 — production | active | 18 | 2026-07-30 14:49:16 |
| mapsnap | BU Edition ready to ship | active | 152 | 2026-08-07 13:33:09 |
| mq | Phase 0 — scaffold | new | 1 | 2026-04-06 12:00:00 |
| naya | Phase 3 — bot + UI live | paused | 5 | 2026-06-23 16:03:19 |
| nexus | Phase 2 — NSSM-supervised | active | 17 | 2026-08-07 15:35:36 |
| openclaw | Phase 2 — agent expansion | active | 26 | 2026-07-31 18:11:10 |
| personalsong | Working app | active | 11 | 2026-06-18 00:35:04 |
| playdeck | Feature build â€” subjects and cross-site subscriptions | active | 5 | 2026-08-08 14:48:55 |
| qi_brain | Phase 5 — operational | active | 4 | 2026-04-20 01:16:39 |
| qi_hive | Dashboard UX polish | active | 139 | 2026-08-05 04:53:27 |
| retirementanalyzer | v1 - engine + API + UI live | active | 7 | 2026-07-03 02:52:18 |
| tubescout | MVP + refinements complete | active | 12 | 2026-06-18 10:22:23 |
| universal | Migration into C:\QIH | merged | 21 | 2026-04-20 01:16:46 |

## Per-project

### autopdf
- **Phase:** Hardening + MCP integration
- **Status:** active
- **Summary:** Six weeks of accumulated work committed and pushed to GitHub (0a367e5, master) - the first commit since 2026-06-29. Three bodies of work landed together: (1) regex-library corruption root-caused to regression test 5*.10 and fixed durably with a server-side integrity guard on POST /api/regex-library-save plus a .prev generation backup; library reseeded to 30 built-ins. (2) MCP gateway - AutoPDF is an MCP server on 127.0.0.1:8701 running as QI_AutoPDFMCP, nine independently switchable tools, disabled tools never registered. (3) Settings reorganization - AI config split into its own "AI & Connections" section, every group given an explicit id. Regression suite is 28 PASS / 0 FAIL / 1 SKIP. Documentation regenerated (Technical Documentation, Technical Guide, User Guide, Test Guide, Cheatsheet) with the regex-library endpoints, the guard's rationale, and new test-guide rows 5*.11/5*.12. .gitignore corrected: live config/mcp_gateway.json now stays local (per-install, same rule as autopdf-settings.json) while the template ships, and Application/_register_mcp_service.ps1 was un-ignored - the _*.ps1 scratch rule had been swallowing a real deliverable. Version backup at _backups/2026-08-07_1527_before-commit-regexguard.
- **Next:** Apply the same integrity-guard pattern to the other whole-file replace endpoints (templates, presets, settings) - the regex library is unlikely to be the only store a bad round-trip can blank. Audit remaining regression tests for the GET -> rebuild -> POST shape. Resolve the docs generator collision: _make_all_docs.py and _make_docs.py both write AutoPDF_User_Guide.docx, so run order decides the content. Still open from earlier: code signing for AutoPDF.exe (CrowdStrike EDR blocker), dots.ocr engine evaluation, user-facing date-format picker.

### avatarstudio
- **Phase:** v1 — secured + backed up
- **Status:** active
- **Summary:** Gradio talking-head pipeline on :7862. D-ID API key moved out of studio_config.json into gitignored secrets/avatarstudio.env (loaded via env/secret overlay; stripped on save). Key purged from the AvatarStudio private GitHub repo (history rewritten). Now git-backed at Quiddity-Innovations/AvatarStudio.
- **Next:** Renne: rotate D-ID key at dashboard, paste new value into secrets/avatarstudio.env. Optional: install QI_AvatarStudio service (DEMAND_START) via the master installer.

### claude_manager
- **Phase:** Operational
- **Status:** active
- **Summary:** Ecosystem fully booted + reconciled 2026-06-10..12. Drift watchdog live. 3 new GitHub remotes synced nightly.
- **Next:** Named tunnels after domain purchase; monitor brain_drift checks

### claude_voice
- **Phase:** Dual-brain routing + Hive/launcher registration
- **Status:** active
- **Summary:** Root-caused a hallucination report: LINE/Telegram were answering from the local Ollama model impersonating Claude (it invented a meeting + wrong project list). Built brain.py â€” two named brains: 'Claude' (real, via claude_bridge) and 'Ronald' (local Ollama, renamed out of Claude + given an anti-hallucination prompt). Switchable by name in chat ('Claudeâ€¦' / 'Ronald, take a break') OR by config UI on :8720 (segmented toggle + hard-set lock that overrides voice commands). Wired into line_bot.py + telegram_bot.py; new QI_ClaudeVoiceControl service serves the UI. Fixed ffmpeg resolution for services (util.py) so voice notes work. Added a Claude Voice card to the QI Launchpad (C:\QIH\landing\index.html) with localhost addresses (Brain UI :8720, Meeting Room :8722) + LINE webhook hostname; updated qi_registry.json :8720 note. Default brain = Ronald (safe always-on; Claude/bridge only answers while a live session bridges).
- **Next:** Run install_service.bat once (UAC) to persist QI_ClaudeVoiceControl (:8720). Wire the dual-brain toggle into the voice loops (meeting_server.py :8722, realtime.py) â€” they still use the local brain only. Optionally add claudevoice to the Hive dashboard KNOWN_TUNNELS. Decide whether to enable the paid Anthropic backend for 24/7 'real Claude' on LINE/Telegram without a live session.

### cognibase
- **Phase:** Pre-POC — Phase B core complete
- **Status:** active
- **Summary:** M18 + M25-minimal + portability shipped, 50/50 tests passing. Runs as QI_CogniBase service :8650 + tunnel.
- **Next:** BU pilot preparation

### connector
- **Phase:** v1.0 live
- **Status:** active_development
- **Summary:** Remote MCP connector live at connector.quiddityinnovations.com (QI_ConnectorMCP :9030 + QI_ConnectorTunnel). 7 tools, dual auth, smoke-tested publicly.
- **Next:** Renne adds capability URL in claude.ai Settings->Connectors; then evaluate extra tools.

### cypherminer
- **Phase:** Phase 1 — frontend + tunnel live
- **Status:** complete
- **Summary:** Bilingual offline tools suite. Static frontend served on :7842 (QI_CypherMinerUI), API on :8502, public tunnel QI_CypherMinerTunnel live (2026-06-15). Registered in ecosystem registry; now registered in Brain.  Status corrected per owner (Renne) 2026-06-18 dashboard review.
- **Next:** Stand up a persistent API service for 8502; wire /health,/version,/info; git first commit.

### digitization
- **Phase:** v1 — tool + docs delivered
- **Status:** complete
- **Summary:** BU Digitization Cost Comparison Tool (client-side HTML) built with technical documentation and user guide (2026-06-15). Lives under Downloads\DIGITIZATION COSTS.  Status corrected per owner (Renne) 2026-06-18 dashboard review.
- **Next:** Migrate to C:\ project folder per QI standards; git init; decide if it needs hosting/tunnel.

### easyflow
- **Phase:** v1.2.x tester feedback cycle
- **Status:** blocked
- **Summary:** Pivoted to Chrome/Edge extension v1.2.1; tester package distributed. No local server anymore (old :8550 dashboard retired). MailBrain rename under assessment.
- **Next:** Decide on MailBrain rename; process tester feedback

### filehq
- **Phase:** Retired — merged into Naya
- **Status:** retired
- **Summary:** Capabilities absorbed into Naya (C:\NAYA\filehq). Original C:\FileHQ marked for deletion.
- **Next:** None

### gamez
- **Phase:** Correctness & data integrity (post-feature-complete)
- **Status:** active
- **Summary:** Feature set complete; this pass fixed AI-Analyst/Quant correctness: board grounding (no more deflection), survive-to-title precompute, the DEF/ATT line null bug (pos_group coarse labels) across all 48 WC teams, removal of the per-match-vs-title category error, and a server-side model-vs-market guard. Verified live on prod 8710; merged to main and pushed.
- **Next:** Optional: Teams-Eval card visual pass now that lines are real; consider extending the guard to single-team title answers if needed.

### lotterywiz
- **Phase:** v1 — live + public
- **Status:** active
- **Summary:** Fantasy 5 covering-design app live on :8777 as QI_LotteryWiz; public Cloudflare tunnel QI_LotteryWizTunnel installed as a persistent service 2026-06-15.
- **Next:** Add to nightly reconcile maps; consider git init + GitHub; named tunnel once domain is live.

### m2v
- **Phase:** v0.1.0 — scaffold + first render
- **Status:** active
- **Summary:** API :8501 live (/health ok). First test video produced (forro_anime_mv.mp4).
- **Next:** Define pipeline phases; wire to PersonalSong output

### maia
- **Phase:** Phase 4 — production
- **Status:** active
- **Summary:** Bot :8001 + Gradio :7860 + tunnels live under NSSM. Last code work 2026-05-15 (BP overrides, sibling filter, topic propagation, Cloudflare primary).
- **Next:** Multi-bot template engine + RAG (ChromaDB)

### mapsnap
- **Phase:** BU Edition ready to ship
- **Status:** active
- **Summary:** BU Edition finalized 2026-07-31: dist\MapSnap_BU_Edition_2026-07-31.zip â€” one kit, two modes (deploy.json). BU MCP gateway live as QI_MapSnapMCPBU :8652 (3 tools, table_data off), 4/4 acceptance vs main edition. IIS front door rehearsed with SSE streaming proven, machine reverted to local mode. SERVER_DEPLOY.md covers server promotion.
- **Next:** Rotate leaked OpenRouter key; BU-account claude mcp add + conversational 4-test rerun; table_data decision on main gateway; optional QIH gateway-code sync.

### mq
- **Phase:** Phase 0 — scaffold
- **Status:** new
- **Summary:** API scaffold runs on :8500 (/health ok). Started 2026-06-10 as part of full-ecosystem boot.  Status corrected per owner (Renne) 2026-06-18 dashboard review.
- **Next:** Obtain Meta credentials

### naya
- **Phase:** Phase 3 — bot + UI live
- **Status:** paused
- **Summary:** Bot :8002 + Gradio :7861 + tunnel, LAN-only, Telegram long-poll. Last code work 2026-05-15 (BP overrides, parse fix).  Status set to paused per owner (Renne) 2026-06-18.
- **Next:** FileHQ Phase 2 code absorption (pending Renne approval)

### nexus
- **Phase:** Phase 2 — NSSM-supervised
- **Status:** active
- **Summary:** API :8010 + UI :7880 + tunnel live. 7 providers wired, Scout digest live.
- **Next:** Fix chain routing; Judge/Bench Phase 2

### openclaw
- **Phase:** Phase 2 — agent expansion
- **Status:** active
- **Summary:** Agents live in WSL (Tasuke, Kaze, Yubin, Sentry, Asa, Koe, Kakei). Kaze Config API :8401. Keepalive service running.
- **Next:** NotebookLM connection re-evaluation; Maia action routing

### personalsong
- **Phase:** Working app
- **Status:** active
- **Summary:** Studio on :8088 (ACE-Step vocals + Demucs/Seed-VC clone). 4 session summaries 2026-06-05/06. Git repo initialized 2026-06-10.
- **Next:** Register tunnel/port block decision; continue feature work

### playdeck
- **Phase:** Feature build â€” subjects and cross-site subscriptions
- **Status:** active
- **Summary:** Subjects list plus a Subs tab that pulls new videos from every site the user is signed in to, filtered by subject. Eleven platforms mapped, YouTube first-class. Live on 127.0.0.1:8506 with Instagram and Reddit returning items.
- **Next:** Save a YouTube login via Settings, refresh the feed, load the subscribed-channel list, re-capture TikTok cookies.

### qi_brain
- **Phase:** Phase 5 — operational
- **Status:** active
- **Summary:** Brain API on :9011 (moved from 9010 on 2026-05-14 — Logitech G HUB squats 9010). SQLite + ChromaDB + 12 MCP tools. NSSM QI_BrainAPI running.
- **Next:** Self-logging discipline; ChromaDB doc refresh

### qi_hive
- **Phase:** Dashboard UX polish
- **Status:** active
- **Summary:** Dashboard home, /hive and LLM Usage redesigned to a calm Bento + status-table layout; Documentation Brain UI (search + Plex graph + split view + draggable resize). Fixed a Brain feedback loop where the poller re-ingested its own [auto:state_file] marker from status.json (qi_hive's state file = statu
- **Next:** None

### retirementanalyzer
- **Phase:** v1 - engine + API + UI live
- **Status:** active
- **Summary:** Scaffolded via qi_new_project.py (19/19 compliance). Built stdlib analysis engine (allocation, concentration/HHI, drift, rebalancing), FastAPI on 8504, Gradio UI on 7844, sample dataset. Verified /analyze on sample (11 positions, $210k). Registered in registry + Brain + dashboard.
- **Next:** Install QI_FidelityAnalyzer + QI_FidelityAnalyzerTunnel services; add PDF positions parsing; configurable target allocation in UI; first git commit + GitHub.

### tubescout
- **Phase:** MVP + refinements complete
- **Status:** active
- **Summary:** Overnight refinements done: page persists via no-admin Startup launcher (NSSM service wedged on SYSTEM account, corrected bat left); classification fixed (other 450->1 via YouTube topicCategories + ranking, new granular topics); cross-channel dedup live (10 dups->8 cross-covered, '+N also covered' on page); Whisper fallback built + verified (opt-in, off by default, live-stream guard); Brain test feature 304 removed. Page serving 353 deduped cards / 13 topics; 7am/7pm tasks Ready.
- **Next:** Optional: enable whisper.enabled for caption-less enrichment; run install_service_admin.bat as admin for real service+tunnel; narrow scout_export if Kaze gets too many YouTube items.

### universal
- **Phase:** Migration into C:\QIH
- **Status:** merged
- **Summary:** C:\UNIVERSAL absorbed into C:\QIH (2026-04-22). Folder slated for deletion.  Status corrected per owner (Renne) 2026-06-18 dashboard review.
- **Next:** Delete C:\UNIVERSAL after final verification

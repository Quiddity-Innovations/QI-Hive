# QI Hive — LATEST

_Auto-generated: 2026-08-18 00:33:35 (nightly reconciler)_

| Project | Phase | Status | Sessions | Last |
|---|---|---|---|---|
| autopdf | Hardening + MCP integration | active | 60 | 2026-08-17 11:56:15 |
| avatarstudio | v1 — secured + backed up | active | 3 | 2026-06-16 16:10:00 |
| claude_manager | Operational | active | 53 | 2026-08-09 15:20:35 |
| claude_voice | Dual-brain routing + Hive/launcher registration | active | 12 | 2026-08-07 02:01:14 |
| cognibase | Pre-POC — Phase B core complete | active | 29 | 2026-08-13 18:42:32 |
| comfyui | Active â€” media engine operational | active | 3 | 2026-08-17 23:27:35 |
| connector | v1.0 live | active_development | 1 | 2026-07-30 21:21:48 |
| cypherminer | Phase 1 — frontend + tunnel live | complete | 4 | 2026-06-16 11:29:45 |
| digitization | v1 — tool + docs delivered | complete | 4 | 2026-08-11 17:10:00 |
| easyflow | v1.2.x tester feedback cycle | blocked | 85 | 2026-05-22 15:24:39 |
| filehq | Retired — merged into Naya | retired | 0 | — |
| gamez | Correctness & data integrity (post-feature-complete) | active | 8 | 2026-06-29 21:42:14 |
| lotterywiz | Public demo â€” documented | active | 9 | 2026-08-16 20:53:09 |
| m2v | v0.1.0 — scaffold + first render | paused | 6 | 2026-06-18 00:35:05 |
| maia | Phase 4 — production | active | 23 | 2026-08-13 21:00:07 |
| mapsnap | OnBase DNA â€” Tier C dark-mask calibration | active | 179 | 2026-08-17 12:06:21 |
| mq | Phase 0 — scaffold | paused | 1 | 2026-04-06 12:00:00 |
| naya | Phase 3 — bot + UI live | paused | 5 | 2026-06-23 16:03:19 |
| nexus | Phase 2 — NSSM-supervised | active | 43 | 2026-08-11 19:00:00 |
| openclaw | Phase 2 — agent expansion | active | 65 | 2026-07-31 21:58:24 |
| personalsong | Working app | paused | 11 | 2026-06-18 00:35:04 |
| playdeck | Feature build â€” subjects and cross-site subscriptions | active | 5 | 2026-08-08 14:48:55 |
| qi_brain | Phase 5 — operational | active | 4 | 2026-04-20 01:16:39 |
| qi_hive | Dashboard UX polish | active | 197 | 2026-08-17 14:10:47 |
| retirementanalyzer | v1 - engine + API + UI live | active | 7 | 2026-07-03 02:52:18 |
| synvox | Phase 0 - Foundation (MatrAIx engine bootstrap) | active | 5 | 2026-08-17 23:51:33 |
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

### comfyui
- **Phase:** Active â€” media engine operational
- **Status:** active
- **Summary:** Local image/video generation engine on D:\AI, port 8189, driven by Claude via the qi-comfy MCP server and directly usable in its own web UI at http://127.0.0.1:8189.

14 workflows verified working: t2i_fast (Z-Image Turbo, ~8s), t2i_sdxl, t2i_lora (SDXL + nudify_xl_lite, the NSFW route), t2i_lora_sd15 (Realistic Vision 5.1 for the three SD 1.5 LoRAs), t2i_ideogram (only engine rendering legible text), i2i, describe2img (Gemma 4 in-graph captioning), t2v_minimax (DEFAULT video â€” 1344x768 WITH stereo audio, ~75s), t2v_wan, i2v_wan, plus video_enhance_av / video_enhance / video_smooth / video_upscale.

Generation is gated: Claude renders only on an explicit RENDER: or /comfy trigger, never inferred. SFW and NSFW both in scope; no real identifiable people, no minors.

Every workflow exists twice â€” API format for Claude, editor twins prefixed "QI - " in the ComfyUI sidebar for Renne. They are copies, not links.

Engine selection and defaults live in D:\AI\workflows\_video_backends.json. Docs: CLAUDE.md (rules), CHEATSHEET.md (daily), RENDER_TEMPLATES.md (5 worked examples doubling as a regression suite), HOW_TO_RUN_IT_YOURSELF.md (GUI steps).

Deliberately not integrated: in-graph Ollama/Cloudflare nodes (NEXUS covers both). Exposes POST /free for VRAM release, already consumed by voice_studio.
- **Next:** 1. Resolve the port conflict: 8189 sits inside Maia's 8100-8199 block. Either formalise 8180-8189 as a media/GPU carve-out, or migrate and update Start_ComfyUI.bat + qi_comfy_mcp.py COMFY_URL + voice_studio together. 2. Finish the ref2va NVFP4 download (11.67 GB) to enable MiniMax Reference-to-Video. 3. Decide whether to enable the MiniMax cloud API nodes (needs credits). 4. Optional third entry point: a Render.bat CLI. 5. No ControlNet models installed yet.

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
- **Phase:** Public demo â€” documented
- **Status:** active
- **Summary:** Live public demo at lottery.quiddityinnovations.com (any email gets a Cloudflare one-time code), now with a complete Quiddity Innovations documentation set: doc\README.md index, LotteryWiz_User_Guide.docx (16 sections, 23 screenshots, 4 recipes), feature-tour videos in both house voices (8.4/8.6 min, 24 scenes, + chapter segments), narration script, and five re-runnable scripts that regenerate everything from the live app.
- **Next:** Pick the house voice (Andrew or Ava); owner click-through of the demo login; share doc\README.md + guide with first guests; decide git vs shared storage for the ~15 MB videos; on approval remove Cloudflare Access and revert QI Gate to protected.

### m2v
- **Phase:** v0.1.0 — scaffold + first render
- **Status:** paused
- **Summary:** Marked paused by the 2026-08-17 audit — 60 days without a session. Silence is now intentional, so compliance stops filing session_freshness/brain_drift. Set back to 'active' on the next real session.
- **Next:** Resume when Renne picks the project back up.

### maia
- **Phase:** Phase 4 — production
- **Status:** active
- **Summary:** Bot :8001 + Gradio :7860 + tunnels live under NSSM. Last code work 2026-05-15 (BP overrides, sibling filter, topic propagation, Cloudflare primary).
- **Next:** Multi-bot template engine + RAG (ChromaDB)

### mapsnap
- **Phase:** OnBase DNA â€” Tier C dark-mask calibration
- **Status:** active
- **Summary:** OnBase DNA Program at 232 dark (type,bit) pairs, 136 reachable by one dialog, 96 needing write-probing; overall row coverage 80.3 percent over an 18-package corpus. action.flags2 is effectively closed (5 dark pairs, 99.8 percent). Audit workstream is current: AUDIT-REPORT-2026-08-11 fully triaged. Note Types and Scan Queues are 100 percent and published.
- **Next:** Locate the Located By sub-selector encoding; mine GOV25's new dark pairs; action.flags (64 reachable); ruletable.flags (6.8 percent row coverage vs 96 dark pairs). Register the OnBase DNA Program as its own project via qi_new_project.py.

### mq
- **Phase:** Phase 0 — scaffold
- **Status:** paused
- **Summary:** Marked paused by the 2026-08-17 audit — 133 days without a session; scaffold only. Silence is now intentional, so compliance stops filing session_freshness/brain_drift. Set back to 'active' on the next real session.
- **Next:** Resume when Renne picks the project back up.

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
- **Status:** paused
- **Summary:** Marked paused by the 2026-08-17 audit — 60 days without a session. Silence is now intentional, so compliance stops filing session_freshness/brain_drift. Set back to 'active' on the next real session.
- **Next:** Resume when Renne picks the project back up.

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

### synvox
- **Phase:** Phase 0 - Foundation (MatrAIx engine bootstrap)
- **Status:** active
- **Summary:** SynVox registered in the QI registry and bootstrapped on PowerSpec. Engine (MatrAIx, MIT) cloned to C:\APPS\SynVox\engine\matraix with a uv-managed Python 3.12 venv and all editable packages installed; Persona 1M dataset pulled locally. Remote operations are live: the QI Connector now carries a whitelisted executor (qi_list_scripts / qi_execute_script / qi_script_status), so the whole bootstrap re-runs from any device with qi_execute_script('setup-synvox'). Phase 0 is complete except its gate - the free Docker smoke test - because Docker Desktop is not installed on this machine.
- **Next:** 1) Install Docker Desktop (needs WSL2 + reboot) and run the free harbor smoke test - the Phase 0 gate, no API key required. 2) setx ANTHROPIC_API_KEY with the personal Quiddity Innovations key. 3) Write persona_explore.py - free pandas/Polars segment profiling over Persona 1M, no inference cost. 4) Email/Discord the MatrAIx team for written clarification of the Persona 1M license before any commercial redistribution. 5) Phase 1: draft task qi-survey_nexus-pricing-tiers, debug on 3-5 Haiku personas, then ~100-persona cohort on Sonnet (~$1-5).

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

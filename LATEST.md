# QI Hive — LATEST

_Auto-generated: 2026-09-09 09:38:55 (nightly reconciler)_

| Project | Phase | Status | Sessions | Last |
|---|---|---|---|---|
| akiyascout | Registered, no commits yet | paused | 0 | — |
| autopdf | Hardening + MCP integration | active | 60 | 2026-08-17 11:56:15 |
| avatarstudio | v1 — launcher repaired 2026-09-05 (orphaned venv); not yet an NSSM service | active | 6 | 2026-09-06 03:21:16 |
| baguapp | Prototype frozen 2026-09-08 (owner decision, CLAUDE.md §16) | paused | 2 | 2026-09-08 19:22:18 |
| baguapp_prod | Marco zero — spec + docs, no code yet | active | 0 | — |
| bakeoff | Eval rig — Hermes vs OpenClaw smoke 10/10 (2026-07-06) | complete | 0 | — |
| claude_manager | Trinity â€” both assistants live over MCP; 30-day trial running | active | 1016 | 2026-09-09 13:03:22 |
| claude_voice | Deliberately powered down 2026-08-20; auto-restore armed for 2026-09-19 | blocked | 40 | 2026-08-20 15:41:37 |
| cognibase | Pre-POC — Phase B core complete; feature-tour video delivered 2026-08-13 | active | 29 | 2026-08-13 18:42:32 |
| comfyui | Active â€” media engine operational | active | 5 | 2026-09-06 14:52:30 |
| connector | v1.0 live + dispatch executor tools (2026-08-16); docs behind code | active | 1 | 2026-07-30 21:21:48 |
| cypherminer | Phase 1 — frontend + tunnel live | complete | 4 | 2026-06-16 11:29:45 |
| digitization | v1 — tool + docs delivered | complete | 4 | 2026-08-11 17:10:00 |
| easyflow | v1.2.1 extension shipped; July QI LLM Hub mode added; fork to MailBrain | blocked | 85 | 2026-05-22 15:24:39 |
| filehq | Retired — merged into Naya | retired | 0 | — |
| filmforge | Completion plan defined 2026-08-27; core scene-split module built | active | 1 | 2026-08-11 04:04:31 |
| gamez | Correctness & data integrity (post-feature-complete) | active | 8 | 2026-06-29 21:42:14 |
| headroom | Promoted — QI_Headroom NSSM service live on :9020 fronting api.anthropic.com | active | 0 | — |
| lotterywiz | Public demo â€” documented | active | 9 | 2026-08-16 20:53:09 |
| m2v | v0.1.0 — scaffold + first render | paused | 6 | 2026-06-18 00:35:05 |
| maia | Phase 4 — production; AWS LINE relay + channel refactor live | active | 23 | 2026-08-13 21:00:07 |
| mailbrain | Phase 1 live (Chrome MV3 extension + Flask :8550 helper, manual-run) | active | 0 | — |
| mapsnap | Active stable — secret-reference migration done 2026-08-17; Unity API buttons pending verification | active | 187 | 2026-09-04 22:43:44 |
| mediastudio | Composition layer live over six generators | active | 72 | 2026-09-09 08:18:29 |
| mq | Phase 0 — scaffold | paused | 1 | 2026-04-06 12:00:00 |
| mythologies | Static site live | active | 5 | 2026-08-27 14:44:24 |
| naya | Phase 5 — capability behind OpenClaw (application retired 2026-08-28) | paused | 12 | 2026-08-28 08:07:21 |
| nexus | Phase 2 — NSSM-supervised; role under review after Trinity ruling | active | 43 | 2026-08-11 19:00:00 |
| noosorbis | v0.5.0 â€” complete; owner signed off | complete | 10 | 2026-08-26 15:28:47 |
| onbase_dna | Active knowledge program, no service/ports | active | 5 | 2026-08-22 17:49:08 |
| openclaw | Phase 2 â€” agent expansion (recovered + modernized) | active | 67 | 2026-08-27 15:52:00 |
| personalsong | Working app | paused | 11 | 2026-06-18 00:35:04 |
| playdeck | Feature build — subjects + subscriptions; live-broadcast fix shipped 2026-08-28 | active | 5 | 2026-08-08 14:48:55 |
| qi_brain | Phase 5 — operational (SQLite + ChromaDB + MCP, :9011) | active | 4 | 2026-04-20 01:16:39 |
| qi_hive | Observability hardening | active | 245 | 2026-09-09 00:35:02 |
| retirementanalyzer | v0.14 â€” Task 1 cleared; end-to-end walkthrough in progress | paused | 140 | 2026-09-06 00:03:30 |
| synvox | Phase 4 â€” evidence layer / reality check; monetisation deferred | active | 79 | 2026-09-09 09:30:16 |
| trinity | 30-day assistant trial → review 2026-10-16 | active | 1 | 2026-09-08 22:28:44 |
| tubescout | MVP + refinements; OAuth outage fixed 2026-08-27 (API-key sweep) | active | 12 | 2026-06-18 10:22:23 |
| universal | Retired — absorbed into C:\QIH 2026-04-22; C:\UNIVERSAL deleted | complete | 32 | 2026-09-02 13:47:29 |
| vlcdaemon | Working daemon, no repo until 2026-09-08 | active | 0 | — |
| voice_studio | Batch voice rendering active; test guide in docs/TESTING.md | active | 0 | — |

## Per-project

### akiyascout
- **Phase:** Registered, no commits yet
- **Status:** paused
- **Summary:** Japanese real estate (Akiya/Kominka) aggregation platform with a personalized Scout Engine. Per registry notes and CLAUDE.md, repo exists at C:\APPS\AkiyaScout with ports allocated (API 8505 / UI 7845) but zero commits as of 2026-09-08.
- **Next:** see project docs

### autopdf
- **Phase:** Hardening + MCP integration
- **Status:** active
- **Summary:** Six weeks of accumulated work committed and pushed to GitHub (0a367e5, master) - the first commit since 2026-06-29. Three bodies of work landed together: (1) regex-library corruption root-caused to regression test 5*.10 and fixed durably with a server-side integrity guard on POST /api/regex-library-save plus a .prev generation backup; library reseeded to 30 built-ins. (2) MCP gateway - AutoPDF is an MCP server on 127.0.0.1:8701 running as QI_AutoPDFMCP, nine independently switchable tools, disabled tools never registered. (3) Settings reorganization - AI config split into its own "AI & Connections" section, every group given an explicit id. Regression suite is 28 PASS / 0 FAIL / 1 SKIP. Documentation regenerated (Technical Documentation, Technical Guide, User Guide, Test Guide, Cheatsheet) with the regex-library endpoints, the guard's rationale, and new test-guide rows 5*.11/5*.12. .gitignore corrected: live config/mcp_gateway.json now stays local (per-install, same rule as autopdf-settings.json) while the template ships, and Application/_register_mcp_service.ps1 was un-ignored - the _*.ps1 scratch rule had been swallowing a real deliverable. Version backup at _backups/2026-08-07_1527_before-commit-regexguard.
- **Next:** Apply the same integrity-guard pattern to the other whole-file replace endpoints (templates, presets, settings) - the regex library is unlikely to be the only store a bad round-trip can blank. Audit remaining regression tests for the GET -> rebuild -> POST shape. Resolve the docs generator collision: _make_all_docs.py and _make_docs.py both write AutoPDF_User_Guide.docx, so run order decides the content. Still open from earlier: code signing for AutoPDF.exe (CrowdStrike EDR blocker), dots.ocr engine evaluation, user-facing date-format picker.

### avatarstudio
- **Phase:** v1 — launcher repaired 2026-09-05 (orphaned venv); not yet an NSSM service
- **Status:** active
- **Summary:** Backfilled 2026-09-09 from QI_Project_Status_Report_2026-09-09.docx (Claude Fable 5.1). The C:\1-AI to C:\APPS move had orphaned .venv (pyvenv.cfg pointed at a deleted python.exe) so run_studio.bat died silently for months. 2026-09-05 repointed the venv to C:\Program Files\Python311, verified 322 packages, added pre-flight + logging, verified :7862 returns 200. Not a service, so it does not survive reboot.
- **Next:** 1) Install + register QI_AvatarStudio as an NSSM service. 2) pip install pytest so tests/test_smoke.py runs. 3) Audit sibling C:\APPS projects for the same orphaned-venv pattern (started 2026-09-09). 4) Owner: confirm whether the D-ID key still needs rotation (open since June).

### baguapp
- **Phase:** Prototype frozen 2026-09-08 (owner decision, CLAUDE.md §16)
- **Status:** paused
- **Summary:** Prototype frozen by owner decision. Only numbered patches for use-blocking defects with owner approval. Successor: baguapp_prod. Live at baguapp.vercel.app.
- **Next:** No active work — successor is baguapp_prod.

### baguapp_prod
- **Phase:** Marco zero — spec + docs, no code yet
- **Status:** active
- **Summary:** Registered 2026-09-08. The real BaguApp product; inherits from the frozen prototype at C:\APPS\Baguapp. Mould for MilkWise.
- **Next:** Begin implementation from spec/docs.

### bakeoff
- **Phase:** Eval rig — Hermes vs OpenClaw smoke 10/10 (2026-07-06)
- **Status:** complete
- **Summary:** Registered 2026-09-08 (was unregistered). One-time eval rig, results archived.
- **Next:** None — complete.

### claude_manager
- **Phase:** Trinity â€” both assistants live over MCP; 30-day trial running
- **Status:** active
- **Summary:** 2026-09-08 evening, after Claude Code restart: qi_trinity_check.py --ping = overall PASS (Codex 0.153.4 logged in on ChatGPT Plus, 3 fresh mcp-servers, 0 on deleted binary; Gemini key accepted, 6/200 calls, gemini-3.6-flash; 2 Agent HR rows). Then Claude commanded Codex directly over MCP from the new session (gpt-5.6-luna, read-only, approval never): def_count=18 for qi_gemini_mcp.py, verified by grep = 18. Both Trinity legs now proven on the MCP path, which was the one failure in the previous session (stale 0.118.0 binary until restart). Trial clock starts 2026-09-08; review 2026-10-16.
- **Next:** Use Trinity on real work per the Â§3.1 rubric (Codex lunaâ†’terraâ†’sol; Gemini 3.6-flash, no sensitive data on the free tier). Log every assistant run to Agent HR project 'trinity'. Phase 3 next: register MailBrain + own repo + sweep 13 worktrees. Fix %APPDATA%\npm. Confirm which QI_TaskHealth (task vs service) is live.

### claude_voice
- **Phase:** Deliberately powered down 2026-08-20; auto-restore armed for 2026-09-19
- **Status:** blocked
- **Summary:** Backfilled 2026-09-09 from QI_Project_Status_Report_2026-09-09.docx (Claude Fable 5.1). 2026-08-20 root-caused why the stack would not stay off (global SessionStart hook re-armed the bridge in every project session). Built the VOICE_DISABLED kill switch, pinned the four QI_ClaudeVoice* services to demand-start, disabled meeting-room/bridge-health tasks, and scheduled QI_ClaudeVoiceRestore_20260919. QI_ClaudeVoiceControl :8720 STOPPED by design; claudevoice.quiddityinnovations.com returns 530 until restore.
- **Next:** On 2026-09-19: 1) confirm the restore task fired and the four services are RUNNING; 2) redesign the SessionStart hook to arm only inside this project; 3) fix Session-0 dashboard health reporting (LocalSystem zombie reads green); 4) Renne confirms the public LINE/Telegram bots may come back online.

### cognibase
- **Phase:** Pre-POC — Phase B core complete; feature-tour video delivered 2026-08-13
- **Status:** active
- **Summary:** Backfilled 2026-09-09 from QI_Project_Status_Report_2026-09-09.docx (Claude Fable 5.1). QI_CogniBase :8650 RUNNING. Last real code commit 2026-06-12 (secret env-var indirection). 2026-08-13 produced the Andrew/Ava feature-tour video (12.3–12.8 min) disclosing on screen that the product is design-only with no live OnBase connection. OnBase REST/Unity clients are still stubs against local fixtures.
- **Next:** 1) Owner decision: is a real BU pilot being pursued this quarter? 2) If yes: wire one live OnBase connector to replace fixture stubs (L, Opus). 3) Optional: vendor-neutral PUBLIC video cut; BU-only Configuration-chapter cut.

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
- **Phase:** v1.0 live + dispatch executor tools (2026-08-16); docs behind code
- **Status:** active
- **Summary:** Backfilled 2026-09-09 from QI_Project_Status_Report_2026-09-09.docx (Claude Fable 5.1). QI_ConnectorMCP :9030 and QI_ConnectorTunnel RUNNING, /health ok. Since the 07-30 summary: generic MapSnap/NEXUS/Maia/Naya tool sections (07-31 to 08-02) and dispatch executor tools qi_list_scripts / qi_execute_script / qi_script_status (08-16) — never documented in a session summary.
- **Next:** 1) Write the catch-up session summary for the 08-02/08-16 additions. 2) Confirm a GitHub remote exists. 3) Owner: confirm the capability URL is still active in claude.ai Connectors.

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
- **Phase:** v1.2.1 extension shipped; July QI LLM Hub mode added; fork to MailBrain
- **Status:** blocked
- **Summary:** Backfilled 2026-09-09 from QI_Project_Status_Report_2026-09-09.docx (Claude Fable 5.1). Last real feature commit 2026-07-02 (QI LLM Hub mode — hub-first chat + AI triage with fallback). Docs last refreshed 2026-05-13. MailBrain now exists as a separately registered successor (302 uncommitted files, committed 2026-09-09).
- **Next:** 1) Refresh Master Status Report / Implementation Log to reflect the July work. 2) Confirm whether tester feedback ever arrived. 3) Owner decision: freeze EasyFlow at v1.2.1 and continue in MailBrain, or keep both.

### filehq
- **Phase:** Retired — merged into Naya
- **Status:** retired
- **Summary:** Capabilities absorbed into Naya (C:\NAYA\filehq). Original C:\FileHQ marked for deletion.
- **Next:** None

### filmforge
- **Phase:** Completion plan defined 2026-08-27; core scene-split module built
- **Status:** active
- **Summary:** Long-form film orchestration (story to scenes to overnight GPU render). Per docs/ROADMAP.md (most recent doc, written 2026-08-27), most of the pipeline already exists -- Module B (script/shotlist.py) already outputs shot lists accepted by Media Studio's compose --dry-run.
- **Next:** see project docs

### gamez
- **Phase:** Correctness & data integrity (post-feature-complete)
- **Status:** active
- **Summary:** Feature set complete; this pass fixed AI-Analyst/Quant correctness: board grounding (no more deflection), survive-to-title precompute, the DEF/ATT line null bug (pos_group coarse labels) across all 48 WC teams, removal of the per-match-vs-title category error, and a server-side model-vs-market guard. Verified live on prod 8710; merged to main and pushed.
- **Next:** Optional: Teams-Eval card visual pass now that lines are real; consider extending the guard to single-team title answers if needed.

### headroom
- **Phase:** Promoted — QI_Headroom NSSM service live on :9020 fronting api.anthropic.com
- **Status:** active
- **Summary:** Backfilled 2026-09-09 from QI_Project_Status_Report_2026-09-09.docx (Claude Fable 5.1). Contrary to the registry ("pilot, not yet promoted"), QI_Headroom is SERVICE_RUNNING (headroom-proxy 0.32.1, ~3.6 days uptime on 2026-09-09) via Tools/headroom_env; upstream is https://api.anthropic.com, not Ollama as documented. Internal kompress backend reports unhealthy while overall status is healthy. Stale 2.0 GB headroom_env.old deleted 2026-09-09; venv untracked from git.
- **Next:** 1) Investigate the unhealthy kompress check — is compression working or bypassed? 2) Write a minimal README/docs so "see project docs" points somewhere. 3) Owner: confirm the Anthropic-upstream routing was intended; re-confirm Claude Code OAuth never routes through the proxy.

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
- **Phase:** Phase 4 — production; AWS LINE relay + channel refactor live
- **Status:** active
- **Summary:** Backfilled 2026-09-09 from QI_Project_Status_Report_2026-09-09.docx (Claude Fable 5.1). Bot :8001, Gradio, tunnel, QueueDrain all RUNNING under NSSM. Since June: AWS Lambda+SQS webhook relay (2026-07-30), channels/*.py split with replay tests, Meta signature verification, bcrypt auth, watchdog hardening, QI-RELAY collaborator channel (2026-08-19). Last real feature commits ~2026-08-05.
- **Next:** 1) QI-Relay: verify L2 drafting authenticates (qi_relay_draft.py --budget 0.40; Renne refreshes claude CLI login if needed); narrow peers.json; first real message to Urcil. 2) Multi-bot template engine + RAG (ChromaDB). 3) maia.db OpenRouter-key ACL tightening (MapSnap 08-17 sibling item).

### mailbrain
- **Phase:** Phase 1 live (Chrome MV3 extension + Flask :8550 helper, manual-run)
- **Status:** active
- **Summary:** Registered 2026-09-08. Clone of EasyFlow repo lineage — needs own repo (architecture plan Wave 0.9). 4-provider AI adapter (Gemini/OpenAI/Anthropic/Ollama).
- **Next:** Split into its own repo per Wave 0.9 plan.

### mapsnap
- **Phase:** Active stable — secret-reference migration done 2026-08-17; Unity API buttons pending verification
- **Status:** active
- **Summary:** Backfilled 2026-09-09 from QI_Project_Status_Report_2026-09-09.docx (Claude Fable 5.1). QI_MapSnap :9876 and QI_MapSnapMCP :8651 healthy. 2026-08-17 closed a live OpenRouter-key exposure (GET /api/settings served the key over the public tunnel): qi_secrets.py resolver, key moved to an ACL-locked env file, backups redacted. 2026-08-14 shipped login-race fix, 6 OnBase Unity common-elements collections, environment profiles, 39-table Setup Guide + installer. The previous "OnBase DNA Tier C" phase label belongs to project onbase_dna.
- **Next:** 1) Sign in and confirm the 6 new OnBase API buttons render. 2) Dry-run kit/setup_unity_api.ps1 against a fresh environment key. 3) Fix the 4 failing qi_validator checks (root CLAUDE.md, requirements.txt, docs naming). 4) Owner: three-way merge decision for D:\Dev\BU Edition (untouched since 2026-08-08).

### mediastudio
- **Phase:** Composition layer live over six generators
- **Status:** active
- **Summary:** Indexes assets from ComfyUI/Voice Studio/AvatarStudio/PersonalSong/M2V and turns shot lists into finished media, generating nothing itself. Per docs/INTERFACE.md (most recent doc), it adds the indexing + assembly step that was previously hand-rolled ffmpeg per generator.
- **Next:** see project docs

### mq
- **Phase:** Phase 0 — scaffold
- **Status:** paused
- **Summary:** Marked paused by the 2026-08-17 audit — 133 days without a session; scaffold only. Silence is now intentional, so compliance stops filing session_freshness/brain_drift. Set back to 'active' on the next real session.
- **Next:** Resume when Renne picks the project back up.

### mythologies
- **Phase:** Static site live
- **Status:** active
- **Summary:** Static site mapping 37 world mythologies (1,498 figures, 2,969 relationships) deployed to Vercel. Per CLAUDE.md, renders require an explicit RENDER: trigger from Renne and the aboriginal/arabian verticals remain held pending his framing sign-off.
- **Next:** see project docs

### naya
- **Phase:** Phase 5 — capability behind OpenClaw (application retired 2026-08-28)
- **Status:** paused
- **Summary:** Backfilled 2026-09-09 from QI_Project_Status_Report_2026-09-09.docx (Claude Fable 5.1). App layer (QI_NayaBot/Gradio/Tunnel) STOPPED, StartType Manual, deliberate. Engine lives on as QI_FileHQ :8200 + QI_NayaMCP :8250, both RUNNING and consumed by OpenClaw and Claude Desktop. naya_brain.db (4.15 GB) and filehq.db (2.63 GB) intact. Registry status corrected 2026-09-09 to paused.
- **Next:** 1) Owner: approve/reject enabling find / duplicate_group executor actions (unlocks >1 TB reclaim). 2) Build the enumerate-approve-execute duplicate flow once decided. 3) Resume index categorisation (~12% classified) during the GPU-free window. 4) Decide fate of naya_server.py / naya_gradio.py.

### nexus
- **Phase:** Phase 2 — NSSM-supervised; role under review after Trinity ruling
- **Status:** active
- **Summary:** Backfilled 2026-09-09 from QI_Project_Status_Report_2026-09-09.docx (Claude Fable 5.1). QI_NEXUS + QI_NexusMCP (:8310) + API :8010 all healthy. No feature work since the 2026-06-10 snapshot beyond an 08-11 feature-tour video. The 2026-09-08 Trinity decision takes NEXUS out of assistant orchestration (Claude + Codex MCP + Gemini MCP instead); provider routing and Scout digest still served.
- **Next:** 1) Confirm whether the Chain Routing Mode error (2026-05-26) still reproduces. 2) Create the four missing standard docs (Implementation Log, Meeting Minutes, Version History, Master Status Report). 3) After the 2026-10-16 Trinity review: Renne decides NEXUS forward role; update registry description/family_notes.

### noosorbis
- **Phase:** v0.5.0 â€” complete; owner signed off
- **Status:** complete
- **Summary:** Live at https://noosorbis.quiddityinnovations.com, commits e6a98da â†’ 66eee99, working tree clean, 203 tests green. Renne has confirmed he is happy with the final product and closed the session.

Front page rebuilt around the mark: no masthead on "/", one Ask-the-Librarian field, four dismissible panels with a restore bar, a Try shelf randomised each load from Wikipedia's featured feed, add-to-collection confirmation, and a mission statement set as a centred dedication spanning the page container.

Librarian has three modes across three engines, with provenance carried on every backend event and painted as a distinct colour, badge and footnote. "In the library" (local Ollama over Wikipedia passages) and "Its own knowledge" (Gemini 3.7 Flash, free tier) are live. "The whole internet" is built and tested but dark pending an EXA_API_KEY â€” it now runs on a search provider plus the local model rather than Google grounding, so it needs no billing and keeps the reader's question on the machine.

"What you asked" keeps every answer in the browser with the mode that produced it, and compares answers to the same question side by side â€” the site's central argument made visible rather than asserted.

secrets/ is hardened: one editable file, git ignores the folder wholesale, key lookup falls back across it. No billing account exists on any provider, so the public site cannot incur charges.
- **Next:** Two optional jobs, neither blocking and both Renne's to do. (1) Add EXA_API_KEY to C:\APPS\NoosOrbis\secrets\noosorbis.env and restart to light up "The whole internet" â€” free, no card, from https://dashboard.exa.ai; the mode reports itself off until then rather than failing after someone types. (2) Rotate the Gemini key, which appeared in a chat transcript during setup; git history is verified clean so this is precaution, and Google auto-revokes keys it detects as leaked.

No further development planned. If ever wanted: server-side answer history for cross-device comparison (deliberately browser-only today), diagrams from an article's own structured data rather than the disabled diffusion pipeline, deleting the three *_noosorbis_exception elevation-whitelist rules now the app runs from C:\APPS\NoosOrbis, and Cloudflare Access while gate mode is open.

### onbase_dna
- **Phase:** Active knowledge program, no service/ports
- **Status:** active
- **Summary:** Genotype-to-phenotype decoding of OnBase configuration for the DNA Codex. Per GOV25-DIALOG-TARGETS.md (most recent doc), current work is calibration dialog-trip targets for the GOV25 vertical, generated 2026-08-14 by _gov25_workorder.py.
- **Next:** see project docs

### openclaw
- **Phase:** Phase 2 â€” agent expansion (recovered + modernized)
- **Status:** active
- **Summary:** Fully recovered and modernized 2026-08-27. All SIX agents verified working: Kaze (digests fired unattended 18:00/18:05), Sentry, Asa, Kakei, Tasuke, and YUBIN. Service renamed to QI_OCKeepalive and proven broker-manageable (nssm restart via QI_Elevate returns status: ok); freshness alarm armed and logging "Kaze digest OK" every 30 min. OpenClaw upgraded 2026.4.26 -> 2026.6.34; gateway on loopback; MCP recovered from total failure via transport=streamable-http, giving Tasuke 38 tools. Memory on local nomic-embed-text (4/4 files). TOOLS.md truncation eliminated. CORRECTION LOGGED (decision 581): my earlier claim that Yubin was dead was WRONG â€” it logs to /home/hyosuke/.openclaw/logs/yubin-task.log, not runtime/logs/agents/yubin/, and ran successfully today at 16:22 and 17:59. Yubin is load-bearing (feeds Kakei, Sentry, Asa, Tasuke) and is the email half of the shared "Maia Quiddam" persona alongside Kaze. Do not retire it.
- **Next:** 1) RENNE (elevated): run C:\APPS\OC\tools\repoint_yubin_tasks.ps1 â€” OC-Yubin-Daily-8AM/-6PM are the last two OC tasks still on the dead /mnt/c/OC/ path; they work only via the C:\OC junction. 2) Broaden memory indexing beyond the 4 workspace files. 3) Build Koe voice (whisper.cpp + Kokoro-82M/Piper) as an OpenClaw channel plugin rather than migrating to Hermes. 4) Ecosystem-wide conhost --headless exit-code audit. DO NOT migrate the digests into OpenClaw cron â€” they are gateway-independent today, and the gateway is deliberately stopped 10h/day.

### personalsong
- **Phase:** Working app
- **Status:** paused
- **Summary:** Marked paused by the 2026-08-17 audit — 60 days without a session. Silence is now intentional, so compliance stops filing session_freshness/brain_drift. Set back to 'active' on the next real session.
- **Next:** Resume when Renne picks the project back up.

### playdeck
- **Phase:** Feature build — subjects + subscriptions; live-broadcast fix shipped 2026-08-28
- **Status:** active
- **Summary:** Backfilled 2026-09-09 from QI_Project_Status_Report_2026-09-09.docx (Claude Fable 5.1). QI_PlayDeck :8506 RUNNING (the only media-group service actually up). 2026-08-28 fixed HLS-manifest capture for non-flat yt-dlp entries and the live-broadcast 0% hang (pre-check + plain-English refusal + dismiss stuck rows). The fix ran live but sat uncommitted for 12 days; committed 2026-09-09.
- **Next:** 1) Live badge on browse cards before download. 2) --live-from-start as explicit opt-in. 3) Continue bedding in subjects + unified subscriptions.

### qi_brain
- **Phase:** Phase 5 — operational (SQLite + ChromaDB + MCP, :9011)
- **Status:** active
- **Summary:** Backfilled 2026-09-09 from QI_Project_Status_Report_2026-09-09.docx (Claude Fable 5.1). QI_BrainAPI :9011 healthy (version 002), 586 decisions / 2,265 sessions logged. Bookkeeping for Brain-as-a-project had stopped at 2026-06-10 because all Brain-touching work is logged under qi_hive/claude_manager.
- **Next:** 1) ChromaDB doc refresh (open since June). 2) Decide whether qi_brain is tracked separately or folded into qi_hive bookkeeping. 3) Add a TaskHealth rule flagging any project whose git activity is >14 days newer than its Brain project_state.

### qi_hive
- **Phase:** Observability hardening
- **Status:** active
- **Summary:** Scheduled-task health audit found 7 of 37 tasks silently dead; 8 of 9 remediation items completed and verified the same day (2026-08-27). QI_TaskHealth now monitors 22 tasks by output artifact every 30 min with Telegram alerting, replacing LastTaskResult and log-mtime as the health signals â€” both
- **Next:** None

### retirementanalyzer
- **Phase:** v0.14 â€” Task 1 cleared; end-to-end walkthrough in progress
- **Status:** paused
- **Summary:** 712 tests pass, everything pushed, tree clean. Tier conservative, figures signed 2026-08-27, one detector firing (property exemptions). A blank disposable clone runs at C:\APPS\RetirementAnalyzer-TEST on 17844/18504 for the walkthrough; two of its steps have been walked and produced four defects. Resuming Sunday 2026-08-30.
- **Next:** Start both apps (neither runs as a service), hard-refresh, finish docs/WALKTHROUGH.md from household A step 1, then delete the test copy. Then: her SSA statement, the spouse's annual contribution, the import-vs-rows decision, and sign-off on the three house-policy datasets.

### synvox
- **Phase:** Phase 4 â€” evidence layer / reality check; monetisation deferred
- **Status:** active
- **Summary:** Session 12 (continued). Owner deferred monetisation: SynVox charges nobody, it is an internal tool for Renne and Urcil, and only enough endpoint surface was to be reserved for a future pricing model. Done and closed â€” synvox/billing.py holds the contract with no implementation, four routes (GET /v1/billing/plans, /account, /usage, POST /v1/billing/subscribe) answer 501 capability_disabled, capability_flags.billing is False, and all four were verified live. Nothing had to be moved: SynVox never had customer-billing code, and the two things that wear the word "price" â€” the pre-run cost gate and the Van Westendorp/Gabor-Granger instruments â€” are not billing and are now asserted untouched. The hard part is recorded rather than solved: on the subscription lane SynVox cannot measure money at all, so billing.METERABLE marks runs/personas/inference-calls countable and provider cost and tokens not, so nobody designs a plan on a number that reads zero for subscription-lane customers.

Acting on that led into /v1/capabilities, where three statements had been false for four sessions: the reality_check flag said the matcher was not built after D1..D6 built it, the honesty block asserted a FIXED reality-check status (wrong shape for a per-verdict outcome), and the note â€” rendered on two UI screens â€” told users grade A was unreachable until a layer that had already shipped. All three were pinned by two tests and a route-walk check, which is why nobody noticed. Fixed, and an over-broad guard that asserted on a whole file while claiming to be about evidence routes was narrowed.

D6b then attempted a second coverage gap and closed none, on the evidence: GitHub release-download velocity (cumulative counts with no timestamps make "latest > previous" near-structural), Open Collective cancellations (updatedAt is dominated by the platform's own billing sweep â€” 40 of 146 in the 00:00 UTC hour, busiest minutes 00:03 on the 21st of five months), and share-shift measures (attention moving between products is not people moving). The generalisation is the deliverable: a count can be dominated by the system rather than the users it describes â€” three instances now â€” and the test is "would this number move if no user did anything?". The follow-up audit of every change producer found nothing else and is closed.

Suite 1202 -> 1219 passed / 0 failed; reality_coverage unchanged at 2 of 6 (deliberately); every gate PASS; end-to-end study graded 3/3 in 105s at $0; 11/11 mutations caught.
- **Next:** D6c: close a coverage gap or establish that none can be closed yet â€” read CLAUDE.md rule 2i first, three candidates are already measured and rejected and repeating them wastes the session. D1d: price_stance wants a `band` kind no source emits; decide on paper. NEW: audit the rest of /v1/capabilities for stale claims (three in one block were false for four sessions; capability_flags.web_ui reads False on an install serving a web UI). Also: surface a source's refusal rate, and settle what reality_check.sources means when a source produced only a refusal. Monetisation stays deferred â€” do not build plans, metering or payment; when it is time, read billing.py's docstring first, including its flag that "edition" reads like a price tier and is not one.

### trinity
- **Phase:** 30-day assistant trial → review 2026-10-16
- **Status:** active
- **Summary:** Claude (spearhead) + ChatGPT via codex mcp-server + Gemini via qi_gemini_mcp.py. Components documented in C:\QIH\trinity\README.md. No ports, no services, nothing unattended.
- **Next:** Review trial outcome 2026-10-16.

### tubescout
- **Phase:** MVP + refinements; OAuth outage fixed 2026-08-27 (API-key sweep)
- **Status:** active
- **Summary:** Backfilled 2026-09-09 from QI_Project_Status_Report_2026-09-09.docx (Claude Fable 5.1). QI_TubeScout :8503 and tunnel RUNNING; data\logs\cycle.log shows a full sweep completing 2026-09-09 07:08 (109 channels). The 2026-08-27 audit finding "dead 66 days on expired OAuth token" was fixed the same day: Google OAuth Testing mode caps refresh tokens at 7 days, so the daily sweep moved to a non-expiring API key and --login can recover a revoked token. Audit item closed 2026-09-09.
- **Next:** 1) Optional: Whisper fallback for caption-less enrichment. 2) Optional: admin-mode service reinstall (install_service_admin.bat). 3) Narrow scout_export if Kaze digest gets too many YouTube items.

### universal
- **Phase:** Retired — absorbed into C:\QIH 2026-04-22; C:\UNIVERSAL deleted
- **Status:** complete
- **Summary:** Backfilled 2026-09-09 from QI_Project_Status_Report_2026-09-09.docx (Claude Fable 5.1). C:\UNIVERSAL verified gone from disk on 2026-09-09; the "delete after final verification" next step recorded 2026-06-18 was completed but never written back. QI Launcher :8650 decommissioned 2026-06-15 in favour of Hive Dashboard :8600.
- **Next:** None — retired.

### vlcdaemon
- **Phase:** Working daemon, no repo until 2026-09-08
- **Status:** active
- **Summary:** git init done 2026-09-08 (local only, no remote yet — Wave 0.9).
- **Next:** Add remote repo when Wave 0.9 executes.

### voice_studio
- **Phase:** Batch voice rendering active; test guide in docs/TESTING.md
- **Status:** active
- **Summary:** Studio (batch) voice tier for VibeVoice 1.5B narration. Per docs/TESTING.md (most recent doc), Test 0 confirms 9 preset voices load OK (scope=internal) via VoiceStudio_Voices.bat.
- **Next:** see project docs

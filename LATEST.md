# QI Hive — LATEST

_Auto-generated: 2026-08-27 18:43:42 (nightly reconciler)_

| Project | Phase | Status | Sessions | Last |
|---|---|---|---|---|
| autopdf | Hardening + MCP integration | active | 60 | 2026-08-17 11:56:15 |
| avatarstudio | v1 — secured + backed up | active | 3 | 2026-06-16 16:10:00 |
| claude_manager | Operational | active | 710 | 2026-08-27 18:41:56 |
| claude_voice | Dual-brain routing + Hive/launcher registration | active | 40 | 2026-08-20 15:41:37 |
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
| mapsnap | OnBase DNA â€” Tier C dark-mask calibration | active | 185 | 2026-08-22 17:49:18 |
| mq | Phase 0 — scaffold | paused | 1 | 2026-04-06 12:00:00 |
| naya | Phase 4 â€” standalone application | paused | 10 | 2026-08-27 15:42:15 |
| nexus | Phase 2 — NSSM-supervised | active | 43 | 2026-08-11 19:00:00 |
| noosorbis | v0.5.0 â€” complete; owner signed off | complete | 10 | 2026-08-26 15:28:47 |
| openclaw | Phase 2 â€” agent expansion (recovered + modernized) | active | 67 | 2026-08-27 15:52:00 |
| personalsong | Working app | paused | 11 | 2026-06-18 00:35:04 |
| playdeck | Feature build â€” subjects and cross-site subscriptions | active | 5 | 2026-08-08 14:48:55 |
| qi_brain | Phase 5 — operational | active | 4 | 2026-04-20 01:16:39 |
| qi_hive | Observability hardening | active | 227 | 2026-08-27 19:06:18 |
| retirementanalyzer | v0.14 â€” Task 1 cleared; end-to-end walkthrough in progress | paused | 82 | 2026-08-27 20:18:18 |
| synvox | Phase 4 â€” evidence layer / reality check; monetisation deferred | active | 78 | 2026-08-26 12:43:55 |
| tubescout | MVP + refinements complete | active | 12 | 2026-06-18 10:22:23 |
| universal | Migration into C:\QIH | merged | 31 | 2026-08-26 14:39:51 |

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
- **Phase:** Phase 4 â€” standalone application
- **Status:** paused
- **Summary:** Naya is now a complete independent application (2026-08-22). Zero code or data reach-in to C:\APPS\QI: Maia's maia_db/maia_lang/maia_context vendored in-tree as naya_db_core/naya_lang/naya_context (deliberate fork), all 8 sys.path injections removed, peer-bridge relocated to C:\QIH\shared\bridge + C:\QIH\secrets. Fixed a real bug where naya_gradio.py was reading Maia's maia.db. Bot :8002 and Gradio :7861 verified HTTP 200 after restart via the QI_Elevate broker; error log empty.

Drive scanning is paused per owner: \Naya\scan_for_duplicates (daily 02:00 over C:/D:/E:/F:) disabled, and usb_auto_scan + usb_scan_at_night set false. Telegram 409 root-caused â€” a webhook is registered, so getUpdates 409s by design; poller backed off from every-15s to once daily at 07:00, and 166.9 MB of log spam cleared.

Status remains 'paused' (owner's standing decision from 2026-06-18) â€” this session was structural cleanup, not feature work.
- **Next:** 1) Decide Telegram delivery path â€” webhook (working) or poller (now a once-daily no-op); running both is what caused the 409 storm. 2) Review naya_brain.db at 4.07 GB now that duplicate scans are paused. 3) Naya's four standard docs (Implementation Log, Meeting Minutes, Version History, Master Status Report) are still missing. 4) Optional: point Maia at C:\QIH\shared\bridge as well, once its code freeze lifts.

### nexus
- **Phase:** Phase 2 — NSSM-supervised
- **Status:** active
- **Summary:** API :8010 + UI :7880 + tunnel live. 7 providers wired, Scout digest live.
- **Next:** Fix chain routing; Judge/Bench Phase 2

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

### openclaw
- **Phase:** Phase 2 â€” agent expansion (recovered + modernized)
- **Status:** active
- **Summary:** Fully recovered and modernized 2026-08-27. Kaze digests verified firing UNATTENDED at 18:00 and 18:05 through the repointed scheduled tasks (log paths confirm the new /mnt/c/APPS/OC/ path, not the junction fallback). Upgraded 2026.4.26 -> 2026.6.34, which regenerated a stale gateway unit (written by 2026.4.5) and cleared the memory-plugin failure. MCP recovered from total failure â€” root cause was a missing `transport` field causing a legacy SSE-first fallback (openclaw#72757); Tasuke now reaches 38 tools (qi-connector 29, qi-autopdf 5, qi-mapsnap 4). Memory search moved off a keyless OpenAI config to local nomic-embed-text (4/4 files, 10 chunks). TOOLS.md truncation eliminated (72,892/72,892 chars â€” the agent gating rulebook had been cut at ~line 470). Gateway moved to loopback. Found and disabled 3 hidden OpenClaw cron jobs with 36 consecutive errors each, all scheduled inside the GPU pause window. Kakei had 2 real non-path bugs (heredoc stealing stdin; unconditional success logging) â€” fixed. Sentry, Asa, Kakei all verified live. Decision: keep OpenClaw as the assistant â€” it is the only harness examined that supports LINE; build Koe voice inside it (whisper.cpp + Kokoro/Piper) rather than migrating to Hermes.
- **Next:** 1) RENNE (elevated, one run): powershell -ExecutionPolicy Bypass -File "C:\APPS\OC\tools\rename_keepalive_service.ps1" â€” renames to QI_OCKeepalive, updates 5 referencing files, arms the digest freshness alarm. 2) RENNE decision: schedule or retire Yubin (no output ever; cron job now disabled). 3) Broaden memory indexing beyond 4 workspace files. 4) Build Koe as an OC channel plugin. 5) Ecosystem-wide conhost --headless exit-code audit (separate session). DO NOT migrate the digests into OpenClaw cron â€” they are currently independent of the gateway, which is deliberately stopped 10h/day.

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

# QI Ecosystem — Major Audit & Review Plan

**Date:** 2026-07-31 · **Prepared by:** Claude (Claude Manager session) · **Owner:** Renne Santiago
**Scope:** Every registered QI project, product and tool (27 items), all 46 NSSM services, plus planned/not-started initiatives.
**Evidence base:** `qi_registry.json` (2026-07-31), `QI_Service_Registry.md`, QI Brain snapshot (688 sessions / 496 decisions), live NSSM status sweep + live HTTP health probes run 2026-07-31.

---

## 1. Executive Summary

- **46 NSSM services checked live: 44 RUNNING, 2 stopped.** QI_GamezQuantProxy is off by design (manual Hyde switch). **QI_AutoPDF is down unintentionally** — while its public tunnel is still up, so autopdf.quiddityinnovations.com is serving errors.
- **Live HTTP probes:** 19 apps answered healthy. **Down: AutoPDF (:6969), Retirement Analyzer (:8504), M2V (:8501), AkiyaScout (:8505), EasyFlow (:8550), MQ (:8500), PersonalSong (:8088)** — the last four are expected (on-demand tools or not-started projects); the first three are findings.
- **Portfolio shape:** 8 production/backbone systems, 4 BU/business-track products, 10 utilities and media tools, 5 paused/blocked projects needing a decision.
- **Top risks found:** (1) dead public URLs (AutoPDF, M2V) behind live tunnels; (2) QI_NayaTunnel running despite the registry rule "NEVER expose Naya"; (3) quiddam.com DNS zone still empty while QI_MQTunnel runs; (4) the Supervisor dashboard generator is broken — every project reports the identical "0 untracked, 7 modified" with an empty last-commit, so ecosystem git monitoring is currently blind; (5) 44 pending feature reviews accumulating in QI Brain.
- **Proposal:** one week of red-flag remediation, then an 8-week deep-dive rotation covering every project, layered on the automation that already exists (Sentry daily probes, QI_ClaudeSelfAudit monthly), settling into a weekly-ops / monthly-self-audit / quarterly-full-audit cadence.

---

## 2. Portfolio Scorecard (all 27 items)

| # | Project | Path | Tier | Registry status | Live today (2026-07-31) | Risk |
|---|---|---|---|---|---|---|
| 1 | Maia | C:\QI | Core | active_production | ✅ :8001 healthy; AWS relay draining | Low |
| 2 | NEXUS | C:\NEXUS | Backbone | active_development | ✅ :8010 healthy; MCP :8310 live | Low |
| 3 | QI Brain | C:\QIH\engine\brain | Backbone | active | ✅ :9011 healthy; 44 pending reviews | Medium |
| 4 | QI Hive / Dashboard | C:\QIH | Orchestration | active_development | ✅ :8600 healthy; supervisor report broken | Medium |
| 5 | QI Connector | C:\QIP\Connector | Backbone | active_development | ✅ :9030 healthy; public MCP | Medium (new+public) |
| 6 | OpenClaw | C:\OC (WSL) | Cousin | active_production | ✅ agents live; Kaze API/tunnel up | Low |
| 7 | Claude Voice | C:\CLAUDE\Claude Voice | Cousin | active_development | ✅ 4 services up; :8720 healthy | Low |
| 8 | Claude Manager | C:\CLAUDE | Backbone (meta) | active | ⚠️ git tree heavily dirty, uncommitted | Medium |
| 9 | MapSnap | C:\MapSnap | Standalone tool | active_stable | ✅ :9876 + MCP :8651/:8652 healthy | Low |
| 10 | CogniBase | C:\CogniBase | Standalone tool | pre_poc | ✅ :8650 healthy; publicly tunneled | Medium |
| 11 | AutoPDF | C:\AutoPDF | Tool | Active Dev (Ph 2c) | 🔴 service STOPPED, tunnel still up | High |
| 12 | Digitization Cost Tool | Downloads\DIGITIZATION COSTS | Sibling | complete | ➖ static tool; still in Downloads | Low |
| 13 | TubeScout | C:\TUBESCOUT | Cousin | active_development | ✅ :8503 healthy; AM/PM sweeps | Low |
| 14 | Gamez / WC2026 | C:\Gamez | Cousin | active | ✅ :8710 healthy; tournament ended | Low |
| 15 | LotteryWiz | C:\Lottery Wiz | Sibling | active | ✅ :8777 live + public | Low |
| 16 | CypherMiner | C:\CypherMiner | Sibling | complete | ✅ UI :7842 + tunnel live | Low |
| 17 | PlayDeck | C:\PlayDeck | Cousin | new | ✅ :8506 healthy | Low |
| 18 | M2V | C:\M2V | Cousin | new (v0.1) | 🔴 origin down, tunnel up → public 530 | High |
| 19 | PersonalSong Studio | C:\PersonalSong | Cousin | active_development | ➖ on-demand, not running (expected) | Low |
| 20 | AvatarStudio | C:\1-AI\APPS\AvatarStudio | Sibling | active (v1) | ➖ on-demand Gradio (expected) | Low |
| 21 | Retirement Analyzer | C:\Retirement Analyzer | Sibling | active (v1) | 🔴 :8504 down; known AppDirectory bug | Medium |
| 22 | Headroom | C:\CLAUDE\Tools | Backbone (pilot) | pilot | ✅ proxy :9020 healthy; adopt/drop TBD | Low |
| 23 | Naya | C:\NAYA | Sibling candidate | running_dev_paused | ✅ bot+UI up; ⚠️ tunnel violates own rule | Medium |
| 24 | EasyFlow | C:\EasyFlow | Standalone tool | blocked | ➖ not running; blocked since 2026-05-22 | Medium |
| 25 | MQ (Maia Quiddam) | C:\MQ | Cousin | new (Phase 0) | ➖ blocked on Meta; quiddam.com DNS empty | Medium |
| 26 | AkiyaScout | C:\AkiyaScout | Cousin | active_development | ➖ not running; cadence unclear | Low |
| 27 | FileHQ | C:\NAYA\filehq | Merged | merged_into_naya | ✅ engine ok; Phase 2 absorption pending | Low |

Legend: ✅ verified healthy today · 🔴 down when it should be up · ➖ down but expected (on-demand / blocked / static) · ⚠️ operational but with a finding.

---

## 3. Immediate Red Flags — fix in Week 1

1. **AutoPDF public URL is dead.** QI_AutoPDF is STOPPED while QI_AutoPDFTunnel runs. Likely tied to the known "double owner of :6969" conflict from the mobo-swap recovery notes. Action: resolve port owner, restart service, verify https://autopdf.quiddityinnovations.com, or stop the tunnel until fixed.
2. **M2V public URL returns 530.** M2V is a manual-launch app but its named tunnel auto-starts. Action: either give M2V an NSSM service (auto-start) or make QI_M2VTunnel demand-start.
3. **Retirement Analyzer down.** The QI_RetirementAnalyzer AppDirectory path bug flagged after the mobo swap was never fixed. Action: repair service config, decide auto-start vs on-demand.
4. **Naya tunnel contradiction.** Registry safety rule says "NEVER expose Naya via Cloudflare tunnel — Maia ONLY," yet QI_NayaTunnel is installed and RUNNING (naya.quiddityinnovations.com → :7861). Action: Renne decides — either retire the tunnel or amend the rule; today the docs and reality disagree, which is exactly what an audit must not leave standing.
5. **quiddam.com DNS zone is empty** (junk-record incident) while QI_MQTunnel runs for nothing. Action: rebuild the zone or stop the tunnel until MQ unblocks.
6. **Supervisor monitoring is blind.** DASHBOARD.md shows every project with identical "0 untracked, 7 modified" and blank last-commit — the git checker is reading one repo (almost certainly C:\CLAUDE) for all 26 projects. Action: fix `Dashboard/server.py` / supervisor cwd handling; until then, ecosystem git-drift monitoring produces false data.
7. **QI Brain review backlog:** 44 pending feature evaluations. Action: triage session (approve/reject/defer) so the feature pipeline stays meaningful.
8. **Claude Manager repo dirty:** large uncommitted restructure (old Agents/Skills deleted, new .claude/agents added). Action: commit or revert deliberately.

---

## 4. Project Evaluations

### Group A — Production core & backbone (review monthly, ops-swept weekly)

**Maia — flagship, Phase 4 production.** Healthy on :8001; the LINE webhook path was cut over to AWS (Lambda `qi-maia-webhook` → SQS FIFO → QI_MaiaQueueDrain) on 2026-07-30, so messages now survive machine downtime. Gradio UI + named tunnel live. Open: multi-bot template engine + RAG (ChromaDB) is the declared next milestone and hasn't started; the shared-Python-interpreter risk (one broken pip affects all services) still applies ecosystem-wide. Verify the AWS relay's queue metrics weekly for the first month.

**NEXUS — AI backbone.** Healthy on :8010; LLM Hub (`/v1`, OpenAI-compatible + Ollama shim) is live with Maia, Naya, Gamez and TubeScout on it; MCP gateway :8310 installed 2026-07-31. Open: ~10 tools remain "ready-to-flip" onto the Hub (EasyFlow, CogniBase, Retirement, M2V, PersonalSong, LotteryWiz, MQ, MapSnap, AutoPDF, Claude Voice); Grok provider still pending.

**QI Brain — knowledge substrate.** Healthy on :9011; 24 active projects, 688 sessions, 496 decisions, ChromaDB indexes populated (1,215 docs). Finding: 44 pending feature reviews is a governance backlog — the cross-project feature pipeline only works if verdicts are issued. Also several projects' Brain state is months stale (e.g. qi_brain itself last active 2026-04-20), so `update_project_state` discipline needs a refresh during each deep-dive week.

**QI Hive / Dashboard.** Healthy on :8600 with the full worker fleet running (Elevate, HiveIngest, HiveApply, InspectorDrain, Caddy). Findings: the Supervisor report generator is broken (Section 3.6); `QI_Ecosystem_Map.md` is stale (last updated 2026-04-19) while `qi_registry.json` is current — the two are supposed to stay in sync.

**QI Connector — public MCP front door.** Healthy on :9030, public at connector.quiddityinnovations.com, bearer/capability-URL auth. It is 1 day old and internet-exposed: schedule a 30-day security review (token rotation, access-log review, tool-surface check) in late August.

**OpenClaw — agent platform.** Production in WSL; Tasuke, Kaze, Yubin, Sentry live; Kaze config API (:8401) and news tunnel running. Open: the Hermes-vs-OpenClaw bakeoff full suite is still on Renne to run and decide; the native-MCP check is on the MCP-gateway backlog; Koe (voice) remains planned Phase 4.

**Claude Voice.** All four services running, control API healthy on :8720, hourly bridge health check and 8 AM meeting-room task in place. Claude CLI backend gives real-Claude answers at no API cost. Open roadmap (not started): LiveKit spine and the voice→Hive dispatch console.

**Claude Manager (this workspace).** Operationally fine but the git tree carries a large uncommitted restructure. As the workspace that audits everything else, it should itself be clean — commit the agent-file migration this week.

### Group B — BU / business track (review bi-weekly while BU is hot)

**MapSnap — most business-critical tool right now.** Stable and demo-ready; server :9876, MCP gateway :8651 and the new BU-Edition gateway :8652 all healthy; service-token auth added 2026-07-30. Blocked externally: awaiting the BU server to deploy the BU Edition against OnBase/Jenzabar. Keep warm; re-verify the BU kit end-to-end the week the server lands.

**CogniBase.** Honest status: pre-POC, despite a working server (:8650, 50/50 tests as of May). Finding: a pre-POC product is publicly tunneled (cognibase.quiddityinnovations.com) — decide whether that exposure is still wanted. Its future is tied to the BU strategy (governance layer over the systems-of-record federation); review alongside MapSnap.

**AutoPDF.** Phase 2c complete (templates v2, regex library, three-tier tests, real docx docs — the best-documented tool in the fleet). Today it is the fleet's one hard outage (Section 3.1). Phase 3 (QI Hive scheduler integration) not started. After the fix, it drops to quarterly review.

**Digitization Cost Tool.** Complete, delivered, client-side only. One debt: still lives under Downloads instead of a C:\ project root — fold the migration into BU week rather than leaving it as a permanent exception.

### Group C — Utilities & media (review quarterly once stable)

**TubeScout** — healthy, MVP + refinements complete, AM/PM scheduled sweeps feeding Kaze/NEXUS. No action beyond cadence checks.

**Gamez / WC2026** — healthy, but the World Cup ended 2026-07-19. The tool has served its purpose: schedule a post-tournament retro — archive it, or generalize the engine for future tournaments; decommission its tunnel if archived. Hyde side-service correctly off.

**LotteryWiz** — v1 live and public; steady state. **CypherMiner** — complete; UI + tunnel live; maintenance only. **PlayDeck** — two days old and running; active dev continues, keep loopback-only.

**M2V** — v0.1 scaffold; public URL currently dead (Section 3.2). **PersonalSong** — working app, on-demand by design; fine. **AvatarStudio** — v1 secured and backed up; it becomes central again when Phase N Stages 1–4 (avatars for the Hive agents) start.

**Retirement Analyzer** — v1 engine/API/UI shipped but currently down with a known service-config bug (Section 3.3). **AkiyaScout** — registered active_development but not running and quiet; confirm whether it's genuinely active or should be marked paused. **Headroom** — pilot healthy on :9020; the adopt-or-drop decision (promote to QI_Headroom NSSM service if token savings hold) should be made with data by end of August.

### Group D — Paused / blocked / decision-needed (one decision review, then semiannual)

**Naya** — services healthy and the daily update loop runs, but development is paused and the strategic decision is already made: Naya's future is a LOCAL file-management/system utility, excluded from cloud plans. The rework hasn't started. Plus the tunnel contradiction (Section 3.4). Decision week should produce: rework scope + tunnel verdict + whether FileHQ Phase 2 absorption happens as part of it.

**EasyFlow** — blocked in the v1.2.x tester-feedback cycle since 2026-05-22, with 163 logged decisions (the most-governed project in Brain — a lot of invested thinking is idling). Decision: chase testers and resume, or officially park with a written re-entry condition. Phase 2 (Outlook/Teams/Planner) and .exe packaging stay frozen until then.

**MQ (Maia Quiddam)** — Phase 0 scaffold, blocked externally on Facebook Page approval + Meta credentials; meanwhile quiddam.com has no DNS records and its tunnel burns quietly (Section 3.5). Decision: chase the Meta pipeline or freeze cleanly (stop tunnel, note re-entry trigger).

**FileHQ** — merged into Naya; only Phase 2 (physical code absorption) remains, pending Renne's approval; after that, retire the registry entry.

---

## 5. Not-Yet-Started / Planned Initiatives (tracked so they can't silently die)

| Initiative | Trigger / owner | Target review |
|---|---|---|
| BU server buildout + MapSnap BU + CogniBase-on-BU deployment | BU server delivery (external) | The week the server arrives |
| AWS day-0 hygiene + next edge projects | Credits expire ~2027-01 — clock is running | Week 2 (with Maia) |
| Maia multi-bot template engine + RAG (ChromaDB) | Declared next milestone | Week 2 scoping |
| Naya rework → local file utility | Decision made, work unstarted | Week 8 decision review |
| OpenClaw Koe (voice agent, Phase 4) | After Claude Voice bridge matures | Week 4 |
| Hermes vs OpenClaw bakeoff — full suite + verdict | Renne runs the suite | Week 4 |
| Phase N Avatar & Voice, Stages 1–4 (Stage 0 shipped) | Renne prioritization | Week 6 (with AvatarStudio) |
| Claude Voice LiveKit spine + voice→Hive dispatch console | Roadmap item | Week 4 |
| LLM Hub flips (~10 tools, one-URL changes) | Low effort, batchable | Week 2 |
| QI MCP Gateway rollout to remaining apps (+ OpenClaw/Hermes native-MCP check) | Standing directive | Week 3 |
| quiddam.com DNS zone rebuild | Prereq for MQ | Week 1 |
| EasyFlow Phase 2 (Outlook/Teams/Planner) + .exe packaging | Blocked on v1.2.x decision | Week 8 |
| AutoPDF Phase 3 (Hive scheduler integration) | After Week 1 fix | Quarterly |
| FileHQ Phase 2 code absorption into C:\NAYA | Renne approval | Week 8 |
| Digitization tool migration out of Downloads | Housekeeping | Week 5 |
| Per-product NSSM naming — verify the armed 2026-06-27 task actually ran | Unverified automation | Week 3 |
| Unified QI Platform merge | Long-term vision | Quarterly audits |

---

## 6. Proposed Audit & Review Schedule

### 6.1 Steady-state cadence (permanent)

| Layer | What | When | Mechanism |
|---|---|---|---|
| Daily | Service/tunnel liveness probes | Continuous | Already exists — Sentry + Hive dashboard health |
| Weekly | Ops sweep: 46 services, public URLs, queue depth (Maia SQS), disk/GPU | Monday morning | 15-min Claude session (or scheduled task) |
| Monthly | Automated self-audit + auto-fix + LINE notify | Last Friday 09:00 | Already exists — QI_ClaudeSelfAudit (fires today); extend its checklist with the public-URL probe from this audit |
| 8 weeks | Per-project deep-dive rotation | See 6.2 | One focused Claude+Renne session/week |
| Quarterly | Full ecosystem audit — refresh THIS document, re-probe everything, re-score | Late Oct 2026, late Jan 2027 | Claude, half-day |

### 6.2 Deep-dive rotation (one theme per week, every project covered)

| Week of | Theme | Projects / items |
|---|---|---|
| Aug 3 | Red-flag remediation + security & exposure | AutoPDF fix, M2V tunnel, Retirement service, Naya-tunnel verdict, quiddam DNS, tunnel/token inventory |
| Aug 10 | Core stack | Maia (AWS relay 1-week check, template-engine scoping), NEXUS (Hub flips batch, Grok) |
| Aug 17 | Brain & Hive infrastructure | 44-review triage, supervisor fix, ecosystem-map sync, NSSM naming-task verify, Caddy/Elevate check |
| Aug 24 | Agent layer | OpenClaw (bakeoff verdict, Koe scoping), Claude Voice (LiveKit scoping), Connector 30-day security review. Fri Aug 28 = monthly self-audit |
| Aug 31 | BU / business track | MapSnap + BU Edition end-to-end, CogniBase exposure decision, AutoPDF Phase 3 scoping, Digitization migration |
| Sep 7 | Media & creative | M2V, PersonalSong, AvatarStudio (+Phase N), PlayDeck, TubeScout |
| Sep 14 | Utilities | Gamez retro (archive vs generalize), LotteryWiz, CypherMiner, Retirement re-verify, AkiyaScout status truth-up, Headroom adopt/drop with data |
| Sep 21 | Strategy & decisions | Naya rework, EasyFlow resume/park, MQ go/freeze, FileHQ Phase 2, unified-platform roadmap, write Q4 plan |

Each deep-dive produces, per project: verified health, registry/Brain state refreshed (`qi.update_project_state`), risks logged, next actions with owners, and the review date stamped — so by Sep 25 every one of the 27 items has been touched, decided, or deliberately parked.

---

## 7. Why This Plan Makes Sense

1. **Risk-weighted, not alphabetical.** Internet-exposed and production systems (Maia's AWS path, the brand-new public Connector, all 16 named tunnels) get reviewed first and most often; loopback-only hobby tools get quarterly touches. The audit effort lands where a failure actually hurts.
2. **Fix before review.** Week 1 repairs the things this very audit found broken (dead public URLs, a rule-violating tunnel, blind monitoring). Auditing on top of known-broken telemetry would just produce fiction — the supervisor bug proves that the current "22 red" dashboard is noise, not signal.
3. **It builds on automation you already own instead of duplicating it.** Sentry does daily, QI_ClaudeSelfAudit does monthly — this plan slots a weekly human-grade sweep and an 8-week deep-dive rotation between them, and feeds one new check (public-URL probing) back into the existing self-audit so the worst finding-class (dead public URL behind a live tunnel) can never recur silently. That follows the standing "fix the systemic failure mode" rule.
4. **One mental model per session.** Weeks are grouped by theme (core, BU, media, utilities), so each session loads one context instead of thrashing across 27 projects — cheaper in time and tokens, and matches how the projects actually share infrastructure.
5. **Decisions are batched last, on purpose.** Naya, EasyFlow, MQ, FileHQ and Headroom don't need code — they need verdicts. Scheduling them in Week 8 means Renne decides with seven weeks of fresh data instead of gut feel, and every "paused" project exits the audit either revived or deliberately parked with a written re-entry trigger — no more silent zombies.
6. **Not-started work is on the books.** Section 5 gives every planned-but-unstarted initiative a named trigger and a review slot, so items like the AWS credit clock (hard expiry ~Jan 2027) or the BU server can't drift unnoticed.
7. **It's sustainable.** One focused session per week plus the existing automation. The quarterly refresh of this document is the flywheel: probe, score, fix, re-schedule.

---

*Companion files: this document at* `C:\QIH\shared\documentation\self_audits\QI_Ecosystem_Major_Audit_2026-07-31.md` *and the Word edition beside it.*

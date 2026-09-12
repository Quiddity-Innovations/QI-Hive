# QI Ecosystem — Assistant Onboarding (L1)

_Generated 2026-09-11 02:36:20 · qi_registry.json sha256[:12] = af112b6067ac_

## Who QI is

- Quiddity Innovations (QI) — owner Renne Santiago, sole developer + AI ambassador.
- 43 registered projects sharing one machine, ports, git, and a converging future.
- Two tiers (owner's ruling 2026-09-10, `QI_Standards.md` §1.1): `C:\APPS\<App>` is the app Renne runs **and** the development source - git lives there, sessions open there, services point there. `D:\Dev\<App>` is a plain clone of the same remote: a backup on a second disk and the source for installing elsewhere, never edited, no `.venv`. Nothing operational may name `D:\Dev`.
- Port blocks are per-project (e.g. Maia 8100-8199, NEXUS 8300-8399, QI Hive 9000-9099) —
  never pick an adjacent port; check `C:\QIH\ecosystem\qi_registry.json` `port_strategy`.
- `C:\QIH\ecosystem\qi_registry.json` is the single source of truth for ports, services,
  status and relationships across every project.

## The Six Laws (QI_Architecture_Principles.md)

- Law 1 — The Registry is the Source of Truth
- Law 2 — Every Module Must Honor the Contract
- Law 3 — Independence with Declared Dependencies
- Law 4 — API Contract First, Implementation Second
- Law 5 — One Registry, Always Current
- Law 6 — Owner Override and Best-Practice Surfacing

## Assistant non-negotiables

- Read-only, unless a worktree is explicitly named for you to work in.
- Never touch `C:\QIH\ecosystem`, any folder literally named `secrets`, NSSM services,
  ports, or `.claude.json`.
- Answer in the exact format the task requests.
- If you don't know something, say UNKNOWN — never guess.
- If a rule in this brief conflicts with the task, stop and say which rule conflicts.
- Assistants never call, route through, or depend on a QI application (NEXUS, Maia,
  OpenClaw…); apps are context, not tools — the only tools you may call are the MCP
  servers you were given (qi-registry, qi-brain).

## Project index

| id | path | status | phase | ports | purpose |
|---|---|---|---|---|---|
| filehq | C:\APPS\NAYA\filehq | merged_into_naya | - | api 8000 | File intelligence engine — MERGED into Naya (C:\APPS\NAYA\filehq\) |
| maia | C:\APPS\QI | active_production | - | api 8001 · ui 7860 | Multi-channel AI assistant platform (LINE, Telegram, Messenger, Instagram, WhatsApp) |
| naya | C:\APPS\NAYA | paused | - | api 8002 · ui 7861 | Personal AI assistant for Renne — AI/physics/programming/networking domains + file scanni… |
| nexus | C:\APPS\NEXUS | active_development | - | api 8010 · ui 7880 · mcp 8310 | Neural Exchange and Unified Synthesis — AI orchestration backbone for all QI projects |
| openclaw | C:\APPS\OC | active_production | - | gateway 18789 | Autonomous AI agent platform — Tasuke-orchestrated (Renne talks only to Tasuke) |
| mq | C:\APPS\MQ | paused | - | api 8500 · ui 7840 | Maia Quiddam — autonomous AI social media persona for Facebook, Instagram, WhatsApp |
| easyflow | C:\APPS\EasyFlow | blocked | - | dashboard 8550 | Email organization tool — tier-based inbox management with Gmail API + Apps Script automa… |
| universal | C:\QIH | merged | - | — | Universal tools and dashboards shared across all QI projects — QI Launcher, cross-project… |
| qi_brain | C:\QIH\engine\brain | active | - | api 9011 · mcp stdio | Shared knowledge substrate for the QI ecosystem |
| qi_hive | C:\QIH | active_development | - | dashboard 8600 | Unified agent orchestration and knowledge system — QI Brain + Dashboard + 7 hive agents |
| autopdf | C:\APPS\AutoPDF | Active Dev | 2c | http 6969 · mcp 8701 | Self-contained PDF toolkit: convert / split / extract / catalog |
| cognibase | C:\APPS\CogniBase | pre_poc | - | api 8650 | Local desktop platform that connects to Hyland OnBase, lifts its data into a vector store… |
| mapsnap | C:\APPS\MapSnap | active_stable | - | api 9876 · mcp 8651 | Local-first schema-intelligence tool for ANY enterprise database set up as a profile (SQL… |
| cypherminer | C:\APPS\CypherMiner | complete | - | api 8502 · ui 7842 | Local-first bilingual (EN/PT) offline suite of crypto, encoding, math and text tools |
| lotterywiz | C:\APPS\Lottery Wiz | active | - | api 8777 | Fantasy 5 covering-design app — generates optimal play sets with guaranteed coverage |
| digitization | C:\Users\renne\Downloads\DIGITIZATION COSTS | complete | - | — | BU Digitization Cost Comparison Tool — client-side HTML calculator for Document Imaging &… |
| tubescout | C:\APPS\TUBESCOUT | active_development | - | api 8503 · ui 7843 | YouTube subscription intelligence: organize subs, sweep daily uploads, transcript-to-news… |
| retirementanalyzer | C:\APPS\Retirement Analyzer | paused | - | api 8504 · ui 7844 | Ingests a Fidelity positions CSV export and computes allocation, tax-bucket split (Taxabl… |
| avatarstudio | C:\APPS\AvatarStudio | active | - | ui 7862 | QI Avatar Studio — Gradio pipeline that turns a script into a talking-head avatar video (… |
| claude_manager | C:\APPS\CLAUDE | active | - | — | Claude Code management workspace — QI Hive orchestration, ecosystem reconciliation script… |
| gamez | C:\APPS\Gamez | active | - | api 8710 · quant 8712 | World Cup 2026 betting-window dashboard |
| claude_voice | C:\APPS\CLAUDE\Claude Voice | active_development | - | api 8720 · line 8721 · webcall 8722 · voice_api 8725 | Voice-driven assistant + (in progress) VOICE DISPATCH console |
| akiyascout | C:\APPS\AkiyaScout | new | - | api 8505 · ui 7845 | English-first Japanese real estate (Akiya/Kominka/rural) aggregation platform with a pers… |
| headroom | C:\APPS\CLAUDE\Tools | pilot | - | proxy 9020 · mcp stdio | Context/token compression layer (open-source, Apache-2.0) — proxy + MCP server that compr… |
| playdeck | C:\APPS\PlayDeck | active | - | api 8506 · ui 7846 | Personal hybrid video player — custom control UI over YouTube/Vimeo (IFrame API) and gene… |
| connector | C:\APPS\QIP\Connector | active_development | - | api 9030 | QI Connector — remote MCP server (Streamable HTTP) exposing QI ecosystem tools (Brain, re… |
| voice_studio | C:\APPS\VoiceStudio | active_development | - | ui 7863 | Studio (batch) voice tier: VibeVoice 1.5B long-form, multi-speaker rendering with consent… |
| comfyui | D:\AI | active | - | api 8740 | Local image and video generation engine |
| mediastudio | C:\APPS\MediaStudio | active_development | - | ui 7864 | The composition layer for QI's generators |
| filmforge | C:\APPS\FilmForge | active_development | - | api 7865 | Long-form film orchestration: story -> script -> scenes -> shot lists -> overnight GPU re… |
| onbase_dna | C:\Users\renne\Downloads\NOTE DISCOVERY | active | - | — | Genotype-to-phenotype decoding of OnBase configuration (DNA Codex, calibration, generated… |
| synvox | C:\APPS\SynVox | active_development | - | api 8751 · ai_router 8753 | SynVox (synthetic vox - the synthetic voice of the people) |
| noosorbis | C:\APPS\NoosOrbis | live | - | api 8507 · ui 7847 | Modern reading experience over live Wikipedia, with a Librarian AI assistant |
| mythologies | C:\APPS\Mythologies | live | - | — | Static site mapping 37 world mythologies as relationship graphs |
| baguapp_prod | C:\APPS\BaguApp_Prod | active | Marco zero — spec + docs, no… | — | The real BaguApp product — Bagua/Feng Shui analysis app |
| baguapp | C:\APPS\Baguapp | frozen | Prototype frozen 2026-09-08 (… | — | Bagua/Feng Shui analysis prototype |
| mailbrain | C:\APPS\MailBrain | active_development | Phase 1 live (Chrome MV3 exte… | — | Email intelligence assistant — Chrome MV3 extension + Flask helper |
| vlcdaemon | C:\APPS\VLCDaemon | paused | Working daemon, no repo until… | — | Background daemon that drives VLC for QI's YouTube/media workflows |
| trinity | C:\QIH\trinity | active | 30-day assistant trial → revi… | — | Tri-platform AI orchestration — Claude (spearhead) + ChatGPT via codex mcp-server + Gemin… |
| qi_gate | C:\QIH\engine\gate | active | Demo-account rollout live 202… | edge 9040 · auth 9041 | Authentication wall in front of every internet-exposed QI application: Caddy edge :9040 +… |
| aws_edge | C:\QIH\shared\documentation\guides | paused | M1 relay live; M2/M4/M6 demoe… | — | Hybrid 'edge on AWS, brain at home': Lambda LINE webhook relay + SQS queue (M1, live, dra… |
| transfer_station | TBD — locate console source (built 2026-08-12..19) | paused | Built and disarmed 2026-08-19… | sftp 22022 · console 8751 | Hardened Windows OpenSSH SFTP receive station (port 22022, chrooted, no shell) with a loc… |
| godseye | C:\APPS\Godseye | live | - | ui 8780 | Third-party open-source (MIT) real-time spatial-intelligence console: photorealistic 3D g… |

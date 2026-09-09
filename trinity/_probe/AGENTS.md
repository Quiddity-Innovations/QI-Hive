# QI Ecosystem — Assistant Onboarding (L1)

_Generated 2026-09-08 18:26:05 · qi_registry.json sha256[:12] = f7ccfea7a8fd_

## Who QI is

- Quiddity Innovations (QI) — owner Renne Santiago, sole developer + AI ambassador.
- 42 registered projects sharing one machine, ports, git, and a converging future.
- Two run tiers: `C:\APPS` is the gold build/run tier; `D:\Dev` is the packaged-out copy.
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
| naya | C:\APPS\NAYA | running_dev_paused | - | api 8002 · ui 7861 | Personal AI assistant for Renne — AI/physics/programming/networking domains + file scanni… |
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
| m2v | C:\APPS\M2V | paused | - | api 8501 · ui 7841 | Music to Video — AI-powered music video generator from lyrics + audio track |
| personalsong | C:\APPS\PersonalSong | paused | - | ui 8088 | Local free AI song generator — ACE-Step sung vocals + Demucs/Seed-VC voice clone |
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
| playdeck | C:\APPS\PlayDeck | new | - | api 8506 · ui 7846 | Personal hybrid video player — custom control UI over YouTube/Vimeo (IFrame API) and gene… |
| connector | C:\APPS\QIP\Connector | active_development | - | api 9030 | QI Connector — remote MCP server (Streamable HTTP) exposing QI ecosystem tools (Brain, re… |
| voice_studio | C:\APPS\VoiceStudio | active_development | - | ui 7863 | Studio (batch) voice tier: VibeVoice 1.5B long-form, multi-speaker rendering with consent… |
| comfyui | D:\AI | active | - | api 8740 | Local image and video generation engine |
| mediastudio | C:\APPS\MediaStudio | active_development | - | ui 7864 | The composition layer for QI's generators |
| filmforge | C:\APPS\FilmForge | active_development | - | api 7865 | Long-form film orchestration: story -> script -> scenes -> shot lists -> overnight GPU re… |
| onbase_dna | C:\Users\renne\Downloads\NOTE DISCOVERY | active | - | — | Genotype-to-phenotype decoding of OnBase configuration (DNA Codex, calibration, generated… |
| synvox | C:\APPS\SynVox | active_development | - | api 8751 · ai_router 8753 | SynVox (synthetic vox - the synthetic voice of the people) |
| noosorbis | C:\APPS\NoosOrbis | new | - | api 8507 · ui 7847 | Modern reading experience over live Wikipedia, with a Librarian AI assistant |
| mythologies | C:\APPS\Mythologies | live | - | — | Static site mapping 37 world mythologies as relationship graphs |
| baguapp_prod | C:\APPS\BaguApp_Prod | active | Marco zero — spec + docs, no… | — | The real BaguApp product — Bagua/Feng Shui analysis app |
| baguapp | C:\APPS\Baguapp | frozen | Prototype frozen 2026-09-08 (… | — | Bagua/Feng Shui analysis prototype |
| mailbrain | C:\APPS\MailBrain | active_development | Phase 1 live (Chrome MV3 exte… | — | Email intelligence assistant — Chrome MV3 extension + Flask helper |
| bakeoff | C:\APPS\QIP\Bakeoff | complete | Eval rig — Hermes vs OpenClaw… | — | Eval rig comparing Hermes vs OpenClaw on a shared gpt-oss-20b brain |
| vlcdaemon | C:\APPS\VLCDaemon | active | Working daemon, no repo until… | — | Background daemon that drives VLC for QI's YouTube/media workflows |
| trinity | C:\QIH\trinity | active | 30-day assistant trial → revi… | — | Tri-platform AI orchestration — Claude (spearhead) + ChatGPT via codex mcp-server + Gemin… |

---

# BaguApp Prod (baguapp_prod) — L2 brief

_Generated 2026-09-08 18:26:05_

## Registry facts
- Path: `C:\APPS\BaguApp_Prod`
- Status: active
- Phase: Marco zero — spec + docs, no code yet
- Notes: The real BaguApp product; inherits from the frozen prototype at C:\APPS\Baguapp. Mould for MilkWise.

## Brain
- Current state: status=active, phase=Marco zero — spec + docs, no code yet
  Registered 2026-09-08. The real BaguApp product; inherits from the frozen prototype at C:\APPS\Baguapp. Mould for MilkWise.
- No project-scoped decisions recorded.

## CLAUDE.md rules
# BaguApp — o aplicativo de verdade
protótipo: cada regra aqui custou um erro real para ser descoberta lá.

---
## 0. Regra zero: o protótipo está congelado
protótipo parecer errado, anote em `docs/` e siga — não corrija lá.

Consequência boa: como o protótipo não evolui, **copiar** os arquivos dele
para cá é seguro. O perigo de "duas cópias que se afastam" só existe quando
as duas mudam. Aqui só esta muda.
## 1. O que é o produto
cada símbolo é explicado e as correções vêm **integradas a cada passo**, não
numa seção separada. O Resumo do Laudo é mais formal, técnico e longo que o
da Jornada.
## 2. O que herdar do protótipo (copiar uma vez, de `C:\APPS\Baguapp`)
| `iching_temas.json` | os 64 temas + leitura para um cômodo, **texto próprio** (a edição canônica é protegida; nada dela foi reproduzido) | copiar tal qual; expandir se precisar, nunca colar fonte |
| `fengshui_referencia.json` | 25 princípios do Zangshu (chinês clássico, domínio público) com explicação e aplicação à casa, nossas | copiar tal qual |
| `iching_mapeamento.json` | Céu Posterior: direção → trigrama → área | copiar |
| `DOUTRINA - I Ching e o Bagua.md` (já em `docs/`) | a regra setor = interior, fachada = exterior, e por quê | é lei |
| `vercel/api/analisar.js` + `health.js` | roteador de motores com escada, validação de estrutura e **cânone**, castigo de modelo sem cota, credencial de equipe | base do serviço de análise; refatorar em módulos, manter o comportamento |
| `BaguApp Prototipo.html` | tabelas dos seis idiomas (`I18N`, `UI`, `AREA_T`, `ELEM_T`, `DIR_T`, `TRI_*`, `RING`, `LBL`, `P`, `HTTP_HINT`), `SCHEMA`, `SYSTEM_INSTRUCTION`, `tabelaIChing()`, `referenciaFengShui()`, o Luo Pan (`drawLuoPan`), a grade do Bagua (`gradeBagua`), os trigramas (`trigramasEmJogo`), `prepararImagem()`, o catálogo (`chaveCatalogo`, `catalogoLer/Gravar`) | **extrair** para arquivos próprios (JSON para dados, módulos JS para lógica). É o item "separar os dados do HTML" que o protótipo deixou em aberto |
Não herdar: os `_remendos/` (mecanismo do arquivo único; aqui o git é o diff),
o login de `localStorage` (é de mentira), a aba oculta como está (o painel
aqui é uma rota autenticada de verdade).
## 3. Decisões que já valem (não reabrir sem motivo novo)
1. **Chave nunca no cliente.** Só em variáveis de ambiente do servidor. Nem em
   HTML, nem em `localStorage`, nem em conversa. Localmente: `secrets/<projeto>.env`.
2. **O usuário só tem direito de rodar o programa.** Chave, motor, modelo e
   programa). A tela do usuário não menciona chave nem nomeia modelo.
3. **Roteador de motores com validação.** Escada de provedores; cada degrau é
   conferido — estrutura e **cânone** (cada leitura do I Ching cita, por hanzi
   que respondeu vai na resposta (para o painel, não para o usuário).
4. **Duas camadas de determinismo** (do `answer_cache.py` do MapSnap):
   `temperature 0` (+ `seed`), e um **catálogo de laudos verificados** — a
   usuário é texto nosso. Nunca reproduzir a tradução. A tabela de trigramas
   **não tem coluna de elemento** — Wilhelm rejeita os cinco elementos; o
   elemento é material de Feng Shui, fica no cartão da zona.
6. **A estrutura é calculada, a prosa é do modelo.** Hexagramas, setores,
7. **Seis idiomas, sempre**: pt, en, fr, es, ja, ko. Toda string nasce nos
   seis; há auditoria que sai com código 1 se faltar uma.
8. **Luo Pan**: a agulha aponta o norte, sempre; nasce parada; 子 centrado em
   0°; ordem canônica das 24 montanhas; Céu Posterior N=坎 NE=艮 L=震 SE=巽
   S=離 SO=坤 O=兌 NO=乾. Ver `ROTEIRO - Luo Pan em 4 camadas.md` no protótipo
   qualidade decide, não custo.
10. **Vercel Hobby veta uso comercial.** No dia do primeiro real: Vercel Pro ou
    Cloudflare Pages + Workers (recomendado: zero, comercial, sem o limite de
## 4. Arquitetura proposta (três fases)
(nunca montar a estrutura à mão) e validar com `qi_validator.py`.

---
## 5. Perguntas em aberto — responder no início da primeira sessão
9. Hospedagem do v2: projeto **novo** na Vercel (`baguapp-v2`, URL própria) — a URL do protótipo nunca pode quebrar.

---
## 6. Armadilhas já pagas (as que mais importam; a lista inteira está no protótipo)
- **Barra invertida não sobrevive a heredoc** no Bash daqui: `\\` vira `\`, `\b` vira backspace. Regex em script inline: `chr(92)`, ou a ferramenta de escrita.
- `getpass` no Windows lê do console e **ignora pipe** — de propósito; a chave só entra por uma pessoa num terminal.
- Uma pasta movida quebra tudo que aponta para ela (386 arquivos no OpenClaw). **Antes de mover, `grep`.** Vale para o protótipo se um dia virar `Baguapp_Demo`; esta pasta já nasceu com o nome definitivo.
## 7. Como o dono trabalha
- Respostas completas e estruturadas, com tabelas, e o **contra-argumento mais forte primeiro**. Não enfeite.
- Prefere script automático a passo manual. Se não consegue clicar em algo, direcione-o com precisão — ele clica.
- Ele corrige quando você erra, e tem razão com frequência suficiente para você verificar antes de discordar.
- Publicar é ação dele (`.bat`). Chave nunca passa pela conversa.

## Entry points
- none found

---

Task follows in the prompt. Reply in the requested format.

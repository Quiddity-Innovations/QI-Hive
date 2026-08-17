# BU Laptop Files — Evaluation & Disposition Report

**Date:** 2026-08-08 · **Subject:** `D:\BU Laptop Files` (22,390 files, ~38 GB)
**Status:** Evaluation only — **nothing has been deleted, moved, or pushed.**

---

## 1. Executive summary

| Disposition | Size | Share |
|---|---|---|
| **DELETE-SAFE** (regenerable, duplicate, or re-downloadable) | **~35.4 GB** | ~93% |
| **KEEP — work-confidential** (isolate, never publish) | ~0.5 GB | |
| **KEEP — import to home** (genuinely new capability) | < 2 MB | |
| **CREDENTIALS — rotate then delete** | 17 files | |

The overwhelming majority of the 38 GB is AI model weights and Python virtualenvs.
The genuinely valuable unique content is under 2 MB of source code plus a few MB of documents.

---

## 2. 🔴 Credentials — act on these first

17 credential-bearing files were located. **Contents were never opened.**

| Path | Risk | Recommendation |
|---|---|---|
| `AI\INFO\Claude Token.txt` | **108 bytes — the length of an Anthropic API key**, plaintext | **Revoke + reissue in the Anthropic console**, then delete |
| `.claude\.credentials.json` | BU laptop's Claude Code auth token | Delete — never reuse another machine's session token |
| `AI\tools\ClaudeConnectorGuard\backups\*.json` | MapSnap bearer token **in cleartext** (per the tool's own README) | Delete; rotate the MapSnap token |
| `MapSnap\config\secrets\` (claude.env, mapsnap_api_token.txt, mcp_bearer_token.txt, mcp_path_token.txt) | BU MapSnap deployment secrets | Regenerate on whichever machine needs them |
| `MapSnap\Application\service_tokens.json` | MapSnap service tokens | Regenerate |
| `AI\BU Hive\.env`, `AI\BU Hive\data\.secret_key` | BU Hive secrets | Delete |
| `AI\Products\CogniBase\.env` | CogniBase secrets | Delete |
| `MapSnap\onbase_dev_useraccounts.csv` | **OnBase dev user accounts — employer data** | Should not reside on a personal machine |

---

## 3. 🔴 Security gap found in the LIVE home MapSnap

BU's MapSnap closed a row-data egress hole that the home copy still has open. Verified directly:

| Check | BU | Home |
|---|---|---|
| `guardrail.py` has `row_egress_allowed()` / `filter_rows_for_egress()` | ✅ (Aug 1, 15,679 B) | ❌ **0 matches** (Jun 24, 11,862 B) |
| `server.py` gates `/api/table-data` on `allow_row_data` for MCP callers | ✅ | ❌ **0 matches** |

**Live exposure:** `QI_MapSnapMCP` is RUNNING and `config\mcp_gateway.json` has `"table_data": true`.
A profile set to "Local only" (FERPA/GLBA/HIPAA) will still return real row values to any
authenticated MCP client. **This is the highest-priority merge item.**

---

## 4. ✅ Resolved: the Ollama-gated chat picker bug

The open bug tracked in `project_bu_server_mapsnap.md` is **fixed — and home's fix is better.**

| Copy | State |
|---|---|
| `AI\MapSnapV3` (Jul 31) | Bug present — original nested gate |
| `MapSnap` BU (Aug 5) | Minimal patch: gate forced to `if(true)`, structure unchanged |
| **Home `C:\APPS\MapSnap` (Aug 2, commits `056e028`, `ac23a42`)** | **Rewritten into four independent provider blocks** (Ollama / OpenRouter / Direct API / Claude) with graduated status messages |

**Do not port BU's patch.** If anything, BU should receive home's version. The memory note
saying "do NOT patch C:\APPS\MapSnap meanwhile" can now be closed out.

Home is also **ahead** of BU on: Independent AI Connections board, multi-model-per-provider for
direct APIs, wider provider list (Groq, Mistral, DeepSeek, Qwen, Kimi, GLM, MiniMax), and newer
ONBASE UT1/UT2 schema data (Aug 7 vs Aug 3). **A merge must not overwrite these.**

---

## 5. KEEP AND IMPLEMENT — what's genuinely worth adopting

### 5.1 MapSnap code to merge into the product (generic, not BU-specific)

| Priority | Item | Why |
|---|---|---|
| **1** | Row-data egress gate (`guardrail.py`, `server.py`) | Security fix — see §3 |
| 2 | Claude effort/persona/headroom chat controls + routing backend | Fully generic |
| 3 | `compare_config.py` + Compare-tab diff UI | Its own docstring says "universal, not OnBase-specific" |
| 4 | `improve_ddl_schema.py` (4-pass DDL coverage-gap fixer) | Generic DDL post-processor |
| 5 | Schema group/sort visual editor, Ops tab, `_brainGet`/`_brainSet` | Generic UI + QI Brain plumbing |

### 5.2 Claude Voice capabilities absent at home (verified: none of these exist in `C:\APPS\CLAUDE\Claude Voice`)

| Item | Capability gap it closes |
|---|---|
| `session_watch.py` + `session_hook.py` | Self-healing supervisor: arms mic + speaks morning brief once/day when any Claude session opens. Uses redundant signals and a level-reconcile loop; docstrings record three earlier failed designs. Home only speaks after each reply. |
| `control_panel.py` | One loopback web page controlling every voice service, brain mode, mic, and the daily scheduled task. Home has no unified control surface. |
| `bridge_responder.py` (`_reply_claude_code`) | Headless auto-responder via `claude -p --resume`, voice-tuned prompt, tools locked down. Home's equivalent is manual-only. |
| `speech_trace.py` | JSONL trace of TTS attempts with `--dupes` mode for double-speak races. Drop-in. |
| `config.py` + `cvlog.py` | Shared config/logging layer the above depend on. |
| `wait_for_inbox.py` | Event-driven inbox wait with dedup (stops the mic hearing Claude's own TTS). |

⚠️ Requires port remapping — BU defaults sit outside the home 8720–8729 Claude Voice block.

### 5.3 Governance and standards worth adopting

| Item | Why |
|---|---|
| **PreToolUse git guardrail** (`hooks\require-git-approval.ps1` + policy in BU `CLAUDE.md`) | Home has **no PreToolUse hook at all**. Deterministically blocks `git push --force`, `reset --hard`, `rebase`, `clean -fd`. **Recommendation: adopt the DENY rules only** — the ASK-on-commit/push rules would fight the "Update all" workflow and global bypassPermissions. Prose in CLAUDE.md can be overridden by context; a hook cannot. |
| **Tier-gated project lifecycle + doc-freshness** (`Documentation-Standard.md`, `Project-Structure-Standard.md`) | POC → Dev&Test → Beta → Production gates with override + audit trail, and staleness computed from source mtime vs doc mtime. QI standards enforce structure but nothing enforces "are the docs current" or "has this cleared its gate". |
| **`session_capture.py` transcript parser** | Per-tool call counts, files-touched, git commands, and **subagent outcomes classified ok/error/incomplete with duration**. Home's `subagent_stop.py` writes far thinner stubs. Port the parser, not the schema — Brain has one. |
| **25 BU memory files** (tiny) | Several transferable, notably *"no loose scripts — build ops actions as Ops-tab controls, not `python foo.py` one-liners"*. |
| **`onbase-notetype-decoder` tooling** | ⚠️ Home's skill is **doc-only** (`SKILL.md`). The runnable `calibrate.py` / `notetype_dna.py` exist **only** here. Import the code; leave the BU data extract behind. |

### 5.4 Not worth importing

The seven `bu-*` agents are thin stubs; home's `hive-*` agents have richer descriptions, model
tiers, tool lists, and ecosystem context. Home is ahead. `ClaudeConnectorGuard` is superseded by
the QI Connector. The `.claude` consolidation plans describe a state home already reached.

---

## 6. WORK-CONFIDENTIAL — isolate, never publish

⚠️ `Quiddity-Innovations/QI-Hive` is a **PUBLIC** repo. None of the following may reach it.

| Item | What it is |
|---|---|
| `AI\Projects\OnBase Documentation\` | Real BU solution docs, config sheets, test plans, project number PRJ2035014 |
| `AI\Cowork Projects\Whiteboard Transcription.md` + images | Internal retro naming real BU engagements (GMS, TR, SPC, UFM, CAMED, QST) |
| `AI\BU Hive\data\bu_registry.json`, `bu_hive.db` + backups | Live wiring to BU's OnBase and SQL Server systems |
| `AI\Products\CogniBase\` | BU-internal OnBase vector-search / SQL-reporting tool |
| `AI\Products\ClaudeVoice\teams_bot.py` + Teams/Planner docs | Built against a real BU Entra/Teams tenant |
| `MapSnap\Product\ONBASE*`, `JENZABAR*`, `BU_JENZABAR*` | BU institutional schema data |
| `AI TEMP\onbase-notetype-decoder\full_report.txt` | Decoded extract of a **live BU OnBase 25 dev database** (config metadata; no PII) |
| `AI\BU Hive\deploy\` | BU IT IIS hosting specifics |

**Open question for Renne:** `AI\Products\ClaudeVoice\data\transcripts\meeting_1782146412.json` —
a recorded meeting transcript, deliberately not read. If it is a real BU meeting rather than test
data, it is employer content and should not remain here.

**Ambiguity worth a gut-check:** `BU Hive\app\*.py` contains no BU business logic — it is Renne's
own tooling pattern — but it was built on an employer-managed machine. BU's IP policy may still
claim it. Worth confirming before treating it as freely portable.

---

## 7. DELETE-SAFE — the reclaim list (~35.4 GB)

| Item | Size | Why safe |
|---|---|---|
| `AI\COMFYUI\z-image-turbo-bf16-aio.safetensors` | 19.11 GB | Home already runs Z-Image-Turbo bf16 via `C:\1-AI\APPS\ComfyUI\models\unet\` + VAE |
| `AI\COMFYUI\z-image-turbo-fp8-aio.safetensors` | 9.64 GB | Home has `z_image_turbo-Q8_0.gguf`, same model, same low-VRAM use case |
| `AI\COMFYUI\juggernaut_reborn.safetensors` | 1.99 GB | Free one-click CivitAI re-download |
| `AI\COMFYUI\` (installer + XTTS node source) | 14 MB | GitHub |
| `AI\AI_LEARNING\ComfyUI Course ....mkv` | 2.63 GB | Public course video |
| `AI\AI_LEARNING\*.zip` (7 archives) | 290 MB | All public GitHub/CivitAI |
| `AI\tools\ffmpeg` | 595 MB | Byte-identical build already installed at home via WinGet |
| `AI\Products\ClaudeVoice\.venv` | 406 MB | `pip install -r requirements.txt` |
| `AI\MapSnapV3\` | 343 MB | Strict subset of the newer BU MapSnap; nothing unique; still contains the Ollama bug |
| `MapSnap\dist\` | 78 MB | Build output |
| `MapSnap\Distribution\*.zip` | 75 MB | Regenerable via `tools/build_bu_kit.py` |
| `AI\MapSnap_BU_Edition_2026-07-31 (2).zip` | 73 MB | Superseded by `(3).zip` 20 min later |
| `.claude\projects\*\*.jsonl` | ~78 MB | Session transcripts — history only |
| `AI\Products\CogniBase\.venv` | 52 MB | Regenerable |
| `AI\BU Hive\.venv` | 34 MB | Regenerable |
| `MapSnap\LOGS\`, `AI\Sessions\`, `AI\Logs\`, `AI\Temp\` | ~9 MB | Runtime logs and history |
| **Total** | **~35.4 GB** | |

**Recommended sequencing:** merge the §5.1 MapSnap code first (especially the security fix),
confirm it works, *then* delete. The BU MapSnap folder is the merge source — it must stay until
the merge is done.

**Keep despite small size:** `AI\AI_LEARNING` personal docs (~53 MB), `AI TEMP` (1.2 MB),
`.claude\projects\*\memory\*.md` (25 files), `AI\COMFYUI\fastNSWFPrompt_v10\PromptCaption.json`.

---

## 8. Recommended order of operations

1. **Revoke the Anthropic key** in `AI\INFO\Claude Token.txt`; rotate the MapSnap tokens.
2. **Merge the MapSnap row-egress security fix** into `C:\APPS\MapSnap` (§3) and restart `QI_MapSnapMCP`.
3. Decide on `meeting_1782146412.json` and the `BU Hive\app` IP question (§6).
4. Merge the remaining MapSnap features (§5.1), reconciling against home's newer work.
5. Import the Claude Voice capabilities (§5.2) with ports remapped into 8720–8729.
6. Adopt the git guardrail DENY rules and the doc-freshness/tier standard (§5.3).
7. **Then** run the deletions (§7) — approximately 35.4 GB reclaimed.
8. Move the remaining work-confidential residue into one clearly-labelled isolated folder.

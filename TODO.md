# 📋 QI Hive — Open Items Board

**Updated:** 2026-08-08 · Maintained by the Claude manager session. One glance = everything pending.
(🔴 needs Renne · 🟡 Claude in progress · ⚪ queued/decision)

## 🤖 Agent assignments — today's workforce (transparency ledger)
| Agent | Model tier | Assignment | Status |
|---|---|---|---|
| hive-builder | 🟩 Sonnet | Build Agent HR: roster DB + `:8600/agents` board + SubagentStop ingest | ✅ Done — 8.7 min, 109.4k tokens, 69 tool calls; hook edit audited by manager (fail-safe verified), board live |
| general-purpose | 🟧 Opus | MapSnap BU feature merge (compare-diff, DDL fixer, effort/persona controls, schema editor, Ops tab) — hard divergent-code reconciliation, hence Opus | ✅ Done — 28.6 min, 310.7k tokens, 231 tool calls; 8 commits, all features ported, home features verified intact by manager |
| hive-ops | 🟢 Haiku | Delete stale C:\ copies (exact 13-path list; mechanical) | ✅ Done — ~3 GB freed, 152s, 27.8k tokens; leftovers: 3 locked OneDriveTemp items + 0-byte `C:\list` (permission-denied, needs elevation, cosmetic) |
| 4× general-purpose | 🟩 Sonnet | BU Laptop Files evaluation (Products/Hive/MapSnap/bulk) | ✅ Done this morning |
| hive-builder | 🟩 Sonnet | Integrate Agent HR into QI Hive UI (home tile, Mission Control cross-links, registry-linked projects, Docs Brain registration) | ✅ Done — 7.6 min, 130.3k tokens, 78 tool calls; verified by manager (tile, cross-links, 14-agent API, auth parity via QI Gate) |
| Manager (this session) | 🟥 Fable | Orchestration, specs, review, security-sensitive edits only; authored the BU "AR" buildout prompt | — |

> Full per-agent metrics (runs, tokens, hours, history) land on the **Agent HR board → `http://127.0.0.1:8600/agents`** once hive-builder ships it; runs auto-record via the SubagentStop hook from then on.

## 🔴 Renne — security console actions (Claude cannot do these)
- [ ] **Revoke the Anthropic API key** (`_CREDENTIALS\Claude Token.txt`) — verified 2026-08-08: NOTHING on
      this machine uses it (Claude auth is OAuth; ClaudeVoice anthropic backend disabled, no key set). Check
      the console's *last-used* column first: never/stale → revoke; recent → the BU laptop uses it, reissue
      there properly, then revoke. Renne conditionally agreed 2026-08-08.
- [ ] ~~Rotate MapSnap tokens~~ **Downgraded 2026-08-08**: hash-compare proves the quarantined BU tokens ≠ home's
      live tokens — they open nothing here. Just destroy them with `_CREDENTIALS` (item E); rotate on the BU
      side only if that deployment still runs.
- [ ] **Judge the meeting transcript**: `...\ClaudeVoice BU-tenant items\meeting_1782146412.json` — test data or real BU meeting? (never opened)
- [ ] **F:\ (ROG ESD-S1C)**: reseat cable into a motherboard port, run `chkdsk F: /f` — drive dropped writes on 2026-08-08; do not park data on it until proven
- [ ] **Gut-check BU Hive / CogniBase app-code IP** (built on employer machine) before any reuse outside BU work

## 🟡 Claude — in progress
- [x] **MapSnap feature merge** — ✅ done 2026-08-08 (Opus agent, verified by manager): compare-config diff
      engine + UI, DDL post-processor, effort/persona/headroom chat controls, schema group editor, Ops tab,
      Brain hooks + row-egress admin control; 8 commits on main, pushed, dev fast-forwarded. BU-only leftovers
      deliberately not ported (top-bar refactor, FK dual-shape, claude_cli endpoint UI, OnBase-ping badge,
      no-SQL doc retrieval) — say the word if wanted. Item B (delete D:\BU Laptop Files remainder) now unblocked
      pending Renne's browser check of the new features.
- [x] **Agent HR board** — ✅ LIVE at `http://127.0.0.1:8600/agents` (2026-08-08): 13 agents on the roster, 44 historical runs backfilled from transcripts, auto-onboarding works (already discovered `claude-code-guide` on its own), every future sub-agent run records automatically via the SubagentStop hook
- [x] **C:\ stale-copy cleanup** — ✅ done by hive-ops (Haiku) 2026-08-08: 8 folders deleted, temps emptied, ~3 GB freed, verified by manager. Cosmetic leftovers: 3 locked OneDriveTemp items, 0-byte `C:\list` (both need elevation; harmless)

## 🛑 Pending approval — irreversible actions (Renne must say yes per item)
| # | Item | Size | Consequence if deleted | Recoverable? |
|---|---|---|---|---|
| A | `C:\AutoPDF_Portable` | 1.4 GB | Current portable build gone | Yes — rebuildable from C:\AutoPDF, but it IS the latest build, so held for approval |
| B | `D:\BU Laptop Files` (remainder) | 183 MB | The BU MapSnap merge SOURCE + ClaudeVoice originals + personal docs disappear | Partially — only delete AFTER the MapSnap feature merge is verified working |
| C | `F:\BU Edition` + `F:\Server 2012 R2*` fragments | ~2 GB | Corrupt partial copies on the failing drive | Superseded by D:\ full copy — but drive needs chkdsk first; deleting from a failing volume can worsen it |
| D | `C:\Server 2012 R2` (the parked VM) | 45 GB on C:\ | The ONLY copy of the 2012 R2 VM | Decision needed: move to D:\ (reversible, frees C:\) vs keep vs discard (you're building Server 2025) — moving recommended, discard needs explicit approval |
| E | `_CREDENTIALS (rotate then destroy)` folder | small | Old tokens destroyed | Destroy ONLY after Renne rotates/revokes each credential |

*(The 13-path stale-copy list running now was explicitly pre-approved and contains none of the above.)*

## ⚪ Queued / awaiting decision
- [ ] **C:\ARCHIVE (362 GB) → D:\** — frees C:\ to ~50%; D:\ is NTFS and ready; needs Renne's go
- [ ] **C:\ runtime consolidation** — move running apps into one folder (52 NSSM services to repoint); own session
- [ ] **`D:\Apps` release tier** — pending external NVMe purchase; then per-app installation packages → `C:\Program Files`
- [ ] **QI-Hive GitHub repo is PUBLIC** — holds hostname inventory; consider making private (hardening commit still unpushed)
- [ ] **MailBrain git remote** points at EasyFlow.git — fix, then push its dev branch
- [ ] **PlayDeck / OpenClaw / AkiyaScout** — no GitHub remotes; create private repos, push dev
- [ ] **E:\ (My Book Duo) exFAT→NTFS** — blocked until ~12.3 TB of parking space exists
- [ ] **Windows Server 2025 VM + OnBase 2025** — new build for direct SQL access (MapSnap BU work); VM parked at `C:\Server 2012 R2` is safe

## ✅ Recently done (2026-08-08)
- D:\ exFAT→NTFS (+73 GB recovered) · D:\Dev rebuilt + verified · 16 dev branches on GitHub
- BU Edition workspace + policy kit (strict-by-default editions) · qi_new_edition.py
- BU Laptop Files: evaluated (4 agents), valuables imported, employer material → `BU Administrative Backups` (gitignored), ~36 GB deleted
- MapSnap row-egress security gate merged + live (`7c36fba`), propagated main→dev→edition/bu
- Claude Voice: session supervisor, control panel :8724, headless responder — imported + running
- Git guardrail wired (mode=off at home) · doc-freshness governance (observe) · hibernation off (+27 GB)

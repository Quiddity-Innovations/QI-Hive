# COWORK_CONTEXT.md
# CoWork persistent state — read this at the start of every CoWork session
# Maintained by: Claude Code + QI Hive | Last updated: 2026-04-20

---

## ANSWERS TO YOUR 2 QUESTIONS

### Q1 — Which projects have migrated to C:\QIP as of today?
**None.** `C:\QIP` exists as an empty folder. No projects have moved yet.

Current authoritative paths (use these — not QIP paths):
| Project    | Current Path      | Status         |
|------------|-------------------|----------------|
| QI Hive    | C:\QIH            | ✅ Already at final location |
| Maia       | C:\QI             | 🔄 Migrates to C:\QIP\Maia eventually |
| Naya       | C:\NAYA           | 🔄 Migrates to C:\QIP\Naya eventually |
| NEXUS      | C:\NEXUS          | 🔄 Migrates to C:\QIP\NEXUS eventually |
| OpenClaw   | C:\OC             | 🔄 Migrates to C:\QIP\OC eventually |
| MQ         | C:\MQ             | 🔄 Migrates to C:\QIP\MQ eventually |
| EasyFlow   | C:\EasyFlow       | 🔄 Migrates to C:\QIP\EasyFlow eventually |
| QI-Universal | C:\UNIVERSAL    | Infrastructure — stays |

Migration rule: ONE project at a time. Renne decides the order. Maia first is the suggestion but not confirmed.
After all projects move, `C:\QI` is renamed to `C:\QIB` (QI Business — brand, legal, marketing, admin).

---

### Q2 — Is C:\QIH\shared\reports\inbox\ already watched?
**YES — already live.** `QI_HiveIngest` is a running NSSM service that watches the inbox and auto-ingests reports into `status.json`.

You can start writing session reports there NOW. No endpoint needs to be built first.

**Write your session reports to:**
`C:\QIH\shared\reports\inbox\cowork_YYYYMMDD_HHMMSS.json`

**Use this exact schema:**
```json
{
  "source": "cowork",
  "session_date": "2026-04-20T00:00:00",
  "type": "session_report",
  "summary": "One paragraph of what happened",
  "decisions": ["decision 1", "decision 2"],
  "flags": ["items needing Claude Code or Renne attention"],
  "outputs": ["files produced and their paths"],
  "next_suggested": ["what you think should happen next"]
}
```

---

## DISPATCH PROTOCOL (now live)

**For tasks/proposals/reviews you want actioned by Claude Code or Renne:**

Write a dispatch file to: `C:\QIH\cowork-dispatch\`
File name: `dispatch_YYYYMMDD_HHMMSS_<type>.json`

Schema:
```json
{
  "dispatch_id": "uuid",
  "source": "cowork",
  "type": "report | brief | decision | task | review | proposal",
  "priority": "high | normal | low",
  "project": "qi_hive | maia | naya | nexus | openclaw | mq | easyflow",
  "payload": {},
  "reply_path": "C:\\QIH\\shared\\reports\\inbox\\reply_<uuid>.json"
}
```

QI Hive Dashboard shows all dispatches as cards with **Approve / Decline / Discuss** buttons.
- **Approve** → logged to QI Brain + queued for Claude Code
- **Decline** → logged with reason
- **Discuss** → opens threaded notes visible to all parties before execution

---

## DIVISION OF RESPONSIBILITY

| Cowork owns | Claude Code owns |
|---|---|
| Strategy, roadmaps, planning | All code writing and execution |
| Documents (.docx, .pdf, .xlsx, .pptx) | NSSM, deployment, services |
| Briefings for agents before sessions | QI Brain API calls requiring auth |
| Cross-project reasoning | Session hooks, scheduled tasks |
| Human-facing communication | Anything autonomous or scheduled |
| Decision drafting + task prioritization | Debugging, migrations |

**The loop:** CoWork drafts → Renne approves (via Dashboard) → Claude Code executes.
**This loop is never shortcut.**

---

## SYSTEM STATE SNAPSHOT (as of 2026-04-20)

| Service | Port | Status |
|---|---|---|
| QI Brain API | 9010 | ✅ Running (NSSM: QI_BrainAPI) |
| Hive Dashboard | 8600 | ✅ Running (NSSM: QI_Dashboard) |
| Maia Bot | 8001 | ✅ Production (LINE/Telegram/Messenger live) |
| Naya Bot | 8002 | ✅ Active (Telegram @Naya_qi_bot, LAN-only) |
| NEXUS | 8010 | ✅ Active (AI synthesis backbone) |
| HiveIngest | — | ✅ Running (watches inbox folder) |

**Active projects:** Maia, Naya, NEXUS, OpenClaw, MQ (new), EasyFlow, QI Hive
**Agents:** architect, builder, inspector, ops, scout, scribe, tester

---

## HOW TO KEEP EVERYONE AWARE

1. **After every CoWork session** → write `cowork_YYYYMMDD_HHMMSS.json` to inbox
2. **For proposals needing action** → write dispatch file to `C:\QIH\cowork-dispatch\`
3. **For urgent flags** → set `"priority": "high"` in dispatch + add to `"flags"` in session report
4. **Renne sees everything** on the Hive Dashboard at `http://localhost:8600`

---

## KEY CONTACTS IN THE SYSTEM

- **Renne Santiago** — owner, final decision authority, reachable via Telegram (@Naya_qi_bot) or LINE (via Maia)
- **Claude Code** — technical executor, reads this file at session start, acts on approved dispatches
- **QI Brain** — shared memory at http://localhost:9010, source of truth for all decisions/sessions/features

---
*This file is automatically updated by Claude Code. Do not edit manually.*

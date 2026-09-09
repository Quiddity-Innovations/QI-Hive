# QI Handoff — Phase 0 packet exchange

Plain-file handoff for work that only exists as an "app-only feature" —
ChatGPT Deep Research / voice / Custom GPTs, Gemini Workspace panels / Gems /
Scheduled Actions / NotebookLM — where no MCP tool exists (Layer C of
`QI_TriPlatform_AI_Orchestration_Plan_2026-09-08.md`, §2.1). Until Bus v1
(SQLite journal, Wave 0.7 of the architecture plan) ships, packets are plain
Markdown files. The bus design explicitly tolerates that.

## What a packet is

A single Markdown file with YAML front matter (see `PACKET_TEMPLATE.md`)
naming who it is from, who it is to, what is being asked, and where the
answer should land. It never contains a secret — `qi_handoff.py redact`
refuses to emit a packet that matches a secret pattern.

## Lifecycle

```
outbox/HANDOFF-YYYYMMDD-NNN-<to>.md   <- created by `qi_handoff.py new`, redacted, clipboard-copied
        |  Renne pastes it into ChatGPT / Gemini by hand
        v
   (assistant produces an answer in its own UI)
        |  Renne saves/exports the reply as a local file
        v
inbox/RETURN-YYYYMMDD-NNN-<from>.md   <- stored by `qi_handoff.py ingest`, row appended to ledger.csv
        |
        v
archive/                              <- moved here once the packet's work is merged/closed
```

- **Numbering**: `NNN` is a zero-padded, monotonically increasing counter shared across
  `outbox/` and `inbox/` for a given day — `qi_handoff.py new` picks the next free number.
- **Naming**:
  - Outbound: `HANDOFF-YYYYMMDD-NNN-<to>.md` (`<to>` is `chatgpt` or `gemini`)
  - Return: `RETURN-YYYYMMDD-NNN-<from>.md` (`<from>` matches the `to` of the packet it answers)
- **A packet is never archived until its return has been ingested** — `list` shows anything
  in `outbox/` without a matching `RETURN-*` in `inbox/` as still open.
- **Secrets never travel through this folder.** `new` runs the redactor before writing;
  `redact` can also be run standalone on any file before it is pasted anywhere.

## Folders

| Folder | Contents |
|---|---|
| `outbox/` | Packets waiting to be pasted into an assistant's UI |
| `inbox/` | Returns that have been ingested and logged |
| `archive/` | Closed packet/return pairs, moved here manually once merged |

## Ledger

`ledger.csv` (created on first `ingest`) — one row per closed packet:
`id, to, title, created, returned, chars`.

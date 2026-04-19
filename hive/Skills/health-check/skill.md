# health-check

Run a full status check across all QI projects and report clearly.

## Triggers
Any of these phrases:
- "check status"
- "check if all is up to date"
- "health check"
- "what's the state of everything"
- "how are the projects doing"

## Process

1. **Run the health check script:**
   ```
   python C:\Claude\health_check.py --save
   ```
   `--save` updates status.json with the live results.

2. **Read the output** and present a clear summary table:
   | Project | Service | Port | Git | Docs | Issues |
   Each cell gets a simple ✅ / ⚠️ / ❌ — no raw data dumps.

3. **Flag anything requiring action** — list them clearly at the bottom:
   - Stopped services
   - Stale documentation
   - Uncommitted code
   - Missing SUMMARY.md

4. **Offer to explain any project** — if Renne asks "tell me about Naya" or "explain NEXUS",
   read `C:\{PROJECT}\SUMMARY.md` and give a plain-English summary.
   If SUMMARY.md is missing, read the project's CLAUDE.md and key server file instead.

5. **Offer to fix issues** — after reporting, ask:
   "Want me to fix any of these? I can commit the loose files, update the docs, or restart the service."

## Output format

```
QI ECOSYSTEM — STATUS CHECK  [date/time]

Project        | Service  | Port | Git      | Docs     | Health
---------------|----------|------|----------|----------|--------
Maia           | ✅ up    | ✅   | ⚠️ dirty | ✅       | ⚠️
Naya           | ✅ up    | ✅   | ✅       | ⚠️ stale | ⚠️
NEXUS          | ❌ down  | ❌   | ⚠️ dirty | ❌       | 🔴
OpenClaw       | ⚪ WSL   | ⚪   | ✅       | ✅       | ✅
MQ             | ⚪ n/a   | ⚪   | ⚠️ dirty | ❌       | ⚠️
Claude Manager | ✅ up    | ✅   | ✅       | ✅       | ✅

⚠️  ACTION NEEDED:
  - NEXUS: service not installed, port 8010 closed
  - Maia: 21 uncommitted files
  - Naya: docs 6 days behind code
```

## "Explain it to me" protocol

When Renne asks to understand a project, feature, or build:
1. Read the project's SUMMARY.md (plain English overview)
2. Read the relevant section of the Implementation Log or recent git commits
3. Explain in plain language — no jargon, use analogies where helpful
4. Offer to go deeper on any part

## Frequency
Run automatically:
- At the start of every session (silent check — only surface issues)
- When explicitly asked
- Before starting any cross-project work

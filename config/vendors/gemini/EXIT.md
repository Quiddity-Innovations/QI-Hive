# Gemini — Exit Checklist

Order matters: export first, flip second, revoke last. Do not revoke access
before the export step is confirmed complete — Gem instructions and saved
info are not recoverable after account/key cutoff.

## 1. Export (do this first)

- [ ] Copy the instruction text of every Gem (Inbox Triage, Week Planner,
      YouTube Researcher) into
      `C:\QIH\config\vendors\gemini\INSTRUCTIONS_MIRROR.md`
- [ ] Export Gemini "saved info" if the product exposes an export option
      that month; otherwise copy by hand
- [ ] Export or note the NotebookLM notebook's source list (it is seeded
      from `C:\QIH\shared\documentation` exports, so the underlying docs
      are already local — only the notebook structure itself is at risk)
- [ ] Save any open packet threads: run `qi_handoff.py list` and ingest
      outstanding returns before cutoff

## 2. Flip (disable the integration)

- [ ] Remove or set `enabled:false` on the `qi_gemini_mcp` stdio MCP entry
      in Claude Code's MCP config
- [ ] Disable the three Scheduled Actions (07:00 inbox+calendar summary,
      Sunday YouTube digest) in the Gemini app — these are cross-checks
      only; Asa/Kaze/Yubin/TubeScout remain primary and are unaffected
- [ ] Confirm no scheduled task or NSSM service references the Gemini
      free-tier key or `qi_gemini_mcp.py`

## 3. Revoke (last — irreversible)

- [ ] Cancel the Google AI Pro subscription
- [ ] Revoke/delete the free-tier AI Studio API key
      (`C:\QIH\secrets\trinity_gemini.env`) — confirm the Google Cloud
      project never had a billing account attached (plan D1/§2.1 rule)
- [ ] Turn off the enabled Gemini app connections (Gmail, Calendar, Drive,
      Keep, Tasks, YouTube) under Gemini app → Settings → Apps
- [ ] Delete `C:\QIH\secrets\trinity_gemini.env` once revocation is
      confirmed

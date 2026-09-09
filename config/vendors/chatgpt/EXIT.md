# ChatGPT / Codex — Exit Checklist

Order matters: export first, flip second, revoke last. Do not revoke access
before the export step is confirmed complete — you cannot re-fetch
Custom GPT instructions or memory after the account is cut off.

## 1. Export (do this first)

- [ ] Copy the instruction text of every Custom GPT used by QI work into
      `C:\QIH\config\vendors\chatgpt\INSTRUCTIONS_MIRROR.md`
- [ ] Request and download the ChatGPT data export ZIP (Settings → Data
      controls → Export data) — save under
      `C:\QIH\config\vendors\chatgpt\exports\` (create the folder at export time)
- [ ] Save any open packet threads: run `qi_handoff.py list` and ingest
      outstanding returns before cutoff
- [ ] Note which of the "QI File Steward" Custom GPT's proposals are still
      pending application via `qi_fs_apply.py`

## 2. Flip (disable the integration)

- [ ] Remove or set `enabled:false` on the `codex` stdio MCP entry in
      Claude Code's MCP config
- [ ] Confirm `hive-*` delegation rubric routes coder tasks to the local
      fallback (`gemma4:31b` / `qwen3-coder` via a hive-* sub-agent, or a
      Claude Sonnet sub-agent) — see plan §7 cancel-safety matrix
- [ ] Confirm no scheduled task or NSSM service references `codex` or
      `codex mcp-server`

## 3. Revoke (last — irreversible)

- [ ] Sign out `codex login` in WSL (`~/.codex`)
- [ ] Cancel the ChatGPT Plus subscription in OpenAI account settings
- [ ] Revoke any Developer Mode connector granted to QI Connector
      (reverse direction, plan §2.1 Layer D)
- [ ] Delete the local `~/.codex` credential cache once revocation is
      confirmed

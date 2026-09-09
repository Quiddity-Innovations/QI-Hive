# QI Vendor Exit Contract

Source: `C:\QIH\shared\documentation\plans\QI_TriPlatform_AI_Orchestration_Plan_2026-09-08.md` §2.2.
Applies to every vendor integration in the ecosystem, not just ChatGPT/Gemini.
An integration is not considered "in" until it satisfies all five rules.

## The five rules

1. **One-flag disable** — an MCP entry removed or `enabled:false`, never a code change.
2. **No orphaned knowledge** — Custom GPT instructions, Gem instructions, ChatGPT memory
   and Gemini "saved info" are exported monthly to `C:\QIH\config\vendors\<vendor>\` and
   committed. (ChatGPT has no memory export button — copy by hand or via the data export
   ZIP; Custom GPT configs must be pasted manually.)
3. **Named local fallback** — the Ollama model or hive-* agent that takes the job if the
   vendor disappears (see the cancel-safety matrix, plan §7).
4. **No vendor in the critical path** — no scheduled task, NSSM service or QI app
   *requires* an assistant to run. Assistants are called by Claude during sessions, not
   by unattended jobs.
5. **Exit checklist filed** — `C:\QIH\config\vendors\<vendor>\EXIT.md`: what to export,
   what to flip, what to revoke (OAuth grants, keys), in that order.

## Monthly export checklist (every vendor, every month)

- [ ] Export/copy Custom GPT / Gem instruction text into that vendor's
      `INSTRUCTIONS_MIRROR.md`
- [ ] Export ChatGPT memory (data export ZIP) or Gemini "saved info" if either
      product exposes one that month
- [ ] Confirm the vendor's MCP entry still has a one-line disable
      (`enabled:false` or entry removal) — re-verify after any Claude Code
      config change
- [ ] Confirm the named local fallback (Ollama model / hive-* agent) still
      exists and has not been removed or renamed
- [ ] Confirm no scheduled task or NSSM service calls the vendor directly
      (`grep` scheduled task XML / NSSM AppParameters for the vendor's CLI or API)
- [ ] Update `<vendor>/EXIT.md` if the export/flip/revoke steps changed
- [ ] Commit the vendor config folder

## Quarterly vendor blackout drill

Flip every assistant MCP entry to `enabled:false` for one day, run workflows
W1–W3 (plan §6) with local fallbacks only, and confirm no QI service, task
or app degraded. See plan §7 and §11a for the pass/fail criteria.

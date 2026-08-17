# Phases 2–5 — session starter

**Model:** Opus 5
**Start Claude Code from:** `C:\` (NOT `C:\PlayDeck` — that folder moves in Phase 4)

Paste the prompt below as the first message.

---

## The prompt

```
Continuing a migration that Phase 1 completed on 2026-08-08. Read these first,
they are the handoff:

  C:\QIH\shared\documentation\migration_2026-08\inventory.txt
  C:\QIH\shared\documentation\session_summaries\ComfyUI_Migration_Summary_2026-08-08_1301.docx

Phase 1 is done: ComfyUI now runs from D:\AI on port 8189, all models live in
D:\AI\models (the install's internal models folder is a junction to it), the
qi-comfy MCP server is registered user-wide, and the old C:\1-AI\APPS\ComfyUI
was deleted after file-by-file verification. C: went from 241 GB to 415 GB free.

Do phases 2 through 4. Phase 5 is design work for later — plan it, don't build it.

PHASE 2 — Python
  Install Python for ALL USERS to C:\Program Files (NOT the per-user default in
  AppData: 31 QI services run as LocalSystem and must not load binaries from a
  user profile). Then repoint everything that references
  C:\1-AI\APPS\PYTHON\python.exe:
    - 31 NSSM services (nssm set <name> Application ...)
    - 4 scheduled tasks (NightlyReconcile, ComplianceFast, GamezAIPin, OC-Keepalive)
    - 2 MCP servers in ~/.claude.json (qi-brain, qi-registry)
    - the venv at C:\CogniBase\.venv (recreate it, don't edit pyvenv.cfg)
  Multiple Python versions may coexist — if a project needs 3.11, point it at
  3.11 rather than forcing everything onto one version. Verify each service
  starts and its health endpoint answers before moving on.

PHASE 3 — retire C:\1-AI
  Move C:\1-AI\APPS\AvatarStudio to C:\APPS\AvatarStudio first — it is a live
  registered QI project (id: avatarstudio, port 7862), not junk. Reinstall
  VSCode and LM Studio to their standard locations (settings and models in the
  user profile survive; only program files are replaced). Then delete C:\1-AI
  once nothing references it. Do NOT touch D:\Review — that is a decision pile.

PHASE 4 — consolidate to C:\APPS
  Move self-built apps from the root of C: into C:\APPS\<app>. Third-party stays
  in Program Files. Update every reference: NSSM AppDirectory, qi_registry.json,
  CLAUDE.md files, MCP configs, tunnels, scheduled tasks.
  Separate code from data as part of the same pass — apps currently write logs
  and DBs next to their code (C:\QI\LOGS, C:\NEXUS\LOGS, maia.db), which blocks
  Program Files packaging later. Route data through one shared resolver:
    code -> C:\APPS\<app>  |  machine data -> C:\ProgramData\Quiddity Innovations\<app>
    per-user config -> %APPDATA%  |  cache/logs -> %LOCALAPPDATA%
  Move C:\PlayDeck LAST. Also clean up duplicate project-scoped MCP entries in
  ~/.claude.json: C:\QI and C:/QI both hold sqlite-maia, same for C:\NAYA
  and C:/NAYA — path-separator drift, only one spelling takes effect.

PHASE 5 — plan only
  Write a plan for installer packaging (Inno Setup or WiX over PyInstaller or
  Nuitka, plus code signing). Do not build it.

Rules for this run:
  - Take a restore point or note rollback steps before each destructive step.
  - Verify before deleting anything: prove the new location works first.
  - I will need to click UAC prompts — tell me clearly when one is coming.
  - Repoint the MCP servers LAST: it ends this session when Claude Code restarts.
  - Report progress every 5 tasks. Never ask "should I continue".

Loop
```

---

## Why Opus 5

Phases 2–4 touch 31 services running as LocalSystem, involve irreversible
deletes, and require tracing one dependency across NSSM, scheduled tasks, MCP
config and a venv. Mistakes are expensive and the failure modes are ambiguous —
that is the profile the top tier is for. Phase 5 alone would be fine on Sonnet 5.

## Known traps, already verified

| Trap | Why it matters |
|---|---|
| Python installer defaults to per-user | Services run as LocalSystem — must be all-users |
| `C:\1-AI\APPS\PYTHON` is load-bearing | 31 services + 4 tasks + 2 MCP servers + 1 venv |
| AvatarStudio lives inside `C:\1-AI` | Live project — move it, never delete |
| No VSCode found elsewhere on the machine | That portable copy is likely the one in use |
| `C:\PlayDeck` is this session's likely cwd | Move it last, or from a session started at `C:\` |
| Apps write data beside their code | Blocks Program Files packaging — fix during the move |
| Duplicate `C:\QI` / `C:/QI` MCP entries | Only the spelling matching the launch dir takes effect |

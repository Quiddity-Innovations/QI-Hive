# Phases 2-5 (v2) - session starter for 2026-08-09

**Model:** Opus 5
**Start Claude Code from:** `C:\` (NOT `C:\PlayDeck` - that folder moves in Phase 4)

Supersedes `PHASE_2-5_PROMPT.md`. The v1 prompt's Phase 2.1 approach fails - see
`session_summaries\QIH_Migration_Summary_2026-08-08_2250.docx` for why.

---

## The prompt

```
Continuing a migration. Phase 1 (ComfyUI -> D:\AI) completed 2026-08-08.
Phase 2 was ATTEMPTED the same evening and partially failed. Read these first:

  C:\QIH\shared\documentation\session_summaries\QIH_Migration_Summary_2026-08-08_2250.docx
  C:\QIH\shared\documentation\migration_2026-08\inventory.txt
  C:\QIH\shared\documentation\migration_2026-08\phase2\rollback\services_before.csv

STATE RIGHT NOW (verified, machine is healthy, nothing is broken):
  - Python 3.11.9 lives at C:\1-AI\APPS\PYTHON as a PER-USER install.
    All 473 packages intact and importing. 47/52 QI_* services running.
  - C:\Program Files\Python311 does NOT exist.
  - No restart is pending or needed. Do NOT restart this machine.
  - Restore point #141 "QI migration Phase2 pre-Python" exists.
  - Rollback data is in ...\migration_2026-08\phase2\rollback\
  - python-3.11.9-amd64.exe is already downloaded in ...\migration_2026-08\phase2\

WHY PHASE 2.1 FAILED LAST TIME - do not repeat this:
  Running python-3.11.9-amd64.exe with InstallAllUsers=1 TargetDir="C:\Program
  Files\Python311" did NOT install there. The WiX Burn bundle detected the existing
  per-user 3.11.8 as a related bundle, switched to upgrade mode, and on that path it
  IGNORES both TargetDir and InstallAllUsers - it upgraded the old install in place
  instead. It also asked for a restart because python311.dll was in use.

DO PHASE 2.1 THIS WAY INSTEAD (new location works before anything depends on it):
  1. robocopy C:\1-AI\APPS\PYTHON -> C:\Program Files\Python311  (~4.7 GB; Lib is
     4.4 GB). Exclude the nested "venvs" and "testenv" folders - they are venvs with
     hardcoded paths, not part of the interpreter.
  2. Uninstall the per-user bundle {1da2e09b-199c-4def-9a99-93a8c1b8ddf2}
     with /quiet /norestart. Running services keep their mapped DLL and survive.
     Do NOT restart any service during this window.
  3. Install python-3.11.9-amd64.exe /quiet /norestart InstallAllUsers=1
     TargetDir="C:\Program Files\Python311". With no related bundle left it installs
     and registers per-machine correctly. Nothing is executing from that directory
     yet, so there is no file-in-use conflict, and site-packages survives.
  4. ALWAYS pass /norestart to every installer in this migration.

THEN FINISH PHASE 2:
  - Repoint 31 NSSM services (nssm set <name> Application "C:\Program Files\Python311\python.exe").
    The exact list of 31 is in rollback\services_before.csv (filter Application for 1-AI).
  - Repoint 12 scheduled tasks - NOT 4. The v1 prompt undercounted. Eight of them hide
    the python path inside "conhost.exe --headless <python> <script>" arguments, so scan
    Arguments as well as Execute. Full list:
      MaiaNightlySync, OC-ChatGPT-Keepalive, QI_BrainBackfill, QI_ComplianceFast,
      QI_DemoDayStartup, QI_GamezAIPin, QI_McpConnectorGuard, QI_NightlyBackup,
      QI_NightlyGitSync, QI_NightlyReconcile, QI_Ollama_Watchdog,
      Maia\Maia Tunnel Watchdog
    Note QI_NightlyBackup also points at a dead path (C:\UNIVERSAL\qi_brain\tools\
    backup.py) - it has been broken since the UNIVERSAL->QIH migration. Fix or retire it.
  - Recreate C:\CogniBase\.venv on the new Python (recreate, do not edit pyvenv.cfg).
  - Fix registry pollution: HKLM\SOFTWARE\Python\PythonCore\3.11 and the HKCU
    equivalent both point at C:\1-AI\APPS\PYTHON. Correct both before deleting C:\1-AI.
  - Verify each service starts and its health endpoint answers before moving on.

IF YOU REBUILD PACKAGES FROM PIP INSTEAD OF COPYING:
  requirements-new.txt (467 pinned) is ready in phase2\. Two caveats:
   - torch==2.10.0 and torchaudio==2.10.0 are +cpu builds. Plain PyPI gives the CUDA
     wheel. Use --index-url https://download.pytorch.org/whl/cpu for those two.
   - the "openspace" editable install is dangling (C:\CLAUDE\OpenSpace is gone). Drop it.
   - the "cognibase" editable install resolves to C:\CogniBase\Application.

PHASE 3 - retire C:\1-AI
  Move C:\1-AI\APPS\AvatarStudio to C:\APPS\AvatarStudio first - it is a live
  registered QI project (id: avatarstudio, port 7862), not junk. Reinstall VSCode and
  LM Studio to their standard locations (settings and models in the user profile
  survive; only program files are replaced). Then delete C:\1-AI once nothing
  references it. Do NOT touch D:\Review - that is a decision pile.

PHASE 4 - consolidate to C:\APPS
  Move self-built apps from the root of C: into C:\APPS\<app>. Third-party stays in
  Program Files. Update every reference: NSSM AppDirectory, qi_registry.json,
  CLAUDE.md files, MCP configs, tunnels, scheduled tasks.
  Separate code from data as part of the same pass - apps currently write logs and DBs
  next to their code (C:\QI\LOGS, C:\NEXUS\LOGS, maia.db), which blocks Program Files
  packaging later. Route data through one shared resolver:
    code -> C:\APPS\<app>  |  machine data -> C:\ProgramData\Quiddity Innovations\<app>
    per-user config -> %APPDATA%  |  cache/logs -> %LOCALAPPDATA%
  Move C:\PlayDeck LAST. Also clean up duplicate project-scoped MCP entries in
  ~/.claude.json: C:\QI and C:/QI both hold sqlite-maia, same for C:\NAYA and C:/NAYA -
  path-separator drift, only one spelling takes effect.

PHASE 5 - plan only
  Write a plan for installer packaging (Inno Setup or WiX over PyInstaller or Nuitka,
  plus code signing). Do not build it.

Rules for this run:
  - NEVER restart this machine. Pass /norestart to every installer. If something
    claims it needs a reboot, tell me and stop - do not reboot.
  - Elevation: use gsudo (C:\Program Files\gsudo\Current\gsudo.exe), CacheMode=Auto
    with a 24h cache, so one UAC click covers the session. Invoke as:
      gsudo powershell -NoProfile -ExecutionPolicy Bypass -File "C:/forward/slash/path.ps1"
    Use FORWARD SLASHES in paths passed through bash, or the backslashes get eaten.
  - Write ALL .ps1 files as pure ASCII. PowerShell 5.1 reads a BOM-less .ps1 as ANSI,
    and a UTF-8 em dash decodes to a sequence containing a double quote, which breaks
    string parity and produces a cascade of parser errors far from the real line.
  - Take a restore point or note rollback steps before each destructive step.
  - Verify before deleting anything: prove the new location works first.
  - Tell me clearly when a UAC prompt is coming.
  - Repoint the MCP servers (qi-brain, qi-registry in ~/.claude.json) LAST: it ends
    the session when Claude Code restarts. Write the session summary BEFORE that.
  - Report progress every 5 tasks. Never ask "should I continue".

Loop
```

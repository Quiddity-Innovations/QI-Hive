# Continuation prompt — Phase 4 (app consolidation), 2026-08-09

**Start Claude Code from:** `C:\` (NOT `C:\PlayDeck` or any folder still to move)
**Model:** Opus 5

---

## The prompt

```
Continuing the QI migration. Phases 2 and 3 are done; Phase 4 is ~77% through.
Read these first:

  C:\QIH\shared\documentation\migration_2026-08\PHASE_4_Consolidation_Plan.md
  C:\QIH\shared\documentation\session_summaries\QIH_Migration_Summary_2026-08-09_0930.docx
  C:\QIH\shared\documentation\session_summaries\QIH_Migration_Addendum_2026-08-09_1100.docx

STATE (verified, machine healthy, 47 QI_ services running / 5 stopped — the same
5 that were stopped before any of this began):

  - Python 3.11.9 is per-machine at C:\Program Files\Python311. 33 services and
    14 scheduled tasks run on it. DONE, do not revisit.
  - C:\1-AI was renamed to C:\1-AI.RETIRED_2026-08-09 (17.28 GB, Renne deletes
    it by hand). A junction C:\1-AI\APPS\PYTHON -> C:\Program Files\Python311
    remains, because 11 venvs still name the old base. It goes when they are
    rebuilt.
  - 20 of 26 apps are moved to C:\APPS. Originals are held at
    D:\_PREMOVE_2026-08-09\<App> — nothing has been deleted.

RULES FOR THIS RUN (Renne's, non-negotiable):
  - NEVER delete anything. Apps to retire get RENAMED "<App>_for deletion".
    Duplicates get preserved as "<App>_Dupe". Renne deletes, not you.
  - NO junction or pointer folder left at the C: root. C:\<App> must be gone.
    Originals go to D:\_PREMOVE_2026-08-09\.
  - Do not touch D:\Review — cleaned up by Renne, stays for future work.
  - C:\QIH stays at the root. PERMANENT EXCEPTION, decided 2026-08-09.
  - Target end state for C: root: APPS, QIH, TEMP, tmp, and nothing else of
    Renne's.
  - Verify before deleting. Report progress every 5 tasks. Never ask
    "should I continue".

STILL TO MOVE (use C:\QIH\shared\documentation\migration_2026-08\phase2\move_app.py,
which is written, tested and idempotent — dry run first, then --apply):

  1. AutoPDF          - EMPTY leftover dir, locked. Just needs removing.
  2. NEXUS            - EMPTY leftover dir, locked. Just needs removing.
  3. AutoPDF_Portable - 1.4 GB, unregistered, no services. DUPLICATE of AutoPDF
                        -> move to C:\APPS\AutoPDF_Portable_Dupe
  4. QIB              - 0 bytes, empty, unregistered
                        -> rename to "QIB_for deletion" in the hold area
  5. CLAUDE           - 3.8 GB. SPECIAL, see below.
  6. PersonalSong     - 13.5 GB, no services
  7. PlayDeck         - 1.7 GB. MOVE LAST of the apps (Renne's original brief).
  8. ARCHIVE          - 361.7 GB. STOP HERE. Renne wants to review whether any
                        of it is needed before anything happens.

CLAUDE NEEDS SPECIAL HANDLING — do not use the plain mover:
  C:\CLAUDE\Tools\headroom_env is a venv, and QI_Headroom's Application is
  headroom_env\Scripts\headroom.exe. A pip console-script .exe has the venv's
  interpreter path baked into its binary, so moving the folder breaks it even
  though python.exe itself would still work.
  Do this instead: move the folder, then run
     C:\QIH\shared\documentation\migration_2026-08\phase2\fix_console_scripts.py
  adapted to the venv's Scripts dir (it anchors on the PK zip magic and scans
  BACKWARDS for the shebang — a forward scan for b'#!' hits a false positive in
  the launcher stub's own error-string table and produces a binary that dies
  with 0xC0000005; this is tested, do not re-derive it).
  Also: NSSM writes QI_Headroom's logs INTO the venv (headroom_env\logs), so the
  log directory must exist or the service will not start.

TRAPS ALREADY HIT — do not rediscover these:
  - Some app folders survive the move because they hold their own nssm.exe,
    locked by the service it hosts (C:\OC and C:\NEXUS both did). Fix with
    phase2\fix_stray_nssm.ps1 -App <name> -Apply: it repoints the service's
    ImagePath to C:\APPS\<App>\nssm.exe.
  - 'nssm set' FAILS SILENTLY against a service registered by a different nssm
    binary — it reports success while the registry keeps the old value. Write
    to HKLM\SYSTEM\CurrentControlSet\Services\<svc>\Parameters directly and
    read it back.
  - Non-elevated Get-ScheduledTask does not see every task. Always enumerate
    elevated.
  - Scanning for 'QI_*' services misses OC-Keepalive-Service, ClaudeManager,
    NayaTunnel and NEXUSTunnel. Enumerate NSSM-hosted services instead.
  - Backslashes get eaten passing paths through bash to PowerShell. Use forward
    slashes, and write .ps1 files as pure ASCII.
  - A folder can linger empty because a process holds it as its cwd (Renne
    having NEXUS open did this). Bounce the owner or wait for reboot.

AFTER THE MOVES:
  a. Global stale-reference sweep. Per-app moves leave cross-project references
     behind purely from ordering (Retirement Analyzer's CLAUDE.md naming
     TUBESCOUT, etc). One pass at the end catches them all.
     NOTE: move_app.py's text_refs() OVERCOUNTS — its JSON-escaped branch uses
     a plain str.count() with no word boundary, so "C:\\QI" also matches
     "C:\\QIH", "C:\\QIB", "C:\\QIP". The rewrite itself is correctly bounded;
     only the reported number is inflated. Fix the counter before trusting it.
  b. Reinstall VSCode and LM Studio. First attempt FAILED the same way the
     Python install did: winget found the existing registration, flipped to
     upgrade mode, ignored --scope machine, and reinstalled into
     C:\1-AI\APPS\VSCode — recreating that folder next to the junction.
     UNINSTALL FIRST, then install. Script: phase2\p3m_reinstall_vscode.ps1
     (written, never run — Renne stopped it). LM Studio id: ElementLabs.LMStudio
  c. Then drop the last Machine PATH entry naming C:\1-AI\APPS\VSCode.
  d. Remove the duplicate tunnel services NEXUSTunnel and NayaTunnel — both are
     leftovers of the QI_ rename, and NEXUSTunnel is RUNNING alongside
     QI_NEXUSTunnel on the same port 7880.
  e. Dedupe the Brain's project_state: 53 rows for 32 projects. Every project is
     stored twice — once as a full record under its snake_case id, once as a
     status-only stub under its display name. That is why AvatarStudio looked
     missing from the dev view. Renne approved this as a separate pass.
  f. Reconcile fidelityanalyzer (in the Brain, absent from qi_registry.json) and
     MailBrain (on disk, in neither).
  g. Loose FILES at the C: root worth a decision: C:\GANET.rdg, C:\RDCMan.exe.
  h. Third-party at the root, not ours to move: GOOSE, Plex,
     "POWERSPEC - G484 DRIVERS", "Server 2012 R2". Reinstall or archive to D:.
  i. qi-registry MCP will reconnect on Claude Code restart — its two processes
     were killed to free C:\1-AI. Config on disk is already correct.

Loop
```

---

## Quick reference — what exists already

| Tool | Purpose |
|---|---|
| `phase2\move_app.py` | The mover. `--app <name>` dry run, `--apply` to commit. Copies, verifies file counts, repoints services/tasks/text, restarts, retires the original to D:, confirms C:\<App> is gone |
| `phase2\fix_stray_nssm.ps1` | Frees a folder held by its own nssm.exe |
| `phase2\clear_empty_leftovers.ps1` | Removes empty leftover dirs at the C: root |
| `phase2\fix_console_scripts.py` | Rewrites the interpreter baked into pip console-script .exe files |
| `phase2\p3m_reinstall_vscode.ps1` | VSCode uninstall-then-install (written, not run) |
| `phase2\assess_apps.py` | Sizes, duplicates, services, uncommitted git work |
| `phase2\croot_plan.py` | Classifies every C: root folder against the target end state |
| `QIH\engine\common\qi_paths.py` | The code/data path resolver for the separation work |

## Moved so far (20)

AkiyaScout, SCRIPTS, VLCDaemon, MQ, CypherMiner, Lottery Wiz, TUBESCOUT,
Retirement Analyzer, QIP, OC, EasyFlow, NEXUS, MailBrain, Gamez, MapSnap,
CogniBase, AutoPDF, M2V, NAYA, QI

All verified: file counts matched, services restarted, `C:\<App>` gone,
originals held at `D:\_PREMOVE_2026-08-09\`.

## Not yet done from the original brief

**Code/data separation** (`qi_paths.py` adoption) has NOT started. The apps moved
to `C:\APPS` still write logs and DBs beside their code. The resolver is written
and tested; adopting it per-app is the remaining half of Phase 4, and it is the
prerequisite for Phase 5 packaging.

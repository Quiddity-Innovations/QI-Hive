# QI Media Studio (mediastudio) — L2 brief

_Generated 2026-09-10 15:35:33_

## Registry facts
- Path: `C:\APPS\MediaStudio`
- Status: active_development
- Ports: ui:7864
- Notes: Read-only over every source directory: it records where media is and what made it, and never moves, renames or deletes another project's files. Provenance survives the mux - each composition writes a .json manifest naming every voice, prompt and source file. Registered 2026-08-10. | git history lives in C:\APPS\MediaStudio (the source tier since the owner's ruling of 2026-09-10) and on GitHub; D:\Dev\MediaStudio is a plain backup clone. | 2026-09-09: paths repointed D:\Dev -> C:\APPS (app runs from C:\APPS per the 2026-09-02 ruling).

## Brain
- Current state: status=active, phase=Realigned to the C:\APPS source tier; Autopilot v1 flown, review gate pending
  2026-09-10 tier realignment: C:\APPS\MediaStudio is now the git working copy AND the development source (owner's ruling). Repo pushed to github.com/Quiddity-Innovations/MediaStudio (branch dev) - before today the only history was on D:\Dev with no remote at all. The service runs from C:\APPS and proves it: GET /version reports root C:\APPS\MediaStudio, tier "runtime", and the HEAD commit. 119 tests pass, qi_validator 20/20. Config, tools, tests and docs repointed off D:\Dev; plugins.extra_manifests, and AvatarStudio's and VoiceStudio's plug-in launch blocks, all now name C:\APPS (they pointed at D:\Dev launchers that no longer have a .venv - each would have failed silently). session_handoff.py's drift table was inverted to mean "the D:\Dev backup is N commits behind". Autopilot remains engaged=false pending the Fable review gate; that is unchanged by this work. The earlier state note saying "Media Studio deliberately not promoted; the C:\APPS copy is stale" is obsolete - there is no promotion any more.
- Last decisions:
  - Decision 3 closed (Hallo2 10.3 GB); AvatarStudio promoted to C:\APPS as the QI_AvatarStudio service; qi_promote.py created; Ollama unloaded before exclusive steps (2026-09-10)

## CLAUDE.md rules
# QI Media Studio — how Claude works with this project
disk: never edited, never running anything. Registered in
`C:\QIH\ecosystem\qi_registry.json` as `mediastudio`, ui **7864**, block
**8740-8749** reserved.
## 🔴 The rule that defines this project: it generates nothing
| Need | Goes to | Never |
|---|---|---|
| stills, video | ComfyUI :8740 via `D:\AI\workflows` | a model in this venv |
that also means it can never break ComfyUI's transformers version.

## 🔴 The consent gate is not reimplemented here
Never add a bypass, a `--force`, or a "the panel already checked" shortcut.

## 🔴 Read-only over every source
files are; it never moves, renames or deletes them. A scan that writes to a source
directory is a bug.

## 🔴 ComfyUI's registry is the authority on engines
are enabled, and what their defaults are. Read it; never copy values out of it
into this codebase. A disabled engine is **refused, not substituted** — that rule
is the ComfyUI project's and it is inherited here.

## Architecture
because generated video must never be asked to render text: every video model
garbles it, so the overlay is ffmpeg's job and lives in the one ffmpeg layer.

## Two design decisions worth not re-litigating
**Duration comes from narration.** Shots are never given a frame count; a shot
lasts as long as its line plus `tail_seconds`. This is why the format is usable.

> Corrected 2026-08-27. This read "2.4 s" and that figure was never right. The
> engine default was `length: 61`, which is not on MiniMax's 17k+5 frame grid and
> snapped up to 73 frames = **2.92 s**, not 2.4. More to the point, 61 sat *below*
## GPU
## 🔴 The cockpit may start things, but only declared things
is no path parameter, no command field, no override. Do not add a "just this
once" bypass — that turns a loopback panel into a remote shell.

A launcher is always the other project's own `.bat`, never arguments copied out
of one. `Start_ComfyUI.bat` rotates its log and sets `--disable-smart-memory
--reserve-vram 2`; a copy of those flags here would drift the first time ComfyUI
tuned its own launcher. Same rule as `_video_backends.json`: read the authority,
never duplicate it.

Media Studio itself is declared with `"control": "none"`. It is serving the page;
**Turning an engine on is not flying.** The cockpit never starts a render, and
GPU arbitration is still FilmForge's question — see `docs/CONVERGENCE.md`.

is wired, rather than offering buttons that do nothing. When it is built, every
unattended job ships with its own freshness check: `conhost --headless` always
returns 0, so an exit code is never evidence a scheduled run worked.

## 🔴 A session ends on purpose, never by running out
repos and two tiers, and the thing that gets lost is never the code. It is the
knowledge of *which copy is running* and *what was half-done*.

   continue with no other context: what is done, what is left, what must not be
   done, and the gotcha most likely to trip it. Overwrite it — there is exactly
   one current handoff, and git keeps the old ones.
### Scheduling the continuation — two different limits, two different answers
Do not confuse them:

- **Context filled up.** Nothing to schedule. The work can continue immediately
Schedule it for **shortly after the reset time the CLI reported**. If you do not
actually know that time, say so and hand the owner the command — **do not guess a
time and let a cloud run fire into a still-exhausted quota**. A wrong schedule is
worse than none: it burns the first tokens of the new window on a run that
## Suite membership
Modules are discovered from `qi_registry.json`, never hardcoded. A project joins
by having `/health`, `/version`, `/info`, a panel route honouring `?embed=1`, and
a registry entry that mentions it. Adding AvatarStudio must not require editing
`service.py`.

## QI ecosystem compliance
## Related

## Entry points
`MediaStudio_Panel.bat`, `MediaStudio_Stop.bat`, `QI_Autopilot_Control.bat`

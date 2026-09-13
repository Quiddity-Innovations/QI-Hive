# QI Media Studio (mediastudio) — L2 brief

_Generated 2026-09-12 02:35:04_

## Registry facts
- Path: `C:\APPS\MediaStudio`
- Status: active_development
- Ports: ui:7864
- Notes: Read-only over every source directory: it records where media is and what made it, and never moves, renames or deletes another project's files. Provenance survives the mux - each composition writes a .json manifest naming every voice, prompt and source file. Registered 2026-08-10. | git history lives in C:\APPS\MediaStudio (the source tier since the owner's ruling of 2026-09-10) and on GitHub; D:\Dev\MediaStudio is a plain backup clone. | 2026-09-09: paths repointed D:\Dev -> C:\APPS (app runs from C:\APPS per the 2026-09-02 ruling).

## Brain
- Current state: status=active, phase=Teaching sessions done (S3+S4); S5 is GUI consistency + writing the manual
  2026-09-11 (S4): second teaching session complete. Video, fit, music, assembly, av_mux primitives and run records all walked end to end against the running machine, every example producing a file that opens. Deliverable S4_What_Media_Studio_Is (48 s) mixes a card, a generated still with Ken Burns, a generated MiniMax clip looped to fit, four narration lines in one model load, and a ducked music bed - built in 10.2 s from docs/shotlists/s4_studio.json. Preflight found gemma4:26b resident and idle in Ollama holding the card with 0.4 GB free while every cockpit light was green; unloading took it to 13.82 GB. Narration is verified by rendering a real wav now, never by /health. docs/HOWTO_GAPS.md is at 33 items (G27-G33 added). Biggest finding: /api/runs/{id}/rerun is a ComfyUI cache hit, not a re-render (decision 612). G10 is answered - personalsong and m2v were retired by owner decision on 2026-09-10, so the 155 library rows the S3 rescan dropped were deliberate; the implied config edit (drop personalsong_legacy and m2v from library.sources, fix CLAUDE.md's music row) awaits the owner's yes. No docs were fixed: HOWTO.md and CHEATSHEET.md are still wrong on all 33 counts, and S5 writes the manual. Autopilot remains engaged=false pending the Fable review gate. Committed a6e3b6b, pushed, D:\Dev backup pulled.
- Last decisions:
  - Rerun reproduces provenance, it does not re-roll â€” /api/runs/{id}/rerun is a ComfyUI cache hit (2026-09-11)

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

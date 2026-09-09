# QI Media Studio (mediastudio) — L2 brief

_Generated 2026-09-08 17:56:10_

## Registry facts
- Path: `C:\APPS\MediaStudio`
- Status: active_development
- Ports: ui:7864
- Notes: Read-only over every source directory: it records where media is and what made it, and never moves, renames or deletes another project's files. Provenance survives the mux - each composition writes a .json manifest naming every voice, prompt and source file. Registered 2026-08-10. | git history currently only in D:\Dev\Media Studio; C:\APPS copy has no .git — seed per architecture plan Wave 0.9 (pending).

## Brain
- No current_state recorded.
- Last decisions:
  - Hive currency pass 2026-09-08: registry brought to 42 projects; C:\APPS stays the registered path even where git history lives only in D:\Dev; QI-RELAY is a Maia component, not a project (2026-09-08 21:51:31)
  - Trinity health is inspected daily without calling an assistant; every assistant run is recorded in Agent HR as trial evidence (2026-09-08 21:37:12)
  - Codex calls always name the model; CLI default pinned to gpt-5.6-terra; ladder luna â†’ terra â†’ sol, astra only with a stated reason (2026-09-08 21:37:00)

## CLAUDE.md rules
# QI Media Studio — how Claude works with this project
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

## Suite membership
Modules are discovered from `qi_registry.json`, never hardcoded. A project joins
by having `/health`, `/version`, `/info`, a panel route honouring `?embed=1`, and
a registry entry that mentions it. Adding AvatarStudio must not require editing
`service.py`.

## QI ecosystem compliance
## Related

## Entry points
`MediaStudio_Panel.bat`

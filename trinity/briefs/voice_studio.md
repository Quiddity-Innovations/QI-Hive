# QI Voice Studio (voice_studio) — L2 brief

_Generated 2026-09-08 17:56:10_

## Registry facts
- Path: `C:\APPS\VoiceStudio`
- Status: active_development
- Ports: ui:7863
- Notes: Consent gate is mandatory and ships enabled: every voice needs an owner + consent record in data/voices/manifest.json, scoped internal or commercial. Renders write a .json audit sidecar. Code and weights are MIT; supply chain pinned in config/provenance.json. Registered 2026-08-10. | git history currently only in D:\Dev\VoiceStudio; C:\APPS copy has no .git — seed per architecture plan Wave 0.9 (pending).

## Brain
- No current_state recorded.
- Last decisions:
  - Hive currency pass 2026-09-08: registry brought to 42 projects; C:\APPS stays the registered path even where git history lives only in D:\Dev; QI-RELAY is a Maia component, not a project (2026-09-08 21:51:31)
  - Trinity health is inspected daily without calling an assistant; every assistant run is recorded in Agent HR as trial evidence (2026-09-08 21:37:12)
  - Codex calls always name the model; CLI default pinned to gpt-5.6-terra; ladder luna â†’ terra â†’ sol, astra only with a stated reason (2026-09-08 21:37:00)

## CLAUDE.md rules
# QI Voice Studio — how Claude works with this project
## 🔴 The one rule that matters: this is the STUDIO tier
**Never wire this into Claude Voice's conversational path.** `realtime.py`, the LINE and
Telegram bridges, the meeting room on `:8722` and the shared voice API on `:8725` run on
edge-tts at ~300 ms first-audio and must stay there. VibeVoice has no streaming: you wait
for the whole utterance before hearing a word.

cloning**, which collides with the hard rule that Claude sounds like `en-US-AndrewNeural`.
Cloning a Microsoft commercial voice to preserve that timbre is not on the table. This was
decided 2026-08-09; do not re-open it without new facts.

## 🔴 The consent gate is not optional
- Never add a bypass, a `--force`, or a "just this once" path.
- Never widen a voice's scope without Renne saying so explicitly.
- The panel and any future UI must **shell out to the CLIs**, never reimplement rendering,
  so no surface can acquire a softer rule than the command line.
- Voice samples are biometric data: gitignored, loopback-only, never tunneled, never sent
  anywhere.

## Layout
| `vendor/VibeVoice/` | Pinned upstream clone, detached HEAD. Do not track a branch. |

## Ports
## GPU
## Video narration — a deck is data, never a code path
`--deck PATH --out PATH --solo/--male/--female KEY --scope`. Adding a `vs:` voice must
never change behaviour for decks that don't use one.

🔴 **Never put a product name in this codebase.** Until 2026-08-28 the MapSnap and
AutoPDF explainers were Python dicts in `C:\APPS\CLAUDE\Tools\bu_video_scripts.py`,
listed by name in `config/voicestudio.json` as `video_builder.apps`, and the panel
## QI ecosystem compliance
## Environment
transformers pinned 4.51.3 by the vendor. **Do not install this into ComfyUI's embedded
python** — that runs 3.13 / transformers 5.x and the downgrade would break Wan, Qwen3VL and
Ideogram.

## Entry points
`VoiceStudio_AddMyVoice.bat`, `VoiceStudio_Panel.bat`, `VoiceStudio_RenderBUDemo.bat`, `VoiceStudio_TestMyVoice.bat`, `VoiceStudio_Voices.bat`

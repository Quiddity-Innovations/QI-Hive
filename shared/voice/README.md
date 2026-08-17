# QI Shared Voice — canonical pronunciation

Make every QI app that talks say the owner's name (and other words) correctly **in audio only**,
without changing printed/displayed text.

- **`pronounce.py`** — reusable fixer. `pronounce.apply(text)` rewrites text for TTS.
- **`pronunciation.json`** — the map (source of truth). Owner rule: **"Renne" is pronounced "Renee" (ruh-NAY).**

## Adopt in any app (1 line at each TTS call site)
```python
import sys; sys.path.insert(0, r"C:\QIH\shared\voice")
import pronounce
audio_text = pronounce.apply(text)   # synth audio_text; print/display the ORIGINAL text
```
Portable/offline apps may copy `pronounce.py` + `pronunciation.json` next to their code.

Reference implementation: `C:\APPS\CLAUDE\Claude Voice` (speak.py, realtime.py, telegram_bot.py all use it).

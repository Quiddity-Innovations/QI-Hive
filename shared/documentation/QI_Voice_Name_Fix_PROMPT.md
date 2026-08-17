# 🎙️ QI Session Prompt — Fix voice/name pronunciation across ANY app

> **How to use:** open a new Claude Code session in the project you want to fix (or in `C:\QIH`
> for an ecosystem-wide sweep) and paste everything between the lines below as your first message.
> It is self-contained — it tells the session who I am, the rule, the canonical fix, where to look,
> and how to verify. Re-usable for every app that has voice/talk/TTS now or in the future.

---

## ✅ PASTE FROM HERE

**Mission:** Make this app **say my name correctly** — and follow the QI voice standard — anywhere it speaks (TTS / voice notes / avatar narration / read-aloud).

### Who I am (the owner)
- I am **Renne Santiago** (Quiddity Innovations). My name is **spelled "Renne"** but **pronounced like the US name "Renee" (ruh-NAY)**. Most TTS engines read the spelling "Renne" wrong (as "Ren"/"Renn"). Neural TTS says **"Renee"** correctly.
- This has bitten apps before (e.g. **AvatarStudio** mispronounced my name).

### The rule (hard)
1. **Spoken-only fix:** rewrite text *before* it goes to the TTS engine so my name is *said* as "Renee". **Never** change the printed/displayed/subtitle text — only the audio.
2. If this is **Claude's own voice** (e.g. Claude Voice, a Claude assistant), Claude's voice is **MALE** (`en-US-AndrewNeural` / `pt-BR-AntonioNeural`) and his name is always **"Claude"**, never "Andrew". (For other apps/personas, keep their own configured voice — just apply the name-pronunciation fix.)

### Use the canonical fix — do NOT reinvent it
There is a shared, tested component. Reuse it:
- **`C:\QIH\shared\voice\pronounce.py`** + **`C:\QIH\shared\voice\pronunciation.json`** (map: `Renne → Renee`).
- Adopt at **every** TTS call site (one line):
  ```python
  import sys; sys.path.insert(0, r"C:\QIH\shared\voice")
  import pronounce
  audio_text = pronounce.apply(text)   # synthesize audio_text; print/display the ORIGINAL text
  ```
- Portable/offline apps: copy `pronounce.py` + `pronunciation.json` next to the app's code (it still works if the JSON is missing — built-in default).
- Reference implementation that already does this correctly: **`C:\APPS\CLAUDE\Claude Voice`** (`speak.py`, `realtime.py`, `telegram_bot.py`, `pronounce.py`).
- If you find a *new* word/name I pronounce unusually, add it to `C:\QIH\shared\voice\pronunciation.json` (`map`), don't hardcode it.

### Where to look (apps with voice/talk capability)
Check whichever applies to this session; for an ecosystem sweep, do all:
- **AvatarStudio** — `C:\APPS\AvatarStudio`. TTS call sites: `avatar_pipeline.py`, `avatar_studio.py`, `gen_voices_kokoro.py` (Kokoro), `gen_tokyo_times_tts.py`, `test_edge_tts.py`. Apply the fix wherever a script/line is sent to edge-tts **or Kokoro** before render/lip-sync.
- **Claude Voice** — `C:\APPS\CLAUDE\Claude Voice` (already fixed; use as the model).
- **OpenClaw "Koe"** (voice agent), **Maia** (any voice channel/read-aloud) — check if/when they synthesize speech.
- **Anything else:** discover voice apps by grepping the ecosystem for TTS usage, e.g. search project roots under `C:\` for: `edge_tts`, `Communicate(`, `kokoro`, `pyttsx`, `SpeechSynthesizer`, `gTTS`, `elevenlabs`, `azure.*speech`, `.save(` near audio. Each hit is a candidate call site.

### Do this
1. **Discover** every place this app turns text into speech (the call sites above / your greps).
2. **Apply** `pronounce.apply(text)` to the text *right before* synthesis at each site. Leave printed/UI/subtitle text untouched.
3. **Test:** synthesize a line containing my name and confirm it sounds like **"Renee."** Good test line: *"Welcome, Renne — this is Renne speaking."* (Listen, or for headless apps generate the audio file and play it.) Also test any non-English voice the app uses.
4. If this is a Claude persona, also confirm the **MALE voice + name "Claude"** rules hold.

### QI process (follow it)
- Obey `C:\QIH\ecosystem\QI_Architecture_Principles.md` (Six Laws) and `QI_Standards.md`. Registry first if you add anything: `C:\QIH\ecosystem\qi_registry.json`.
- **One MCP tool call per turn** (parallel MCP calls crash the session on Windows).
- If the QI Brain is up at `:9011`, log a short `qi_log_decision` ("adopted QI shared pronunciation fix in <app>") and, for a new reusable bit, `qi_log_feature`. Skip silently if Brain is offline.
- Save a session summary `.docx` to `C:\QIH\shared\documentation\session_summaries\` (`<App>_Summary_YYYY-MM-DD_HHMM.docx`).
- Document what you changed in the app's own docs/CHANGELOG.

### Done when
- Every TTS path in the app routes through `pronounce.apply(...)`.
- A spoken test says my name as **"Renee."**
- Printed/subtitle text is unchanged.
- Change is documented (and Brain-logged if Brain is up).

## ✅ PASTE TO HERE

---

### Notes for me (Renne)
- Canonical fix + map: `C:\QIH\shared\voice\` (`pronounce.py`, `pronunciation.json`, `README.md`).
- Reference app that's already correct: `C:\APPS\CLAUDE\Claude Voice`.
- To teach a new word/name, edit the `map` in `C:\QIH\shared\voice\pronunciation.json`.
- First target to fix with this prompt: **AvatarStudio** (`C:\APPS\AvatarStudio`).

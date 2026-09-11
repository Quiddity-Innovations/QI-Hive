# QI Media Studio — guided component walkthrough (test it together)

Written 2026-09-10. Paste the fenced block under **Prompt** into a fresh Claude Code
session opened in `D:\Dev\MediaStudio`. Model: **Sonnet 5** is enough for this — it is
a guided tour, not a design session. Bump to Opus only if a step fails and the cause is
not obvious.

Budget yourself about **90 minutes** for the full tour, or stop after any checkpoint —
every step ends with a pass/fail line, so a half-done tour is still a useful record.

---

## Prompt

```
QI - S3 - QI Media Studio: Guided component walkthrough - test it together, one step at a time

You are walking me through every component of QI Media Studio, one at a time, and we test
each one together. I drive the clicks; you tell me what to do, what I should see, and you
verify with your own probes (curl, the API, the logs) that what I saw is what happened.
Observe, never assume.

HOW WE WORK
- One step at a time. Present the step, wait for my "next", "pass" or "fail". Never run
  ahead to the next step.
- After each step, print a single line:  [step N] PASS | FAIL | SKIP - one-sentence reason
  and keep a running table. At the end, the table is the deliverable.
- Anything that needs a UAC prompt or a launcher that opens a window is MINE to click.
  Tell me the exact command or .bat and wait.
- Anything you can probe yourself (health endpoints, /api/*, file mtimes, logs), do it
  and quote the actual response, not what the docs say it should be.
- Fix nothing during the tour. Record the failure with the evidence (response body, log
  lines, mtimes), tag it, and move on. We fix in a separate session.

HARD RULES
- Do NOT flip cockpit.autopilot.engaged to true. If I ask for a supervised Autopilot run,
  remind me the switch is mine, wait for my explicit "engage", and set it back to false
  the moment the run finishes.
- Do NOT promote anything to C:\APPS and do NOT copy config/mediastudio.json between
  C:\APPS\MediaStudio and D:\Dev\MediaStudio in either direction. The two copies differ
  on purpose: D:\Dev holds the plug-in layer and Autopilot; C:\APPS is what serves :7864.
  Read the _sync_note at the top of the C:\APPS config if you doubt this.
- Do NOT schedule anything. No task, no trigger.
- Every GPU step: check the GPU chip / nvidia-smi BEFORE and AFTER and report free VRAM.
  Free VRAM is a misleading health signal; contention is what we are watching for.

READ FIRST (in this order, silently): CLAUDE.md, docs/NEXT_SESSION.md (the STATE block
is generated - read the drift table), docs/HOWTO.md, docs/CHEATSHEET.md,
docs/INTERFACE.md, docs/AUTOPILOT_FIRST_RUN.md. Then start at step 0.

THE TOUR

Step 0 - Ground truth (no clicks)
  a. Run: python tools\session_handoff.py  and show me the STATE table and drift table.
  b. Tell me which copy is serving :7864 (probe /api/plugins: 404 means the C:\APPS
     copy, a JSON list means D:\Dev). Say it in one line.
  c. Probe all five cockpit systems from config cockpit.systems and show a table:
     ComfyUI :8740 /system_stats, Voice Studio :7863 /health, AvatarStudio :7862 /health
     + /info, Ollama :11434 /api/tags, Media Studio :7864 /health + /version + /info.
  d. nvidia-smi: what is loaded on the card right now, and how much is free.

Step 1 - Cockpit and pre-flight (panel + API)
  a. I open http://127.0.0.1:7864 and click the System tab. You tell me what chips I
     should see and confirm each via GET /api/cockpit.
  b. POST /api/cockpit/preflight. Show me the readout. Confirm the ollama_unload step
     reports what it did (which models it unloaded, or "nothing resident").
  c. nvidia-smi again: did Ollama's model actually leave the card?

Step 2 - Library (HOWTO step 1)
  a. I search "leaf". You confirm via /api/library/search?q=leaf and /api/library/stats
     that the counts match what I see.
  b. I filter Kind -> audio, then Source -> avatarstudio. You confirm the counts.
  c. I click Rescan. You time it via /api/library/scan and report what changed.

Step 3 - Compose, dry run then render (HOWTO step 2, no GPU for the dry run)
  a. Start from mapsnap_teaser.json -> Load -> Dry run. You read the log and tell me
     shots / narration lines / generations the dry run predicted.
  b. Only when I say "render": Render. You follow /api/jobs/{id} to done, then probe
     the output with engine\av_mux.py probe and report duration, streams, size.
  c. Play it. I say pass or fail on what I see and hear.

Step 4 - Voice Studio and the consent gate
  a. From C:\APPS\VoiceStudio: engine\consent.py - who is registered, which scopes.
  b. Render one line for a registered voice via POST /api/voice/render. Confirm the wav
     exists and its duration.
  c. Negative test: request a voice that is NOT registered for the scope. Expected:
     CONSENT GATE refusal. Quote the refusal text. If it renders anyway, that is a FAIL
     of the highest severity - stop the tour and tell me.

Step 5 - ComfyUI generation
  a. GET /api/generate/options - list what is enabled.
  b. I generate one still from the Generate tab. You follow the job, report the file,
     and confirm the Library indexes it after a rescan with its prompt recovered.
  c. VRAM before / after.

Step 6 - AvatarStudio
  a. /info and /api/jobs on :7862 - what version, what queue.
  b. sc query QI_AvatarStudio - RUNNING? Which path does the service run
     (C:\APPS\AvatarStudio\engine\service.py is the promoted one as of 2026-09-10)?
  c. One talking-head job through Media Studio if a shot type supports it, otherwise
     through AvatarStudio's own panel. VRAM before / after; note the Hallo2 peak.

Step 7 - The plug-in layer (D:\Dev only)
  a. python engine\plugins.py  - the manifest report. Which manifests were found, from
     which source (registry vs extra), and any validation warnings.
  b. python -m pytest tests\test_plugins.py -q  (or unittest if that is what the repo
     uses - check). Report pass/fail counts.
  c. Explain to me in five lines which capability each plug-in serves and what happens
     if Voice Studio is down: a refusal, never a silent skip. Prove it if it is cheap.

Step 8 - Autopilot, read-only (D:\Dev only, engaged stays false)
  a. .venv\Scripts\python.exe engine\autopilot.py docs\projects\autopilot_reference.json --preflight
  b. ... --dry-run   - confirm it executes NOTHING (check the run record's step states).
  c. GET /api/autopilot/runs is a 404 on :7864 (C:\APPS) - so list runs from
     data\autopilot\*.json instead; --verify the most recent done run and explain the
     freshness check to me in three lines.
  d. Optional, only on my explicit "engage": one supervised run, you narrate every
     step and the GPU lease, then set engaged back to false and prove it.

Step 9 - Wrap
  a. Run tools\session_handoff.py again and diff the STATE block against step 0.
  b. Print the final pass/fail table.
  c. Save the table to docs\TEST_WALKTHROUGH_RESULTS_<date>.md, commit it on dev.
  d. Session summary .docx to C:\QIH\shared\documentation\session_summaries\ with the
     MediaStudio_ prefix, and log the session to Brain. Anything tagged FAIL becomes a
     NEXT UP item with its evidence attached.
```

---

## Why the tour is shaped this way

- Steps 0–3 need no GPU and no UAC. If time is short, do those and stop; they cover the
  airframe (panel, library, compose, mux) end to end.
- Steps 4–6 each touch one external engine, in the order the cockpit warms them.
- Steps 7–8 exist only in D:\Dev. The running :7864 service is the C:\APPS copy and has
  no `/api/plugins` or `/api/autopilot/*` routes, which is why those steps use the CLI.
- The consent gate negative test (4c) is the one step that must never be skipped.

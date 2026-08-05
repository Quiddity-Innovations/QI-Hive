# Phase N — Agent War Room (Avatar, Voice & Live Chat)

**Date:** 2026-06-18
**Status:** DRAFT — Stage 0 (text-chat MVP) shipping this session; Stages 1-4 are roadmap
**Owner:** Renne Santiago / Quiddity Innovations
**Author:** hive-architect (Opus 4.8)
**Brain reference:** Feature #297 (recorded 2026-04-20, clarified 2026-05-14)
**Reviewers:** hive-inspector (Five/Six Laws compliance) before hive-builder pickup

---

## 1. Vision & Two Use Cases

Phase N gives **every entity in the QI system a face and a voice**, and a room to meet in. The nine participants:

| # | Participant | Kind | Note |
|---|---|---|---|
| 1 | hive-architect | subagent | designs before building |
| 2 | hive-builder | subagent | implements |
| 3 | hive-inspector | subagent | standards enforcer |
| 4 | hive-ops | subagent | services / infra |
| 5 | hive-scout | subagent | research |
| 6 | hive-scribe | subagent | docs / memory |
| 7 | hive-tester | subagent | verification |
| 8 | Claude Code | interactive | "I think you deserve one" — Renne, 2026-04-20 |
| 9 | Claude Work | interactive | the other Claude surface |

Renne (the owner) is the tenth participant — the human in the room.

The rendering surface is the **War Room** page inside the Hive Dashboard (port **8600**). Two distinct experiences are in scope:

### Use case A — Live video-call feel
Renne talks to one or more agents **live**, Teams/Zoom-style: tiled avatars, the speaker's portrait animates while their voice plays, low latency favoured over fidelity. This is the conversational console.

### Use case B — Async selfie-video messages
An agent records a **phone-style selfie video** explaining something — a design walkthrough, a build summary, an inspector verdict — rendered offline at higher quality and dropped into the thread like a voice note. Latency does not matter; cinematic quality does.

These two cases pull the stack in opposite directions (see section 7, the real-time vs. cinematic tradeoff), which is why the roadmap separates them into different stages.

---

## 2. Current State (Honest Accounting)

There is a gap between what was envisioned and what exists. Recording it plainly so nobody mistakes the monitoring board for the chat vision.

### What /warroom is **today** (2026-06-18, pre-session)
The /warroom route on the Hive Dashboard (render_warroom() in C:\QIH\engine\hive\dashboard\server.py, served by warroom_page()) is a **read-only MONITORING dashboard** — a single-pane-of-glass of: agent heartbeats (last-seen per agent, from agent_heartbeats in qi_brain.db), active projects, and recent dispatches.

It has **no chat, no avatars, no voice, no two-way interaction**. It is a status board that happens to carry the name "War Room."

### What was **envisioned** (Feature #297)
A live, multi-way conversation room with per-agent avatars and voices — the experience described in section 1. None of that exists yet.

### What changes **this session**
1. **Rename the monitoring board → "Mission Control"**, moved to route /mission-control. Its function (heartbeats / projects / dispatches single-pane) is unchanged and remains valuable; only the name and route change so the "War Room" name is freed for its intended purpose.
2. **Reclaim /warroom** for a new, minimal **TEXT-ONLY 4-way agent chat** — Phase N **Stage 0**. No avatars, no voice yet; just a live, persisted, multi-participant message thread that proves the room and the data spine before any media is layered on.

This spec is the roadmap from that text-chat MVP up to the full avatar + voice vision.

> WARNING — **Naming correction:** the task brief and some older notes cite the Brain API on port **9010**. The Brain API is on **9011** — port 9010 is permanently squatted by Logitech G HUB (lghub_agent.exe on 127.0.0.1:9010), moved 2026-05-14 (qi_registry.json -> projects.qi_brain.ports.api). All Stage 0+ wiring targets **9011**.

---

## 3. Constraints (Must Hold True)

- **Registry-first:** no new HTTP port. The War Room is a route on the existing Dashboard (8600); message storage is the existing Brain API (9011). Any new NSSM service (only from Stage 3) is prefixed QI_ and registered in QI_Service_Registry.md.
- **Single source of truth:** all War Room state (messages, avatars) lives in **C:\QIH\data\qi_brain.db** (the live Brain DB — verified this session). No parallel JSON state files.
- **Naming:** lowercase agent_id values (hive-architect, claude_code, claude_work, renne); QI_-prefixed services.
- **Reversibility:** every schema change is additive (CREATE TABLE IF NOT EXISTS / ALTER ADD COLUMN); route changes are config; media generation is opt-in and gated behind a flag.
- **The Five / Six Laws:** registry-first, single source of truth, naming discipline, reversibility, audit completeness — plus **Law 6 (Owner Override + Best-Practice Surfacing):** Renne's calls are final, and the architect must flag where the QI plan diverges from industry best practice (done inline below).
- **Budget:** POC = **free / local tools only** (see section 9). No paid API or cloud GPU without escalation to Renne.

---

## 4. Staged Roadmap

The roadmap is deliberately incremental: each stage is independently shippable, independently valuable, and independently reversible. Media (Stages 1-4) layers on top of a working text spine (Stage 0), never the reverse.

### Stage 0 — Text-Chat MVP (ships this session)

Scope. Reclaim /warroom as a minimal, persisted, multi-way text chat between Renne and the agents. Messages are stored in Brain, rendered by the Dashboard, and pollable. No avatars, no voice. This proves the room, the data model, and the agent POST path.

What ships:
- warroom_messages table in qi_brain.db (schema section 5).
- Brain endpoints: POST /api/warroom/message, GET /api/warroom/messages?since=ID.
- Dashboard /warroom route renders the thread + a compose box; polls GET ...?since= every ~3 s.
- Monitoring board renamed/moved to /mission-control (Mission Control); nav + breadcrumbs updated.

Dependencies. None hard. Brain API (9011) and Dashboard (8600) already run as services. Agents posting into the room is gated on dispatch integration (section 8) but is NOT required for Stage 0: a human (Renne or Claude Code via the Brain endpoint) can post on behalf of an agent so the UI is exercisable day one.

Free/local tools. SQLite (Brain), FastAPI (Brain + Dashboard), Bootstrap (existing Dashboard CSS). Zero new dependencies.

Acceptance criteria.
- [ ] /mission-control serves the former War Room board unchanged; old /warroom board content is reachable at the new route.
- [ ] /warroom shows a live text thread with a working compose box.
- [ ] A message POSTed to POST /api/warroom/message appears in the thread within one poll cycle (<= ~3 s) without a page reload.
- [ ] Messages persist across Dashboard restart (they live in Brain, not memory).
- [ ] agent_id is stored lowercase; sender avatar/voice columns are absent (deferred) and nothing breaks by their absence.

### Stage 1 — Avatars (static portraits + identity)

Scope. Give each of the nine participants a distinct static portrait and a stable visual identity (name, color, role badge). The thread renders each message with the avatar of its sender. This is the first visible step toward the vision and is cheap.

What ships:
- qi_avatars table (schema section 5), seeded with nine rows.
- A portrait per agent: either Ready Player Me exported stills or SDXL-generated portraits (local), stored under C:\QIH\data\avatars\AGENT_ID\portrait.png.
- Dashboard renders sender avatar beside each warroom_messages row; a roster strip shows all nine.

Dependencies. Stage 0 schema + render loop.

Free/local tools. SDXL via local ComfyUI (free) for portraits, or Ready Player Me (free tier) for 3D-style stills. Image files served statically by the Dashboard. No runtime model needed once portraits are baked.

Acceptance criteria.
- [ ] Nine qi_avatars rows exist, each with a portrait_path that resolves to a file on disk.
- [ ] Every message in /warroom renders with the correct sender portrait + name + role color.
- [ ] Missing-portrait fallback: a default silhouette renders rather than a broken image.
- [ ] Portraits are reproducible: the generating prompt/workflow is stored (personality_prompt, comfyui_workflow_json) so an avatar can be regenerated.

### Stage 2 — Voice (TTS per agent)

Scope. Each agent gets a distinct voice. A message can be played back as audio (a read-aloud affordance per message, and eventually auto-play in live mode). Still no video.

What ships:
- voice_engine / voice_id / voice_sample_path columns populated in qi_avatars.
- A TTS render path: text -> per-agent voice -> MP3, cached by message hash under C:\QIH\data\avatars\AGENT_ID\tts\HASH.mp3.
- Dashboard play button per message.

Dependencies. Stage 1 (identity). A render trigger (on-demand button; batch optional).

Free/local tools (validated, Law 6 note below):
- edge-tts — free, fast, no GPU, cloud-hosted Microsoft voices. Best for distinct-but-not-cloned voices and lowest effort. Recommended for the Stage 2 baseline.
- Kokoro — small, fast, fully local, high quality; good middle ground, no cloning.
- XTTS-v2 / F5-TTS — local, voice-cloneable from a short sample. Use when Renne wants a specific designed voice per agent rather than off-the-shelf.

> Law 6 best-practice surfacing. The 2024-era SadTalker/XTTS stack in the original memo still works and is free, but the field has moved. As of early 2026 the strongest local TTS options are Kokoro (speed/size) and F5-TTS (quality/cloning); edge-tts remains the pragmatic free baseline when local GPU time is the constraint. Recommendation: ship Stage 2 on edge-tts for nine instantly-distinct voices, and treat XTTS-v2/F5-TTS cloning as a Stage 2.5 polish only if Renne wants bespoke voices.

Acceptance criteria.
- [ ] Each of the nine agents has an audibly distinct voice.
- [ ] Clicking play on a message renders (or serves cached) audio in the voice of that agent.
- [ ] Audio is cached by content hash: the same message is not re-synthesised twice.
- [ ] No paid API key is required to produce any voice (edge-tts baseline).

### Stage 3 — Lip-Sync Video (async selfie messages) (Use case B)

Scope. Deliver Use case B: an agent records an async selfie-style talking-head video (portrait + voice + lip-sync) rendered offline, dropped into the thread as a video message.

What ships:
- A ComfyUI workflow per agent (the orchestrator choice from Renne): text -> (existing voice MP3 from Stage 2) -> lip-sync -> MP4.
- A batch render service, QI_WarRoomRender (NSSM, QI_-prefixed, registered in QI_Service_Registry.md), that tails a render queue and writes MP4s under C:\QIH\data\avatars\AGENT_ID\video\MESSAGE_ID.mp4.
- warroom_messages.media_path + media_kind=video populated; Dashboard renders an inline player.

Dependencies. Stage 1 (portrait), Stage 2 (voice), local GPU for the animation model, ComfyUI installed.

Free/local tools (validated, Law 6 note):
- LivePortrait — fast, high-quality portrait animation; current best-in-class free local for expressive talking heads.
- SadTalker — older, reliable, lower fidelity; fine as a fallback.
- Hallo2 / EchoMimic — higher fidelity, heavier; reserve for hero clips.

> Law 6 best-practice surfacing. Of the four animators in the original memo, LivePortrait has become the practical default for free local talking-head work (speed + quality); SadTalker is the safe fallback; Hallo2/EchoMimic are quality-max but slow. Recommendation: build the ComfyUI graph around LivePortrait, keep SadTalker as the low-VRAM fallback node.

Acceptance criteria.
- [ ] An agent can produce an MP4 talking-head message from a text input via the ComfyUI graph, end-to-end, with no paid service.
- [ ] The MP4 lands in the thread as an inline-playable message tied to its message_id.
- [ ] Render is queued + batched (does not block the chat); a pending message shows a rendering state.
- [ ] The render service is QI_-prefixed and registered; it has a HALT kill-switch like other Hive services.

### Stage 4 — Live Mode (Use case A)

Scope. Deliver Use case A: the Teams/Zoom-style live room — tiled avatars, the active speaker animates in near-real-time while their voice streams. Latency is prioritised over cinematic fidelity (see section 7).

What ships:
- A real-time path: streamed/low-latency TTS + static-portrait real-time animation (not the batch ComfyUI graph).
- Dashboard live view: avatar tiles, active-speaker highlight, push (WebSocket/SSE) instead of 3 s polling.
- Turn/floor management so multiple agents do not talk over each other.

Dependencies. Stages 1-3 assets; a streaming transport (SSE/WebSocket) added to the Dashboard; dispatch integration fully live so agents can actually be summoned to speak (section 8).

Free/local tools. Real-time-capable TTS (edge-tts streaming / Kokoro), lightweight real-time portrait animation (LivePortrait real-time mode or a 2D mouth-shape approximation), SSE/WebSocket in FastAPI.

Acceptance criteria.
- [ ] Multiple agent tiles render live; the speaking agent tile animates with synced audio.
- [ ] End-to-end speak latency is conversational (target < ~2 s from text-ready to audio start).
- [ ] Floor control prevents overlapping speech (one speaker at a time, or explicit interrupt).
- [ ] Live mode degrades gracefully to Stage 0 text if media services are down.

---

## 5. Data Model

Two tables, both in C:\QIH\data\qi_brain.db. Additive only.

### 5.1 warroom_messages (backs Stage 0 text chat; extended by later stages)

```
CREATE TABLE IF NOT EXISTS warroom_messages (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  thread_id     TEXT    NOT NULL DEFAULT 'main',
  agent_id      TEXT    NOT NULL,
  agent_kind    TEXT,
  role          TEXT    NOT NULL DEFAULT 'message',
  body          TEXT    NOT NULL,
  reply_to      INTEGER,
  media_kind    TEXT,
  media_path    TEXT,
  media_state   TEXT,
  project_id    TEXT,
  meta_json     TEXT,
  created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_warroom_thread_id ON warroom_messages(thread_id, id);
CREATE INDEX IF NOT EXISTS ix_warroom_agent     ON warroom_messages(agent_id, id DESC);
```

Column notes: thread_id = room/topic (main for the single shared room); agent_id lowercase (hive-*, claude_code, claude_work, renne); agent_kind = subagent | interactive | human; role = message | system | status | tool_note; reply_to -> warroom_messages.id for threading; media_kind = NULL(text) | audio | video (Stages 2/3); media_state = NULL | queued | rendering | ready | failed; meta_json = freeform (dispatch_id, model, tokens).

Stage 0 uses only id, thread_id, agent_id, agent_kind, role, body, created_at. The media_* columns are present from day one (so no migration churn later) but stay NULL until Stages 2/3.

### 5.2 qi_avatars (identity + media config; populated from Stage 1)

```
CREATE TABLE IF NOT EXISTS qi_avatars (
  agent_id              TEXT PRIMARY KEY,
  display_name          TEXT NOT NULL,
  role_label            TEXT,
  accent_color          TEXT,
  portrait_path         TEXT,
  voice_engine          TEXT,
  voice_id              TEXT,
  voice_sample_path     TEXT,
  personality_prompt    TEXT,
  comfyui_workflow_json TEXT,
  is_active             INTEGER NOT NULL DEFAULT 1,
  created_at            TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at            TEXT
);
```

Column notes: agent_id matches warroom_messages.agent_id; display_name (Architect, Builder, Claude Code); accent_color hex for badge/tile border; portrait_path PNG (Stage 1); voice_engine = edge-tts | kokoro | xtts | f5 (Stage 2); voice_sample_path cloning sample (Stage 2.5); personality_prompt drives portrait + tone; comfyui_workflow_json parameterized lip-sync graph (Stage 3).

> Note: use the literal datetime('now') in the actual DDL (the sibling Auto-Apply doc flagged a NOW placeholder slip; avoid it here).

---

## 6. Architecture

```
  +-----------------------------+         +------------------------------+
  | Hive Dashboard  (port 8600) |         |  QI Brain API  (port 9011)   |
  |  /warroom   -> text chat UI |  HTTP   |  POST /api/warroom/message   |
  |  /mission-control -> monitor| ------> |  GET  /api/warroom/messages  |
  |  polls GET ...?since=ID 3s  | <------ |      ?thread_id=&since=ID    |
  +-----------------------------+         |  (writes/reads qi_brain.db)  |
        ^ render                          +---------------+--------------+
        |                                                 |
  +-----+-----------+   POST /api/warroom/message  +------v--------------+
  | Renne (compose) | ---------------------------> |  qi_brain.db        |
  | Agents (hooks / | ---------------------------> |  warroom_messages   |
  | dispatch / CLI) |                              |  qi_avatars         |
  +-----------------+                              +---------------------+
```

- Where messages live. All messages and avatar config live in the Brain SQLite at C:\QIH\data\qi_brain.db, served by the Brain API on 9011. The Dashboard holds NO chat state: single source of truth (Law 2). This mirrors the agent_heartbeats pattern already proven for the monitoring board.
- How each agent POSTs. Any client posts to POST /api/warroom/message with {thread_id?, agent_id, agent_kind?, role?, body, reply_to?, project_id?, meta?} and receives the inserted row id. Writers: Renne via the compose box (proxied through the Dashboard), Claude Code / subagents via the SubagentStop/Stop hook envelope, Claude Work via its integration handshake (section 8), and ad-hoc CLI/manual posts. Same contract for all, exactly like the heartbeat endpoint design.
- How the Dashboard renders/polls. /warroom renders the thread server-side on load, then polls GET /api/warroom/messages?thread_id=main&since=lastId every ~3 s and appends new rows client-side. Stage 4 swaps polling for SSE/WebSocket push; the render contract is unchanged.
- Media generation (Stages 2-3) never runs inside the request path. A message is posted with media_state=queued; a separate QI_WarRoomRender service produces the MP3/MP4 and flips media_state=ready with media_path. The chat stays responsive regardless of GPU load.

---

## 7. The Real-Time vs. Cinematic Tradeoff

The two use cases cannot be served by one render path with free/local tools today:

| | Use case A — Live (Stage 4) | Use case B — Async selfie (Stage 3) |
|---|---|---|
| Priority | Latency (conversational) | Fidelity (cinematic) |
| Animation | Real-time static-portrait lip-sync / 2D mouth shapes | Batch ComfyUI graph (LivePortrait/Hallo2) |
| Voice | Streaming TTS (edge-tts/Kokoro) | Pre-rendered, can be cloned (XTTS/F5) |
| Compute | Must fit a live budget on local GPU | Can take seconds to minutes per clip |
| Quality | Good enough to feel live | Looks recorded on a phone, deliberately |

Consequence for sequencing: build the cinematic, batch path first (Stage 3) because it is more forgiving — quality is decoupled from latency, and the assets (portraits, voices, ComfyUI graphs) it produces are exactly what live mode reuses. Live mode (Stage 4) is then the hard optimisation problem (latency under a free-GPU budget), attempted last, with graceful degradation back to text.

---

## 8. Gating, Dependencies & Open Decisions

Hard gates (from Feature #297: implement only after the 4-way integration works):
1. Dispatch integration — agents must be able to be summoned and to post programmatically. Stage 0 does not require it (humans can post), but Stages 3-4 (agents speaking on their own initiative) do.
2. Claude Work handshake — the Claude Work surface must be able to authenticate and POST to the room for it to be a true participant rather than a placeholder tile.

Stage 0 is therefore safe to ship now without either gate. Stages 1-2 (portraits, voice) are also ungated — they are asset + render work. Stages 3-4 are gated on the two items above.

Open decisions for Renne:
- D1 — Avatar source: Ready Player Me 3D stills vs. SDXL local portraits for the nine? (Affects look + reproducibility.) Recommendation: SDXL local — fully free, reproducible from stored prompt, no external account.
- D2 — Voice approach: off-the-shelf distinct voices (edge-tts) vs. designed/cloned voices (XTTS/F5) per agent? Recommendation: edge-tts baseline now, cloning as opt-in Stage 2.5.
- D3 — Single shared room vs. per-agent DM threads (thread_id)? Schema supports both; UI scope differs. Recommendation: single main room for Stage 0; add threads later if needed.
- D4 — Does Renne get a rendered avatar/voice, or is the human always live-on-camera/typed? (Affects whether renne needs a qi_avatars row.)
- D5 — Live transport: SSE vs. WebSocket for Stage 4 push. Recommendation: SSE first (simpler, one-way fits the render-then-play model); WebSocket only if true interrupt is needed.

Escalation triggers (per role rules): escalate to Renne before any paid API/GPU spend, any change touching more than 2 QI projects, or any breaking change to Maia/OpenClaw. None of Stages 0-2 trip these. Stage 3 (new NSSM render service) needs Renne to ratify the service name + run-as account, like QI_HiveApply did.

---

## 9. Cost Note

POC = free / local tools only, per the standing budget rule (POC -> free unless absolutely necessary).

| Layer | Tool | Cost |
|---|---|---|
| Storage / API | SQLite + FastAPI (existing Brain) | Free |
| UI | Bootstrap (existing Dashboard) | Free |
| Portraits | SDXL (local ComfyUI) or Ready Player Me free tier | Free |
| Voice | edge-tts (free cloud) / Kokoro / XTTS / F5 (local) | Free |
| Lip-sync video | LivePortrait / SadTalker / Hallo2 via local ComfyUI | Free (local GPU time only) |
| Orchestration | ComfyUI graphs | Free |

The only non-zero cost is local GPU time for Stages 3-4 renders — no cloud bill, no API key. If Renne later wants a hosted/real-time avatar service (for production polish), that is a paid escalation and out of POC scope.

---

## 10. Handoff

- To hive-inspector: review for Five/Six Laws compliance — confirm no new port, schema is additive, agent_id lowercase, service naming reserved for Stage 3, single-source-of-truth (no Dashboard-local state). Confirm the 9011 (not 9010) Brain port is used everywhere.
- To hive-builder (Stage 0 only, after inspector pass):
  1. CREATE TABLE IF NOT EXISTS warroom_messages + indexes in qi_brain.db (C:\QIH\data\qi_brain.db).
  2. Add POST /api/warroom/message + GET /api/warroom/messages to C:\QIH\engine\brain\api.py.
  3. In C:\QIH\engine\hive\dashboard\server.py: rename the current render_warroom() board to Mission Control and register it at /mission-control; update the nav tuple and the page allowlist accordingly.
  4. Add a new minimal text-chat render_warroom() + /warroom route that posts to / polls the Brain endpoints.
  5. Do NOT touch qi_avatars, voice, or video — those are Stages 1+.
- Risks & rollback: all Stage 0 changes are additive (one new table, two new endpoints, one route rename). Rollback = drop warroom_messages, restore the old /warroom route name, remove the two endpoints. The monitoring board is never deleted — only renamed — so the operational console is never lost.

---

Five/Six Laws self-check: registry-first (no new port); single source of truth (qi_brain.db only); naming (lowercase ids, QI_ service reserved); reversibility (additive schema, route rename not deletion); audit (messages are themselves the ledger); owner override + best-practice surfaced (Law 6 notes on TTS and animator choices inline).

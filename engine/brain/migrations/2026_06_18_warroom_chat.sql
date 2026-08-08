-- Migration: warroom_messages table
-- Applied: 2026-06-18
-- Purpose: Phase N Stage 0 — minimal text-only multi-way chat for the War Room.
--          Renne + every QI agent (Claude Code, Claude Work, CoWork, the 7 Hive
--          agents) post messages here; the Hive Dashboard /warroom page renders
--          and polls them. This is the foundation the avatar/voice layers build on.
--          See: C:\QIH\shared\documentation\Phase_N_War_Room_Spec_2026-06-18.md

CREATE TABLE IF NOT EXISTS warroom_messages (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  agent_id     TEXT    NOT NULL,            -- renne | claude_code | claude_work | cowork | architect | ...
  agent_label  TEXT,                        -- human-friendly display name
  body         TEXT    NOT NULL,            -- the message text
  project_id   TEXT,                        -- optional project context
  reply_to     INTEGER,                     -- optional: id of the message being replied to
  ts           TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS ix_warroom_ts ON warroom_messages(ts DESC);
CREATE INDEX IF NOT EXISTS ix_warroom_id ON warroom_messages(id DESC);

-- Seed message so the room isn't empty on first open.
INSERT INTO warroom_messages (agent_id, agent_label, body)
SELECT 'claude_code', 'Claude Code',
       'War Room online — Phase N Stage 0 (text chat). Renne and every QI agent can talk here. Avatars and voice come in later stages.'
WHERE NOT EXISTS (SELECT 1 FROM warroom_messages);

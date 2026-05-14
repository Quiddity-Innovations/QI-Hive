-- Migration: agent_heartbeats table
-- Applied: 2026-05-13
-- Purpose: Per-agent last-seen tracking for War Room Section 9.
--          Replaces the "assign most-recent project's ts to every card" hack
--          with real per-agent write events from hooks, approve route, and future
--          Claude Work / Claude Chat integrations.

CREATE TABLE IF NOT EXISTS agent_heartbeats (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  agent_id        TEXT    NOT NULL,
  agent_kind      TEXT    NOT NULL,
  project_id      TEXT,
  event           TEXT    NOT NULL,
  session_ref     TEXT,
  model           TEXT,
  ts              TEXT    NOT NULL DEFAULT (datetime('now')),
  meta_json       TEXT
);

CREATE INDEX IF NOT EXISTS ix_heartbeat_agent_ts   ON agent_heartbeats(agent_id, ts DESC);
CREATE INDEX IF NOT EXISTS ix_heartbeat_project_ts ON agent_heartbeats(project_id, ts DESC);

-- One-time backfill: session_log rows that carry an agent_id get a synthetic
-- 'stop' heartbeat so the War Room has historical data on first render.
INSERT INTO agent_heartbeats (agent_id, agent_kind, event, project_id, model, session_ref, ts)
SELECT agent_id, 'interactive', 'stop', project_id, model_used,
       CAST(session_id AS TEXT),
       COALESCE(ended_at, started_at)
FROM session_log
WHERE agent_id IS NOT NULL AND agent_id != '' AND agent_id != 'unknown';

-- QI Brain — Database Schema
-- Plan 001 + Supplement A (I-02, I-05, I-06, I-08, I-14)
-- Apply via: bootstrap.py step 1
-- SQLite 3.x required

-- ─────────────────────────────────────────────────────────────────────────────
-- PRAGMAs (I-02: WAL mode for concurrent write safety)
-- ─────────────────────────────────────────────────────────────────────────────
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 5000;
PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. agents  (I-05: track which agent logged each record)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agents (
    agent_id    TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    agent_type  TEXT NOT NULL CHECK(agent_type IN ('claude','maia','nexus','naya','system')),
    active      INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. llm_providers
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS llm_providers (
    provider_id   TEXT PRIMARY KEY,
    display_name  TEXT NOT NULL,
    provider_type TEXT NOT NULL CHECK(provider_type IN ('ollama','openai','anthropic','nexus_relay','nomic_embed')),
    base_url      TEXT NOT NULL,
    model_name    TEXT NOT NULL,
    api_key_env   TEXT,           -- env var NAME that holds the key (never the key itself)
    role          TEXT NOT NULL,  -- 'eval' | 'embed' | 'general' | 'heavy'
    timeout_s     INTEGER NOT NULL DEFAULT 60,
    max_tokens    INTEGER NOT NULL DEFAULT 2048,
    active        INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. brain_config
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS brain_config (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    description TEXT,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. projects
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS projects (
    project_id   TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    tagline      TEXT,
    path         TEXT,
    api_port     INTEGER,
    ui_port      INTEGER,
    tier         TEXT NOT NULL DEFAULT 'project',  -- 'backbone' | 'project' | 'tool'
    active       INTEGER NOT NULL DEFAULT 1,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. project_state
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS project_state (
    state_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  TEXT NOT NULL REFERENCES projects(project_id),
    agent_id    TEXT NOT NULL DEFAULT 'claude' REFERENCES agents(agent_id),
    phase       TEXT NOT NULL,
    status      TEXT NOT NULL,  -- 'active' | 'paused' | 'blocked' | 'complete'
    summary     TEXT NOT NULL,
    blockers    TEXT,
    next_steps  TEXT,
    recorded_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. decisions  (I-05: agent_id, I-08: superseded columns)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS decisions (
    decision_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id       TEXT NOT NULL REFERENCES projects(project_id),
    agent_id         TEXT NOT NULL DEFAULT 'claude' REFERENCES agents(agent_id),
    decision_code    TEXT UNIQUE,   -- e.g. 'AD-001', optional human-readable key
    title            TEXT NOT NULL,
    rationale        TEXT NOT NULL,
    impact_scope     TEXT NOT NULL DEFAULT 'project',  -- 'project' | 'ecosystem' | 'global'
    tags             TEXT,          -- JSON array of strings
    superseded_by    INTEGER REFERENCES decisions(decision_id),
    superseded_at    TEXT,
    superseded_reason TEXT,
    recorded_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_decisions_project  ON decisions(project_id);
CREATE INDEX IF NOT EXISTS idx_decisions_scope    ON decisions(impact_scope);
CREATE INDEX IF NOT EXISTS idx_decisions_active   ON decisions(superseded_by) WHERE superseded_by IS NULL;

-- ─────────────────────────────────────────────────────────────────────────────
-- 7. features
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS features (
    feature_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    source_project  TEXT NOT NULL REFERENCES projects(project_id),
    logged_by_agent TEXT NOT NULL DEFAULT 'claude' REFERENCES agents(agent_id),
    name            TEXT NOT NULL,
    description     TEXT NOT NULL,
    domain          TEXT NOT NULL,   -- 'ui' | 'api' | 'llm' | 'data' | 'infra' | 'pattern'
    code_ref        TEXT,            -- file path or function name
    propagated      INTEGER NOT NULL DEFAULT 0,  -- 1 = engine has run evaluations
    recorded_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_features_project    ON features(source_project);
CREATE INDEX IF NOT EXISTS idx_features_propagated ON features(propagated);

-- ─────────────────────────────────────────────────────────────────────────────
-- 8. feature_evaluations  (I-05: agent_id)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS feature_evaluations (
    eval_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_id       INTEGER NOT NULL REFERENCES features(feature_id),
    target_project   TEXT NOT NULL REFERENCES projects(project_id),
    agent_id         TEXT NOT NULL DEFAULT 'system' REFERENCES agents(agent_id),
    relevance_score  REAL NOT NULL CHECK(relevance_score >= 0 AND relevance_score <= 1),
    recommendation   TEXT NOT NULL CHECK(recommendation IN ('adopt','adapt','skip','discuss')),
    reasoning        TEXT NOT NULL,
    confidence       REAL NOT NULL DEFAULT 1.0,
    eval_model       TEXT NOT NULL,
    decided          INTEGER NOT NULL DEFAULT 0,   -- 1 = Renne has reviewed
    decided_at       TEXT,
    decided_action   TEXT,
    evaluated_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_evals_feature  ON feature_evaluations(feature_id);
CREATE INDEX IF NOT EXISTS idx_evals_target   ON feature_evaluations(target_project);
CREATE INDEX IF NOT EXISTS idx_evals_pending  ON feature_evaluations(decided) WHERE decided = 0;

-- ─────────────────────────────────────────────────────────────────────────────
-- 9. evaluation_overrides  (I-14: Renne override mechanism)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS evaluation_overrides (
    override_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    evaluation_id      INTEGER NOT NULL REFERENCES feature_evaluations(eval_id),
    overridden_by      TEXT NOT NULL DEFAULT 'renne',
    new_recommendation TEXT NOT NULL CHECK(new_recommendation IN ('adopt','adapt','skip','discuss')),
    reason             TEXT NOT NULL,
    created_at         TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 10. session_log  (I-05: agent_id)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS session_log (
    session_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      TEXT NOT NULL REFERENCES projects(project_id),
    agent_id        TEXT NOT NULL DEFAULT 'claude' REFERENCES agents(agent_id),
    session_title   TEXT NOT NULL,
    summary         TEXT NOT NULL,
    decisions_made  INTEGER NOT NULL DEFAULT 0,
    features_logged INTEGER NOT NULL DEFAULT 0,
    files_changed   TEXT,   -- JSON array
    next_steps      TEXT,
    model_used      TEXT,
    started_at      TEXT,
    ended_at        TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_sessions_project ON session_log(project_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 11. bootstrap_log  (I-06: idempotent bootstrap tracking)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bootstrap_log (
    step_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    step_name    TEXT NOT NULL UNIQUE,
    status       TEXT NOT NULL CHECK(status IN ('pending','running','done','failed')),
    detail       TEXT,
    completed_at TEXT
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Seed data — agents
-- ─────────────────────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO agents (agent_id, display_name, agent_type) VALUES
    ('claude',  'Claude Code',         'claude'),
    ('system',  'QI Brain System',     'system'),
    ('maia',    'Maia AI Assistant',   'maia'),
    ('nexus',   'NEXUS Scout Engine',  'nexus'),
    ('naya',    'Naya Assistant',      'naya');

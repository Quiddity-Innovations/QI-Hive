-- Migration: 2026_05_13_auto_apply
-- Adds auto-apply pipeline columns to dispatches and creates dispatch_runs table.
-- Safe to re-run: ALTER TABLE fails silently via Python runner; CREATE TABLE uses IF NOT EXISTS.

ALTER TABLE dispatches ADD COLUMN apply_state    TEXT;
ALTER TABLE dispatches ADD COLUMN apply_run_id   INTEGER;
ALTER TABLE dispatches ADD COLUMN applied_at     TEXT;
ALTER TABLE dispatches ADD COLUMN applied_commit TEXT;

CREATE TABLE IF NOT EXISTS dispatch_runs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    dispatch_id      TEXT    NOT NULL,
    state            TEXT    NOT NULL,
    builder_log      TEXT,
    inspector_verdict TEXT,
    inspector_reasons TEXT,
    diff_path        TEXT,
    worktree_path    TEXT,
    commit_sha       TEXT,
    started_at       TEXT    DEFAULT (datetime('now')),
    finished_at      TEXT,
    error            TEXT,
    meta             TEXT
);

CREATE INDEX IF NOT EXISTS ix_runs_state    ON dispatch_runs(state);
CREATE INDEX IF NOT EXISTS ix_runs_dispatch ON dispatch_runs(dispatch_id);

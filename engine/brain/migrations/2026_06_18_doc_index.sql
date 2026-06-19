-- QI Brain — Documentation Index + Knowledge Graph
-- Added 2026-06-18 to power the Documentation Brain ("TheBrain-style" Plex) and
-- the hive-librarian agent. The `docs` table is the catalog (one row per file);
-- `doc_relationships` holds the typed edges that turn the catalog into a graph.
-- Idempotent — safe to re-run. Also self-ensured by doc_harvester.py.

-- 1. docs — catalog of every documentation file in the ecosystem
CREATE TABLE IF NOT EXISTS docs (
    doc_id       TEXT PRIMARY KEY,            -- sha1 of normalized path (stable)
    path         TEXT NOT NULL UNIQUE,
    title        TEXT,
    project_id   TEXT,                        -- best-effort, may be NULL
    doc_type     TEXT,                        -- session_summary|standard|implementation_log|
                                              -- meeting_minutes|version_history|readme|changelog|
                                              -- architecture|guide|other
    fmt          TEXT,                        -- md|docx
    size_bytes   INTEGER,
    content_hash TEXT,                        -- sha256 of extracted text
    mtime        TEXT,                        -- file mtime, ISO
    word_count   INTEGER,
    embedded     INTEGER NOT NULL DEFAULT 0,  -- 1 = present in qi_docs Chroma collection
    stale        INTEGER NOT NULL DEFAULT 0,  -- 1 = flagged stale by the librarian
    stale_reason TEXT,
    indexed_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_docs_project ON docs(project_id);
CREATE INDEX IF NOT EXISTS idx_docs_type    ON docs(doc_type);
CREATE INDEX IF NOT EXISTS idx_docs_stale   ON docs(stale) WHERE stale = 1;

-- 2. doc_relationships — the graph edges (the "links" in a TheBrain Plex)
CREATE TABLE IF NOT EXISTS doc_relationships (
    rel_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    src_type   TEXT NOT NULL,   -- doc|project|decision|feature|session
    src_id     TEXT NOT NULL,
    edge_type  TEXT NOT NULL,   -- belongs_to|references|links_to|mentions|supersedes|describes
    dst_type   TEXT NOT NULL,
    dst_id     TEXT NOT NULL,
    weight     REAL NOT NULL DEFAULT 1.0,
    source     TEXT,            -- path|wikilink|mention|manual
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(src_type, src_id, edge_type, dst_type, dst_id)
);
CREATE INDEX IF NOT EXISTS idx_rel_src ON doc_relationships(src_type, src_id);
CREATE INDEX IF NOT EXISTS idx_rel_dst ON doc_relationships(dst_type, dst_id);

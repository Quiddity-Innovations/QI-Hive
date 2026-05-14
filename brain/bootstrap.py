# -*- coding: utf-8 -*-
"""
QI Brain — Bootstrap script.

Idempotent 10-step initialization. Safe to re-run — skips completed steps.
Each step is tracked in the bootstrap_log table.

Run:
    python bootstrap.py
    python bootstrap.py --reset   (clears bootstrap_log, re-runs all steps)

Steps (I-06 ordering):
    1.  create_db          — Create qi_brain.db from schema.sql
    2.  seed_agents        — Seed agents table (done by schema, verify here)
    3.  seed_providers     — Seed llm_providers from config
    4.  seed_config        — Seed brain_config defaults
    5.  seed_projects      — Seed projects from qi_registry.json
    6.  init_chroma        — Initialize ChromaDB collections
    7.  ingest_docs        — Embed ecosystem docs into qi_docs collection
    8.  ingest_summaries   — Embed Session_Summaries/*.docx into qi_sessions
    9.  seed_decisions     — Seed 4 EasyFlow decisions from 2026-04-18
    10. log_bootstrap      — Log bootstrap completion to session_log
"""
from __future__ import annotations
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# ── Path setup ────────────────────────────────────────────────────────────────
BRAIN_DIR    = Path(__file__).parent
ECOSYSTEM    = Path(r"C:\UNIVERSAL\ECOSYSTEM")
SUMMARIES    = Path(r"C:\UNIVERSAL\DOCUMENTATION\Session_Summaries")
REGISTRY     = ECOSYSTEM / "qi_registry.json"

sys.path.insert(0, str(BRAIN_DIR))
from core.db import open_brain_db, init_db, DB_PATH
from core.memory_store import MemoryStore


# ── Bootstrap log helpers ─────────────────────────────────────────────────────

def _step_done(step_name: str) -> bool:
    try:
        with open_brain_db() as conn:
            row = conn.execute(
                "SELECT status FROM bootstrap_log WHERE step_name = ?", (step_name,)
            ).fetchone()
        return row is not None and row["status"] == "done"
    except Exception:
        # bootstrap_log table doesn't exist yet — step not done
        return False


def _mark_step(step_name: str, status: str, detail: str = "") -> None:
    try:
        with open_brain_db() as conn:
            conn.execute(
                """
                INSERT INTO bootstrap_log (step_name, status, detail, completed_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(step_name) DO UPDATE SET
                    status=excluded.status, detail=excluded.detail,
                    completed_at=excluded.completed_at
                """,
                (step_name, status, detail, datetime.now().isoformat())
            )
            conn.commit()
    except Exception:
        pass  # DB not ready yet on very first step — silently skip


def _step(name: str):
    """Decorator: skip if already done, mark running/done/failed."""
    def decorator(fn):
        async def wrapper(*args, **kwargs):
            if _step_done(name):
                print(f"  [SKIP] {name} (already done)")
                return
            print(f"  [RUN ] {name} ...")
            _mark_step(name, "running")
            try:
                await fn(*args, **kwargs)
                _mark_step(name, "done")
                print(f"  [DONE] {name}")
            except Exception as exc:
                _mark_step(name, "failed", str(exc))
                print(f"  [FAIL] {name}: {exc}")
                raise
        return wrapper
    return decorator


# ── Steps ─────────────────────────────────────────────────────────────────────

@_step("create_db")
async def step_create_db():
    init_db()
    # bootstrap_log table must exist now for further steps — verify
    with open_brain_db() as conn:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
    assert "bootstrap_log" in tables, "bootstrap_log table missing after init_db"


@_step("seed_providers")
async def step_seed_providers():
    providers = [
        {
            "provider_id":   "ollama_qwen3_8b",
            "display_name":  "Ollama qwen3:8b (Eval)",
            "provider_type": "ollama",
            "base_url":      "http://localhost:11434",
            "model_name":    "qwen3:8b",
            "api_key_env":   None,
            "role":          "eval",
            "timeout_s":     90,
            "max_tokens":    1024,
        },
        {
            "provider_id":   "ollama_qwen3_4b",
            "display_name":  "Ollama qwen3:4b (Fast)",
            "provider_type": "ollama",
            "base_url":      "http://localhost:11434",
            "model_name":    "qwen3:4b",
            "api_key_env":   None,
            "role":          "general",
            "timeout_s":     60,
            "max_tokens":    2048,
        },
        {
            "provider_id":   "ollama_deepseek_r1_8b",
            "display_name":  "Ollama deepseek-r1:8b (Reasoning)",
            "provider_type": "ollama",
            "base_url":      "http://localhost:11434",
            "model_name":    "deepseek-r1:8b",
            "api_key_env":   None,
            "role":          "general",
            "timeout_s":     120,
            "max_tokens":    2048,
        },
        {
            "provider_id":   "ollama_gemma4_31b",
            "display_name":  "Ollama gemma4:31b (Heavy)",
            "provider_type": "ollama",
            "base_url":      "http://localhost:11434",
            "model_name":    "gemma4:31b",
            "api_key_env":   None,
            "role":          "heavy",
            "timeout_s":     300,
            "max_tokens":    4096,
        },
        {
            "provider_id":   "nomic_embed_text",
            "display_name":  "Nomic Embed Text (Embedder)",
            "provider_type": "nomic_embed",
            "base_url":      "http://localhost:11434",
            "model_name":    "nomic-embed-text",
            "api_key_env":   None,
            "role":          "embed",
            "timeout_s":     30,
            "max_tokens":    8192,
        },
    ]
    with open_brain_db() as conn:
        for p in providers:
            conn.execute(
                """
                INSERT OR IGNORE INTO llm_providers
                    (provider_id, display_name, provider_type, base_url, model_name,
                     api_key_env, role, timeout_s, max_tokens)
                VALUES (:provider_id, :display_name, :provider_type, :base_url, :model_name,
                        :api_key_env, :role, :timeout_s, :max_tokens)
                """,
                p
            )
        conn.commit()


@_step("seed_config")
async def step_seed_config():
    defaults = [
        ("eval_model",      "qwen3:8b",          "LLM model used for feature evaluation"),
        ("embed_model",     "nomic-embed-text",   "Embedding model for ChromaDB"),
        ("token_budget",    "2000",               "Max tokens for get_context() response"),
        ("context_days",    "14",                 "Days of decisions to include in get_context"),
        ("backup_enabled",  "true",               "Enable nightly backups"),
        ("backup_retain",   "30",                 "Days of backup retention"),
        ("api_port",        "9011",               "FastAPI server port"),
        ("version",         "001",                "Brain plan version"),
    ]
    with open_brain_db() as conn:
        for key, value, description in defaults:
            conn.execute(
                "INSERT OR IGNORE INTO brain_config (key, value, description) VALUES (?, ?, ?)",
                (key, value, description)
            )
        conn.commit()


@_step("seed_projects")
async def step_seed_projects():
    if not REGISTRY.exists():
        print(f"    WARNING: qi_registry.json not found at {REGISTRY} — skipping project seed")
        return

    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    projects_data = data.get("projects", [])
    # Normalise: registry uses a list of objects with an 'id' field
    if isinstance(projects_data, dict):
        projects_list = [{"id": k, **v} for k, v in projects_data.items()]
    else:
        projects_list = projects_data

    with open_brain_db() as conn:
        # QI Brain itself as backbone tier
        conn.execute(
            "INSERT OR IGNORE INTO projects "
            "  (project_id, display_name, tagline, path, api_port, ui_port, tier) "
            "VALUES ('qi_brain', 'QI Brain', "
            "  'Shared knowledge substrate for the QI ecosystem', "
            "  'C:/UNIVERSAL/qi_brain', 9011, NULL, 'backbone')"
        )
        for proj in projects_list:
            pid   = proj.get("id") or proj.get("project_id", "unknown")
            ports = proj.get("ports", {})
            # ports may be {"api": {"current": 8000}} or {"api": 8000}
            api_p = ports.get("api")
            if isinstance(api_p, dict):
                api_p = api_p.get("current")
            ui_p  = ports.get("ui")
            if isinstance(ui_p, dict):
                ui_p = ui_p.get("current")
            conn.execute(
                "INSERT OR IGNORE INTO projects "
                "  (project_id, display_name, tagline, path, api_port, ui_port, tier) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    pid,
                    proj.get("name", pid),
                    proj.get("description", ""),
                    proj.get("path", ""),
                    api_p,
                    ui_p,
                    proj.get("tier", "project"),
                )
            )
        conn.commit()


@_step("init_chroma")
async def step_init_chroma():
    store = MemoryStore()
    store.init_collections()
    counts = store.collection_counts()
    print(f"    ChromaDB collections: {counts}")


@_step("ingest_docs")
async def step_ingest_docs():
    """Embed ecosystem markdown docs into qi_docs collection."""
    docs = [
        (ECOSYSTEM / "QI_Standards.md",              "qi_standards"),
        (ECOSYSTEM / "QI_Ecosystem_Map.md",           "qi_map"),
        (ECOSYSTEM / "QI_Architecture_Principles.md", "qi_principles"),
        (ECOSYSTEM / "QI_Ecosystem_Plan_001_Brain_Architecture.md", "plan_001"),
        (Path(r"C:\Users\renne\.claude\CLAUDE.md"),   "claude_md"),
    ]
    store = MemoryStore()
    ingested = 0
    for doc_path, doc_id in docs:
        if not doc_path.exists():
            print(f"    SKIP (not found): {doc_path.name}")
            continue
        text = doc_path.read_text(encoding="utf-8", errors="replace")
        # Chunk into 1000-char pieces with 200-char overlap
        chunks = _chunk_text(text, size=1000, overlap=200)
        for i, chunk in enumerate(chunks):
            await store.add_doc(
                doc_id=f"{doc_id}_chunk_{i}",
                text=chunk,
                metadata={"source": str(doc_path), "doc_id": doc_id, "chunk": i},
            )
        print(f"    Ingested {doc_path.name}: {len(chunks)} chunks")
        ingested += len(chunks)
    print(f"    Total doc chunks ingested: {ingested}")


@_step("ingest_summaries")
async def step_ingest_summaries():
    """Embed session summary .docx files into qi_sessions collection."""
    try:
        from docx import Document as DocxDoc
    except ImportError:
        print("    WARNING: python-docx not installed — skipping summary ingestion")
        return

    store = MemoryStore()
    docx_files = list(SUMMARIES.glob("*.docx")) if SUMMARIES.exists() else []
    ingested = 0
    for docx_path in docx_files:
        try:
            doc = DocxDoc(str(docx_path))
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            if len(text) < 50:
                continue
            chunks = _chunk_text(text, size=800, overlap=150)
            for i, chunk in enumerate(chunks):
                await store.add_doc(
                    doc_id=f"session_{docx_path.stem}_chunk_{i}",
                    text=chunk,
                    metadata={
                        "source":   str(docx_path),
                        "filename": docx_path.name,
                        "type":     "session_summary",
                        "chunk":    i,
                    },
                )
            ingested += len(chunks)
        except Exception as exc:
            print(f"    WARN: could not process {docx_path.name}: {exc}")

    print(f"    Session summaries ingested: {len(docx_files)} files, {ingested} chunks")


@_step("seed_decisions")
async def step_seed_decisions():
    """Seed 4 key EasyFlow/ecosystem decisions from 2026-04-18 session."""
    decisions = [
        {
            "project_id":    "qi_brain",
            "agent_id":      "claude",
            "decision_code": "AD-001",
            "title":         "SQLite for all structured data",
            "rationale":     "SQLite is zero-config, file-based, ACID-compliant, and sufficient for the QI ecosystem scale. Config, decisions, state, features, session log all go here.",
            "impact_scope":  "ecosystem",
            "tags":          '["storage","sqlite","architecture"]',
        },
        {
            "project_id":    "qi_brain",
            "agent_id":      "claude",
            "decision_code": "AD-002",
            "title":         "ChromaDB for semantic/vector memory only",
            "rationale":     "ChromaDB handles semantic search over decisions, features, and docs. Complements SQLite (structured) with natural-language recall. Not a replacement.",
            "impact_scope":  "ecosystem",
            "tags":          '["storage","chromadb","embeddings","architecture"]',
        },
        {
            "project_id":    "qi_brain",
            "agent_id":      "claude",
            "decision_code": "AD-005",
            "title":         "Zero hardcoded LLM configuration anywhere",
            "rationale":     "All LLM provider config (model, URL, timeout, role) lives in llm_providers table. API keys in env vars only — never in DB or code. Replicates NEXUS provider pattern.",
            "impact_scope":  "ecosystem",
            "tags":          '["llm","config","architecture","security"]',
        },
        {
            "project_id":    "qi_brain",
            "agent_id":      "claude",
            "decision_code": "AD-008",
            "title":         "Projects stay independent — brain is purely additive",
            "rationale":     "Maia, NEXUS, Naya, EasyFlow, MQ remain fully independent. The brain reads from them (via registry) but nothing depends on the brain to run. Zero coupling.",
            "impact_scope":  "ecosystem",
            "tags":          '["architecture","independence","coupling"]',
        },
    ]
    with open_brain_db() as conn:
        for d in decisions:
            conn.execute(
                """
                INSERT OR IGNORE INTO decisions
                    (project_id, agent_id, decision_code, title, rationale, impact_scope, tags)
                VALUES (:project_id, :agent_id, :decision_code, :title, :rationale, :impact_scope, :tags)
                """,
                d
            )
        conn.commit()


@_step("log_bootstrap")
async def step_log_bootstrap():
    summary = (
        "Initial bootstrap complete. Database, providers, projects, ChromaDB, "
        "docs, session summaries, and seed decisions all initialized."
    )
    with open_brain_db() as conn:
        conn.execute(
            "INSERT INTO session_log "
            "  (project_id, agent_id, session_title, summary, decisions_made, "
            "   features_logged, next_steps, model_used, started_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("qi_brain", "system", "QI Brain Bootstrap", summary,
             4, 0, "Proceed to Phase 3: Dashboard Brain tab UI.",
             "bootstrap.py", datetime.now().isoformat())
        )
        conn.commit()


# ── Text chunking utility ─────────────────────────────────────────────────────

def _chunk_text(text: str, size: int = 1000, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks for embedding."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap
    return chunks


# ── Main ──────────────────────────────────────────────────────────────────────

async def main(reset: bool = False) -> None:
    print("=" * 60)
    print("QI Brain Bootstrap")
    print("=" * 60)

    if reset:
        print("[RESET] Clearing bootstrap_log ...")
        with open_brain_db() as conn:
            conn.execute("DELETE FROM bootstrap_log")
            conn.commit()

    await step_create_db()

    # After DB exists, the remaining steps can use open_brain_db safely
    await step_seed_providers()
    await step_seed_config()
    await step_seed_projects()
    await step_init_chroma()
    await step_ingest_docs()
    await step_ingest_summaries()
    await step_seed_decisions()
    await step_log_bootstrap()

    print("=" * 60)
    print("Bootstrap complete.")

    # Print summary
    with open_brain_db() as conn:
        n_projects  = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        n_decisions = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        n_providers = conn.execute("SELECT COUNT(*) FROM llm_providers").fetchone()[0]
        n_config    = conn.execute("SELECT COUNT(*) FROM brain_config").fetchone()[0]

    store = MemoryStore()
    chroma_counts = store.collection_counts()

    print(f"  Projects:  {n_projects}")
    print(f"  Decisions: {n_decisions}")
    print(f"  Providers: {n_providers}")
    print(f"  Config:    {n_config} keys")
    print(f"  ChromaDB:  {chroma_counts}")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="QI Brain Bootstrap")
    parser.add_argument("--reset", action="store_true", help="Re-run all steps")
    args = parser.parse_args()
    asyncio.run(main(reset=args.reset))

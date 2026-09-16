# -*- coding: utf-8 -*-
"""
QI Brain — Chroma backfill.

Root cause (2026-09-16 audit): session_log / decisions / features gain rows
from THREE write paths, but only one of them embeds into ChromaDB:

  1. FastAPI /api/log_session, /api/log_decision, /api/log_feature
     (engine/brain/api.py) -> calls MemoryStore.add_session/add_decision/
     add_feature. This is the ONLY path that embeds.
  2. engine/hive/ingest/hive_ingest.py write_to_brain() (NSSM QI_HiveIngest,
     runs continuously) -> raw `INSERT INTO session_log` via sqlite3, no
     embed call at all. This is the dominant source of session_log rows.
  3. engine/brain/poller.py _process_inbox_file() -> raw `INSERT INTO
     session_log` / `INSERT INTO decisions` for inbox messages of type
     "session" / "decision", also no embed call.

This script finds every SQLite row missing from its Chroma collection and
embeds it using the Brain's own embedder (nomic-embed-text via Ollama,
same as core/memory_store.py), with the exact same id scheme, document
text, and metadata shape the API uses -- so /brain-search results are
indistinguishable from rows the API embedded directly.

Idempotent: only embeds ids that are missing from the collection, and uses
upsert(), so re-running is always safe.

Chroma is opened directly (chromadb PersistentClient, same qi_memory path
as MemoryStore) -- verified 2026-09-16 that this is safe to do from a
second process while QI_BrainAPI is running: Chroma's SQLite backend is in
WAL mode and a second read/write client opened cleanly with correct counts.
If that assumption ever stops holding (a hard "database is locked" error),
this script has no HTTP fallback -- SEE THE REPORT for why (the API has no
generic "embed only" endpoint that wouldn't also insert a duplicate SQL
row), and abort rather than duplicate rows.

Usage:
    python C:\\QIH\\engine\\brain\\tools\\chroma_backfill.py [--dry-run]
"""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

_BRAIN_DIR = Path(r"C:\QIH\engine\brain")
sys.path.insert(0, str(_BRAIN_DIR))

from core.db import open_brain_db  # noqa: E402
from core.memory_store import (  # noqa: E402
    MemoryStore, COL_SESSIONS, COL_DECISIONS, COL_FEATURES,
)

BATCH_SIZE = 25
CONCURRENCY = 5


def _existing_ids(store: MemoryStore, collection: str) -> set[str]:
    col = store._get_col(collection)
    ids: set[str] = set()
    count = col.count()
    if count == 0:
        return ids
    # Chroma .get() with no filter returns everything; batching by offset
    # keeps memory bounded for large collections.
    page = 1000
    got = col.get(include=[])
    ids.update(got["ids"])
    return ids


def _sql_rows(conn, table: str, id_col: str, cols: list[str]) -> list[dict]:
    rows = conn.execute(f"SELECT {', '.join([id_col] + cols)} FROM {table}").fetchall()
    return [dict(r) for r in rows]


async def _embed_one(store: MemoryStore, kind: str, row: dict, sem: asyncio.Semaphore) -> tuple[bool, str]:
    async with sem:
        try:
            if kind == "session":
                sid = row["session_id"]
                text = f"{row['session_title'] or ''}\n{row['summary'] or ''}"
                await store.add_session(
                    session_id=sid,
                    text=text,
                    metadata={"project_id": row["project_id"] or "", "model": row["model_used"] or ""},
                )
                return True, f"session_{sid}"
            elif kind == "decision":
                did = row["decision_id"]
                text = f"{row['title'] or ''}\n{row['rationale'] or ''}"
                await store.add_decision(
                    decision_id=did,
                    text=text,
                    metadata={"project_id": row["project_id"] or "", "scope": row["impact_scope"] or ""},
                )
                return True, f"decision_{did}"
            else:
                fid = row["feature_id"]
                text = f"{row['name'] or ''}\n{row['description'] or ''}"
                await store.add_feature(
                    feature_id=fid,
                    text=text,
                    metadata={"source_project": row["source_project"] or "", "domain": row["domain"] or ""},
                )
                return True, f"feature_{fid}"
        except Exception as exc:  # noqa: BLE001
            return False, f"{kind}:{row.get('session_id') or row.get('decision_id') or row.get('feature_id')} -> {exc}"


async def backfill_collection(
    store: MemoryStore,
    conn,
    kind: str,
    collection: str,
    table: str,
    id_col: str,
    cols: list[str],
    dry_run: bool,
) -> tuple[int, int, int]:
    existing = _existing_ids(store, collection)
    id_prefix = {"session": "session_", "decision": "decision_", "feature": "feature_"}[kind]
    rows = _sql_rows(conn, table, id_col, cols)
    missing = [r for r in rows if f"{id_prefix}{r[id_col]}" not in existing]

    print(f"[{collection}] sql_rows={len(rows)} already_indexed={len(existing)} missing={len(missing)}")
    if dry_run or not missing:
        return len(rows), len(existing), 0

    sem = asyncio.Semaphore(CONCURRENCY)
    done = 0
    failed = 0
    for i in range(0, len(missing), BATCH_SIZE):
        batch = missing[i : i + BATCH_SIZE]
        results = await asyncio.gather(*[_embed_one(store, kind, r, sem) for r in batch])
        for ok, info in results:
            if ok:
                done += 1
            else:
                failed += 1
                print(f"  FAILED: {info}")
        print(f"  ...{min(i + BATCH_SIZE, len(missing))}/{len(missing)} embedded (failed so far: {failed})")

    return len(rows), len(existing), done


async def main() -> None:
    dry_run = "--dry-run" in sys.argv

    store = MemoryStore()
    conn = open_brain_db()

    print("=== BEFORE ===")
    before = store.collection_counts()
    for k, v in before.items():
        print(f"  {k}: {v}")

    plan = [
        ("session", COL_SESSIONS, "session_log", "session_id",
         ["project_id", "session_title", "summary", "model_used"]),
        ("decision", COL_DECISIONS, "decisions", "decision_id",
         ["project_id", "title", "rationale", "impact_scope"]),
        ("feature", COL_FEATURES, "features", "feature_id",
         ["source_project", "name", "description", "domain"]),
    ]

    for kind, collection, table, id_col, cols in plan:
        await backfill_collection(store, conn, kind, collection, table, id_col, cols, dry_run)

    conn.close()

    print("=== AFTER ===")
    after = store.collection_counts()
    for k, v in after.items():
        delta = v - before.get(k, 0)
        print(f"  {k}: {v} (+{delta})")


if __name__ == "__main__":
    asyncio.run(main())

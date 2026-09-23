# -*- coding: utf-8 -*-
"""
Rebuild one Brain Chroma collection from its own stored documents.

Written 2026-09-23 for the QI_BrainAPI outage (2026-09-20 18:16 -> 2026-09-23).
The persisted qi_sessions HNSW snapshot deadlocked chromadb (1.5.5, and 1.5.9 too)
whenever a fresh process applied unflushed log entries to it: 0% CPU, GIL held, so
every thread in the process froze. Brain's event loop, /health included, stopped
answering while NSSM still reported SERVICE_RUNNING, and QI_HiveIngest froze the
same way on its next add_session.

Any Chroma read of a poisoned collection can trigger the deadlock, so this tool
never asks Chroma to open the old index. It reads documents and metadata straight
from the SQLite metadata segment, re-embeds them with the same model and prompt
Brain uses (NomicEmbedProvider: raw text, nomic-embed-text; re-embedding
reproduces stored vectors at cosine 1.0), then drops and recreates the collection.

Two phases, so the service outage covers only the swap:

  prepare  (services may keep running)   export + embed -> <workfile>.json
  swap     (Brain + HiveIngest STOPPED)  verify the segment is unchanged since
                                         prepare, drop, recreate, add, verify

Usage:
  python rebuild_chroma_collection.py prepare qi_sessions C:\\path\\work.json
  python rebuild_chroma_collection.py swap    qi_sessions C:\\path\\work.json

Back up C:\\QIH\\engine\\brain\\qi_memory before `swap`. Rollback = stop Brain,
restore that folder, start Brain.
"""
from __future__ import annotations

import faulthandler
import http.client
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
faulthandler.dump_traceback_later(1800, exit=True)   # a deadlock must never be silent

CHROMA_DIR = Path(os.environ.get("QI_BRAIN_CHROMA", Path(__file__).resolve().parents[1] / "qi_memory"))
OLLAMA_HOST, OLLAMA_PORT = "127.0.0.1", 11434          # 127.0.0.1, never localhost (IPv6 stall)
MODEL = "nomic-embed-text"
DIM = 768
BATCH = 100


def segment_fingerprint(name: str) -> dict:
    """Identify the collection's metadata segment and how many rows it holds."""
    db = sqlite3.connect(f"file:{(CHROMA_DIR / 'chroma.sqlite3').as_posix()}?mode=ro", uri=True)
    try:
        (seg,) = db.execute(
            "SELECT s.id FROM segments s JOIN collections c ON s.collection = c.id "
            "WHERE c.name = ? AND s.scope = 'METADATA'", (name,)).fetchone()
        rows, max_seq = db.execute(
            "SELECT COUNT(*), MAX(seq_id) FROM embeddings WHERE segment_id = ?", (seg,)).fetchone()
    finally:
        db.close()
    return {"segment": seg, "rows": rows, "max_seq": max_seq}


def export_records(seg: str) -> list[dict]:
    db = sqlite3.connect(f"file:{(CHROMA_DIR / 'chroma.sqlite3').as_posix()}?mode=ro", uri=True)
    try:
        recs: dict[int, dict] = {}
        for rid, eid in db.execute(
                "SELECT id, embedding_id FROM embeddings WHERE segment_id = ? ORDER BY id", (seg,)):
            recs[rid] = {"id": eid, "document": None, "metadata": {}}
        for rid, key, s, i, f, b in db.execute(
                "SELECT m.id, m.key, m.string_value, m.int_value, m.float_value, m.bool_value "
                "FROM embedding_metadata m JOIN embeddings e ON e.id = m.id WHERE e.segment_id = ?", (seg,)):
            val = s if s is not None else i if i is not None else f if f is not None else (
                bool(b) if b is not None else None)
            if key == "chroma:document":
                recs[rid]["document"] = val
            else:
                recs[rid]["metadata"][key] = val
    finally:
        db.close()
    out = list(recs.values())
    missing = [r["id"] for r in out if not r["document"]]
    if missing:
        raise SystemExit(f"ABORT: {len(missing)} records have no document, e.g. {missing[:5]}")
    return out


_conn: http.client.HTTPConnection | None = None


def embed(text: str) -> list[float]:
    # One keep-alive connection for the whole run. A fresh connection per record
    # leaves thousands of sockets in TIME_WAIT and Windows runs out of ephemeral
    # ports (WinError 10048) partway through a 5,000-record rebuild.
    global _conn
    body = json.dumps({"model": MODEL, "prompt": text})
    for attempt in range(3):
        try:
            if _conn is None:
                _conn = http.client.HTTPConnection(OLLAMA_HOST, OLLAMA_PORT, timeout=120)
            _conn.request("POST", "/api/embeddings", body, {"Content-Type": "application/json"})
            resp = _conn.getresponse()
            payload = resp.read()
            if resp.status != 200:
                raise RuntimeError(f"HTTP {resp.status}: {payload[:200]!r}")
            vec = json.loads(payload)["embedding"]
            break
        except Exception:
            if _conn is not None:
                _conn.close()
            _conn = None
            if attempt == 2:
                raise
            time.sleep(2)
    if len(vec) != DIM:
        raise SystemExit(f"ABORT: {MODEL} returned {len(vec)} dims, expected {DIM}")
    return vec


def prepare(name: str, work: Path) -> None:
    fp = segment_fingerprint(name)
    recs = export_records(fp["segment"])
    print(f"exported {len(recs)} records from {name} (segment {fp['segment']})", flush=True)
    t = time.time()
    for n, r in enumerate(recs, 1):
        r["embedding"] = embed(r["document"])
        if n % 500 == 0:
            print(f"  embedded {n}/{len(recs)} ({time.time() - t:.0f}s)", flush=True)
    work.write_text(json.dumps({"collection": name, "fingerprint": fp, "records": recs}), encoding="utf-8")
    print(f"embedded {len(recs)} in {time.time() - t:.0f}s -> {work}", flush=True)


def swap(name: str, work: Path) -> None:
    data = json.loads(work.read_text(encoding="utf-8"))
    if data["collection"] != name:
        raise SystemExit(f"ABORT: {work} was prepared for {data['collection']}, not {name}")
    now_fp = segment_fingerprint(name)
    if now_fp != data["fingerprint"]:
        raise SystemExit(f"ABORT: {name} changed since prepare: {data['fingerprint']} -> {now_fp}. "
                         f"Re-run prepare with the writers stopped.")
    recs = data["records"]

    import chromadb
    from chromadb.config import Settings
    client = chromadb.PersistentClient(path=str(CHROMA_DIR), settings=Settings(anonymized_telemetry=False))
    client.delete_collection(name)
    print(f"dropped {name}", flush=True)
    col = client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})  # as MemoryStore._get_col
    for i in range(0, len(recs), BATCH):
        chunk = recs[i:i + BATCH]
        col.add(ids=[r["id"] for r in chunk],
                embeddings=[r["embedding"] for r in chunk],
                documents=[r["document"] for r in chunk],
                metadatas=[r["metadata"] or None for r in chunk])
    count = col.count()
    # Probe with a record whose text is unique: many session docs are identical
    # 'subagent_end' stubs, and identical vectors tie, so a duplicate would
    # report a false mismatch.
    texts: dict[str, int] = {}
    for r in recs:
        texts[r["document"]] = texts.get(r["document"], 0) + 1
    probe = next(r for r in reversed(recs) if texts[r["document"]] == 1)
    hit = col.query(query_embeddings=[probe["embedding"]], n_results=1)["ids"][0][0]
    ok = count == len(recs) and hit == probe["id"]
    print(f"rebuilt {name}: count={count}/{len(recs)}  self-query {probe['id']} -> {hit}  "
          f"{'OK' if ok else 'FAILED'}", flush=True)
    if not ok:
        raise SystemExit(1)


def main() -> None:
    if len(sys.argv) != 4 or sys.argv[1] not in ("prepare", "swap"):
        raise SystemExit(__doc__)
    phase, name, work = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    (prepare if phase == "prepare" else swap)(name, work)


if __name__ == "__main__":
    main()

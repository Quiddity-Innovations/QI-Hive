# -*- coding: utf-8 -*-
"""
QI Brain — ChromaDB semantic memory store.

Manages 4 collections:
  - qi_decisions   : vectorized decision records
  - qi_features    : vectorized feature records
  - qi_sessions    : vectorized session summaries
  - qi_docs        : vectorized ecosystem documents (Standards, Map, Principles, etc.)

All embeddings produced by nomic-embed-text via NomicEmbedProvider.

Usage:
    from core.memory_store import MemoryStore
    store = MemoryStore()
    await store.add_decision(decision_id=1, text="Use SQLite WAL mode...", metadata={...})
    results = await store.search("concurrent database writes", collection="qi_decisions", n=5)
"""
from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Optional

# ChromaDB import — graceful failure if not installed
try:
    import chromadb
    from chromadb.config import Settings
    _CHROMA_AVAILABLE = True
except ImportError:
    _CHROMA_AVAILABLE = False

from .providers.factory import ProviderFactory

# ── Paths ─────────────────────────────────────────────────────────────────────
_BRAIN_DIR  = Path(__file__).parent.parent
CHROMA_PATH = _BRAIN_DIR / "qi_memory"

# ── Collection names ──────────────────────────────────────────────────────────
COL_DECISIONS = "qi_decisions"
COL_FEATURES  = "qi_features"
COL_SESSIONS  = "qi_sessions"
COL_DOCS      = "qi_docs"
ALL_COLLECTIONS = [COL_DECISIONS, COL_FEATURES, COL_SESSIONS, COL_DOCS]


class MemoryStore:
    """
    Semantic memory via ChromaDB with nomic-embed-text embeddings.

    Instantiation is lightweight — ChromaDB client connects on first use.
    Call init_collections() once at bootstrap to ensure collections exist.
    """

    def __init__(self, chroma_path: Path = CHROMA_PATH):
        if not _CHROMA_AVAILABLE:
            raise RuntimeError(
                "chromadb not installed. Run: pip install chromadb"
            )
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(chroma_path),
            settings=Settings(anonymized_telemetry=False),
        )
        self._embed_provider = None  # lazy load

    def _get_embedder(self):
        if self._embed_provider is None:
            self._embed_provider = ProviderFactory.get_by_role("embed")
        return self._embed_provider

    def _get_col(self, name: str):
        return self._client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    def init_collections(self) -> None:
        """Create all 4 collections if they don't exist. Safe to call repeatedly."""
        for col_name in ALL_COLLECTIONS:
            self._get_col(col_name)

    # ── Embed helper ───────────────────────────────────────────────────────────
    async def _embed(self, text: str) -> list[float]:
        embedder = self._get_embedder()
        return await embedder.embed(text)

    # ── Add documents ──────────────────────────────────────────────────────────

    async def add_decision(
        self,
        decision_id: int,
        text: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Vectorize and store a decision."""
        vec = await self._embed(text)
        col = self._get_col(COL_DECISIONS)
        col.upsert(
            ids=[f"decision_{decision_id}"],
            embeddings=[vec],
            documents=[text],
            metadatas=[metadata or {}],
        )

    async def add_feature(
        self,
        feature_id: int,
        text: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Vectorize and store a feature."""
        vec = await self._embed(text)
        col = self._get_col(COL_FEATURES)
        col.upsert(
            ids=[f"feature_{feature_id}"],
            embeddings=[vec],
            documents=[text],
            metadatas=[metadata or {}],
        )

    async def add_session(
        self,
        session_id: int,
        text: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Vectorize and store a session summary."""
        vec = await self._embed(text)
        col = self._get_col(COL_SESSIONS)
        col.upsert(
            ids=[f"session_{session_id}"],
            embeddings=[vec],
            documents=[text],
            metadatas=[metadata or {}],
        )

    async def add_doc(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Vectorize and store an ecosystem document chunk."""
        vec = await self._embed(text)
        col = self._get_col(COL_DOCS)
        col.upsert(
            ids=[doc_id],
            embeddings=[vec],
            documents=[text],
            metadatas=[metadata or {}],
        )

    # ── Search ─────────────────────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        collection: str = COL_DECISIONS,
        n: int = 5,
        where: Optional[dict] = None,
    ) -> list[dict]:
        """
        Semantic search across a collection.

        Args:
            query:      Natural language query.
            collection: One of COL_DECISIONS, COL_FEATURES, COL_SESSIONS, COL_DOCS.
            n:          Number of results to return.
            where:      Optional ChromaDB metadata filter dict.

        Returns:
            List of {id, document, metadata, distance} dicts, closest first.
        """
        vec = await self._embed(query)
        col = self._get_col(collection)
        kwargs: dict = {"query_embeddings": [vec], "n_results": n, "include": ["documents", "metadatas", "distances"]}
        if where:
            kwargs["where"] = where

        results = col.query(**kwargs)

        output = []
        for i, doc_id in enumerate(results["ids"][0]):
            output.append({
                "id":       doc_id,
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
            })
        return output

    # ── Stats ──────────────────────────────────────────────────────────────────

    def collection_counts(self) -> dict[str, int]:
        """Return document count per collection."""
        return {
            name: self._get_col(name).count()
            for name in ALL_COLLECTIONS
        }

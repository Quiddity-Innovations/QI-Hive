# -*- coding: utf-8 -*-
"""
CogniBase MCP Server  (PROPOSAL / SCAFFOLD — not wired into production)
=======================================================================

Why this exists
---------------
Boston University's Nexus / Regent agents reach data *exclusively* through MCP
(Model Context Protocol) tools. Exposing CogniBase's retrieval + RAG as MCP tools
makes CogniBase natively callable by BU's agents with zero bespoke integration —
the single highest-leverage compatibility move (see the BU fit assessment).

This scaffold wraps the EXISTING CogniBase engine:
    - Application/rag/retriever.py     -> RagRetriever.search(query, top_k, filters)
    - Application/rag/query_engine.py  -> QueryEngine.answer(question, vendor, top_k)
    - Application/vendors/router.py    -> VendorRouter (pluggable Claude/OpenAI/Gemini/Ollama)

It does NOT change any production code, register a service, or open a port by default.
Run it standalone over stdio for local testing, or behind APISIX for BU.

Status: SKELETON. The TODO blocks mark where construction details from the live
app (collection name, settings load, gate enforcement) must be wired in.

Install (when ready to test):
    pip install "mcp[cli]"          # official Python MCP SDK (FastMCP)
Run (stdio, for an MCP client / Claude Desktop / Nexus dev):
    python proposals/mcp_server.py

Author: QI / Claude  —  2026-06-27
"""
from __future__ import annotations
import sys, os, json
from typing import Any

# --- make the CogniBase Application package importable -----------------------
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                      # C:\CogniBase
sys.path.insert(0, ROOT)

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover
    print("Install the MCP SDK first:  pip install \"mcp[cli]\"", file=sys.stderr)
    raise

# --- CogniBase engine imports (existing code) --------------------------------
# NOTE: these imports assume the package layout under Application/.
from Application.vendors.router import VendorRouter
from Application.rag.retriever import RagRetriever
from Application.rag.query_engine import QueryEngine


# ---------------------------------------------------------------------------
# Engine bootstrap
# ---------------------------------------------------------------------------
def _build_engine() -> tuple[RagRetriever, QueryEngine]:
    """
    Construct the CogniBase RAG stack once and reuse across tool calls.

    TODO(wire): mirror however Application/server/app.py builds these today:
      - load Settings/settings.json (active vendors, keys, base_urls)
      - choose the collection_name per corpus (cognibase_main / _config / doc_corpus)
      - apply the BU 'mode' (Entra ID identity, Gate policy) when BU_MODE=1
    """
    router = VendorRouter()                       # TODO(wire): pass loaded settings
    retriever = RagRetriever(router, collection_name="cognibase_main")
    engine = QueryEngine(retriever, router)
    return retriever, engine


_RETRIEVER: RagRetriever | None = None
_ENGINE: QueryEngine | None = None


def _engine() -> QueryEngine:
    global _RETRIEVER, _ENGINE
    if _ENGINE is None:
        _RETRIEVER, _ENGINE = _build_engine()
    return _ENGINE


def _retriever() -> RagRetriever:
    global _RETRIEVER, _ENGINE
    if _RETRIEVER is None:
        _RETRIEVER, _ENGINE = _build_engine()
    return _RETRIEVER


# ---------------------------------------------------------------------------
# MCP surface
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "cognibase",
    instructions=(
        "CogniBase exposes Boston University OnBase knowledge as structured tools. "
        "Use cognibase.search for raw passages with citations, cognibase.ask for a "
        "synthesized, cited answer, and cognibase.schema_explain to understand OnBase "
        "table/DocType structure. All results are gate-filtered and audited; regulated "
        "values are masked by the Privacy Transformer before they leave the box."
    ),
)


@mcp.tool()
def search(query: str, top_k: int = 8, filters: dict | None = None) -> list[dict]:
    """Semantic search over the CogniBase corpus. Returns passages with ids, scores,
    and metadata for grounding. Use this when you want raw evidence to reason over."""
    hits = _retriever().search(query, top_k=top_k, filters=filters)
    # Already gate-filtered/masked upstream by the retriever's source layer.
    return hits


@mcp.tool()
def ask(question: str, vendor: str | None = None, top_k: int = 8) -> dict:
    """Ask a natural-language question about BU OnBase. CogniBase retrieves grounding
    context and synthesizes a cited answer using the active (or requested) LLM vendor.
    Returns {answer, citations[], vendor_used, tokens_in, tokens_out}."""
    return _engine().answer(question, vendor=vendor, top_k=top_k)


@mcp.tool()
def schema_explain(entity: str, top_k: int = 8) -> dict:
    """Explain an OnBase schema entity (table, DocType, KeywordType) and its
    relationships in plain English, grounded in the OnBase Configuration corpus.

    TODO(wire): route this at the 'cognibase_config' collection so explanations draw
    from .expk packages + schema.json + MRG annotations rather than operational data.
    """
    # Interim implementation reuses the RAG answer path with a schema-scoped prompt.
    q = (f"Explain the OnBase entity '{entity}': its purpose, key columns/keywords, "
         f"and how it relates to other DocTypes. Cite configuration sources.")
    return _engine().answer(q, top_k=top_k)


# ---------------------------------------------------------------------------
# Planned tools (stubs — implement against existing modules)
# ---------------------------------------------------------------------------
# @mcp.tool()
# def federated_query(logical_query: dict, group: str) -> dict:
#     """Run a cross-DocType query via the Query Federator (Normalizer joins).
#     TODO(wire): Application/... Query Federator entrypoint + Gate(group) enforcement."""
#
# @mcp.tool()
# def list_doctypes() -> list[dict]:
#     """List OnBase DocTypes known to this profile (from schema.json / .expk)."""


if __name__ == "__main__":
    # Default transport = stdio (works with Claude Desktop, Nexus dev harness, mcp inspector).
    # For BU: run with a streamable-http transport behind APISIX + Entra ID instead.
    mcp.run()

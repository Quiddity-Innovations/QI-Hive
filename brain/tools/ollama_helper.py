# -*- coding: utf-8 -*-
"""
QI Brain — Ollama grunt task helper.

Used during the build and at runtime to offload cheap tasks to local Ollama:
- Docstring generation
- JSON extraction / structured output
- Log summarization
- Test data generation

Claude calls these helpers instead of burning Claude tokens on trivial work.

Usage (CLI):
    python tools/ollama_helper.py summarize "Long text to summarize..."
    python tools/ollama_helper.py extract_json "Extract the port number from: port=9010"
    python tools/ollama_helper.py list_models
"""
from __future__ import annotations
import asyncio
import json
import sys
from typing import Optional

import httpx

OLLAMA_URL  = "http://localhost:11434"
FAST_MODEL  = "qwen3:4b"    # boilerplate, trivial tasks
SMART_MODEL = "qwen3:8b"    # structured output, reasoning
EMBED_MODEL = "nomic-embed-text"


# ── List models ───────────────────────────────────────────────────────────────

async def list_models() -> list[str]:
    """Return names of all locally available Ollama models."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{OLLAMA_URL}/api/tags")
        resp.raise_for_status()
        data = resp.json()
    return [m["name"] for m in data.get("models", [])]


# ── Core generate ─────────────────────────────────────────────────────────────

async def _generate(prompt: str, model: str, system: Optional[str] = None) -> str:
    payload: dict = {"model": model, "prompt": prompt, "stream": False}
    if system:
        payload["system"] = system
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()


# ── Task helpers ──────────────────────────────────────────────────────────────

async def summarize(text: str, max_words: int = 100) -> str:
    """Produce a short summary of text. Uses FAST_MODEL."""
    prompt = (
        f"Summarize the following text in at most {max_words} words. "
        f"Be concise and factual.\n\n{text}"
    )
    return await _generate(prompt, FAST_MODEL)


async def extract_json(text: str, schema_hint: str = "") -> dict:
    """
    Extract structured JSON from text. Uses SMART_MODEL.

    Args:
        text:        Raw text to extract from.
        schema_hint: Optional hint like "extract fields: name, port, status"

    Returns:
        Parsed dict, or {"error": "parse_failed", "raw": text} on failure.
    """
    system = (
        "You extract structured data from text. "
        "Return ONLY valid JSON with no explanation, no markdown, no code block."
    )
    hint = f"\nExtract: {schema_hint}" if schema_hint else ""
    prompt = f"Extract JSON from this text{hint}:\n\n{text}"
    raw = await _generate(prompt, SMART_MODEL, system=system)

    # Try to parse — handle markdown code fences
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"error": "parse_failed", "raw": raw}


async def generate_docstring(code: str) -> str:
    """Generate a Python docstring for a function/class. Uses FAST_MODEL."""
    system = (
        "You write Python docstrings. Given a function or class, return ONLY the docstring "
        "(the triple-quoted string, no def line, no extra text)."
    )
    return await _generate(f"Write a docstring for:\n\n{code}", FAST_MODEL, system=system)


async def generate_test_data(schema: str, n: int = 5) -> list[dict]:
    """
    Generate n fake records matching a schema description. Uses SMART_MODEL.

    Args:
        schema: Description like "project with fields: id, name, port"
        n:      Number of records to generate.

    Returns:
        List of dicts, or empty list on parse failure.
    """
    system = (
        "Generate test data as a JSON array. "
        "Return ONLY the JSON array, no explanation."
    )
    prompt = f"Generate {n} realistic fake records for: {schema}"
    raw = await _generate(prompt, SMART_MODEL, system=system)
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        result = json.loads(cleaned)
        return result if isinstance(result, list) else []
    except json.JSONDecodeError:
        return []


async def embed(text: str) -> list[float]:
    """Embed text using nomic-embed-text. Returns 768-dim vector."""
    payload = {"model": EMBED_MODEL, "prompt": text}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{OLLAMA_URL}/api/embeddings", json=payload)
        resp.raise_for_status()
        return resp.json()["embedding"]


# ── CLI entrypoint ────────────────────────────────────────────────────────────

async def _main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print("Usage: python ollama_helper.py <command> [args...]")
        print("Commands: list_models, summarize, extract_json, generate_docstring, generate_test_data, embed")
        return

    cmd = sys.argv[1].lower()

    if cmd == "list_models":
        models = await list_models()
        print("\n".join(models))

    elif cmd == "summarize":
        text = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else sys.stdin.read()
        result = await summarize(text)
        print(result)

    elif cmd == "extract_json":
        text = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else sys.stdin.read()
        result = await extract_json(text)
        print(json.dumps(result, indent=2))

    elif cmd == "embed":
        text = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else sys.stdin.read()
        vec = await embed(text)
        print(f"Vector dim={len(vec)}, first 5 values: {vec[:5]}")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    asyncio.run(_main())

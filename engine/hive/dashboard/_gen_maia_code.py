# -*- coding: utf-8 -*-
"""Generate C:\\APPS\\QI\\INTRO\\status_code.json — Maia's "Code Explained" tab.

Every snippet is extracted verbatim from the live source at generation time
rather than transcribed, so the tab cannot drift into describing code that no
longer exists. Explanations are written against what the code actually does.

Schema matches the other projects (see C:\\APPS\\NEXUS\\INTRO\\status_code.json):
    {"intro": str, "sections": [{"category": str, "snippets": [
        {"title","feature","file","language","code","explanation"}]}]}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

QI = Path(r"C:\APPS\QI")
OUT = QI / "INTRO" / "status_code.json"
MAX_LINES = 22


def grab(relpath: str, start: int, end: int) -> str:
    """Extract lines [start, end] (1-indexed, inclusive) verbatim."""
    lines = (QI / relpath).read_text(encoding="utf-8", errors="replace").splitlines()
    chunk = lines[start - 1:end]
    while chunk and not chunk[-1].strip():
        chunk.pop()
    if len(chunk) > MAX_LINES:
        chunk = chunk[:MAX_LINES] + ["    # ..."]
    return "\n".join(chunk)


SPEC = [
    ("Service Contract (FastAPI :8001)", [
        ("maia_server.py", 6221, 6240,
         "QI module contract endpoints",
         "Health, version and registry self-description",
         "Every QI service must answer /health, /version and /info (Law 2). "
         "/health is a flat liveness probe the Hive dashboard polls. /version "
         "reads system.version live from maia.db, so a version bump needs no "
         "redeploy. /info resolves this project's own entry out of "
         "qi_registry.json and returns it, which is how sibling projects "
         "discover Maia's ports without hardcoding them — and it degrades to "
         "an error envelope rather than raising if the registry is unreadable."),
    ]),
    ("LLM Routing", [
        ("maia_server.py", 3691, 3714,
         "llm_chat() — the single LLM entry point",
         "Multi-LLM fallback chain with language-aware routing",
         "Every model call in Maia funnels through this one function, which "
         "walks LLM_CHAIN in order and returns on the first success. Cloud "
         "models are tried first (no local RAM cost) with Ollama as the safety "
         "net, so the user always receives a reply instead of an error. Two "
         "runtime switches matter: LLM_PROVIDER='ollama' strips every cloud "
         "provider so the bot runs with no internet and no API keys, and a "
         "Japanese detection prepends JP_LLM_CHAIN so JP-tuned models are "
         "tried ahead of the general chain."),
        ("maia_server.py", 3717, 3722,
         "Anthropic mode read live from the database",
         "Config changes without a restart",
         "The Anthropic routing mode (off | fallback | priority) is re-read "
         "from maia.db on every single call rather than cached at import. That "
         "is the concrete expression of Maia's no-hardcoded-values rule: "
         "flipping Anthropic off is a database update, not a deployment."),
    ]),
    ("Retrieval (RAG)", [
        ("maia_rag.py", 34, 44,
         "ChromaDB singleton client",
         "Per-bot document retrieval",
         "A single PersistentClient is created lazily on first use and reused "
         "for the process lifetime; chromadb is imported inside the function so "
         "a deployment that never touches RAG does not pay its import cost."),
        ("maia_rag.py", 42, 45,
         "Per-bot collection namespacing",
         "One codebase, many named bots",
         "Each bot gets its own ChromaDB collection keyed by bot_key. This is "
         "what lets the template-engine vision work: Maia, Naya and any future "
         "named bot share one codebase and one process while keeping their "
         "knowledge bases completely separate. Hyphens are normalised to "
         "underscores because ChromaDB restricts collection names."),
    ]),
    ("Language Handling", [
        ("maia_lang.py", 135, 156,
         "Script-first language detection",
         "Automatic multilingual replies",
         "Detection runs on Unicode character names before any library is "
         "consulted. Hiragana or katakana means Japanese, bare CJK means "
         "Chinese, and Cyrillic and Greek are decided the same way — all "
         "deterministic, dependency-free and immune to the short-string "
         "misfires langdetect is prone to. langdetect is only consulted for "
         "Latin-script text of at least four characters. The result feeds "
         "llm_chat(), which is why a Japanese message routes to the JP chain."),
    ]),
    ("Persistence", [
        ("maia_db.py", 32, 37,
         "SQLite connection factory",
         "All configuration in maia.db, nothing hardcoded",
         "Row factory gives dict-like access, check_same_thread=False lets "
         "FastAPI's threadpool share the handle, and WAL journal mode allows "
         "the Gradio UI to read while the bot writes without lock contention — "
         "the two processes hit the same file concurrently by design."),
    ]),
]

INTRO = (
    "Maia is a multi-channel AI assistant (LINE, Telegram, Facebook Messenger, "
    "Instagram) built on FastAPI, SQLite and a fallback chain of LLM providers. "
    "Its two organising principles show up throughout the code: every value "
    "that could change lives in maia.db rather than in source, and every "
    "external dependency degrades instead of failing. The snippets below are "
    "extracted verbatim from the live source and map each feature to the code "
    "that implements it."
)


def main() -> None:
    sections = []
    for category, items in SPEC:
        snippets = []
        for relpath, a, b, title, feature, explanation in items:
            snippets.append({
                "title": title,
                "feature": feature,
                "file": f"{relpath} :: lines {a}-{b}",
                "language": "python",
                "code": grab(relpath, a, b),
                "explanation": explanation,
            })
        sections.append({"category": category, "snippets": snippets})

    OUT.write_text(json.dumps({"intro": INTRO, "sections": sections},
                              indent=2, ensure_ascii=False), encoding="utf-8")
    n = sum(len(s["snippets"]) for s in sections)
    print(f"wrote {OUT}  ({len(sections)} sections, {n} snippets)")


if __name__ == "__main__":
    main()

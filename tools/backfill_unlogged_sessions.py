# -*- coding: utf-8 -*-
"""backfill_unlogged_sessions.py — for each session marked needs_backfill in the
candidates manifest, classify by content and emit a session-stub JSON to the
HiveIngest inbox. Stubs are picked up automatically and written to qi_brain.db.

USAGE:
  python C:\\QIH\\tools\\backfill_unlogged_sessions.py \\
      --candidates C:\\QIH\\shared\\reports\\inbox\\backfill_candidates_20260515.json \\
      --dry-run
  # then re-run without --dry-run to actually drop the stubs.
"""
from __future__ import annotations
import argparse, json, os, sys, uuid
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

INBOX = Path(r"C:\QIH\shared\reports\inbox")

# Topic-detection rules. Each rule: (project_id, [substring keywords (lower)]).
# Earlier rules win. Substrings checked against first_prompt + last_prompt + files_touched.
RULES: list[tuple[str, list[str]]] = [
    ("openclaw",   ["c:\\oc\\", "/mnt/c/oc/", "openclaw", "kaze", "tasuke", "yubin",
                    "koe", "asa", "kakei", "sentry-",
                    "line_handoff", "tasuke-bridge", "kaze-llm",
                    "bot-voices", "telegram-bot", "oc_audit",
                    "adult groups", "bots are all"]),
    ("mapsnap",    ["mapsnap", "c:\\mapsnap", "schema_browser",
                    "build_browser.py", "document_indexer", "onbase schema",
                    ".expk", "build_catalog", "catalog_loader"]),
    ("maia",       ["c:\\qi\\", "qi_sibling_control", "maia_server.py",
                    "sibling bot", "quiet.json"]),
    ("naya",       ["c:\\naya", "naya_server", "naya_line.py", "filehq",
                    "naya bot"]),
    ("nexus",      ["c:\\nexus", "nexus_server", "nexus rag"]),
    ("easyflow",   ["c:\\easyflow", "easyflow", "gmail filter"]),
    ("autopdf",    ["c:\\autopdf", "autopdf"]),
    ("cognibase",  ["c:\\cognibase", "cognibase"]),
    ("qi_hive",    ["qi hive", "qi_hive", "qih\\engine", "qih/engine",
                    "dashboard audit", "hive dashboard", "qi brain",
                    "task board", "qi-dashboard", "ecosystem_audit",
                    "scheduled-task", "quiddam-com",
                    "domain availability", "qi.com", "quiddity"]),
]


def classify(c: dict) -> str:
    """Pick the most likely project_id based on transcript clues."""
    blob = " ".join([
        (c.get("first_prompt") or "").lower(),
        (c.get("last_prompt")  or "").lower(),
        " ".join(c.get("files_touched") or []).lower(),
        (c.get("cwd") or "").lower(),
    ])
    for pid, kws in RULES:
        for kw in kws:
            if kw in blob:
                return pid
    # Worktrees fall through to here — leave as claude_manager
    return c.get("project_id") or "unknown"


def summarize(c: dict) -> tuple[str, str, str]:
    """Return (title, summary, started_at_iso) for a stub."""
    first = (c.get("first_prompt") or "").strip().replace("\n", " ")
    title = first[:90] or "Untitled session"
    np    = c.get("user_prompts", 0)
    ar    = c.get("assistant_replies", 0)
    files = c.get("files_touched") or []
    files_str = "; ".join(files[:8])
    last = (c.get("last_prompt") or "").strip().replace("\n", " ")[:200]
    started = c.get("first_ts") or c.get("mtime") or datetime.now().isoformat()
    transcript = c.get("transcript", "")
    summary = (
        f"AUTO-RECONSTRUCTED FROM TRANSCRIPT (session_end hook silence backfill).\n"
        f"TRANSCRIPT: {transcript}\n"   # used by scanner for exact-match dedup
        f"User prompts: {np}, assistant replies: {ar}.\n"
        f"First prompt: {first[:300]}\n"
        f"Last prompt: {last}\n"
        f"Files touched (top 8): {files_str if files_str else '(none recorded)'}"
    )
    return title, summary, started


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    manifest = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
    cands = manifest.get("candidates", [])
    todo  = [c for c in cands if not c.get("likely_logged")]
    print(f"Loaded {len(cands)} candidates; {len(todo)} need backfill.\n")

    INBOX.mkdir(parents=True, exist_ok=True)

    written = 0
    by_project: dict[str, int] = {}
    for c in sorted(todo, key=lambda x: x.get("first_ts","")):
        pid = classify(c)
        by_project[pid] = by_project.get(pid, 0) + 1
        title, summary, started = summarize(c)
        sid = str(uuid.uuid4())
        # IMPORTANT: timestamp must be the SESSION's real start time, not the
        # moment of stub creation. HiveIngest uses `timestamp` as `started_at`
        # in session_log, and the matcher uses `started_at` to detect existing
        # rows. If we set timestamp=now(), every tick re-detects every session
        # as unlogged and duplicates them. (Fix landed 2026-05-15 22:35.)
        stub = {
            "source":         "claude_code_backfill",
            "event":          "session_end",
            "project":        pid,
            "session_id":     sid,
            "session_date":   started,
            "timestamp":      started,
            "stubbed_at":     datetime.now().isoformat(timespec="seconds"),
            "cwd":            c.get("cwd",""),
            "transcript":     c.get("transcript",""),
            "reason":         "auto_backfill_20260515",
            "type":           "session_report",
            "title":          title,
            "summary":        summary,
            "decisions":      [],
            "flags":          ["auto_stub", "backfilled", "low_confidence_reconstruction"],
            "outputs":        [],
            "next_suggested": [],
            "model_used":     "claude-code (unknown — reconstructed)",
            "user_prompts":   c.get("user_prompts", 0),
            "files_touched":  c.get("files_touched") or [],
        }
        # filename pattern matches what HiveIngest expects
        ts_compact = (started or datetime.now().isoformat()).replace(":","").replace("-","")[:15]
        fname = f"{pid}_session_backfill_{ts_compact}_{sid[:8]}.json"
        out = INBOX / fname
        if args.dry_run:
            print(f"  [DRY] would write: {fname}  →  project={pid:15s}  title={title[:60]}")
        else:
            out.write_text(json.dumps(stub, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"  wrote: {fname}  →  project={pid:15s}  title={title[:60]}")
            written += 1

    print()
    print("Distribution by project:")
    for pid, n in sorted(by_project.items(), key=lambda x: -x[1]):
        print(f"  {pid:15s} {n}")
    print()
    if args.dry_run:
        print(f"DRY RUN. Would have written {len(todo)} stubs.")
    else:
        print(f"Wrote {written} stubs to {INBOX}.")
        print("QI_HiveIngest will consume them on its next pass.")


if __name__ == "__main__":
    main()

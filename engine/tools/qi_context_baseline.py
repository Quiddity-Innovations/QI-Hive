# -*- coding: utf-8 -*-
"""
qi_context_baseline.py - measure the fixed context cost of a Claude Code session.

Phase 0 of the 2026-09-24 declutter plan. Re-run after each phase (Phase 5
compares against the first snapshot) - never edit the old snapshot files.

Measures:
  * ground truth: total input tokens on the FIRST assistant turn of recent
    sessions (input + cache_creation + cache_read), read from transcripts
  * the files/hooks that make up that cost (bytes and ~tokens at 4 chars/token)
  * how much documentation each session produces

Usage:  python qi_context_baseline.py [--label NAME] [--days 14]
Output: C:\\QIH\\shared\\documentation\\plans\\context_baseline\\<date>_<label>.json
"""
import argparse, glob, json, os, statistics, subprocess, sys, time
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CLAUDE_HOME = Path(r"C:\Users\renne\.claude")
PY = r"C:\Program Files\Python311\python.exe"
OUT_DIR = Path(r"C:\QIH\shared\documentation\plans\context_baseline")
SUMMARIES = Path(r"C:\QIH\shared\documentation\session_summaries")
SHARED_DOCS = Path(r"C:\QIH\shared\documentation")


def tok(chars: int) -> int:
    return round(chars / 4)


def text_size(path: Path) -> dict:
    try:
        t = path.read_text(encoding="utf-8", errors="replace")
        return {"path": str(path), "bytes": path.stat().st_size, "chars": len(t), "est_tokens": tok(len(t))}
    except FileNotFoundError:
        return {"path": str(path), "missing": True}


SESSION_STATE = Path(r"C:\QIH\qi_session\session_state.json")


def run_hook(script: Path, cwd: str, stdin: str = "", fresh: bool = False) -> dict:
    # Both hooks write/delete the shared session_state.json - put it back after,
    # so measuring never changes what a live session gets briefed on.
    saved = SESSION_STATE.read_bytes() if SESSION_STATE.exists() else None
    try:
        if fresh:  # measure as a new session would see it
            SESSION_STATE.unlink(missing_ok=True)
        return _run_hook(script, cwd, stdin)
    finally:
        if saved is None:
            SESSION_STATE.unlink(missing_ok=True)
        else:
            SESSION_STATE.write_bytes(saved)


def _run_hook(script: Path, cwd: str, stdin: str = "") -> dict:
    try:
        r = subprocess.run([PY, str(script)], cwd=cwd, input=stdin, capture_output=True,
                           text=True, encoding="utf-8", timeout=30)
        ctx = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
        return {"cwd": cwd, "chars": len(ctx), "est_tokens": tok(len(ctx))}
    except Exception as e:
        return {"cwd": cwd, "error": f"{type(e).__name__}: {e}"}


def first_turn_usage(days: int) -> dict:
    """Ground truth from transcripts: context size at the first assistant turn."""
    cutoff = time.time() - days * 86400
    per_session, turns = [], []
    for f in glob.glob(str(CLAUDE_HOME / "projects" / "*" / "*.jsonl")):
        if os.path.getmtime(f) < cutoff:
            continue
        first, n_user = None, 0
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    try:
                        m = json.loads(line)
                    except Exception:
                        continue
                    if m.get("type") == "user" and not m.get("isSidechain"):
                        c = (m.get("message") or {}).get("content")
                        if isinstance(c, str) or (isinstance(c, list) and any(
                                isinstance(b, dict) and b.get("type") == "text" for b in c)):
                            n_user += 1
                    if first is None and m.get("type") == "assistant" and not m.get("isSidechain"):
                        u = (m.get("message") or {}).get("usage")
                        if u:
                            first = (u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
                                     + u.get("cache_read_input_tokens", 0))
        except Exception:
            continue
        if first:
            per_session.append({"project": Path(f).parent.name, "first_turn_tokens": first,
                                "user_prompts": n_user})
            turns.append(n_user)
    vals = [s["first_turn_tokens"] for s in per_session]
    by_proj = {}
    for s in per_session:
        by_proj.setdefault(s["project"], []).append(s["first_turn_tokens"])
    return {
        "days": days,
        "sessions": len(vals),
        "first_turn_tokens_median": int(statistics.median(vals)) if vals else None,
        "first_turn_tokens_p90": int(sorted(vals)[int(len(vals) * 0.9) - 1]) if len(vals) >= 10 else None,
        "user_prompts_per_session_median": statistics.median(turns) if turns else None,
        "by_project_median": {k: int(statistics.median(v)) for k, v in
                              sorted(by_proj.items(), key=lambda kv: -len(kv[1]))[:12]},
    }


def docs_produced(days: int) -> dict:
    cutoff = time.time() - days * 86400
    summ = [p for p in SUMMARIES.glob("*.docx") if p.stat().st_mtime >= cutoff]
    shared = [p for p in SHARED_DOCS.rglob("*") if p.is_file() and p.stat().st_mtime >= cutoff]
    return {"days": days, "session_summary_docx": len(summ), "shared_docs_files_touched": len(shared),
            "session_summary_docx_total": len(list(SUMMARIES.glob("*.docx")))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="baseline")
    ap.add_argument("--days", type=int, default=14)
    a = ap.parse_args()

    stores = {}
    for d in sorted((CLAUDE_HOME / "projects").glob("*/memory")):
        idx = d / "MEMORY.md"
        stores[d.parent.name] = {"files": len(list(d.glob("*.md"))),
                                 "index_bytes": idx.stat().st_size if idx.exists() else 0}

    agents = {p.name: p.stat().st_size for p in (CLAUDE_HOME / "agents").glob("*.md")}

    snap = {
        "taken": datetime.now().isoformat(timespec="seconds"),
        "label": a.label,
        "ground_truth": first_turn_usage(a.days),
        "static": {
            "global_claude_md": text_size(CLAUDE_HOME / "CLAUDE.md"),
            "memory_index_C--CLAUDE": text_size(CLAUDE_HOME / "projects" / "C--CLAUDE" / "memory" / "MEMORY.md"),
            "memory_stores": stores,
            "agent_defs_bytes": agents,
        },
        "hooks": {
            "session_start": [run_hook(CLAUDE_HOME / "session_context.py", c)
                              for c in (r"C:\CLAUDE", r"C:\APPS\QI", r"C:\APPS\MapSnap")],
            "user_prompt_ecosystem_word": run_hook(
                CLAUDE_HOME / "user_prompt_hook.py", r"C:\CLAUDE",
                json.dumps({"prompt": "check the ecosystem dashboard"}), fresh=True),
        },
        "docs": docs_produced(30),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{datetime.now():%Y-%m-%d_%H%M}_{a.label}.json"
    out.write_text(json.dumps(snap, indent=2, ensure_ascii=False), encoding="utf-8")
    g, s = snap["ground_truth"], snap["static"]
    print(f"Saved {out}")
    print(f"First-turn context (median of {g['sessions']} sessions, {a.days}d): {g['first_turn_tokens_median']:,} tokens"
          f"  p90={g['first_turn_tokens_p90']}  prompts/session median={g['user_prompts_per_session_median']}")
    print(f"CLAUDE.md ~{s['global_claude_md']['est_tokens']:,} tok | MEMORY.md(C--CLAUDE) "
          f"~{s['memory_index_C--CLAUDE']['est_tokens']:,} tok")
    for h in snap["hooks"]["session_start"]:
        print(f"SessionStart hook @ {h['cwd']}: ~{h.get('est_tokens', h.get('error'))} tok")
    print(f"UserPromptSubmit on 'ecosystem dashboard': ~{snap['hooks']['user_prompt_ecosystem_word'].get('est_tokens')} tok")
    print(f"Docs (30d): {snap['docs']}")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""scan_unlogged_sessions.py — find Claude Code sessions on disk that have no
matching Brain log entry, summarize each, and emit a JSON manifest so backfill
can be done explicitly.

This is the read/diagnose half of the SessionEnd backstop. Pair with a periodic
task (Scheduler) to run it; pair with qi.log_session calls to act on it.

USAGE:
  python C:\\QIH\\tools\\scan_unlogged_sessions.py --since 2026-05-14
  python C:\\QIH\\tools\\scan_unlogged_sessions.py --since 2026-05-14 --output C:\\QIH\\shared\\reports\\inbox\\backfill_candidates.json
"""
from __future__ import annotations
import argparse, json, os, re, sqlite3, sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CLAUDE_PROJECTS_DIR = Path(r"C:\Users\renne\.claude\projects")
REGISTRY            = Path(r"C:\QIH\ecosystem\qi_registry.json")
BRAIN_DB            = Path(r"C:\QIH\data\qi_brain.db")


def load_registry_paths() -> dict[str, str]:
    """Return {normalized_path: project_id} from the registry."""
    out: dict[str, str] = {}
    try:
        reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
        for p in reg.get("projects", []):
            path = p.get("path") or ""
            if path:
                key = os.path.normcase(os.path.normpath(path))
                out[key] = p.get("id") or "unknown"
    except Exception as e:
        print(f"[warn] could not load registry: {e}", file=sys.stderr)
    return out


def projectdir_to_cwd(projectdir_name: str) -> str:
    """The Claude Code projects directory encodes the cwd as e.g.
    'C--CLAUDE--claude-worktrees-foo' which represents 'C:\\CLAUDE\\.claude\\worktrees\\foo'.
    Decode that back to a path."""
    # First dash is the colon. Subsequent double-dashes are backslashes.
    # 'C--CLAUDE--claude-worktrees-foo' → 'C:\\CLAUDE\\.claude\\worktrees-foo'
    # Special case: the literal pattern '.claude' is rendered as '-claude' because
    # the leading dot was stripped. There's no clean reverse — we approximate.
    if not projectdir_name:
        return ""
    parts = projectdir_name.split("--")
    if not parts:
        return ""
    # parts[0] is drive letter, e.g. 'C'
    drive = parts[0] + ":"
    rest = "\\".join(parts[1:])
    # Restore .claude folder that lost its leading dot
    rest = rest.replace("\\claude\\worktrees\\", "\\.claude\\worktrees\\")
    rest = rest.replace("claude-worktrees-", ".claude\\worktrees\\")
    return drive + "\\" + rest


def infer_project(cwd: str, registry: dict[str, str]) -> str:
    if not cwd:
        return "unknown"
    cwd_n = os.path.normcase(os.path.normpath(cwd))
    best, best_len = None, 0
    for p, pid in registry.items():
        if cwd_n == p or cwd_n.startswith(p + os.sep):
            if len(p) > best_len:
                best, best_len = pid, len(p)
    if best:
        return best
    if cwd_n.startswith(os.path.normcase(r"C:\CLAUDE")):
        return "claude_manager"
    return "unknown"


def transcript_summary(jsonl_path: Path) -> dict:
    """Read a Claude Code session transcript and produce a coarse summary."""
    user_prompts: list[str] = []
    assistant_replies = 0
    files_touched: set[str] = set()
    first_ts = last_ts = None
    cwd = ""
    try:
        with jsonl_path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except Exception:
                    continue
                ts = msg.get("timestamp") or msg.get("ts") or msg.get("created_at")
                if ts:
                    first_ts = first_ts or ts
                    last_ts  = ts
                if not cwd:
                    cwd = msg.get("cwd") or ""
                t = msg.get("type")
                if t == "user":
                    content = (msg.get("message") or {}).get("content")
                    if isinstance(content, str):
                        user_prompts.append(content[:300])
                    elif isinstance(content, list):
                        for blk in content:
                            if isinstance(blk, dict) and blk.get("type") == "text":
                                user_prompts.append((blk.get("text") or "")[:300])
                elif t == "assistant":
                    assistant_replies += 1
                    content = (msg.get("message") or {}).get("content")
                    if isinstance(content, list):
                        for blk in content:
                            if isinstance(blk, dict) and blk.get("type") == "tool_use":
                                inp = blk.get("input") or {}
                                fp = inp.get("file_path") or inp.get("path")
                                if isinstance(fp, str):
                                    files_touched.add(fp)
    except Exception as e:
        return {"error": str(e), "path": str(jsonl_path)}
    return {
        "transcript":      str(jsonl_path),
        "cwd":             cwd,
        "first_ts":        first_ts,
        "last_ts":         last_ts,
        "user_prompts":    len(user_prompts),
        "assistant_replies": assistant_replies,
        "files_touched":   sorted(files_touched)[:30],
        "first_prompt":    (user_prompts[0][:240] if user_prompts else ""),
        "last_prompt":     (user_prompts[-1][:240] if user_prompts else ""),
    }


def load_brain_state_since(cutoff_iso: str) -> tuple[set[tuple[str,str,str]], set[str]]:
    """Return (rows, transcript_paths) where:
      rows = {(project_id, started_at, title), ...} for time-proximity match
      transcript_paths = {full transcript path, ...} mentioned in any session
                        summary — used for exact-match dedup of backfill rows.
    """
    rows: set[tuple[str,str,str]] = set()
    transcripts: set[str] = set()
    if not BRAIN_DB.exists():
        return rows, transcripts
    try:
        c = sqlite3.connect(f"file:{BRAIN_DB}?mode=ro", uri=True)
        try:
            for row in c.execute(
                "SELECT project_id, started_at, session_title, summary "
                "FROM session_log WHERE started_at >= ?",
                (cutoff_iso,)
            ):
                pid = (row[0] or "").lower()
                started = row[1] or ""
                title = (row[2] or "")[:80]
                summary = row[3] or ""
                rows.add((pid, started, title))
                # extract transcript paths mentioned in summary (backfill rows
                # include a "TRANSCRIPT: <path>" line — we match those exactly).
                for line in summary.splitlines():
                    line = line.strip()
                    if line.startswith("TRANSCRIPT:"):
                        tp = line.split(":", 1)[1].strip()
                        if tp:
                            transcripts.add(os.path.normcase(os.path.normpath(tp)))
        except sqlite3.OperationalError:
            for row in c.execute(
                "SELECT project_id, started_at FROM session_log WHERE started_at >= ?",
                (cutoff_iso,)
            ):
                rows.add(((row[0] or "").lower(), row[1] or "", ""))
        c.close()
    except Exception as e:
        print(f"[warn] could not read brain: {e}", file=sys.stderr)
    return rows, transcripts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", required=True, help="ISO date cutoff e.g. 2026-05-14")
    ap.add_argument("--output", default=None, help="Write JSON manifest here")
    args = ap.parse_args()

    cutoff_dt = datetime.fromisoformat(args.since)
    cutoff_iso = cutoff_dt.isoformat()
    registry = load_registry_paths()

    print(f"Scanning transcripts in {CLAUDE_PROJECTS_DIR}")
    print(f"Cutoff: {cutoff_iso}")
    print(f"Registry: {len(registry)} project paths")
    print()

    brain, brain_transcripts = load_brain_state_since(cutoff_iso)
    print(f"Brain has {len(brain)} session_log rows since cutoff")
    print(f"Brain has {len(brain_transcripts)} backfilled transcript-path references")
    brain_by_project: dict[str, list[tuple[str,str]]] = {}
    for pid, started, title in brain:
        brain_by_project.setdefault(pid, []).append((started, title))
    print()

    candidates = []
    seen = 0
    skipped_old = 0
    skipped_sub = 0

    for jsonl in CLAUDE_PROJECTS_DIR.rglob("*.jsonl"):
        # skip subagent transcripts
        if "subagents" in jsonl.parts:
            skipped_sub += 1
            continue
        st = jsonl.stat()
        if datetime.fromtimestamp(st.st_mtime) < cutoff_dt:
            skipped_old += 1
            continue
        seen += 1
        info = transcript_summary(jsonl)
        if not info.get("cwd"):
            # try to infer from projectdir name
            try:
                info["cwd"] = projectdir_to_cwd(jsonl.parent.name)
            except Exception:
                pass
        info["project_id"] = infer_project(info.get("cwd", ""), registry)
        info["mtime"]      = datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")
        info["size_bytes"] = st.st_size

        # Decide: probably logged or not?
        # Strategy 1: exact-match — the transcript path appears in any Brain
        # row's summary (means a previous backfill captured this one).
        # Strategy 2 (fallback): within 12h of any Brain row for the same project.
        info["likely_logged"] = False
        # Normalize aggressively — handle forward/back slashes, casing, trailing
        # whitespace differences between writer and reader.
        def _canon(p: str) -> str:
            return os.path.normcase(os.path.normpath(p.strip())).replace("/", "\\")
        tp_norm = _canon(str(jsonl))
        brain_tp_norm = {_canon(t) for t in brain_transcripts}
        if tp_norm in brain_tp_norm:
            info["likely_logged"] = True
            info["matched_via"] = "transcript_exact"
        elif info["project_id"] in brain_by_project and info.get("first_ts"):
            try:
                first_dt = datetime.fromisoformat(info["first_ts"].rstrip("Z").split("+")[0])
                for started, title in brain_by_project[info["project_id"]]:
                    try:
                        b_dt = datetime.fromisoformat(started.rstrip("Z").split("+")[0])
                        if abs((b_dt - first_dt).total_seconds()) < 12 * 3600:
                            info["likely_logged"] = True
                            info["matched_via"] = "time_proximity"
                            info["matched_brain_started"] = started
                            info["matched_brain_title"]   = title
                            break
                    except Exception:
                        continue
            except Exception:
                pass

        candidates.append(info)

    manifest = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "cutoff":       cutoff_iso,
        "transcripts_scanned": seen,
        "transcripts_skipped_old": skipped_old,
        "transcripts_skipped_subagent": skipped_sub,
        "brain_rows_in_window": len(brain),
        "candidates":   candidates,
        "summary": {
            "needs_backfill": sum(1 for c in candidates if not c["likely_logged"]),
            "already_logged": sum(1 for c in candidates if c["likely_logged"]),
        },
    }

    out_path = Path(args.output) if args.output else None
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nManifest written: {out_path}")
    else:
        print(json.dumps(manifest, indent=2, ensure_ascii=False))

    print()
    print(f"Total candidates: {len(candidates)}")
    print(f"  - needs_backfill: {manifest['summary']['needs_backfill']}")
    print(f"  - already_logged: {manifest['summary']['already_logged']}")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
Agent HR — roster and metrics for QI Hive / Claude Code sub-agents.

Tracks every agent (Hive role, Claude Code built-in, or auto-discovered) and
every run they've done: what they worked on, how long it took, how many
tokens it cost. Feeds the "Agent HR" page on the QI Hive dashboard (:8600).

DB: C:\\QIH\\engine\\hive\\agents\\agent_hr.db (stdlib sqlite3 only).

CLI:
  --seed          read C:\\APPS\\CLAUDE\\.claude\\agents\\*.md + built-ins -> agents table
  --backfill      scan Claude Code transcripts for completed sub-agent runs
  --ingest-hook   read a SubagentStop hook JSON payload from stdin, record one run
  --report        print a roster summary table
"""
import sys
import os
import re
import json
import glob
import sqlite3
import argparse
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DB_PATH        = r"C:\QIH\engine\hive\agents\agent_hr.db"
AGENTS_MD_DIR  = r"C:\APPS\CLAUDE\.claude\agents"
TRANSCRIPTS_GLOB = r"C:\Users\renne\.claude\projects\*\*.jsonl"
MAX_FILE_BYTES = 50 * 1024 * 1024
TAIL_BYTES     = 2 * 1024 * 1024   # how far back --ingest-hook looks in a live transcript

BUILTIN_AGENTS = [
    ("general-purpose", "builtin", "inherit",
     "Built-in Claude Code agent for open-ended search and multi-step tasks."),
    ("Explore", "builtin", "inherit",
     "Built-in fast, read-only codebase exploration agent."),
    ("Plan", "builtin", "inherit",
     "Built-in planning agent used to design an approach before implementation."),
    ("claude", "builtin", "inherit",
     "Default Claude agent identity when no specialized subagent_type is set."),
]

# Tool names that represent a sub-agent dispatch across observed Claude Code
# harness versions ("Task" is the documented name; this environment's
# transcripts record it as "Agent").
AGENT_TOOL_NAMES = {"Task", "Agent"}


# ── DB ────────────────────────────────────────────────────────────────────

def get_conn():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    ensure_schema(conn)
    return conn


def ensure_schema(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            name        TEXT PRIMARY KEY,
            kind        TEXT,
            model       TEXT,
            description TEXT,
            source      TEXT,
            first_seen  TEXT,
            last_active TEXT,
            status      TEXT DEFAULT 'active'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            agent       TEXT,
            project     TEXT,
            task_desc   TEXT,
            started_at  TEXT,
            duration_ms INTEGER,
            tokens      INTEGER,
            tool_uses   INTEGER,
            outcome     TEXT,
            session_id  TEXT,
            UNIQUE(agent, session_id, started_at, task_desc)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_agent ON runs(agent)")
    conn.commit()


def upsert_agent(conn, name, kind, model, description, source, first_seen=None, discovered=False):
    """INSERT OR IGNORE — never clobbers a curated agent row with noisy discovery data."""
    now = first_seen or datetime.now().isoformat()
    cur = conn.execute(
        "INSERT OR IGNORE INTO agents (name, kind, model, description, source, first_seen, last_active, status) "
        "VALUES (?, ?, ?, ?, ?, ?, NULL, 'active')",
        (name, kind, model, description, source, now),
    )
    return cur.rowcount > 0


def touch_agent_last_active(conn, name, when_iso):
    conn.execute(
        "UPDATE agents SET last_active = ? WHERE name = ? AND (last_active IS NULL OR last_active < ?)",
        (when_iso, name, when_iso),
    )


# ── --seed ────────────────────────────────────────────────────────────────

def parse_frontmatter(text):
    """Minimal YAML-frontmatter reader for `---\\nkey: value\\n---` blocks. No PyYAML dep."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end].strip("\n")
    fm = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        fm[key.strip()] = val.strip()
    return fm


def cmd_seed(conn):
    added_agents = 0
    md_files = sorted(glob.glob(os.path.join(AGENTS_MD_DIR, "*.md")))
    for md_path in md_files:
        try:
            text = Path(md_path).read_text(encoding="utf-8")
        except Exception as e:
            print(f"  skip {md_path}: {type(e).__name__}: {e}")
            continue
        fm = parse_frontmatter(text)
        if not fm or not fm.get("name"):
            continue
        mtime = datetime.fromtimestamp(os.path.getmtime(md_path)).isoformat()
        if upsert_agent(
            conn, fm["name"], "hive", fm.get("model", "sonnet"),
            fm.get("description", ""), md_path, first_seen=mtime,
        ):
            added_agents += 1

    for name, kind, model, description in BUILTIN_AGENTS:
        if upsert_agent(conn, name, kind, model, description, "builtin"):
            added_agents += 1

    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
    print(f"Seed complete: {added_agents} new agent(s) added, {total} total in roster.")


# ── transcript scanning (shared by --backfill and --ingest-hook) ───────────

def decode_project_folder(folder_name):
    """C--CLAUDE -> C:\\APPS\\CLAUDE ; best-effort, only used when a line has no cwd."""
    parts = folder_name.split("--")
    if len(parts) >= 2 and len(parts[0]) == 1 and parts[0].isalpha():
        return parts[0] + ":\\" + "\\".join(parts[1:])
    return folder_name


_USAGE_RE = {
    "tokens":      re.compile(r"subagent_tokens[^\d]{0,10}(\d+)"),
    "tool_uses":   re.compile(r"tool_uses[^\d]{0,10}(\d+)"),
    "duration_ms": re.compile(r"duration_ms[^\d]{0,10}(\d+)"),
}


def extract_usage(text):
    """Robust to both `<subagent_tokens>N</subagent_tokens>` and
    `<usage>subagent_tokens: N\\ntool_uses: N\\nduration_ms: N</usage>` shapes."""
    out = {}
    for key, rx in _USAGE_RE.items():
        m = rx.search(text)
        out[key] = int(m.group(1)) if m else None
    return out["tokens"], out["tool_uses"], out["duration_ms"]


def _result_text(content_blocks):
    if isinstance(content_blocks, str):
        return content_blocks
    parts = []
    if isinstance(content_blocks, list):
        for b in content_blocks:
            if isinstance(b, dict) and b.get("type") == "text":
                parts.append(b.get("text") or "")
    return "\n".join(parts)


def iter_runs_from_transcript(path, tail_bytes=None):
    """Yield resolved run dicts (tool_use matched with its tool_result) from one
    transcript .jsonl file. If tail_bytes is set, only the tail of the file is
    scanned (used by --ingest-hook so a live, possibly huge, transcript stays cheap)."""
    session_id_fallback = Path(path).stem
    folder_fallback = decode_project_folder(Path(path).parent.name)

    pending = {}  # tool_use_id -> dict

    try:
        size = os.path.getsize(path)
    except OSError:
        return

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        if tail_bytes and size > tail_bytes:
            f.seek(size - tail_bytes)
            f.readline()  # discard partial first line
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            except Exception:
                continue

            dtype = d.get("type")
            timestamp = d.get("timestamp") or ""
            cwd = d.get("cwd") or folder_fallback
            session_id = d.get("sessionId") or session_id_fallback

            if dtype == "assistant":
                content = (d.get("message") or {}).get("content")
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    if block.get("name") not in AGENT_TOOL_NAMES:
                        continue
                    inp = block.get("input") or {}
                    subagent_type = inp.get("subagent_type")
                    if not subagent_type:
                        continue
                    task_desc = inp.get("description") or (inp.get("prompt") or "")[:200]
                    pending[block.get("id")] = {
                        "subagent_type": subagent_type,
                        "task_desc":     task_desc,
                        "model":         inp.get("model"),
                        "started_at":    timestamp,
                        "project":       cwd,
                        "session_id":    session_id,
                    }

            elif dtype == "user":
                content = (d.get("message") or {}).get("content")
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict) or block.get("type") != "tool_result":
                        continue
                    tid = block.get("tool_use_id")
                    if tid not in pending:
                        continue
                    info = pending.pop(tid)
                    text = _result_text(block.get("content"))
                    tokens, tool_uses, duration_ms = extract_usage(text)
                    is_error = bool(block.get("is_error"))
                    yield {
                        "agent":       info["subagent_type"],
                        "project":     info["project"],
                        "task_desc":   info["task_desc"],
                        "started_at":  info["started_at"] or timestamp,
                        "duration_ms": duration_ms,
                        "tokens":      tokens,
                        "tool_uses":   tool_uses,
                        "outcome":     "error" if is_error else "completed",
                        "session_id":  info["session_id"],
                        "model":       info["model"],
                        "resolved_at": timestamp,
                    }


def record_run(conn, run, source):
    """Insert a run row + auto-onboard an unknown agent. Returns (run_added, agent_added)."""
    agent_name = run["agent"]
    known = conn.execute("SELECT 1 FROM agents WHERE name = ?", (agent_name,)).fetchone()
    agent_added = False
    if not known:
        agent_added = upsert_agent(
            conn, agent_name, "discovered", run.get("model") or "unknown",
            "HR onboarding", source, first_seen=run["started_at"] or datetime.now().isoformat(),
        )

    cur = conn.execute(
        "INSERT OR IGNORE INTO runs (agent, project, task_desc, started_at, duration_ms, tokens, "
        "tool_uses, outcome, session_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (agent_name, run["project"], run["task_desc"], run["started_at"], run["duration_ms"],
         run["tokens"], run["tool_uses"], run["outcome"], run["session_id"]),
    )
    run_added = cur.rowcount > 0
    when = run.get("resolved_at") or run["started_at"] or datetime.now().isoformat()
    touch_agent_last_active(conn, agent_name, when)
    return run_added, agent_added


# ── --backfill ────────────────────────────────────────────────────────────

def cmd_backfill(conn):
    files = sorted(glob.glob(TRANSCRIPTS_GLOB))
    runs_added = 0
    agents_added = 0
    files_scanned = 0
    files_skipped = 0

    for path in files:
        try:
            if os.path.getsize(path) > MAX_FILE_BYTES:
                files_skipped += 1
                continue
        except OSError:
            continue
        files_scanned += 1
        try:
            for run in iter_runs_from_transcript(path):
                r_added, a_added = record_run(conn, run, source=path)
                runs_added += int(r_added)
                agents_added += int(a_added)
        except Exception as e:
            print(f"  warn: {path}: {type(e).__name__}: {e}")
            continue

    conn.commit()
    print(f"Backfill complete: scanned {files_scanned} transcript(s) ({files_skipped} skipped >50MB), "
          f"{runs_added} new run(s) added, {agents_added} new agent(s) discovered.")


# ── --ingest-hook ─────────────────────────────────────────────────────────

def cmd_ingest_hook(conn):
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw else {}
    except Exception:
        payload = {}

    try:
        session_id = payload.get("session_id") or ""
        cwd = payload.get("cwd") or os.getcwd()
        transcript = payload.get("transcript_path") or ""
        agent_raw = (
            payload.get("subagent_type")
            or payload.get("agent_type")
            or payload.get("agent")
            or payload.get("subagent")
            or ""
        )

        run = None
        if transcript and os.path.exists(transcript):
            try:
                last = None
                for candidate in iter_runs_from_transcript(transcript, tail_bytes=TAIL_BYTES):
                    last = candidate  # take the most recently resolved run in the tail
                run = last
            except Exception:
                run = None

        if run:
            if not run.get("agent"):
                run["agent"] = agent_raw or "unknown_subagent"
            if not run.get("project"):
                run["project"] = cwd
            if not run.get("session_id"):
                run["session_id"] = session_id
        else:
            now_iso = datetime.now().isoformat()
            run = {
                "agent":       agent_raw or "unknown_subagent",
                "project":     cwd,
                "task_desc":   None,
                "started_at":  now_iso,
                "duration_ms": None,
                "tokens":      None,
                "tool_uses":   None,
                "outcome":     "completed",
                "session_id":  session_id,
                "model":       payload.get("model"),
                "resolved_at": now_iso,
            }

        record_run(conn, run, source="ingest-hook")
        conn.commit()
        print(f"Agent HR: recorded run for {run['agent']}")
    except Exception as e:
        print(f"Agent HR ingest skipped: {type(e).__name__}: {e}")
    # Hook must never fail the session regardless of what happened above.
    sys.exit(0)


# ── --report ──────────────────────────────────────────────────────────────

def cmd_report(conn):
    rows = conn.execute("""
        SELECT a.name, a.kind, a.model, a.last_active,
               COUNT(r.id)                    AS runs,
               COALESCE(SUM(r.tokens), 0)     AS tokens,
               COALESCE(SUM(r.duration_ms), 0) AS ms
        FROM agents a
        LEFT JOIN runs r ON r.agent = a.name
        GROUP BY a.name
        ORDER BY runs DESC, a.name ASC
    """).fetchall()

    print(f"{'AGENT':<20} {'KIND':<11} {'MODEL':<9} {'RUNS':>5} {'TOKENS':>10} {'MINUTES':>9}  LAST ACTIVE")
    print("-" * 90)
    for name, kind, model, last_active, runs, tokens, ms in rows:
        minutes = round((ms or 0) / 60000, 1)
        print(f"{name:<20} {kind or '':<11} {model or '':<9} {runs:>5} {tokens:>10} {minutes:>9}  {last_active or '-'}")
    print("-" * 90)
    print(f"{len(rows)} agent(s) on the roster.")


# ── main ──────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="QI Hive Agent HR")
    ap.add_argument("--seed", action="store_true", help="load agents from .claude/agents/*.md + built-ins")
    ap.add_argument("--backfill", action="store_true", help="scan Claude Code transcripts for past runs")
    ap.add_argument("--ingest-hook", action="store_true", help="record one run from a SubagentStop hook payload on stdin")
    ap.add_argument("--report", action="store_true", help="print roster summary")
    args = ap.parse_args()

    if args.ingest_hook:
        # Do not run ensure_schema-heavy setup before we can guarantee exit 0.
        try:
            conn = get_conn()
        except Exception as e:
            print(f"Agent HR ingest skipped (db unavailable): {type(e).__name__}: {e}")
            sys.exit(0)
        cmd_ingest_hook(conn)
        return  # unreachable, cmd_ingest_hook always exits

    conn = get_conn()
    did_something = False
    if args.seed:
        cmd_seed(conn)
        did_something = True
    if args.backfill:
        cmd_backfill(conn)
        did_something = True
    if args.report:
        cmd_report(conn)
        did_something = True
    if not did_something:
        ap.print_help()
    conn.close()


if __name__ == "__main__":
    main()

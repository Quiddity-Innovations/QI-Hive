# AI-GENERATED BEGIN (Claude Code, 2026-06-19)
"""BU Hive session capture hook.

Invoked by Claude Code hooks (SessionStart / SessionEnd) with the hook JSON on
stdin. Writes meeting-minutes to C:\\AI\\Sessions\\code, a raw log header to
C:\\AI\\Logs, and rows into the BU Hive SQLite DB. Defensive by design: ANY error
is logged to C:\\AI\\Error\\bu-hive and the process still exits 0, so capture can
never break a Claude session.

Verified hook contract (Claude Code 2.x, code.claude.com/docs/en/hooks):
  common stdin fields: session_id, transcript_path, cwd, hook_event_name
  SessionStart adds: source, model?, session_title?
  SessionEnd adds:   reason
  transcript_path is a JSONL file (one message object per line).
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# --- Fixed C:\AI taxonomy (framework standard); user resolved by Windows itself.
SESSIONS_DIR = Path(r"C:\AI\Sessions\code")
LOGS_DIR     = Path(r"C:\AI\Logs")
DB_PATH      = Path(r"C:\AI\BU Hive\data\bu_hive.db")
STATE_DIR    = Path(r"C:\AI Temp\bu-hive\sessions")
ERROR_DIR    = Path(r"C:\AI\Error\bu-hive")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _log_error(msg: str) -> None:
    try:
        ERROR_DIR.mkdir(parents=True, exist_ok=True)
        f = ERROR_DIR / f"error_{datetime.now():%Y-%m-%d}.log"
        with f.open("a", encoding="utf-8") as fh:
            fh.write(f"[{_now()}] session_capture: {msg}\n")
    except Exception:
        pass


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return s or "session"


def _state_path(session_id: str) -> Path:
    return STATE_DIR / f"{_slug(session_id)}.json"


def _db():
    if not DB_PATH.exists():
        return None
    try:
        con = sqlite3.connect(str(DB_PATH))
        con.execute("PRAGMA busy_timeout=3000")
        return con
    except Exception as exc:
        _log_error(f"db connect failed: {exc}")
        return None


def on_session_start(data: dict) -> None:
    sid = data.get("session_id", "unknown")
    cwd = data.get("cwd", "")
    model = data.get("model", "")
    title = data.get("session_title") or Path(cwd).name or "session"
    slug = _slug(title)
    started = _now()
    started_file = datetime.now().strftime("%Y-%m-%d")
    started_time = datetime.now().strftime("%H-%M-%S")

    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    minutes = SESSIONS_DIR / f"{started_file}_code_{slug}_{_slug(sid)[:8]}.md"
    minutes.write_text(
        f"# Session Minutes - {title}\n\n"
        f"- **Date:** {started_file}\n"
        f"- **Surface:** code\n"
        f"- **Attendees:** Renne Santiago (rennesan), Claude ({model or 'cloud'})\n"
        f"- **Started:** {started}\n"
        f"- **Session id:** {sid}\n"
        f"- **CWD:** {cwd}\n\n"
        f"## Topics discussed\n_(auto-filled at session end)_\n\n"
        f"## Decisions\n\n## Action items\n\n"
        f"## Artifacts produced\n\n## Session summary (auto)\n_(pending session end)_\n",
        encoding="utf-8",
    )

    logf = LOGS_DIR / f"{slug}_{started_file}_{started_time}.txt"
    logf.write_text(
        "================================================================\n"
        " Session Log\n"
        "================================================================\n"
        f"Session name : {slug}\n"
        f"Surface      : code (Claude Code)\n"
        f"Started      : {started} America/New_York\n"
        f"Transcript   : {data.get('transcript_path','')}\n"
        "================================================================\n\n"
        f"[{started}] --- session start ---\n",
        encoding="utf-8",
    )

    db_session_id = None
    con = _db()
    if con:
        try:
            cur = con.execute(
                "INSERT INTO sessions (started_at, surface, title, model) VALUES (?,?,?,?)",
                (started, "code", slug, model),
            )
            db_session_id = cur.lastrowid
            con.commit()
        except Exception as exc:
            _log_error(f"session insert failed: {exc}")
        finally:
            con.close()

    _state_path(sid).write_text(
        json.dumps({
            "minutes": str(minutes), "log": str(logf), "slug": slug,
            "started": started, "db_session_id": db_session_id,
            "transcript": data.get("transcript_path", ""),
        }), encoding="utf-8",
    )


def _duration_ms(start: str, end: str):
    """Best-effort ms between two transcript timestamps (ISO 8601 or our own
    '%Y-%m-%d %H:%M:%S'). Returns None if either is missing/unparseable."""
    def _parse(t):
        if not t:
            return None
        t = t.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(t)
        except Exception:
            try:
                return datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
            except Exception:
                return None
    a, b = _parse(start), _parse(end)
    if not a or not b:
        return None
    try:
        ms = int((b - a).total_seconds() * 1000)
        return ms if ms >= 0 else None
    except Exception:
        return None


def _parse_transcript(path: str) -> dict:
    """Tolerant JSONL parse: counts turns, tool calls, files, git commands, and
    spun-off subagents (Task/Agent tool launches paired with their results)."""
    out = {"user_turns": 0, "assistant_turns": 0, "tool_calls": 0,
           "tools": {}, "files": set(), "git": [], "entries": 0, "subagents": []}
    # AI-GENERATED BEGIN (Claude Code, 2026-06-22) — subagent run capture (approval #17)
    pending = {}  # tool_use_id -> run dict, finalized when its tool_result is seen
    # AI-GENERATED END
    p = Path(path) if path else None
    if not p or not p.exists():
        return out
    try:
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            out["entries"] += 1
            try:
                obj = json.loads(line)
            except Exception:
                continue
            msg = obj.get("message", obj)
            role = msg.get("role") or obj.get("type")
            ts = obj.get("timestamp") or msg.get("timestamp") or ""
            if role == "user":
                out["user_turns"] += 1
            elif role == "assistant":
                out["assistant_turns"] += 1
            content = msg.get("content")
            blocks = content if isinstance(content, list) else []
            for b in blocks:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_use":
                    out["tool_calls"] += 1
                    name = b.get("name", "?")
                    out["tools"][name] = out["tools"].get(name, 0) + 1
                    ti = b.get("input", {}) or {}
                    # AI-GENERATED BEGIN (Claude Code, 2026-06-22) — spun-off subagent launch
                    if name in ("Task", "Agent"):
                        run = {
                            "subagent_type": (ti.get("subagent_type") or "").strip(),
                            "description": (ti.get("description") or "").strip()[:300],
                            "started_at": ts, "ended_at": "", "outcome": "ok",
                        }
                        bid = b.get("id")
                        if bid:
                            pending[bid] = run
                        out["subagents"].append(run)
                    # AI-GENERATED END
                    fp = ti.get("file_path") or ti.get("path")
                    if fp:
                        out["files"].add(str(fp))
                    if name == "Bash":
                        cmd = (ti.get("command") or "")
                        if re.search(r"\bgit\s+(commit|push|reset|rebase|clean|branch)\b", cmd):
                            out["git"].append(cmd.strip()[:120])
                # AI-GENERATED BEGIN (Claude Code, 2026-06-22) — pair subagent result
                elif b.get("type") == "tool_result":
                    run = pending.get(b.get("tool_use_id"))
                    if run:
                        run["ended_at"] = ts
                        if b.get("is_error"):
                            run["outcome"] = "error"
                # AI-GENERATED END
    except Exception as exc:
        _log_error(f"transcript parse failed: {exc}")
    return out


def on_session_end(data: dict) -> None:
    sid = data.get("session_id", "unknown")
    ended = _now()
    sp = _state_path(sid)
    state = {}
    if sp.exists():
        try:
            state = json.loads(sp.read_text(encoding="utf-8"))
        except Exception:
            state = {}

    transcript = data.get("transcript_path") or state.get("transcript", "")
    stats = _parse_transcript(transcript)

    tools_line = ", ".join(f"{k}×{v}" for k, v in sorted(stats["tools"].items())) or "none"
    files_list = "\n".join(f"- {f}" for f in sorted(stats["files"])) or "_none recorded_"
    git_list = "\n".join(f"- `{g}`" for g in stats["git"]) or "_none_"
    summary = (
        f"- **Ended:** {ended}  (reason: {data.get('reason','?')})\n"
        f"- **Turns:** {stats['user_turns']} user / {stats['assistant_turns']} assistant\n"
        f"- **Tool calls:** {stats['tool_calls']}  ({tools_line})\n"
        f"- **Transcript entries:** {stats['entries']}\n\n"
        f"**Files touched:**\n{files_list}\n\n"
        f"**Git commands seen:**\n{git_list}\n"
    )

    minutes = Path(state["minutes"]) if state.get("minutes") else None
    if minutes and minutes.exists():
        try:
            txt = minutes.read_text(encoding="utf-8")
            txt = txt.replace("## Session summary (auto)\n_(pending session end)_\n",
                              f"## Session summary (auto)\n{summary}")
            minutes.write_text(txt, encoding="utf-8")
        except Exception as exc:
            _log_error(f"minutes finalize failed: {exc}")
    else:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        fallback = SESSIONS_DIR / f"{datetime.now():%Y-%m-%d}_code_{_slug(sid)[:8]}.md"
        fallback.write_text(f"# Session Minutes (recovered)\n\n## Session summary (auto)\n{summary}", encoding="utf-8")

    logf = Path(state["log"]) if state.get("log") else None
    if logf and logf.exists():
        try:
            with logf.open("a", encoding="utf-8") as fh:
                fh.write(f"\n[{ended}] --- session end ---\n")
        except Exception:
            pass

    con = _db()
    if con:
        try:
            db_sid = state.get("db_session_id")
            if db_sid:
                con.execute(
                    "UPDATE sessions SET ended_at=?, turns=?, tool_calls=?, summary=? WHERE id=?",
                    (ended, stats["user_turns"] + stats["assistant_turns"],
                     stats["tool_calls"], f"tools: {tools_line}", db_sid),
                )
            for g in stats["git"]:
                con.execute(
                    "INSERT INTO git_events (session_id, command, decision, created_at) VALUES (?,?,?,?)",
                    (db_sid, g, "seen", ended),
                )
            # AI-GENERATED BEGIN (Claude Code, 2026-06-22) — record spun-off subagents (approval #17)
            for run in stats.get("subagents", []):
                stype = run.get("subagent_type") or "subagent"
                slug = stype if stype.startswith("bu-") else None  # roster member, else ad-hoc
                # No paired result by session-end => the run never completed.
                outcome = run.get("outcome") or "ok"
                if not run.get("ended_at"):
                    outcome = "incomplete"
                con.execute(
                    "INSERT INTO agent_runs (session_id, agent_slug, adhoc_label, started_at,"
                    " ended_at, duration_ms, tool_calls, outcome, task_summary)"
                    " VALUES (?,?,?,?,?,?,?,?,?)",
                    (db_sid, slug, stype, run.get("started_at") or ended,
                     run.get("ended_at") or None,
                     _duration_ms(run.get("started_at"), run.get("ended_at")),
                     0, outcome,
                     run.get("description") or stype),
                )
            # AI-GENERATED END
            con.commit()
        except Exception as exc:
            _log_error(f"session end db update failed: {exc}")
        finally:
            con.close()


def main() -> None:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception as exc:
        _log_error(f"bad stdin: {exc}")
        sys.exit(0)

    event = data.get("hook_event_name", "")
    try:
        if event == "SessionStart":
            on_session_start(data)
        elif event == "SessionEnd":
            on_session_end(data)
        # Stop / others: intentionally ignored (per-turn; not session-level)
    except Exception as exc:
        _log_error(f"handler {event} failed: {exc}")
    sys.exit(0)


if __name__ == "__main__":
    main()
# AI-GENERATED END

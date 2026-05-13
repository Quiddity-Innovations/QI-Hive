# -*- coding: utf-8 -*-
"""
QI Hive Ingester - reads reports from C:\\QIH\\shared\\reports\\inbox\\
and files them into:
  1. status.json (legacy, for backward compat with dashboard fallback paths)
  2. qi_brain.db session_log table (PRIMARY - dashboard now reads from here)

Runs in a simple loop; installable as NSSM service QI_HiveIngest.
"""
from __future__ import annotations
import json
import sqlite3
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT     = Path(r"C:\QIH")
INBOX    = ROOT / "shared" / "reports" / "inbox"
ARCHIVE  = ROOT / "shared" / "reports" / "archive"
STATUS   = ROOT / "data" / "status.json"
BRAIN_DB = ROOT / "data" / "qi_brain.db"
LOG_DIR  = ROOT / "logs" / "hive"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG = LOG_DIR / "ingest.log"

for d in [INBOX, ARCHIVE]:
    d.mkdir(parents=True, exist_ok=True)


def log(msg: str) -> None:
    line = f"{datetime.now().isoformat()}  {msg}"
    print(line, flush=True)
    try:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_status() -> dict:
    if STATUS.exists():
        return json.loads(STATUS.read_text(encoding="utf-8"))
    return {"projects": {}, "hive_reports": []}


def save_status(s: dict) -> None:
    STATUS.write_text(json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8")


def write_to_brain(payload: dict) -> bool:
    """Insert a session_log row in qi_brain.db. Returns True on success."""
    if not BRAIN_DB.exists():
        log(f"[BRAIN] DB missing at {BRAIN_DB}; skipping insert")
        return False
    try:
        ts = (payload.get("timestamp") or payload.get("session_date")
              or datetime.now().isoformat()).replace("T", " ")
        # Truncate microseconds and timezone for clean DB timestamps
        if "." in ts:
            ts = ts.split(".")[0]
        if "+" in ts:
            ts = ts.split("+")[0]

        project = payload.get("project") or "unknown"
        # Map "unknown" / "?" / empty to "claude_manager" if source is claude_code
        if project in ("unknown", "?", "", None) and payload.get("source") == "claude_code":
            project = "claude_manager"

        source = payload.get("source") or "unknown"
        # Prefer explicit agent_id in payload (set by sub-agent hooks); else derive from source.
        explicit_agent = (payload.get("agent_id") or payload.get("agent") or "").strip()
        if explicit_agent:
            # Normalize: "hive-architect" / "architect" -> "hive_architect" (matches DB rows)
            norm = explicit_agent.lower().replace("-", "_")
            if norm in ("architect", "builder", "inspector", "ops", "scout", "scribe", "tester"):
                agent_id = f"hive_{norm}"
            else:
                agent_id = norm
        else:
            agent_id = {
                "claude_code": "claude",
                "claude_work": "cowork",
                "openclaw":    "openclaw",
            }.get(source, source)

        title = payload.get("title") or payload.get("event") or "session_end"
        # Make a more readable title if we have summary content
        summary = (payload.get("summary") or "").strip()
        if title in ("session_end", "session_report") and summary:
            # First 60 chars of summary as title
            title = summary[:60] + ("..." if len(summary) > 60 else "")

        model_used = payload.get("model_used") or "unknown"
        files_changed = payload.get("outputs") or []
        next_steps = payload.get("next_suggested") or payload.get("next_steps") or []

        conn = sqlite3.connect(str(BRAIN_DB), timeout=5.0)
        try:
            conn.execute("""
                INSERT INTO session_log
                  (project_id, agent_id, session_title, summary,
                   decisions_made, features_logged, files_changed, next_steps,
                   model_used, started_at, ended_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project,
                agent_id,
                title,
                summary or "(no summary captured)",
                len(payload.get("decisions") or []),
                0,
                json.dumps(files_changed),
                "\n".join(str(x) for x in next_steps) if isinstance(next_steps, list) else str(next_steps),
                model_used,
                ts,
                ts,
            ))
            conn.commit()
            sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            log(f"[BRAIN] inserted session_log id={sid} project={project} agent={agent_id}")
            return True
        finally:
            conn.close()
    except Exception as e:
        log(f"[BRAIN ERROR] {type(e).__name__}: {e}")
        return False


def ingest(path: Path) -> None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        log(f"[ERROR] cannot parse {path.name}: {e}")
        shutil.move(str(path), str(ARCHIVE / f"BAD_{path.name}"))
        return

    project = payload.get("project", "?")
    event   = payload.get("event", payload.get("type", "?"))
    log(f"[{project}] {event} - {(payload.get('summary') or '')[:80]}")

    # 1) Legacy status.json append
    try:
        s = load_status()
        s.setdefault("hive_reports", [])
        s["hive_reports"].append(payload)
        s["hive_reports"] = s["hive_reports"][-500:]
        if project in s.get("projects", {}):
            proj = s["projects"][project]
            proj["last_activity"] = datetime.now().strftime("%Y-%m-%d")
            if event == "session_end" and payload.get("summary"):
                proj.setdefault("recent_sessions", [])
                proj["recent_sessions"].append({
                    "at": payload.get("timestamp", datetime.now().isoformat()),
                    "summary": payload["summary"],
                    "next_steps": payload.get("next_steps") or payload.get("next_suggested", []),
                })
                proj["recent_sessions"] = proj["recent_sessions"][-20:]
        save_status(s)
    except Exception as e:
        log(f"[STATUS ERROR] {type(e).__name__}: {e}")

    # 2) Brain DB insert (primary path)
    write_to_brain(payload)

    # 3) Archive
    try:
        shutil.move(str(path), str(ARCHIVE / path.name))
    except Exception as e:
        log(f"[ARCHIVE ERROR] {type(e).__name__}: {e}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    log("QI Hive Ingester starting (status.json + qi_brain.db)")
    log(f"inbox: {INBOX}")
    log(f"brain_db: {BRAIN_DB}")
    while True:
        try:
            for p in sorted(INBOX.glob("*.json"), key=lambda x: x.stat().st_mtime):
                ingest(p)
            time.sleep(2)
        except KeyboardInterrupt:
            log("shutting down")
            break
        except Exception as e:
            log(f"[LOOP ERROR] {type(e).__name__}: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
QI Ecosystem Health Check
Queries every project for: service status, git state, doc freshness, active tasks.
Run standalone or imported by the dashboard.
"""

import json
import os
import subprocess
import sys
import time
import threading
from datetime import datetime, timezone
from pathlib import Path

# ── TTL cache ────────────────────────────────────────────────────────────────
# run_health_check() fans out many subprocess calls (sc, netstat, git). On
# every dashboard page load this adds seconds of latency. Cache the result
# for HEALTH_CACHE_TTL seconds so back-to-back page loads are fast.
HEALTH_CACHE_TTL = 30  # seconds
_health_cache = {"t": 0.0, "data": None}
_health_lock = threading.Lock()

# ── Service name map ────────────────────────────────────────────────────────
# Registry project IDs that have known NSSM service names not derivable from
# the registry alone. Keys are registry `id` values (lowercase).
_SERVICE_MAP = {
    "maia":             "QI_MaiaBot",
    "naya":             "QI_NayaBot",
    "nexus":            "QI_NEXUS",
    "cognibase":        "QI_CogniBase",
    "mapsnap":          "QI_MapSnap",
    "autopdf":          "QI_AutoPDF",
    "lotterywiz":       "QI_LotteryWiz",
    "cypherminer":      "QI_CypherMinerUI",
    "tubescout":        "QI_TubeScout",
    "fidelityanalyzer": "QI_FidelityAnalyzer",
    "avatarstudio":     "QI_AvatarStudio",
    "personalsong":     "QI_PersonalSong",
    "m2v":              "QI_M2V",
    "mq":               "QI_MQ",
    "qi_brain":         "QI_BrainAPI",
    "qi_hive":          "QI_Dashboard",
}

# Project IDs that have a public Cloudflare tunnel service.
_TUNNEL_IDS = {
    "maia", "naya", "nexus", "cognibase", "mapsnap",
    "autopdf", "lotterywiz", "cypherminer", "tubescout", "m2v",
}

# Project IDs that have no NSSM service at all (static sites, WSL, no-op).
_NO_SERVICE_IDS = {
    "openclaw", "easyflow", "universal", "filehq",
    "claude_manager", "digitization", "digicost",
}

_REGISTRY_PATH = Path(r"C:\QIH\ecosystem\qi_registry.json")


def _first_port(ports_dict: dict) -> int | None:
    """Return the first usable integer port from a registry project's `ports` dict."""
    for key in ("api", "http", "dashboard", "ui", "gateway"):
        entry = ports_dict.get(key)
        if isinstance(entry, dict):
            val = entry.get("current")
            if isinstance(val, int):
                return val
    return None


def _build_projects_from_registry() -> dict:
    """
    Dynamically build the PROJECTS structure from qi_registry.json.
    Returns a dict keyed by display name with the same shape the health-check
    logic and dashboard renderer expect.
    """
    with open(_REGISTRY_PATH, encoding="utf-8") as fh:
        reg = json.load(fh)

    projects = {}
    for entry in reg.get("projects", []):
        pid = entry.get("id", "").lower()
        name = entry.get("name") or pid
        path = entry.get("path") or entry.get("path_standard") or ""

        ports = entry.get("ports", {})
        api_port = _first_port(ports)

        # UI port: second pass for explicit "ui" key when api already consumed another
        ui_port = None
        ui_entry = ports.get("ui")
        if isinstance(ui_entry, dict):
            ui_port = ui_entry.get("current") if isinstance(ui_entry.get("current"), int) else None

        service = None if pid in _NO_SERVICE_IDS else _SERVICE_MAP.get(pid)
        tunnel = f"QI_{name.replace(' ', '')}Tunnel" if pid in _TUNNEL_IDS else None

        # Derive sensible doc_path: prefer DOCUMENTATION sub-folder; fall back to path root.
        doc_path = str(Path(path) / "DOCUMENTATION") if path else path

        cfg = {
            "path": path,
            "service": service,
            "tunnel": tunnel,
            "api_port": api_port,
            "ui_port": ui_port,
            "db": None,
            "doc_path": doc_path,
            "key_files": [],
        }

        note = entry.get("status_reason") or entry.get("family_notes") or entry.get("path_migration_note")
        if note:
            cfg["note"] = note[:200]

        # Use the human-readable name as key to keep dashboard display consistent.
        projects[name] = cfg

    return projects


# ── Project registry ────────────────────────────────────────────────────────
# Fallback used when the registry file cannot be read.
_PROJECTS_FALLBACK = {
    "Maia": {
        "path": r"C:\QI",
        "service": "QI_MaiaBot",
        "tunnel": "QI_MaiaTunnel",
        "api_port": 8001,
        "ui_port": 7860,
        "db": r"C:\QI\maia.db",
        "doc_path": r"C:\QI\DOCUMENTATION",
        "key_files": ["maia_server.py", "maia_gradio.py"],
    },
    "Naya": {
        "path": r"C:\NAYA",
        "service": "QI_NayaBot",
        "tunnel": None,
        "api_port": 8002,
        "ui_port": 7861,
        "db": r"C:\NAYA\naya.db",
        "doc_path": r"C:\NAYA\DOCUMENTATION",
        "key_files": ["naya_server.py"],
    },
    "NEXUS": {
        "path": r"C:\NEXUS",
        "service": "QI_NEXUS",
        "tunnel": None,
        "api_port": 8010,
        "ui_port": 7880,
        "db": r"C:\NEXUS\nexus.db",
        "doc_path": r"C:\NEXUS\Quiddity Innovations - NEXUS Documentation",
        "key_files": ["main.py"],
    },
    "OpenClaw": {
        "path": r"C:\OC",
        "service": None,
        "tunnel": None,
        "api_port": None,
        "ui_port": None,
        "db": None,
        "doc_path": r"C:\OC\DOCUMENTATION",
        "key_files": [],
        "note": "Runs in WSL — service check not applicable",
    },
    "MQ": {
        "path": r"C:\MQ",
        "service": None,
        "tunnel": None,
        "api_port": None,
        "ui_port": None,
        "db": r"C:\MQ\mq.db",
        "doc_path": r"C:\MQ\DOCUMENTATION",
        "key_files": [],
        "note": "Not yet live — waiting on Meta credentials",
    },
    "QI Hive": {
        "path": r"C:\QIH",
        "service": "QI_Dashboard",
        "tunnel": None,
        "api_port": 8600,
        "ui_port": None,
        "db": None,
        "doc_path": r"C:\QIH\engine\hive\dashboard\LOGS",
        "key_files": ["engine/hive/dashboard/server.py"],
        "note": "QI Hive — dashboard + agent system. Brain at port 9011.",
    },
    "QI Brain": {
        "path": r"C:\QIH\engine\brain",
        "service": "QI_BrainAPI",
        "tunnel": None,
        "api_port": 9011,
        "ui_port": None,
        "db": r"C:\QIH\data\qi_brain.db",
        "doc_path": r"C:\QIH\engine\brain",
        "key_files": ["api.py"],
        "note": "QI Brain — hive nervous system. SQLite + ChromaDB + MCP.",
    },
    "EasyFlow": {
        "path": r"C:\EasyFlow",
        "service": None,
        "tunnel": None,
        "api_port": 8550,
        "ui_port": None,
        "db": None,
        "doc_path": r"C:\EasyFlow\DOCUMENTATION",
        "key_files": ["app.py"],
        "note": "Email/inbox tier automation. Local Flask dashboard (not NSSM).",
    },
    "Claude Manager": {
        "path": r"C:\CLAUDE",
        "service": None,
        "tunnel": None,
        "api_port": None,
        "ui_port": None,
        "db": None,
        "doc_path": r"C:\CLAUDE\DOCUMENTATION",
        "key_files": [],
        "note": "Orchestration/PM layer. No served ports.",
    },
    "FileHQ": {
        "path": r"C:\NAYA\filehq",
        "service": None,
        "tunnel": None,
        "api_port": None,
        "ui_port": None,
        "db": None,
        "doc_path": r"C:\NAYA\filehq",
        "key_files": [],
        "note": "Merged into Naya 2026-Q1. Kept for visibility.",
    },
}

try:
    PROJECTS = _build_projects_from_registry()
except Exception as _reg_err:
    import warnings as _warnings
    _warnings.warn(
        f"[health_check] Failed to load registry ({_reg_err}); using fallback PROJECTS dict.",
        RuntimeWarning,
        stacklevel=1,
    )
    PROJECTS = _PROJECTS_FALLBACK

STATUS_FILE = Path(r"C:\Claude\status.json")


# ── Helpers ──────────────────────────────────────────────────────────────────

def run(cmd, cwd=None, timeout=8):
    """Run a shell command, return (stdout, returncode)."""
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            cwd=cwd, timeout=timeout, encoding="utf-8", errors="replace"
        )
        return r.stdout.strip(), r.returncode
    except Exception as e:
        return str(e), -1


def check_service(name):
    """Returns 'running', 'paused', 'stopped', 'not_found', or 'n/a'."""
    if not name:
        return "n/a"
    out, code = run(f'sc query "{name}"')
    if "RUNNING" in out:
        return "running"
    if "PAUSED" in out:
        return "paused"
    if "STOPPED" in out:
        return "stopped"
    if "does not exist" in out or code != 0:
        return "not_found"
    return "unknown"


def check_port(port):
    """Returns True if something is listening on the port."""
    if not port:
        return None
    out, _ = run(f'netstat -ano | findstr ":{port} "')
    return "LISTENING" in out


def git_status(path):
    """Returns dict with last_commit, branch, uncommitted."""
    if not Path(path).exists():
        return {"error": "path not found"}

    branch, _ = run("git rev-parse --abbrev-ref HEAD", cwd=path)
    last_commit, _ = run('git log -1 --format="%ci | %s"', cwd=path)
    dirty, _ = run("git status --porcelain", cwd=path)

    return {
        "branch": branch or "unknown",
        "last_commit": last_commit or "no commits",
        "uncommitted_changes": len(dirty.splitlines()) if dirty else 0,
    }


def doc_freshness(doc_path, code_path):
    """
    Compare newest code file mtime vs newest doc file mtime.
    Returns: 'current', 'stale', 'no_docs', or 'no_code'
    """
    def newest_mtime(folder, exts):
        folder = Path(folder)
        if not folder.exists():
            return None
        files = [f for f in folder.rglob("*") if f.suffix in exts and f.is_file()]
        return max((f.stat().st_mtime for f in files), default=None)

    code_mtime = newest_mtime(code_path, {".py", ".js", ".ts", ".sql"})
    doc_mtime = newest_mtime(doc_path, {".md", ".docx", ".pdf"})

    if not code_mtime:
        return "no_code"
    if not doc_mtime:
        return "no_docs"

    diff_days = (code_mtime - doc_mtime) / 86400
    if diff_days > 3:
        return f"stale ({int(diff_days)}d behind)"
    return "current"


def check_summary(path):
    """Check if SUMMARY.md exists and return first line."""
    summary = Path(path) / "SUMMARY.md"
    if not summary.exists():
        return None
    try:
        with open(summary, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    return line
        return "exists"
    except Exception:
        return "exists"


# ── Main check ───────────────────────────────────────────────────────────────

def run_health_check(force: bool = False):
    """Cached public entrypoint. Pass force=True to skip the 30s cache."""
    now = time.time()
    if not force:
        with _health_lock:
            if _health_cache["data"] is not None and (now - _health_cache["t"]) < HEALTH_CACHE_TTL:
                return _health_cache["data"]
    data = _compute_health_check()
    with _health_lock:
        _health_cache["t"] = time.time()
        _health_cache["data"] = data
    return data


def _compute_health_check():
    results = {}
    checked_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for name, cfg in PROJECTS.items():
        path = cfg["path"]
        exists = Path(path).exists()

        project_result = {
            "name": name,
            "path": path,
            "exists": exists,
            "checked_at": checked_at,
        }

        if not exists:
            project_result["status"] = "path_missing"
            results[name] = project_result
            continue

        # Service check
        svc = check_service(cfg.get("service"))
        tunnel = check_service(cfg.get("tunnel"))
        project_result["service"] = svc
        if cfg.get("tunnel"):
            project_result["tunnel"] = tunnel

        # Port check
        api_port = cfg.get("api_port")
        if api_port:
            project_result["port_open"] = check_port(api_port)

        # Git
        project_result["git"] = git_status(path)

        # Docs
        doc_path = cfg.get("doc_path", path)
        project_result["docs"] = doc_freshness(doc_path, path)

        # Summary
        project_result["has_summary"] = check_summary(path) is not None

        # DB
        db = cfg.get("db")
        if db:
            project_result["db_exists"] = Path(db).exists()

        # Notes
        if cfg.get("note"):
            project_result["note"] = cfg["note"]

        # Overall health signal
        issues = []
        if svc == "stopped":
            issues.append("service stopped")
        if svc == "not_found":
            issues.append("service not installed")
        if "stale" in str(project_result.get("docs", "")):
            issues.append(project_result["docs"])
        if not project_result.get("has_summary"):
            issues.append("no SUMMARY.md")
        if project_result.get("git", {}).get("uncommitted_changes", 0) > 0:
            issues.append(f"{project_result['git']['uncommitted_changes']} uncommitted files")

        project_result["issues"] = issues
        project_result["health"] = "ok" if not issues else ("warning" if len(issues) <= 2 else "attention")

        results[name] = project_result

    return {"checked_at": checked_at, "projects": results}


BRAIN_DB = Path(r"C:\QIH\data\qi_brain.db")


def _promote_dispatches_to_tasks(tasks: list) -> list:
    """Promote approved/applied dispatches from Brain into the task list."""
    if not BRAIN_DB.exists():
        return tasks
    existing_ids = {t.get("id") for t in tasks}
    try:
        import sqlite3 as _sql
        conn = _sql.connect(BRAIN_DB)
        conn.row_factory = _sql.Row
        rows = conn.execute(
            """SELECT dispatch_id, project_id, status, apply_state, payload,
                      reviewed_at, created_at
               FROM dispatches
               WHERE reviewed_at IS NOT NULL OR apply_state IS NOT NULL
               ORDER BY COALESCE(reviewed_at, created_at) DESC
               LIMIT 200"""
        ).fetchall()
        conn.close()
    except Exception as e:
        print(f"[health_check] dispatch promotion query failed: {e}", file=sys.stderr)
        return tasks

    import json as _json
    for r in rows:
        task_id = f"disp-{r['dispatch_id']}"
        if task_id in existing_ids:
            continue
        try:
            payload = _json.loads(r["payload"]) if r["payload"] else {}
        except Exception:
            payload = {}
        title = (payload.get("message") or f"Dispatch {r['dispatch_id'][:8]}")[:120]
        _sf = payload.get("suggested_fix") or ""
        if isinstance(_sf, dict):
            _sf = _json.dumps(_sf, ensure_ascii=False)
        elif not isinstance(_sf, str):
            _sf = str(_sf)
        suggested_fix = _sf[:500]
        fix_category = payload.get("fix_category") or ""
        apply_state = (r["apply_state"] or "").lower()
        if apply_state in ("applied",):
            column = "done"
        elif apply_state in ("in_progress", "queued", "review"):
            column = "in_progress"
        elif apply_state in ("rejected_auto", "failed"):
            column = "review"
        else:
            column = "backlog"
        ts = (r["created_at"] or r["reviewed_at"] or "")
        tasks.append({
            "id": task_id,
            "title": title,
            "project": r["project_id"] or "qihive",
            "agent": "cowork",
            "priority": "medium",
            "description": suggested_fix,
            "column": column,
            "created_at": ts.split("T")[0] if "T" in ts else ts[:10],
            "category": fix_category,
            "source": "brain_dispatch",
        })
        existing_ids.add(task_id)
    return tasks


def sync_tasks(health_data: dict):
    """
    Keep tasks.json in sync with actual project state.
    - Marks tasks as DONE if the underlying issue is resolved.
    - Creates new tasks for issues not yet on the board.
    - Never creates a duplicate.
    """
    import uuid as _uuid

    tasks_path = Path(r"C:\QIH\data\tasks.json")
    if not tasks_path.exists():
        return

    with open(tasks_path, encoding="utf-8") as f:
        tasks_data = json.load(f)
    tasks = tasks_data.get("tasks", [])

    tasks = _promote_dispatches_to_tasks(tasks)

    # Issue fingerprint → task auto-resolution rules
    # If condition is now clear, move matching open task to done
    resolutions = []
    for name, p in health_data.get("projects", {}).items():
        svc = p.get("service", "")
        port = p.get("port_open")
        dirty = p.get("git", {}).get("uncommitted_changes", 0)

        # Service now running → resolve service tasks for this project
        if svc == "running":
            resolutions.append((name, ["service not installed", "service stopped"]))

        # Port now open → resolve port tasks
        if port:
            resolutions.append((name, ["port closed", "port not open"]))

        # No uncommitted files → resolve commit tasks
        if dirty == 0:
            resolutions.append((name, ["uncommitted files", "uncommitted changes", "commit loose"]))

        # Docs current → resolve stale docs tasks
        if p.get("docs") == "current":
            resolutions.append((name, ["stale", "docs behind", "documentation"]))

    # Apply resolutions — move open tasks to done if issue is cleared
    for proj, keywords in resolutions:
        for t in tasks:
            if t.get("project") == proj and t.get("column") != "done":
                title_lower = t["title"].lower()
                desc_lower = t.get("description", "").lower()
                if any(kw in title_lower or kw in desc_lower for kw in keywords):
                    t["column"] = "done"

    # Create new tasks for open issues not already on the board
    open_titles = {t["title"].lower() for t in tasks if t.get("column") != "done"}
    today = datetime.now().strftime("%Y-%m-%d")

    issue_templates = {
        "service not installed": lambda n: {
            "title": f"Install {n} NSSM service",
            "description": f"{n} service not found. Register with NSSM.",
            "agent": "ops", "priority": "high"
        },
        "service stopped": lambda n: {
            "title": f"Restart {n} service",
            "description": f"{n} service is installed but stopped.",
            "agent": "ops", "priority": "high"
        },
        "uncommitted files": lambda n: {
            "title": f"Commit loose files in {n}",
            "description": f"{n} has uncommitted changes. Review and commit.",
            "agent": "builder", "priority": "medium"
        },
        "no SUMMARY.md": lambda n: {
            "title": f"Write SUMMARY.md for {n}",
            "description": f"{n} is missing its plain-English SUMMARY.md.",
            "agent": "scribe", "priority": "low"
        },
    }

    for name, p in health_data.get("projects", {}).items():
        for issue in p.get("issues", []):
            for key, template_fn in issue_templates.items():
                if key.lower() in issue.lower():
                    tmpl = template_fn(name)
                    if tmpl["title"].lower() not in open_titles:
                        new_task = {
                            "id": "t" + _uuid.uuid4().hex[:6],
                            "column": "backlog",
                            "project": name,
                            "created_at": today,
                            **tmpl,
                        }
                        tasks.append(new_task)
                        open_titles.add(tmpl["title"].lower())

    tasks_data["tasks"] = tasks
    with open(tasks_path, "w", encoding="utf-8") as f:
        json.dump(tasks_data, f, indent=2)


def print_report(data):
    """Print a human-readable report to stdout."""
    print(f"\n{'='*60}")
    print(f"  QI ECOSYSTEM HEALTH CHECK — {data['checked_at']}")
    print(f"{'='*60}\n")

    for name, p in data["projects"].items():
        health = p.get("health", "unknown")
        icon = {"ok": "✅", "warning": "⚠️", "attention": "🔴"}.get(health, "❓")

        print(f"{icon}  {name}  ({p['path']})")

        if not p.get("exists"):
            print("     ❌ Path not found on disk\n")
            continue

        svc = p.get("service", "n/a")
        svc_icon = "🟢" if svc == "running" else ("🔴" if svc == "stopped" else "⚪")
        print(f"     {svc_icon} Service: {svc}")

        if "tunnel" in p:
            t_icon = "🟢" if p["tunnel"] == "running" else "🔴"
            print(f"     {t_icon} Tunnel:  {p['tunnel']}")

        if "port_open" in p:
            p_icon = "🟢" if p["port_open"] else "🔴"
            print(f"     {p_icon} Port:    {'open' if p['port_open'] else 'closed'}")

        git = p.get("git", {})
        if "error" not in git:
            dirty = git.get("uncommitted_changes", 0)
            dirty_str = f"  ⚠️  {dirty} uncommitted" if dirty else "  clean"
            print(f"     📁 Git:    {git.get('branch','?')} | {git.get('last_commit','?')[:60]}{dirty_str}")

        docs = p.get("docs", "unknown")
        d_icon = "✅" if docs == "current" else ("⚠️" if "stale" in str(docs) else "❌")
        print(f"     {d_icon} Docs:    {docs}")

        summary = "✅ yes" if p.get("has_summary") else "❌ missing"
        print(f"     📄 Summary: {summary}")

        if p.get("issues"):
            print(f"     ⚠️  Issues: {', '.join(p['issues'])}")

        if p.get("note"):
            print(f"     ℹ️  Note: {p['note']}")

        print()

    print(f"{'='*60}\n")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    data = run_health_check()
    sync_tasks(data)        # auto-close resolved tasks, auto-open new ones
    print_report(data)

    # Optionally save to status.json
    if "--save" in sys.argv:
        if STATUS_FILE.exists():
            with open(STATUS_FILE, encoding="utf-8") as f:
                status = json.load(f)
        else:
            status = {}
        status["last_health_check"] = data
        status["_meta"]["last_updated"] = datetime.now().isoformat()
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(status, f, indent=2)
        print(f"Saved to {STATUS_FILE}")

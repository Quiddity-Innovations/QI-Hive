# -*- coding: utf-8 -*-
"""
QI Hive Dashboard — port 8600
AdminLTE v4 + Bootstrap 5 + SortableJS kanban
Powered by QI Brain (port 9011) as the hive's nervous system.
"""
import html
import json
import logging
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))
from health_check import run_health_check, sync_tasks
from qi_brain_client import (
    brain_online, get_agents, get_ecosystem_snapshot,
    get_recent_sessions, get_agent_profile, get_brain_status,
)

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="QI Hive", version="3.0.0")
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Tunnel write-protection (2026-06-12, decision OWNER-2026-06-12-TUNNEL) ──
# The public Cloudflare quick tunnel stays up (owner call), but mutating
# requests that arrive THROUGH the tunnel must carry the shared token.
# Tunnel traffic is identified by the Cf-Ray / CF-Connecting-IP headers that
# cloudflared injects; direct localhost/LAN requests have neither and pass
# untouched, so local workflow and hive agents are unaffected.
_WRITE_TOKEN_FILE = Path(r"C:\QIH\secrets\dashboard_write_token.txt")

def _write_token() -> str:
    try:
        return _WRITE_TOKEN_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        return ""

# Paths exempt from the tunnel write-token guard. Theme is a cosmetic,
# low-risk preference, so it's temporarily unlocked (2026-06-26) while the
# token flow for it is being reworked. Revisit and re-lock when ready.
_WRITE_GUARD_EXEMPT = {"/api/theme"}

@app.middleware("http")
async def tunnel_write_guard(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH", "DELETE") \
            and request.url.path not in _WRITE_GUARD_EXEMPT:
        via_tunnel = bool(request.headers.get("cf-ray") or request.headers.get("cf-connecting-ip"))
        if via_tunnel:
            tok = _write_token()
            supplied = request.headers.get("x-qi-token") or request.query_params.get("qi_token", "")
            if not tok or supplied != tok:
                return JSONResponse({"status": "error", "error": "write access via tunnel requires X-QI-Token"},
                                    status_code=403)
    return await call_next(request)

# ── No-store for dynamic HTML (2026-06-18) ──
# Dashboard pages render live every request. Without this, browsers cache the
# HTML per-origin, so a public-tunnel origin can show a stale launcher even
# after services/tunnels change while localhost looks fresh. Force revalidation
# on HTML only; /static assets keep their own caching.
@app.middleware("http")
async def no_store_html(request: Request, call_next):
    response = await call_next(request)
    ctype = response.headers.get("content-type", "")
    if ctype.startswith("text/html"):
        response.headers["Cache-Control"] = "no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

_PROJECT_DIR = Path(__file__).parent.parent.parent.parent  # C:\QIH
STATUS_FILE  = _PROJECT_DIR / "data" / "status.json"
TASKS_FILE   = _PROJECT_DIR / "data" / "tasks.json"
# Legacy per-agent config folder. This has not existed since the UNIVERSAL->QIH
# migration; load_agents() returns {} and is now only a fallback enricher for the
# Brain-backed agent table. The authoritative agent registry is qi_brain.db.
# (2026-08-17 audit — /api/agents was serving {} because of this dead path.)
AGENTS_DIR   = _PROJECT_DIR / "hive" / "Agents"
BRAIN_DB     = _PROJECT_DIR / "data" / "qi_brain.db"

def _brain_db_query(sql: str, params: tuple = ()) -> list[dict]:
    """Read-only query against qi_brain.db. Returns [] if DB missing or query fails."""
    import sqlite3
    if not BRAIN_DB.exists():
        return []
    try:
        conn = sqlite3.connect(f"file:{BRAIN_DB}?mode=ro", uri=True, timeout=2.0)
        conn.row_factory = sqlite3.Row
        try:
            return [dict(r) for r in conn.execute(sql, params)]
        finally:
            conn.close()
    except Exception:
        return []


def _brain_db_execute(sql: str, params: tuple = ()) -> int | None:
    """Read-WRITE statement against qi_brain.db. Returns lastrowid or None on failure.

    WAL mode + busy_timeout let this coexist with the Brain process writing the
    same DB. Used by the War Room chat so Renne can post without a Brain restart.
    """
    import sqlite3
    if not BRAIN_DB.exists():
        return None
    try:
        conn = sqlite3.connect(str(BRAIN_DB), timeout=5.0)
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA busy_timeout = 5000")
            cur = conn.execute(sql, params)
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()
    except Exception:
        return None


def _brain_db_agents_last_seen() -> list[dict]:
    """Read agent_heartbeats directly from Brain SQLite (avoids HTTP hop + Brain restart dependency).

    Returns one row per agent with the latest heartbeat.  Keys match what the
    Brain HTTP /api/agents/last_seen endpoint returns so render_mission_control
    needs no further changes.
    """
    return _brain_db_query(
        """
        SELECT h.agent_id, h.ts AS last_ts, h.project_id AS last_project,
               h.model AS last_model, h.event AS last_event
        FROM agent_heartbeats h
        INNER JOIN (
            SELECT agent_id, MAX(ts) AS max_ts
            FROM agent_heartbeats
            WHERE agent_id IN ('claude_code','claude','claude_work','cowork','claude_chat')
            GROUP BY agent_id
        ) m ON m.agent_id = h.agent_id AND m.max_ts = h.ts
        """
    )

# Wire up QI Logger
sys.path.insert(0, str(_PROJECT_DIR))
from engine.common.qi_logger import get_logger, set_level, list_services
from engine.common import usage_stats
log = get_logger("dashboard")

# ── Durable usage history ────────────────────────────────────────────────────
# usage_stats is stateless: it re-parses ~/.claude/projects/**/*.jsonl on every
# call, and Claude Code deletes those transcripts on a retention timer. That
# silently truncated every long-horizon figure (QTD/YTD lost months of history
# each time cleanup ran). usage_ledger is the persistent per-day store in
# qi_brain.db; prefer it for calendar-aligned windows and fall back to live
# parsing if it is empty or unavailable.
try:
    from engine.common import usage_ledger
    from engine.common import usage_dimensions
    from engine.common import usage_snapshot_task
except Exception as _e:                                    # pragma: no cover
    usage_ledger = usage_dimensions = usage_snapshot_task = None
    log.warning(f"usage_ledger unavailable, falling back to live parse: {_e}")


def merge_status_projects(projects: dict) -> dict:
    """Collapse duplicate project entries in status.json into one row each.

    status.json is written by two independent producers that key projects
    differently:

      * nightly_reconcile.regenerate_views keys by canonical registry id
        ("maia") and carries the editorial fields — display_name, phase,
        current_task, notes, ports.
      * an external supervisor keys by display name ("Maia") and carries
        health fields — git dirty state, severity, supervisor_findings, and
        often a fresher last_activity.

    Neither recognises the other's key, so 21 of 28 projects appeared twice on
    the dashboard — once with a Progress bar and once showing "—", because
    project_readiness.json is keyed canonically and never matched the
    display-name row.

    Merging here rather than rewriting status.json is deliberate: the
    supervisor owns its keys and would simply recreate them, and other
    consumers may still read them. This is presentation-layer reconciliation,
    so it cannot lose data.

    Identity is resolved on normalised `path` first — the strongest signal,
    since both rows point at the same directory — falling back to a
    normalised id. Path matching also catches pairs that id matching misses,
    e.g. universal/QI-Universal and personalsong/PersonalSong Studio.
    """
    import re as _re

    def _norm_path(v):
        return _re.sub(r"[\\/]+$", "", str(v or "")).replace("/", "\\").upper()

    def _norm_id(v):
        return _re.sub(r"[^a-z0-9]", "", str(v or "").lower())

    # Registry gives a canonical path for rows that carry an id but no path —
    # without it, "retirementanalyzer" (no path) and "Retirement Analyzer"
    # (path only) never meet.
    reg_path: dict[str, str] = {}
    try:
        _reg = json.loads(Path(r"C:\QIH\ecosystem\qi_registry.json").read_text(encoding="utf-8"))
        for _p in _reg.get("projects", []):
            if _p.get("id") and _p.get("path"):
                reg_path[_norm_id(_p["id"])] = _norm_path(_p["path"])
    except Exception as e:
        log.warning(f"merge_status_projects: registry unreadable: {e}")

    # A project can be identified by any of several signals, and different
    # producers supply different ones. Union rows that share ANY signal rather
    # than committing to a single key.
    parent: dict[str, str] = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    signals: dict[str, list[str]] = {}
    for key, entry in projects.items():
        if not isinstance(entry, dict):
            continue
        nid = _norm_id(entry.get("id") or key)
        sig = [f"k:{_norm_id(key)}", f"i:{nid}"]
        if entry.get("display_name"):
            sig.append(f"k:{_norm_id(entry['display_name'])}")
        path = _norm_path(entry.get("path")) or reg_path.get(nid, "")
        if path:
            sig.append(f"p:{path}")
        signals[key] = sig
        for s in sig[1:]:
            union(sig[0], s)

    groups: dict[str, list[tuple[str, dict]]] = {}
    for key, entry in projects.items():
        if key not in signals:
            continue
        groups.setdefault(find(signals[key][0]), []).append((key, entry))

    # Fields the supervisor owns; copied onto the canonical row when absent.
    HEALTH = ("git", "severity", "supervisor_findings")

    merged: dict[str, dict] = {}
    for members in groups.values():
        # The canonical row is the one carrying editorial fields.
        canonical = next(
            (m for m in members if m[1].get("display_name") or m[1].get("phase")),
            members[0])
        key, base = canonical[0], dict(canonical[1])
        for other_key, other in members:
            if other_key == key:
                continue
            for f in HEALTH:
                if f not in base and f in other:
                    base[f] = other[f]
            # last_activity: keep whichever producer saw activity most recently.
            a, b = str(base.get("last_activity") or ""), str(other.get("last_activity") or "")
            if b > a:
                base["last_activity"] = other["last_activity"]
            # Never let a merge drop a field nobody else supplied.
            for f, v in other.items():
                base.setdefault(f, v)
        # Record every key that folded into this row. Task records reference
        # projects by whichever label their creator used, so the Open count
        # has to match on any alias — without this it silently undercounts
        # (21 open tasks matched no row at all before this was added).
        base["_aliases"] = sorted({m[0] for m in members}
                                  | {str(m[1].get("id")) for m in members if m[1].get("id")}
                                  | {str(m[1].get("display_name")) for m in members
                                     if m[1].get("display_name")})
        merged[key] = base
    return merged


def _win(days: int):
    """Trailing-N-day window as (start, end) local dates, inclusive."""
    from datetime import date as _d, timedelta as _td
    end = _d.today()
    return end - _td(days=days - 1), end


def _ensure_usage_fresh():
    """Repair a stale ledger before any usage read.

    Every helper below prefers the ledger whenever it holds ANY row for the
    requested window. That makes a stale ledger far worse than an empty one:
    an empty window falls back to live parsing and is correct, while a
    partially-covered window silently truncates at the ledger's last day. That
    is exactly how YTD froze at $60,124 for the eight days after 2026-08-05 —
    and how 30d came to read LOWER than 7d, because only the 7d window was
    empty enough to trigger the fallback.

    Keeping the ledger current is the fix. The snapshot runs on a background
    thread (throttled to once per 5 min) so it never adds to this request's
    latency — see `usage_snapshot_task.ensure_fresh`. The scheduled task
    `QI_UsageSnapshot` is the primary guarantee; this is the safety net for
    when it has not run yet.
    """
    if usage_snapshot_task is None:
        return
    if usage_snapshot_task.ensure_fresh():
        log.info("usage ledger refresh started in background")


def _warn_if_truncating(start, end):
    """Log when the ledger cannot cover a window it is about to answer for.

    `_ensure_usage_fresh` should prevent this, so reaching here means the
    snapshot is failing. Without this line the symptom is invisible: the tile
    just quietly reports a smaller number.
    """
    if usage_ledger is None:
        return
    try:
        m = usage_ledger.max_day()
        if m is not None and m < end:
            log.warning(
                f"usage ledger only covers through {m} but window ends {end} — "
                f"figures for this window are truncated; check QI_UsageSnapshot")
    except Exception:
        pass


def usage_range(start, end):
    """Window metrics, preferring the ledger so reconstructed history is
    included. Falls back to live transcript parsing if the ledger is empty."""
    _ensure_usage_fresh()
    if usage_ledger is not None:
        try:
            r = usage_ledger.range_stats(start, end)
            if r.get("turns"):
                _warn_if_truncating(start, end)
                return r
        except Exception as e:
            log.warning(f"usage_ledger.range_stats failed: {e}")
    return usage_stats.range_stats(start, end)


def usage_totals(days: int):
    r = usage_range(*_win(days))
    r.setdefault("days", days)
    return r


def usage_daily(days: int):
    _ensure_usage_fresh()
    if usage_ledger is not None:
        try:
            rows = usage_ledger.daily_range(*_win(days))
            if any(x["cost_usd"] for x in rows):
                return rows
        except Exception as e:
            log.warning(f"usage_ledger.daily_range failed: {e}")
    return usage_stats.daily(days)


def usage_by_project(days: int):
    _ensure_usage_fresh()
    if usage_dimensions is not None:
        try:
            rows = usage_dimensions.by_project(*_win(days))
            if rows:
                return rows
        except Exception as e:
            log.warning(f"usage_dimensions.by_project failed: {e}")
    return usage_stats.by_project(days)


def usage_by_model(days: int):
    _ensure_usage_fresh()
    if usage_dimensions is not None:
        try:
            rows = usage_dimensions.by_model(*_win(days))
            if rows:
                return rows
        except Exception as e:
            log.warning(f"usage_dimensions.by_model failed: {e}")
    return usage_stats.by_model(days)


def usage_savings_by_project(days: int):
    _ensure_usage_fresh()
    if usage_dimensions is not None:
        try:
            rows = usage_dimensions.savings_by_project(*_win(days))
            if rows:
                return rows
        except Exception as e:
            log.warning(f"usage_dimensions.savings_by_project failed: {e}")
    return usage_stats.savings_by_project(days)


def usage_savings_by_model(days: int):
    _ensure_usage_fresh()
    if usage_dimensions is not None:
        try:
            rows = usage_dimensions.savings_by_model(*_win(days))
            if rows:
                return rows
        except Exception as e:
            log.warning(f"usage_dimensions.savings_by_model failed: {e}")
    return usage_stats.savings_by_model(days)


def usage_totals_since(start):
    """Calendar-window totals, preferring the durable ledger.

    Returns the usage_stats shape plus, when the ledger answered,
    `cost_by_source` / `measured_pct` so the UI can show how much of the
    figure is measured versus reconstructed.
    """
    _ensure_usage_fresh()
    if usage_ledger is not None:
        try:
            r = usage_ledger.totals_since(start)
            if r.get("turns"):
                from datetime import date as _d
                _warn_if_truncating(start, _d.today())
                return r
        except Exception as e:
            log.warning(f"usage_ledger.totals_since failed: {e}")
    return usage_stats.totals_since(start)

# ── Data helpers ─────────────────────────────────────────────────────────────

def load_json(path: Path) -> dict:
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(path: Path, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_status(): return load_json(STATUS_FILE)
def load_tasks():  return load_json(TASKS_FILE).get("tasks", [])
def save_tasks(tasks):
    data = load_json(TASKS_FILE)
    data["tasks"] = tasks
    save_json(TASKS_FILE, data)

def load_agents():
    agents = {}
    if AGENTS_DIR.exists():
        for folder in AGENTS_DIR.iterdir():
            cfg = folder / "config.json"
            if cfg.exists():
                agents[folder.name] = load_json(cfg)
    return agents

# ── AdminLTE base layout ──────────────────────────────────────────────────────

PAGE_READMES: dict[str, str] = {
    "dashboard": """
        <p>The <strong>Dashboard</strong> is the home screen of QI Hive. It gives you a live snapshot of the entire Quiddity Innovations ecosystem at a glance.</p>
        <ul class="mb-2">
          <li><strong>Project cards</strong> — one card per registered project, colour-coded by status (production, in development, backlog, retired). The card shows the current task and open task count.</li>
          <li><strong>Claude usage strip</strong> — today's token spend and 30-day rolling totals across all agents and models.</li>
          <li><strong>Hive agent team</strong> — the 7 active agents (Architect, Builder, Scout, Scribe, Ops, Inspector, Tester) and their current state.</li>
          <li><strong>Session log</strong> — the last few Claude Code sessions with model, duration, and project.</li>
          <li><strong>Task summary</strong> — counts per Kanban column across all projects.</li>
        </ul>
        <p class="mb-0 text-muted">Nothing on this page is interactive — it is read-only. Use the sidebar to navigate to the page where you can act on a specific area.</p>
    """,
    "hive": """
        <p><strong>The Hive</strong> is QI Brain's control panel — the intelligence layer that connects all QI projects.</p>
        <ul class="mb-2">
          <li><strong>Brain status</strong> — shows whether QI Brain (port 9011) is online. If offline, agents fall back gracefully but session logging and cross-project memory are suspended.</li>
          <li><strong>Stats row</strong> — active projects, logged decisions, tracked features, and sessions recorded in the Brain database.</li>
          <li><strong>Agent cards</strong> — profiles for each of the 7 Hive agents. Each agent has a speciality (architecture, building, testing, etc.), a growth log, and a list of known patterns. Click an agent card to see its full profile.</li>
          <li><strong>Ecosystem snapshot</strong> — a live read from QI Brain of the current state of every registered project.</li>
          <li><strong>Growth log</strong> — patterns and insights the agents have accumulated over time.</li>
        </ul>
        <p class="mb-0 text-muted">The Hive is the "nervous system" of QI. It does not run code — it holds memory and coordinates agents. Claude Code and Claude Work both read from and write to it.</p>
    """,
    "health": """
        <p><strong>Health Check</strong> pings every registered QI project and surfaces anything that needs attention.</p>
        <ul class="mb-2">
          <li><strong>Per-project rows</strong> — checks that the project folder exists on disk, the git repo is clean (or notes uncommitted changes), required docs are present, INTRO status files are populated, and any NSSM services are running.</li>
          <li><strong>Health badges</strong> — <span class="badge text-bg-success">ok</span> everything is fine · <span class="badge text-bg-warning">warning</span> something is missing but not broken · <span class="badge text-bg-danger">attention</span> something is broken or missing that will affect operation.</li>
          <li><strong>Action items list</strong> — a consolidated punch-list at the top of items that need fixing, in priority order.</li>
        </ul>
        <p class="mb-0 text-muted">Run this before starting a session on any project to catch stale state, stopped services, or missing files before they cause confusion mid-session.</p>
    """,
    "board": """
        <p>The <strong>Task Board</strong> is a cross-project Kanban board. All open work across every QI project lives here in one view.</p>
        <ul class="mb-2">
          <li><strong>Columns</strong> — Backlog (queued, not started) · In Progress (actively being worked) · Review (done, awaiting check) · Done (complete).</li>
          <li><strong>Drag and drop</strong> — drag any card between columns to update its status. Changes persist immediately.</li>
          <li><strong>Priority colours</strong> — red left-border = high · yellow = medium · green = low.</li>
          <li><strong>Agent badges</strong> — each card shows which Hive agent owns the task (Architect, Builder, Scout, etc.).</li>
          <li><strong>Project filter</strong> — use the dropdown at the top right to show only one project's tasks.</li>
          <li><strong>Add task</strong> — use the + button at the top of any column to add a new task directly to that column.</li>
        </ul>
        <p class="mb-0 text-muted">This board is the single source of truth for work in flight. CoWork Dispatch items that get approved are automatically promoted to tasks here.</p>
    """,
    "tests": """
        <p>The <strong>Tests</strong> page has two sections: the QI Hive automated test runner, and the EasyFlow Chrome extension launcher.</p>
        <p><strong>QI Hive test runner:</strong></p>
        <ul class="mb-2">
          <li><strong>Smoke tests</strong> — fast health checks: are all services up, do the key API routes respond, is the Brain reachable?</li>
          <li><strong>API tests</strong> — tests every <code>/api/*</code> endpoint for correct response shape and status codes.</li>
          <li><strong>UI tests</strong> — checks that all dashboard pages render without errors.</li>
          <li><strong>Run All</strong> — runs all suites in sequence. Results appear in the table below (passed/failed/skipped per test).</li>
        </ul>
        <p><strong>EasyFlow Chrome extension launcher:</strong></p>
        <ul class="mb-0">
          <li>Paste the current unpacked extension ID (from <code>chrome://extensions</code>) into the field and save it — it persists across sessions.</li>
          <li><strong>Open Test Runner</strong> — opens the automated test page inside the extension in a new Chrome tab.</li>
          <li><strong>Open Options Page</strong> — opens the EasyFlow settings page in a new tab.</li>
          <li>The two manual test scripts (<code>v12_feature_test.js</code>, <code>regression_test.js</code>) are listed with one-click copy paths for use in DevTools.</li>
        </ul>
    """,
    "projects": """
        <p><strong>Project Status</strong> gives you a deep-dive view of any individual QI project — everything in one place without opening files manually.</p>
        <ul class="mb-2">
          <li><strong>Project selector</strong> — choose any registered project from the dropdown. Each project has its own set of status tabs.</li>
          <li><strong>Intro tab</strong> — what the project is, who it is for, and its current phase.</li>
          <li><strong>Documentation tab</strong> — links to all key documents (implementation log, meeting minutes, version history, architecture diagrams).</li>
          <li><strong>Business features tab</strong> — user-facing features by status (live, in development, planned).</li>
          <li><strong>Dev features tab</strong> — technical features and API endpoints, with file and line references.</li>
          <li><strong>Tech stack tab</strong> — languages, frameworks, databases, services, and external APIs in use.</li>
          <li><strong>Future tab</strong> — planned enhancements and ideas not yet started.</li>
        </ul>
        <p class="mb-0 text-muted">All content is read from each project's <code>INTRO/</code> folder. To update a project's status page, edit the JSON/MD files there — or ask Claude Code to update them after a session.</p>
    """,
    "services": """
        <p><strong>Services</strong> shows the live state of every Windows NSSM service in the QI ecosystem.</p>
        <ul class="mb-2">
          <li>All QI services follow the naming convention <code>QI_&lt;Project&gt;&lt;Role&gt;</code> (e.g. <code>QI_MaiaBot</code>, <code>QI_BrainAPI</code>).</li>
          <li><span class="badge bg-success">RUNNING</span> — service is active and healthy. <span class="badge bg-danger">STOPPED</span> — service is down; dependent features will not work.</li>
          <li>The <strong>App Directory</strong> column shows which project folder the service runs from — useful for confirming a service is pointing at the right path after a migration.</li>
          <li>Start/stop/restart controls route through the <strong>QI Elevation Broker</strong> (<code>QI_Elevate</code>) — no UAC prompt required.</li>
        </ul>
        <p class="mb-0 text-muted">Rule: never manually kill a port without checking this table first. Stopping <code>QI_MaiaBot</code> cuts off all LINE/Telegram/Messenger users immediately. Stopping <code>QI_NayaBot</code> also stops the FileHQ engine.</p>
    """,
    "tasks": """
        <p><strong>Scheduled Tasks</strong> lists every Windows Task Scheduler job that supports the QI ecosystem — nightly syncs, health polls, token usage snapshots, and automation scripts.</p>
        <ul class="mb-2">
          <li><strong>State</strong> — Ready (will run at next trigger), Running, Disabled.</li>
          <li><strong>Every</strong> — the interval or schedule (daily, every N minutes, on logon, etc.).</li>
          <li><strong>Last run / Result</strong> — when it last fired and whether it succeeded. <span class="badge bg-success">OK</span> = exit code 0. <span class="badge bg-danger">ABORTED</span> = killed mid-run, usually by ExecutionTimeLimit — the task needs a longer timeout or the script is hanging.</li>
          <li><strong>Next run</strong> — when it will fire next. If this is far in the future or blank, the task may be disabled.</li>
          <li>The <i class="bi bi-eye-slash text-success"></i> icon means the task runs hidden (no console popup). <i class="bi bi-eye text-warning"></i> means it will flash a window briefly.</li>
        </ul>
        <p class="mb-0 text-muted">Approximately one-third of planned tasks are active. The rest are designed but not yet created. Use this page to confirm that nightly jobs actually ran before assuming the data they produce is fresh.</p>
    """,
    "usage": """
        <p><strong>LLM Usage</strong> tracks token consumption and estimated cost across every Claude session logged by QI Brain.</p>
        <ul class="mb-2">
          <li><strong>Today / 7d / 30d cards</strong> — total tokens (input + output + cache) and cost for each window.</li>
          <li><strong>Daily chart</strong> — three bars per day: Actual cost · Cost with local models substituted · Cost with both local and batch optimisations. Hover for exact figures.</li>
          <li><strong>By project / By model</strong> — break down spend to see which projects and which models are consuming the most budget.</li>
          <li><strong>Savings calculator</strong> — shows how much you could save by routing more work through local models (Ollama) or using the Anthropic Batch API for non-interactive tasks.</li>
        </ul>
        <p class="mb-0 text-muted">Data is logged automatically by Claude Code session hooks. If a session shows no usage data, check that the <code>QI_BrainAPI</code> service was running during that session — usage is only recorded when Brain is online.</p>
    """,
    "activity": """
        <p><strong>Activity</strong> shows two live event feeds — one from each Claude runtime.</p>
        <ul class="mb-2">
          <li><strong>Hive event log</strong> — events fired by Claude Code session hooks across all projects: <span class="badge text-bg-info">session_start</span> <span class="badge text-bg-success">session_end</span> <span class="badge text-bg-primary">task_done</span> <span class="badge text-bg-danger">error</span>. Each entry shows the project, a summary of what happened, and the user/host it ran on.</li>
          <li><strong>Claude Code session log</strong> — one row per Claude Code session from the last 7 days. Shows project, model used, session duration, and token cost. Colour-coded by model family (Opus / Sonnet / Haiku).</li>
        </ul>
        <p class="mb-0 text-muted">This is an audit trail, not a control surface — nothing here is clickable. Use it to answer "what happened in the last session?", "which model did I use yesterday?", or "why did costs spike on Tuesday?"</p>
    """,
    "dispatch": """
        <p><strong>CoWork Dispatch</strong> is the decision gate between Claude Work (CoWork) and execution. Nothing CoWork proposes moves to Claude Code without passing through here.</p>
        <ul class="mb-2">
          <li><strong>Pending</strong> — new proposals, briefings, or task requests from CoWork waiting for a decision.</li>
          <li><strong>Discussing</strong> — items where a conversation thread is open. CoWork, Claude Code, and you can all leave notes before a decision is made.</li>
          <li><strong>Resolved</strong> — approved (queued for Claude Code), declined (logged with reason), or already executed.</li>
        </ul>
        <p><strong>Actions on each card:</strong></p>
        <ul class="mb-2">
          <li><span class="badge text-bg-success">Approve</span> — logs the decision to QI Brain and queues it for Claude Code execution.</li>
          <li><span class="badge text-bg-danger">Decline</span> — logs it with a reason. CoWork sees this in its next session context.</li>
          <li><span class="badge text-bg-warning text-dark">Discuss</span> — opens a threaded note on the card. Use this when you need more information before deciding.</li>
        </ul>
        <p class="mb-0 text-muted">CoWork writes dispatch files to <code>C:\QIH\cowork-dispatch\</code> and session reports to <code>C:\QIH\shared\reports\inbox\</code>. Both are watched automatically — you do not need to import anything manually.</p>
    """,
    "logs": """
        <p><strong>Logs</strong> aggregates log output from all QI services and lets you tail, filter, and read them without opening files manually.</p>
        <ul class="mb-2">
          <li><strong>File selector</strong> — choose any <code>.log</code> file from across the QI ecosystem. Files are sorted by most recently modified.</li>
          <li><strong>Line count</strong> — show the last 100 / 200 / 500 / 1000 lines.</li>
          <li><strong>Filter</strong> — type any substring to filter lines in real time (client-side, no reload needed).</li>
          <li><strong>Auto-refresh</strong> — when the toggle is on, the selected log reloads every 3 seconds so you can watch a service live.</li>
        </ul>
        <p><strong>Log Level Configuration</strong> (section below):</p>
        <ul class="mb-0">
          <li>Adjust verbosity per service — DEBUG shows everything, ERROR shows only failures. Changes to the Dashboard service apply immediately; other services pick up the change on next restart.</li>
          <li>Settings persist to <code>config/logging.json</code>.</li>
        </ul>
    """,
    "config": """
        <p><strong>Config</strong> manages <code>gsudo</code> — the elevation tool that lets Claude Code run admin commands (NSSM service restarts, etc.) without a UAC prompt every time.</p>
        <p><strong>Quick Presets</strong> — one click to apply a named security profile globally:</p>
        <ul class="mb-2">
          <li><span class="badge text-bg-success">Loose</span> — auto-cache, never expires. For trusted daily-use projects.</li>
          <li><span class="badge text-bg-primary">Normal</span> — auto-cache, 8-minute idle timeout. Standard development.</li>
          <li><span class="badge text-bg-warning text-dark">Strict</span> — manual cache start only, 2-minute timeout, UAC isolation on. For sensitive work.</li>
          <li><span class="badge text-bg-danger">Locked</span> — no cache, always prompts. Maximum security for one-off operations.</li>
        </ul>
        <p><strong>Manual controls</strong> — fine-tune Cache Mode, Cache Duration, Log Level, UAC Isolation, and New Window behaviour individually.</p>
        <p><strong>Per-Project Profiles</strong> — save a named gsudo profile per project. Hit Apply on any row to instantly switch the machine-wide gsudo config to that project's security level. The active profile is highlighted.</p>
        <p class="mb-0 text-muted">All changes route through the QI Elevation Broker (<code>QI_Elevate</code>) — no UAC prompt. The broker runs as SYSTEM and only allows whitelisted gsudo commands.</p>
    """,
    "guide": """
        <p>The <strong>Guide</strong> is the built-in reference library for the QI ecosystem — cheatsheets, architecture notes, and quick-reference cards in one place.</p>
        <ul class="mb-2">
          <li>Content is loaded from <code>C:\\QIH\\ecosystem\\QI_Claude_Manager_Guide.md</code> and rendered as formatted HTML.</li>
          <li>Use <code>Ctrl+F</code> to search within the page — the guide is fully text-searchable.</li>
          <li><strong>NEW — Documentation Brain:</strong> 900+ docs across the ecosystem are now indexed and semantically searchable via the <code>qi_docs</code> collection, with a typed knowledge graph and the <code>hive-librarian</code> agent. See PART 12 of the Guide.</li>
        </ul>
        <p class="mb-0 text-muted">Planned additions: QI Standards reference, port registry table, NSSM command cheatsheet, LLM chain topology diagram, and a new-project quickstart walkthrough. These will be migrated here once the higher-priority dashboard rebuild is complete.</p>
    """,
}


def _readme_block(page_id: str) -> str:
    content = PAGE_READMES.get(page_id, "")
    if not content:
        return ""
    return f"""<div class="mb-4">
      <a class="small text-muted text-decoration-none d-inline-flex align-items-center gap-1"
         data-bs-toggle="collapse" href="#{page_id}-readme" role="button" aria-expanded="false">
        <i class="bi bi-info-circle me-1"></i>
        About this page
        <i class="bi bi-chevron-down" id="{page_id}-readme-chevron"
           style="font-size:.7rem;transition:transform .2s;"></i>
      </a>
      <div class="collapse mt-2" id="{page_id}-readme">
        <div class="card card-body small py-3"
             style="background:var(--bs-tertiary-bg);border:1px solid var(--bs-border-color);">
          {content}
        </div>
      </div>
    </div>
    <script>
    (function(){{
      var el   = document.getElementById('{page_id}-readme');
      var chev = document.getElementById('{page_id}-readme-chevron');
      if (el && chev) {{
        el.addEventListener('show.bs.collapse', function(){{ chev.style.transform='rotate(180deg)'; }});
        el.addEventListener('hide.bs.collapse', function(){{ chev.style.transform='rotate(0deg)';   }});
      }}
    }})();
    </script>"""


VALID_THEMES = {"penumbra", "light", "auto", "orange", "dark", "museum", "manuscript"}

# QI theme -> Bootstrap base ('auto' has no entry — resolved client-side from
# the OS). 'penumbra' is the original QI dark look (renamed 2026-08-06);
# 'orange' and 'dark' are ports of the two major NEXUS themes and share the
# NEXUS orange accent (#f97316) on a light / dark base respectively.
_THEME_BASE   = {"penumbra": "dark", "light": "light", "orange": "light", "dark": "dark",
                 "museum": "dark", "manuscript": "light"}
_THEME_ACCENT = {"orange": "orange", "dark": "orange"}
QI_ACCENT_ORANGE = "#f97316"

# Museum / Manuscript are a *skin*, not an accent: they restate the whole
# surface-and-ink palette rather than recolouring one hue. They ride their own
# attribute so they never contend with the NEXUS orange accent above.
_THEME_SKIN = {"museum": "museum", "manuscript": "manuscript"}
# Loaded only when a skin is active — the other five themes pay nothing, and
# the fallback stack below is a real serif on every Windows box, so an offline
# dashboard degrades to Palatino rather than to Arial.
QI_SKIN_FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    'family=Cormorant+Garamond:wght@500;600;700&family=Inter:wght@400;500;600&display=swap">'
)

QI_ACCENT_CSS = """
    /* ── QI accent themes (Orange / Dark — ported from NEXUS, 2026-08-06) ── */
    html[data-qi-accent="orange"] {
      --bs-primary:#f97316; --bs-primary-rgb:249,115,22;
      --bs-link-color:#ea580c; --bs-link-hover-color:#c2410c;
      --bs-link-color-rgb:234,88,12; --bs-link-hover-color-rgb:194,65,12;
      --bs-focus-ring-color:rgba(249,115,22,.25);
    }
    html[data-qi-accent="orange"][data-bs-theme="dark"] {
      --bs-link-color:#fb923c; --bs-link-hover-color:#f97316;
      --bs-link-color-rgb:251,146,60; --bs-link-hover-color-rgb:249,115,22;
    }
    html[data-qi-accent="orange"] .btn-primary {
      --bs-btn-bg:#f97316; --bs-btn-border-color:#f97316;
      --bs-btn-hover-bg:#ea580c; --bs-btn-hover-border-color:#ea580c;
      --bs-btn-active-bg:#c2410c; --bs-btn-active-border-color:#c2410c;
      --bs-btn-disabled-bg:#fdba74; --bs-btn-disabled-border-color:#fdba74;
    }
    html[data-qi-accent="orange"] .btn-outline-primary {
      --bs-btn-color:#ea580c; --bs-btn-border-color:#f97316;
      --bs-btn-hover-bg:#f97316; --bs-btn-hover-border-color:#f97316;
      --bs-btn-active-bg:#ea580c; --bs-btn-active-border-color:#ea580c;
    }
    html[data-qi-accent="orange"] .text-primary   { color:#f97316 !important; }
    html[data-qi-accent="orange"] .bg-primary     { background-color:#f97316 !important; }
    html[data-qi-accent="orange"] .border-primary { border-color:#f97316 !important; }
    html[data-qi-accent="orange"] .app-sidebar .nav-link.active {
      background-color:#f97316 !important; color:#fff !important;
    }
    html[data-qi-accent="orange"] .app-sidebar .nav-link.active .nav-icon { color:#fff !important; }
    html[data-qi-accent="orange"] .nav-pills .nav-link.active { background-color:#f97316; color:#fff; }
    html[data-qi-accent="orange"] .nav-tabs .nav-link.active  { color:#ea580c; }
    html[data-qi-accent="orange"] .form-check-input:checked {
      background-color:#f97316; border-color:#f97316;
    }
    html[data-qi-accent="orange"] input[type="checkbox"],
    html[data-qi-accent="orange"] input[type="radio"],
    html[data-qi-accent="orange"] input[type="range"] { accent-color:#f97316; }
    html[data-qi-accent="orange"] .page-link { color:#ea580c; }
    html[data-qi-accent="orange"] .dropdown-item.active { background-color:#f97316; }
    html[data-qi-accent="orange"] .progress-bar { background-color:#f97316; }
"""


QI_SKIN_CSS = """
    /* ══ QI skins: Museum (dark) / Manuscript (light) ══════════════════════
       Added 2026-08-22, retuned the same day against the measured values in
       C:\\APPS\\Mythologies\\site\\css\\style.css rather than an approximation
       of them. The five older themes are Bootstrap's stock greys with one hue
       swapped; these two restate the whole palette — warm ink on a deep indigo
       or a parchment ground, gold hairlines instead of grey borders, a serif
       for display type, and pill geometry throughout.

       Everything is expressed as Bootstrap and AdminLTE custom properties, so
       components inherit it without per-component overrides. */

    html[data-qi-skin] {
      --qi-serif: "Cormorant Garamond", "Palatino Linotype", Palatino, Georgia, serif;
      --qi-sans: "Inter", "Segoe UI", system-ui, -apple-system, sans-serif;
      /* .hero is 22px and .pantheon-card 18px; the dashboard is denser than the
         hub, so it takes the card value as its ceiling. */
      --qi-radius: 18px;
      --qi-radius-sm: 10px;
      --qi-pill: 999px;
    }

    /* ── Museum — dark ── */
    html[data-qi-skin="museum"] {
      --qi-bg: #0e1019;
      --qi-canvas: radial-gradient(1400px 800px at 50% -12%, #1a1e30 0%, #12141f 45%, #0b0d15 100%);
      --qi-raised: #171a28;
      --qi-raised-2: #1d2133;
      --qi-overlay: rgba(14, 16, 25, 0.82);
      --qi-ink: #eae4d6;
      --qi-ink-strong: #f6f1e5;
      --qi-ink-muted: #b1a993;
      --qi-gold: #d4af6a;
      --qi-gold-strong: #e8c987;
      --qi-gold-line: rgba(212, 175, 106, 0.34);
      --qi-hairline: rgba(212, 175, 106, 0.16);
      --qi-hairline-strong: rgba(212, 175, 106, 0.32);
      --qi-tint: rgba(212, 175, 106, 0.07);
      --qi-chip-bg: rgba(212, 175, 106, 0.10);
      --qi-chip-ink: #dcc99a;
      --qi-ink-on-gold: #17130a;
      --qi-shadow-soft: 0 6px 24px rgba(0, 0, 0, 0.40);
      --qi-shadow: 0 18px 50px rgba(0, 0, 0, 0.55);

      --bs-body-bg: #0e1019;         --bs-body-bg-rgb: 14,16,25;
      --bs-body-color: #eae4d6;      --bs-body-color-rgb: 234,228,214;
      --bs-emphasis-color: #f6f1e5;
      --bs-secondary-bg: #171a28;    --bs-secondary-bg-rgb: 23,26,40;
      --bs-tertiary-bg: #1d2133;     --bs-tertiary-bg-rgb: 29,33,51;
      --bs-secondary-color: rgba(234,228,214,0.66);
      --bs-tertiary-color: rgba(234,228,214,0.46);
      --bs-border-color: rgba(212,175,106,0.16);
      --bs-border-color-translucent: rgba(212,175,106,0.14);
      --bs-heading-color: #f6f1e5;
      --bs-primary: #d4af6a;         --bs-primary-rgb: 212,175,106;
      --bs-link-color: #dcc99a;      --bs-link-color-rgb: 220,201,154;
      --bs-link-hover-color: #e8c987; --bs-link-hover-color-rgb: 232,201,135;
      --bs-focus-ring-color: rgba(212,175,106,0.28);
      --bs-code-color: #dcc99a;
      color-scheme: dark;
    }

    /* ── Manuscript — light ── */
    html[data-qi-skin="manuscript"] {
      --qi-bg: #f2ead9;
      --qi-canvas: radial-gradient(1300px 750px at 50% -12%, #faf5e8 0%, #f2ead9 55%, #e9dfc8 100%);
      --qi-raised: #faf5e9;
      --qi-raised-2: #f2eadb;
      --qi-overlay: rgba(250, 245, 233, 0.88);
      --qi-ink: #35301f;
      --qi-ink-strong: #221c10;
      --qi-ink-muted: #6d6350;
      --qi-gold: #9a7a2e;
      --qi-gold-strong: #7c5f1d;
      --qi-gold-line: rgba(154, 122, 46, 0.5);
      --qi-hairline: rgba(154, 122, 46, 0.24);
      --qi-hairline-strong: rgba(154, 122, 46, 0.45);
      --qi-tint: rgba(154, 122, 46, 0.07);
      --qi-chip-bg: rgba(154, 122, 46, 0.10);
      --qi-chip-ink: #6d5313;
      /* The reference sets .cta-primary ink to #17130a unconditionally — dark
         on gold in BOTH themes. Cream on the mid-gold #9a7a2e is only 3.8:1;
         the dark ink is 4.6:1 and passes AA for body text. */
      --qi-ink-on-gold: #17130a;
      --qi-shadow-soft: 0 5px 18px rgba(96, 78, 42, 0.16);
      --qi-shadow: 0 16px 40px rgba(96, 78, 42, 0.22);

      --bs-body-bg: #f2ead9;         --bs-body-bg-rgb: 242,234,217;
      --bs-body-color: #35301f;      --bs-body-color-rgb: 53,48,31;
      --bs-emphasis-color: #221c10;
      --bs-secondary-bg: #faf5e9;    --bs-secondary-bg-rgb: 250,245,233;
      --bs-tertiary-bg: #f2eadb;     --bs-tertiary-bg-rgb: 242,234,219;
      --bs-secondary-color: rgba(53,48,31,0.68);
      --bs-tertiary-color: rgba(53,48,31,0.48);
      --bs-border-color: rgba(154,122,46,0.24);
      --bs-border-color-translucent: rgba(154,122,46,0.2);
      --bs-heading-color: #221c10;
      --bs-primary: #9a7a2e;         --bs-primary-rgb: 154,122,46;
      --bs-link-color: #7c5f1d;      --bs-link-color-rgb: 124,95,29;
      --bs-link-hover-color: #5c4614; --bs-link-hover-color-rgb: 92,70,20;
      --bs-focus-ring-color: rgba(154,122,46,0.28);
      --bs-code-color: #7c5f1d;
      color-scheme: light;
    }

    /* ── Ground ── */
    html[data-qi-skin] body {
      font-family: var(--qi-sans);
      font-size: 15px;
      line-height: 1.55;
      background-color: var(--qi-bg) !important;
      background-image: var(--qi-canvas);
      background-attachment: fixed;
      color: var(--qi-ink);
    }
    /* AdminLTE paints these panels itself; hand them back to the skin. */
    html[data-qi-skin] .app-main,
    html[data-qi-skin] .app-content,
    html[data-qi-skin] .app-content-header,
    html[data-qi-skin] .app-wrapper { background: transparent !important; }

    /* ── Display type ── */
    html[data-qi-skin] h1, html[data-qi-skin] h2, html[data-qi-skin] h3,
    html[data-qi-skin] h4, html[data-qi-skin] h5, html[data-qi-skin] h6 {
      font-family: var(--qi-serif);
      font-weight: 600;
      letter-spacing: 0.01em;
      line-height: 1.14;
      color: var(--qi-ink-strong);
    }
    html[data-qi-skin] h1 { font-size: 2.3rem; }
    html[data-qi-skin] h2 { font-size: 1.85rem; }
    html[data-qi-skin] h3 { font-size: 1.5rem; }
    /* The page-title strip is the dashboard's nearest thing to a hero. */
    html[data-qi-skin] .app-content-header h3 { font-size: 1.72rem; }

    /* ── Panels ──
       .pantheon-card: 18px radius, hairline border, soft shadow. The first pass
       zeroed the shadow; the reference keeps it, and without it the panels sit
       flat on the ground instead of above it. */
    html[data-qi-skin] .card {
      background-color: var(--qi-raised);
      border: 1px solid var(--qi-hairline);
      border-radius: var(--qi-radius);
      box-shadow: var(--qi-shadow-soft);
    }
    /* .coll-group-h — the shelf header: serif, uppercase, gold, hairline rule. */
    html[data-qi-skin] .card-header {
      background: transparent;
      border-bottom: 1px solid var(--qi-gold-line);
      font-family: var(--qi-serif);
      color: var(--qi-gold-strong);
      font-size: 1rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      padding-top: 0.8rem;
      padding-bottom: 0.7rem;
    }
    html[data-qi-skin] .card-header .card-title {
      font-family: var(--qi-serif);
      font-size: 1rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--qi-gold-strong);
    }
    html[data-qi-skin] .card-body > .card-title { font-family: var(--qi-serif); text-transform: none; letter-spacing: 0.01em; }
    html[data-qi-skin] .card-footer { background: transparent; border-top: 1px solid var(--qi-hairline); }

    /* ── Chrome ── */
    html[data-qi-skin] .app-sidebar {
      background-color: var(--qi-raised) !important;
      border-right: 1px solid var(--qi-hairline);
      box-shadow: none !important;
      --lte-sidebar-color: var(--bs-secondary-color);
      --lte-sidebar-hover-color: var(--qi-ink-strong);
      --lte-sidebar-hover-bg: var(--qi-tint);
      --lte-sidebar-active-color: var(--qi-gold-strong);
      --lte-sidebar-menu-active-bg: var(--qi-tint);
      --lte-sidebar-menu-active-color: var(--qi-gold-strong);
      --lte-sidebar-header-color: var(--qi-ink-muted);
      --lte-sidebar-submenu-color: var(--bs-secondary-color);
      --lte-sidebar-submenu-hover-color: var(--qi-ink-strong);
      --lte-sidebar-submenu-hover-bg: var(--qi-tint);
      --lte-sidebar-submenu-active-color: var(--qi-gold-strong);
      --lte-sidebar-submenu-active-bg: var(--qi-tint);
    }
    /* Gold is a hairline hue, not a fill — a solid gold nav block is garish and
       drops the label contrast. The active item gets a rule and warm ink. */
    html[data-qi-skin] .app-sidebar .nav-link.active {
      background: var(--qi-tint) !important;
      color: var(--qi-gold-strong) !important;
      box-shadow: inset 2px 0 0 var(--qi-gold);
    }
    html[data-qi-skin] .app-sidebar .nav-link.active .nav-icon { color: var(--qi-gold) !important; }
    html[data-qi-skin] .sidebar-brand {
      border-bottom: 1px solid var(--qi-gold-line);
      background: transparent;
    }
    /* .brand-title / .brand-sub */
    html[data-qi-skin] .brand-text {
      font-family: var(--qi-serif);
      font-size: 1.28rem;
      font-weight: 600;
      letter-spacing: 0.04em;
      color: var(--qi-ink-strong);
    }
    html[data-qi-skin] .brand-image,
    html[data-qi-skin] .sidebar-brand .nav-icon { color: var(--qi-gold); }

    /* .topbar — translucent with a blur, not an opaque bar. */
    html[data-qi-skin] .app-header {
      background-color: var(--qi-overlay) !important;
      backdrop-filter: blur(10px);
      border-bottom: 1px solid var(--qi-hairline);
      box-shadow: none;
    }
    html[data-qi-skin] .app-footer {
      background: transparent;
      border-top: 1px solid var(--qi-hairline);
      color: var(--qi-ink-muted);
    }
    html[data-qi-skin] body.lock-header .app-content-header {
      background: var(--qi-bg);
      box-shadow: 0 1px 0 var(--qi-hairline);
    }

    /* ── Tables ── */
    html[data-qi-skin] .table {
      --bs-table-bg: transparent;
      --bs-table-color: var(--qi-ink);
      --bs-table-border-color: var(--qi-hairline);
      --bs-table-hover-bg: var(--qi-tint);
      --bs-table-hover-color: var(--qi-ink-strong);
      --bs-table-active-bg: var(--qi-tint);
      --bs-table-active-color: var(--qi-ink-strong);
    }
    /* .browse-h — the wide-tracked section label. */
    html[data-qi-skin] .table > thead th {
      font-size: 0.72rem;
      font-weight: 600;
      letter-spacing: 0.22em;
      text-transform: uppercase;
      color: var(--qi-gold);
      border-bottom-color: var(--qi-gold-line);
    }

    /* ── Controls — pill geometry throughout (.solid-btn / .ghost-btn / .tab) ── */
    html[data-qi-skin] .btn { border-radius: var(--qi-pill); }
    html[data-qi-skin] .btn-primary {
      --bs-btn-bg: var(--qi-gold);        --bs-btn-border-color: var(--qi-gold);
      --bs-btn-color: var(--qi-ink-on-gold);
      --bs-btn-hover-bg: var(--qi-gold-strong);
      --bs-btn-hover-border-color: var(--qi-gold-strong);
      --bs-btn-hover-color: var(--qi-ink-on-gold);
      --bs-btn-active-bg: var(--qi-gold-strong);
      --bs-btn-active-border-color: var(--qi-gold-strong);
      --bs-btn-active-color: var(--qi-ink-on-gold);
      --bs-btn-disabled-bg: var(--qi-gold); --bs-btn-disabled-border-color: var(--qi-gold);
      --bs-btn-disabled-color: var(--qi-ink-on-gold);
      font-weight: 600;
    }
    /* .ghost-btn rests in MUTED ink and only warms to gold on hover — gold at
       rest on every secondary button is what made the first pass look busy. */
    html[data-qi-skin] .btn-outline-primary,
    html[data-qi-skin] .btn-outline-secondary {
      --bs-btn-color: var(--qi-ink-muted);
      --bs-btn-bg: var(--qi-raised-2);
      --bs-btn-border-color: var(--qi-hairline);
      --bs-btn-hover-bg: var(--qi-raised-2);
      --bs-btn-hover-border-color: var(--qi-gold-line);
      --bs-btn-hover-color: var(--qi-gold-strong);
      --bs-btn-active-bg: var(--qi-tint);
      --bs-btn-active-border-color: var(--qi-gold);
      --bs-btn-active-color: var(--qi-gold-strong);
    }
    html[data-qi-skin] .btn-group > .btn:not(:first-child) { border-top-left-radius: var(--qi-pill); border-bottom-left-radius: var(--qi-pill); }
    html[data-qi-skin] .btn-group > .btn:not(:last-child)  { border-top-right-radius: var(--qi-pill); border-bottom-right-radius: var(--qi-pill); }
    html[data-qi-skin] .btn-group { gap: 4px; }

    html[data-qi-skin] .text-primary   { color: var(--qi-gold) !important; }
    html[data-qi-skin] .bg-primary     { background-color: var(--qi-gold) !important; color: var(--qi-ink-on-gold) !important; }
    html[data-qi-skin] .border-primary { border-color: var(--qi-gold) !important; }
    /* Bootstrap hardcodes white ink on .text-bg-primary because its stock
       primary is a mid blue. Gold is a LIGHT hue, so white on it lands at
       1.4:1 — illegible. Both skins therefore restate the ink, not just the
       ground. Same trap for the skip-link, which is gold-on-gold otherwise. */
    html[data-qi-skin] .text-bg-primary,
    html[data-qi-skin] .badge.bg-primary,
    html[data-qi-skin] .skip-link {
      background-color: var(--qi-gold) !important;
      color: var(--qi-ink-on-gold) !important;
    }
    html[data-qi-skin] .text-bg-primary a,
    html[data-qi-skin] .badge.bg-primary a { color: var(--qi-ink-on-gold) !important; }

    /* .chip — pill, tinted, gold-hairlined, letterspaced. */
    html[data-qi-skin] .badge {
      border-radius: var(--qi-pill);
      font-weight: 600;
      letter-spacing: 0.07em;
      padding: 0.32em 0.72em;
    }
    html[data-qi-skin] .badge.text-bg-secondary,
    html[data-qi-skin] .badge.bg-secondary {
      background-color: var(--qi-chip-bg) !important;
      color: var(--qi-chip-ink) !important;
      border: 1px solid var(--qi-gold-line);
    }

    /* .tab */
    html[data-qi-skin] .nav-pills .nav-link { border-radius: var(--qi-pill); }
    html[data-qi-skin] .nav-pills .nav-link.active {
      background-color: var(--qi-chip-bg);
      color: var(--qi-gold-strong);
      border: 1px solid var(--qi-gold-line);
    }
    html[data-qi-skin] .nav-tabs { border-bottom-color: var(--qi-hairline); }
    html[data-qi-skin] .nav-tabs .nav-link.active {
      color: var(--qi-gold-strong);
      background: transparent;
      border-color: var(--qi-hairline) var(--qi-hairline) transparent;
    }

    /* ── Forms — softened, but not pills; a pill text field reads as a search
       box and most of these are not. ── */
    html[data-qi-skin] .form-check-input:checked {
      background-color: var(--qi-gold); border-color: var(--qi-gold);
    }
    html[data-qi-skin] input[type="checkbox"],
    html[data-qi-skin] input[type="radio"],
    html[data-qi-skin] input[type="range"] { accent-color: var(--qi-gold); }
    html[data-qi-skin] .form-control,
    html[data-qi-skin] .form-select {
      background-color: var(--qi-raised-2);
      border-color: var(--qi-hairline);
      border-radius: var(--qi-radius-sm);
      color: var(--qi-ink);
    }
    html[data-qi-skin] .form-control:focus,
    html[data-qi-skin] .form-select:focus {
      border-color: var(--qi-gold);
      box-shadow: 0 0 0 0.2rem var(--bs-focus-ring-color);
    }
    html[data-qi-skin] .form-label {
      font-size: 0.72rem;
      font-weight: 600;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--qi-ink-muted);
    }
    html[data-qi-skin] .input-group > .form-control { border-radius: var(--qi-radius-sm) 0 0 var(--qi-radius-sm); }
    html[data-qi-skin] .input-group > .btn:last-child { border-radius: 0 var(--qi-pill) var(--qi-pill) 0; }

    /* ── Surfaces ── */
    html[data-qi-skin] .dropdown-menu {
      background-color: var(--qi-raised);
      border: 1px solid var(--qi-hairline);
      border-radius: var(--qi-radius-sm);
      box-shadow: var(--qi-shadow);
      --bs-dropdown-link-hover-bg: var(--qi-tint);
      --bs-dropdown-link-active-bg: var(--qi-tint);
      --bs-dropdown-link-active-color: var(--qi-gold-strong);
    }
    html[data-qi-skin] .modal-content,
    html[data-qi-skin] .offcanvas {
      background-color: var(--qi-raised);
      border-color: var(--qi-hairline);
      border-radius: var(--qi-radius);
      color: var(--qi-ink);
    }
    html[data-qi-skin] .list-group-item {
      background-color: var(--qi-raised);
      border-color: var(--qi-hairline);
      color: var(--qi-ink);
    }
    html[data-qi-skin] .progress { background-color: var(--qi-raised-2); border-radius: var(--qi-pill); }
    html[data-qi-skin] .progress-bar { background-color: var(--qi-gold); }
    html[data-qi-skin] .page-link { color: var(--qi-gold); background: transparent; border-color: var(--qi-hairline); }
    html[data-qi-skin] hr,
    html[data-qi-skin] .dropdown-divider { border-color: var(--qi-hairline); opacity: 1; }
    html[data-qi-skin] code, html[data-qi-skin] kbd, html[data-qi-skin] pre {
      font-family: ui-monospace, SFMono-Regular, "Cascadia Mono", Consolas, monospace;
    }
    /* The small-box KPI tiles ship as saturated flat blocks. Mute them to the
       card surface and let the status colour survive as a left rule only. */
    html[data-qi-skin] .small-box {
      background: var(--qi-raised) !important;
      border: 1px solid var(--qi-hairline);
      border-radius: var(--qi-radius);
      color: var(--qi-ink) !important;
      box-shadow: var(--qi-shadow-soft);
    }
    html[data-qi-skin] .small-box .inner h3 { font-family: var(--qi-serif); color: var(--qi-ink-strong); }
    html[data-qi-skin] .small-box a,
    html[data-qi-skin] .small-box .small-box-footer { color: var(--qi-gold) !important; }
"""

def _get_theme() -> str:
    cfg = _load_hive_config()
    t = cfg.get("theme", "penumbra")
    if t == "dark" and not cfg.get("theme_v2"):
        # Pre-2026-08-06 configs: "dark" meant the original dark look, which
        # is now called "penumbra" ("dark" is the NEXUS-style dark). Migrate
        # once so the saved look does not silently change.
        t = "penumbra"
        try:
            cfg["theme"] = t
            cfg["theme_v2"] = True
            _save_hive_config(cfg)
        except Exception:
            pass
    return t if t in VALID_THEMES else "penumbra"

def _get_header_lock() -> bool:
    """When True, each page's header area (top navbar + title/breadcrumb bar)
    stays pinned while only the content below scrolls. When False, the whole
    page scrolls together (legacy behaviour)."""
    return bool(_load_hive_config().get("lock_header", True))

def _theme_icon(theme: str) -> str:
    return {"penumbra": "bi-moon-stars-fill", "light": "bi-sun-fill",
            "auto": "bi-circle-half", "orange": "bi-brightness-high-fill",
            "dark": "bi-moon-fill", "museum": "bi-bank",
            "manuscript": "bi-journal-bookmark"}.get(theme, "bi-circle-half")


def base_layout(title: str, content: str, active: str = "") -> str:
    nav_items = [
        ("dashboard", "/",        "bi-speedometer2",  "Dashboard"),
        ("voice",     "/voice",   "bi-mic",           "Claude Voice"),
        ("launcher",  "/launcher","bi-grid-3x3-gap",  "Launcher"),
        ("tunnels",   "/tunnels", "bi-globe2",        "Tunnels"),
        ("hive",      "/hive",    "bi-hexagon",       "The Hive"),
        ("health",    "/health",  "bi-heart-pulse",   "Health Check"),
        ("board",     "/board",   "bi-kanban",        "Task Board"),
        ("tests",     "/tests",   "bi-bug",           "Tests"),
        ("projects",  "/projects/status", "bi-clipboard-data", "Project Status"),
        ("services",  "/services","bi-gear-wide-connected", "Services"),
        ("ops",       "/ops",     "bi-wrench-adjustable",   "Ops"),
        ("tasks",     "/tasks",   "bi-calendar-event",      "Scheduled Tasks"),
        ("usage",     "/usage",   "bi-graph-up-arrow","LLM Usage"),
        ("effort",    "/effort",  "bi-stopwatch",     "Effort Ledger"),
        ("news",      "/news",    "bi-newspaper",     "Headlines"),
        ("activity",  "/activity","bi-activity",      "Activity"),
        ("dispatch",  "/dispatch","bi-send-check",    "CoWork Dispatch"),
        ("brain",     "/brain",   "bi-cpu",           "QI Brain"),
        ("mission",   "/mission-control", "bi-broadcast-pin", "Mission Control"),
        ("agent_hr",  "/agents",  "bi-person-badge",  "Agent HR"),
        ("warroom",   "/warroom", "bi-chat-dots",     "War Room"),
        ("logs",      "/logs",    "bi-journal-text",  "Logs"),
        ("config",    "/config",  "bi-sliders",       "Config"),
        ("library",   "/library", "bi-journals",      "Library"),
        ("guide",     "/guide",   "bi-book",          "Guide"),
    ]
    nav_html = ""
    for key, href, icon, label in nav_items:
        active_cls = "active" if active == key else ""
        nav_html += f"""
        <li class="nav-item">
          <a href="{href}" class="nav-link {active_cls}">
            <i class="nav-icon bi {icon}"></i>
            <p>{label}</p>
          </a>
        </li>"""

    now   = datetime.now().strftime("%Y-%m-%d %H:%M")
    theme = _get_theme()
    t_icon = _theme_icon(theme)
    t_icon_style = f' style="color:{QI_ACCENT_ORANGE}"' if theme in _THEME_ACCENT else ""
    # QI theme -> Bootstrap base; 'auto' maps to no data-bs-theme (client resolves from OS)
    _base = _THEME_BASE.get(theme)
    bs_theme_attr = f'data-bs-theme="{_base}"' if _base else ""
    _accent = _THEME_ACCENT.get(theme, "")
    accent_attr = f'data-qi-accent="{_accent}"' if _accent else ""
    _skin = _THEME_SKIN.get(theme, "")
    skin_attr = f'data-qi-skin="{_skin}"' if _skin else ""
    skin_fonts = QI_SKIN_FONTS if _skin else ""
    header_lock_cls = "lock-header" if _get_header_lock() else ""
    return f"""<!doctype html>
<html lang="en" {skin_attr}>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{title} | QI Claude Manager</title>
  {skin_fonts}
  <link rel="stylesheet" href="/static/vendor/overlayscrollbars.min.css"/>
  <link rel="stylesheet" href="/static/vendor/bootstrap-icons/bootstrap-icons.min.css"/>
  <link rel="stylesheet" href="/static/css/adminlte.min.css"/>
  <link rel="stylesheet" href="/static/css/qi-plex.css"/>
  <script src="/static/vendor/bootstrap.bundle.min.js"></script>
  <script src="/static/js/adminlte.min.js"></script>
  <script src="/static/vendor/Sortable.min.js"></script>
  <style>
    /* Hide decorative small-box corner icons (flash/dollar/chat/calendar/play/etc.) — pure chrome, removed to de-clutter. Delete this rule to restore them. */
    .small-box-icon {{ display: none !important; }}
    .bg-qi-purple    {{ background-color: #7e57c2 !important; color: #fff !important; }}
    .bg-qi-purple .small-box-icon,
    .bg-qi-purple a {{ color: #fff !important; }}
    .badge-qi-purple {{ background-color: #7e57c2 !important; color: #fff !important; }}
    .priority-high   {{ border-left: 4px solid #dc3545 !important; }}
    .priority-medium {{ border-left: 4px solid #ffc107 !important; }}
    .priority-low    {{ border-left: 4px solid #198754 !important; }}
    .kanban-col      {{ min-height: 200px; }}
    .task-card       {{ cursor: grab; margin-bottom: 10px; position: relative; }}
    .task-card:active{{ cursor: grabbing; }}
    .task-card:hover .task-actions {{ opacity: 1 !important; }}
    .task-card.selected {{ outline: 2px solid #0d6efd; outline-offset: 1px; }}
    .task-check      {{ visibility: hidden; position: absolute; top: 7px; right: 7px; z-index: 20;
                        width: 1.1rem; height: 1.1rem; cursor: pointer; }}
    .select-mode .task-check        {{ visibility: visible; }}
    .select-mode .task-card         {{ cursor: pointer; }}
    .select-mode .task-card .task-actions {{ display: none !important; }}
    .col-header      {{ font-size: .75rem; font-weight: 700; text-transform: uppercase;
                        letter-spacing: .08em; padding: 8px 12px; border-radius: 6px 6px 0 0; }}
    .badge-agent     {{ font-size: .68rem; }}
    .health-ok       {{ color: #198754; }}
    .health-warn     {{ color: #ffc107; }}
    .health-bad      {{ color: #dc3545; }}
    .sortable-ghost  {{ opacity: .4; }}
    /* ── Locked header area ──────────────────────────────────────────────
       When <body> has .lock-header, the layout becomes truly fixed: the
       wrapper is pinned to the viewport so the top navbar (Home/date/theme)
       and footer stay in place, and only .app-main scrolls internally
       (it already has overflow:auto). The per-page title/breadcrumb strip
       is stuck to the top of that scroll area. Toggle lives under
       Config → "Header area on scroll". */
    body.lock-header .app-wrapper {{
      height: 100vh;
      overflow: hidden;
    }}
    body.lock-header .app-content-header {{
      position: sticky; top: 0; z-index: 1020;
      background: var(--bs-body-bg);
      box-shadow: 0 1px 0 var(--bs-border-color-translucent);
    }}
    /* ── Mobile display fixes (≤991px — where the sidebar already collapses) ──
       Two phone-only problems are fixed here without touching desktop:
       1. The desktop header-lock pins the app to 100vh + overflow:hidden. On
          phones 100vh sits behind the browser address bar, so the bottom gets
          clipped and you can't scroll to it — release it on small screens so
          the page uses normal document scrolling.
       2. Horizontal overflow ("content too wide"): wide tables scroll inside
          their own box, fixed-width blocks/images/SVG shrink to fit, and the
          wrapper never lets the page scroll sideways. */
    @media (max-width: 991.98px) {{
      body.lock-header .app-wrapper {{ height: auto; overflow: visible; }}
      body.lock-header .app-main    {{ overflow: visible; }}
      .app-wrapper                  {{ overflow-x: hidden; }}
      .app-content table            {{ display: block; width: 100%;
                                        overflow-x: auto; -webkit-overflow-scrolling: touch; }}
      .app-content [style*="width"] {{ max-width: 100%; }}
      .app-content img,
      .app-content svg,
      .app-content canvas,
      .app-content pre              {{ max-width: 100%; height: auto; }}
    }}
{QI_ACCENT_CSS}
{QI_SKIN_CSS}
  </style>
  <script>
    /* Resolve the theme onto <html> so EVERY component (incl. dropdowns/modals
       portaled to body) inherits it. 'auto' follows the OS and reacts live —
       Bootstrap has no native 'auto', so we map it here. QI themes map to a
       Bootstrap base plus an optional accent attribute (Orange/Dark = NEXUS
       orange accent; Penumbra = the original QI dark). */
    (function(){{
      var t = "{theme}";
      var BASE   = {{penumbra:'dark', dark:'dark', orange:'light', light:'light',
                     museum:'dark', manuscript:'light'}};
      var ACCENT = {{orange:'orange', dark:'orange'}};
      var SKIN   = {{museum:'museum', manuscript:'manuscript'}};
      var mq = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
      function resolve(){{ return t === 'auto' ? (mq && mq.matches ? 'dark' : 'light') : (BASE[t] || 'dark'); }}
      function apply(){{
        document.documentElement.setAttribute('data-bs-theme', resolve());
        if (ACCENT[t]) document.documentElement.setAttribute('data-qi-accent', ACCENT[t]);
        else document.documentElement.removeAttribute('data-qi-accent');
        if (SKIN[t]) document.documentElement.setAttribute('data-qi-skin', SKIN[t]);
        else document.documentElement.removeAttribute('data-qi-skin');
      }}
      apply();
      if (t === 'auto' && mq && mq.addEventListener) mq.addEventListener('change', apply);
    }})();
  </script>
</head>
<body class="layout-fixed sidebar-expand-lg bg-body-tertiary {header_lock_cls}" {bs_theme_attr} {accent_attr} {skin_attr}>
<div class="app-wrapper">

  <!-- Navbar -->
  <nav class="app-header navbar navbar-expand bg-body">
    <div class="container-fluid">
      <ul class="navbar-nav">
        <li class="nav-item">
          <a class="nav-link" data-lte-toggle="sidebar" href="#" role="button">
            <i class="bi bi-list"></i>
          </a>
        </li>
      </ul>
      <ul class="navbar-nav ms-auto">
        <li class="nav-item"><span class="nav-link text-muted" style="font-size:.8rem">{now}</span></li>
        <!-- Theme switcher -->
        <li class="nav-item dropdown">
          <a class="nav-link" href="#" data-bs-toggle="dropdown" title="Switch theme" id="themeToggle">
            <i class="bi {t_icon}"{t_icon_style}></i>
          </a>
          <ul class="dropdown-menu dropdown-menu-end" style="min-width:140px">
            <li><a class="dropdown-item {'fw-bold' if theme=='penumbra' else ''}"
                   href="#" onclick="setTheme('penumbra');return false;">
              <i class="bi bi-moon-stars-fill me-2"></i>Penumbra</a></li>
            <li><a class="dropdown-item {'fw-bold' if theme=='light' else ''}"
                   href="#" onclick="setTheme('light');return false;">
              <i class="bi bi-sun-fill me-2"></i>Light</a></li>
            <li><a class="dropdown-item {'fw-bold' if theme=='auto' else ''}"
                   href="#" onclick="setTheme('auto');return false;">
              <i class="bi bi-circle-half me-2"></i>System</a></li>
            <li><hr class="dropdown-divider"></li>
            <li><a class="dropdown-item {'fw-bold' if theme=='orange' else ''}"
                   href="#" onclick="setTheme('orange');return false;">
              <i class="bi bi-brightness-high-fill me-2" style="color:{QI_ACCENT_ORANGE}"></i>Orange</a></li>
            <li><a class="dropdown-item {'fw-bold' if theme=='dark' else ''}"
                   href="#" onclick="setTheme('dark');return false;">
              <i class="bi bi-moon-fill me-2" style="color:{QI_ACCENT_ORANGE}"></i>Dark</a></li>
            <li><hr class="dropdown-divider"></li>
            <li><a class="dropdown-item {'fw-bold' if theme=='museum' else ''}"
                   href="#" onclick="setTheme('museum');return false;">
              <i class="bi bi-bank me-2" style="color:#d4af6a"></i>Museum</a></li>
            <li><a class="dropdown-item {'fw-bold' if theme=='manuscript' else ''}"
                   href="#" onclick="setTheme('manuscript');return false;">
              <i class="bi bi-journal-bookmark me-2" style="color:#9a7a2e"></i>Manuscript</a></li>
          </ul>
        </li>
        <!-- Write-access unlock (needed for in-page saves through the tunnel) -->
        <li class="nav-item">
          <a class="nav-link" href="#" id="qiLockToggle" title="Write access"
             onclick="return qiUnlock();">
            <i class="bi bi-lock-fill" id="qiLockIcon"></i>
          </a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="/health" title="Run Health Check">
            <i class="bi bi-heart-pulse"></i>
          </a>
        </li>
      </ul>
    </div>
  </nav>

  <!-- Sidebar -->
  <aside class="app-sidebar bg-body-secondary shadow" {bs_theme_attr}>
    <div class="sidebar-brand">
      <a href="/" class="brand-link">
        <i class="bi bi-cpu brand-image" style="font-size:1.6rem;margin-right:8px;color:#6366f1"></i>
        <span class="brand-text fw-bold">QI Hive</span>
      </a>
    </div>
    <div class="sidebar-wrapper d-flex flex-column" style="height:calc(100vh - 56px);">
      <nav class="mt-2 flex-grow-1">
        <ul class="nav sidebar-menu flex-column" data-lte-toggle="treeview" role="navigation">
          <li class="nav-header">QI HIVE</li>
          {nav_html}
        </ul>
      </nav>
      <div class="sidebar-legend px-3 pb-3 pt-2 border-top border-secondary-subtle" style="font-size:.75rem;">
        <div class="text-uppercase text-secondary fw-bold mb-2" style="letter-spacing:.05em;font-size:.68rem;">Status Legend</div>
        <div class="d-flex align-items-center mb-1"><span class="badge text-bg-dark me-2" style="width:14px;height:14px;padding:0;">&nbsp;</span><span>Complete</span></div>
        <div class="d-flex align-items-center mb-1"><span class="badge text-bg-success me-2" style="width:14px;height:14px;padding:0;">&nbsp;</span><span>In Progress</span></div>
        <div class="d-flex align-items-center mb-1"><span class="badge text-bg-warning me-2" style="width:14px;height:14px;padding:0;">&nbsp;</span><span>Backlog / Paused</span></div>
        <div class="d-flex align-items-center mb-1"><span class="badge text-bg-light me-2" style="width:14px;height:14px;padding:0;border:1px solid #555">&nbsp;</span><span>New</span></div>
        <div class="d-flex align-items-center mb-1"><span class="badge badge-qi-purple me-2" style="width:14px;height:14px;padding:0;">&nbsp;</span><span>Pre-POC</span></div>
        <div class="d-flex align-items-center mb-1"><span class="badge text-bg-secondary me-2" style="width:14px;height:14px;padding:0;">&nbsp;</span><span>Retired / Merged</span></div>
        <div class="d-flex align-items-center"><span class="badge text-bg-info me-2" style="width:14px;height:14px;padding:0;">&nbsp;</span><span>Unknown status</span></div>
      </div>
    </div>
  </aside>

  <!-- Content -->
  <main class="app-main">
    <div class="app-content-header">
      <div class="container-fluid">
        <div class="row">
          <div class="col-sm-6"><h3 class="mb-0">{title}</h3></div>
          <div class="col-sm-6">
            <ol class="breadcrumb float-sm-end">
              <li class="breadcrumb-item"><a href="/">Home</a></li>
              <li class="breadcrumb-item active">{title}</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
    <div class="app-content">
      <div class="container-fluid">
        {_readme_block(active)}{content}
      </div>
    </div>
  </main>

  <footer class="app-footer">
    <div class="float-end d-none d-sm-inline">QI Hive v3.0 — Powered by QI Brain</div>
    <strong>Quiddity Innovations</strong>
  </footer>
</div>

<script src="/static/vendor/overlayscrollbars.browser.es5.min.js"></script>
<script>
/* ── Tunnel write-access unlock ───────────────────────────────────────────────
   The server's tunnel_write_guard rejects mutating requests that arrive through
   the public tunnel unless they carry X-QI-Token. We store the token in this
   browser (localStorage) once, then transparently attach it to every same-origin
   write so in-page saves (theme, tasks, config…) work remotely. Anonymous
   visitors who never enter the token stay read-only. */
(function(){{
  var TKEY = 'qiWriteToken';
  function tok(){{ try {{ return localStorage.getItem(TKEY) || ''; }} catch(e) {{ return ''; }} }}

  var _fetch = window.fetch.bind(window);
  window.fetch = function(input, init){{
    init = init || {{}};
    var method = (init.method || (input && input.method) || 'GET').toUpperCase();
    var url    = (typeof input === 'string') ? input : (input && input.url) || '';
    var sameOrigin = url.indexOf('/') === 0 || url.indexOf(location.origin) === 0;
    if (sameOrigin && ['POST','PUT','PATCH','DELETE'].indexOf(method) !== -1) {{
      var t = tok();
      if (t) {{
        var h = new Headers(init.headers || (typeof input !== 'string' && input.headers) || {{}});
        h.set('X-QI-Token', t);
        init.headers = h;
      }}
    }}
    return _fetch(input, init);
  }};

  function setIcon(unlocked){{
    var i = document.getElementById('qiLockIcon');
    if (i) i.className = 'bi ' + (unlocked ? 'bi-unlock-fill text-success' : 'bi-lock-fill');
    var a = document.getElementById('qiLockToggle');
    if (a) a.title = unlocked ? 'Write access unlocked — click to clear'
                              : 'Locked — click to enter write token';
  }}

  window.qiUnlock = function(){{
    if (tok()) {{
      if (confirm('Clear stored write token? Saves through the tunnel will be blocked again.')) {{
        try {{ localStorage.removeItem(TKEY); }} catch(e) {{}}
        setIcon(false);
      }}
      return false;
    }}
    var t = (prompt('Enter dashboard write token\\n(from C:\\\\QIH\\\\secrets\\\\dashboard_write_token.txt):') || '').trim();
    if (!t) return false;
    _fetch('/api/write-token/verify', {{headers: {{'X-QI-Token': t}}}})
      .then(function(r){{ return r.json(); }})
      .then(function(d){{
        if (d && d.ok) {{
          try {{ localStorage.setItem(TKEY, t); }} catch(e) {{}}
          setIcon(true);
          alert('Unlocked — in-page saves will now work through the tunnel.');
        }} else {{
          alert('Invalid token — not stored.');
        }}
      }})
      .catch(function(){{ alert('Could not verify token.'); }});
    return false;
  }};

  document.addEventListener('DOMContentLoaded', function(){{ setIcon(!!tok()); }});
}})();

function setTheme(t) {{
  fetch('/api/theme', {{method:'POST', headers:{{'Content-Type':'application/json'}},
    body: JSON.stringify({{theme: t}})
  }}).then(function(r){{
    if (r.ok) {{ location.reload(); return; }}
    if (r.status === 403) {{ alert('Theme change blocked — click the lock icon and enter your write token first.'); }}
    else {{ alert('Could not change theme (HTTP ' + r.status + ').'); }}
  }}).catch(function(){{ alert('Could not reach the server to change theme.'); }});
}}
</script>
</body>
</html>"""

# ── Main Dashboard ────────────────────────────────────────────────────────────

def _get_agent_activity_overrides() -> dict:
    """For non-Claude/Hive agents, pull activity from their own production sources.
    Returns {agent_id: {count, last_seen, label, source}}.

    Honest semantics: 'count' is whatever that agent's natural unit of work is
    (conversations for chat agents, digests/sessions for orchestrators), NOT
    Claude Code session_log entries. The Agent Team panel uses this when an
    override is present; falls back to session_log query otherwise.
    """
    import sqlite3
    overrides = {}

    # Maia: conversations grouped by conv_key (each conv_key = one chat thread)
    try:
        c = sqlite3.connect("file:C:/APPS/QI/maia.db?mode=ro", uri=True, timeout=2.0)
        try:
            total_convs = c.execute("SELECT COUNT(DISTINCT conv_key) FROM conversations").fetchone()[0]
            last_ts = c.execute("SELECT MAX(ts) FROM conversations").fetchone()[0]
            msgs_7d = c.execute("SELECT COUNT(*) FROM conversations WHERE ts >= datetime('now','-7 days')").fetchone()[0]
            overrides["maia"] = {
                "count": total_convs,
                "last_seen": last_ts,
                "label": f"{total_convs} conv · {msgs_7d} msgs 7d",
                "source": "C:/APPS/QI/maia.db conversations",
                "unit": "conversations",
            }
        finally:
            c.close()
    except Exception:
        pass

    # Naya: same shape
    try:
        c = sqlite3.connect("file:C:/APPS/NAYA/naya.db?mode=ro", uri=True, timeout=2.0)
        try:
            total_convs = c.execute("SELECT COUNT(DISTINCT conv_key) FROM conversations").fetchone()[0]
            last_ts = c.execute("SELECT MAX(ts) FROM conversations").fetchone()[0]
            msgs_7d = c.execute("SELECT COUNT(*) FROM conversations WHERE ts >= datetime('now','-7 days')").fetchone()[0]
            overrides["naya"] = {
                "count": total_convs,
                "last_seen": last_ts,
                "label": f"{total_convs} conv · {msgs_7d} msgs 7d",
                "source": "C:/APPS/NAYA/naya.db conversations",
                "unit": "conversations",
            }
        finally:
            c.close()
    except Exception:
        pass

    # NEXUS: scout digests + synthesis sessions
    try:
        c = sqlite3.connect("file:C:/APPS/NEXUS/nexus.db?mode=ro", uri=True, timeout=2.0)
        try:
            digests = c.execute("SELECT COUNT(*) FROM scout_digests").fetchone()[0]
            sessions = c.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            last_digest = c.execute("SELECT MAX(created_at) FROM scout_digests").fetchone()[0]
            last_sess = c.execute("SELECT MAX(created_at) FROM sessions").fetchone()[0]
            last = max(filter(None, [last_digest, last_sess]), default=None)
            overrides["nexus"] = {
                "count": digests + sessions,
                "last_seen": last,
                "label": f"{digests} digests · {sessions} synth",
                "source": "C:/APPS/NEXUS/nexus.db",
                "unit": "digests + sessions",
            }
        finally:
            c.close()
    except Exception:
        pass

    # OpenClaw: count log files per known agent folder + latest mtime
    try:
        oc_logs = Path(r"C:\APPS\OC\runtime\logs\agents")
        if oc_logs.exists():
            total_logs = 0
            latest = None
            for sub in oc_logs.iterdir():
                if sub.is_dir():
                    logs = list(sub.glob("*.log"))
                    total_logs += len(logs)
                    if logs:
                        m = max(p.stat().st_mtime for p in logs)
                        if latest is None or m > latest:
                            latest = m
            from datetime import datetime as _dt
            last_str = _dt.fromtimestamp(latest).strftime("%Y-%m-%d %H:%M:%S") if latest else None
            overrides["openclaw"] = {
                "count": total_logs,
                "last_seen": last_str,
                "label": f"{total_logs} agent log files",
                "source": "C:/APPS/OC/runtime/logs/agents",
                "unit": "log files",
            }
    except Exception:
        pass

    return overrides

# Project LLM inventory is near-static config (a few read-only DB/JSON reads
# plus one NEXUS probe), but it is rendered on the root page, so every single
# dashboard load paid for it. Cache it briefly: a model list that is up to a
# minute stale is harmless, a slow root page is not.
_project_llms_cache = {"data": [], "ts": 0.0}
_PROJECT_LLMS_TTL = 60.0   # seconds


def _get_project_llms() -> list[dict]:
    """Read each project's Ollama model usage from its own config.
    Returns list of {project, models: [{name, role, notes}], source}."""
    import sqlite3, time as _time
    if (_time.time() - _project_llms_cache["ts"] < _PROJECT_LLMS_TTL
            and _project_llms_cache["data"]):
        return _project_llms_cache["data"]
    out = []

    # Maia + Naya: both have llm_chain tables with the same schema
    for proj, db_path in [("Maia", r"C:\APPS\QI\maia.db"), ("Naya", r"C:\APPS\NAYA\naya.db")]:
        try:
            c = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2.0)
            try:
                rows = list(c.execute(
                    "SELECT bot_key, priority, model, label, notes FROM llm_chain "
                    "WHERE provider='ollama' AND active=1 ORDER BY bot_key, priority"
                ))
                models = [{
                    "name":  r[2],
                    "role":  f"#{r[1]} {r[0]}",
                    "notes": (r[4] or "")[:80],
                } for r in rows]
            finally:
                c.close()
            out.append({"project": proj, "source": db_path, "models": models})
        except Exception as e:
            out.append({"project": proj, "source": db_path, "models": [], "error": str(e)})

    # NEXUS: hits /providers; specific models come from the running router config
    try:
        import urllib.request, json as _j
        # 127.0.0.1, never "localhost". On this box localhost resolves to ::1
        # first and IPv6 loopback SYNs are dropped rather than refused, so
        # urllib — which tries addresses sequentially, unlike curl's parallel
        # Happy Eyeballs — burned the full timeout before falling back to IPv4.
        # NEXUS binds 127.0.0.1 only, so this cost 2s on every dashboard load.
        with urllib.request.urlopen("http://127.0.0.1:8010/providers", timeout=2.0) as r:
            prov = _j.loads(r.read().decode('utf-8')).get("providers", [])
        models = []
        if "ollama" in prov:
            models.append({"name": "ollama (provider configured)", "role": "router", "notes": "specific models chosen per request"})
        if "gemma4" in prov:
            models.append({"name": "gemma4:* (provider alias)", "role": "router", "notes": ""})
        out.append({"project": "NEXUS", "source": "http://127.0.0.1:8010/providers", "models": models})
    except Exception as e:
        out.append({"project": "NEXUS", "source": "API", "models": [], "error": str(e)})

    # CogniBase: settings.json → vendors[id=ollama]
    try:
        cb_cfg = json.loads(Path(r"C:\APPS\CogniBase\Settings\settings.json").read_text(encoding="utf-8"))
        ollama_vendors = [v for v in cb_cfg.get("vendors", []) if "ollama" in (v.get("id") or "").lower()]
        models = []
        for v in ollama_vendors:
            active = "✅ active" if v.get("active") else "⚪ configured"
            for m in (v.get("models_chat") or []):
                models.append({"name": m, "role": v.get("id"), "notes": active})
            if not v.get("models_chat"):
                models.append({"name": f"({v.get('id')}: no models defined)", "role": v.get("id"), "notes": active})
        out.append({"project": "CogniBase", "source": r"C:\APPS\CogniBase\Settings\settings.json", "models": models})
    except Exception as e:
        out.append({"project": "CogniBase", "source": "settings.json", "models": [], "error": str(e)})

    # AutoPDF: autopdf-settings.json
    try:
        ap = json.loads(Path(r"C:\APPS\AutoPDF\Application\autopdf-settings.json").read_text(encoding="utf-8"))
        m = ap.get("ollamaModel")
        models = [{"name": m, "role": "smart-mapping", "notes": "AI template authoring + field extract"}] if m else []
        out.append({"project": "AutoPDF", "source": r"C:\APPS\AutoPDF\Application\autopdf-settings.json", "models": models})
    except Exception as e:
        out.append({"project": "AutoPDF", "source": "settings", "models": [], "error": str(e)})

    # OpenClaw: documented in OC repo (router fallback + vision). Hardcoded from repo docs.
    out.append({"project": "OpenClaw", "source": r"C:\APPS\OC\repo\agents (docs)", "models": [
        {"name": "qwen3:8b",      "role": "kaze-router-fallback", "notes": "activates when Cloudflare Workers AI fails"},
        {"name": "qwen3-vl:8b",   "role": "vision (default)",     "notes": "Playwright NLM element location, fast"},
        {"name": "qwen3-vl:32b",  "role": "vision (--accurate)",  "notes": "slower, excellent accuracy"},
    ]})

    # MapSnap: confirmed no LLM usage (static schema browser)
    out.append({"project": "MapSnap", "source": r"C:\APPS\MapSnap (no LLM)", "models": []})

    # EasyFlow: no Ollama usage detected in source
    out.append({"project": "EasyFlow", "source": r"C:\APPS\EasyFlow (Gmail tooling, no LLM)", "models": []})

    _project_llms_cache.update({"data": out, "ts": _time.time()})
    return out

def render_project_llms() -> str:
    data = _get_project_llms()
    rows = ""
    total_models = 0
    for proj in data:
        ms = proj.get("models") or []
        name = proj["project"]
        if not ms:
            rows += (
                f'<tr><td><strong>{name}</strong></td>'
                f'<td colspan="3" class="text-muted fst-italic" style="font-size:.8rem">'
                f'No Ollama models registered'
                f'{" — " + proj["error"] if proj.get("error") else ""}'
                f'</td></tr>'
            )
            continue
        for i, m in enumerate(ms):
            total_models += 1
            mn = m.get("name", "?")
            role = m.get("role", "")
            notes = m.get("notes", "")
            proj_cell = f'<strong>{name}</strong>' if i == 0 else '<span class="text-muted" style="font-size:.7rem">•</span>'
            badge_cls = "text-bg-success" if "active" in notes.lower() or "default" in notes.lower() else "text-bg-secondary"
            rows += (
                f'<tr><td>{proj_cell}</td>'
                f'<td><span class="badge {badge_cls}" style="font-family:Consolas,monospace;font-size:.72rem">{mn}</span></td>'
                f'<td class="text-muted" style="font-size:.78rem">{role}</td>'
                f'<td class="text-muted" style="font-size:.75rem">{notes}</td></tr>'
            )
    return f"""
    <div class="row mt-2">
      <div class="col-12">
        <div class="card">
          <div class="card-header d-flex align-items-center">
            <h3 class="card-title mb-0"><i class="bi bi-cpu-fill me-2"></i>Local LLMs by Project (Ollama)</h3>
            <span class="ms-auto text-muted" style="font-size:.7rem">live from each project's config · {total_models} model bindings</span>
          </div>
          <div class="card-body p-0">
            <table class="table table-sm table-hover mb-0">
              <thead><tr><th style="width:14%">Project</th><th style="width:24%">Ollama Model</th><th style="width:22%">Role</th><th>Notes</th></tr></thead>
              <tbody>{rows}</tbody>
            </table>
          </div>
        </div>
      </div>
    </div>"""

def render_dashboard() -> str:
    status  = load_status()
    agents  = load_agents()
    tasks   = load_tasks()
    readiness = load_json(Path(r"C:\QIH\data\project_readiness.json"))

    # Status -> (color, icon). Must match the sidebar legend:
    #   dark      = Complete / production-stable
    #   success   = In Progress / active development
    #   warning   = Backlog / paused (work needed before it can move)
    #   light     = New / not started
    #   purple    = Pre-POC (custom, see qi-purple CSS class)
    #   secondary = Retired / merged / deprecated (i.e. dead)
    proj_colors = {
        # Pre-POC (custom purple — needs qi-purple class injected in base_layout CSS)
        "pre_poc":                              ("qi-purple", "bi-lightbulb"),
        "pre-poc":                              ("qi-purple", "bi-lightbulb"),
        # Legend statuses (original)
        "complete":                            ("dark",      "bi-check-circle-fill"),
        "in_progress":                         ("success",   "bi-play-circle-fill"),
        "backlog":                              ("warning",   "bi-inbox-fill"),
        "new":                                  ("light",     "bi-stars"),
        "retired":                              ("secondary", "bi-archive-fill"),
        "idle":                                 ("secondary", "bi-dash-circle"),
        # Production / complete (dark)
        "active_production":                    ("dark",      "bi-check-circle-fill"),
        "active_stable":                        ("dark",      "bi-shield-check"),
        "phase_b_core_complete_pilot_ready":    ("dark",      "bi-check-circle-fill"),
        # In Progress / actively developing (success/green)
        "active_development":                   ("success",   "bi-play-circle-fill"),
        "in_development":                       ("success",   "bi-play-circle-fill"),
        "active":                               ("success",   "bi-play-circle-fill"),
        "active dev":                           ("success",   "bi-play-circle-fill"),  # lowercased
        # Backlog / paused (warning/yellow)
        "paused":                               ("warning",   "bi-pause-circle"),
        "paused_pending_credentials":           ("warning",   "bi-pause-circle"),
        "pending":                              ("warning",   "bi-hourglass-split"),
        # Retired-equivalents (secondary/grey)
        "merged_into_naya":                     ("secondary", "bi-arrow-right-circle"),
        "merged":                               ("secondary", "bi-arrow-right-circle"),
        "migrating":                            ("secondary", "bi-arrow-right-circle"),
        "deprecated":                           ("secondary", "bi-archive-fill"),
    }

    # Project status rows — compact table (replaces the old saturated small-boxes).
    # Status drives a small theme-safe dot instead of a full colored card so the
    # screen reads calmly; the per-project detail/board links live in the row.
    _dot_colors = {
        "success":   "var(--bs-success)",   # in progress / active dev
        "warning":   "var(--bs-warning)",   # backlog / paused
        "info":      "var(--bs-info)",       # unknown
        "secondary": "var(--bs-secondary)",  # retired / merged
        "dark":      "var(--bs-emphasis-color)",  # complete / production (adapts per theme)
        "light":     "var(--bs-tertiary-color)",  # new / not started
        "qi-purple": "#7e57c2",             # pre-POC
    }
    project_rows = ""
    for name, p in merge_status_projects(status.get("projects", {})).items():
        st = p.get("status","unknown")
        # Case-insensitive lookup; unknown statuses fall through to INFO (blue),
        # never secondary (grey) which is reserved for retired/merged.
        color, _icon = proj_colors.get(st.lower() if isinstance(st, str) else st,
                                       ("info", "bi-question-circle"))
        dotc = _dot_colors.get(color, "var(--bs-info)")
        pid  = p.get("id", name)
        # Match on any alias this row absorbed, case/punctuation-insensitively —
        # tasks are labelled with whatever name their creator used ("FileHQ"
        # vs "filehq"), and a literal match on the row key undercounts.
        _alias_set = {__import__("re").sub(r"[^a-z0-9]", "", a.lower())
                      for a in p.get("_aliases", [name])}
        _alias_set.add(__import__("re").sub(r"[^a-z0-9]", "", str(pid).lower()))
        open_tasks = sum(
            1 for t in tasks
            if t.get("column") != "done"
            and __import__("re").sub(r"[^a-z0-9]", "", str(t.get("project", "")).lower())
            in _alias_set)
        # Readiness is keyed canonically (lowercase id). Some status.json rows
        # are keyed by display name with no id at all, so a direct lookup
        # missed them and rendered "—" despite the data existing.
        _rk = __import__("re").sub(r"[^a-z0-9]", "", str(name).lower())
        _rd = (readiness.get(name) or readiness.get(pid)
               or next((v for k, v in readiness.items()
                        if isinstance(v, dict)
                        and __import__("re").sub(r"[^a-z0-9]", "", k.lower()) == _rk), None)
               or {})
        _pct = _rd.get("pct")
        if isinstance(_pct, (int, float)):
            _lbl = html.escape(str(_rd.get("label") or ""))
            _note = html.escape(str(_rd.get("note") or ""))
            _tip = " — ".join(x for x in (_lbl, _note) if x)
            _derived = ' style="border-bottom:1px dotted var(--bs-border-color)"' if _rd.get("derived") else ""
            prog = (
                f'<div class="progress flex-grow-1" style="height:5px;max-width:120px;" title="{_tip}">'
                f'<div class="progress-bar bg-secondary opacity-50" style="width:{_pct}%"></div></div>'
                f'<small class="text-body-tertiary ms-2"{_derived} '
                f'style="font-family:Consolas,monospace" title="{_tip}">{_pct}%</small>'
            )
        elif _rd.get("not_applicable"):
            # Don't show a bare dash for something that will never have a
            # percentage — say so, and carry the reason in the tooltip.
            prog = (f'<small class="text-body-tertiary fst-italic" '
                    f'title="{html.escape(str(_rd.get("note") or ""))}">n/a</small>')
        else:
            _why = html.escape(str(_rd.get("note") or "No readiness entry for this project."))
            prog = f'<small class="text-body-tertiary" title="{_why}">—</small>'
        project_rows += f"""<tr>
          <td style="width:16px"><span class="d-inline-block rounded-circle" style="width:8px;height:8px;background:{dotc}" title="{st.replace("_"," ").title()}"></span></td>
          <td><a href="/project/{pid}" class="text-decoration-none fw-medium text-body">{p.get("display_name", name)}</a></td>
          <td><span class="text-body-secondary small">{st.replace("_"," ").title()}</span></td>
          <td><div class="d-flex align-items-center">{prog}</div></td>
          <td class="text-end text-body-secondary small">{open_tasks}</td>
          <td class="text-end"><a href="/board?project={pid}" class="text-decoration-none small">Board <i class="bi bi-arrow-right"></i></a></td>
        </tr>"""

    # Agent table — live from qi_brain.db (agents joined with session_log).
    # Falls back to legacy AGENTS_DIR config files if Brain DB is unavailable.
    # Per-role defaults shown only when an agent has zero sessions logged.
    # These reflect the natural model tier for each role; the dashboard always
    # prefers the actual model_used from the most recent session.
    AGENT_MODEL_DEFAULTS = {
        "hive_architect": "claude-opus-4-7",
        "hive_builder":   "claude-sonnet-4-6",
        "hive_inspector": "claude-sonnet-4-6",
        "hive_ops":       "claude-haiku-4-5-20251001",
        "hive_scout":     "claude-haiku-4-5-20251001",
        "hive_scribe":    "claude-haiku-4-5-20251001",
        "hive_tester":    "claude-haiku-4-5-20251001",
        "claude":         "claude-sonnet-4-6",
        "cowork":         "claude-sonnet-4-6",
    }

    def _model_badge(model: str | None) -> str:
        m = (model or "").lower()
        if "opus" in m:    cls, label = "danger",    "opus"
        elif "sonnet" in m: cls, label = "primary",   "sonnet"
        elif "haiku" in m:  cls, label = "secondary", "haiku"
        elif m in ("git-only","unknown","",None): return '<span class="text-muted">—</span>'
        else:               cls, label = "dark",     m
        # tier suffix: pull "4-7", "4-6", "4-5" if present
        import re
        v = re.search(r"\b(\d-\d)\b", m or "")
        if v: label = f"{label} {v.group(1)}"
        return f'<span class="badge text-bg-{cls}">{label}</span>'

    brain_agents = _brain_db_query("""
        SELECT a.agent_id, a.display_name, a.agent_type, a.active, a.description,
               (SELECT s.ended_at FROM session_log s
                  WHERE s.agent_id = a.agent_id
                  ORDER BY COALESCE(s.ended_at, s.started_at) DESC LIMIT 1) AS last_seen,
               (SELECT s.model_used FROM session_log s
                  WHERE s.agent_id = a.agent_id
                  ORDER BY COALESCE(s.ended_at, s.started_at) DESC LIMIT 1) AS last_model,
               (SELECT COUNT(*) FROM session_log s
                  WHERE s.agent_id = a.agent_id) AS session_count
        FROM agents a
        WHERE a.active = 1
        ORDER BY (last_seen IS NULL), last_seen DESC, a.display_name
    """)

    def _fmt_last_seen(ts: str | None) -> str:
        if not ts:
            return '<span class="text-muted fst-italic">never</span>'
        from datetime import datetime, timezone
        try:
            dt = datetime.fromisoformat(ts.replace(" ", "T"))
            now = datetime.now()
            delta = now - dt
            secs = delta.total_seconds()
            if secs < 0:        label = ts
            elif secs < 3600:   label = f"{int(secs//60)}m ago"
            elif secs < 86400:  label = f"{int(secs//3600)}h ago"
            elif secs < 86400*7: label = f"{int(secs//86400)}d ago"
            else:               label = dt.strftime("%Y-%m-%d")
            cls = "text-success" if secs < 86400 else ("text-warning" if secs < 86400*7 else "text-muted")
            return f'<span class="{cls}" title="{ts}">{label}</span>'
        except Exception:
            return f'<span class="text-muted">{ts}</span>'

    activity_overrides = _get_agent_activity_overrides()

    agent_rows = ""
    if brain_agents:
        # Legacy config lookup is used only for scope text (Brain has descriptions too).
        legacy = {n.lower(): c for n, c in agents.items()}
        for a in brain_agents:
            aid   = a["agent_id"]
            name  = a["display_name"] or aid
            kind  = a["agent_type"] or ""
            legacy_key = aid.replace("hive_", "").lower()
            cfg   = legacy.get(legacy_key, {})
            scope = cfg.get("scope") or a["description"] or "—"

            # Activity override: for non-Claude/Hive agents, pull from production source.
            ov = activity_overrides.get(aid)
            if ov:
                # Replace the Brain-DB-derived last_seen / count with production data.
                a = dict(a)
                a["last_seen"]      = ov.get("last_seen") or a.get("last_seen")
                a["session_count"]  = ov.get("count", a.get("session_count", 0))
                a["_activity_label"] = ov.get("label")
                a["_activity_source"] = ov.get("source")
                a["_activity_unit"]   = ov.get("unit")
            kind_badge = {
                "hive":   "text-bg-primary",
                "claude": "text-bg-info",
                "system": "text-bg-dark",
            }.get(kind, "text-bg-secondary")

            # Model: prefer actual model_used from most recent session; fall back to role default.
            last_model = (a.get("last_model") or "").strip().lower()
            if last_model and last_model not in ("unknown", "git-only", "—"):
                model_html = _model_badge(last_model)
            else:
                default_model = AGENT_MODEL_DEFAULTS.get(aid, "")
                if default_model:
                    model_html = (
                        '<span class="text-muted" style="font-size:.7rem">default:</span> '
                        + _model_badge(default_model).replace("text-bg-", "text-bg-").replace('class="badge ', 'class="badge opacity-75 ')
                    )
                else:
                    model_html = '<span class="text-muted">—</span>'

            activity_cell = (
                f'<span class="badge text-bg-light" title="{a.get("_activity_source","")}">'
                f'{a.get("session_count",0)}</span>'
                + (f' <small class="text-muted ms-1">{a.get("_activity_label")}</small>'
                   if a.get("_activity_label") else '')
            )
            agent_rows += f"""<tr>
              <td><strong>{name}</strong> <span class="badge {kind_badge} ms-1" style="font-size:.6rem;font-weight:500">{kind}</span></td>
              <td>{_fmt_last_seen(a.get("last_seen"))}</td>
              <td>{activity_cell}</td>
              <td>{model_html}</td>
              <td class="text-muted small">{scope}</td>
            </tr>"""
    else:
        # Fallback to legacy static configs (used when Brain DB is offline)
        for name, cfg in sorted(agents.items()):
            st  = cfg.get("status","idle")
            mdl = cfg.get("model_default","—")
            mshort = mdl.replace("claude-","").replace("-4-6","").replace("-4-5-20251001","")
            bcol = model_colors.get(mdl,"secondary")
            scope = cfg.get("scope","—")
            agent_rows += f"""<tr>
              <td><strong>{name.title()}</strong></td>
              <td><span class="text-muted">{st} (static)</span></td>
              <td>—</td>
              <td><span class="badge text-bg-{bcol}">{mshort}</span></td>
              <td class="text-muted small">{scope}</td>
            </tr>"""

    # Recent sessions — live from qi_brain.db session_log table.
    sessions = _brain_db_query("""
        SELECT session_id, project_id, agent_id, session_title, summary,
               started_at, ended_at, model_used
        FROM session_log
        ORDER BY COALESCE(ended_at, started_at) DESC
        LIMIT 12
    """)
    session_rows = ""
    if sessions:
        for s in sessions:
            ts    = s.get("ended_at") or s.get("started_at") or ""
            title = s.get("session_title") or "—"
            proj  = s.get("project_id") or "—"
            summ  = (s.get("summary") or "").replace("<", "&lt;")
            if len(summ) > 180:
                summ = summ[:180] + "…"
            session_rows += f"""<tr>
              <td>
                <div><strong style="font-size:.85rem">{title}</strong></div>
                <div class="text-muted" style="font-size:.7rem;font-family:Consolas,monospace">{ts} · {proj}</div>
              </td>
              <td><small class="text-muted">{summ}</small></td>
            </tr>"""
    else:
        # Fallback to old status.json list if Brain DB unavailable
        for s in reversed(status.get("session_log", [])):
            session_rows += f"""<tr>
              <td><small>{s.get("session","—")}</small></td>
              <td><small class="text-muted">{s.get("summary","—")}</small></td>
            </tr>"""

    # Open task count badges
    col_counts = {}
    for t in tasks:
        col_counts[t.get("column","backlog")] = col_counts.get(t.get("column","backlog"),0)+1

    # Claude usage snapshot — consumption ladder: today / week / 30d / QTD / YTD.
    from datetime import date as _date
    def _fmt_tok(t):
        t = t or 0
        if t >= 1_000_000: return f'{t/1_000_000:.1f}M'
        if t >= 1_000:     return f'{t/1_000:.0f}K'
        return str(int(t))
    try:
        _today_d = _date.today()
        _q_num   = (_today_d.month - 1) // 3 + 1
        _q_start = _date(_today_d.year, (_q_num - 1) * 3 + 1, 1)
        _y_start = _date(_today_d.year, 1, 1)
        u_today = usage_stats.today()
        u_week  = usage_totals(7)
        u_30    = usage_totals(30)
        u_qtd   = usage_totals_since(_q_start)
        u_ytd   = usage_totals_since(_y_start)
        tokens_today   = _fmt_tok(u_today["tokens"])
        cost_today     = f'${u_today["cost_usd"]:,.2f}'
        sessions_today = u_today["sessions"]
        turns_today    = u_today["assistant_turns"]
        cost_week = f'${u_week["cost_usd"]:,.0f}'
        cost_30   = f'${u_30["cost_usd"]:,.0f}'
        cost_qtd  = f'${u_qtd["cost_usd"]:,.0f}'
        cost_ytd  = f'${u_ytd["cost_usd"]:,.0f}'
        sub_today = f'{turns_today} turns'
        sub_week  = f'{_fmt_tok(u_week["tokens"])} tok'
        sub_30    = f'{_fmt_tok(u_30["tokens"])} tok'
        # Long-horizon tiles are served from the durable ledger, which mixes
        # measured days with reconstructed ones (transcripts deleted before
        # 2026-06-26 are gone for good). Surface that ratio rather than let a
        # largely-modelled figure read as hard data.
        def _prov(u):
            pct = u.get("measured_pct")
            return f' · {pct:.0f}% measured' if pct is not None else ''
        sub_qtd   = f'{_fmt_tok(u_qtd["tokens"])} tok{_prov(u_qtd)}'
        sub_ytd   = f'{_fmt_tok(u_ytd["tokens"])} tok{_prov(u_ytd)}'
        q_label   = f'Q{_q_num} to date'
    except Exception as e:
        tokens_today = cost_today = sessions_today = turns_today = "—"
        cost_week = cost_30 = cost_qtd = cost_ytd = "—"
        sub_today = sub_week = sub_30 = sub_qtd = sub_ytd = ""
        q_label = "Quarter"
        log.warning(f"usage_stats failed: {e}")

    # Agent HR headline — active roster + this week's activity (read-only
    # agent_hr.db; same DB the /agents page and /api/agent-hr read).
    agent_hr_active = agent_hr_runs_week = agent_hr_tokens_week = "—"
    try:
        from datetime import timedelta as _hr_td
        _hr_cutoff = (datetime.now() - _hr_td(days=7)).isoformat()
        _hr_conn = _agent_hr_conn()
        try:
            agent_hr_active = _hr_conn.execute(
                "SELECT COUNT(*) FROM agents WHERE last_active >= ?", (_hr_cutoff,)
            ).fetchone()[0]
            _hr_runs, _hr_tokens = _hr_conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(tokens),0) FROM runs WHERE started_at >= ?",
                (_hr_cutoff,),
            ).fetchone()
            agent_hr_runs_week = _hr_runs
            agent_hr_tokens_week = _fmt_tok(_hr_tokens)
        finally:
            _hr_conn.close()
    except Exception as e:
        log.warning(f"agent_hr summary failed: {e}")

    def _tile(label, value, href="/usage", sub=""):
        sub_html = (f'<div class="text-body-tertiary" style="font-size:.62rem;line-height:1.1">{sub}</div>'
                    if sub else '')
        return (
            f'<div class="col"><a href="{href}" class="text-decoration-none">'
            f'<div class="card border-0 bg-body-secondary h-100"><div class="card-body py-2 px-3">'
            f'<div class="text-body-secondary" style="font-size:.72rem">{label}</div>'
            f'<div class="fw-medium text-body" style="font-size:1.2rem;line-height:1.2">{value}</div>'
            f'{sub_html}'
            f'</div></div></a></div>'
        )

    return f"""
    <!-- Bento metric tiles: token consumption + cost + task counts -->
    <div class="row g-2 mb-3">
      <div class="col-12 col-lg-4">
        <div class="card border-0 bg-body-secondary h-100">
          <div class="card-body d-flex flex-column justify-content-between py-3 px-3">
            <span class="text-body-secondary d-flex align-items-center gap-1" style="font-size:.75rem"><i class="bi bi-lightning-charge"></i> Tokens today</span>
            <div>
              <div class="fw-medium" style="font-size:1.9rem;line-height:1.05">{tokens_today}</div>
              <div class="text-body-tertiary" style="font-size:.7rem">fresh, ex-cache · {sessions_today} sessions · {turns_today} turns · <a href="/usage" class="text-decoration-none">details</a></div>
            </div>
          </div>
        </div>
      </div>
      <div class="col-12 col-lg-8">
        <div class="d-flex flex-column gap-2 h-100">
          <div class="row row-cols-2 row-cols-md-5 g-2">
            {_tile("API today", cost_today, "/usage", sub_today)}
            {_tile("Week (7d)", cost_week, "/usage", sub_week)}
            {_tile("30 days", cost_30, "/usage", sub_30)}
            {_tile(q_label, cost_qtd, "/usage", sub_qtd)}
            {_tile("Year to date", cost_ytd, "/usage", sub_ytd)}
          </div>
          <div class="row row-cols-2 row-cols-md-4 g-2">
            {_tile("In progress", col_counts.get("in_progress",0), "/board")}
            {_tile("Backlog", col_counts.get("backlog",0), "/board")}
            {_tile("In review", col_counts.get("review",0), "/board")}
            {_tile("Done", col_counts.get("done",0), "/board")}
          </div>
        </div>
      </div>
    </div>

    <!-- Agent HR headline — first-class landing tile, mirrors the bento cards above -->
    <div class="row g-2 mb-3">
      <div class="col-12">
        <a href="/agents" class="text-decoration-none">
          <div class="card border-0 bg-body-secondary">
            <div class="card-body d-flex flex-wrap align-items-center gap-4 py-3 px-3">
              <span class="text-body-secondary d-flex align-items-center gap-1" style="font-size:.75rem"><i class="bi bi-person-badge"></i> Agent HR</span>
              <div class="d-flex align-items-baseline gap-1">
                <div class="fw-medium text-body" style="font-size:1.5rem;line-height:1.05">{agent_hr_active}</div>
                <div class="text-body-tertiary" style="font-size:.7rem">active agents</div>
              </div>
              <div class="d-flex align-items-baseline gap-1">
                <div class="fw-medium text-body" style="font-size:1.5rem;line-height:1.05">{agent_hr_runs_week}</div>
                <div class="text-body-tertiary" style="font-size:.7rem">runs this week</div>
              </div>
              <div class="d-flex align-items-baseline gap-1">
                <div class="fw-medium text-body" style="font-size:1.5rem;line-height:1.05">{agent_hr_tokens_week}</div>
                <div class="text-body-tertiary" style="font-size:.7rem">tokens this week</div>
              </div>
              <span class="ms-auto text-body-secondary" style="font-size:.72rem">Roster & recent assignments <i class="bi bi-arrow-right"></i></span>
            </div>
          </div>
        </a>
      </div>
    </div>

    <!-- Project status table -->
    <div class="card mb-3">
      <div class="card-header d-flex align-items-center py-2">
        <span class="fw-medium"><i class="bi bi-folder2-open me-2 text-body-secondary"></i>Projects</span>
        <a href="/board" class="ms-auto small text-decoration-none">Open board <i class="bi bi-arrow-right"></i></a>
      </div>
      <div class="card-body p-0">
        <table class="table table-sm table-hover align-middle mb-0">
          <thead><tr class="text-body-secondary" style="font-size:.72rem">
            <th></th><th>Project</th><th>Status</th><th>Progress</th><th class="text-end">Open</th><th></th>
          </tr></thead>
          <tbody>{project_rows}</tbody>
        </table>
      </div>
    </div>

    <!-- Agents + Sessions: clean summaries; full detail on their own pages -->
    <div class="row g-3">
      <div class="col-lg-6">
        <div class="card h-100">
          <div class="card-header d-flex align-items-center py-2">
            <span class="fw-medium"><i class="bi bi-people me-2 text-body-secondary"></i>Agent team</span>
            <a href="/hive" class="ms-auto small text-decoration-none">The Hive <i class="bi bi-arrow-right"></i></a>
          </div>
          <div class="card-body p-0">
            <table class="table table-sm table-hover align-middle mb-0" style="font-size:.82rem">
              <thead><tr class="text-body-secondary" style="font-size:.72rem"><th>Agent</th><th>Last active</th><th>Activity</th><th>Model</th><th>Scope</th></tr></thead>
              <tbody>{agent_rows}</tbody>
            </table>
          </div>
        </div>
      </div>
      <div class="col-lg-6">
        <div class="card h-100">
          <div class="card-header d-flex align-items-center py-2">
            <span class="fw-medium"><i class="bi bi-journal-text me-2 text-body-secondary"></i>Session log</span>
            <a href="/hive" class="ms-auto small text-decoration-none">View all <i class="bi bi-arrow-right"></i></a>
          </div>
          <div class="card-body p-0">
            <table class="table table-sm table-hover align-middle mb-0" style="font-size:.82rem">
              <tbody>{session_rows}</tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    {render_project_llms()}

    <!-- Live tiles: the QI_HiveIngest service refreshes status.json every ~90s.
         Reload only when this tab is in the foreground so background tabs and
         other pages are never disturbed. -->
    <script>
      setInterval(() => {{
        if (document.visibilityState === 'visible') location.reload();
      }}, 90000);
    </script>
    """

# ── Health Page ───────────────────────────────────────────────────────────────

def render_health() -> str:
    data = run_health_check()
    checked_at = data["checked_at"]

    rows = ""
    action_items = []

    svc_map = {
        "running":   ('<span class="health-ok"><i class="bi bi-circle-fill"></i> running</span>'),
        "stopped":   ('<span class="health-bad"><i class="bi bi-circle-fill"></i> stopped</span>'),
        "not_found": ('<span class="health-bad"><i class="bi bi-dash-circle"></i> not found</span>'),
        "n/a":       ('<span class="text-muted">n/a</span>'),
        "unknown":   ('<span class="text-muted">unknown</span>'),
    }
    health_badge = {
        "ok":        "success",
        "warning":   "warning",
        "attention": "danger",
    }

    for name, p in data["projects"].items():
        health = p.get("health","unknown")
        hbadge = health_badge.get(health,"secondary")

        if not p.get("exists"):
            rows += f"""<tr><td><strong>{name}</strong></td>
              <td colspan="5"><span class="text-danger">Path not found on disk</span></td>
              <td><span class="badge text-bg-danger">missing</span></td></tr>"""
            continue

        svc_html = svc_map.get(p.get("service","n/a"), '<span class="text-muted">—</span>')
        if "tunnel" in p:
            t = svc_map.get(p.get("tunnel","n/a"),'')
            svc_html += f"<br><small>{t} tunnel</small>"

        port_open = p.get("port_open")
        port_html = '<span class="text-muted">n/a</span>' if port_open is None else (
            '<span class="health-ok"><i class="bi bi-check-circle"></i></span>' if port_open else
            '<span class="health-bad"><i class="bi bi-x-circle"></i></span>')

        git = p.get("git", {})
        dirty = git.get("uncommitted_changes", 0)
        branch = git.get("branch","?")
        last = (git.get("last_commit") or "no commits")[:45]
        git_html = f'<small class="d-block">{branch} · {last}</small>'
        if dirty:
            git_html += f'<span class="badge text-bg-warning">{dirty} uncommitted</span>'

        docs = p.get("docs","—")
        docs_html = (f'<span class="health-ok"><i class="bi bi-check-circle"></i> {docs}</span>' if docs=="current"
                     else f'<span class="health-warn"><i class="bi bi-exclamation-triangle"></i> {docs}</span>' if "stale" in str(docs)
                     else f'<span class="health-bad"><i class="bi bi-x-circle"></i> {docs}</span>')

        sum_html = ('<span class="health-ok"><i class="bi bi-check-circle"></i></span>' if p.get("has_summary")
                    else '<span class="health-bad"><i class="bi bi-x-circle"></i> missing</span>')

        issues = p.get("issues",[])
        for issue in issues:
            action_items.append(f"<strong>{name}</strong>: {issue}")

        rows += f"""<tr>
          <td><strong>{name}</strong><br><small class="text-muted">{p['path']}</small></td>
          <td>{svc_html}</td><td>{port_html}</td>
          <td>{git_html}</td><td>{docs_html}</td><td>{sum_html}</td>
          <td><span class="badge text-bg-{hbadge}">{health}</span></td>
        </tr>"""

    action_html = ""
    if action_items:
        items = "".join(f"<li>{a}</li>" for a in action_items)
        action_html = f"""
        <div class="callout callout-warning mb-3">
          <h5><i class="bi bi-exclamation-triangle me-2"></i>Action Needed</h5>
          <ul class="mb-0">{items}</ul>
        </div>"""

    return f"""
    <div class="row mb-3">
      <div class="col-12 d-flex justify-content-between align-items-center">
        <span class="text-muted"><i class="bi bi-clock me-1"></i>Checked: {checked_at}</span>
        <button class="btn btn-success btn-sm" onclick="location.reload()">
          <i class="bi bi-arrow-clockwise me-1"></i>Re-check
        </button>
      </div>
    </div>
    {action_html}
    <div class="card">
      <div class="card-header"><h3 class="card-title">All Projects</h3></div>
      <div class="card-body p-0">
        <table class="table table-hover table-sm mb-0">
          <thead class="table-dark">
            <tr><th>Project</th><th>Service</th><th>Port</th><th>Git</th><th>Docs</th><th>Summary</th><th>Health</th></tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </div>
    <script>setTimeout(()=>location.reload(),60000);</script>"""

# ── Kanban Board ──────────────────────────────────────────────────────────────

def render_board(project_filter: str = "") -> str:
    tasks   = load_tasks()
    status  = load_status()

    projects = ["All"] + list(status.get("projects", {}).keys())
    proj_opts = "".join(
        f'<option value="{p}" {"selected" if p==project_filter else ""}>{p}</option>'
        for p in projects)

    columns = [
        ("backlog",     "Backlog",     "warning"),
        ("in_progress", "In Progress", "success"),
        ("review",      "Review",      "info"),
        ("done",        "Done",        "dark"),
    ]

    priority_colors = {"high": "danger", "medium": "warning", "low": "success"}
    agent_icons = {
        "architect": "bi-pencil-square", "builder": "bi-hammer",
        "scout": "bi-binoculars",        "scribe": "bi-journal-text",
        "ops": "bi-gear",                "inspector": "bi-shield-check",
        "tester": "bi-bug",
    }

    col_html = ""
    for col_key, col_label, col_color in columns:
        col_tasks = [t for t in tasks
                     if t.get("column") == col_key
                     and (not project_filter or project_filter == "All" or t.get("project") == project_filter)]
        cards = ""
        for t in col_tasks:
            pri = t.get("priority","medium")
            pri_color = priority_colors.get(pri,"secondary")
            agent = t.get("agent","—")
            a_icon = agent_icons.get(agent,"bi-person")
            proj = t.get("project","—")
            cards += f"""
            <div class="card task-card priority-{pri}" data-id="{t['id']}"
                 data-title="{t['title'].replace(chr(34), '&quot;')}"
                 data-desc="{t.get('description','').replace(chr(34), '&quot;')}"
                 data-project="{proj}"
                 data-agent="{agent}"
                 data-priority="{pri}"
                 onclick="cardClick(event, this)">
              <input type="checkbox" class="task-check form-check-input"
                     onclick="event.stopPropagation()" onchange="onCheckChange()"/>
              <div class="card-body p-2">
                <div class="d-flex justify-content-between align-items-start mb-1">
                  <span class="badge text-bg-{pri_color} badge-agent">{pri}</span>
                  <div class="d-flex gap-1 task-actions"
                       style="opacity:0;transition:opacity .15s;">
                    <button class="btn btn-xs btn-outline-secondary py-0 px-1"
                            onclick="event.stopPropagation();openEditModal('{t['id']}')"
                            title="Edit task" style="font-size:.68rem;">
                      <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-xs btn-outline-danger py-0 px-1"
                            onclick="event.stopPropagation();deleteTask('{t['id']}')"
                            title="Delete task" style="font-size:.68rem;">
                      <i class="bi bi-trash3"></i>
                    </button>
                  </div>
                </div>
                <p class="mb-1 fw-semibold" style="font-size:.9rem">{t['title']}</p>
                <p class="text-muted mb-2" style="font-size:.78rem">{t.get('description','')[:80]}{'...' if len(t.get('description',''))>80 else ''}</p>
                <div class="d-flex justify-content-between align-items-center">
                  <span class="badge text-bg-secondary badge-agent">
                    <i class="bi {a_icon} me-1"></i>{agent}
                  </span>
                  <span class="badge text-bg-dark badge-agent">{proj}</span>
                </div>
              </div>
            </div>"""

        count = len(col_tasks)
        col_html += f"""
        <div class="col-lg-3 col-md-6">
          <div class="col-header bg-{col_color} bg-opacity-25 mb-2 d-flex justify-content-between">
            <span>{col_label}</span>
            <span class="badge text-bg-{col_color}">{count}</span>
          </div>
          <div class="kanban-col" id="col-{col_key}" data-column="{col_key}">{cards}</div>
        </div>"""

    proj_select_opts = "".join(
        f'<option value="{p}">{p}</option>' for p in list(status.get("projects",{}).keys()))
    agent_select_opts = "".join(
        f'<option value="{a}">{a.title()}</option>'
        for a in ["architect","builder","scout","scribe","ops","inspector","tester"])

    return f"""
    <!-- Toolbar -->
    <div class="row mb-3">
      <div class="col-md-4">
        <div class="input-group input-group-sm">
          <label class="input-group-text">Project</label>
          <select class="form-select" id="projectFilter" onchange="filterProject(this.value)">
            {proj_opts}
          </select>
        </div>
      </div>
      <div class="col-md-8 text-end d-flex gap-2 justify-content-end">
        <button class="btn btn-sm btn-danger d-none" id="deleteSelectedBtn"
                onclick="deleteSelected()">
          <i class="bi bi-trash3 me-1"></i>Delete Selected (<span id="selCount">0</span>)
        </button>
        <button class="btn btn-sm btn-outline-secondary" id="selectToggleBtn"
                onclick="toggleSelectMode()">
          <i class="bi bi-check2-square me-1"></i>Select
        </button>
        <button class="btn btn-sm btn-primary" data-bs-toggle="modal" data-bs-target="#addTaskModal">
          <i class="bi bi-plus-circle me-1"></i>Add Task
        </button>
      </div>
    </div>

    <!-- Board -->
    <div class="row" id="kanban-board">{col_html}</div>

    <!-- Add Task Modal -->
    <div class="modal fade" id="addTaskModal" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title"><i class="bi bi-plus-circle me-2"></i>New Task</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">Title</label>
              <input type="text" class="form-control" id="newTitle" placeholder="What needs to be done?"/>
            </div>
            <div class="mb-3">
              <label class="form-label">Description</label>
              <textarea class="form-control" id="newDesc" rows="2" placeholder="Details..."></textarea>
            </div>
            <div class="row">
              <div class="col-md-4 mb-3">
                <label class="form-label">Project</label>
                <select class="form-select" id="newProject">
                  {proj_select_opts}
                </select>
              </div>
              <div class="col-md-4 mb-3">
                <label class="form-label">Agent</label>
                <select class="form-select" id="newAgent">
                  {agent_select_opts}
                </select>
              </div>
              <div class="col-md-4 mb-3">
                <label class="form-label">Priority</label>
                <select class="form-select" id="newPriority">
                  <option value="high">High</option>
                  <option value="medium" selected>Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-primary" onclick="addTask()">Add to Backlog</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Edit Task Modal -->
    <div class="modal fade" id="editTaskModal" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title"><i class="bi bi-pencil me-2"></i>Edit Task</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <input type="hidden" id="editTaskId"/>
            <div class="mb-3">
              <label class="form-label">Title</label>
              <input type="text" class="form-control" id="editTitle"/>
            </div>
            <div class="mb-3">
              <label class="form-label">Description</label>
              <textarea class="form-control" id="editDesc" rows="2"></textarea>
            </div>
            <div class="row">
              <div class="col-md-4 mb-3">
                <label class="form-label">Project</label>
                <select class="form-select" id="editProject">
                  {proj_select_opts}
                </select>
              </div>
              <div class="col-md-4 mb-3">
                <label class="form-label">Agent</label>
                <select class="form-select" id="editAgent">
                  {agent_select_opts}
                </select>
              </div>
              <div class="col-md-4 mb-3">
                <label class="form-label">Priority</label>
                <select class="form-select" id="editPriority">
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-primary" onclick="saveEdit()">Save Changes</button>
          </div>
        </div>
      </div>
    </div>

    <script>
    // Initialise SortableJS on each column
    document.querySelectorAll('.kanban-col').forEach(col => {{
      Sortable.create(col, {{
        group: 'tasks',
        animation: 150,
        ghostClass: 'sortable-ghost',
        filter: '.task-check',
        onEnd: function(evt) {{
          const taskId = evt.item.dataset.id;
          const newCol = evt.to.dataset.column;
          fetch('/api/tasks/' + taskId, {{
            method: 'PATCH',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{column: newCol}})
          }}).then(() => updateCounts());
        }}
      }});
    }});

    function updateCounts() {{
      document.querySelectorAll('.kanban-col').forEach(col => {{
        const colKey = col.dataset.column;
        const count  = col.querySelectorAll('.task-card').length;
        const badge  = col.previousElementSibling.querySelector('.badge');
        if (badge) badge.textContent = count;
      }});
    }}

    function filterProject(val) {{
      window.location.href = '/board?project=' + encodeURIComponent(val);
    }}

    function addTask() {{
      const payload = {{
        title:    document.getElementById('newTitle').value,
        description: document.getElementById('newDesc').value,
        project:  document.getElementById('newProject').value,
        agent:    document.getElementById('newAgent').value,
        priority: document.getElementById('newPriority').value,
      }};
      fetch('/api/tasks', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify(payload)
      }}).then(() => location.reload());
    }}

    function deleteTask(id) {{
      if (!confirm('Delete this task?')) return;
      fetch('/api/tasks/' + id, {{method: 'DELETE'}})
        .then(() => location.reload());
    }}

    // ── Edit modal ────────────────────────────────────────────────────────
    function openEditModal(id) {{
      const card = document.querySelector('.task-card[data-id="' + id + '"]');
      if (!card) return;
      document.getElementById('editTaskId').value    = id;
      document.getElementById('editTitle').value     = card.dataset.title || '';
      document.getElementById('editDesc').value      = card.dataset.desc  || '';
      const proj = document.getElementById('editProject');
      if (proj) {{ for (let o of proj.options) o.selected = (o.value === card.dataset.project); }}
      const agent = document.getElementById('editAgent');
      if (agent) {{ for (let o of agent.options) o.selected = (o.value === card.dataset.agent); }}
      const pri = document.getElementById('editPriority');
      if (pri) {{ for (let o of pri.options) o.selected = (o.value === card.dataset.priority); }}
      new bootstrap.Modal(document.getElementById('editTaskModal')).show();
    }}

    function saveEdit() {{
      const id = document.getElementById('editTaskId').value;
      const payload = {{
        title:       document.getElementById('editTitle').value,
        description: document.getElementById('editDesc').value,
        project:     document.getElementById('editProject').value,
        agent:       document.getElementById('editAgent').value,
        priority:    document.getElementById('editPriority').value,
      }};
      fetch('/api/tasks/' + id, {{
        method: 'PATCH',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify(payload)
      }}).then(() => location.reload());
    }}

    // ── Select / bulk-delete ──────────────────────────────────────────────
    let _selectMode = false;

    function toggleSelectMode() {{
      _selectMode = !_selectMode;
      const board = document.getElementById('kanban-board');
      const btn   = document.getElementById('selectToggleBtn');
      if (_selectMode) {{
        board.classList.add('select-mode');
        btn.classList.remove('btn-outline-secondary');
        btn.classList.add('btn-warning');
        btn.innerHTML = '<i class="bi bi-x-lg me-1"></i>Cancel';
      }} else {{
        board.classList.remove('select-mode');
        btn.classList.remove('btn-warning');
        btn.classList.add('btn-outline-secondary');
        btn.innerHTML = '<i class="bi bi-check2-square me-1"></i>Select';
        document.querySelectorAll('.task-check').forEach(cb => {{ cb.checked = false; }});
        document.querySelectorAll('.task-card').forEach(c => c.classList.remove('selected'));
        onCheckChange();
      }}
    }}

    function cardClick(evt, card) {{
      if (!_selectMode) return;
      const cb = card.querySelector('.task-check');
      cb.checked = !cb.checked;
      card.classList.toggle('selected', cb.checked);
      onCheckChange();
    }}

    function onCheckChange() {{
      const count = document.querySelectorAll('.task-check:checked').length;
      document.getElementById('selCount').textContent = count;
      const btn = document.getElementById('deleteSelectedBtn');
      btn.classList.toggle('d-none', count === 0);
    }}

    function deleteSelected() {{
      const ids = [...document.querySelectorAll('.task-check:checked')]
                    .map(cb => cb.closest('.task-card').dataset.id);
      if (!ids.length) return;
      if (!confirm('Delete ' + ids.length + ' task(s)?')) return;
      Promise.all(ids.map(id =>
        fetch('/api/tasks/' + id, {{method: 'DELETE'}})
      )).then(() => location.reload());
    }}
    </script>"""

# ── Hive Page ─────────────────────────────────────────────────────────────────

def render_hive() -> str:
    online  = brain_online()
    agents  = get_agents()
    snap    = get_ecosystem_snapshot()
    bstatus = get_brain_status()

    brain_badge = (
        '<span class="badge text-bg-success"><i class="bi bi-circle-fill me-1"></i>Online :9011</span>'
        if online else
        '<span class="badge text-bg-danger"><i class="bi bi-circle-fill me-1"></i>Offline</span>'
    )

    # ── Stats row: prefer Brain, fall back to inferred local metrics ──
    # Brain uses flat keys: active_projects, active_decisions, features_logged, sessions_logged
    import json as _json
    from pathlib import Path as _Path

    def _local_inferred():
        """Compute reasonable fallbacks from local files when Brain is empty/offline."""
        proj_active = 0
        try:
            sj = _json.loads(_Path(r"C:\QIH\data\status.json").read_text(encoding="utf-8"))
            proj_active = sum(1 for p in sj.get("projects", {}).values()
                              if str(p.get("status","")).lower() not in ("retired","archived"))
        except Exception: pass
        # Decisions proxy: one session-summary docx = roughly one decision set
        decisions = 0
        try:
            ss = _Path(r"C:\QIH\shared\documentation\session_summaries")
            if ss.exists():
                decisions = sum(1 for _ in ss.glob("*.docx"))
        except Exception: pass
        # Features proxy: open tasks on the board
        features = 0
        try:
            tj = _json.loads(_Path(r"C:\QIH\data\tasks.json").read_text(encoding="utf-8"))
            features = len(tj.get("tasks", []))
        except Exception: pass
        # Sessions: actual Claude Code sessions on disk (30d)
        sessions = 0
        try:
            sessions = len(usage_stats.sessions_log(days=30, limit=10_000))
        except Exception: pass
        return proj_active, decisions, features, sessions

    loc_proj, loc_dec, loc_feat, loc_sess = _local_inferred()

    def _as_int(v):
        try: return max(int(v), 0)
        except Exception: return 0

    # Always take max(brain, local-inferred) — brain's counters undercount until every
    # session explicitly logs via qi.log_* calls, so local disk data is the truer floor.
    n_projects  = max(_as_int(bstatus.get("active_projects",  bstatus.get("projects",{}).get("active",0))),  loc_proj)
    n_decisions = max(_as_int(bstatus.get("active_decisions", bstatus.get("decisions",{}).get("active",0))), loc_dec)
    n_features  = max(_as_int(bstatus.get("features_logged",  bstatus.get("features",{}).get("total",0))),   loc_feat)
    n_sessions  = max(_as_int(bstatus.get("sessions_logged",  bstatus.get("sessions",{}).get("total",0))),   loc_sess)

    # ── Per-agent task counts from local tasks.json ──
    agent_local_counts: dict[str, int] = {}
    try:
        tasks = _json.loads(_Path(r"C:\QIH\data\tasks.json").read_text(encoding="utf-8")).get("tasks", [])
        for t in tasks:
            a = (t.get("agent") or "").lower().strip()
            if not a: continue
            # map raw agent → brain agent_id (tasks use short names; brain uses hive_<name>)
            bid = f"hive_{a}" if a in {"architect","builder","inspector","ops","scout","scribe","tester"} else a
            agent_local_counts[bid] = agent_local_counts.get(bid, 0) + 1
        # Claude Code sessions count as its task volume
        agent_local_counts["claude"] = loc_sess
        # Project-bound agents: count tasks targeting that project
        proj_agent = {"Maia":"maia","Naya":"naya","NEXUS":"nexus"}
        for t in tasks:
            p = t.get("project")
            if p in proj_agent:
                k = proj_agent[p]
                agent_local_counts[k] = agent_local_counts.get(k, 0) + 1
    except Exception:
        pass

    def _stat_tile(label, value):
        return (
            f'<div class="col"><div class="card border-0 bg-body-secondary h-100">'
            f'<div class="card-body py-2 px-3">'
            f'<div class="text-body-secondary" style="font-size:.72rem">{label}</div>'
            f'<div class="fw-medium text-body" style="font-size:1.4rem;line-height:1.2">{value}</div>'
            f'</div></div></div>'
        )
    stats_html = f"""
    <div class="row row-cols-2 row-cols-md-4 g-2 mb-3">
      {_stat_tile("Active projects", n_projects)}
      {_stat_tile("Decisions logged", n_decisions)}
      {_stat_tile("Features tracked", n_features)}
      {_stat_tile("Sessions logged", n_sessions)}
    </div>"""

    # Agent cards
    type_colors = {"hive": "primary", "claude": "danger", "maia": "success",
                   "nexus": "warning", "naya": "info", "system": "secondary"}
    agent_cards = ""
    for a in agents:
        atype  = a.get("agent_type", "system")
        color  = type_colors.get(atype, "secondary")
        brain_tasks = a.get("task_count", 0) or 0
        local_tasks = agent_local_counts.get(a["agent_id"], 0)
        tasks  = max(brain_tasks, local_tasks)
        name   = a.get("display_name", a["agent_id"])
        desc   = (a.get("description") or "")[:90]
        aid    = a["agent_id"]
        agent_cards += f"""
        <div class="col-lg-4 col-md-6 mb-3">
          <div class="card h-100 border-{color}" style="border-left:4px solid !important">
            <div class="card-body">
              <div class="d-flex justify-content-between align-items-start mb-2">
                <h5 class="card-title mb-0">{name}</h5>
                <span class="badge text-bg-{color}">{atype}</span>
              </div>
              <p class="card-text text-muted" style="font-size:.83rem">{desc}</p>
              <div class="d-flex justify-content-between align-items-center mt-auto">
                <small class="text-muted"><i class="bi bi-lightning me-1"></i>{tasks} tasks logged</small>
                <a href="/hive/agent/{aid}" class="btn btn-sm btn-outline-{color}">Profile</a>
              </div>
            </div>
          </div>
        </div>"""

    if not agent_cards:
        # Distinguish: Brain offline vs Brain online but no agents registered yet.
        logger.debug("/api/agents returned %d agents (brain_online=%s)", len(agents), online)
        if not online:
            agent_cards = '<div class="col-12"><div class="alert alert-warning">QI Brain offline — agent profiles unavailable.</div></div>'
        else:
            agent_cards = '<div class="col-12"><div class="alert alert-info">No agents registered yet. Agents appear here once they connect to QI Brain.</div></div>'

    # Recent sessions — query Brain DB directly (ecosystem_snapshot has no recent_sessions key)
    sessions = _brain_db_query(
        "SELECT session_title, project_id, summary, COALESCE(ended_at,started_at) AS ended_at "
        "FROM session_log ORDER BY ended_at DESC LIMIT 6")
    session_rows = ""
    for s in sessions:
        session_rows += f"""<tr>
          <td><small><strong>{s.get('session_title','—')}</strong></small></td>
          <td><small class="badge text-bg-secondary">{s.get('project_id','—')}</small></td>
          <td><small class="text-muted">{(s.get('summary',''))[:70]}</small></td>
          <td><small>{(s.get('ended_at',''))[:10]}</small></td>
        </tr>"""
    if not session_rows:
        session_rows = '<tr><td colspan="4" class="text-center text-muted">No sessions logged yet.</td></tr>'

    return f"""
    <!-- Brain status banner -->
    <div class="row mb-3">
      <div class="col-12 d-flex justify-content-between align-items-center">
        <div><i class="bi bi-cpu me-2 text-primary"></i><strong>QI Brain</strong> {brain_badge}</div>
        <a href="/brain/docs" target="_blank" class="btn btn-sm btn-outline-secondary">
          <i class="bi bi-box-arrow-up-right me-1"></i>Brain API Docs
        </a>
      </div>
    </div>

    {stats_html}

    <!-- Agent grid -->
    <div class="row mb-2">
      <div class="col-12">
        <h5 class="mb-3"><i class="bi bi-hexagon me-2 text-primary"></i>Hive Agents</h5>
      </div>
    </div>
    <div class="row">{agent_cards}</div>

    <!-- Session log -->
    <div class="row mt-3">
      <div class="col-12">
        <div class="card">
          <div class="card-header d-flex justify-content-between">
            <h3 class="card-title"><i class="bi bi-journal-text me-2"></i>Recent Sessions (QI Brain)</h3>
          </div>
          <div class="card-body p-0">
            <table class="table table-sm table-hover mb-0">
              <thead class="table-dark"><tr><th>Session</th><th>Project</th><th>Summary</th><th>Date</th></tr></thead>
              <tbody>{session_rows}</tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- Brain Poller -->
    <div class="row mt-4">
      <div class="col-lg-6">
        <div class="card">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h3 class="card-title"><i class="bi bi-arrow-repeat me-2 text-info"></i>Brain Poller</h3>
            <button class="btn btn-sm btn-outline-info" onclick="triggerPoll()">
              <i class="bi bi-play-fill me-1"></i>Poll Now
            </button>
          </div>
          <div class="card-body" id="pollerStatus">
            <p class="text-muted">Loading poller status…</p>
          </div>
        </div>
      </div>

      <!-- Distillation -->
      <div class="col-lg-6">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title"><i class="bi bi-funnel me-2 text-warning"></i>Distil Brain Memory</h3>
          </div>
          <div class="card-body">
            <div class="mb-2">
              <label class="form-label form-label-sm">Project</label>
              <select class="form-select form-select-sm" id="distillProject">
                <option value="">— select project —</option>
                {''.join(f'<option value="{p}">{p}</option>' for p in [
                    "qi_hive","easyflow","maia","naya","nexus","openclaw","filehq"
                ])}
              </select>
            </div>
            <div class="mb-2">
              <label class="form-label form-label-sm">Reason</label>
              <select class="form-select form-select-sm" id="distillReason" onchange="toggleDistillFields()">
                <option value="stale_cleanup">Stale cleanup (remove dead paths / worktree refs)</option>
                <option value="scope_dropped">Scope dropped (feature or project line retired)</option>
                <option value="completed">Project completed (squash to final state)</option>
              </select>
            </div>
            <div id="distillScopeFields">
              <div class="mb-2">
                <label class="form-label form-label-sm">Scope label <small class="text-muted">(what was dropped)</small></label>
                <input type="text" class="form-control form-control-sm" id="distillScope"
                       placeholder="e.g. Naya chat interface, NEXUS v1, worktree paths"/>
              </div>
              <div class="mb-2">
                <label class="form-label form-label-sm">Reason note <small class="text-muted">(kept in live Brain)</small></label>
                <input type="text" class="form-control form-control-sm" id="distillNote"
                       placeholder="e.g. Scope paused pending redesign"/>
              </div>
            </div>
            <button class="btn btn-sm btn-warning w-100" onclick="runDistill()">
              <i class="bi bi-funnel-fill me-1"></i>Distil Now
            </button>
            <div id="distillResult" class="mt-2"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Poll history -->
    <div class="row mt-3">
      <div class="col-12">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title"><i class="bi bi-clock-history me-2"></i>Poll History (last 10)</h3>
          </div>
          <div class="card-body p-0">
            <table class="table table-sm table-hover mb-0" id="pollHistory">
              <thead class="table-dark">
                <tr><th>Time</th><th>Duration</th><th>Projects</th><th>Changes</th><th>Inbox</th><th>Errors</th><th>Summary</th></tr>
              </thead>
              <tbody><tr><td colspan="7" class="text-center text-muted">Loading…</td></tr></tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <script>
    // ── Poller status ──────────────────────────────────────────────────────────
    function loadPollerStatus() {{
      fetch('/brain/api/poll/status')
        .then(r => r.json()).then(d => {{
          const el = document.getElementById('pollerStatus');
          const lr = d.last_result || {{}};
          el.innerHTML = `
            <div class="d-flex gap-3 mb-2">
              <span class="badge text-bg-${{d.poller_alive ? 'success':'danger'}}">
                ${{d.poller_alive ? 'Running' : 'Stopped'}}
              </span>
              ${{d.poller_running ? '<span class="badge text-bg-warning">Polling…</span>' : ''}}
            </div>
            <small class="text-muted">Last poll: ${{(lr.started_at || '—').slice(0,19)}}</small><br/>
            <small class="text-muted">${{lr.summary || 'No polls yet'}}</small>`;

          // Fill history table
          const tbody = document.querySelector('#pollHistory tbody');
          if (d.history && d.history.length) {{
            tbody.innerHTML = d.history.slice(0,10).map(h => `
              <tr>
                <td style="font-size:.78rem">${{h.started_at.slice(0,19)}}</td>
                <td>${{h.duration_ms}}ms</td>
                <td>${{h.projects_checked}}</td>
                <td>${{h.changes_found}}</td>
                <td>${{h.inbox_processed}}</td>
                <td>${{h.errors ? JSON.parse(h.errors).length : 0}}</td>
                <td style="font-size:.75rem">${{(h.summary||'').slice(0,80)}}</td>
              </tr>`).join('');
          }} else {{
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No polls recorded yet</td></tr>';
          }}
        }}).catch(() => {{
          document.getElementById('pollerStatus').innerHTML =
            '<span class="text-danger">Brain API offline — poller status unavailable</span>';
        }});
    }}
    loadPollerStatus();

    function triggerPoll() {{
      const btn = event.target;
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Polling…';
      fetch('/brain/api/poll/trigger', {{method:'POST'}})
        .then(r => r.json()).then(d => {{
          btn.disabled = false;
          btn.innerHTML = '<i class="bi bi-play-fill me-1"></i>Poll Now';
          loadPollerStatus();
        }}).catch(() => {{
          btn.disabled = false;
          btn.innerHTML = '<i class="bi bi-play-fill me-1"></i>Poll Now';
        }});
    }}

    // ── Distillation ──────────────────────────────────────────────────────────
    function toggleDistillFields() {{
      const reason = document.getElementById('distillReason').value;
      document.getElementById('distillScopeFields').style.display =
        reason === 'completed' ? 'none' : 'block';
    }}

    function runDistill() {{
      const project = document.getElementById('distillProject').value;
      const reason  = document.getElementById('distillReason').value;
      const scope   = document.getElementById('distillScope').value;
      const note    = document.getElementById('distillNote').value;
      if (!project) {{ alert('Select a project first'); return; }}
      if (reason !== 'completed' && !scope) {{ alert('Enter a scope label'); return; }}
      if (!confirm(`Distil ${{project}} (${{reason}})? This will archive matching records.`)) return;

      const el = document.getElementById('distillResult');
      el.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Distilling…';

      fetch('/brain/api/distill', {{
        method: 'POST',
        headers: {{'Content-Type':'application/json'}},
        body: JSON.stringify({{
          project_id: project, reason, scope_label: scope, drop_reason: note
        }})
      }}).then(r => r.json()).then(d => {{
        el.innerHTML = d.ok
          ? `<div class="alert alert-success py-1 mb-0">
               ✅ Done — ${{d.decisions_archived}} decisions + ${{d.features_archived}} features archived.
             </div>`
          : `<div class="alert alert-danger py-1 mb-0">Error: ${{d.detail || JSON.stringify(d)}}</div>`;
      }}).catch(e => {{
        el.innerHTML = `<div class="alert alert-danger py-1 mb-0">Network error: ${{e}}</div>`;
      }});
    }}
    </script>"""


def render_agent_profile(agent_id: str) -> str:
    profile = get_agent_profile(agent_id)
    if not profile:
        return f'<div class="alert alert-danger">Agent "{agent_id}" not found or QI Brain offline.</div>'

    growth = profile.get("recent_growth", [])
    patterns = profile.get("top_patterns", [])
    stats = profile.get("stats", {})

    growth_rows = ""
    for g in growth:
        growth_rows += f"""<tr>
          <td><small>{g.get('recorded_at','')[:16]}</small></td>
          <td><small>{g.get('task_summary','')[:60]}</small></td>
          <td><small class="text-success">{g.get('what_worked','') or '—'}</small></td>
          <td><small class="text-warning">{g.get('what_to_improve','') or '—'}</small></td>
          <td><small class="text-info">{g.get('pattern_learned','') or '—'}</small></td>
        </tr>"""
    if not growth_rows:
        growth_rows = '<tr><td colspan="5" class="text-center text-muted">No growth entries yet — this agent has not logged any tasks.</td></tr>'

    pattern_badges = "".join(
        f'<span class="badge text-bg-info me-1 mb-1">{p["pattern"]} <small>×{p["frequency"]}</small></span>'
        for p in patterns
    ) or '<span class="text-muted">No patterns yet.</span>'

    return f"""
    <div class="row mb-3">
      <div class="col-lg-4">
        <div class="card">
          <div class="card-body text-center">
            <i class="bi bi-person-circle" style="font-size:3rem;color:#6366f1"></i>
            <h4 class="mt-2">{profile['display_name']}</h4>
            <span class="badge text-bg-primary">{profile['agent_type']}</span>
            <p class="text-muted mt-2" style="font-size:.85rem">{profile.get('description') or ''}</p>
            <hr/>
            <div class="d-flex justify-content-around">
              <div><h5>{stats.get('total_tasks',0)}</h5><small class="text-muted">Tasks Logged</small></div>
            </div>
          </div>
        </div>
      </div>
      <div class="col-lg-8">
        <div class="card">
          <div class="card-header"><h5 class="card-title">Learned Patterns</h5></div>
          <div class="card-body">{pattern_badges}</div>
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-header"><h5 class="card-title">Growth Log</h5></div>
      <div class="card-body p-0">
        <table class="table table-sm table-hover mb-0">
          <thead class="table-dark">
            <tr><th>Date</th><th>Task</th><th>What Worked</th><th>To Improve</th><th>Pattern</th></tr>
          </thead>
          <tbody>{growth_rows}</tbody>
        </table>
      </div>
    </div>"""


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return base_layout("Dashboard", render_dashboard(), "dashboard")

REGISTRY_PATH = Path(r"C:\QIH\ecosystem\qi_registry.json")

# Known Cloudflare tunnels. As of the 2026-06-20 migration to STATIC NAMED
# tunnels on quiddityinnovations.com, the public URL of each port is PERMANENT
# and resolved from engine/tunnels/tunnels.json (static_urls.url_for_port).
# The "json"/"log" fields below are kept only as a legacy fallback for any port
# still on a quick tunnel.
_TRYCF_RE = __import__("re").compile(r"https://[a-z0-9-]+\.trycloudflare\.com")

# Shared resolver for the static quiddityinnovations.com URLs (source of truth)
import sys as _sys
_TUN_DIR = r"C:\QIH\engine\tunnels"
if _TUN_DIR not in _sys.path:
    _sys.path.insert(0, _TUN_DIR)
try:
    from static_urls import url_for_port as _static_url_for_port
except Exception:
    def _static_url_for_port(_port):
        return None

KNOWN_TUNNELS = [
    {"port": 8600, "label": "Hive Dashboard",
     "json": r"C:\QIH\engine\hive\tunnel\status\tunnel.json"},
    {"port": 6969, "label": "AutoPDF",
     "json": r"C:\AUTOPDF\Application\status\tunnel.json"},
    {"port": 8001, "label": "Maia API",
     "log":  r"C:\APPS\QI\LOGS\tunnel_log.txt"},
    {"port": 7860, "label": "Maia Demo (Gradio)",
     "log":  r"C:\APPS\QI\LOGS\Maia_Gradio_Tunnel_Log.txt"},
    {"port": 7861, "label": "Naya UI",
     "log":  r"C:\APPS\NAYA\LOGS\QI_NayaTunnel.stderr.log"},
    {"port": 7880, "label": "NEXUS UI",
     "log":  r"C:\APPS\NEXUS\LOGS\QI_NEXUSTunnel.stderr.log"},
    {"port": 8650, "label": "CogniBase",
     "log":  r"C:\APPS\CogniBase\LOGS\QI_CogniBaseTunnel.stderr.log"},
    {"port": 9876, "label": "MapSnap",
     "log":  r"C:\APPS\MapSnap\LOGS\QI_MapSnapTunnel.stderr.log"},
    {"port": 8777, "label": "LotteryWiz",
     "log":  r"C:\APPS\Lottery Wiz\LOGS\tunnel.log"},
    {"port": 7842, "label": "CypherMiner",
     "log":  r"C:\APPS\CypherMiner\LOGS\tunnel.log"},
    {"port": 7841, "label": "M2V",
     "log":  r"C:\APPS\M2V\logs\tunnel.log"},
    {"port": 8503, "label": "TubeScout",
     "log":  r"C:\APPS\TUBESCOUT\data\logs\tunnel.log"},
    {"port": 8710, "label": "Gamez (WC2026)",
     "log":  r"C:\APPS\Gamez\proxy\LOGS\tunnel_log.txt"},
]

def _get_tunnels() -> dict[int, dict]:
    """Return {port: {url, status, source, updated_at}} for every known tunnel."""
    out: dict[int, dict] = {}
    for spec in KNOWN_TUNNELS:
        port = int(spec["port"])
        entry = {"url": None, "status": "unknown", "source": None,
                 "updated_at": None, "label": spec.get("label", "")}
        # Permanent static URL from tunnels.json (source of truth) wins.
        static_url = _static_url_for_port(port)
        if static_url:
            entry["url"] = static_url
            entry["status"] = "running"
            entry["source"] = "tunnels.json"
            entry["updated_at"] = "static-named-tunnel"
            out[port] = entry
            continue
        # Try JSON state file first
        if spec.get("json"):
            p = Path(spec["json"])
            entry["source"] = str(p)
            if p.exists():
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    entry["url"]        = data.get("url")
                    entry["status"]     = data.get("status", "unknown")
                    entry["updated_at"] = data.get("updated_at")
                except Exception:
                    pass
        # Fall back to log parsing (last trycloudflare URL wins)
        if not entry["url"] and spec.get("log"):
            p = Path(spec["log"])
            entry["source"] = str(p)
            if p.exists():
                try:
                    # Tail-read: only scan last 256 KB to keep this fast
                    size = p.stat().st_size
                    with open(p, "rb") as f:
                        if size > 262144:
                            f.seek(size - 262144)
                        tail = f.read().decode("utf-8", errors="ignore")
                    matches = _TRYCF_RE.findall(tail)
                    if matches:
                        entry["url"] = matches[-1]
                        entry["status"] = "running"
                        entry["updated_at"] = __import__("datetime").datetime.fromtimestamp(p.stat().st_mtime).isoformat()
                except Exception:
                    pass
        out[port] = entry
    return out

# Non-QI services worth surfacing in the launcher (not in qi_registry.json).
# Each tile: (label, host, port, path_suffix)
LAUNCHER_EXTRAS = [
    ("Ollama — Shared LLM", [
        ("Ollama",        "http://localhost", 11434, ""),
        ("Loaded Models", "http://localhost", 11434, "/api/tags"),
    ]),
]

def _port_open(port, host="127.0.0.1", timeout=0.25):
    import socket
    try:
        port = int(port)
    except (TypeError, ValueError):
        return False
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        return s.connect_ex((host, port)) == 0
    except Exception:
        return False
    finally:
        s.close()

def _probe_ports_parallel(ports):
    """ports: iterable of ints. Returns {port: bool}."""
    from concurrent.futures import ThreadPoolExecutor
    unique = sorted({int(p) for p in ports if isinstance(p, (int, str)) and str(p).isdigit()})
    if not unique:
        return {}
    with ThreadPoolExecutor(max_workers=min(16, len(unique))) as ex:
        results = list(ex.map(_port_open, unique))
    return dict(zip(unique, results))

def _role_tiles(role: str, base: str, public: bool = False):
    """Tiles for one role rooted at `base` (a localhost origin OR a public tunnel URL).

    Returns list of (label, href). The label is derived from the registry ROLE so a
    project's public links read 'Public UI' / 'Public API' / 'Public Docs' — never a
    hand-maintained per-port name that drifts (the old 'Public Maia API' bug).
    Health is local-only (not useful through a public tunnel)."""
    role_l = (role or "").lower()
    b = base.rstrip("/")
    pre = "Public " if public else ""
    if role_l == "api":
        tiles = [(f"{pre}API", b), (f"{pre}Docs", f"{b}/docs")]
        if not public:
            tiles.append(("Health", f"{b}/health"))
        return tiles
    if role_l == "ui":
        return [(f"{pre}UI", b)]
    if role_l == "dashboard":
        return [(f"{pre}Dashboard", b)]
    if role_l == "launcher":
        return [(f"{pre}Launcher", b)]
    if role_l in ("http", "gateway"):
        return [(f"{pre}{role.title()}", b)]
    # Generic: just expose the root with the role label.
    return [(f"{pre}{role.title() or 'Open'}", b)]

def render_launcher(via_tunnel: bool = False) -> str:
    """QI Launcher — full Launchpad look (categorized dark cards, status dots,
    public-tunnel buttons) with a grid <-> columns toggle. Card data is built
    live from qi_registry.json + the dashboard's port probe + tunnel resolver,
    so URLs (including rotating Quick Tunnel URLs) are always current.
    Scoped under #qi-lp so it never collides with the dashboard's Bootstrap CSS.
    """
    import html as _html
    try:
        reg = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        load_err = None
    except Exception as e:
        reg = {"projects": []}
        load_err = str(e)
    projects = [p for p in (reg.get("projects") or []) if isinstance(p, dict)]

    CATEGORIES = [
        ("Core Product",        "core",     ["maia"]),
        ("Backbone",            "backbone", ["nexus", "qi_brain", "qi_hive", "claude_manager"]),
        ("Assistants",          "",         ["naya", "mq", "openclaw"]),
        ("Standalone Tools",    "tool",     ["cognibase", "mapsnap", "autopdf", "easyflow",
                                             "digitization"]),
        ("Utilities & Media",   "tool",     ["lotterywiz", "cypherminer", "tubescout",
                                             "retirementanalyzer", "m2v", "personalsong",
                                             "avatarstudio", "gamez"]),
    ]
    HIDE = {"filehq", "universal"}
    ROLE_LABEL = {"api": "API", "ui": "UI", "dashboard": "Dashboard",
                  "gateway": "Gateway", "http": "App", "desktop": "App"}
    TOOL_CATS = {"Standalone Tools", "Utilities & Media"}
    STRIP_TOOL = {"Standalone Tools"}

    EXTRA_CARDS = [
        ("Assistants & Agents", {
            "name": "Kaze News Tunnel", "badge": "", "type_tag": "Service",
            "desc": "Public Cloudflare tunnel for the Kaze news digest — viewable anywhere, "
                    "including phone. Public link rotates per restart and is pushed to Telegram.",
            "path": "QI_KazeNewsTunnel · C:\\APPS\\OC", "strip": "type-service", "is_tool": False,
            "local": [("News (local) :18800", "http://localhost:18800/ai-digest/", 18800)],
            "extra_links": [("⛅ Public link ↗",
                             "file:///C:/APPS/OC/runtime/dashboard/news-tunnel.html", "tunnel")],
            "github": "",
        }),
        ("Local Infrastructure", {
            "name": "Ollama", "badge": "", "type_tag": "Service",
            "desc": "Local LLM server — Gemma3, DeepSeek-R1, Qwen3, Kimi, etc. "
                    "Shared by Maia, NEXUS, Naya, AutoPDF.",
            "path": "Ollama", "strip": "type-service", "is_tool": False,
            "local": [("Ollama :11434", "http://localhost:11434", 11434),
                      ("/api/tags", "http://localhost:11434/api/tags", 11434)],
            "extra_links": [], "github": "",
        }),
    ]

    # gather ports + probe + resolve tunnels (all live, from the Hive host)
    all_ports = []
    for proj in projects:
        for info in (proj.get("ports") or {}).values():
            if isinstance(info, dict) and str(info.get("current", "")).isdigit():
                all_ports.append(int(info["current"]))
    for _cat, c in EXTRA_CARDS:
        for _l, _h, p in c.get("local", []):
            all_ports.append(int(p))
    port_status = _probe_ports_parallel(all_ports)
    tunnels = _get_tunnels()

    cat_of, cat_badge = {}, {}
    for cname, badge, ids in CATEGORIES:
        cat_badge[cname] = badge
        for i in ids:
            cat_of[i] = cname
    order = ["Core Product", "Backbone", "Assistants", "Agents",
             "Standalone Tools", "Utilities & Media", "Local Infrastructure", "Other"]
    buckets = {c: [] for c in order}

    def esc(s):
        return _html.escape(str(s if s is not None else ""))

    def loc_tile(label, href, up, is_tool):
        dot = "up" if up else ("idle" if is_tool else "down")
        dim = " local-dim" if via_tunnel else ""
        title = "Local only — works on the machine running the Hive" if via_tunnel else href
        return (f'<a class="local{dim}" href="{esc(href)}" target="_blank" rel="noopener" '
                f'title="{esc(title)}">{esc(label)} <span class="status {dot}"></span></a>')

    def tun_tile(url, label="⛅ Tunnel"):
        return (f'<a class="tunnel" href="{esc(url)}" target="_blank" rel="noopener" '
                f'title="Public tunnel — {esc(url)}">{esc(label)}</a>')

    def gh_tile(github):
        if github and str(github).startswith("http"):
            return f'<a class="muted" href="{esc(github)}" target="_blank" rel="noopener">GitHub</a>'
        return ""

    def card_html(name, badge, type_tag, desc, path, links_html, keywords, strip):
        badge_html = f'<span class="badge2 {badge}">{badge}</span>' if badge else ""
        d = (desc or "").strip()
        if len(d) > 180:
            d = d[:177] + "…"
        return (
            f'<div class="card {strip}" data-keywords="{esc(keywords.lower())}">'
            f'<div class="head-row"><h4>{esc(name)} {badge_html}</h4>'
            f'<span class="type-tag">{esc(type_tag)}</span></div>'
            f'<div class="desc">{esc(d)}</div>'
            f'<div class="path">{esc(path)}</div>'
            f'<div class="links">{links_html}</div></div>'
        )

    for proj in projects:
        pid = proj.get("id") or "?"
        if pid in HIDE:
            continue
        name = proj.get("name") or pid
        status = proj.get("status") or ""
        reason = proj.get("status_reason") or ""
        path = proj.get("path") or ""
        ports = proj.get("ports") or {}
        github = proj.get("github") or ""
        cname = cat_of.get(pid, "Other")
        badge = cat_badge.get(cname, "")
        is_tool = cname in TOOL_CATS
        sl = (status + " " + reason).lower()
        paused = any(k in sl for k in ("paused", "pending", "awaiting"))
        strip = "type-paused" if paused else ("type-tool" if cname in STRIP_TOOL else "type-service")
        type_tag = "Paused" if paused else ("On-demand" if cname in STRIP_TOOL else "Service")

        local_html = ""
        kw = f"{name} {pid} {cname}"
        tunnel_candidates = []  # (role, url) for each port with a live tunnel
        for role, info in ports.items():
            if not isinstance(info, dict):
                continue
            cur = info.get("current")
            if not (isinstance(cur, int) or (isinstance(cur, str) and str(cur).isdigit())):
                continue
            port = int(cur)
            up = port_status.get(port, False)
            label = ROLE_LABEL.get(role.lower(), role.title()) + f" :{port}"
            local_html += loc_tile(label, f"http://localhost:{port}", up, is_tool)
            kw += f" {port}"
            ti = tunnels.get(port)
            if ti and ti.get("url") and ti.get("status") == "running":
                tunnel_candidates.append((role.lower(), ti["url"]))
        # One tunnel button per card. The API is already reachable via its local
        # "API" link, so when a card has both an API tunnel and a real UI/app
        # tunnel (Maia, Naya, MQ), drop the redundant API one and keep the public
        # entry point. Cards whose ONLY tunnel is the API still show that one.
        tunnel_html = ""
        if tunnel_candidates:
            non_api = [u for r, u in tunnel_candidates if r != "api"]
            tunnel_html = tun_tile(non_api[0] if non_api else tunnel_candidates[0][1])
        if not (local_html or tunnel_html):
            local_html = '<span class="desc" style="margin:0">No HTTP port</span>'
        links_html = local_html + tunnel_html + gh_tile(github)
        buckets[cname].append(card_html(name, badge, type_tag,
                                        proj.get("description") or "", path, links_html, kw, strip))

    for cname, c in EXTRA_CARDS:
        local_html, extra_html = "", ""
        kw = c["name"] + " " + cname
        for label, href, port in c.get("local", []):
            up = port_status.get(int(port), False)
            local_html += loc_tile(label, href, up, c.get("is_tool", False))
            kw += f" {port}"
        for label, href, kind in c.get("extra_links", []):
            if kind == "tunnel":
                extra_html += tun_tile(href, label)
            else:
                extra_html += f'<a href="{esc(href)}" target="_blank" rel="noopener">{esc(label)}</a>'
        links_html = local_html + extra_html + gh_tile(c.get("github", ""))
        buckets.setdefault(cname, []).append(
            card_html(c["name"], c.get("badge", ""), c.get("type_tag", "Service"),
                      c.get("desc", ""), c.get("path", ""), links_html, kw,
                      c.get("strip", "type-service")))

    # ---- Hive agents (the team behind "The Hive") ----
    AGENTS = [
        ("hive_architect", "🏗️ Architect", "Designs the plan before anyone builds — blueprints, trade-off decisions (ADRs), and a step-by-step build plan. Decides HOW, never writes the final code."),
        ("hive_builder",   "🔨 Builder",   "The hands of the Hive. Takes the Architect's plan and writes the actual code — Python, SQL, APIs, config. Gets features built and shipped."),
        ("hive_scout",     "🔍 Scout",     "The researcher. Looks up APIs, libraries, pricing and AI news, and investigates unknowns. Fast, cheap first-responder for 'how does X work?'"),
        ("hive_scribe",    "✍️ Scribe",    "The writer. Produces all documentation — session summaries, meeting minutes, version history and guides. Keeps the project's memory readable."),
        ("hive_ops",       "🛠️ Ops",       "The custodian. Watches the services, restarts what's down, reads the logs and keeps every app healthy. Operational triage for the ecosystem."),
        ("hive_inspector", "🛡️ Inspector", "The reviewer. Checks code and config for bugs, security issues and QI-standards compliance before anything ships. A read-only quality gate."),
        ("hive_tester",    "✅ Tester",    "The quality guardian. Runs API, UI and load tests across every QI project and reports what passed or failed. Cross-project regression checks."),
    ]
    for aid, aname, adesc in AGENTS:
        links_html = (f'<a class="local" href="/hive/agent/{aid}" target="_blank" rel="noopener">Profile ↗</a>'
                      f'<a class="local" href="/hive" target="_blank" rel="noopener">The Hive ↗</a>')
        kw = f"{aname} {aid} agent hive"
        buckets["Agents"].append(
            card_html(aname, "agent", "Hive Agent", adesc, f"QI Hive · {aid}", links_html, kw, "type-agent"))

    sections = ""
    for cname in order:
        cards = buckets.get(cname) or []
        if not cards:
            continue
        sections += (f'<section class="tier"><h3>{esc(cname)}</h3>'
                     f'<div class="grid">{"".join(cards)}</div></section>')

    public_live = sum(1 for t in tunnels.values() if t.get("url") and t.get("status") == "running")
    n_proj = len([p for p in projects if (p.get("id") not in HIDE)])

    err_html = ""
    if load_err:
        err_html = (f'<div style="background:#3a1d1d;border:1px solid #f85149;color:#ffb3ad;'
                    f'padding:8px 12px;border-radius:8px;margin-bottom:12px;font-size:13px">'
                    f'Registry load failed: {esc(load_err)}</div>')

    note = ('<div class="legend">'
            '<div class="item"><span class="dot up"></span> Up — port responding</div>'
            '<div class="item"><span class="dot down"></span> Down — service not responding</div>'
            '<div class="item"><span class="dot idle"></span> Idle — on-demand tool</div>'
            '<div class="item"><span class="dot paused"></span> Paused — waiting on dependency</div>'
            f'<div class="item">⛅ <strong style="color:var(--accent-2)">&nbsp;{public_live}</strong>'
            f'&nbsp;public tunnel(s) live</div>'
            '</div>')

    via_note = ""
    if via_tunnel:
        via_note = ('<div class="legend" style="color:var(--accent-2)">Viewing through a public tunnel — '
                    'use the ⛅ tunnel buttons; localhost buttons are dimmed (they point at your own device).</div>')

    css = """
#qi-lp{--bg:#0d1117;--panel:#161b22;--panel-2:#1f2630;--border:#30363d;--text:#e6edf3;--muted:#8b949e;--accent:#58a6ff;--accent-2:#f0b429;--good:#3fb950;--bad:#f85149;--idle:#6e7681;--paused:#a371f7;color:var(--text);}
[data-bs-theme=light] #qi-lp{--bg:#ffffff;--panel:#ffffff;--panel-2:#f6f8fa;--border:#d0d7de;--text:#1f2328;--muted:#57606a;--accent:#0969da;--accent-2:#9a6700;--good:#1a7f37;--bad:#cf222e;--idle:#6e7681;--paused:#8250df;}
#qi-lp *{box-sizing:border-box;}
#qi-lp .lp-head{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:12px;}
#qi-lp .lp-head h2{margin:0;font-size:20px;}
#qi-lp .lp-controls{display:flex;gap:8px;align-items:center;flex-wrap:wrap;}
#qi-lp .lp-controls input{background:var(--panel);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:7px 11px;font-size:13px;width:210px;}
#qi-lp .lp-controls button{background:var(--panel);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:7px 11px;font-size:13px;cursor:pointer;}
#qi-lp .lp-controls button:hover{border-color:var(--accent);}
#qi-lp .legend{display:flex;gap:16px;flex-wrap:wrap;font-size:12px;color:var(--muted);margin-bottom:14px;align-items:center;}
#qi-lp .legend .item{display:flex;align-items:center;gap:6px;}
#qi-lp .dot{width:10px;height:10px;border-radius:50%;display:inline-block;}
#qi-lp .dot.up{background:var(--good);}
#qi-lp .dot.down{background:var(--bad);}
#qi-lp .dot.idle{background:var(--idle);}
#qi-lp .dot.paused{background:var(--paused);}
#qi-lp .tier{margin-bottom:26px;}
#qi-lp .tier h3{font-size:12px;text-transform:uppercase;letter-spacing:1.4px;color:var(--muted);border-bottom:1px solid var(--border);padding-bottom:8px;margin:0 0 14px;}
#qi-lp .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px;}
#qi-lp .card{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:15px;display:flex;flex-direction:column;min-height:150px;transition:border-color .15s,transform .15s;}
#qi-lp .card:hover{border-color:var(--accent);transform:translateY(-2px);}
#qi-lp .card.type-service{border-left:3px solid var(--good);}
#qi-lp .card.type-tool{border-left:3px solid var(--accent-2);}
#qi-lp .card.type-paused{border-left:3px solid var(--paused);}
#qi-lp .card.type-agent{border-left:3px solid var(--paused);}
#qi-lp .head-row{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;gap:8px;}
#qi-lp .card h4{margin:0;font-size:16px;font-weight:600;}
#qi-lp .type-tag{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;font-weight:600;white-space:nowrap;}
#qi-lp .badge2{font-size:10px;font-weight:600;padding:2px 6px;border-radius:4px;background:var(--panel-2);color:var(--muted);border:1px solid var(--border);text-transform:uppercase;letter-spacing:.5px;margin-left:6px;}
#qi-lp .badge2.core{color:var(--accent-2);border-color:var(--accent-2);}
#qi-lp .badge2.backbone{color:var(--accent);border-color:var(--accent);}
#qi-lp .badge2.tool{color:var(--good);border-color:var(--good);}
#qi-lp .badge2.agent{color:var(--paused);border-color:var(--paused);}
#qi-lp .desc{color:var(--muted);font-size:12.5px;line-height:1.4;flex:1;margin-bottom:10px;}
#qi-lp .path{color:var(--muted);font-size:11px;font-family:Consolas,monospace;margin-bottom:8px;}
#qi-lp .links{display:flex;flex-wrap:wrap;gap:6px;}
#qi-lp .links a{background:var(--panel-2);color:var(--accent);text-decoration:none;border:1px solid var(--border);padding:5px 9px;border-radius:6px;font-size:12px;font-family:Consolas,monospace;display:inline-flex;align-items:center;gap:5px;}
#qi-lp .links a:hover{background:var(--accent);color:var(--bg);}
#qi-lp .links a.muted{color:var(--muted);}
#qi-lp .links a.local-dim{opacity:.45;}
#qi-lp .links a.tunnel{color:var(--accent-2);border-color:#3a3324;}
#qi-lp .links a.tunnel:hover{background:var(--accent-2);color:var(--bg);}
#qi-lp .status{width:8px;height:8px;border-radius:50%;background:var(--muted);display:inline-block;}
#qi-lp .status.up{background:var(--good);}
#qi-lp .status.down{background:var(--bad);}
#qi-lp .status.idle{background:var(--idle);}
/* Columns view = one tall flex row. Cap its height to the viewport so it
   scrolls INSIDE the box; this keeps the horizontal scrollbar pinned at the
   bottom of the visible area instead of hiding below the tallest column
   (2026-06-26). overflow-x:scroll forces the bar to always show. */
#qi-lp #qilp-content.view-columns{display:flex;gap:18px;align-items:flex-start;
  overflow-x:scroll;overflow-y:auto;max-height:calc(100vh - 210px);
  padding-bottom:6px;scrollbar-gutter:stable;}
#qi-lp #qilp-content.view-columns .tier{flex:0 0 320px;margin-bottom:0;}
#qi-lp #qilp-content.view-columns .grid{grid-template-columns:1fr;}
#qi-lp #qilp-content.view-columns .card{min-height:0;}
"""

    js = """
(function(){
  function f(){
    var q=(document.getElementById('qilp-filter').value||'').trim().toLowerCase();
    document.querySelectorAll('#qi-lp .card').forEach(function(c){
      var kw=c.getAttribute('data-keywords')||'';
      c.style.display=(!q||kw.indexOf(q)>=0)?'':'none';
    });
    document.querySelectorAll('#qi-lp .tier').forEach(function(t){
      var vis=Array.prototype.slice.call(t.querySelectorAll('.card')).some(function(c){return c.style.display!=='none';});
      t.style.display=vis?'':'none';
    });
  }
  function apply(mode){
    var c=document.getElementById('qilp-content'),b=document.getElementById('qilp-viewToggle');
    if(!c||!b)return;
    if(mode==='columns'){c.classList.add('view-columns');b.textContent='▤ Grid view';}
    else{c.classList.remove('view-columns');b.textContent='▥ Columns view';}
    try{localStorage.setItem('qiHiveLauncherView',mode);}catch(e){}
  }
  window.qilpFilter=f;
  window.qilpToggleView=function(){apply(document.getElementById('qilp-content').classList.contains('view-columns')?'grid':'columns');};
  var saved='grid';try{saved=localStorage.getItem('qiHiveLauncherView')||'grid';}catch(e){}
  apply(saved);
})();
"""

    return (f'<div id="qi-lp"><style>{css}</style>'
            f'<div class="lp-head"><h2>QI Launcher</h2>'
            f'<div class="lp-controls">'
            f'<input id="qilp-filter" placeholder="Filter by name / port…" oninput="qilpFilter()">'
            f'<button id="qilp-viewToggle" onclick="qilpToggleView()" title="Switch grid / columns">▥ Columns view</button>'
            f'<span style="color:#8b949e;font-size:12px">{n_proj} projects</span>'
            f'</div></div>'
            f'{note}{via_note}{err_html}'
            f'<div id="qilp-content">{sections}</div>'
            f'<script>{js}</script></div>')

@app.get("/launcher", response_class=HTMLResponse)
def launcher_page(request: Request):
    # Detect whether this page itself arrived via a Cloudflare tunnel, so the launcher
    # can prefer public URLs (localhost tiles are useless from a remote machine).
    h = request.headers
    via_tunnel = bool(h.get("cf-ray") or h.get("cf-connecting-ip"))
    if not via_tunnel:
        host = (h.get("host") or "").split(":")[0].lower()
        via_tunnel = host.endswith(".trycloudflare.com") or (
            host not in ("localhost", "127.0.0.1", "") and not host.startswith("192.168."))
    return base_layout("Launcher", render_launcher(via_tunnel), "launcher")

@app.get("/api/tunnels")
def api_tunnels():
    """Live aggregate of Cloudflare tunnel state across all known QI tunnels."""
    return JSONResponse({"tunnels": {str(p): v for p, v in _get_tunnels().items()}})

def render_tunnels() -> str:
    """Human-readable view of every live Cloudflare tunnel: clickable URL,
    copy-to-clipboard button, and an offline QR code (segno) for phone access."""
    import html as _html
    tunnels = _get_tunnels()

    def esc(s):
        return _html.escape(str(s if s is not None else ""))

    def qr_svg(data):
        try:
            import io as _io, base64 as _b64, segno
            buf = _io.BytesIO()
            segno.make(data, error="m").save(buf, kind="png", scale=6, border=4,
                                             dark="#000000", light="#ffffff")
            b = _b64.b64encode(buf.getvalue()).decode("ascii")
            return f'<img alt="QR code" src="data:image/png;base64,{b}">'
        except Exception:
            return ""

    live, offline = [], []
    for port, t in sorted(tunnels.items()):
        label = t.get("label") or f"Port {port}"
        url = t.get("url")
        status = (t.get("status") or "").lower()
        if url and status == "running":
            live.append((port, label, url))
        else:
            offline.append((port, label, status or "unknown"))

    cards = ""
    for port, label, url in live:
        cards += (
            '<div class="tn-card">'
            f'<div class="tn-qr">{qr_svg(url)}</div>'
            '<div class="tn-body">'
            f'<div class="tn-name">{esc(label)} <span class="tn-port">:{port}</span> '
            '<span class="tn-pill up">live</span></div>'
            f'<a class="tn-url" href="{esc(url)}" target="_blank" rel="noopener">{esc(url)}</a>'
            '<div class="tn-actions">'
            f'<button class="tn-btn" data-url="{esc(url)}" onclick="tnCopy(this)">Copy</button>'
            f'<a class="tn-btn" href="{esc(url)}" target="_blank" rel="noopener">Open ↗</a>'
            '</div>'
            '<div class="tn-updated">📱 scan the QR to open on your phone</div>'
            '</div></div>'
        )
    live_html = cards or '<div class="tn-empty">No tunnels are running right now.</div>'

    off_html = ""
    if offline:
        rows = "".join(
            f'<li>{esc(l)} <span class="tn-port">:{p}</span> — <span class="tn-off">{esc(s)}</span></li>'
            for p, l, s in offline)
        off_html = (
            f'<div class="tn-offline"><div class="tn-offline-h">Not running ({len(offline)})</div>'
            f'<ul>{rows}</ul>'
            '<div class="tn-updated">Start the matching <code>QI_&lt;App&gt;Tunnel</code> service, then refresh.</div></div>'
        )

    css = """
#qi-tn{--bg:#0d1117;--panel:#161b22;--panel-2:#1f2630;--border:#30363d;--text:#e6edf3;--muted:#8b949e;--accent:#58a6ff;--accent-2:#f0b429;--good:#3fb950;color:var(--text);}
[data-bs-theme=light] #qi-tn{--bg:#ffffff;--panel:#ffffff;--panel-2:#f6f8fa;--border:#d0d7de;--text:#1f2328;--muted:#57606a;--accent:#0969da;--accent-2:#9a6700;--good:#1a7f37;}
#qi-tn *{box-sizing:border-box;}
#qi-tn .tn-head{display:flex;align-items:baseline;gap:12px;margin-bottom:14px;flex-wrap:wrap;}
#qi-tn .tn-head h2{margin:0;font-size:20px;}
#qi-tn .tn-sub{color:var(--muted);font-size:13px;}
#qi-tn .tn-card{display:flex;gap:16px;align-items:center;background:var(--panel);border:1px solid var(--border);border-left:3px solid var(--good);border-radius:10px;padding:14px;margin-bottom:12px;}
#qi-tn .tn-qr{flex:0 0 auto;width:150px;height:150px;background:#fff;border-radius:8px;padding:8px;}
#qi-tn .tn-qr img{width:100%;height:100%;display:block;image-rendering:pixelated;}
#qi-tn .tn-body{min-width:0;flex:1;}
#qi-tn .tn-name{font-size:15px;font-weight:600;margin-bottom:6px;display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
#qi-tn .tn-port{color:var(--muted);font-family:Consolas,monospace;font-size:12px;font-weight:400;}
#qi-tn .tn-pill{font-size:10px;text-transform:uppercase;letter-spacing:.5px;padding:2px 7px;border-radius:10px;font-weight:600;}
#qi-tn .tn-pill.up{background:rgba(63,185,80,.15);color:var(--good);border:1px solid var(--good);}
#qi-tn .tn-url{display:block;color:var(--accent);font-family:Consolas,monospace;font-size:13px;word-break:break-all;text-decoration:none;margin-bottom:8px;}
#qi-tn .tn-url:hover{text-decoration:underline;}
#qi-tn .tn-actions{display:flex;gap:8px;}
#qi-tn .tn-btn{background:var(--panel-2);color:var(--accent);border:1px solid var(--border);border-radius:6px;padding:5px 12px;font-size:12px;cursor:pointer;text-decoration:none;display:inline-block;}
#qi-tn .tn-btn:hover{background:var(--accent);color:var(--bg);}
#qi-tn .tn-updated{color:var(--muted);font-size:11px;margin-top:8px;}
#qi-tn .tn-empty{color:var(--muted);padding:20px;text-align:center;background:var(--panel);border:1px solid var(--border);border-radius:10px;}
#qi-tn .tn-offline{margin-top:18px;background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:14px;}
#qi-tn .tn-offline-h{font-size:12px;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-bottom:8px;}
#qi-tn .tn-offline ul{margin:0;padding-left:18px;}
#qi-tn .tn-offline li{font-size:13px;margin-bottom:4px;}
#qi-tn .tn-off{color:var(--accent-2);}
#qi-tn code{color:#94a3b8;}
"""
    js = """
function tnCopy(btn){
  var u=btn.getAttribute('data-url');
  function done(){var o=btn.textContent;btn.textContent='Copied!';setTimeout(function(){btn.textContent=o;},1200);}
  function fb(){var t=document.createElement('textarea');t.value=u;document.body.appendChild(t);t.select();try{document.execCommand('copy');}catch(e){}document.body.removeChild(t);done();}
  if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(u).then(done,fb);}else{fb();}
}
"""
    return ('<div id="qi-tn"><style>' + css + '</style>'
            '<div class="tn-head"><h2>Public Tunnels</h2>'
            f'<span class="tn-sub">{len(live)} live · scan a QR to open on your phone</span></div>'
            + live_html + off_html
            + '<script>' + js + '</script></div>')

EFFORT_DB = Path(r"C:\QIH\data\effort\effort_ledger.db")
EFFORT_ENGINE = Path(r"C:\QIH\engine\effort")


def render_effort() -> str:
    """Effort Ledger summary. Degrades to a notice if the ledger is absent --
    this page must never take the dashboard down."""
    if not EFFORT_DB.exists():
        return ('<div class="alert alert-warning">Effort ledger not found at '
                f'<code>{EFFORT_DB}</code>. Run '
                '<code>python qi_effort_ledger.py --backfill</code>.</div>')
    try:
        import sqlite3
        import sys as _sys
        if str(EFFORT_ENGINE) not in _sys.path:
            _sys.path.insert(0, str(EFFORT_ENGINE))
        from qi_effort_ledger import (union_buckets, governance,
                                      MIXED_PROVENANCE, verify_chain)
        con = sqlite3.connect(f"file:{EFFORT_DB}?mode=ro", uri=True)

        u = union_buckets(con)
        tot = u["_total"] / 60.0
        bus = u.get("business", 0) / 60.0
        off = (u.get("after_hours", 0) + u.get("early_morning", 0)
               + u.get("weekend", 0) + u.get("holiday", 0)) / 60.0
        ux = union_buckets(con, exclude=MIXED_PROVENANCE)
        xt = ux["_total"] / 60.0
        xo = (ux.get("after_hours", 0) + ux.get("early_morning", 0)
              + ux.get("weekend", 0) + ux.get("holiday", 0)) / 60.0

        rng = con.execute(
            "SELECT MIN(day_local), MAX(day_local) FROM events").fetchone()
        tk = con.execute(
            "SELECT SUM(tok_out), SUM(cost_usd) FROM events").fetchone()
        seal = con.execute("SELECT day_local, hash, created_at FROM ledger "
                           "ORDER BY seq DESC LIMIT 1").fetchone()
        ok, chain_msg = verify_chain(con)

        per = con.execute("""
            SELECT project, SUM(minutes)/60.0, SUM(min_business)/60.0,
                   (SUM(min_after_hours)+SUM(min_early_morning)
                    +SUM(min_weekend)+SUM(min_holiday))/60.0
            FROM sessions GROUP BY project ORDER BY 2 DESC""").fetchall()
        con.close()
    except Exception as exc:                      # never break the dashboard
        return ('<div class="alert alert-danger">Effort ledger unavailable: '
                f'{html.escape(str(exc))}</div>')

    def card(label, value, sub, colour):
        return f"""<div class="col-md-3">
          <div class="card border-{colour} h-100"><div class="card-body">
            <div class="text-muted small text-uppercase">{label}</div>
            <div class="display-6 fw-bold">{value}</div>
            <div class="small text-muted">{sub}</div>
          </div></div></div>"""

    pct = (off / tot * 100) if tot else 0
    cards = ('<div class="row g-3 mb-4">'
             + card("Elapsed hours", f"{tot:.1f}",
                    f"{rng[0]} → {rng[1]}", "secondary")
             + card("Business hours", f"{bus:.1f}",
                    "weekdays 08:00–17:30", "info")
             + card("Off-hours", f"{off:.1f}",
                    "evenings · weekends · holidays", "success")
             + card("Off-hours share", f"{pct:.1f}%",
                    f"{xo / xt * 100 if xt else 0:.1f}% excl. mixed", "success")
             + '</div>')

    roll = {}
    for p, t, b, o in per:
        a = roll.setdefault(governance(p), [0.0, 0.0, 0.0, 0])
        a[0] += t
        a[1] += b
        a[2] += o
        a[3] += 1
    badge = {"Shared with BU": "warning", "Mixed provenance": "danger",
             "Personal": "success", "Employer work": "secondary"}
    grows = ""
    for g in ["Shared with BU", "Mixed provenance", "Personal",
              "Employer work"]:
        if g not in roll:
            continue
        a = roll[g]
        grows += (f'<tr><td><span class="badge text-bg-{badge[g]}">{g}</span>'
                  f'</td><td>{a[3]}</td><td>{a[0]:.1f}</td><td>{a[1]:.1f}</td>'
                  f'<td>{a[2]:.1f}</td>'
                  f'<td>{(a[2] / a[0] * 100) if a[0] else 0:.0f}%</td></tr>')

    prows = ""
    for p, t, b, o in per:
        if t < 0.25:
            continue
        g = governance(p)
        prows += (f'<tr><td>{html.escape(p)}</td>'
                  f'<td><span class="badge text-bg-{badge[g]}">{g}</span></td>'
                  f'<td>{t:.1f}</td><td>{b:.1f}</td><td>{o:.1f}</td>'
                  f'<td>{(o / t * 100) if t else 0:.0f}%</td></tr>')

    chain_cls = "success" if ok else "danger"
    seal_html = (f'sealed {seal[0]} · <code>{seal[1][:16]}…</code> · '
                 f'{seal[2]}' if seal else 'no ledger entries yet')

    return f"""
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h4 class="mb-0"><i class="bi bi-stopwatch"></i> Effort Ledger</h4>
      <span class="badge text-bg-{chain_cls}">chain: {html.escape(chain_msg)}</span>
    </div>
    <p class="text-muted small">Elapsed hours count concurrent work on several
    projects once. Per-project hours below are attributed and therefore sum to
    more than elapsed time. Governance values are owner-declared.</p>
    {cards}
    <div class="card mb-4"><div class="card-header">Governance roll-up</div>
      <table class="table table-sm mb-0">
        <thead><tr><th>Governance</th><th>Projects</th><th>Attributed h</th>
        <th>Business h</th><th>Off-hours h</th><th>Off %</th></tr></thead>
        <tbody>{grows}</tbody></table></div>
    <div class="card mb-4"><div class="card-header">By project</div>
      <div style="max-height:520px;overflow:auto">
      <table class="table table-sm table-striped mb-0">
        <thead class="sticky-top bg-light"><tr><th>Project</th>
        <th>Governance</th><th>Attributed h</th><th>Business h</th>
        <th>Off-hours h</th><th>Off %</th></tr></thead>
        <tbody>{prows}</tbody></table></div></div>
    <div class="row g-3">
      <div class="col-md-6"><div class="card h-100"><div class="card-body">
        <h6>Compute</h6>
        <div>{(tk[0] or 0):,} tokens generated</div>
        <div class="text-muted small">US${(tk[1] or 0):,.2f} replacement cost
        at list rates — not an amount paid</div>
      </div></div></div>
      <div class="col-md-6"><div class="card h-100"><div class="card-body">
        <h6>Latest sealed entry</h6>
        <div class="small">{seal_html}</div>
        <div class="text-muted small mt-2">Collected nightly 23:50 by
        QI_EffortLedger_Daily</div>
      </div></div></div>
    </div>"""


@app.get("/effort", response_class=HTMLResponse)
def effort_page():
    return base_layout("Effort Ledger", render_effort(), "effort")


@app.get("/api/effort")
def api_effort():
    if not EFFORT_DB.exists():
        return JSONResponse({"available": False}, status_code=503)
    try:
        import sqlite3
        import sys as _sys
        if str(EFFORT_ENGINE) not in _sys.path:
            _sys.path.insert(0, str(EFFORT_ENGINE))
        from qi_effort_ledger import union_buckets, verify_chain
        con = sqlite3.connect(f"file:{EFFORT_DB}?mode=ro", uri=True)
        u = union_buckets(con)
        ok, msg = verify_chain(con)
        con.close()
        tot = u["_total"] / 60.0
        off = (u.get("after_hours", 0) + u.get("early_morning", 0)
               + u.get("weekend", 0) + u.get("holiday", 0)) / 60.0
        return JSONResponse({
            "available": True,
            "elapsed_hours": round(tot, 1),
            "business_hours": round(u.get("business", 0) / 60.0, 1),
            "off_hours": round(off, 1),
            "off_hours_pct": round(off / tot * 100, 1) if tot else 0,
            "chain_ok": ok, "chain": msg,
        })
    except Exception as exc:
        return JSONResponse({"available": False, "error": str(exc)},
                            status_code=500)


@app.get("/tunnels", response_class=HTMLResponse)
def tunnels_page():
    return base_layout("Tunnels", render_tunnels(), "tunnels")

@app.get("/hive", response_class=HTMLResponse)
def hive_page():
    return base_layout("The Hive", render_hive(), "hive")

@app.get("/hive/agent/{agent_id}", response_class=HTMLResponse)
def hive_agent_page(agent_id: str):
    return base_layout(f"Agent: {agent_id}", render_agent_profile(agent_id), "hive")

@app.get("/api/brain/agents")
def api_brain_agents():
    return JSONResponse({"agents": get_agents(), "brain_online": brain_online()})

@app.get("/api/brain/status")
def api_brain_status():
    return JSONResponse({"brain_online": brain_online(), **get_brain_status()})

@app.get("/health")
def health_page(request: Request):
    """Content-negotiated: browsers get HTML, monitors/API clients get JSON.
    QI validator uses Accept: application/json or curl default → JSON probe."""
    accept = (request.headers.get("accept") or "").lower()
    wants_html = "text/html" in accept and "application/json" not in accept
    if wants_html:
        return HTMLResponse(base_layout("Health Check", render_health(), "health"))
    # JSON probe
    return JSONResponse({
        "status":  "ok",
        "service": "qi_hive",
        "port":    8600,
        "version": "3.0.0",
    })

@app.get("/board", response_class=HTMLResponse)
def board_page(project: str = "All"):
    return base_layout("Task Board", render_board(project), "board")

GUIDE_FILE = Path(r"C:\QIH\ecosystem\QI_Claude_Manager_Guide.md")

@app.get("/guide", response_class=HTMLResponse)
def guide_page():
    md_text = GUIDE_FILE.read_text(encoding="utf-8") if GUIDE_FILE.exists() else "# Guide not found"
    # Escape for JS string embedding
    md_escaped = md_text.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
    content = f"""
    <div class="row">
      <div class="col-12">
        <div class="card">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h3 class="card-title"><i class="bi bi-book me-2"></i>QI Claude Manager — Cheatsheet</h3>
            <a href="/api/guide/raw" class="btn btn-sm btn-outline-secondary">
              <i class="bi bi-download me-1"></i>Raw .md
            </a>
          </div>
          <div class="card-body" id="guide-content" style="font-size:.92rem;line-height:1.7"></div>
        </div>
      </div>
    </div>
    <link rel="stylesheet" href="/static/vendor/github-markdown-dark.min.css"/>
    <style>
      .markdown-body {{ background:transparent!important; color:inherit!important; }}
      .markdown-body table {{ width:100%; }}
      .markdown-body pre {{ background:#0d1117; border-radius:6px; padding:16px; }}
      .markdown-body h1,.markdown-body h2 {{ border-bottom:1px solid #30363d; padding-bottom:.3em; }}
      .markdown-body h1 {{ font-size:1.6rem; }}
      .markdown-body h2 {{ font-size:1.25rem; margin-top:1.5rem; }}
      .markdown-body h3 {{ font-size:1rem; color:#58a6ff; }}
    </style>
    <script src="/static/vendor/marked.min.js"></script>
    <script>
      document.getElementById('guide-content').innerHTML =
        '<div class="markdown-body p-2">' + marked.parse(`{md_escaped}`) + '</div>';
    </script>"""
    return base_layout("Guide", content, "guide")


@app.get("/api/guide/raw")
def api_guide_raw():
    text = GUIDE_FILE.read_text(encoding="utf-8") if GUIDE_FILE.exists() else "# Guide not found"
    return Response(content=text, media_type="text/plain")


# ── Documentation Library (Documentation Brain — Stage 1: search tile) ──────────

@app.get("/api/library/facets")
def api_library_facets():
    """Index health + filter facets, read straight from qi_brain.db docs catalog."""
    stats = _brain_db_query(
        "SELECT COUNT(*) n, COALESCE(SUM(embedded),0) emb, COALESCE(SUM(stale),0) stale FROM docs")
    edges = _brain_db_query("SELECT COUNT(*) n FROM doc_relationships")
    projects = _brain_db_query(
        "SELECT COALESCE(project_id,'(none)') id, COUNT(*) n FROM docs "
        "GROUP BY id ORDER BY n DESC")
    types = _brain_db_query(
        "SELECT COALESCE(doc_type,'other') t, COUNT(*) n FROM docs "
        "GROUP BY t ORDER BY n DESC")
    s = stats[0] if stats else {}
    return {
        "total":    s.get("n", 0),
        "embedded": s.get("emb", 0),
        "stale":    s.get("stale", 0),
        "edges":    (edges[0]["n"] if edges else 0),
        "projects": projects,
        "types":    types,
    }


@app.get("/api/library/search")
def api_library_search(q: str = "", project: str = "", doc_type: str = "",
                       stale: int = 0, limit: int = 30):
    """Search the Documentation Brain.

    With a query: semantic search via the Brain API (collection=docs), enriched
    from the catalog. Falls back to keyword LIKE if the Brain API is offline.
    Without a query: most-recently-modified docs. Project/type/stale filter on top.
    """
    q = (q or "").strip()
    rows: list[dict] = []
    mode = "recent"

    if q:
        try:
            import urllib.request, json as _j
            body = _j.dumps({"query": q, "collection": "docs",
                             "n": max(limit * 2, 40)}).encode("utf-8")
            req = urllib.request.Request(
                # 127.0.0.1, not "localhost" — see _get_project_llms: an IPv6
                # loopback attempt stalls for the full timeout (8s here).
                "http://127.0.0.1:9011/api/search_memory", data=body,
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=8) as r:
                data = _j.loads(r.read().decode("utf-8"))
            ids = [x["id"] for x in data.get("results", [])]
            dist = {x["id"]: x.get("distance") for x in data.get("results", [])}
            if ids:
                ph = ",".join("?" * len(ids))
                cmap = {c["doc_id"]: c for c in
                        _brain_db_query(f"SELECT * FROM docs WHERE doc_id IN ({ph})", tuple(ids))}
                for i in ids:                     # preserve similarity ranking
                    c = cmap.get(i)
                    if c:
                        c = dict(c)
                        c["distance"] = dist.get(i)
                        rows.append(c)
                mode = "semantic"
            # title-boost: docs whose title/filename contain every query word
            # always rank first, so a doc is findable by its own name even when
            # the semantic embedding of a large/table-heavy file ranks poorly
            import re as _re
            words = [w for w in _re.split(r"[^a-zA-Z0-9]+", q) if len(w) >= 3][:6]
            clauses = " AND ".join("(title LIKE ? OR path LIKE ?)" for _ in words)
            params = tuple(x for w in words for x in (f"%{w}%", f"%{w}%"))
            tb = _brain_db_query(
                f"SELECT * FROM docs WHERE {clauses} AND stale=0 "
                "ORDER BY mtime DESC LIMIT 10", params) if words else []
            seen = {r["doc_id"] for r in rows}
            boosted = [dict(r) for r in tb if r["doc_id"] not in seen]
            if boosted:
                rows = boosted + rows
                mode = "semantic+title"
        except Exception:
            rows = []
        if not rows:                              # Brain API down → keyword fallback
            like = f"%{q}%"
            rows = _brain_db_query(
                "SELECT * FROM docs WHERE title LIKE ? OR path LIKE ? "
                "ORDER BY mtime DESC LIMIT 200", (like, like))
            mode = "keyword"
    else:
        rows = _brain_db_query("SELECT * FROM docs ORDER BY mtime DESC LIMIT 300")

    def keep(r: dict) -> bool:
        if project and (r.get("project_id") or "") != project:
            return False
        if doc_type and (r.get("doc_type") or "") != doc_type:
            return False
        if stale and not r.get("stale"):
            return False
        return True

    rows = [r for r in rows if keep(r)][:limit]
    return {"ok": True, "mode": mode, "count": len(rows), "results": rows}


@app.get("/api/library/graph")
def api_library_graph(node: str = "root:qi"):
    """Return the neighbourhood of one node — the TheBrain 'Plex'. Clicking a node
    re-centers by re-querying this with that node. Sources both doc_relationships
    edges and the natural foreign keys in decisions/features/session_log."""
    try:
        ntype, nid = node.split(":", 1)
    except ValueError:
        ntype, nid = "root", "qi"

    nodes: dict[str, dict] = {}
    links: list[dict] = []

    def add(_id, label, _type, sub="", path=""):
        nodes[_id] = {"id": _id, "label": label, "type": _type, "sub": sub, "path": path}

    def link(a, b, lbl):
        links.append({"from": a, "to": b, "label": lbl})

    if ntype == "root":
        add("root:qi", "QI Ecosystem", "root", "click a project")
        for p in _brain_db_query(
                "SELECT COALESCE(project_id,'(none)') id, COUNT(*) n FROM docs "
                "GROUP BY id ORDER BY n DESC LIMIT 24"):
            add(f"project:{p['id']}", p["id"], "project", f"{p['n']} docs")
            link("root:qi", f"project:{p['id']}", "project")

    elif ntype == "project":
        add(f"project:{nid}", nid, "project")
        add("root:qi", "QI Ecosystem", "root")
        link("root:qi", f"project:{nid}", "project")
        for r in _brain_db_query("SELECT doc_id, title, path, doc_type FROM docs "
                                 "WHERE project_id=? ORDER BY mtime DESC LIMIT 14", (nid,)):
            add(f"doc:{r['doc_id']}", (r["title"] or "(untitled)")[:38], "doc",
                r.get("doc_type") or "", r.get("path") or "")
            link(f"project:{nid}", f"doc:{r['doc_id']}", "has")
        for r in _brain_db_query("SELECT decision_id, title FROM decisions "
                                 "WHERE project_id=? AND superseded_by IS NULL "
                                 "ORDER BY recorded_at DESC LIMIT 8", (nid,)):
            add(f"decision:{r['decision_id']}", (r["title"] or "decision")[:38], "decision")
            link(f"project:{nid}", f"decision:{r['decision_id']}", "decided")
        for r in _brain_db_query("SELECT feature_id, name FROM features "
                                 "WHERE source_project=? ORDER BY recorded_at DESC LIMIT 8", (nid,)):
            add(f"feature:{r['feature_id']}", (r["name"] or "feature")[:38], "feature")
            link(f"project:{nid}", f"feature:{r['feature_id']}", "implements")
        for r in _brain_db_query("SELECT session_id, session_title FROM session_log "
                                 "WHERE project_id=? ORDER BY ended_at DESC LIMIT 8", (nid,)):
            add(f"session:{r['session_id']}", (r["session_title"] or "session")[:38], "session")
            link(f"project:{nid}", f"session:{r['session_id']}", "produced")

    elif ntype == "doc":
        d = _brain_db_query("SELECT doc_id, title, project_id, path, doc_type "
                            "FROM docs WHERE doc_id=?", (nid,))
        if d:
            d = d[0]
            add(f"doc:{nid}", (d["title"] or "(untitled)")[:48], "doc",
                d.get("doc_type") or "", d.get("path") or "")
            if d.get("project_id"):
                add(f"project:{d['project_id']}", d["project_id"], "project")
                link(f"project:{d['project_id']}", f"doc:{nid}", "has")
                for r in _brain_db_query("SELECT doc_id, title, path FROM docs WHERE project_id=? "
                                         "AND doc_id<>? ORDER BY mtime DESC LIMIT 6",
                                         (d["project_id"], nid)):
                    add(f"doc:{r['doc_id']}", (r["title"] or "(untitled)")[:34], "doc",
                        "", r.get("path") or "")
                    link(f"project:{d['project_id']}", f"doc:{r['doc_id']}", "has")
            for r in _brain_db_query("SELECT dst_id FROM doc_relationships WHERE src_type='doc' "
                                     "AND src_id=? AND edge_type='mentions' AND dst_type='project'", (nid,)):
                add(f"project:{r['dst_id']}", r["dst_id"], "project")
                link(f"doc:{nid}", f"project:{r['dst_id']}", "mentions")

    elif ntype in ("decision", "feature", "session"):
        spec = {"decision": ("decisions", "decision_id", "title", "project_id"),
                "feature":  ("features", "feature_id", "name", "source_project"),
                "session":  ("session_log", "session_id", "session_title", "project_id")}[ntype]
        r = _brain_db_query(
            f"SELECT {spec[1]} id, {spec[2]} label, {spec[3]} pid FROM {spec[0]} WHERE {spec[1]}=?", (nid,))
        if r:
            r = r[0]
            add(f"{ntype}:{nid}", (r["label"] or ntype)[:48], ntype)
            if r.get("pid"):
                add(f"project:{r['pid']}", r["pid"], "project")
                link(f"project:{r['pid']}", f"{ntype}:{nid}", ntype)

    return {"focus": node, "nodes": list(nodes.values()), "links": links}


# ── Documentation Library — file actions (open / reveal / download) ─────────────
# These act on the HOST machine, and the dashboard is reachable via the public
# tunnel, so they are gated to LOCAL requests only: anything arriving through the
# Cloudflare tunnel carries forwarding headers and is refused. Paths are resolved
# from the docs catalog by doc_id (never trusted from the client) and limited to a
# safe extension allowlist.
_DOC_OPEN_EXT = {".md", ".docx", ".doc", ".pdf", ".txt", ".pptx", ".xlsx", ".csv", ".rtf"}


def _request_is_local(request: Request) -> bool:
    if (request.headers.get("x-forwarded-for") or request.headers.get("cf-connecting-ip")
            or request.headers.get("cf-ray") or request.headers.get("x-forwarded-host")):
        return False
    host = request.client.host if request.client else ""
    return host in ("127.0.0.1", "::1", "localhost")


def _doc_path_by_id(doc_id: str):
    rows = _brain_db_query("SELECT path FROM docs WHERE doc_id=?", (doc_id,))
    return rows[0]["path"] if rows else None


@app.post("/api/library/open")
def api_library_open(request: Request, doc_id: str = ""):
    if not _request_is_local(request):
        raise HTTPException(403, "Opening files is allowed only from the local machine.")
    path = _doc_path_by_id(doc_id)
    if not path:
        raise HTTPException(404, "Unknown document.")
    p = Path(path)
    if p.suffix.lower() not in _DOC_OPEN_EXT or not p.exists():
        raise HTTPException(400, "Document is not openable or no longer exists.")
    try:
        import os
        os.startfile(str(p))  # open in the OS default application
        return {"ok": True, "opened": str(p)}
    except Exception as e:
        raise HTTPException(500, f"Could not open: {e}")


@app.post("/api/library/reveal")
def api_library_reveal(request: Request, doc_id: str = ""):
    if not _request_is_local(request):
        raise HTTPException(403, "Reveal is allowed only from the local machine.")
    path = _doc_path_by_id(doc_id)
    if not path or not Path(path).exists():
        raise HTTPException(404, "Document not found.")
    try:
        subprocess.Popen(["explorer", "/select,", str(Path(path))])
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, f"Could not reveal: {e}")


@app.get("/api/library/file")
def api_library_file(request: Request, doc_id: str = ""):
    if not _request_is_local(request):
        raise HTTPException(403, "Download is allowed only from the local machine.")
    path = _doc_path_by_id(doc_id)
    if not path or not Path(path).exists():
        raise HTTPException(404, "Document not found.")
    from fastapi.responses import FileResponse
    return FileResponse(path, filename=Path(path).name)


@app.get("/library", response_class=HTMLResponse)
def library_page():
    content = """
    <div class="row mb-2"><div class="col-12 d-flex align-items-center flex-wrap gap-2">
      <div class="btn-group" role="group">
        <button id="lt-search" class="btn btn-sm btn-primary"><i class="bi bi-search me-1"></i>Search</button>
        <button id="lt-graph" class="btn btn-sm btn-outline-primary"><i class="bi bi-diagram-3 me-1"></i>Graph (Plex)</button>
        <button id="lt-split" class="btn btn-sm btn-outline-primary"><i class="bi bi-layout-split me-1"></i>Split</button>
        <button id="lt-status" class="btn btn-sm btn-outline-primary"><i class="bi bi-clipboard-data me-1"></i>Project Status</button>
      </div>
      <span id="lib-stats" class="small text-muted ms-2">loading index&hellip;</span>
    </div></div>

    <div id="v-search">
      <div class="card mb-3"><div class="card-body">
        <div class="row g-2 align-items-end">
          <div class="col-md-5"><label class="form-label small mb-1">Search</label>
            <input id="s-q" class="form-control" placeholder="e.g. NEXUS digest spec, elevation broker, dispatch queue&hellip;" autocomplete="off"></div>
          <div class="col-md-3"><label class="form-label small mb-1">Project</label>
            <select id="s-project" class="form-select"><option value="">All projects</option></select></div>
          <div class="col-md-2"><label class="form-label small mb-1">Type</label>
            <select id="s-type" class="form-select"><option value="">All types</option></select></div>
          <div class="col-md-2 d-grid"><button id="s-go" class="btn btn-primary"><i class="bi bi-search me-1"></i>Search</button></div>
        </div>
        <div class="form-check mt-2"><input class="form-check-input" type="checkbox" id="s-stale"><label class="form-check-label small" for="s-stale">Only stale docs</label></div>
      </div></div>
      <div class="card"><div class="card-body">
        <div id="s-mode" class="small text-muted mb-2"></div>
        <div id="s-results"></div>
      </div></div>
    </div>

    <div id="v-status" style="display:none">
      <div class="card mb-3"><div class="card-body">
        <div class="row g-2 align-items-end">
          <div class="col-md-5"><label class="form-label small mb-1">Project / Product</label>
            <select id="ps-project" class="form-select"><!--PS_OPTIONS--></select></div>
          <div class="col-md-4"><div class="small text-muted">Published documentation for every QI project &mdash; Overview, Blueprint, Feature Status (Business &amp; Dev), Code Explained, Future, Tech Stack &amp; Docs &mdash; in one place.</div></div>
          <div class="col-md-3 d-grid"><a id="ps-open" class="btn btn-outline-primary" target="_blank" href="/project/maia/status"><i class="bi bi-box-arrow-up-right me-1"></i>Open full page</a></div>
        </div>
      </div></div>
      <div class="card mb-3"><div class="card-body p-2">
        <iframe id="ps-frame" title="Project Status" src="about:blank" style="width:100%;height:80vh;border:0;border-radius:6px;background:var(--bs-body-bg)"></iframe>
      </div></div>
      <div class="card"><div class="card-header"><i class="bi bi-grid-3x3-gap me-1"></i>All projects &amp; products</div>
        <div class="card-body"><div class="row g-2"><!--PS_CARDS--></div></div>
      </div>
    </div>

    <div id="v-graph" style="display:none">
      <div class="card"><div class="card-body">
        <div class="d-flex justify-content-between align-items-center mb-2 flex-wrap gap-2">
          <div class="d-flex align-items-center gap-2" style="min-width:0">
            <i class="bi bi-diagram-3 text-secondary"></i>
            <nav id="g-crumb" class="plex-crumb" aria-label="Plex trail"><span class="crumb-link current">QI Ecosystem</span></nav>
          </div>
          <div class="small text-muted">Click a node to inspect &middot; double-click or <kbd>E</kbd> to expand &middot; drag to rearrange</div>
        </div>
        <div id="g-plex" style="height:72vh"></div>
      </div></div>
    </div>

    <style>
      .lib-split{display:flex;align-items:stretch;width:100%}
      .lib-split .lib-pane{min-width:240px;overflow:hidden}
      .lib-split #sp-left{flex:0 0 40%}
      .lib-split #sp-right{flex:1 1 auto}
      #sp-gutter{flex:0 0 14px;cursor:col-resize;display:flex;align-items:center;justify-content:center;user-select:none}
      #sp-gutter .lib-grip{width:4px;height:48px;border-radius:3px;background:var(--bs-border-color,#888);opacity:.55;transition:opacity .12s,background .12s}
      #sp-gutter:hover .lib-grip,#sp-gutter.dragging .lib-grip{opacity:1;background:var(--bs-primary,#3b82f6)}
      @media (max-width:820px){
        .lib-split{flex-direction:column}
        .lib-split #sp-left,.lib-split #sp-right{flex:1 1 auto !important;width:100%}
        #sp-gutter{display:none}
      }
    </style>
    <div id="v-split" style="display:none">
      <div id="sp-split" class="lib-split">
        <div id="sp-left" class="lib-pane">
          <div class="card h-100"><div class="card-body">
            <div class="input-group input-group-sm mb-2">
              <input id="sp-q" class="form-control" placeholder="Search docs&hellip;" autocomplete="off">
              <button id="sp-go" class="btn btn-primary"><i class="bi bi-search"></i></button>
            </div>
            <div class="d-flex gap-2 mb-2">
              <select id="sp-project" class="form-select form-select-sm"><option value="">All projects</option></select>
              <select id="sp-type" class="form-select form-select-sm"><option value="">All types</option></select>
            </div>
            <div id="sp-results" style="max-height:64vh;overflow:auto"></div>
          </div></div>
        </div>
        <div id="sp-gutter" title="Drag to resize"><div class="lib-grip"></div></div>
        <div id="sp-right" class="lib-pane">
          <div class="card h-100"><div class="card-body">
            <div class="d-flex align-items-center mb-2 flex-wrap gap-2" style="min-width:0">
              <i class="bi bi-diagram-3 text-secondary"></i>
              <nav id="sp-crumb" class="plex-crumb" aria-label="Plex trail"><span class="crumb-link current">QI Ecosystem</span></nav>
            </div>
            <div id="sp-plex" style="height:64vh"></div>
            <div class="small text-muted mt-2">List &rarr; graph: click a result to center it. Graph &rarr; list: selecting a project filters, selecting a doc highlights. Drag the divider to resize.</div>
          </div></div>
        </div>
      </div>
    </div>

    <script>
    (function(){
      const $ = id => document.getElementById(id);
      const esc = s => (s||'').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
      const badge = (t,c) => '<span class="badge '+(c||'text-bg-secondary')+'">'+esc(t)+'</span>';
      const sim = d => { if(d==null) return ''; const v=Math.max(0,Math.round((1-d)*100));
        const c=v>=70?'text-bg-success':(v>=50?'text-bg-info':'text-bg-secondary'); return '<span class="badge '+c+'">'+v+'%</span>'; };
      const api = {
        facets: () => fetch('/api/library/facets').then(r=>r.json()),
        search: p => fetch('/api/library/search?'+new URLSearchParams(p)).then(r=>r.json()),
        graph:  id => fetch('/api/library/graph?node='+encodeURIComponent(id)).then(r=>r.json())
      };

      function renderList(el, data, opts){
        opts = opts || {};
        if(!data.results.length){ el.innerHTML='<div class="text-muted py-3">No documents match.</div>'; return; }
        let h='<table class="table table-sm table-hover align-middle mb-0"><tbody>';
        data.results.forEach(r => {
          const stale = r.stale ? ' <span class="badge text-bg-warning" title="'+esc(r.stale_reason||'stale')+'">stale</span>' : '';
          h += '<tr data-doc="'+esc(r.doc_id)+'" style="cursor:pointer">'+
            '<td><div class="fw-semibold" style="font-size:13px">'+esc(r.title||'(untitled)')+stale+'</div>'+
            '<div class="text-muted" style="font-size:11px">'+badge(r.project_id||'\\u2014','text-bg-primary')+' '+badge(r.doc_type||'other')+(r.distance!=null?' '+sim(r.distance):'')+'</div>'+
            (opts.path ? '<div class="text-muted text-truncate" style="font-size:11px;max-width:560px">'+esc(r.path)+'</div>' : '')+
            '</td>'+
            (opts.copy ? '<td class="text-end"><button class="btn btn-sm btn-outline-secondary lib-copy" data-p="'+esc(r.path)+'" title="Copy path"><i class="bi bi-clipboard"></i></button></td>' : '')+
            '</tr>';
        });
        h += '</tbody></table>';
        el.innerHTML = h;
        el.querySelectorAll('.lib-copy').forEach(b => b.addEventListener('click', e => {
          e.stopPropagation(); navigator.clipboard.writeText(b.dataset.p);
          const i=b.querySelector('i'); i.className='bi bi-check2'; setTimeout(()=>i.className='bi bi-clipboard',1200);
        }));
        if(opts.onRow){
          el.querySelectorAll('tr[data-doc]').forEach(tr => tr.addEventListener('click', () => {
            el.querySelectorAll('tr.table-active').forEach(x=>x.classList.remove('table-active'));
            tr.classList.add('table-active');
            opts.onRow(data.results.find(x => x.doc_id===tr.getAttribute('data-doc')));
          }));
        }
      }

      /* The Plex is drawn by /static/js/qi-plex.js (D3 v7) — see that file for
         the visual grammar. Both scripts are fetched on first use only; the
         Library page costs nothing extra until someone opens the Graph tab. */
      let plexLoading=false, plexQ=[];
      function loadPlex(cb){
        if(window.QIPlex && window.d3){ cb(true); return; }
        plexQ.push(cb);
        if(plexLoading) return; plexLoading=true;
        const one = src => new Promise((res,rej)=>{ const s=document.createElement('script');
          s.src=src; s.onload=res; s.onerror=rej; document.head.appendChild(s); });
        one('/static/vendor/d3.v7.min.js')
          .then(()=>one('/static/js/qi-plex.js'))
          .then(()=>{ plexQ.forEach(f=>f(true)); plexQ=[]; })
          .catch(()=>{ plexQ.forEach(f=>f(false)); plexQ=[]; });
      }
      /* Trail of re-centres, so drilling three projects deep is reversible. */
      function renderCrumb(el, trail, go){
        if(!el) return;
        if(!trail || !trail.length){ el.innerHTML='<span class="crumb-link current">QI Ecosystem</span>'; return; }
        el.innerHTML = trail.map((t,i)=>{
          const last = i===trail.length-1;
          return '<button type="button" class="crumb-link'+(last?' current':'')+'" data-i="'+i+'"'+
                 (last?' aria-current="page"':'')+'>'+esc(t.label)+'</button>'+
                 (last?'':'<span class="crumb-sep" aria-hidden="true">/</span>');
        }).join('');
        el.querySelectorAll('button[data-i]').forEach(b=>b.addEventListener('click',()=>{
          const t=trail[+b.dataset.i]; if(t) go(t.id);
        }));
      }
      function toast(msg, kind){
        let t=document.getElementById('plex-toast');
        if(!t){ t=document.createElement('div'); t.id='plex-toast';
          t.style.cssText='position:fixed;bottom:18px;right:18px;z-index:3100;padding:10px 14px;border-radius:8px;font-size:13px;color:#fff;box-shadow:0 6px 24px rgba(0,0,0,.3);display:none';
          document.body.appendChild(t); }
        t.style.background = kind==='danger' ? 'var(--bs-danger,#b02a37)' : 'var(--bs-success,#198754)';
        t.textContent=msg; t.style.display='block';
        clearTimeout(t._h); t._h=setTimeout(()=>{ t.style.display='none'; }, 2800);
      }
      function copyText(t){ navigator.clipboard.writeText(t); toast('Copied to clipboard.','success'); }
      async function openDoc(docId){
        try{ const r=await fetch('/api/library/open?doc_id='+encodeURIComponent(docId),{method:'POST'});
          if(r.ok){ toast('Opened in default app.','success'); }
          else { const j=await r.json().catch(()=>({})); toast(j.detail||'Could not open (local machine only).','danger'); }
        }catch(e){ toast('Open failed.','danger'); }
      }
      async function revealDoc(docId){
        try{ const r=await fetch('/api/library/reveal?doc_id='+encodeURIComponent(docId),{method:'POST'});
          if(!r.ok){ const j=await r.json().catch(()=>({})); toast(j.detail||'Reveal is local only.','danger'); }
        }catch(e){ toast('Reveal failed.','danger'); }
      }
      function downloadDoc(docId){ window.open('/api/library/file?doc_id='+encodeURIComponent(docId),'_blank'); }
      function plexMenu(){
        let m=document.getElementById('plex-menu');
        if(!m){ m=document.createElement('div'); m.id='plex-menu';
          m.style.cssText='position:fixed;z-index:3050;display:none;min-width:190px;background:var(--bs-body-bg,#1f1f1f);border:1px solid var(--bs-border-color,#444);border-radius:8px;padding:4px;box-shadow:0 8px 28px rgba(0,0,0,.35);font-size:13px';
          document.body.appendChild(m);
          document.addEventListener('click',()=>{ m.style.display='none'; });
          window.addEventListener('blur',()=>{ m.style.display='none'; });
        }
        return m;
      }
      function showMenu(x,y,items){
        const m=plexMenu(); m.innerHTML='';
        items.forEach(it=>{ const d=document.createElement('div');
          d.innerHTML='<i class="bi '+it.icon+' me-2"></i>'+it.label;
          d.style.cssText='padding:7px 11px;border-radius:6px;cursor:pointer;white-space:nowrap;color:var(--bs-body-color,#e6e6e6)';
          d.onmouseenter=()=>d.style.background='var(--bs-tertiary-bg,#333)';
          d.onmouseleave=()=>d.style.background='';
          d.onclick=e=>{ e.stopPropagation(); m.style.display='none'; it.fn(); };
          m.appendChild(d);
        });
        m.style.left=Math.min(x, window.innerWidth-210)+'px';
        m.style.top=Math.min(y, window.innerHeight-40-items.length*36)+'px';
        m.style.display='block';
      }
      function makeGraph(container, crumbEl, onSelect){
        const inst = QIPlex.create(container, {
          rootId: 'root:qi',
          fetchGraph: id => api.graph(id),
          onSelect: n => { if(n && onSelect) onSelect(n.id, n); },
          onTrail: trail => renderCrumb(crumbEl, trail, id => inst.recenter(id)),
          /* The inspector rail covers these too — the menu stays for anyone
             who already has the right-click habit. */
          onContextMenu: (ev, d) => {
            const rest=d.id.split(':').slice(1).join(':'), items=[];
            if(d.type==='doc'){
              items.push({label:'Open document',icon:'bi-box-arrow-up-right',fn:()=>openDoc(rest)});
              items.push({label:'Reveal in folder',icon:'bi-folder2-open',fn:()=>revealDoc(rest)});
              items.push({label:'Download',icon:'bi-download',fn:()=>downloadDoc(rest)});
              if(d.path) items.push({label:'Copy path',icon:'bi-clipboard',fn:()=>copyText(d.path)});
            } else {
              items.push({label:'Copy id',icon:'bi-clipboard',fn:()=>copyText(rest)});
            }
            items.push({label:'Expand here',icon:'bi-bullseye',fn:()=>inst.recenter(d.id)});
            showMenu(ev.clientX, ev.clientY, items);
          },
          actions: {
            open:     id => openDoc(id),
            reveal:   id => revealDoc(id),
            download: id => downloadDoc(id),
            copy:     p  => copyText(p)
          }
        });
        return inst;
      }

      async function loadFacets(){
        try{
          const f=await api.facets();
          $('lib-stats').innerHTML='<i class="bi bi-files me-1"></i>'+f.total+' docs &middot; '+
            '<i class="bi bi-cpu me-1"></i>'+f.embedded+' embedded &middot; '+
            '<i class="bi bi-diagram-3 me-1"></i>'+f.edges+' edges &middot; '+
            '<span class="text-warning">'+f.stale+' stale</span>';
          [['s-project','projects','id'],['sp-project','projects','id'],['s-type','types','t'],['sp-type','types','t']].forEach(spec=>{
            const el=$(spec[0]); (f[spec[1]]||[]).forEach(o=>{ const op=document.createElement('option');
              op.value=o[spec[2]]; op.textContent=o[spec[2]]+' ('+o.n+')'; el.appendChild(op); });
          });
        }catch(e){ $('lib-stats').textContent='index unavailable'; }
      }

      async function searchMain(){
        $('s-results').innerHTML='<div class="text-muted py-3"><span class="spinner-border spinner-border-sm me-2"></span>Searching&hellip;</div>';
        const d=await api.search({q:$('s-q').value,project:$('s-project').value,doc_type:$('s-type').value,stale:$('s-stale').checked?1:0,limit:40});
        $('s-mode').innerHTML='Mode: '+badge(d.mode,'text-bg-dark')+' &middot; '+d.count+' result'+(d.count===1?'':'s');
        renderList($('s-results'), d, {path:true, copy:true});
      }
      $('s-go').addEventListener('click', searchMain);
      $('s-q').addEventListener('keydown', e => { if(e.key==='Enter') searchMain(); });
      ['s-project','s-type','s-stale'].forEach(id => $(id).addEventListener('change', searchMain));

      let mainGraph=null;
      function initGraph(){
        if(mainGraph) return;
        loadPlex(ok => { if(!ok){ $('g-plex').innerHTML='<div class="text-danger p-3">Could not load the graph library (offline?).</div>'; return; }
          mainGraph=makeGraph($('g-plex'), $('g-crumb'), null);
          mainGraph.home();
        });
      }

      let splitGraph=null, splitInited=false;
      async function splitSearch(){
        const d=await api.search({q:$('sp-q').value,project:$('sp-project').value,doc_type:$('sp-type').value,limit:40});
        renderList($('sp-results'), d, {onRow:r => { if(splitGraph) splitGraph.recenter('doc:'+r.doc_id); }});
      }
      function highlightDoc(docId){
        const tr=$('sp-results').querySelector('tr[data-doc="'+(window.CSS&&CSS.escape?CSS.escape(docId):docId)+'"]');
        if(tr){ $('sp-results').querySelectorAll('tr.table-active').forEach(x=>x.classList.remove('table-active'));
          tr.classList.add('table-active'); tr.scrollIntoView({block:'nearest'}); }
      }
      function initSplit(){
        if(splitInited) return; splitInited=true;
        loadPlex(ok => { if(!ok){ $('sp-plex').innerHTML='<div class="text-danger p-3">Could not load the graph library (offline?).</div>'; return; }
          splitGraph=makeGraph($('sp-plex'), $('sp-crumb'), (id, n) => {
            const rest=id.split(':').slice(1).join(':');
            if(n.type==='project'){ $('sp-project').value=rest; splitSearch(); }
            else if(n.type==='doc'){ highlightDoc(rest); }
          });
          splitGraph.home();
        });
        splitSearch();
      }
      $('sp-go').addEventListener('click', splitSearch);
      $('sp-q').addEventListener('keydown', e => { if(e.key==='Enter') splitSearch(); });
      ['sp-project','sp-type'].forEach(id => $(id).addEventListener('change', splitSearch));

      (function(){
        const split=$('sp-split'), left=$('sp-left'), gutter=$('sp-gutter');
        if(!split || !gutter || !left) return;
        const KEY='qi_lib_split_w';
        const saved=localStorage.getItem(KEY); if(saved) left.style.flexBasis=saved;
        let dragging=false;
        function move(clientX){
          const r=split.getBoundingClientRect();
          let pct=((clientX - r.left)/r.width)*100;
          pct=Math.max(20, Math.min(78, pct));
          left.style.flexBasis=pct.toFixed(1)+'%';
        }
        function start(e){ dragging=true; gutter.classList.add('dragging'); document.body.style.cursor='col-resize';
          document.body.style.userSelect='none'; e.preventDefault();
          window.addEventListener('mousemove', onMouse); window.addEventListener('mouseup', stop);
          window.addEventListener('touchmove', onTouch, {passive:false}); window.addEventListener('touchend', stop); }
        function onMouse(e){ if(dragging) move(e.clientX); }
        function onTouch(e){ if(dragging && e.touches[0]){ e.preventDefault(); move(e.touches[0].clientX); } }
        function stop(){ if(!dragging) return; dragging=false; gutter.classList.remove('dragging');
          document.body.style.cursor=''; document.body.style.userSelect='';
          localStorage.setItem(KEY, left.style.flexBasis);
          window.removeEventListener('mousemove', onMouse); window.removeEventListener('mouseup', stop);
          window.removeEventListener('touchmove', onTouch); window.removeEventListener('touchend', stop); }
        gutter.addEventListener('mousedown', start);
        gutter.addEventListener('touchstart', start, {passive:false});
        gutter.addEventListener('dblclick', () => { left.style.flexBasis='40%'; localStorage.setItem(KEY,'40%'); });
      })();

      function selPS(pid){
        var f=$('ps-frame'); if(f) f.src='/project/'+pid+'/status?embed=1';
        var o=$('ps-open'); if(o) o.href='/project/'+pid+'/status';
        var sel=$('ps-project'); if(sel && sel.value!==pid) sel.value=pid;
      }
      window.selPS=selPS;
      let psInited=false;
      function initStatus(){ if(psInited) return; psInited=true;
        var sel=$('ps-project'); selPS(sel && sel.value ? sel.value : 'maia'); }
      (function(){ var sel=$('ps-project'); if(sel) sel.addEventListener('change', function(){ selPS(sel.value); }); })();
      const TABS=[['lt-search','v-search',null,()=>null],['lt-graph','v-graph',initGraph,()=>mainGraph],['lt-split','v-split',initSplit,()=>splitGraph],['lt-status','v-status',initStatus,()=>null]];
      function show(active){
        TABS.forEach(t => { $(t[1]).style.display=(t[0]===active)?'':'none';
          $(t[0]).className='btn btn-sm '+(t[0]===active?'btn-primary':'btn-outline-primary'); });
      }
      TABS.forEach(t => $(t[0]).addEventListener('click', () => {
        show(t[0]); if(t[2]) t[2]();
        const g=t[3](); if(g&&g.resize) setTimeout(()=>{ try{ g.resize(); }catch(e){} }, 90);
      }));

      loadFacets(); searchMain();
    })();
    </script>"""
    # Project Status hub — server-render the dropdown + project grid from the
    # same project list the per-project status pages use.
    _ps = _ps_list()
    _opts, _cards = [], []
    for p in _ps:
        sel = " selected" if p["pid"] == "maia" else ""
        _opts.append(f"<option value='{p['pid']}'{sel}>{html.escape(p['name'])}</option>")
        badge = ("<span class='badge bg-success'>ready</span>" if p["ready"]
                 else "<span class='badge bg-secondary'>empty</span>")
        _cards.append(
            f"<div class='col-sm-6 col-md-4 col-lg-3'>"
            f"<a href='#' onclick=\"selPS('{p['pid']}');return false;\" "
            f"class='d-block text-decoration-none border rounded p-2 h-100'>"
            f"<div class='fw-semibold text-body'>{html.escape(p['name'])}</div>"
            f"<div class='small mt-1'>{badge}</div></a></div>"
        )
    content = content.replace("<!--PS_OPTIONS-->", "".join(_opts))
    content = content.replace("<!--PS_CARDS-->", "".join(_cards))
    return base_layout("Library", content, "library")


# ── API: Status ───────────────────────────────────────────────────────────────

@app.get("/api/status")
def api_status():
    return JSONResponse(load_status())

@app.get("/api/ping")
def api_ping():
    return JSONResponse({
        "pong": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": app.version,
    })

@app.get("/version")
def api_version():
    """Simple version probe — QI ecosystem standard."""
    return JSONResponse({"service": "qi_hive", "version": app.version, "build": "2026-04-20"})

@app.get("/info")
def api_info():
    """Full service metadata — capabilities, endpoints, runtime."""
    import sys, platform
    return JSONResponse({
        "service":         "qi_hive",
        "version":         app.version,
        "build":           "2026-04-20",
        "port":            8600,
        "python":          sys.version.split()[0],
        "platform":        platform.system(),
        "capabilities":    ["dashboard", "task_board", "services", "brain_ui",
                            "mission_control", "warroom_chat", "cowork_dispatch",
                            "themes", "scheduled_tasks"],
        "endpoints_total": len([r for r in app.routes if hasattr(r, "path")]),
        "docs_url":        "/docs",
    })

@app.get("/api/scout/digest")
def api_scout_digest():
    """Fetch AI news digest from NEXUS and return top items."""
    import urllib.request, json as _json
    try:
        with urllib.request.urlopen("http://127.0.0.1:8010/scout/digest", timeout=10) as resp:
            data = _json.loads(resp.read().decode())
        # Parse the markdown to extract first 5 headlines
        content = data.get("content_md", "")
        items = []
        for line in content.splitlines():
            if line.startswith("### ["):
                title_end = line.index("](")
                url_end = line.index(")", title_end)
                title = line[5:title_end]
                url = line[title_end + 2:url_end]
                items.append({"title": title, "url": url})
                if len(items) >= 5:
                    break
        return JSONResponse({
            "ok": True,
            "date": data.get("date"),
            "item_count": data.get("item_count", 0),
            "top_5": items,
        })
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=503)

@app.get("/api/agents")
def api_agents():
    # Serve the authoritative Brain-backed roster. This used to return
    # load_agents(), which reads a legacy folder that has not existed since the
    # UNIVERSAL->QIH migration — so the endpoint served {} while /api/brain/agents
    # returned all 15 agents. Legacy folder configs, if ever restored, are merged
    # in as enrichment only. (2026-08-17 audit.)
    agents = get_agents()
    legacy = load_agents()
    if legacy:
        by_id = {str(a.get("agent_id", "")).lower(): a for a in agents}
        for name, cfg in legacy.items():
            target = by_id.get(name.lower())
            if target:
                for k, v in (cfg or {}).items():
                    target.setdefault(k, v)
    return JSONResponse({"agents": agents, "brain_online": brain_online()})

@app.get("/api/health")
def api_health():
    # Serve cached data and never recompute or sync on the request path. This
    # endpoint used to call run_health_check() + sync_tasks() inline; with a cold
    # cache that fan-out exceeded 30s and the request simply timed out.
    # _board_sync_loop() (every 300s) owns both the refresh and the board sync.
    # (2026-08-17 audit.)
    from health_check import cached_health_check
    data = cached_health_check()
    if data is not None:
        return JSONResponse(data)
    # Cold cache — the dashboard restarted and _board_sync_loop()'s first pass
    # (~45s of service/git probes) has not finished. Never block a request on it:
    # warm in the background and tell the caller we're still warming, so the page
    # can render a placeholder instead of hanging until the client times out.
    _warm_health_async()
    return JSONResponse({}, headers={"X-QI-Health": "warming"})


_health_warm_started = False


def _warm_health_async():
    """Kick off one background health computation; subsequent calls are no-ops."""
    import threading
    global _health_warm_started
    if _health_warm_started:
        return
    _health_warm_started = True

    def _run():
        global _health_warm_started
        try:
            sync_tasks(run_health_check())
        except Exception as e:
            log.warning("health warm failed: %s", e)
        finally:
            _health_warm_started = False

    threading.Thread(target=_run, daemon=True, name="qi-health-warm").start()

# ── API: Tasks ────────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    project: Optional[str] = "General"
    agent: Optional[str] = "builder"
    priority: Optional[str] = "medium"

class TaskUpdate(BaseModel):
    column:      Optional[str] = None
    title:       Optional[str] = None
    description: Optional[str] = None
    project:     Optional[str] = None
    agent:       Optional[str] = None
    priority:    Optional[str] = None

@app.get("/api/tasks")
def api_get_tasks():
    return JSONResponse({"tasks": load_tasks()})

@app.post("/api/tasks")
def api_create_task(task: TaskCreate):
    tasks = load_tasks()
    new_task = {
        "id": "t" + uuid.uuid4().hex[:6],
        "title": task.title,
        "description": task.description,
        "project": task.project,
        "agent": task.agent,
        "priority": task.priority,
        "column": "backlog",
        "created_at": datetime.now().strftime("%Y-%m-%d"),
    }
    tasks.append(new_task)
    save_tasks(tasks)
    return JSONResponse(new_task)

@app.patch("/api/tasks/{task_id}")
def api_update_task(task_id: str, update: TaskUpdate):
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            if update.column      is not None: t["column"]      = update.column
            if update.title       is not None: t["title"]       = update.title
            if update.description is not None: t["description"] = update.description
            if update.project     is not None: t["project"]     = update.project
            if update.agent       is not None: t["agent"]       = update.agent
            if update.priority    is not None: t["priority"]    = update.priority
            save_tasks(tasks)
            return JSONResponse(t)
    raise HTTPException(404, "Task not found")

@app.delete("/api/tasks/{task_id}")
def api_delete_task(task_id: str):
    tasks = load_tasks()
    tasks = [t for t in tasks if t["id"] != task_id]
    save_tasks(tasks)
    return JSONResponse({"ok": True})

# ── Background board sync ─────────────────────────────────────────────────────

import asyncio as _asyncio

async def _board_sync_loop():
    while True:
        try:
            from health_check import run_health_check, sync_tasks as _sync_tasks
            await _asyncio.to_thread(lambda: _sync_tasks(run_health_check()))
        except Exception as e:
            log.warning("board sync loop error: %s", e)
        await _asyncio.sleep(300)  # 5 minutes

async def _usage_cache_warm_loop():
    """Keep usage_stats' 30s event cache hot so no visitor pays to rebuild it.

    usage_stats._iter_events() re-parses ~33k jsonl events (~1.9s) whenever its
    30s TTL lapses. Since people arrive at the dashboard more than 30s apart,
    the first request after an idle gap was paying that rebuild — the root page
    measured ~2.3s cold vs ~0.2s warm. Refreshing on a timer instead of on read
    moves the cost off the request path without making the numbers any staler:
    the cache is module-level, so this shares it with every request handler.
    """
    while True:
        try:
            await _asyncio.to_thread(lambda: usage_stats._iter_events(force=True))
        except Exception as e:
            log.warning("usage cache warm loop error: %s", e)
        await _asyncio.sleep(25)   # under usage_stats._TTL (30s) so it never expires

@app.on_event("startup")
async def _start_board_sync():
    # The board sync used to run synchronously here so it would be fresh within
    # seconds of a restart. But run_health_check() probes every QI service, and
    # blocking on it delayed the uvicorn bind by ~47s — the whole dashboard was
    # down for that long on every restart. _board_sync_loop()'s first iteration
    # already performs exactly this sync, on a thread, with no leading sleep, so
    # the board is still fresh within moments of startup; it just no longer
    # holds the port hostage while it waits on other services.
    _asyncio.create_task(_board_sync_loop())
    _asyncio.create_task(_usage_cache_warm_loop())
    # War Room responder — agents actually reply (via NEXUS local LLM, not Claude).
    try:
        from engine.common.qi_warroom_responder import start_in_thread as _wr_start
        _wr_start()
        log.info("war room responder thread started")
    except Exception as e:
        log.warning("war room responder failed to start: %s", e)
    # War Room -> Telegram outbound relay (mirrors the room to Renne's DM via Tasuke).
    try:
        from engine.common.qi_warroom_telegram import start_in_thread as _wrtg_start
        _wrtg_start()
        log.info("war room telegram relay thread started")
    except Exception as e:
        log.warning("war room telegram relay failed to start: %s", e)

# ── Tests Page ───────────────────────────────────────────────────────────────

TESTS_RESULTS = Path(r"C:\Claude\Tests\results\latest.json")
TESTS_RUNNER  = Path(r"C:\Claude\Tests\run_tests.py")

HIVE_CONFIG        = _PROJECT_DIR / "data" / "hive_config.json"
_EF_WORKTREE       = Path(r"C:\APPS\EasyFlow\tester_builds\beta_unpacked")
EASYFLOW_MANIFEST  = _EF_WORKTREE / "manifest.json"
EASYFLOW_TESTS_DIR = _EF_WORKTREE / "tests"


def _load_hive_config() -> dict:
    return load_json(HIVE_CONFIG)

def _save_hive_config(data: dict):
    save_json(HIVE_CONFIG, data)

def render_tests() -> str:
    # Load latest results if available
    summary_html = ""
    detail_html  = ""
    last_run     = "Never"

    if TESTS_RESULTS.exists():
        try:
            with open(TESTS_RESULTS, encoding="utf-8") as f:
                results = json.load(f)

            # Try to get timestamp from file mtime
            import os
            mtime = os.path.getmtime(TESTS_RESULTS)
            last_run = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")

            summary = results.get("summary", {})
            passed  = summary.get("passed", 0)
            failed  = summary.get("failed", 0)
            skipped = summary.get("skipped", 0)
            total   = summary.get("total", passed + failed + skipped)

            if total != passed + failed + skipped:
                log.warning(
                    "tests total mismatch: %d != %d+%d+%d",
                    total, passed, failed, skipped,
                )

            p_pct = round((passed / total * 100) if total else 0)
            f_color = "danger" if failed else "success"

            summary_html = f"""
            <div class="row mb-3">
              <div class="col-md-3">
                <div class="small-box text-bg-success">
                  <div class="inner"><h3>{passed}</h3><p>Passed</p></div>
                  <i class="small-box-icon bi bi-check-circle-fill"></i>
                </div>
              </div>
              <div class="col-md-3">
                <div class="small-box text-bg-{f_color}">
                  <div class="inner"><h3>{failed}</h3><p>Failed</p></div>
                  <i class="small-box-icon bi bi-x-circle-fill"></i>
                </div>
              </div>
              <div class="col-md-3">
                <div class="small-box text-bg-secondary">
                  <div class="inner"><h3>{skipped}</h3><p>Skipped</p></div>
                  <i class="small-box-icon bi bi-skip-forward-fill"></i>
                </div>
              </div>
              <div class="col-md-3">
                <div class="small-box text-bg-info">
                  <div class="inner"><h3>{p_pct}%</h3><p>Pass Rate</p></div>
                  <i class="small-box-icon bi bi-graph-up"></i>
                </div>
              </div>
            </div>"""

            test_rows = ""
            outcome_map = {
                "passed":  '<span class="badge text-bg-success">passed</span>',
                "failed":  '<span class="badge text-bg-danger">failed</span>',
                "skipped": '<span class="badge text-bg-secondary">skipped</span>',
            }
            for t in results.get("tests", []):
                outcome = t.get("outcome", "unknown")
                badge   = outcome_map.get(outcome, f'<span class="badge text-bg-secondary">{outcome}</span>')
                node    = t.get("nodeid", "—")
                # Get duration
                dur = t.get("call", {}).get("duration", None)
                dur_str = f"{dur:.3f}s" if dur else "—"
                # Error message for failures
                err = ""
                if outcome == "failed":
                    crash = t.get("call", {}).get("crash", {})
                    msg = (crash.get("message") or "")[:120]
                    err = f'<br><small class="text-danger">{msg}</small>'

                test_rows += f"""<tr>
                  <td><small><code>{node}</code>{err}</small></td>
                  <td>{badge}</td>
                  <td><small>{dur_str}</small></td>
                </tr>"""

            detail_html = f"""
            <div class="card mt-3">
              <div class="card-header"><h3 class="card-title">Test Results</h3></div>
              <div class="card-body p-0">
                <table class="table table-sm table-hover mb-0">
                  <thead class="table-dark"><tr><th>Test</th><th>Result</th><th>Duration</th></tr></thead>
                  <tbody>{test_rows}</tbody>
                </table>
              </div>
            </div>"""

        except Exception as e:
            summary_html = f'<div class="alert alert-warning">Could not parse results: {e}</div>'

    no_results_msg = "" if TESTS_RESULTS.exists() else """
    <div class="callout callout-info mb-3">
      <h5><i class="bi bi-info-circle me-2"></i>No test results yet</h5>
      <p class="mb-0">Click <strong>Run Smoke Tests</strong> to run the quick health check, or <strong>Run All Tests</strong> for the full suite.</p>
    </div>"""

    return f"""
    <div class="row mb-3">
      <div class="col-12 d-flex justify-content-between align-items-center flex-wrap gap-2">
        <span class="text-muted"><i class="bi bi-clock me-1"></i>Last run: <strong>{last_run}</strong></span>
        <div class="d-flex gap-2">
          <button class="btn btn-sm btn-outline-info" onclick="runTests('smoke')" id="btn-smoke">
            <i class="bi bi-lightning-charge me-1"></i>Smoke Tests
          </button>
          <button class="btn btn-sm btn-outline-warning" onclick="runTests('api')" id="btn-api">
            <i class="bi bi-hdd-network me-1"></i>API Tests
          </button>
          <button class="btn btn-sm btn-outline-secondary" onclick="runTests('ui')" id="btn-ui">
            <i class="bi bi-display me-1"></i>UI Tests
          </button>
          <button class="btn btn-sm btn-primary" onclick="runTests('all')" id="btn-all">
            <i class="bi bi-play-fill me-1"></i>Run All
          </button>
        </div>
      </div>
    </div>

    {no_results_msg}
    {summary_html}
    {detail_html}

    <div id="run-status" class="mt-3" style="display:none">
      <div class="alert alert-info d-flex align-items-center gap-2">
        <div class="spinner-border spinner-border-sm" role="status"></div>
        <span id="run-status-msg">Running tests...</span>
      </div>
    </div>

    <script>
    function runTests(suite) {{
      document.getElementById('run-status').style.display = 'block';
      document.getElementById('run-status-msg').textContent = 'Running ' + suite + ' tests... (this may take 30–60s)';
      ['smoke','api','ui','all'].forEach(s => {{
        const b = document.getElementById('btn-' + s);
        if (b) b.disabled = true;
      }});

      fetch('/api/tests/run?suite=' + suite, {{method: 'POST'}})
        .then(r => r.json())
        .then(data => {{
          document.getElementById('run-status-msg').textContent =
            '✅ Done! ' + data.passed + ' passed, ' + data.failed + ' failed. Refreshing...';
          setTimeout(() => location.reload(), 1500);
        }})
        .catch(err => {{
          document.getElementById('run-status-msg').textContent = '❌ Error: ' + err;
          ['smoke','api','ui','all'].forEach(s => {{
            const b = document.getElementById('btn-' + s);
            if (b) b.disabled = false;
          }});
        }});
    }}
    setInterval(() => {{
      if (document.visibilityState === 'visible') location.reload();
    }}, 30000);
    </script>"""


def render_easyflow_card() -> str:
    """EasyFlow Chrome extension test launcher card."""
    # Read version from manifest (name uses __MSG__ locale key — just use "EasyFlow")
    ef_version = "—"
    if EASYFLOW_MANIFEST.exists():
        try:
            mf = json.loads(EASYFLOW_MANIFEST.read_text(encoding="utf-8"))
            ef_version = mf.get("version", "—")
        except Exception:
            pass

    # Load persisted extension ID
    cfg = _load_hive_config()
    saved_ext_id = cfg.get("easyflow_extension_id", "")

    # Build test-script copy rows
    script_rows = ""
    for script_name in ("v12_feature_test.js", "regression_test.js"):
        sp = EASYFLOW_TESTS_DIR / script_name
        display_path = str(sp).replace("\\", "\\\\")
        label = "Feature Tests v1.2" if "v12" in script_name else "Regression Tests"
        exists_badge = '<span class="badge text-bg-success ms-1">found</span>' if sp.exists() else '<span class="badge text-bg-danger ms-1">missing</span>'
        script_rows += f"""
          <tr>
            <td><small>{label}{exists_badge}</small></td>
            <td><small><code id="path-{script_name}">{display_path}</code></small></td>
            <td>
              <button class="btn btn-xs btn-outline-secondary py-0 px-1"
                      onclick="copyPath('{script_name}')">
                <i class="bi bi-clipboard"></i>
              </button>
            </td>
          </tr>"""

    return f"""
    <hr class="my-4"/>
    <div class="row mb-2">
      <div class="col-12">
        <h5 class="text-muted text-uppercase" style="font-size:.75rem;letter-spacing:.08em;">
          <i class="bi bi-puzzle me-1"></i>Chrome Extension — EasyFlow
        </h5>
      </div>
    </div>
    <div class="card">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h3 class="card-title mb-0">
          <i class="bi bi-envelope-open me-2"></i>EasyFlow
          <span class="badge text-bg-secondary ms-2">v{ef_version}</span>
        </h3>
        <span class="text-muted" style="font-size:.8rem;">
          Unpacked extension — ID changes on each Chrome reload
        </span>
      </div>
      <div class="card-body">

        <!-- Extension ID input -->
        <div class="row g-2 align-items-end mb-3">
          <div class="col">
            <label class="form-label mb-1" style="font-size:.8rem;">Extension ID</label>
            <input type="text" id="ef-ext-id" class="form-control form-control-sm font-monospace"
                   placeholder="e.g. abcdefghijklmnopqrstuvwxyzabcdef"
                   value="{saved_ext_id}"/>
          </div>
          <div class="col-auto">
            <button class="btn btn-sm btn-outline-primary" onclick="saveExtId()">
              <i class="bi bi-floppy me-1"></i>Save ID
            </button>
          </div>
        </div>
        <div id="ef-save-msg" class="small text-success mb-3" style="display:none">
          <i class="bi bi-check-circle me-1"></i>Extension ID saved.
        </div>

        <!-- Action buttons -->
        <div class="d-flex flex-wrap gap-2 mb-4">
          <button class="btn btn-sm btn-primary" onclick="openEfPage('tests/automated_runner.html')">
            <i class="bi bi-play-circle me-1"></i>Open Test Runner
          </button>
          <button class="btn btn-sm btn-outline-secondary" onclick="openEfPage('options/options.html')">
            <i class="bi bi-gear me-1"></i>Open Options Page
          </button>
        </div>

        <!-- Test script references -->
        <div class="card card-secondary card-outline">
          <div class="card-header py-2">
            <h3 class="card-title" style="font-size:.8rem;">Manual Test Scripts</h3>
          </div>
          <div class="card-body p-0">
            <table class="table table-sm mb-0">
              <tbody>{script_rows}</tbody>
            </table>
          </div>
        </div>

      </div>
    </div>

    <script>
    function getExtId() {{
      return document.getElementById('ef-ext-id').value.trim();
    }}
    function openEfPage(page) {{
      const id = getExtId();
      if (!id) {{ alert('Enter the Extension ID first.'); return; }}
      window.open('chrome-extension://' + id + '/' + page, '_blank');
    }}
    function saveExtId() {{
      const id = getExtId();
      fetch('/api/easyflow/config', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{extension_id: id}})
      }}).then(r => r.json()).then(() => {{
        const msg = document.getElementById('ef-save-msg');
        msg.style.display = 'block';
        setTimeout(() => msg.style.display = 'none', 3000);
      }});
    }}
    function copyPath(filename) {{
      const el = document.getElementById('path-' + filename);
      navigator.clipboard.writeText(el.textContent).then(() => {{
        el.style.color = '#198754';
        setTimeout(() => el.style.color = '', 1500);
      }});
    }}
    </script>"""


# ── API: Tests ────────────────────────────────────────────────────────────────

import subprocess as _subprocess

@app.post("/api/tests/run")
def api_run_tests(suite: str = "all"):
    """Run the pytest suite in a subprocess and return summary."""
    if not TESTS_RUNNER.exists():
        raise HTTPException(404, "Test runner not found at C:\\Claude\\Tests\\run_tests.py")

    proc = _subprocess.run(
        [sys.executable, str(TESTS_RUNNER), suite],
        capture_output=True, text=True, timeout=300,
        encoding="utf-8", errors="replace"
    )

    # Read latest results
    if TESTS_RESULTS.exists():
        with open(TESTS_RESULTS, encoding="utf-8") as f:
            results = json.load(f)
        summary = results.get("summary", {})
        return JSONResponse({
            "ok":      True,
            "suite":   suite,
            "passed":  summary.get("passed", 0),
            "failed":  summary.get("failed", 0),
            "skipped": summary.get("skipped", 0),
            "stdout":  proc.stdout[-2000:],
        })

    return JSONResponse({"ok": False, "stdout": proc.stdout[-2000:], "stderr": proc.stderr[-1000:]})


@app.get("/tests", response_class=HTMLResponse)
def tests_page():
    return base_layout("Tests", render_tests() + render_easyflow_card(), "tests")


@app.get("/api/easyflow/config")
def get_easyflow_config():
    cfg = _load_hive_config()
    return JSONResponse({"extension_id": cfg.get("easyflow_extension_id", "")})


@app.post("/api/easyflow/config")
async def save_easyflow_config(request: Request):
    body = await request.json()
    cfg  = _load_hive_config()
    cfg["easyflow_extension_id"] = body.get("extension_id", "")
    _save_hive_config(cfg)
    return JSONResponse({"ok": True})


# ── /config — log level management ────────────────────────────────────────────

LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# gsudo preset definitions — used by both render and apply endpoint
GSUDO_PRESETS = {
    "loose":  {
        "CacheMode": "Auto", "CacheDuration": "Infinite",
        "SecurityEnforceUacIsolation": "False", "LogLevel": "Warning",
        "label": "Loose", "color": "success",
        "description": "Auto cache, never expires — trust this project completely",
    },
    "normal": {
        "CacheMode": "Auto", "CacheDuration": "00:08:00",
        "SecurityEnforceUacIsolation": "False", "LogLevel": "Info",
        "label": "Normal", "color": "primary",
        "description": "Auto cache, 8-minute idle timeout — standard development",
    },
    "strict": {
        "CacheMode": "Explicit", "CacheDuration": "00:02:00",
        "SecurityEnforceUacIsolation": "True", "LogLevel": "Info",
        "label": "Strict", "color": "warning",
        "description": "Manual cache start only, 2-minute timeout, input isolation",
    },
    "locked": {
        "CacheMode": "Disabled", "CacheDuration": "00:00:30",
        "SecurityEnforceUacIsolation": "True", "LogLevel": "Info",
        "label": "Locked", "color": "danger",
        "description": "Always prompt — no caching, maximum security",
    },
}

QI_PROJECTS = [
    ("maia",         "Maia"),
    ("naya",         "Naya"),
    ("nexus",        "NEXUS"),
    ("openclaw",     "OpenClaw"),
    ("mq",           "MQ"),
    ("easyflow",     "EasyFlow"),
    ("qi_hive",      "QI Hive"),
    ("qi_brain",     "QI Brain"),
    ("universal",    "QI-Universal"),
    ("cognibase",    "CogniBase"),
    ("mapsnap",      "MapSnap"),
    ("autopdf",      "AutoPDF"),
    ("personalsong", "PersonalSong Studio"),
    ("m2v",          "M2V"),
    ("lotterywiz",   "LotteryWiz"),
    ("cypherminer",  "CypherMiner"),
    ("digitization", "Digitization Cost Tool"),
    ("fidelityanalyzer", "Fidelity Portfolio Analyzer"),
    ("avatarstudio", "AvatarStudio"),
    ("tubescout", "TubeScout"),
    ("claude_manager", "Claude Manager"),
]


def render_log_config() -> str:
    """Logging level control — rendered inside the Logs page."""
    cfg = list_services()
    rows = []
    for name, svc in cfg["services"].items():
        current = svc.get("level", cfg["default_level"]).upper()
        opts = "".join(
            f'<option value="{lvl}" {"selected" if lvl == current else ""}>{lvl}</option>'
            for lvl in LOG_LEVELS
        )
        rows.append(f"""
          <tr>
            <td><code>{name}</code></td>
            <td><small class="text-muted">{svc.get('file','(default)')}</small></td>
            <td>
              <select class="form-select form-select-sm" data-service="{name}"
                      onchange="setLevel(this)">{opts}</select>
            </td>
          </tr>
        """)

    table_body = "\n".join(rows) if rows else '<tr><td colspan="3" class="text-muted">No services configured</td></tr>'

    return f"""
    <hr class="my-4"/>
    <div class="card">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h5 class="mb-0"><i class="bi bi-sliders"></i> Log Level Configuration</h5>
        <span class="badge bg-secondary">Default: {cfg['default_level']}</span>
      </div>
      <div class="card-body">
        <p class="text-muted small mb-3">
          Adjust log verbosity per service. Changes persist to
          <code>config/logging.json</code> and apply immediately to this
          Dashboard process. Other services pick up changes on next restart.
        </p>
        <table class="table table-sm table-hover align-middle">
          <thead>
            <tr><th>Service</th><th>Log file</th><th style="width:180px">Level</th></tr>
          </thead>
          <tbody>{table_body}</tbody>
        </table>
        <div id="log-config-toast" class="text-success small"></div>
      </div>
    </div>
    <script>
    async function setLevel(sel) {{
      const service = sel.dataset.service;
      const level = sel.value;
      const r = await fetch('/api/config/logging/level', {{
        method: 'POST',
        headers: {{'Content-Type':'application/json'}},
        body: JSON.stringify({{service, level}})
      }});
      const j = await r.json();
      const toast = document.getElementById('log-config-toast');
      toast.textContent = j.ok ? `✓ ${{service}} → ${{level}}` : `✗ Failed`;
      setTimeout(() => toast.textContent = '', 3000);
    }}
    </script>
    """


def _get_gsudo_settings() -> dict:
    """Read current gsudo config — no elevation required."""
    import subprocess as _sp
    try:
        out = _sp.run(
            [r"C:\Program Files\gsudo\Current\gsudo.exe", "config"],
            capture_output=True, text=True, timeout=10
        ).stdout
        settings = {}
        for line in out.splitlines():
            if "=" in line and not line.startswith("#"):
                key, _, rest = line.partition("=")
                val = rest.strip().split()[0].strip('"')
                settings[key.strip()] = val
        return settings
    except Exception as e:
        return {"_error": str(e)}


def render_gsudo_config() -> str:
    """gsudo configuration card for the Config page."""
    s = _get_gsudo_settings()
    err_html = f'<div class="alert alert-warning">Could not read gsudo config: {s["_error"]}</div>' if "_error" in s else ""

    def sel(setting, options):
        current = s.get(setting, "")
        opts = "".join(
            f'<option value="{o}" {"selected" if o == current else ""}>{o}</option>'
            for o in options
        )
        return f'<select class="form-select form-select-sm" id="gs-{setting}" onchange="setSetting(\'{setting}\', this.value)">{opts}</select>'

    cache_dur = s.get("CacheDuration", "")
    isolation = s.get("SecurityEnforceUacIsolation", "False")
    nw_force  = s.get("NewWindow.Force", "False")

    isolation_checked = "checked" if isolation == "True" else ""
    nw_checked        = "checked" if nw_force  == "True" else ""

    # Detect which preset currently matches live settings
    def _matches(preset_key):
        p = GSUDO_PRESETS[preset_key]
        return (s.get("CacheMode")                   == p["CacheMode"] and
                s.get("CacheDuration")               == p["CacheDuration"] and
                s.get("SecurityEnforceUacIsolation")  == p["SecurityEnforceUacIsolation"] and
                s.get("LogLevel")                    == p["LogLevel"])

    active_preset = next((k for k in GSUDO_PRESETS if _matches(k)), None)

    # Preset buttons strip
    preset_buttons = ""
    for key, meta in GSUDO_PRESETS.items():
        is_active  = key == active_preset
        btn_class  = f"btn-{meta['color']}" if is_active else f"btn-outline-{meta['color']}"
        active_lbl = " <small>(active)</small>" if is_active else ""
        preset_buttons += f"""
          <div class="col">
            <button class="btn btn-sm {btn_class} w-100 text-start preset-btn"
                    id="preset-btn-{key}"
                    onclick="applyGlobalPreset('{key}')"
                    title="{meta['description']}">
              <div class="fw-bold">{meta['label']}{active_lbl}</div>
              <div style="font-size:.7rem;opacity:.8;white-space:normal;">
                {meta['CacheMode']} · {meta['CacheDuration']} · UAC {meta['SecurityEnforceUacIsolation']}
              </div>
            </button>
          </div>"""

    return f"""
    {err_html}
    <div class="card mb-3">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h5 class="mb-0">
          <i class="bi bi-shield-lock me-2"></i>gsudo Configuration
        </h5>
        <span class="badge text-bg-secondary" id="gs-version-badge">
          v2.6 — <a href="https://gerardog.github.io/gsudo/docs/config" target="_blank"
                    class="text-decoration-none text-reset">docs</a>
        </span>
      </div>
      <div class="card-body">

        <!-- Quick Presets -->
        <h6 class="text-uppercase text-muted mb-2" style="font-size:.72rem;letter-spacing:.08em;">
          <i class="bi bi-lightning-charge me-1"></i>Quick Presets
        </h6>
        <div class="row g-2 mb-3">
          {preset_buttons}
        </div>

        <!-- Preset reference — collapsible -->
        <div class="mb-4">
          <a class="small text-muted text-decoration-none d-inline-flex align-items-center gap-1"
             data-bs-toggle="collapse" href="#gsudo-preset-readme" role="button"
             aria-expanded="false">
            <i class="bi bi-book me-1"></i>
            <span id="readme-toggle-label">What do these presets mean?</span>
            <i class="bi bi-chevron-down" id="readme-chevron" style="font-size:.7rem;transition:transform .2s;"></i>
          </a>
          <div class="collapse mt-2" id="gsudo-preset-readme">
            <div class="card card-body small" style="background:var(--bs-tertiary-bg);border:1px solid var(--bs-border-color);">
              <p class="mb-2 text-muted" style="font-size:.78rem;">
                gsudo stores elevation credentials in a per-session cache so you are not prompted
                every time a tool needs admin access. These presets control how aggressive that
                caching is. Pick the one that matches how much you trust the work happening in
                that session.
              </p>
              <table class="table table-sm table-borderless mb-2" style="font-size:.78rem;">
                <thead>
                  <tr class="text-muted" style="font-size:.7rem;text-transform:uppercase;letter-spacing:.06em;">
                    <th style="width:90px">Preset</th>
                    <th style="width:110px">Cache Mode</th>
                    <th style="width:110px">Duration</th>
                    <th style="width:80px">UAC Isolation</th>
                    <th>When to use</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><span class="badge text-bg-success">Loose</span></td>
                    <td>Auto</td>
                    <td>Infinite</td>
                    <td><span class="badge text-bg-secondary">Off</span></td>
                    <td>Projects you work on daily and fully trust — Maia, QI Hive. Approve once per machine reboot, never again.</td>
                  </tr>
                  <tr>
                    <td><span class="badge text-bg-primary">Normal</span></td>
                    <td>Auto</td>
                    <td>8 min idle</td>
                    <td><span class="badge text-bg-secondary">Off</span></td>
                    <td>Standard development. Cache expires after 8 minutes of inactivity — a good balance for most projects.</td>
                  </tr>
                  <tr>
                    <td><span class="badge text-bg-warning text-dark">Strict</span></td>
                    <td>Explicit</td>
                    <td>2 min idle</td>
                    <td><span class="badge text-bg-warning text-dark">On</span></td>
                    <td>Projects touching production or sensitive config — NEXUS, auth changes. Cache only starts when you explicitly run <code>gsudo cache on</code>.</td>
                  </tr>
                  <tr>
                    <td><span class="badge text-bg-danger">Locked</span></td>
                    <td>Disabled</td>
                    <td>—</td>
                    <td><span class="badge text-bg-danger">On</span></td>
                    <td>Maximum security. No caching at all — every elevation shows a UAC prompt. Use for one-off sensitive operations or untrusted scripts.</td>
                  </tr>
                </tbody>
              </table>
              <hr class="my-2"/>
              <p class="mb-1 text-muted" style="font-size:.75rem;"><strong>Cache Mode explained:</strong></p>
              <ul class="mb-1" style="font-size:.75rem;padding-left:1.2rem;">
                <li><strong>Auto</strong> — gsudo caches credentials automatically after the first UAC approval. No further prompts until the duration expires.</li>
                <li><strong>Explicit</strong> — cache only activates when you run <code>gsudo cache on</code> manually. Useful when you want a deliberate "start of elevated session" moment.</li>
                <li><strong>Disabled</strong> — every single gsudo call triggers a fresh UAC prompt. Slowest but most secure.</li>
              </ul>
              <p class="mb-1 text-muted" style="font-size:.75rem;"><strong>UAC Isolation:</strong></p>
              <ul class="mb-0" style="font-size:.75rem;padding-left:1.2rem;">
                <li>When <strong>On</strong>, the elevated process has its input handle closed — it cannot read from your terminal. More secure but means you cannot type into elevated prompts.</li>
                <li>When <strong>Off</strong>, the elevated process shares your console — normal interactive use.</li>
              </ul>
            </div>
          </div>
        </div>

        <hr/>

        <!-- Cache settings -->
        <h6 class="text-uppercase text-muted mb-3" style="font-size:.72rem;letter-spacing:.08em;">
          <i class="bi bi-clock-history me-1"></i>Credentials Cache
        </h6>
        <div class="row g-3 mb-4">
          <div class="col-md-4">
            <label class="form-label small mb-1">Cache Mode</label>
            {sel("CacheMode", ["Auto", "Explicit", "Disabled"])}
            <div class="form-text">Auto = cache after first approval. Explicit = only when <code>gsudo cache on</code>. Disabled = always prompt.</div>
          </div>
          <div class="col-md-4">
            <label class="form-label small mb-1">Cache Duration</label>
            <div class="input-group input-group-sm">
              <input type="text" id="gs-CacheDuration" class="form-control font-monospace"
                     value="{cache_dur}" placeholder="HH:MM:SS or Infinite"/>
              <button class="btn btn-outline-secondary" onclick="setSetting('CacheDuration', document.getElementById('gs-CacheDuration').value)">
                <i class="bi bi-check-lg"></i>
              </button>
            </div>
            <div class="form-text">How long cached credentials stay valid when idle. <code>Infinite</code> = until reboot.</div>
          </div>
          <div class="col-md-4">
            <label class="form-label small mb-1">Cache Actions</label>
            <div class="d-flex gap-2">
              <button class="btn btn-sm btn-outline-success w-50" onclick="cacheAction('on')">
                <i class="bi bi-play-fill me-1"></i>Start Cache
              </button>
              <button class="btn btn-sm btn-outline-danger w-50" onclick="cacheAction('invalidate')">
                <i class="bi bi-x-circle me-1"></i>Clear Cache
              </button>
            </div>
            <div class="form-text">Start a cache session or invalidate all stored credentials now.</div>
          </div>
        </div>

        <hr/>

        <!-- Security & behaviour -->
        <h6 class="text-uppercase text-muted mb-3" style="font-size:.72rem;letter-spacing:.08em;">
          <i class="bi bi-shield-exclamation me-1"></i>Security & Behaviour
        </h6>
        <div class="row g-3 mb-4">
          <div class="col-md-4">
            <label class="form-label small mb-1">Log Level</label>
            {sel("LogLevel", ["All", "Debug", "Info", "Warning", "Error", "None"])}
            <div class="form-text">Verbosity of gsudo's own internal log.</div>
          </div>
          <div class="col-md-4">
            <label class="form-label small mb-1">UAC Isolation</label>
            <div class="form-check form-switch mt-1">
              <input class="form-check-input" type="checkbox" id="gs-SecurityEnforceUacIsolation"
                     {isolation_checked}
                     onchange="setSetting('SecurityEnforceUacIsolation', this.checked ? 'True' : 'False')">
              <label class="form-check-label small" for="gs-SecurityEnforceUacIsolation">
                SecurityEnforceUacIsolation
              </label>
            </div>
            <div class="form-text">More secure — closes input handle after elevation. Less convenient.</div>
          </div>
          <div class="col-md-4">
            <label class="form-label small mb-1">Always New Window</label>
            <div class="form-check form-switch mt-1">
              <input class="form-check-input" type="checkbox" id="gs-NewWindow.Force"
                     {nw_checked}
                     onchange="setSetting('NewWindow.Force', this.checked ? 'True' : 'False')">
              <label class="form-check-label small" for="gs-NewWindow.Force">
                NewWindow.Force
              </label>
            </div>
            <div class="form-text">Always elevate in a new window instead of the current console.</div>
          </div>
        </div>

        <div id="gs-toast" class="small mt-2" style="min-height:1.2em;"></div>
      </div>
    </div>

    <script>
    const GS_PRESETS = {json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("label","color","description")} for k, v in GSUDO_PRESETS.items()})};

    // Rotate chevron when readme collapses/expands
    document.addEventListener('DOMContentLoaded', () => {{
      const el = document.getElementById('gsudo-preset-readme');
      if (el) {{
        el.addEventListener('show.bs.collapse',  () => document.getElementById('readme-chevron').style.transform = 'rotate(180deg)');
        el.addEventListener('hide.bs.collapse',  () => document.getElementById('readme-chevron').style.transform = 'rotate(0deg)');
      }}
    }});

    async function applyGlobalPreset(key) {{
      const p = GS_PRESETS[key];
      if (!p) return;
      const t = document.getElementById('gs-toast');
      t.innerHTML = '<span class="text-info">Applying preset...</span>';
      const keys = Object.keys(p);
      let errors = [];
      for (const k of keys) {{
        const r = await fetch('/api/config/gsudo', {{
          method: 'POST',
          headers: {{'Content-Type':'application/json'}},
          body: JSON.stringify({{key: k, value: p[k]}})
        }});
        const j = await r.json();
        if (!j.ok) errors.push(k);
      }}
      if (errors.length) {{
        t.innerHTML = `<span class="text-danger">❌ Failed: ${{errors.join(', ')}}</span>`;
      }} else {{
        t.innerHTML = `<span class="text-success">✅ Preset applied — reloading...</span>`;
        setTimeout(() => location.reload(), 1200);
      }}
    }}

    async function setSetting(key, value) {{
      if (!value) return;
      const r = await fetch('/api/config/gsudo', {{
        method: 'POST',
        headers: {{'Content-Type':'application/json'}},
        body: JSON.stringify({{key, value}})
      }});
      const j = await r.json();
      const t = document.getElementById('gs-toast');
      if (j.ok) {{
        t.innerHTML = `<span class="text-success"><i class="bi bi-check-circle me-1"></i>${{key}} → ${{value}}</span>`;
      }} else {{
        t.innerHTML = `<span class="text-danger"><i class="bi bi-x-circle me-1"></i>${{j.error || 'Failed'}}</span>`;
      }}
      setTimeout(() => t.innerHTML = '', 4000);
    }}
    async function cacheAction(action) {{
      const r = await fetch('/api/config/gsudo/cache', {{
        method: 'POST',
        headers: {{'Content-Type':'application/json'}},
        body: JSON.stringify({{action}})
      }});
      const j = await r.json();
      const t = document.getElementById('gs-toast');
      t.innerHTML = j.ok
        ? `<span class="text-success"><i class="bi bi-check-circle me-1"></i>Cache ${{action}} — done</span>`
        : `<span class="text-danger"><i class="bi bi-x-circle me-1"></i>${{j.error || 'Failed'}}</span>`;
      setTimeout(() => t.innerHTML = '', 4000);
    }}
    </script>
    """


def render_gsudo_profiles() -> str:
    """Per-project gsudo profile card."""
    cfg      = _load_hive_config()
    profiles = cfg.get("gsudo_profiles", [])
    active   = cfg.get("gsudo_active_profile", None)

    # Build profile rows
    rows_html = ""
    for p in profiles:
        pid     = p["project"]
        pname   = p.get("label", pid)
        preset  = p.get("preset", "custom")
        pmeta   = GSUDO_PRESETS.get(preset, {})
        color   = pmeta.get("color", "secondary")
        plabel  = pmeta.get("label", "Custom")

        cm   = p.get("CacheMode", "—")
        cd   = p.get("CacheDuration", "—")
        uac  = p.get("SecurityEnforceUacIsolation", "False")
        lvl  = p.get("LogLevel", "—")

        uac_badge = '<span class="badge text-bg-danger">On</span>' if uac == "True" \
                    else '<span class="badge text-bg-secondary">Off</span>'
        active_cls = "table-active" if active == pid else ""

        rows_html += f"""
        <tr class="{active_cls}" id="prof-row-{pid}">
          <td>
            <strong>{pname}</strong>
            {"<i class='bi bi-check-circle-fill text-success ms-1' title='Currently applied'></i>" if active == pid else ""}
          </td>
          <td><span class="badge text-bg-{color}">{plabel}</span></td>
          <td><small class="font-monospace">{cm}</small></td>
          <td><small class="font-monospace">{cd}</small></td>
          <td>{uac_badge}</td>
          <td><small>{lvl}</small></td>
          <td>
            <div class="d-flex gap-1">
              <button class="btn btn-xs btn-outline-success py-0 px-2"
                      onclick="applyProfile('{pid}')" title="Apply this profile now">
                <i class="bi bi-play-fill"></i> Apply
              </button>
              <button class="btn btn-xs btn-outline-danger py-0 px-2"
                      onclick="deleteProfile('{pid}')" title="Delete profile">
                <i class="bi bi-trash"></i>
              </button>
            </div>
          </td>
        </tr>"""

    empty_row = "" if profiles else """
        <tr><td colspan="7" class="text-muted text-center py-3">
          No profiles yet — add one below.
        </td></tr>"""

    # Project options for add-form dropdown
    proj_opts = "".join(
        f'<option value="{pid}">{name}</option>'
        for pid, name in QI_PROJECTS
        if pid not in {p["project"] for p in profiles}
    ) or '<option value="" disabled>All projects already configured</option>'

    # Preset options
    preset_opts = "".join(
        f'<option value="{k}">{v["label"]} — {v["description"]}</option>'
        for k, v in GSUDO_PRESETS.items()
    )

    # Preset JS map for live preview
    preset_js = json.dumps({
        k: {kk: vv for kk, vv in v.items() if kk not in ("label","color","description")}
        for k, v in GSUDO_PRESETS.items()
    })

    return f"""
    <div class="card mt-3">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h5 class="mb-0">
          <i class="bi bi-diagram-3 me-2"></i>Per-Project Profiles
        </h5>
        <button class="btn btn-sm btn-outline-primary" onclick="toggleAddForm()">
          <i class="bi bi-plus-lg me-1"></i>Add Profile
        </button>
      </div>
      <div class="card-body p-0">

        <!-- Profile table -->
        <table class="table table-sm table-hover align-middle mb-0">
          <thead class="table-dark">
            <tr>
              <th>Project</th>
              <th>Preset</th>
              <th>Cache Mode</th>
              <th>Cache Duration</th>
              <th>UAC Isolation</th>
              <th>Log Level</th>
              <th style="width:120px"></th>
            </tr>
          </thead>
          <tbody id="profiles-tbody">{rows_html}{empty_row}</tbody>
        </table>

        <!-- Add form (hidden by default) -->
        <div id="add-profile-form" class="p-3 border-top" style="display:none;background:var(--bs-body-bg)">
          <h6 class="text-muted text-uppercase mb-3" style="font-size:.72rem;letter-spacing:.08em;">
            New Project Profile
          </h6>
          <div class="row g-3 align-items-end">

            <div class="col-md-3">
              <label class="form-label small mb-1">Project</label>
              <select id="new-project" class="form-select form-select-sm">
                {proj_opts}
              </select>
            </div>

            <div class="col-md-3">
              <label class="form-label small mb-1">Security Preset</label>
              <select id="new-preset" class="form-select form-select-sm"
                      onchange="presetChanged()">
                {preset_opts}
              </select>
            </div>

            <div class="col-md-6">
              <div class="alert alert-secondary py-1 px-2 mb-0 small" id="preset-desc">
                Select a preset to see its description.
              </div>
            </div>

            <!-- Custom overrides (always visible so user can tweak) -->
            <div class="col-md-3">
              <label class="form-label small mb-1">Cache Mode</label>
              <select id="new-CacheMode" class="form-select form-select-sm">
                <option>Auto</option><option>Explicit</option><option>Disabled</option>
              </select>
            </div>
            <div class="col-md-3">
              <label class="form-label small mb-1">Cache Duration</label>
              <input type="text" id="new-CacheDuration" class="form-control form-control-sm font-monospace"
                     placeholder="HH:MM:SS or Infinite"/>
            </div>
            <div class="col-md-3">
              <label class="form-label small mb-1">Log Level</label>
              <select id="new-LogLevel" class="form-select form-select-sm">
                <option>All</option><option>Debug</option><option selected>Info</option>
                <option>Warning</option><option>Error</option><option>None</option>
              </select>
            </div>
            <div class="col-md-3 d-flex align-items-end gap-3">
              <div class="form-check form-switch">
                <input class="form-check-input" type="checkbox" id="new-UacIsolation">
                <label class="form-check-label small" for="new-UacIsolation">UAC Isolation</label>
              </div>
            </div>

            <div class="col-12 d-flex gap-2 justify-content-end">
              <button class="btn btn-sm btn-secondary" onclick="toggleAddForm()">Cancel</button>
              <button class="btn btn-sm btn-primary" onclick="saveProfile()">
                <i class="bi bi-floppy me-1"></i>Save Profile
              </button>
            </div>
          </div>
        </div>

      </div>
    </div>

    <div id="prof-toast" class="small mt-2" style="min-height:1.2em;"></div>

    <script>
    const PRESETS = {preset_js};

    function toggleAddForm() {{
      const f = document.getElementById('add-profile-form');
      f.style.display = f.style.display === 'none' ? 'block' : 'none';
      if (f.style.display === 'block') presetChanged();
    }}

    function presetChanged() {{
      const key = document.getElementById('new-preset').value;
      const p   = PRESETS[key] || {{}};
      if (p.CacheMode)                   document.getElementById('new-CacheMode').value = p.CacheMode;
      if (p.CacheDuration)               document.getElementById('new-CacheDuration').value = p.CacheDuration;
      if (p.LogLevel)                    document.getElementById('new-LogLevel').value = p.LogLevel;
      if (p.SecurityEnforceUacIsolation) document.getElementById('new-UacIsolation').checked = p.SecurityEnforceUacIsolation === 'True';
      // Update description
      const descs = {{ {", ".join(f'"{k}": "{v["description"]}"' for k, v in GSUDO_PRESETS.items())} }};
      document.getElementById('preset-desc').textContent = descs[key] || '';
    }}

    async function saveProfile() {{
      const payload = {{
        project:                    document.getElementById('new-project').value,
        preset:                     document.getElementById('new-preset').value,
        CacheMode:                  document.getElementById('new-CacheMode').value,
        CacheDuration:              document.getElementById('new-CacheDuration').value,
        LogLevel:                   document.getElementById('new-LogLevel').value,
        SecurityEnforceUacIsolation: document.getElementById('new-UacIsolation').checked ? 'True' : 'False',
      }};
      if (!payload.project) {{ alert('Select a project.'); return; }}
      const r = await fetch('/api/config/gsudo/profiles', {{
        method: 'POST',
        headers: {{'Content-Type':'application/json'}},
        body: JSON.stringify(payload)
      }});
      const j = await r.json();
      if (j.ok) location.reload();
      else showProfToast('❌ ' + (j.error || 'Failed'), 'danger');
    }}

    async function deleteProfile(pid) {{
      if (!confirm('Delete profile for ' + pid + '?')) return;
      const r = await fetch('/api/config/gsudo/profiles/' + pid, {{method: 'DELETE'}});
      const j = await r.json();
      if (j.ok) location.reload();
      else showProfToast('❌ ' + (j.error || 'Failed'), 'danger');
    }}

    async function applyProfile(pid) {{
      showProfToast('Applying ' + pid + ' profile...', 'info');
      const r = await fetch('/api/config/gsudo/profiles/' + pid + '/apply', {{method: 'POST'}});
      const j = await r.json();
      if (j.ok) {{
        showProfToast('✅ ' + pid + ' profile applied — gsudo now running at ' + j.preset + ' level.', 'success');
        setTimeout(() => location.reload(), 1800);
      }} else {{
        showProfToast('❌ ' + (j.error || 'Apply failed'), 'danger');
      }}
    }}

    function showProfToast(msg, type) {{
      const t = document.getElementById('prof-toast');
      t.innerHTML = `<span class="text-${{type}}">${{msg}}</span>`;
      if (type !== 'info') setTimeout(() => t.innerHTML = '', 5000);
    }}

    // Init preset description on load
    document.addEventListener('DOMContentLoaded', presetChanged);
    </script>
    """


def render_header_lock_config() -> str:
    """Toggle: lock each tab's header area on scroll vs. scroll the whole page."""
    locked = _get_header_lock()
    return f"""
    <div class="card mb-4">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h5 class="mb-0"><i class="bi bi-layout-text-window-reverse"></i> Header area on scroll</h5>
      </div>
      <div class="card-body">
        <p class="text-muted small mb-3">
          Controls what happens to a page's header — the top bar (Home, date,
          theme) and the title/breadcrumb strip — when you scroll down.
        </p>
        <div class="form-check form-switch mb-2">
          <input class="form-check-input" type="checkbox" role="switch"
                 id="headerLockSwitch" {"checked" if locked else ""}
                 onchange="setHeaderLock(this.checked)">
          <label class="form-check-label" for="headerLockSwitch">
            <strong>Lock the header area</strong> — keep it pinned, scroll only the content below it
          </label>
        </div>
        <p class="text-muted small mb-0">
          Off = scroll the whole page together (the header scrolls out of view).
        </p>
        <div id="header-lock-toast" class="text-success small mt-2"></div>
      </div>
    </div>
    <script>
    async function setHeaderLock(on) {{
      document.body.classList.toggle('lock-header', on);   // live, no reload
      const r = await fetch('/api/config/header-lock', {{
        method: 'POST',
        headers: {{'Content-Type':'application/json'}},
        body: JSON.stringify({{lock: on}})
      }});
      const j = await r.json();
      const toast = document.getElementById('header-lock-toast');
      toast.textContent = j.ok ? (on ? '✓ Header locked' : '✓ Header scrolls with page') : '✗ Failed';
      setTimeout(() => toast.textContent = '', 3000);
    }}
    </script>
    """


def render_config() -> str:
    return (render_header_lock_config() + render_gsudo_config()
            + render_gsudo_profiles() + render_log_config())


class LogLevelPayload(BaseModel):
    service: str
    level: str


@app.get("/config", response_class=HTMLResponse)
def config_page():
    return base_layout("Config", render_config(), "config")


@app.get("/api/config/logging")
def api_logging_config():
    return list_services()


@app.post("/api/config/logging/level")
def api_set_log_level(payload: LogLevelPayload):
    ok = set_level(payload.service, payload.level)
    if not ok:
        raise HTTPException(400, f"Invalid level: {payload.level}")
    log.info(f"log level changed: {payload.service} -> {payload.level}")
    return {"ok": True, "service": payload.service, "level": payload.level.upper()}


class GsudoConfigPayload(BaseModel):
    key: str
    value: str

class GsudoCachePayload(BaseModel):
    action: str  # "on" | "off" | "invalidate"

@app.get("/api/config/gsudo")
def api_gsudo_config_get():
    return JSONResponse(_get_gsudo_settings())

@app.post("/api/config/gsudo")
def api_gsudo_config_set(payload: GsudoConfigPayload):
    ALLOWED_KEYS = {"CacheMode", "CacheDuration", "LogLevel",
                    "SecurityEnforceUacIsolation", "NewWindow.Force"}
    if payload.key not in ALLOWED_KEYS:
        raise HTTPException(400, f"Unknown gsudo setting: {payload.key}")
    try:
        sys.path.insert(0, str(_PROJECT_DIR))
        from engine.common.qi_elevate_client import run_elevated
        r = run_elevated("gsudo", ["config", payload.key, payload.value], submitted_by="dashboard")
        if r["status"] == "ok":
            log.info(f"gsudo config {payload.key} → {payload.value}")
            return JSONResponse({"ok": True})
        return JSONResponse({"ok": False, "error": r.get("stderr") or r.get("error", "denied")}, status_code=500)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.post("/api/config/gsudo/cache")
def api_gsudo_cache(payload: GsudoCachePayload):
    try:
        from engine.common.qi_elevate_client import run_elevated
        if payload.action == "invalidate":
            r = run_elevated("gsudo", ["-k"], submitted_by="dashboard")
        elif payload.action in ("on", "off"):
            r = run_elevated("gsudo", ["cache", payload.action], submitted_by="dashboard")
        else:
            raise HTTPException(400, f"Unknown cache action: {payload.action}")
        ok = r["status"] == "ok"
        return JSONResponse({"ok": ok, "error": None if ok else r.get("stderr", "")})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


# ── gsudo per-project profiles ────────────────────────────────────────────────

class GsudoProfilePayload(BaseModel):
    project: str
    preset: str
    CacheMode: str
    CacheDuration: str
    LogLevel: str
    SecurityEnforceUacIsolation: str


@app.get("/api/config/gsudo/profiles")
def api_gsudo_profiles_get():
    cfg = _load_hive_config()
    return JSONResponse(cfg.get("gsudo_profiles", []))


@app.post("/api/config/gsudo/profiles")
def api_gsudo_profiles_add(payload: GsudoProfilePayload):
    valid_ids = {pid for pid, _ in QI_PROJECTS}
    if payload.project not in valid_ids:
        raise HTTPException(400, f"Unknown project: {payload.project}")
    cfg = _load_hive_config()
    profiles = cfg.get("gsudo_profiles", [])
    # Replace if exists, otherwise append
    label = next((n for pid, n in QI_PROJECTS if pid == payload.project), payload.project)
    entry = {
        "project": payload.project,
        "label":   label,
        "preset":  payload.preset,
        "CacheMode":                   payload.CacheMode,
        "CacheDuration":               payload.CacheDuration,
        "LogLevel":                    payload.LogLevel,
        "SecurityEnforceUacIsolation": payload.SecurityEnforceUacIsolation,
    }
    profiles = [p for p in profiles if p["project"] != payload.project]
    profiles.append(entry)
    cfg["gsudo_profiles"] = profiles
    _save_hive_config(cfg)
    log.info(f"gsudo profile saved: {payload.project} ({payload.preset})")
    return JSONResponse({"ok": True})


@app.delete("/api/config/gsudo/profiles/{project}")
def api_gsudo_profiles_delete(project: str):
    cfg = _load_hive_config()
    before = len(cfg.get("gsudo_profiles", []))
    cfg["gsudo_profiles"] = [p for p in cfg.get("gsudo_profiles", []) if p["project"] != project]
    if cfg.get("gsudo_active_profile") == project:
        cfg.pop("gsudo_active_profile", None)
    _save_hive_config(cfg)
    removed = before - len(cfg["gsudo_profiles"])
    return JSONResponse({"ok": True, "removed": removed})


@app.post("/api/config/gsudo/profiles/{project}/apply")
def api_gsudo_profiles_apply(project: str):
    cfg      = _load_hive_config()
    profiles = cfg.get("gsudo_profiles", [])
    profile  = next((p for p in profiles if p["project"] == project), None)
    if not profile:
        raise HTTPException(404, f"No profile for project: {project}")
    try:
        from engine.common.qi_elevate_client import run_elevated
        settings = {
            "CacheMode":                   profile["CacheMode"],
            "CacheDuration":               profile["CacheDuration"],
            "LogLevel":                    profile["LogLevel"],
            "SecurityEnforceUacIsolation": profile["SecurityEnforceUacIsolation"],
        }
        errors = []
        for key, value in settings.items():
            r = run_elevated("gsudo", ["config", key, value], submitted_by="dashboard")
            if r["status"] != "ok":
                errors.append(f"{key}: {r.get('error','denied')}")
        if errors:
            return JSONResponse({"ok": False, "error": "; ".join(errors)}, status_code=500)
        # Record active profile
        cfg["gsudo_active_profile"] = project
        _save_hive_config(cfg)
        log.info(f"gsudo profile applied: {project} ({profile['preset']})")
        return JSONResponse({"ok": True, "preset": profile["preset"], "project": project})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


# ── Theme API ─────────────────────────────────────────────────────────────────

@app.get("/api/theme")
def api_theme_get():
    return JSONResponse({"theme": _get_theme()})

@app.post("/api/theme")
async def api_theme_set(request: Request):
    body  = await request.json()
    theme = body.get("theme", "penumbra")
    if theme not in VALID_THEMES:
        raise HTTPException(400, f"theme must be one of {sorted(VALID_THEMES)}")
    cfg = _load_hive_config()
    cfg["theme"] = theme
    cfg["theme_v2"] = True  # post-rename value: "dark" now means the NEXUS-style dark
    _save_hive_config(cfg)
    return JSONResponse({"ok": True, "theme": theme})


@app.get("/api/write-token/verify")
def api_write_token_verify(request: Request):
    """Lets the browser confirm a pasted write token before storing it. GET, so it
    is not itself blocked by tunnel_write_guard. Returns {"ok": bool}."""
    tok = _write_token()
    supplied = request.headers.get("x-qi-token") or request.query_params.get("qi_token", "")
    return JSONResponse({"ok": bool(tok) and supplied == tok})


@app.get("/api/config/header-lock")
def api_header_lock_get():
    return JSONResponse({"lock": _get_header_lock()})

@app.post("/api/config/header-lock")
async def api_header_lock_set(request: Request):
    body = await request.json()
    lock = bool(body.get("lock", True))
    cfg = _load_hive_config()
    cfg["lock_header"] = lock
    _save_hive_config(cfg)
    return JSONResponse({"ok": True, "lock": lock})


# ── CoWork Dispatch ───────────────────────────────────────────────────────────

_DISPATCH_LOG: list[dict] = []   # in-memory ring buffer (last 100)
_MAX_DISPATCH_LOG = 100

@app.post("/api/dispatch")
async def api_dispatch(request: Request):
    """
    CoWork → Hive integration endpoint.
    Accepts work orders from CoWork and routes them to the appropriate handler.

    Supported types:
      brain_update   — forward to Brain inbox (/api/inbox on Brain API)
      state_update   — update project state in Brain
      task_create    — add a task to the Hive board
      note           — log to dispatch log only
    """
    import httpx
    body = await request.json()
    msg_type   = body.get("type", "note")
    project_id = body.get("project_id", "unknown")
    source     = body.get("source", "cowork")
    result: dict = {"ok": True, "type": msg_type, "project_id": project_id}

    try:
        if msg_type in ("brain_update", "state_update", "decision", "session", "scope_drop"):
            # Forward to Brain inbox
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    "http://127.0.0.1:9011/api/inbox",
                    json={**body, "source": source}
                )
                result["brain_response"] = r.json()

        elif msg_type == "task_create":
            task_data = {
                "title":       body.get("title", "CoWork task"),
                "description": body.get("description", ""),
                "project":     project_id,
                "agent":       body.get("agent", "builder"),
                "priority":    body.get("priority", "medium"),
            }
            tasks = load_tasks()
            new_task = {
                "id": "t" + __import__("uuid").uuid4().hex[:6],
                **task_data,
                "column": "backlog",
                "created_at": datetime.now().strftime("%Y-%m-%d"),
            }
            tasks.append(new_task)
            save_tasks(tasks)
            result["task_id"] = new_task["id"]

        elif msg_type == "note":
            result["logged"] = True

        else:
            result["warning"] = f"Unknown dispatch type '{msg_type}' — logged only"

    except Exception as e:
        result = {"ok": False, "error": str(e), "type": msg_type, "project_id": project_id}
        log.error(f"dispatch error [{msg_type}]: {e}")

    # Log to ring buffer
    entry = {**result, "received_at": datetime.now().isoformat(), "source": source}
    _DISPATCH_LOG.append(entry)
    if len(_DISPATCH_LOG) > _MAX_DISPATCH_LOG:
        _DISPATCH_LOG.pop(0)

    return JSONResponse(result)


@app.get("/api/dispatch/log")
def api_dispatch_log():
    return JSONResponse({"ok": True, "log": list(reversed(_DISPATCH_LOG))})


# ── /logs — cross-project tail viewer ────────────────────────────────────────

# Legacy single-root kept for backward compat (old /api/log/<filename> callers)
LOGS_ROOT = _PROJECT_DIR / "logs"

# Project chip colors for the UI
_PROJECT_COLORS: dict[str, str] = {
    "qi_hive":  "#7c3aed",  # purple
    "maia":     "#2563eb",  # blue
    "naya":     "#db2777",  # pink
    "nexus":    "#0891b2",  # cyan
    "openclaw": "#16a34a",  # green
    "filehq":   "#ea580c",  # orange
    "easyflow": "#ca8a04",  # yellow
}

# Cache — populated lazily, cleared by POST /api/logs/reload
_LOG_ROOTS_CACHE: dict[str, Path] | None = None


def _resolve_log_roots() -> dict[str, Path]:
    """Read qi_registry.json and return {project_id: root_path} for existing log roots."""
    reg_path = Path(r"C:\QIH\ecosystem\qi_registry.json")
    if not reg_path.exists():
        return {"qi_hive": Path(r"C:\QIH\logs")}
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    out: dict[str, Path] = {}
    for proj in reg.get("projects", []):
        pid = (proj.get("id") or "").lower()
        logs = (proj.get("paths") or {}).get("logs")
        if pid and logs:
            if logs.startswith("\\\\") or logs.startswith("//"):
                logger.warning("Skipping UNC log path for project %s: %s", pid, logs)
                continue
            p = Path(logs)
            if p.exists():
                out[pid] = p
    out.setdefault("qi_hive", Path(r"C:\QIH\logs"))
    return out


def _get_log_roots() -> dict[str, Path]:
    global _LOG_ROOTS_CACHE
    if _LOG_ROOTS_CACHE is None:
        _LOG_ROOTS_CACHE = _resolve_log_roots()
    return _LOG_ROOTS_CACHE


_MAX_LOG_FILES = 500


def _list_log_files(project_id: str | None = None) -> list[dict]:
    """Return [{project_id, name, rel_path, size_bytes, mtime}, ...] sorted by mtime desc."""
    roots = _get_log_roots()
    if project_id:
        pid_lower = project_id.lower()
        if pid_lower not in roots:
            return []
        scan = {pid_lower: roots[pid_lower]}
    else:
        scan = roots

    out = []
    for pid, root in scan.items():
        if not root.exists():
            continue
        collected = 0
        for pat in ("*.log", "*.txt", "*.err", "*.out"):
            if collected >= 300:
                break
            for p in root.rglob(pat):
                try:
                    st = p.stat()
                    rel = str(p.relative_to(root)).replace("\\", "/")
                    out.append({
                        "project_id": pid,
                        "name": p.name,
                        "rel_path": rel,
                        "size_bytes": st.st_size,
                        "mtime": st.st_mtime,
                    })
                    collected += 1
                    if collected >= 300:  # per-project cap (e.g. Maia has 25k+ .txt)
                        break
                except OSError:
                    pass
    out.sort(key=lambda x: x["mtime"], reverse=True)
    if len(out) > _MAX_LOG_FILES:
        logger.warning("Log file walk returned %d files; truncating to %d", len(out), _MAX_LOG_FILES)
        out = out[:_MAX_LOG_FILES]
    return out


def _tail_file(path: Path, n_lines: int, max_bytes: int = 5_000_000) -> str:
    """Reverse-block tail — efficient even on files >100 MB.

    Opens before stat to close the TOCTOU window: if the file disappears or
    becomes unreadable between the exists() check and the open, the OSError
    handler returns "" rather than crashing.
    """
    try:
        with path.open("rb") as f:
            size = f.seek(0, 2)  # seek to end to get size without a separate stat
            f.seek(0)
            if size <= 65_536:
                data = f.read().decode("utf-8", errors="replace")
                return "\n".join(data.splitlines()[-n_lines:])
            chunks: list[bytes] = []
            pos = size
            newlines = 0
            while pos > 0 and newlines <= n_lines and sum(len(c) for c in chunks) < max_bytes:
                step = min(65536, pos)
                pos -= step
                f.seek(pos)
                block = f.read(step)
                newlines += block.count(b"\n")
                chunks.insert(0, block)
            data = b"".join(chunks).decode("utf-8", errors="replace")
            return "\n".join(data.splitlines()[-n_lines:])
    except (FileNotFoundError, PermissionError):
        return ""
    except OSError as e:
        return f"[error reading log: {e}]"


def render_logs() -> str:
    roots = _get_log_roots()
    all_files = _list_log_files()

    # Build project dropdown options — only for roots that actually exist
    project_labels = {
        "": "All projects",
        "qi_hive":  "QI Hive",
        "maia":     "Maia",
        "naya":     "Naya",
        "nexus":    "NEXUS",
        "openclaw": "OpenClaw",
        "filehq":   "FileHQ",
        "easyflow": "EasyFlow",
    }
    proj_options = '<option value="">All projects</option>'
    for pid in sorted(roots.keys()):
        label = project_labels.get(pid, pid)
        proj_options += f'<option value="{pid}">{label}</option>'

    # Inline color map for JS
    color_map_js = json.dumps(_PROJECT_COLORS)

    # Pre-render all file rows as JSON for JS to consume
    files_json = json.dumps(all_files)

    return f"""
    <div class="card">
      <div class="card-header d-flex justify-content-between align-items-center flex-wrap gap-2">
        <h5 class="mb-0"><i class="bi bi-journal-text"></i> Logs</h5>
        <div class="d-flex gap-2 align-items-center flex-wrap">
          <select id="log-project" class="form-select form-select-sm" style="width:160px"
                  onchange="filterProject()">{proj_options}</select>
          <select id="log-file" class="form-select form-select-sm" style="width:300px"
                  onchange="loadLog()"><option value="">(select a file)</option></select>
          <select id="log-lines" class="form-select form-select-sm" style="width:110px"
                  onchange="loadLog()">
            <option value="100">100 lines</option>
            <option value="200" selected>200 lines</option>
            <option value="500">500 lines</option>
            <option value="1000">1000 lines</option>
          </select>
          <input type="text" id="log-filter" class="form-control form-control-sm"
                 placeholder="filter (substring)" style="width:160px" oninput="applyFilter()">
          <label class="form-check form-switch small mb-0 ms-2">
            <input class="form-check-input" type="checkbox" id="log-auto" checked> auto
          </label>
          <button class="btn btn-sm btn-outline-secondary" onclick="loadLog()">
            <i class="bi bi-arrow-clockwise"></i>
          </button>
        </div>
      </div>
      <!-- file table -->
      <div class="table-responsive" style="max-height:260px;overflow-y:auto;">
        <table class="table table-sm table-hover mb-0" id="log-table">
          <thead class="table-dark sticky-top">
            <tr>
              <th style="width:14px"></th>
              <th>Project</th>
              <th>File</th>
              <th>Size</th>
              <th>Modified</th>
            </tr>
          </thead>
          <tbody id="log-table-body"></tbody>
        </table>
      </div>
      <div class="card-body p-0 border-top">
        <pre id="log-content" style="max-height:55vh;overflow:auto;padding:12px;margin:0;
             background:#0e0e10;color:#c9d1d9;font-size:12px;line-height:1.4;">Select a log file above.</pre>
      </div>
    </div>
    <script>
    const _ALL_FILES = {files_json};
    const _COLORS   = {color_map_js};
    let _lastRaw = "";
    let _currentProject = null;
    let _currentFile    = null;

    function _chip(pid) {{
      const bg = _COLORS[pid] || "#6c757d";
      return `<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${{bg}};"></span>`;
    }}

    function _fmtSize(b) {{
      if (b < 1024) return b + " B";
      if (b < 1048576) return (b/1024).toFixed(1) + " KB";
      return (b/1048576).toFixed(1) + " MB";
    }}

    function _fmtTime(ts) {{
      return new Date(ts*1000).toLocaleString();
    }}

    function filterProject() {{
      _currentProject = document.getElementById('log-project').value || null;
      const filtered = _currentProject
        ? _ALL_FILES.filter(f => f.project_id === _currentProject)
        : _ALL_FILES;
      const tbody = document.getElementById('log-table-body');
      tbody.innerHTML = filtered.map(f => `
        <tr style="cursor:pointer" onclick="selectFile('${{f.project_id}}','${{f.rel_path.replace(/'/g,"\\\\'")}}')"
            id="row-${{f.project_id}}-${{encodeURIComponent(f.rel_path)}}">
          <td>${{_chip(f.project_id)}}</td>
          <td><small>${{f.project_id}}</small></td>
          <td><small>${{f.rel_path}}</small></td>
          <td><small>${{_fmtSize(f.size_bytes)}}</small></td>
          <td><small>${{_fmtTime(f.mtime)}}</small></td>
        </tr>`).join('');
      // auto-select first file if available
      if (filtered.length) selectFile(filtered[0].project_id, filtered[0].rel_path);
    }}

    function selectFile(pid, relPath) {{
      _currentFile = {{pid, relPath}};
      // highlight row
      document.querySelectorAll('#log-table-body tr').forEach(r => r.classList.remove('table-active'));
      const row = document.getElementById('row-'+pid+'-'+encodeURIComponent(relPath));
      if (row) row.classList.add('table-active');
      loadLog();
    }}

    async function loadLog() {{
      if (!_currentFile) return;
      const n = document.getElementById('log-lines').value;
      const url = `/api/logs/tail?project=${{encodeURIComponent(_currentFile.pid)}}&path=${{encodeURIComponent(_currentFile.relPath)}}&lines=${{n}}`;
      const r = await fetch(url);
      const j = await r.json();
      _lastRaw = j.content || (j.detail ? '[Error: '+j.detail+']' : '');
      applyFilter();
    }}

    function applyFilter() {{
      const q = document.getElementById('log-filter').value.toLowerCase();
      const pre = document.getElementById('log-content');
      if (!q) pre.textContent = _lastRaw;
      else pre.textContent = _lastRaw.split("\\n").filter(l => l.toLowerCase().includes(q)).join("\\n");
      pre.scrollTop = pre.scrollHeight;
    }}

    setInterval(() => {{ if (document.getElementById('log-auto').checked) loadLog(); }}, 3000);
    filterProject();  // populate table on load
    </script>
    """


@app.get("/logs", response_class=HTMLResponse)
def logs_page():
    return base_layout("Logs", render_logs() + render_log_config(), "logs")


@app.get("/api/logs")
def api_list_logs(project: str | None = None):
    roots = _get_log_roots()
    return {
        "logs": _list_log_files(project_id=project),
        "roots": {pid: str(p) for pid, p in roots.items()},
    }


@app.post("/api/logs/reload")
def api_logs_reload():
    """Clear the log-roots cache and re-resolve from registry."""
    global _LOG_ROOTS_CACHE
    _LOG_ROOTS_CACHE = None
    new_roots = _get_log_roots()
    return {"ok": True, "roots": {pid: str(p) for pid, p in new_roots.items()}, "count": len(new_roots)}


@app.get("/api/logs/tail")
def api_tail_log(project: str, path: str, lines: int = 500):
    """Tail a log file. project = project_id; path = rel_path within that project's log root."""
    # Cap at 5000 lines to bound response size
    lines = min(lines, 5000)
    roots = _get_log_roots()
    pid = project.lower()
    if pid not in roots:
        raise HTTPException(404, f"Unknown project_id '{project}'. Known: {list(roots.keys())}")
    root = roots[pid]
    try:
        full = (root / path).resolve()
        full.relative_to(root.resolve())
    except ValueError:
        raise HTTPException(400, "path escapes the project log root")
    return {"project": pid, "path": path, "lines": lines, "content": _tail_file(full, lines)}


# Backward-compat: old callers that hit /api/log/<filename> get qi_hive root
@app.get("/api/log/{filename}")
def api_tail_log_legacy(filename: str, lines: int = 200):
    root = LOGS_ROOT
    try:
        full = (root / filename).resolve()
        full.relative_to(root.resolve())
    except ValueError:
        raise HTTPException(400, "path escapes logs root")
    return {"path": filename, "lines": lines, "content": _tail_file(full, lines)}


# ── /project/{id} — per-project detail page ─────────────────────────────────

def render_project(pid: str) -> str:
    status = load_status()
    projects = status.get("projects", {})
    # Case-insensitive lookup (status.json is keyed by lowercase canonical id).
    proj = projects.get(pid) or projects.get(pid.lower()) \
        or next((v for k, v in projects.items() if k.lower() == pid.lower()), None)

    registry_path = _PROJECT_DIR / "ecosystem" / "qi_registry.json"
    reg_entry = {}
    try:
        if registry_path.exists():
            reg = json.loads(registry_path.read_text(encoding="utf-8"))
            reg_entry = next((x for x in reg.get("projects", [])
                              if x.get("id", "").lower() == pid.lower()), {})
    except Exception:
        pass

    # Fall back to registry + Brain so any registered project still renders.
    if not proj:
        if not reg_entry:
            return f'<div class="alert alert-warning">Project <code>{pid}</code> not found in registry or status.</div>'
        bst = _brain_db_query(
            "SELECT phase,status,summary,next_steps FROM project_state "
            "WHERE LOWER(project_id)=LOWER(?) ORDER BY recorded_at DESC LIMIT 1", (pid,))
        bst = bst[0] if bst else {}
        proj = {
            "id": pid.lower(),
            "display_name": reg_entry.get("name", pid),
            "status": bst.get("status", reg_entry.get("status", "active")),
            "notes": bst.get("summary", reg_entry.get("description", "")),
            "current_task": bst.get("next_steps", "—"),
            "path": reg_entry.get("path", "(no path)"),
            "last_activity": "", "locked_files": [],
        }

    pid = proj.get("id", pid.lower())
    services = reg_entry.get("services", []) or []

    def _svc_row(s: dict) -> str:
        label = s.get("name", "?")
        nssm = s.get("nssm_name", "")
        port = s.get("port")
        port_badge = f' <span class="badge bg-light text-dark border">:{port}</span>' if port else ""
        if nssm and nssm.startswith("QI_"):
            btn = (
                f'<button class="btn btn-sm btn-outline-secondary" '
                f'onclick="checkSvcStatus(this,\'{nssm}\')" '
                f'data-status-for="{nssm}">status</button>'
                f'<span class="ms-2 badge bg-secondary" data-status-label="{nssm}"></span>'
            )
        else:
            btn = '<button class="btn btn-sm btn-outline-secondary" disabled title="no NSSM service registered">status</button>'
        return f"<tr><td><code>{label}</code>{port_badge}</td><td>{btn}</td></tr>"

    svc_rows = "".join(_svc_row(s) for s in services) or \
        '<tr><td colspan="2" class="text-muted">No services registered</td></tr>'

    sessions = _brain_db_query(
        "SELECT session_title, summary, COALESCE(ended_at,started_at) AS ts "
        "FROM session_log WHERE LOWER(project_id)=LOWER(?) ORDER BY ts DESC LIMIT 6", (pid,))
    sess_rows = "".join(
        f"<tr><td><small>{s.get('session_title','') or ''}</small>"
        f"<div class='text-muted' style='font-size:.7rem'>{(s.get('ts','') or '')[:16]}</div></td>"
        f"<td class='text-muted small'>{(s.get('summary','') or '')[:200]}</td></tr>"
        for s in sessions
    ) or '<tr><td colspan="2" class="text-muted">No sessions logged for this project</td></tr>'

    return f"""
    <div class="row g-3">
      <div class="col-12">
        <div class="card"><div class="card-body">
          <div class="d-flex justify-content-between align-items-start">
            <div>
              <h4 class="mb-0">{proj.get('display_name', pid)}</h4>
              <div class="text-muted small"><code>{proj.get('path','(no path)')}</code> · <span class="badge bg-light text-dark border">{pid}</span></div>
            </div>
            <div class="d-flex gap-2">
              <a href="/project/{pid}/status" class="btn btn-sm btn-primary">
                <i class="bi bi-clipboard-data"></i> Project Status
              </a>
              <span class="badge bg-info align-self-center">{proj.get('status','?')}</span>
            </div>
          </div>
          <p class="mt-2 mb-0">{proj.get('notes','')}</p>
        </div></div>
      </div>
      <div class="col-lg-6"><div class="card h-100">
        <div class="card-header"><i class="bi bi-hdd-stack"></i> Services</div>
        <table class="table table-sm mb-0">
          <thead><tr><th>Service</th><th style="width:120px">Action</th></tr></thead>
          <tbody>{svc_rows}</tbody>
        </table>
      </div></div>
      <div class="col-lg-6"><div class="card h-100">
        <div class="card-header"><i class="bi bi-journal"></i> Recent Sessions</div>
        <table class="table table-sm mb-0"><tbody>{sess_rows}</tbody></table>
      </div></div>
      <div class="col-12"><div class="card">
        <div class="card-header d-flex justify-content-between align-items-center">
          <span><i class="bi bi-terminal"></i> Project Info</span>
          <a href="/logs" class="btn btn-sm btn-outline-primary">
            <i class="bi bi-journal-text"></i> View Logs
          </a>
        </div>
        <div class="card-body"><dl class="row mb-0 small">
          <dt class="col-sm-3">Current task</dt>
          <dd class="col-sm-9">{proj.get('current_task') or '<em>none</em>'}</dd>
          <dt class="col-sm-3">Last activity</dt>
          <dd class="col-sm-9">{proj.get('last_activity','?')}</dd>
          <dt class="col-sm-3">Locked files</dt>
          <dd class="col-sm-9">{', '.join(proj.get('locked_files',[])) or '<em>none</em>'}</dd>
        </dl></div>
      </div></div>
    </div>
    <script>
    async function checkSvcStatus(btn, name) {{
      btn.disabled = true;
      btn.textContent = 'checking...';
      const badge = document.querySelector('[data-status-label="' + name + '"]');
      try {{
        const r = await fetch('/api/services/' + encodeURIComponent(name) + '/status');
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const d = await r.json();
        const s = d.status || 'unknown';
        if (badge) {{
          badge.textContent = s;
          badge.className = 'ms-2 badge ' + (
            s === 'running' ? 'bg-success' :
            s === 'stopped' ? 'bg-danger' :
            'bg-secondary'
          );
        }}
        btn.className = s === 'running' ? 'btn btn-sm btn-success'
                      : s === 'stopped' ? 'btn btn-sm btn-danger'
                      : 'btn btn-sm btn-warning';
      }} catch(e) {{
        btn.textContent = 'error';
        if (badge) {{ badge.textContent = ''; }}
      }} finally {{
        setTimeout(() => {{
          btn.disabled = false;
          btn.textContent = 'status';
          btn.className = 'btn btn-sm btn-outline-secondary';
        }}, 2000);
      }}
    }}
    </script>
    """


@app.get("/project/{pid}", response_class=HTMLResponse)
def project_page(pid: str):
    return base_layout(pid, render_project(pid), "dashboard")


def _allowed_qi_services() -> set:
    """Return the set of QI_* service names declared in qi_registry.json."""
    reg_path = Path(r"C:\QIH\ecosystem\qi_registry.json")
    allowed: set = set()
    if reg_path.exists():
        try:
            reg = json.loads(reg_path.read_text(encoding="utf-8"))
            for proj in reg.get("projects", []):
                for svc in (proj.get("services") or []):
                    sname = svc.get("nssm_name") or svc.get("name")
                    if sname and sname.startswith("QI_"):
                        allowed.add(sname)
        except Exception:
            pass
    # Canonical core services — fallback if registry not yet fully populated.
    allowed.update({
        "QI_MaiaBot", "QI_MaiaTunnel", "QI_MaiaDemoTunnel",
        "QI_NayaBot", "QI_NayaGradio",
        "QI_NEXUS", "QI_Dashboard", "QI_DashboardTunnel",
        "QI_BrainAPI", "QI_Elevate", "QI_HiveIngest", "QI_HiveApply",
    })
    return allowed


@app.get("/api/services/{name}/status")
def api_service_status(name: str):
    if name not in _allowed_qi_services():
        raise HTTPException(status_code=400, detail=f"Service '{name}' not in QI allowlist")
    try:
        result = subprocess.run(
            ["gsudo", r"C:\QIH\engine\bin\nssm.exe", "status", name],
            capture_output=True, text=True, timeout=5,
        )
        raw = result.stdout.strip().lower()
        if "service_running" in raw:
            status = "running"
        elif "service_stopped" in raw:
            status = "stopped"
        else:
            status = "unknown"
    except Exception:
        status = "unknown"
    return JSONResponse({"status": status, "service": name})


# ── Project Status (Maia-style, 7 tabs) ──────────────────────────────────────
from project_status import render_project_status, list_projects as _ps_list


def _status_embed_html(title: str, body: str) -> str:
    """Minimal standalone page (no sidebar) for iframe embedding in the Library."""
    theme = _get_theme()
    _base = _THEME_BASE.get(theme)
    bs = f'data-bs-theme="{_base}"' if _base else ""
    _accent = _THEME_ACCENT.get(theme, "")
    acc = f'data-qi-accent="{_accent}"' if _accent else ""
    _skin = _THEME_SKIN.get(theme, "")
    skn = f'data-qi-skin="{_skin}"' if _skin else ""
    fonts = QI_SKIN_FONTS if _skin else ""
    return (f'<!doctype html><html lang="en" {bs} {acc} {skn}><head><meta charset="utf-8"/>'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"/>'
            f'<title>{html.escape(title)}</title>{fonts}'
            f'<link rel="stylesheet" href="/static/vendor/bootstrap-icons/bootstrap-icons.min.css"/>'
            f'<link rel="stylesheet" href="/static/css/adminlte.min.css"/>'
            f'<link rel="stylesheet" href="/static/css/qi-plex.css"/>'
            f'<script src="/static/vendor/bootstrap.bundle.min.js"></script>'
            f'<style>{QI_ACCENT_CSS}{QI_SKIN_CSS}</style>'
            f'</head><body class="bg-body" {bs} {acc} {skn}><div class="p-3">{body}</div></body></html>')


@app.get("/project/{pid}/status", response_class=HTMLResponse)
def project_status_page(pid: str, tab: str = "overview", embed: int = 0):
    title, body = render_project_status(pid, tab, embed=bool(embed))
    if embed:
        return HTMLResponse(_status_embed_html(title, body))
    return base_layout(title, body, "dashboard")


@app.get("/projects/status", response_class=HTMLResponse)
def project_status_index():
    rows = []
    for p in _ps_list():
        ready = ("<span class='badge bg-success'>ready</span>" if p["ready"]
                 else "<span class='badge bg-secondary'>empty</span>")
        rows.append(
            f"<tr><td><a href='/project/{p['pid']}/status'><strong>{p['name']}</strong></a></td>"
            f"<td>{ready}</td><td class='small text-muted'><code>{p['intro']}</code></td></tr>"
        )
    body = f"""
    <div class='card'><div class='card-header'>
      <i class='bi bi-clipboard-data'></i> Project Status — Maia-style pages for every project
    </div>
    <table class='table table-sm mb-0'>
      <thead><tr><th>Project</th><th>Status</th><th>INTRO folder</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table></div>
    <p class='small text-muted mt-3'>Each project's status pages read from
    <code>status_intro.md</code>, <code>status_documentation.json</code>,
    <code>status_features_business.json</code>, <code>status_features_dev.json</code>,
    <code>status_future.json</code>, <code>status_techstack.json</code>
    in its INTRO folder. Edit those files and click Refresh on the dashboard.</p>
    """
    return base_layout("Project Status — Index", body, "dashboard")


# ── Services + Scheduled Tasks (read-only visibility) ────────────────────────
import subprocess as _sp

_NSSM = r"C:\QIH\engine\bin\nssm.exe"
_CREATE_NO_WINDOW = getattr(_sp, "CREATE_NO_WINDOW", 0)


def _collect_services() -> list[dict]:
    """List QI_* + known legacy services with status + AppDirectory."""
    out = []
    try:
        r = _sp.run([_NSSM, "list"], capture_output=True, text=True, timeout=10,
                    creationflags=_CREATE_NO_WINDOW)
        names = [n.strip() for n in r.stdout.splitlines() if n.strip()]
    except Exception as e:
        return [{"name": "ERROR", "status": str(e), "app_dir": "", "description": ""}]

    # Surface QI_* first, then known legacy OC/Maia/Naya/NEXUS
    legacy = ("OC-", "MaiaBot", "NayaBot", "NayaTunnel", "NEXUS", "ClaudeManager")
    def _keep(n): return n.startswith("QI_") or any(n.startswith(p) for p in legacy)

    for name in sorted(n for n in names if _keep(n)):
        row = {"name": name, "status": "?", "app_dir": "", "description": ""}
        try:
            row["status"] = _sp.run([_NSSM, "status", name], capture_output=True, text=True,
                                    timeout=5, creationflags=_CREATE_NO_WINDOW).stdout.strip()
        except Exception: pass
        for key in ("AppDirectory", "Description"):
            try:
                v = _sp.run([_NSSM, "get", name, key], capture_output=True, text=True,
                            timeout=5, creationflags=_CREATE_NO_WINDOW).stdout.strip()
                row["app_dir" if key == "AppDirectory" else "description"] = v
            except Exception: pass
        out.append(row)
    return out


def _collect_tasks() -> list[dict]:
    """List QI-relevant scheduled tasks with schedule + last result."""
    ps = r"""
    $patterns = @('QI_','QI-','OC-','Maia','Naya','NEXUS','openclaw','claude','nlm','Reconcile','Kaze','TubeScout','Hive','Inspector','Compliance','Backfill')
    Get-ScheduledTask | Where-Object {
      $n = $_.TaskName; $patterns | Where-Object { $n -like "*$_*" }
    } | ForEach-Object {
      $info = Get-ScheduledTaskInfo -TaskName $_.TaskName -TaskPath $_.TaskPath
      $trig = $_.Triggers | Select-Object -First 1
      [PSCustomObject]@{
        name        = $_.TaskName
        state       = $_.State.ToString()
        exec        = $_.Actions[0].Execute
        args        = $_.Actions[0].Arguments
        hidden      = $_.Settings.Hidden
        interval    = if ($trig.Repetition) { $trig.Repetition.Interval } else { '' }
        lastRun     = if ($info.LastRunTime) { $info.LastRunTime.ToString('yyyy-MM-dd HH:mm') } else { '' }
        lastResult  = $info.LastTaskResult
        nextRun     = if ($info.NextRunTime) { $info.NextRunTime.ToString('yyyy-MM-dd HH:mm') } else { '' }
      }
    } | ConvertTo-Json -Depth 3 -Compress
    """
    try:
        r = _sp.run(["powershell", "-NoProfile", "-Command", ps],
                    capture_output=True, text=True, timeout=20,
                    creationflags=_CREATE_NO_WINDOW)
        data = json.loads(r.stdout.strip() or "[]")
        if isinstance(data, dict): data = [data]
        return sorted(data, key=lambda x: x.get("name", ""))
    except Exception as e:
        return [{"name": "ERROR", "state": str(e), "exec": "", "args": "",
                 "hidden": False, "interval": "", "lastRun": "", "lastResult": "",
                 "nextRun": ""}]


@app.get("/api/services")
def api_services():
    return {"services": _collect_services()}


@app.get("/api/tasks/scheduled")
def api_scheduled_tasks():
    return {"tasks": _collect_tasks()}


def render_services() -> str:
    rows = ""
    for s in _collect_services():
        badge_cls = {"SERVICE_RUNNING": "bg-success", "SERVICE_STOPPED": "bg-danger",
                     "SERVICE_PAUSED": "bg-warning"}.get(s["status"], "bg-secondary")
        rows += f"""<tr>
          <td><code>{s['name']}</code></td>
          <td><span class="badge {badge_cls}">{s['status']}</span></td>
          <td class="small text-muted">{s['app_dir']}</td>
          <td class="small">{s['description'][:80]}</td>
        </tr>"""
    return f"""
    <div class="card">
      <div class="card-header d-flex justify-content-between align-items-center">
        <span><i class="bi bi-gear-wide-connected"></i> Windows Services (NSSM)</span>
        <button class="btn btn-sm btn-outline-primary" onclick="location.reload()">
          <i class="bi bi-arrow-clockwise"></i> Refresh
        </button>
      </div>
      <div class="table-responsive">
        <table class="table table-sm table-hover mb-0">
          <thead><tr><th>Service</th><th>Status</th><th>App Directory</th><th>Description</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
      <div class="card-footer small text-muted">
        Start/stop controls route through the QI Elevation Broker — coming next pass.
        For now, use <code>nssm start|stop|restart &lt;name&gt;</code> manually.
      </div>
    </div>
    """


def render_tasks_scheduled() -> str:
    def _fmt_result(r):
        if r == 0: return '<span class="badge bg-success">OK</span>'
        if r == 267009: return '<span class="badge bg-info">RUNNING</span>'
        if r == 267011: return '<span class="badge bg-secondary">NEVER RUN</span>'
        if r == 3221225786: return '<span class="badge bg-danger" title="0xC000013A — task killed (timeout or abort)">ABORTED</span>'
        return f'<span class="badge bg-warning">{r}</span>'

    rows = ""
    for t in _collect_tasks():
        hidden_badge = '<i class="bi bi-eye-slash text-success" title="Hidden (no popup)"></i>' if t.get("hidden") else '<i class="bi bi-eye text-warning" title="Visible window"></i>'
        exec_short = (t.get("exec") or "").split("\\")[-1]
        args_short = (t.get("args") or "")[:60]
        rows += f"""<tr>
          <td><code>{t['name']}</code> {hidden_badge}</td>
          <td>{t.get('state','')}</td>
          <td class="small"><code>{exec_short}</code> {args_short}</td>
          <td class="small">{t.get('interval','—')}</td>
          <td class="small">{t.get('lastRun','—')}</td>
          <td>{_fmt_result(t.get('lastResult', -1))}</td>
          <td class="small">{t.get('nextRun','—')}</td>
        </tr>"""
    return f"""
    <div class="card">
      <div class="card-header d-flex justify-content-between align-items-center">
        <span><i class="bi bi-calendar-event"></i> Scheduled Tasks (QI / Maia / Naya / NEXUS / OC)</span>
        <button class="btn btn-sm btn-outline-primary" onclick="location.reload()">
          <i class="bi bi-arrow-clockwise"></i> Refresh
        </button>
      </div>
      <div class="table-responsive">
        <table class="table table-sm table-hover mb-0">
          <thead><tr>
            <th>Task</th><th>State</th><th>Command</th><th>Every</th>
            <th>Last Run</th><th>Result</th><th>Next Run</th>
          </tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
      <div class="card-footer small text-muted">
        <i class="bi bi-eye-slash text-success"></i> = hidden (no popup)
        &nbsp;·&nbsp; <i class="bi bi-eye text-warning"></i> = visible console window (will flash)
        &nbsp;·&nbsp; <span class="badge bg-danger">ABORTED</span> = task was killed mid-run (usually ExecutionTimeLimit)
      </div>
    </div>
    """


@app.get("/services", response_class=HTMLResponse)
def services_page():
    return base_layout("Services", render_services(), "services")


@app.get("/tasks", response_class=HTMLResponse)
def tasks_page():
    return base_layout("Scheduled Tasks", render_tasks_scheduled(), "tasks")


# ── Claude Usage panel ────────────────────────────────────────────────────────

@app.get("/api/usage/today")
def api_usage_today():
    return JSONResponse(usage_stats.today())

@app.get("/api/usage/daily")
def api_usage_daily(days: int = 30):
    return JSONResponse({"days": days, "series": usage_stats.daily(days)})

@app.get("/api/usage/by_project")
def api_usage_by_project(days: int = 30):
    return JSONResponse({"days": days, "rows": usage_by_project(days)})

@app.get("/api/usage/by_model")
def api_usage_by_model(days: int = 30):
    return JSONResponse({"days": days, "rows": usage_by_model(days)})

@app.get("/api/usage/savings")
def api_usage_savings(days: int = 30):
    return JSONResponse(usage_totals(days))

@app.get("/api/usage/savings/today")
def api_usage_savings_today():
    return JSONResponse(usage_stats.savings_today())

@app.get("/api/usage/savings/by_model")
def api_usage_savings_by_model(days: int = 30):
    return JSONResponse({"days": days, "rows": usage_savings_by_model(days)})

@app.get("/api/usage/range")
def api_usage_range(start: str, end: str = ""):
    """Token + cost + savings metrics for an inclusive [start, end] local-date
    window. Powers the LLM-Usage date-range picker and click-a-bar drilldown.
    `end` defaults to `start` (single-day select). Dates are ISO yyyy-mm-dd."""
    from datetime import date as _d
    try:
        s = _d.fromisoformat(start)
        e = _d.fromisoformat(end) if end else s
    except (ValueError, TypeError):
        return JSONResponse({"error": "dates must be ISO yyyy-mm-dd"}, status_code=400)
    return JSONResponse(usage_range(s, e))


def render_usage() -> str:
    t = usage_stats.today()
    t7 = usage_totals(7)
    t30 = usage_totals(30)
    from datetime import date as _date
    _td = _date.today()
    _qn = (_td.month - 1) // 3 + 1
    t_qtd = usage_totals_since(_date(_td.year, (_qn - 1) * 3 + 1, 1))
    t_ytd = usage_totals_since(_date(_td.year, 1, 1))
    daily = usage_daily(30)
    projects_sav = usage_savings_by_project(30)
    s_models = usage_savings_by_model(30)

    # What-if optimization numbers
    s_today = usage_stats.savings_today()
    s_7  = usage_totals(7)
    s_30 = usage_totals(30)

    # Share of 30d spend that stays on Claude (Opus/Fable = 0% local-offload).
    # Drives the "why does Batch save more than Local" explainer — when this is
    # high, near-zero local savings is correct, not a bug.
    _tot_actual = sum(r["actual_usd"] for r in s_models) or 1.0
    _opus_share = sum(r["actual_usd"] for r in s_models
                      if r["family"] in ("opus", "fable")) / _tot_actual * 100

    # Daily chart: 3 thin bars per day (Actual / w-Local / w-Combined)
    max_cost = max((d["cost_usd"] for d in daily), default=0) or 1
    daily_bars = ""
    for d in daily:
        ha = int((d["cost_usd"]          / max_cost) * 100) if max_cost else 0
        hl = int((d["local_cost_usd"]    / max_cost) * 100) if max_cost else 0
        hb = int((d["batch_cost_usd"]    / max_cost) * 100) if max_cost else 0
        hc = int((d["combined_cost_usd"] / max_cost) * 100) if max_cost else 0
        tip = (f"{d['date']} — click to load this day · Actual ${d['cost_usd']:.2f} · "
               f"w/ Local ${d['local_cost_usd']:.2f} · "
               f"w/ Batch ${d['batch_cost_usd']:.2f} · "
               f"Combined ${d['combined_cost_usd']:.2f}")
        daily_bars += f'''
        <div class="daily-bar-wrap" data-date="{d['date']}" title="{tip}">
          <div class="daily-trio">
            <div class="daily-bar bar-actual"   style="height:{ha}%;"></div>
            <div class="daily-bar bar-local"    style="height:{hl}%;"></div>
            <div class="daily-bar bar-batch"    style="height:{hb}%;"></div>
            <div class="daily-bar bar-combined" style="height:{hc}%;"></div>
          </div>
          <small class="daily-label">{d['date'][-5:]}</small>
        </div>'''

    # "By Project (30d)" — now with savings columns
    project_rows = ""
    for r in projects_sav:
        if r["actual_usd"] <= 0: continue
        project_rows += f'''<tr>
          <td><strong>{r["project"]}</strong></td>
          <td class="text-end">{r["tokens"]/1_000_000:.1f}M</td>
          <td class="text-end">{r["turns"]:,}</td>
          <td class="text-end">${r["actual_usd"]:,.2f}</td>
          <td class="text-end text-info">${r["local_opt_usd"]:,.2f}</td>
          <td class="text-end text-warning">${r["batch_opt_usd"]:,.2f}</td>
          <td class="text-end text-success"><strong>${r["combined_usd"]:,.2f}</strong></td>
          <td class="text-end"><span class="badge text-bg-success-subtle">−${r["total_savings_usd"]:,.2f} ({r["total_savings_pct"]:.1f}%)</span></td>
        </tr>'''

    # "By Model (30d)" — same structure as savings_by_model (actual + w/Local + w/Batch + Combined + Total)
    model_rows_compare = ""
    for r in s_models:
        if r["actual_usd"] <= 0: continue
        short = r["model"].replace("claude-", "").replace("-20251001", "")
        fam = r["family"]
        col = {"opus": "danger", "sonnet": "primary", "haiku": "success"}.get(fam, "secondary")
        model_rows_compare += f'''<tr>
          <td><span class="badge text-bg-{col}">{fam}</span> <code>{short}</code></td>
          <td class="text-end">{r["tokens"]/1_000_000:.1f}M</td>
          <td class="text-end">{r["turns"]:,}</td>
          <td class="text-end">${r["actual_usd"]:,.2f}</td>
          <td class="text-end text-info">${r["local_opt_usd"]:,.2f}</td>
          <td class="text-end text-warning">${r["batch_opt_usd"]:,.2f}</td>
          <td class="text-end text-success"><strong>${r["combined_usd"]:,.2f}</strong></td>
          <td class="text-end"><span class="badge text-bg-success-subtle">−${r["total_savings_usd"]:,.2f} ({r["total_savings_pct"]:.1f}%)</span></td>
        </tr>'''

    # Same rows for the Savings-By-Model card (kept simpler shape)
    savings_model_rows = ""
    for r in s_models:
        if r["actual_usd"] <= 0: continue
        short = r["model"].replace("claude-", "").replace("-20251001", "")
        fam = r["family"]
        col = {"opus": "danger", "sonnet": "primary", "haiku": "success"}.get(fam, "secondary")
        saved = r["total_savings_usd"]
        savings_model_rows += f'''<tr>
          <td><span class="badge text-bg-{col}">{fam}</span> <code>{short}</code></td>
          <td class="text-end">${r["actual_usd"]:,.2f}</td>
          <td class="text-end text-info">${r["local_opt_usd"]:,.2f}</td>
          <td class="text-end text-warning">${r["batch_opt_usd"]:,.2f}</td>
          <td class="text-end text-success"><strong>${r["combined_usd"]:,.2f}</strong></td>
          <td class="text-end"><span class="badge text-bg-success-subtle">−${saved:,.2f} ({r["total_savings_pct"]:.1f}%)</span></td>
        </tr>'''

    # Project totals row
    p_tot_actual = sum(r["actual_usd"] for r in projects_sav)
    p_tot_local  = sum(r["local_opt_usd"] for r in projects_sav)
    p_tot_batch  = sum(r["batch_opt_usd"] for r in projects_sav)
    p_tot_comb   = sum(r["combined_usd"] for r in projects_sav)
    p_tot_sav    = p_tot_actual - p_tot_comb
    p_tot_pct    = (p_tot_sav / p_tot_actual * 100) if p_tot_actual else 0.0

    return f"""
    <style>
      /* Compact small-box: thinner rows across the 3 tiers */
      .row-compact .small-box {{ padding: .35rem .75rem; min-height: auto; }}
      .row-compact .small-box .inner h4 {{ font-size: 1.15rem; margin: 0; line-height: 1.1; }}
      .row-compact .small-box .inner p  {{ font-size: .72rem; margin: 0; opacity: .9; }}
      .row-compact .small-box .small-box-icon {{ font-size: 2rem; right: .5rem; }}

      .daily-bars {{
        display: flex; align-items: flex-end; gap: 3px;
        height: 180px; padding: 10px 0 30px; overflow-x: auto;
      }}
      .daily-bar-wrap {{
        flex: 1 0 34px; display: flex; flex-direction: column;
        align-items: center; justify-content: flex-end; height: 100%;
        position: relative;
      }}
      .daily-trio {{
        display: flex; align-items: flex-end; gap: 1px;
        width: 100%; height: 100%; justify-content: center;
      }}
      .daily-bar {{
        width: 23%; border-radius: 2px 2px 0 0; min-height: 2px;
      }}
      .bar-actual   {{ background: linear-gradient(to top, #6366f1, #a5b4fc); }}
      .bar-local    {{ background: linear-gradient(to top, #0dcaf0, #7fdfff); }}
      .bar-batch    {{ background: linear-gradient(to top, #ffc107, #ffe08a); }}
      .bar-combined {{ background: linear-gradient(to top, #198754, #6fd2a0); }}
      .daily-bar-wrap {{ cursor: pointer; transition: background .12s; border-radius: 3px; }}
      .daily-bar-wrap:hover {{ background: rgba(99,102,241,.10); }}
      .daily-bar-wrap.selected {{ background: rgba(99,102,241,.22); outline: 1px solid rgba(99,102,241,.5); }}
      .daily-label {{
        position: absolute; bottom: -22px; font-size: 10px;
        color: #6c757d; white-space: nowrap;
        transform: rotate(-45deg); transform-origin: center;
      }}
      .chart-legend {{ font-size: .8rem; }}
      .chart-legend .sw {{ display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:4px; vertical-align:middle; }}

      /* Collapsible areas: clickable header + chevron that rotates when collapsed */
      .area-toggle {{ cursor: pointer; user-select: none; }}
      .area-chevron {{ transition: transform .2s; font-size: .9rem; opacity: .7; }}
      .area-toggle.collapsed .area-chevron {{ transform: rotate(-90deg); }}
    </style>

    <!-- MAX-plan disclaimer: these are API list-price equivalents, not actual subscription cost -->
    <div class="alert alert-info d-flex align-items-start mb-3" style="border-left:4px solid #0dcaf0">
      <i class="bi bi-info-circle-fill fs-5 me-2 mt-1"></i>
      <div class="small">
        <strong>Estimates use Anthropic API list pricing.</strong>
        You're on the <strong>Claude MAX plan</strong> — the figures below are <em>what this workload would cost via direct API access</em>, not what you actually pay. Your real monthly outlay is the flat MAX subscription. Use this page to track relative usage trends, plan-tier sizing, and savings from local offload / batch — not as a bill.
        <br>
        <strong>Tokens Today</strong> excludes cache re-reads (same prefix loaded each turn — they don't represent fresh consumption). The cache-read volume is shown separately under each card so you can see what the model is actually re-loading.
      </div>
    </div>

    <!-- Expand / collapse all areas -->
    <div class="d-flex justify-content-end mb-2">
      <div class="btn-group btn-group-sm" role="group" aria-label="expand or collapse all areas">
        <button type="button" id="area-expand-all" class="btn btn-outline-secondary"><i class="bi bi-arrows-expand me-1"></i>Expand all</button>
        <button type="button" id="area-collapse-all" class="btn btn-outline-secondary"><i class="bi bi-arrows-collapse me-1"></i>Collapse all</button>
      </div>
    </div>

    <!-- Interactive Selected-Period panel — driven by the date picker + clickable bars -->
    <div class="card mb-3" style="border-left:4px solid #6366f1">
      <div class="card-header d-flex flex-wrap justify-content-between align-items-center gap-2">
        <h3 class="card-title mb-0 area-toggle d-inline-flex align-items-center gap-2"
            data-bs-toggle="collapse" data-bs-target="#sp-body" role="button" aria-expanded="true">
          <i class="bi bi-chevron-down area-chevron"></i>
          <span><i class="bi bi-calendar-range me-2"></i>Selected Period —
          <span id="sp-label" class="text-primary">today</span></span>
        </h3>
        <div class="d-flex flex-wrap align-items-center gap-2">
          <div class="btn-group btn-group-sm" role="group" aria-label="quick ranges">
            <button type="button" class="btn btn-outline-primary active" data-preset="today">Today</button>
            <button type="button" class="btn btn-outline-primary" data-preset="7d">7d</button>
            <button type="button" class="btn btn-outline-primary" data-preset="30d">30d</button>
            <button type="button" class="btn btn-outline-primary" data-preset="mtd">MTD</button>
            <button type="button" class="btn btn-outline-primary" data-preset="qtd">QTD</button>
            <button type="button" class="btn btn-outline-primary" data-preset="ytd">YTD</button>
          </div>
          <input type="date" id="sp-start" class="form-control form-control-sm" style="width:auto" title="start date">
          <span class="text-muted">&rarr;</span>
          <input type="date" id="sp-end" class="form-control form-control-sm" style="width:auto" title="end date">
        </div>
      </div>
      <div id="sp-body" class="collapse show">
      <div class="card-body">
        <div class="row row-compact g-2">
          <div class="col-6 col-md-3 col-lg"><div class="small-box text-bg-primary"><div class="inner"><h4 id="sp-tokens">&mdash;</h4><p>Tokens</p></div><i class="small-box-icon bi bi-lightning-charge-fill"></i></div></div>
          <div class="col-6 col-md-3 col-lg"><div class="small-box text-bg-secondary"><div class="inner"><h4 id="sp-reads">&mdash;</h4><p>Cache re-reads</p></div><i class="small-box-icon bi bi-arrow-repeat"></i></div></div>
          <div class="col-6 col-md-3 col-lg"><div class="small-box text-bg-success"><div class="inner"><h4 id="sp-cost">&mdash;</h4><p>API-Equiv Cost</p></div><i class="small-box-icon bi bi-currency-dollar"></i></div></div>
          <div class="col-6 col-md-3 col-lg"><div class="small-box text-bg-dark"><div class="inner"><h4 id="sp-turns">&mdash;</h4><p>Turns</p></div><i class="small-box-icon bi bi-chat-left-dots"></i></div></div>
          <div class="col-6 col-md-3 col-lg"><div class="small-box text-bg-dark"><div class="inner"><h4 id="sp-sessions">&mdash;</h4><p>Sessions</p></div><i class="small-box-icon bi bi-window-stack"></i></div></div>
          <div class="col-6 col-md-3 col-lg"><div class="small-box text-bg-info"><div class="inner"><h4 id="sp-local">&mdash;</h4><p>Local Saved</p></div><i class="small-box-icon bi bi-cpu"></i></div></div>
          <div class="col-6 col-md-3 col-lg"><div class="small-box text-bg-warning"><div class="inner"><h4 id="sp-batch">&mdash;</h4><p>Batch Saved</p></div><i class="small-box-icon bi bi-moon-stars"></i></div></div>
          <div class="col-6 col-md-3 col-lg"><div class="small-box text-bg-success"><div class="inner"><h4 id="sp-combined">&mdash;</h4><p>Combined Saved</p></div><i class="small-box-icon bi bi-stars"></i></div></div>
        </div>
        <p class="small text-muted mb-0 mt-1">
          <i class="bi bi-hand-index me-1"></i>Click any bar in the <strong>Daily Spend</strong> chart below, use a preset, or pick a custom start/end date — every field above recomputes for that exact window.
        </p>
      </div>
      </div>
    </div>

    <!-- Row 1: actual spend — consumption ladder (collapsible) -->
    <div class="card mb-2">
      <div class="card-header py-2 area-toggle d-flex justify-content-between align-items-center"
           data-bs-toggle="collapse" data-bs-target="#area-overview" role="button" aria-expanded="true">
        <h3 class="card-title mb-0"><i class="bi bi-speedometer2 me-2"></i>Token &amp; Cost Overview
          <span class="text-muted small fw-normal ms-2">Today → Year-to-date</span></h3>
        <i class="bi bi-chevron-down area-chevron"></i>
      </div>
      <div id="area-overview" class="collapse show"><div class="card-body py-2">
    <div class="row row-compact g-2 mb-1">
      <div class="col-6 col-md-2"><div class="small-box text-bg-primary">
        <div class="inner">
          <h4>{t['tokens']/1_000_000:.1f}M</h4>
          <p>Tokens Today <span class="opacity-75" style="font-size:.62rem">(+{t.get('cache_reads',0)/1_000_000:.0f}M re-reads)</span></p>
        </div>
        <i class="small-box-icon bi bi-lightning-charge-fill"></i>
      </div></div>
      <div class="col-6 col-md-2"><div class="small-box text-bg-success">
        <div class="inner">
          <h4>${t['cost_usd']:.2f}</h4>
          <p>API Equiv. Today</p>
        </div>
        <i class="small-box-icon bi bi-currency-dollar"></i>
      </div></div>
      <div class="col-6 col-md-2"><div class="small-box text-bg-info">
        <div class="inner">
          <h4>${t7['cost_usd']:,.0f}</h4>
          <p>API Equiv. (7d)</p>
        </div>
        <i class="small-box-icon bi bi-calendar-week"></i>
      </div></div>
      <div class="col-6 col-md-2"><div class="small-box text-bg-warning">
        <div class="inner">
          <h4>${t30['cost_usd']:,.0f}</h4>
          <p>API Equiv. (30d)</p>
        </div>
        <i class="small-box-icon bi bi-calendar-range"></i>
      </div></div>
      <div class="col-6 col-md-2"><div class="small-box text-bg-secondary">
        <div class="inner">
          <h4>${t_qtd['cost_usd']:,.0f}</h4>
          <p>Q{_qn} to date</p>
        </div>
        <i class="small-box-icon bi bi-calendar3"></i>
      </div></div>
      <div class="col-6 col-md-2"><div class="small-box text-bg-dark">
        <div class="inner">
          <h4>${t_ytd['cost_usd']:,.0f}</h4>
          <p>Year to date</p>
        </div>
        <i class="small-box-icon bi bi-calendar-check"></i>
      </div></div>
    </div>
    </div></div></div>

    <!-- Row 2: Local FREE LLMs (Ollama) (collapsible) -->
    <div class="card mb-2">
      <div class="card-header py-2 area-toggle d-flex justify-content-between align-items-center"
           data-bs-toggle="collapse" data-bs-target="#area-local" role="button" aria-expanded="true">
        <h3 class="card-title mb-0"><i class="bi bi-cpu me-2"></i>Local FREE LLMs (via Ollama)
          <span class="text-muted small fw-normal ms-2">Haiku → gemma4 / qwen3:8b · Sonnet → gpt-oss-20b / gemma4:31b · Opus → stays on Claude</span></h3>
        <i class="bi bi-chevron-down area-chevron"></i>
      </div>
      <div id="area-local" class="collapse show"><div class="card-body py-2">
    <div class="row row-compact mb-1">
      <div class="col-md-3"><div class="small-box text-bg-info">
        <div class="inner"><h4>{s_today['offloaded_turns']}</h4><p>Offloadable Turns Today</p></div>
        <i class="small-box-icon bi bi-pc-display"></i>
      </div></div>
      <div class="col-md-3"><div class="small-box text-bg-info">
        <div class="inner"><h4>−${s_today['local_savings_usd']:.2f}</h4><p>Saved Today ({s_today['local_savings_pct']:.0f}%)</p></div>
        <i class="small-box-icon bi bi-piggy-bank"></i>
      </div></div>
      <div class="col-md-3"><div class="small-box text-bg-info">
        <div class="inner"><h4>−${s_7['local_savings_usd']:,.0f}</h4><p>Saved (7d)</p></div>
        <i class="small-box-icon bi bi-calendar-week"></i>
      </div></div>
      <div class="col-md-3"><div class="small-box text-bg-info">
        <div class="inner"><h4>−${s_30['local_savings_usd']:,.0f}</h4><p>Saved (30d, {s_30['local_savings_pct']:.0f}%)</p></div>
        <i class="small-box-icon bi bi-calendar-range"></i>
      </div></div>
    </div>
    </div></div></div>

    <!-- Row 3: Claude Batch API (collapsible) -->
    <div class="card mb-3">
      <div class="card-header py-2 area-toggle d-flex justify-content-between align-items-center"
           data-bs-toggle="collapse" data-bs-target="#area-batch" role="button" aria-expanded="true">
        <h3 class="card-title mb-0"><i class="bi bi-moon-stars me-2"></i>Claude Batch API <span class="badge text-bg-warning ms-1">50% OFF</span>
          <span class="text-muted small fw-normal ms-2">Deferred to 00:00–06:00 · Opus · Sonnet · Haiku · 24h async SLA</span></h3>
        <i class="bi bi-chevron-down area-chevron"></i>
      </div>
      <div id="area-batch" class="collapse show"><div class="card-body py-2">
    <div class="row row-compact mb-1">
      <div class="col-md-3"><div class="small-box text-bg-warning">
        <div class="inner"><h4>{s_today['batchable_turns']}</h4><p>Batchable Turns Today</p></div>
        <i class="small-box-icon bi bi-moon-stars"></i>
      </div></div>
      <div class="col-md-3"><div class="small-box text-bg-warning">
        <div class="inner"><h4>−${s_today['batch_savings_usd']:.2f}</h4><p>Saved Today ({s_today['batch_savings_pct']:.0f}%)</p></div>
        <i class="small-box-icon bi bi-piggy-bank"></i>
      </div></div>
      <div class="col-md-3"><div class="small-box text-bg-warning">
        <div class="inner"><h4>−${s_7['batch_savings_usd']:,.0f}</h4><p>Saved (7d)</p></div>
        <i class="small-box-icon bi bi-calendar-week"></i>
      </div></div>
      <div class="col-md-3"><div class="small-box text-bg-warning">
        <div class="inner"><h4>−${s_30['batch_savings_usd']:,.0f}</h4><p>Saved (30d, {s_30['batch_savings_pct']:.0f}%)</p></div>
        <i class="small-box-icon bi bi-calendar-range"></i>
      </div></div>
    </div>
    </div></div></div>

    <!-- Combined summary -->
    <div class="row mb-3">
      <div class="col-12">
        <div class="alert alert-success d-flex align-items-center justify-content-between mb-0">
          <div>
            <i class="bi bi-stars fs-4 me-2"></i>
            <strong>Combined (30d):</strong>
            Claude API Actual <code>${s_30['actual_cost_usd']:,.2f}</code>
            → with Local offload + Batch <code>${s_30['combined_cost_usd']:,.2f}</code>
          </div>
          <div>
            <span class="badge text-bg-success fs-6">Save ${s_30['combined_savings_usd']:,.0f} ({s_30['combined_savings_pct']:.1f}%)</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Why Local saves less than Batch (correct, not a bug) -->
    <div class="alert alert-warning py-2 small mb-3 d-flex align-items-start">
      <i class="bi bi-lightbulb-fill me-2 mt-1"></i>
      <div>
        <strong>Why does Batch save far more than Local?</strong>
        <strong>{_opus_share:.0f}%</strong> of the last 30 days' spend is Opus/Fable (deep reasoning), which the model keeps on Claude — so local offload barely lowers cost.
        The Batch API's 50% discount applies to <em>every</em> model run outside 00:00&ndash;06:00, so it saves much more.
        That's why in the tables below the <span class="text-info fw-semibold">w/ Local</span> cost stays close to Actual while the <span class="text-warning fw-semibold">w/ Batch</span> cost is roughly halved &mdash; this is correct, not a miscalculation. (Local savings approach zero only because almost nothing routes to free local models.)
      </div>
    </div>

    <!-- Daily chart (4 series: Actual / w-Local / w-Batch / Combined) -->
    <div class="card mb-3">
      <div class="card-header d-flex justify-content-between align-items-center area-toggle"
           data-bs-toggle="collapse" data-bs-target="#area-daily" role="button" aria-expanded="true">
        <h3 class="card-title mb-0"><i class="bi bi-graph-up me-2"></i>Daily Spend — Last 30 Days <small class="text-muted fw-normal">(click a bar to drill in)</small></h3>
        <div class="d-flex align-items-center gap-3">
          <div class="chart-legend">
            <span><i class="sw bar-actual"></i>Actual</span>
            <span class="ms-3"><i class="sw bar-local"></i>w/ Local</span>
            <span class="ms-3"><i class="sw bar-batch"></i>w/ Batch</span>
            <span class="ms-3"><i class="sw bar-combined"></i>Combined</span>
          </div>
          <i class="bi bi-chevron-down area-chevron"></i>
        </div>
      </div>
      <div id="area-daily" class="collapse show"><div class="card-body">
        <div class="daily-bars">{daily_bars}</div>
      </div></div>
    </div>

    <div class="row">
      <!-- By project -->
      <div class="col-lg-12">
        <div class="card mb-3">
          <div class="card-header area-toggle d-flex justify-content-between align-items-center"
               data-bs-toggle="collapse" data-bs-target="#area-project" role="button" aria-expanded="true">
            <h3 class="card-title mb-0"><i class="bi bi-folder2-open me-2"></i>By Project (30d) — Claude API vs Local + Batch</h3>
            <i class="bi bi-chevron-down area-chevron"></i>
          </div>
          <div id="area-project" class="collapse show"><div class="card-body p-0">
            <table class="table table-sm table-striped mb-0">
              <thead><tr>
                <th>Project</th>
                <th class="text-end">Tokens</th>
                <th class="text-end">Turns</th>
                <th class="text-end">Actual</th>
                <th class="text-end">w/ Local</th>
                <th class="text-end">w/ Batch</th>
                <th class="text-end">Combined</th>
                <th class="text-end">Total Savings</th>
              </tr></thead>
              <tbody>{project_rows or '<tr><td colspan="8" class="text-muted text-center">no data</td></tr>'}</tbody>
              <tfoot class="table-group-divider">
                <tr class="fw-bold">
                  <td colspan="3">TOTAL</td>
                  <td class="text-end">${p_tot_actual:,.2f}</td>
                  <td class="text-end text-info">${p_tot_local:,.2f}</td>
                  <td class="text-end text-warning">${p_tot_batch:,.2f}</td>
                  <td class="text-end text-success">${p_tot_comb:,.2f}</td>
                  <td class="text-end"><span class="badge text-bg-success">−${p_tot_sav:,.2f} ({p_tot_pct:.1f}%)</span></td>
                </tr>
              </tfoot>
            </table>
          </div></div>
        </div>
      </div>

      <!-- By model -->
      <div class="col-lg-12">
        <div class="card mb-3">
          <div class="card-header area-toggle d-flex justify-content-between align-items-center"
               data-bs-toggle="collapse" data-bs-target="#area-model" role="button" aria-expanded="true">
            <h3 class="card-title mb-0"><i class="bi bi-cpu me-2"></i>By Model (30d) — Claude API vs Local + Batch</h3>
            <i class="bi bi-chevron-down area-chevron"></i>
          </div>
          <div id="area-model" class="collapse show"><div class="card-body p-0">
            <table class="table table-sm table-striped mb-0">
              <thead><tr>
                <th>Model</th>
                <th class="text-end">Tokens</th>
                <th class="text-end">Turns</th>
                <th class="text-end">Actual</th>
                <th class="text-end">w/ Local</th>
                <th class="text-end">w/ Batch</th>
                <th class="text-end">Combined</th>
                <th class="text-end">Total Savings</th>
              </tr></thead>
              <tbody>{model_rows_compare or '<tr><td colspan="8" class="text-muted text-center">no data</td></tr>'}</tbody>
              <tfoot class="table-group-divider">
                <tr class="fw-bold">
                  <td colspan="3">TOTAL</td>
                  <td class="text-end">${s_30['actual_cost_usd']:,.2f}</td>
                  <td class="text-end text-info">${s_30['local_optimized_cost_usd']:,.2f}</td>
                  <td class="text-end text-warning">${s_30['batch_optimized_cost_usd']:,.2f}</td>
                  <td class="text-end text-success">${s_30['combined_cost_usd']:,.2f}</td>
                  <td class="text-end"><span class="badge text-bg-success">−${s_30['combined_savings_usd']:,.2f} ({s_30['combined_savings_pct']:.1f}%)</span></td>
                </tr>
              </tfoot>
            </table>
          </div></div>
        </div>
      </div>
    </div>

    <!-- Savings By Model -->
    <div class="card mb-3">
      <div class="card-header area-toggle d-flex justify-content-between align-items-center"
           data-bs-toggle="collapse" data-bs-target="#area-savings-model" role="button" aria-expanded="true">
        <h3 class="card-title mb-0"><i class="bi bi-stars me-2"></i>Savings by Model (30d) — Claude API vs Local + Batch</h3>
        <i class="bi bi-chevron-down area-chevron"></i>
      </div>
      <div id="area-savings-model" class="collapse show"><div class="card-body p-0">
        <table class="table table-sm table-striped mb-0">
          <thead><tr>
            <th>Model</th>
            <th class="text-end">Actual</th>
            <th class="text-end" title="if offloadable work went to local Ollama">w/ Local</th>
            <th class="text-end" title="if scheduled via batch API 00:00-06:00">w/ Batch</th>
            <th class="text-end" title="local offload first, then batch the rest">Combined</th>
            <th class="text-end">Total Savings</th>
          </tr></thead>
          <tbody>{savings_model_rows or '<tr><td colspan="6" class="text-muted text-center">no data</td></tr>'}</tbody>
          <tfoot class="table-group-divider">
            <tr class="fw-bold">
              <td>TOTAL</td>
              <td class="text-end">${s_30['actual_cost_usd']:,.2f}</td>
              <td class="text-end text-info">${s_30['local_optimized_cost_usd']:,.2f}</td>
              <td class="text-end text-warning">${s_30['batch_optimized_cost_usd']:,.2f}</td>
              <td class="text-end text-success">${s_30['combined_cost_usd']:,.2f}</td>
              <td class="text-end"><span class="badge text-bg-success">−${s_30['combined_savings_usd']:,.2f} ({s_30['combined_savings_pct']:.1f}%)</span></td>
            </tr>
          </tfoot>
        </table>
      </div></div>
    </div>

    <p class="small text-muted mt-3">
      <i class="bi bi-info-circle me-1"></i>
      Data parsed locally from <code>~/.claude/projects/**/*.jsonl</code> — no API calls.
      Pricing per 1M tokens: Opus $15/$75 · Sonnet $3/$15 · Haiku $0.80/$4. Cache-read at 10%, cache-write at 125%/200% (5m/1h).
      <br>
      <i class="bi bi-cpu me-1"></i>
      <strong>Local offload mapping:</strong> Haiku → 100% to gemma4 / qwen3:8b · Sonnet → 40% to gpt-oss-20b / gemma4:31b · Opus → 0% (stays on Claude).
      <br>
      <i class="bi bi-moon-stars me-1"></i>
      <strong>Batch window:</strong> turns outside 00:00–06:00 local time are counted as deferrable via Claude Batch API (50% discount, 24h SLA). Applies to Opus, Sonnet, and Haiku.
    </p>

    <script>
    (function(){{
      const $ = id => document.getElementById(id);
      const startEl = $('sp-start'), endEl = $('sp-end');
      const fmtTok = n => (Number(n)/1e6).toFixed(Number(n) >= 1e6 ? 1 : 2) + 'M';
      const fmtUsd = n => '$' + Number(n).toLocaleString(undefined, {{minimumFractionDigits:2, maximumFractionDigits:2}});
      const isoLocal = dt => dt.getFullYear() + '-' +
        String(dt.getMonth()+1).padStart(2,'0') + '-' + String(dt.getDate()).padStart(2,'0');

      async function load(start, end, label){{
        end = end || start;
        try {{
          const r = await fetch('/api/usage/range?start=' + start + '&end=' + end);
          const d = await r.json();
          if (d.error) {{ $('sp-label').textContent = d.error; return; }}
          $('sp-tokens').textContent   = fmtTok(d.tokens);
          $('sp-reads').textContent    = fmtTok(d.cache_reads);
          $('sp-cost').textContent     = fmtUsd(d.cost_usd);
          $('sp-turns').textContent    = Number(d.turns).toLocaleString();
          $('sp-sessions').textContent = Number(d.sessions).toLocaleString();
          $('sp-local').textContent    = '−' + fmtUsd(d.local_savings_usd);
          $('sp-batch').textContent    = '−' + fmtUsd(d.batch_savings_usd);
          $('sp-combined').textContent = '−' + fmtUsd(d.combined_savings_usd);
          const span = (d.start === d.end) ? d.start : (d.start + ' → ' + d.end + '  (' + d.days + 'd)');
          $('sp-label').textContent = (label ? label + ' · ' : '') + span;
          startEl.value = d.start; endEl.value = d.end;
          document.querySelectorAll('.daily-bar-wrap').forEach(w => {{
            const dt = w.getAttribute('data-date');
            w.classList.toggle('selected', dt >= d.start && dt <= d.end);
          }});
        }} catch (e) {{ $('sp-label').textContent = 'failed to load range'; }}
      }}

      function preset(kind){{
        const now = new Date();
        const today = isoLocal(now);
        let s = today;
        const back = n => {{ const x = new Date(now); x.setDate(x.getDate() - n); return isoLocal(x); }};
        if      (kind === '7d')  s = back(6);
        else if (kind === '30d') s = back(29);
        else if (kind === 'mtd') s = isoLocal(new Date(now.getFullYear(), now.getMonth(), 1));
        else if (kind === 'qtd') s = isoLocal(new Date(now.getFullYear(), Math.floor(now.getMonth()/3)*3, 1));
        else if (kind === 'ytd') s = isoLocal(new Date(now.getFullYear(), 0, 1));
        load(s, today, kind.toUpperCase());
      }}

      function clearPresets(){{ document.querySelectorAll('[data-preset]').forEach(x => x.classList.remove('active')); }}

      document.querySelectorAll('[data-preset]').forEach(b => {{
        b.addEventListener('click', () => {{ clearPresets(); b.classList.add('active'); preset(b.getAttribute('data-preset')); }});
      }});
      function manual(){{
        if (!startEl.value) return;
        clearPresets();
        load(startEl.value, endEl.value || startEl.value, 'Custom');
      }}
      startEl.addEventListener('change', manual);
      endEl.addEventListener('change', manual);
      document.querySelectorAll('.daily-bar-wrap').forEach(w => {{
        w.addEventListener('click', () => {{ clearPresets(); const dt = w.getAttribute('data-date'); load(dt, dt, 'Day'); }});
      }});

      // initial paint: Today
      preset('today');
    }})();
    </script>

    <script>
    // Collapsible areas: remember open/closed state across page refreshes + expand/collapse all
    (function(){{
      const KEY = 'qiUsageCollapsed';
      const read  = () => {{ try {{ return JSON.parse(localStorage.getItem(KEY)) || {{}}; }} catch(e) {{ return {{}}; }} }};
      const write = s => {{ try {{ localStorage.setItem(KEY, JSON.stringify(s)); }} catch(e) {{}} }};
      const toggles = Array.from(document.querySelectorAll('.area-toggle[data-bs-target]'));
      const state = read();

      toggles.forEach(t => {{
        const id = t.getAttribute('data-bs-target').slice(1);
        const panel = document.getElementById(id);
        if (!panel) return;
        // restore collapsed state without animation
        if (state[id] === true) {{
          panel.classList.remove('show');
          t.classList.add('collapsed');
          t.setAttribute('aria-expanded', 'false');
        }}
        panel.addEventListener('shown.bs.collapse',  () => {{ const s = read(); s[id] = false; write(s); }});
        panel.addEventListener('hidden.bs.collapse', () => {{ const s = read(); s[id] = true;  write(s); }});
      }});

      function setAll(collapse){{
        toggles.forEach(t => {{
          const panel = document.getElementById(t.getAttribute('data-bs-target').slice(1));
          if (!panel || typeof bootstrap === 'undefined') return;
          const c = bootstrap.Collapse.getOrCreateInstance(panel, {{toggle:false}});
          collapse ? c.hide() : c.show();
        }});
      }}
      const ea = document.getElementById('area-expand-all');
      const ca = document.getElementById('area-collapse-all');
      if (ea) ea.addEventListener('click', () => setAll(false));
      if (ca) ca.addEventListener('click', () => setAll(true));
    }})();
    </script>
    """


@app.get("/usage", response_class=HTMLResponse)
def usage_page():
    return base_layout("LLM Usage / Token Costs", render_usage(), "usage")


# ── Activity — who did what ──────────────────────────────────────────────────

@app.get("/api/activity/sessions")
def api_activity_sessions(days: int = 7, limit: int = 200):
    return JSONResponse({"days": days, "rows": usage_stats.sessions_log(days, limit)})

@app.get("/api/activity/hive_reports")
def api_activity_hive_reports(limit: int = 50):
    status = load_status()
    reports = status.get("hive_reports", [])
    return JSONResponse({"rows": reports[-limit:][::-1]})


def render_activity() -> str:
    status = load_status()
    hive_reports = list(reversed(status.get("hive_reports", [])))[:50]
    sessions = usage_stats.sessions_log(days=7, limit=100)

    # Hive reports (hook-based, from each project's .claude)
    hive_rows = ""
    for r in hive_reports:
        event = r.get("event", "—")
        ev_color = {
            "session_start": "info",
            "session_end":   "success",
            "task_done":     "primary",
            "error":         "danger",
        }.get(event, "secondary")
        ts = r.get("timestamp", "")[:19].replace("T", " ")
        project = r.get("project", "—")
        summary = (r.get("summary") or "").replace("<", "&lt;")[:160]
        user = r.get("user", "—")
        host = r.get("host", "—")
        hive_rows += f'''<tr>
          <td><small class="text-muted">{ts}</small></td>
          <td><span class="badge text-bg-dark">{project}</span></td>
          <td><span class="badge text-bg-{ev_color}">{event}</span></td>
          <td>{summary or "<em class='text-muted'>no summary</em>"}</td>
          <td><small class="text-muted">{user}@{host}</small></td>
        </tr>'''

    # Session log (derived from JSONL)
    session_rows = ""
    for s in sessions:
        started = s["started"][:19].replace("T", " ")
        dur = f"{s['duration_min']:.0f}m" if s["duration_min"] >= 1 else f"{int(s['duration_min']*60)}s"
        model = s["primary_model"].replace("claude-", "").replace("-20251001", "")
        fam = "opus" if "opus" in model else "sonnet" if "sonnet" in model else "haiku" if "haiku" in model else "?"
        col = {"opus": "danger", "sonnet": "primary", "haiku": "success"}.get(fam, "secondary")
        session_rows += f'''<tr>
          <td><small class="text-muted">{started}</small></td>
          <td><span class="badge text-bg-dark">{s["project"]}</span></td>
          <td><span class="badge text-bg-{col}">{fam}</span> <small><code>{model}</code></small></td>
          <td class="text-end">{s["turns"]:,}</td>
          <td class="text-end"><small>{dur}</small></td>
          <td class="text-end"><small>{s["tokens"]/1_000_000:.1f}M</small></td>
          <td class="text-end">${s["cost_usd"]:,.2f}</td>
          <td><small class="text-muted font-monospace">{s["session"][:8]}…</small></td>
        </tr>'''

    n_hive = len(hive_reports)
    n_sessions = len(sessions)
    total_cost_7d = sum(s["cost_usd"] for s in sessions)
    total_turns_7d = sum(s["turns"] for s in sessions)

    return f"""
    <div class="row mb-3">
      <div class="col-md-4"><div class="small-box text-bg-primary">
        <div class="inner"><h4>{n_sessions}</h4><p>Sessions (7d)</p></div>
        <i class="small-box-icon bi bi-chat-square-dots"></i>
      </div></div>
      <div class="col-md-4"><div class="small-box text-bg-success">
        <div class="inner"><h4>{total_turns_7d:,}</h4><p>Assistant Turns (7d)</p></div>
        <i class="small-box-icon bi bi-robot"></i>
      </div></div>
      <div class="col-md-4"><div class="small-box text-bg-warning">
        <div class="inner"><h4>${total_cost_7d:,.0f}</h4><p>Spend (7d)</p></div>
        <i class="small-box-icon bi bi-cash-stack"></i>
      </div></div>
    </div>

    <!-- Hive reports from .claude hooks -->
    <div class="card mb-3">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h3 class="card-title mb-0"><i class="bi bi-hexagon-fill me-2"></i>Hive Reports ({n_hive}) <small class="text-muted">— hook-based, from each project's <code>.claude</code></small></h3>
        <span class="badge text-bg-info">Live feed</span>
      </div>
      <div class="card-body p-0" style="max-height:320px; overflow-y:auto;">
        <table class="table table-sm table-striped mb-0">
          <thead class="sticky-top bg-body-tertiary"><tr>
            <th style="width:140px">Time</th><th style="width:130px">Project</th>
            <th style="width:120px">Event</th><th>Summary</th><th style="width:160px">User / Host</th>
          </tr></thead>
          <tbody>{hive_rows or '<tr><td colspan="5" class="text-muted text-center py-3">No hive reports yet. Hooks are deployed; entries appear as projects run sessions.</td></tr>'}</tbody>
        </table>
      </div>
    </div>

    <!-- Session log from JSONL -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title"><i class="bi bi-clock-history me-2"></i>Session Log (7d, last {n_sessions}) — who did what, from Claude Code transcripts</h3>
      </div>
      <div class="card-body p-0" style="max-height:560px; overflow-y:auto;">
        <table class="table table-sm table-striped mb-0">
          <thead class="sticky-top bg-body-tertiary"><tr>
            <th style="width:140px">Started</th>
            <th style="width:130px">Project</th>
            <th>Primary Model</th>
            <th class="text-end" style="width:70px">Turns</th>
            <th class="text-end" style="width:70px">Dur</th>
            <th class="text-end" style="width:80px">Tokens</th>
            <th class="text-end" style="width:80px">Cost</th>
            <th style="width:90px">Session</th>
          </tr></thead>
          <tbody>{session_rows or '<tr><td colspan="8" class="text-muted text-center">no sessions in window</td></tr>'}</tbody>
        </table>
      </div>
    </div>

    <p class="small text-muted mt-3">
      <i class="bi bi-info-circle me-1"></i>
      <strong>Two data sources.</strong>
      Hive Reports come from the <code>.claude</code> hooks I deployed to each project (session_start / session_end / task_done). They capture explicit intent and project-reported summaries.
      Session Log is derived from the raw Claude Code <code>.jsonl</code> transcripts — always available, shows every session whether or not the hook fired.
    </p>
    """


@app.get("/activity", response_class=HTMLResponse)
def activity_page():
    return base_layout("Activity", render_activity(), "activity")


# ── Headlines — unified ecosystem activity stream ─────────────────────────────

_HEADLINE_STYLE = {
    "session":    ("primary", "bi-chat-square-dots-fill", "Session"),
    "decision":   ("info",    "bi-signpost-2-fill",       "Decision"),
    "feature":    ("warning", "bi-stars",                 "Feature"),
    "dispatch":   ("secondary","bi-send-fill",            "Dispatch"),
    "compliance": ("danger",  "bi-shield-exclamation",    "Compliance"),
    "state":      ("dark",    "bi-arrow-repeat",          "State"),
}

_HEADLINE_KINDS = ["session", "decision", "feature", "dispatch", "compliance", "state"]


def _relative_time(iso_str: str) -> str:
    """Convert an ISO-ish timestamp into a human relative phrase."""
    if not iso_str:
        return ""
    try:
        s = iso_str[:19].replace("T", " ")
        dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except Exception:
        try:
            dt = datetime.strptime(iso_str[:10], "%Y-%m-%d")
        except Exception:
            return iso_str
    delta = datetime.now() - dt
    secs = int(delta.total_seconds())
    if secs < 60:                return f"{secs}s ago"
    if secs < 3600:              return f"{secs // 60}m ago"
    if secs < 86400:             return f"{secs // 3600}h ago"
    if secs < 86400 * 7:         return f"{secs // 86400}d ago"
    if secs < 86400 * 30:        return f"{secs // (86400 * 7)}w ago"
    if secs < 86400 * 365:       return f"{secs // (86400 * 30)}mo ago"
    return dt.strftime("%Y-%m-%d")


def _headline_row(h: dict) -> str:
    """Render a single Twitter/X-style headline row."""
    kind = h.get("kind", "")
    color, icon, label = _HEADLINE_STYLE.get(kind, ("secondary", "bi-circle", kind.title()))
    project_id = (h.get("project_id") or "?")
    agent_id   = (h.get("agent_id")   or "")
    title      = (h.get("title")      or "").replace("<", "&lt;")
    summary    = (h.get("summary")    or "").replace("<", "&lt;")
    if len(summary) > 220:
        summary = summary[:220] + "…"
    ts_iso = h.get("ts", "")
    ts_rel = _relative_time(ts_iso) or "—"   # humanize helper; fall back to em-dash not "never"

    agent_chip = ""
    if agent_id and agent_id not in ("unknown", "?"):
        agent_chip = f'<span class="badge text-bg-light border ms-1" style="font-size:.65rem">{agent_id}</span>'

    return f"""
    <div class="d-flex gap-3 py-3 border-bottom headline-row" data-kind="{kind}" data-project="{project_id}">
      <div class="flex-shrink-0 text-center" style="width:42px">
        <span class="d-inline-flex justify-content-center align-items-center rounded-circle text-bg-{color}"
              style="width:38px;height:38px"><i class="bi {icon}" style="font-size:1.05rem"></i></span>
      </div>
      <div class="flex-grow-1 min-width-0">
        <div class="d-flex flex-wrap align-items-baseline gap-2 mb-1">
          <span class="badge text-bg-{color}" style="font-size:.65rem;text-transform:uppercase;letter-spacing:.05em">{label}</span>
          <span class="badge text-bg-dark" style="font-size:.65rem">{project_id}</span>
          {agent_chip}
          <small class="text-muted ms-auto" title="{ts_iso}">{ts_rel}</small>
        </div>
        <div class="fw-semibold" style="line-height:1.3">{title}</div>
        <div class="text-muted small mt-1" style="line-height:1.35">{summary}</div>
      </div>
    </div>"""


def render_news() -> str:
    """Twitter/X-style chronological feed of everything happening across QI."""
    data = _brain_get("/api/headlines", {"limit": 200}) or {}
    headlines_list = data.get("headlines", [])

    # Compute project + kind counts for the filter chips
    proj_counts: dict[str, int] = {}
    kind_counts: dict[str, int] = {k: 0 for k in _HEADLINE_KINDS}
    for h in headlines_list:
        pid = h.get("project_id") or "?"
        proj_counts[pid] = proj_counts.get(pid, 0) + 1
        k = h.get("kind", "")
        if k in kind_counts:
            kind_counts[k] += 1

    rows_html = "".join(_headline_row(h) for h in headlines_list)
    if not rows_html:
        rows_html = ('<div class="text-center text-muted py-5">'
                     '<i class="bi bi-newspaper" style="font-size:2rem"></i>'
                     '<p class="mt-2 mb-0">Brain returned no headlines. Is QI_BrainAPI running?</p>'
                     '</div>')

    # Kind filter chips
    kind_chips = ('<button type="button" class="btn btn-sm btn-outline-secondary me-1 mb-1 active" '
                  'data-filter-kind="all">All <span class="badge text-bg-secondary ms-1">{n}</span></button>'
                  ).format(n=len(headlines_list))
    for k in _HEADLINE_KINDS:
        color, icon, label = _HEADLINE_STYLE[k]
        n = kind_counts.get(k, 0)
        kind_chips += (f'<button type="button" class="btn btn-sm btn-outline-{color} me-1 mb-1" '
                       f'data-filter-kind="{k}"><i class="bi {icon} me-1"></i>{label} '
                       f'<span class="badge text-bg-{color} ms-1">{n}</span></button>')

    # Project filter chips (sorted by count desc)
    proj_chips = ('<button type="button" class="btn btn-sm btn-outline-dark me-1 mb-1 active" '
                  'data-filter-project="all">All projects</button>')
    for pid, n in sorted(proj_counts.items(), key=lambda x: -x[1]):
        proj_chips += (f'<button type="button" class="btn btn-sm btn-outline-dark me-1 mb-1" '
                       f'data-filter-project="{pid}">{pid} '
                       f'<span class="badge text-bg-dark ms-1">{n}</span></button>')

    return f"""
    <div class="card mb-3">
      <div class="card-header py-2">
        <div class="d-flex flex-wrap gap-2 align-items-center">
          <h5 class="mb-0 me-3"><i class="bi bi-newspaper me-2"></i>Latest Across the Hive</h5>
          <small class="text-muted">Showing the last {len(headlines_list)} events — sessions, decisions, features, dispatches, compliance findings, state changes.</small>
        </div>
        <div class="mt-2"><div class="d-flex flex-wrap">{kind_chips}</div></div>
        <div class="mt-2"><div class="d-flex flex-wrap">{proj_chips}</div></div>
      </div>
      <div class="card-body p-0">
        <div id="headlines-stream" class="px-3" style="max-height:75vh;overflow-y:auto">
          {rows_html}
        </div>
      </div>
    </div>
    <script>
    (function() {{
      const stream = document.getElementById('headlines-stream');
      if (!stream) return;
      let curKind = 'all';
      let curProject = 'all';
      function applyFilters() {{
        stream.querySelectorAll('.headline-row').forEach(row => {{
          const okKind = (curKind === 'all') || (row.dataset.kind === curKind);
          const okProj = (curProject === 'all') || (row.dataset.project === curProject);
          row.style.display = (okKind && okProj) ? '' : 'none';
        }});
      }}
      document.querySelectorAll('[data-filter-kind]').forEach(btn => {{
        btn.addEventListener('click', () => {{
          document.querySelectorAll('[data-filter-kind]').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          curKind = btn.dataset.filterKind;
          applyFilters();
        }});
      }});
      document.querySelectorAll('[data-filter-project]').forEach(btn => {{
        btn.addEventListener('click', () => {{
          document.querySelectorAll('[data-filter-project]').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          curProject = btn.dataset.filterProject;
          applyFilters();
        }});
      }});
    }})();
    </script>
    """


@app.get("/news", response_class=HTMLResponse)
def news_page():
    return base_layout("Headlines", render_news(), "news")


@app.get("/api/headlines")
def api_headlines_proxy(project_id: str | None = None, since: str | None = None,
                        kinds: str | None = None, limit: int = 100):
    """Proxy to Brain so the Dashboard exposes the same endpoint shape — useful
    for Phase 2 (Kaze / Tasuke pulling the feed from the Dashboard URL)."""
    params = {"project_id": project_id, "since": since, "kinds": kinds, "limit": limit}
    data = _brain_get("/api/headlines", params)
    if data is None:
        return JSONResponse({"ok": False, "error": "brain unreachable"}, status_code=503)
    return JSONResponse(data)


# ── CoWork Dispatch — bi-directional task/proposal channel ───────────────────

def _brain_patch(path: str, payload: dict) -> dict | None:
    try:
        import urllib.request, json as _json
        data = _json.dumps(payload).encode()
        req  = urllib.request.Request(
            f"http://127.0.0.1:9011{path}", data=data,
            headers={"Content-Type": "application/json"}, method="PATCH"
        )
        with urllib.request.urlopen(req, timeout=3) as r:
            return _json.loads(r.read().decode('utf-8'))
    except Exception:
        return None


def _brain_post_dispatch(payload: dict) -> dict | None:
    import urllib.request, json as _json
    try:
        data = _json.dumps(payload).encode()
        req  = urllib.request.Request(
            "http://127.0.0.1:9011/api/dispatch", data=data,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=3) as r:
            return _json.loads(r.read().decode('utf-8'))
    except Exception:
        return None


def _get_dispatches(status_filter: str | None = None, extra: str = "", limit: int = 100) -> list[dict]:
    import urllib.request, json as _json
    try:
        url = f"http://127.0.0.1:9011/api/dispatches?limit={limit}" + extra
        if status_filter:
            url += f"&status={status_filter}"
        with urllib.request.urlopen(url, timeout=5) as r:
            return _json.loads(r.read().decode('utf-8')).get("dispatches", [])
    except Exception:
        return []


def _count_dispatches(status: str, source: str | None = None) -> int:
    """Cheap count via the API (uses the returned list length, capped at limit)."""
    import urllib.request, json as _json
    try:
        url = f"http://127.0.0.1:9011/api/dispatches?status={status}&limit=5000"
        if source:
            url += f"&source={source}"
        with urllib.request.urlopen(url, timeout=4) as r:
            return len(_json.loads(r.read().decode('utf-8')).get("dispatches", []))
    except Exception:
        return 0


def render_dispatch() -> str:
    import json as _json
    # CoWork Dispatch is the human loop: CoWork drafts → Renne approves → Claude Code
    # executes. Inspector compliance findings are a SEPARATE channel surfaced on
    # /compliance — they must NOT pollute this human-review queue (fixed 2026-06-17,
    # after 2,844 stale inspector dispatches buried the genuine CoWork items).
    #
    # We ask the API to EXCLUDE the inspector/compliance channel server-side, otherwise
    # the LIMIT window fills with inspector rows and the genuine human dispatches
    # (pending AND resolved) fall off the end and render as empty lists.
    # Belt-and-suspenders: pull a wide window AND filter client-side, so this works even
    # if the Brain API predates the exclude_source/exclude_type params.
    def _is_human(d: dict) -> bool:
        return not (d.get("source") == "hive_inspector" or d.get("type") == "compliance")
    raw = _get_dispatches(extra="&exclude_source=hive_inspector&exclude_type=compliance", limit=5000)
    human = [d for d in raw if _is_human(d)]
    pending    = [d for d in human if d["status"] == "pending"]
    discussing = [d for d in human if d["status"] == "discussing"]
    resolved   = [d for d in human if d["status"] in ("approved", "declined", "executed", "resolved")]
    inspector_pending = _count_dispatches("pending", source="hive_inspector")
    pending_total = len(pending)
    pending = pending[:30]

    SOURCE_BADGES = {
        "cowork":         ("bg-primary",  "CoWork"),
        "claude_code":    ("bg-warning text-dark", "Claude Code"),
        "renne":          ("bg-success",  "Renne"),
        "maia":           ("bg-info text-dark", "Maia"),
        "naya":           ("bg-secondary","Naya"),
        "hive_inspector": ("bg-dark",     "Inspector"),
    }
    TYPE_ICONS = {
        "report":   "bi-file-text",
        "brief":    "bi-file-earmark-text",
        "decision": "bi-lightning",
        "task":     "bi-check2-square",
        "review":   "bi-search",
        "proposal": "bi-lightbulb",
        "request":  "bi-arrow-right-circle",
        "compliance":"bi-clipboard-check",
        "auto_apply":"bi-magic",
    }
    PRIORITY_COLORS = {"high": "danger", "normal": "secondary", "medium": "warning", "low": "success"}

    def dispatch_card(d: dict, show_actions: bool = True) -> str:
        src_cls, src_label = SOURCE_BADGES.get(d["source"], ("bg-secondary", d["source"]))
        icon = TYPE_ICONS.get(d["type"], "bi-envelope")
        pri_color = PRIORITY_COLORS.get(d["priority"], "secondary")
        try:
            payload = _json.loads(d["payload"]) if isinstance(d["payload"], str) else d["payload"]
            payload_str = _json.dumps(payload, indent=2)[:600]
        except Exception:
            payload_str = str(d["payload"])[:600]
        notes_html = ""
        if d.get("notes"):
            try:
                notes = _json.loads(d["notes"]) if isinstance(d["notes"], str) else d["notes"]
                for n in notes:
                    notes_html += f'<div class="text-muted small mt-1"><strong>{n.get("by","?")}</strong>: {n.get("note","")} <span class="text-muted">({n.get("at","")[:16]})</span></div>'
            except Exception:
                pass
        actions_html = ""
        if show_actions:
            did = d["dispatch_id"]
            actions_html = f"""
            <div class="mt-2 d-flex gap-2 flex-wrap">
              <button class="btn btn-sm btn-success" onclick="reviewDispatch('{did}','approved')">
                <i class="bi bi-check-circle me-1"></i>Approve
              </button>
              <button class="btn btn-sm btn-danger" onclick="reviewDispatch('{did}','declined')">
                <i class="bi bi-x-circle me-1"></i>Decline
              </button>
              <button class="btn btn-sm btn-info" onclick="discussDispatch('{did}')">
                <i class="bi bi-chat-dots me-1"></i>Discuss
              </button>
            </div>"""
        status_badge = {
            "pending":    '<span class="badge bg-warning text-dark">Pending</span>',
            "discussing": '<span class="badge bg-info text-dark">Discussing</span>',
            "approved":   '<span class="badge bg-success">Approved</span>',
            "declined":   '<span class="badge bg-danger">Declined</span>',
            "executed":   '<span class="badge bg-primary">Executed</span>',
        }.get(d["status"], f'<span class="badge bg-secondary">{d["status"]}</span>')
        apply_state = d.get("apply_state") or None
        apply_badge = {
            "queued":         '<span class="badge bg-secondary ms-1" title="Apply: queued">Apply: queued</span>',
            "in_progress":    '<span class="badge bg-info text-dark ms-1" title="Apply: in progress">Apply: in&nbsp;progress</span>',
            "pending_review": '<span class="badge bg-info text-dark ms-1" title="Apply: awaiting inspector verdict">Apply: inspector</span>',
            "review":         '<span class="badge bg-warning text-dark ms-1" title="Apply: inspector failed — needs human review">Apply: review</span>',
            "applied":        '<span class="badge bg-success ms-1" title="Apply: applied">Apply: applied</span>',
            "failed":         '<span class="badge bg-danger ms-1" title="Apply: failed">Apply: failed</span>',
            "rejected_auto":  '<span class="badge bg-dark ms-1" title="Apply: rejected automatically">Apply: rejected</span>',
        }.get(apply_state, "") if apply_state else ""
        return f"""
        <div class="card mb-3 shadow-sm">
          <div class="card-header d-flex align-items-center gap-2">
            <i class="bi {icon} me-1"></i>
            <span class="badge {src_cls}">{src_label}</span>
            <strong class="flex-grow-1">{d['type'].capitalize()}</strong>
            <span class="badge bg-{pri_color}">{d['priority']}</span>
            {status_badge}{apply_badge}
            <small class="text-muted ms-2">{d['created_at'][:16]}</small>
          </div>
          <div class="card-body">
            <pre class="bg-body-secondary rounded p-2 small mb-2" style="max-height:200px;overflow-y:auto">{payload_str}</pre>
            {notes_html}
            {actions_html}
          </div>
        </div>"""

    def section(title: str, icon: str, items: list, show_actions: bool) -> str:
        cards = "".join(dispatch_card(d, show_actions) for d in items) if items else \
            '<p class="text-muted small">None</p>'
        return f"""
        <div class="mb-4">
          <h5><i class="bi {icon} me-2"></i>{title} <span class="badge bg-secondary">{len(items)}</span></h5>
          {cards}
        </div>"""

    return f"""
    <div class="container-fluid">
      <div class="row mb-3">
        <div class="col-12">
          <div class="card">
            <div class="card-header d-flex align-items-center justify-content-between">
              <h4 class="mb-0"><i class="bi bi-send-check me-2"></i>CoWork Dispatch</h4>
              <button class="btn btn-sm btn-outline-primary" onclick="location.reload()">
                <i class="bi bi-arrow-clockwise me-1"></i>Refresh
              </button>
            </div>
            <div class="card-body pb-1">
              <p class="text-muted small mb-0">
                Dispatches from <strong>Claude Work</strong>, <strong>Claude Code</strong>, or <strong>Renne</strong>
                — reviewed here before anything is executed.
                The loop: <strong>CoWork drafts → Renne approves → Claude Code executes.</strong>
              </p>
              {f'''<p class="small mb-0 mt-2"><span class="badge bg-dark">Inspector</span>
                {inspector_pending} open compliance finding(s) live on the
                <a href="/compliance">Compliance board →</a> — they are kept out of this
                human-review queue on purpose.</p>''' if inspector_pending else ''}
            </div>
          </div>
        </div>
      </div>

      <div class="row">
        <div class="col-lg-6">
          {section(f"Pending — Awaiting Review (showing {len(pending)} of {pending_total})", "bi-hourglass-split", pending, True)}
          {section("Discussing", "bi-chat-dots", discussing, True)}
        </div>
        <div class="col-lg-6">
          {section("Resolved (last 20)", "bi-check2-all", resolved[:20], False)}
        </div>
      </div>
    </div>

    <!-- Discuss modal -->
    <div class="modal fade" id="discussModal" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header"><h5 class="modal-title">Add Discussion Note</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button></div>
          <div class="modal-body">
            <input type="hidden" id="discussId"/>
            <textarea class="form-control" id="discussNote" rows="4" placeholder="Your note..."></textarea>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button class="btn btn-info" onclick="submitNote()">Add Note</button>
          </div>
        </div>
      </div>
    </div>

    <script>
    async function reviewDispatch(id, status) {{
      const note = status === 'declined' ? prompt('Reason for declining?') : null;
      const body = {{status, reviewed_by: 'renne'}};
      if (note) body.note = note;
      await fetch('/api/dispatch/' + id + '/review', {{
        method: 'POST', headers: {{'Content-Type':'application/json'}}, body: JSON.stringify(body)
      }});
      location.reload();
    }}
    function discussDispatch(id) {{
      document.getElementById('discussId').value = id;
      document.getElementById('discussNote').value = '';
      new bootstrap.Modal(document.getElementById('discussModal')).show();
    }}
    async function submitNote() {{
      const id = document.getElementById('discussId').value;
      const note = document.getElementById('discussNote').value;
      await fetch('/api/dispatch/' + id + '/review', {{
        method: 'POST', headers: {{'Content-Type':'application/json'}},
        body: JSON.stringify({{status:'discussing', reviewed_by:'renne', note}})
      }});
      bootstrap.Modal.getInstance(document.getElementById('discussModal')).hide();
      location.reload();
    }}
    </script>
    """


@app.post("/api/dispatch/{dispatch_id}/review")
async def api_review_dispatch(dispatch_id: str, body: dict):
    result = _brain_patch(f"/api/dispatch/{dispatch_id}", body)
    if result is None:
        return JSONResponse({"ok": False, "error": "Brain offline"})
    # Return 202 when approved — caller does not wait for apply pipeline
    status_code = 202 if body.get("status") == "approved" else 200
    return JSONResponse(result, status_code=status_code)


@app.get("/dispatch", response_class=HTMLResponse)
def dispatch_page():
    return base_layout("CoWork Dispatch", render_dispatch(), "dispatch")


# ── QI Brain — dedicated web UI ───────────────────────────────────────────────

_BRAIN_CACHE: dict[str, tuple[float, dict]] = {}
_BRAIN_CACHE_TTL = 15.0  # seconds

def _brain_get(path: str, params: dict | None = None) -> dict | None:
    import time as _t
    try:
        import urllib.request, urllib.parse, json as _json
        url = f"http://127.0.0.1:9011{path}"
        if params:
            url += "?" + urllib.parse.urlencode({k:v for k,v in params.items() if v is not None})
        now = _t.time()
        hit = _BRAIN_CACHE.get(url)
        if hit and (now - hit[0]) < _BRAIN_CACHE_TTL:
            return hit[1]
        with urllib.request.urlopen(url, timeout=3) as r:
            data = _json.loads(r.read().decode('utf-8'))
        _BRAIN_CACHE[url] = (now, data)
        return data
    except Exception:
        return None


def render_brain() -> str:
    """QI Brain dashboard — ecosystem snapshot, decisions, features, sessions,
    archive, inbox, and semantic memory search. All data pulled live from
    Brain API on page load (Brain is authoritative)."""

    snap     = _brain_get("/api/ecosystem_snapshot") or {}
    status   = _brain_get("/api/status") or {}
    poll     = _brain_get("/api/poll/status") or {}
    inbox    = _brain_get("/api/inbox/log",          {"limit": 20}) or {}
    arc_dec  = _brain_get("/api/archive/decisions",  {"limit": 25}) or {}
    arc_feat = _brain_get("/api/archive/features",   {"limit": 25}) or {}
    dist_hx  = _brain_get("/api/distill/history",    {"limit": 25}) or {}

    projects = snap.get("projects", []) if isinstance(snap, dict) else []

    # ── Overview: project grid ──
    # API returns last_phase / last_status / last_active / decisions / last_summary.
    # Older code used phase / status / last_updated -- mismatch caused "never" / "-" everywhere.
    proj_cards = ""
    for p in projects:
        pid   = p.get("project_id", "?")
        name  = p.get("display_name", pid)
        phase = p.get("last_phase") or p.get("phase") or "-"
        stat  = p.get("last_status") or p.get("status") or "-"
        last  = (p.get("last_active") or p.get("last_updated") or "")[:16] or "never"
        ndec  = p.get("decisions", 0)
        summary = (p.get("last_summary") or "")[:140]
        color = {"active":"success","active_production":"dark","active_development":"success",
                 "paused":"warning","blocked":"danger","complete":"info","pre_poc":"info",
                 "retired":"secondary","merged_into_naya":"secondary"}.get(stat, "secondary")
        proj_cards += f"""
        <div class="col-md-4 col-lg-3 mb-3">
          <div class="card h-100">
            <div class="card-body p-3">
              <div class="d-flex justify-content-between align-items-start mb-1">
                <strong>{name}</strong>
                <span class="badge text-bg-{color}">{stat}</span>
              </div>
              <div class="small text-muted">{pid}</div>
              <div class="small mt-2"><i class="bi bi-diagram-3 me-1"></i>{phase}</div>
              <div class="small text-muted mt-1"><i class="bi bi-clock me-1"></i>{last}</div>
              <div class="small text-muted mt-1"><i class="bi bi-lightbulb me-1"></i>{ndec} decisions</div>
              {f'<div class="small text-muted mt-1" style="font-size:.72rem">{summary}…</div>' if summary else ''}
            </div>
          </div>
        </div>"""

    # ── Decisions (active, live from qi_brain.db) ──
    # The snapshot endpoint doesn't include nested recent_decisions; query DB directly.
    dec_rows = ""
    active_decisions = _brain_db_query(
        "SELECT project_id, title, rationale, recorded_at FROM decisions "
        "ORDER BY recorded_at DESC LIMIT 30"
    )
    for d in active_decisions:
        dec_rows += f"""
            <tr>
              <td><span class="badge text-bg-primary">{d.get('project_id','?')}</span></td>
              <td>{d.get('title','')}</td>
              <td class="text-muted small">{(d.get('rationale') or '')[:120]}</td>
              <td class="text-muted small">{(d.get('recorded_at','') or '')[:16]}</td>
            </tr>"""
    if not dec_rows:
        dec_rows = '<tr><td colspan="4" class="text-muted text-center">No recent decisions</td></tr>'

    # ── Features (active, live from qi_brain.db) ──
    feat_rows = ""
    active_features = _brain_db_query(
        "SELECT source_project AS project_id, name, domain, description, recorded_at "
        "FROM features ORDER BY recorded_at DESC LIMIT 30"
    )
    for f in active_features:
        feat_rows += f"""
            <tr>
              <td><span class="badge text-bg-info">{f.get('project_id','?')}</span></td>
              <td>{f.get('name','')}</td>
              <td><span class="badge text-bg-secondary">{f.get('domain','-')}</span></td>
              <td class="text-muted small">{(f.get('description') or '')[:120]}</td>
            </tr>"""
    if not feat_rows:
        feat_rows = '<tr><td colspan="4" class="text-muted text-center">No recent features</td></tr>'

    # ── Archive: decisions ──
    arc_dec_rows = ""
    for d in arc_dec.get("decisions", [])[:25] if isinstance(arc_dec, dict) else []:
        arc_dec_rows += f"""
        <tr>
          <td><span class="badge text-bg-primary">{d.get('project_id','?')}</span></td>
          <td>{d.get('title','')}</td>
          <td><span class="badge text-bg-warning">{d.get('archive_reason','-')}</span></td>
          <td class="text-muted small">{d.get('scope_label','') or '-'}</td>
          <td class="text-muted small">{(d.get('archived_at','') or '')[:16]}</td>
        </tr>"""
    if not arc_dec_rows:
        arc_dec_rows = '<tr><td colspan="5" class="text-muted text-center">No archived decisions yet</td></tr>'

    # ── Archive: features ──
    arc_feat_rows = ""
    for f in arc_feat.get("features", [])[:25] if isinstance(arc_feat, dict) else []:
        arc_feat_rows += f"""
        <tr>
          <td><span class="badge text-bg-info">{f.get('source_project','?')}</span></td>
          <td>{f.get('name','')}</td>
          <td><span class="badge text-bg-warning">{f.get('archive_reason','-')}</span></td>
          <td class="text-muted small">{f.get('scope_label','') or '-'}</td>
          <td class="text-muted small">{(f.get('archived_at','') or '')[:16]}</td>
        </tr>"""
    if not arc_feat_rows:
        arc_feat_rows = '<tr><td colspan="5" class="text-muted text-center">No archived features yet</td></tr>'

    # ── Distillation history ──
    dist_rows = ""
    for d in dist_hx.get("drops", [])[:25] if isinstance(dist_hx, dict) else []:
        dist_rows += f"""
        <tr>
          <td><span class="badge text-bg-primary">{d.get('project_id','?')}</span></td>
          <td>{d.get('scope_label','-')}</td>
          <td><span class="badge text-bg-warning">{d.get('reason','-')}</span></td>
          <td class="small">{d.get('decisions_archived',0)}d / {d.get('features_archived',0)}f</td>
          <td class="text-muted small">{d.get('dropped_by','-')}</td>
          <td class="text-muted small">{(d.get('dropped_at','') or '')[:16]}</td>
        </tr>"""
    if not dist_rows:
        dist_rows = '<tr><td colspan="6" class="text-muted text-center">No distillations recorded</td></tr>'

    # ── Inbox log ──
    inbox_rows = ""
    for i in inbox.get("entries", [])[:20] if isinstance(inbox, dict) else []:
        ok = i.get("status") == "processed"
        badge = "success" if ok else "danger"
        inbox_rows += f"""
        <tr>
          <td><span class="badge text-bg-{badge}">{i.get('status','?')}</span></td>
          <td>{i.get('source','-')}</td>
          <td>{i.get('kind','-')}</td>
          <td class="text-muted small">{(i.get('note') or i.get('error') or '')[:80]}</td>
          <td class="text-muted small">{(i.get('received_at','') or '')[:16]}</td>
        </tr>"""
    if not inbox_rows:
        inbox_rows = '<tr><td colspan="5" class="text-muted text-center">Inbox empty</td></tr>'

    # Brain version + poller status line
    ver = status.get("version", "?") if isinstance(status, dict) else "?"
    poller_alive   = poll.get("poller_alive", False) if isinstance(poll, dict) else False
    poller_running = poll.get("poller_running", False) if isinstance(poll, dict) else False
    poll_badge = "success" if poller_alive else "danger"
    poll_txt   = "Running" if poller_alive else "Stopped"
    if poller_running:
        poll_txt += " (polling now)"

    return f"""
    <div class="content-header">
      <h1 class="fw-bold"><i class="bi bi-cpu me-2 text-info"></i>QI Brain</h1>
      <p class="text-muted mb-0">
        Shared memory, decisions, and ecosystem state for every QI project.
        Brain API v{ver} on :9011 ·
        Poller <span class="badge text-bg-{poll_badge}">{poll_txt}</span>
      </p>
    </div>

    <!-- Tabs -->
    <ul class="nav nav-tabs mb-3" id="brainTabs" role="tablist">
      <li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#tab-overview" type="button"><i class="bi bi-grid me-1"></i>Overview</button></li>
      <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-decisions" type="button"><i class="bi bi-check2-square me-1"></i>Decisions</button></li>
      <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-features" type="button"><i class="bi bi-stars me-1"></i>Features</button></li>
      <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-archive" type="button"><i class="bi bi-archive me-1"></i>Archive</button></li>
      <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-distill" type="button"><i class="bi bi-funnel me-1"></i>Distillation</button></li>
      <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-inbox" type="button"><i class="bi bi-inbox me-1"></i>Inbox</button></li>
      <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-search" type="button"><i class="bi bi-search me-1"></i>Search</button></li>
    </ul>

    <div class="tab-content">

      <!-- ─── Overview ─── -->
      <div class="tab-pane fade show active" id="tab-overview">
        <h5 class="mb-3"><i class="bi bi-diagram-3 me-2"></i>Projects in the Brain</h5>
        <div class="row">{proj_cards or '<div class="col-12 text-muted">No projects registered yet.</div>'}</div>
      </div>

      <!-- ─── Decisions ─── -->
      <div class="tab-pane fade" id="tab-decisions">
        <div class="card">
          <div class="card-header"><strong>Recent Active Decisions (from ecosystem snapshot)</strong></div>
          <div class="table-responsive">
            <table class="table table-sm mb-0">
              <thead><tr><th>Project</th><th>Title</th><th>Rationale</th><th>When</th></tr></thead>
              <tbody>{dec_rows}</tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- ─── Features ─── -->
      <div class="tab-pane fade" id="tab-features">
        <div class="card">
          <div class="card-header"><strong>Recent Features</strong></div>
          <div class="table-responsive">
            <table class="table table-sm mb-0">
              <thead><tr><th>Project</th><th>Name</th><th>Domain</th><th>Description</th></tr></thead>
              <tbody>{feat_rows}</tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- ─── Archive ─── -->
      <div class="tab-pane fade" id="tab-archive">
        <div class="row">
          <div class="col-lg-6">
            <div class="card">
              <div class="card-header"><strong>Archived Decisions</strong></div>
              <div class="table-responsive" style="max-height:500px;overflow-y:auto">
                <table class="table table-sm mb-0">
                  <thead><tr><th>Project</th><th>Title</th><th>Reason</th><th>Scope</th><th>When</th></tr></thead>
                  <tbody>{arc_dec_rows}</tbody>
                </table>
              </div>
            </div>
          </div>
          <div class="col-lg-6">
            <div class="card">
              <div class="card-header"><strong>Archived Features</strong></div>
              <div class="table-responsive" style="max-height:500px;overflow-y:auto">
                <table class="table table-sm mb-0">
                  <thead><tr><th>Project</th><th>Name</th><th>Reason</th><th>Scope</th><th>When</th></tr></thead>
                  <tbody>{arc_feat_rows}</tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ─── Distillation history ─── -->
      <div class="tab-pane fade" id="tab-distill">
        <div class="card">
          <div class="card-header"><strong>Distillation History</strong></div>
          <div class="table-responsive">
            <table class="table table-sm mb-0">
              <thead><tr><th>Project</th><th>Scope</th><th>Reason</th><th>Archived</th><th>By</th><th>When</th></tr></thead>
              <tbody>{dist_rows}</tbody>
            </table>
          </div>
        </div>
        <p class="text-muted small mt-2">
          💡 Trigger a new distillation from <a href="/hive">The Hive</a> page (Distil Brain Memory card).
        </p>
      </div>

      <!-- ─── Inbox ─── -->
      <div class="tab-pane fade" id="tab-inbox">
        <div class="card">
          <div class="card-header"><strong>Brain Inbox Log</strong></div>
          <div class="table-responsive">
            <table class="table table-sm mb-0">
              <thead><tr><th>Status</th><th>Source</th><th>Kind</th><th>Note / Error</th><th>Received</th></tr></thead>
              <tbody>{inbox_rows}</tbody>
            </table>
          </div>
        </div>
        <p class="text-muted small mt-2">
          💡 Drop JSON messages in <code>C:\\QIH\\engine\\brain\\inbox\\</code> or POST to <code>/api/inbox</code>.
        </p>
      </div>

      <!-- ─── Search ─── -->
      <div class="tab-pane fade" id="tab-search">
        <div class="card">
          <div class="card-header"><strong>Semantic Memory Search</strong></div>
          <div class="card-body">
            <div class="row g-2 mb-3">
              <div class="col-md-7">
                <input type="text" class="form-control" id="brainSearchQuery"
                       placeholder="Search decisions, features, sessions, docs…"
                       onkeydown="if(event.key==='Enter')runBrainSearch()"/>
              </div>
              <div class="col-md-3">
                <select class="form-select" id="brainSearchCollection">
                  <option value="decisions">Decisions</option>
                  <option value="features">Features</option>
                  <option value="sessions">Sessions</option>
                  <option value="docs">Docs</option>
                </select>
              </div>
              <div class="col-md-2">
                <button class="btn btn-primary w-100" onclick="runBrainSearch()">
                  <i class="bi bi-search me-1"></i>Search
                </button>
              </div>
            </div>
            <div id="brainSearchResults" class="text-muted">
              Type a query and press Enter. Uses ChromaDB vector embeddings.
            </div>
          </div>
        </div>
      </div>

    </div>

    <script>
    async function runBrainSearch() {{
      const q   = document.getElementById('brainSearchQuery').value.trim();
      const col = document.getElementById('brainSearchCollection').value;
      const out = document.getElementById('brainSearchResults');
      if (!q) {{ out.innerHTML = '<span class="text-muted">Empty query.</span>'; return; }}
      out.innerHTML = '<div class="spinner-border spinner-border-sm"></div> Searching…';
      try {{
        const r = await fetch('/brain-search?q=' + encodeURIComponent(q) + '&collection=' + encodeURIComponent(col) + '&n=10');
        const d = await r.json();
        const hits = d.results || d.hits || d.matches || [];
        if (!hits.length) {{ out.innerHTML = '<span class="text-muted">No matches.</span>'; return; }}
        out.innerHTML = hits.map(h => {{
          const title = h.title || h.name || h.session_title || '(untitled)';
          const body  = h.rationale || h.description || h.summary || '';
          const dist  = h.distance != null ? ' · sim=' + (1 - h.distance).toFixed(3) : '';
          const pid   = h.project_id || h.source_project || '';
          return `<div class="border-start border-4 border-info ps-2 mb-2">
            <div class="fw-bold">${{title}}
              ${{pid ? '<span class="badge text-bg-secondary ms-1">'+pid+'</span>' : ''}}
              <span class="text-muted small">${{dist}}</span>
            </div>
            <div class="small text-muted">${{(body||'').slice(0,240)}}</div>
          </div>`;
        }}).join('');
      }} catch(e) {{
        out.innerHTML = '<span class="text-danger">Brain API error: '+e+'</span>';
      }}
    }}
    </script>
    """


@app.get("/brain", response_class=HTMLResponse)
def brain_page():
    return base_layout("QI Brain", render_brain(), "brain")


# ── Mission Control — live monitoring of every agent, project, and dispatch ───
# NOTE: This is the read-only status board. The interactive multi-agent CHAT
# lives at /warroom (render_warroom_chat). The name "War Room" was reclaimed
# for the chat on 2026-06-18 — see Phase_N_War_Room_Spec_2026-06-18.md.

def render_mission_control() -> str:
    """Mission Control: single-pane-of-glass showing all agents, projects, and
    dispatches in flight. Refreshes every 30s. Data from Brain + Hive registry."""

    snap    = _brain_get("/api/ecosystem_snapshot") or {}
    poll    = _brain_get("/api/poll/status") or {}
    inbox   = _brain_get("/api/inbox/log", {"limit": 5}) or {}
    disp    = _brain_get("/api/dispatches", {"limit": 20}) or {}

    projects    = snap.get("projects", []) if isinstance(snap, dict) else []
    dispatches  = disp.get("dispatches", []) if isinstance(disp, dict) else []
    inbox_items = inbox.get("entries", []) if isinstance(inbox, dict) else []

    # ── Agents panel (Claude Code, Claude Work, CoWork, Claude Chat) ──
    # Read directly from Brain SQLite — no HTTP hop, no Brain restart needed.
    last_seen_by_agent = {
        a["agent_id"]: a
        for a in _brain_db_agents_last_seen()
    }

    agent_types = [
        ("claude_code",  "Claude Code",  "bi-terminal",      "primary"),
        ("claude",       "Claude (Interactive)", "bi-chat-square-dots","info"),
        ("cowork",       "CoWork",       "bi-people",        "success"),
        ("claude_work",  "Claude Work",  "bi-window-desktop","secondary"),
    ]
    agent_cards = ""
    for aid, label, icon, color in agent_types:
        seen = last_seen_by_agent.get(aid)
        if seen:
            last_touch  = html.escape((seen.get("last_ts") or "")[:16] or "never")
            active_proj = html.escape(seen.get("last_project") or "-")
            last_event  = html.escape(seen.get("last_event") or "-")
            last_model  = html.escape(seen.get("last_model") or "")
            card_color  = color
            sub_line    = f'on: {active_proj} &nbsp;<span class="text-muted">({last_event})</span>'
            if last_model:
                sub_line += f'<br/><span class="text-muted small">model: {last_model}</span>'
        else:
            last_touch  = "never"
            card_color  = "secondary"
            sub_line    = '<span class="text-muted">no heartbeats recorded</span>'
        agent_cards += f"""
        <div class="col-md-6 col-xl-3 mb-3">
          <div class="card h-100 border-start border-4 border-{card_color}">
            <div class="card-body p-3">
              <div class="d-flex justify-content-between align-items-start">
                <h5 class="mb-1"><i class="bi {icon} me-2 text-{card_color}"></i>{label}</h5>
                <span class="badge text-bg-{card_color}">agent</span>
              </div>
              <div class="small text-muted mb-1">ID: <code>{aid}</code></div>
              <div class="small">Last active: <strong>{last_touch}</strong></div>
              <div class="small">{sub_line}</div>
            </div>
          </div>
        </div>"""

    # ── Project heat map ──
    # Sort projects by last_active desc
    sorted_proj = sorted(projects, key=lambda p: (p.get("last_active") or ""), reverse=True)
    proj_rows = ""
    for p in sorted_proj:
        pid     = html.escape(p.get("project_id", "?"))
        name    = html.escape(p.get("display_name", pid))
        phase   = html.escape(p.get("last_phase", "-") or "-")
        stat    = html.escape(p.get("last_status", "-") or "-")
        last    = html.escape((p.get("last_active") or "")[:16] or "never")
        summary = html.escape((p.get("last_summary") or "")[:140])
        color = {"active":"success","paused":"secondary","blocked":"danger",
                 "complete":"info"}.get(p.get("last_status") or "", "secondary")
        proj_rows += f"""
        <tr>
          <td><strong>{name}</strong><br/><span class="text-muted small">{pid}</span></td>
          <td><span class="badge text-bg-{color}">{stat}</span></td>
          <td class="small">{phase}</td>
          <td class="small text-muted">{summary}</td>
          <td class="small text-muted">{last}</td>
        </tr>"""
    if not proj_rows:
        proj_rows = '<tr><td colspan="5" class="text-muted text-center">No projects in Brain</td></tr>'

    # ── Active dispatches ──
    disp_rows = ""
    for d in dispatches[:15]:
        status      = d.get("status", "?")
        badge = {"pending":"warning","approved":"success","rejected":"danger","declined":"danger",
                 "resolved":"secondary","executed":"secondary",
                 "discussing":"info","in_progress":"primary","done":"secondary"}.get(status, "secondary")
        # Real dispatch schema is source/type/payload/project_id — map accordingly.
        try:
            _pl = json.loads(d.get("payload") or "{}")
        except Exception:
            _pl = {}
        d_status    = html.escape(status)
        d_proj      = html.escape(d.get("project_id") or "-")
        d_title     = html.escape((d.get("title") or _pl.get("message") or d.get("type") or "")[:60])
        d_from      = html.escape(d.get("from_agent") or d.get("source") or "-")
        d_to        = html.escape(d.get("to_agent") or d.get("reviewed_by") or "—")
        d_created   = html.escape((d.get("created_at") or d.get("ts") or "")[:16])
        disp_rows += f"""
        <tr>
          <td><span class="badge text-bg-{badge}">{d_status}</span></td>
          <td>{d_proj}</td>
          <td class="small">{d_title}</td>
          <td class="small text-muted">{d_from} → {d_to}</td>
          <td class="small text-muted">{d_created}</td>
        </tr>"""
    if not disp_rows:
        disp_rows = '<tr><td colspan="5" class="text-muted text-center">No active dispatches</td></tr>'

    # ── Brain heartbeat ──
    poller_alive   = poll.get("poller_alive", False) if isinstance(poll, dict) else False
    poller_running = poll.get("poller_running", False) if isinstance(poll, dict) else False
    last_poll = (poll.get("last_result", {}) or {}).get("finished_at", "never")[:16] if isinstance(poll, dict) else "?"
    proj_checked = (poll.get("last_result", {}) or {}).get("projects_checked", 0) if isinstance(poll, dict) else 0
    changes      = (poll.get("last_result", {}) or {}).get("changes_found", 0) if isinstance(poll, dict) else 0
    brain_color = "success" if poller_alive else "danger"

    # Inbox recent activity
    inbox_html = ""
    for i in inbox_items[:5]:
        ok = i.get("status") == "processed"
        b = "success" if ok else "danger"
        i_status   = html.escape(i.get("status") or "?")
        i_source   = html.escape(i.get("source") or "-")
        i_kind     = html.escape(i.get("kind") or "-")
        i_received = html.escape((i.get("received_at") or "")[:16])
        inbox_html += f"""
        <div class="border-start border-4 border-{b} ps-2 mb-2 small">
          <span class="badge text-bg-{b}">{i_status}</span>
          {i_source} · {i_kind}
          <span class="text-muted">· {i_received}</span>
        </div>"""
    if not inbox_html:
        inbox_html = '<div class="text-muted small">No recent inbox activity.</div>'

    return f"""
    <div class="content-header d-flex justify-content-between align-items-start">
      <div>
        <h1 class="fw-bold"><i class="bi bi-broadcast-pin me-2 text-danger"></i>Mission Control</h1>
        <p class="text-muted mb-0">
          Single-pane-of-glass across every QI agent, project, and dispatch in flight.
          Auto-refreshes every 30s.
          <a href="/warroom" class="ms-2"><i class="bi bi-chat-dots"></i> Open the War Room chat &rarr;</a>
          <a href="/agents" class="ms-2"><i class="bi bi-person-badge"></i> Personnel files &rarr; Agent HR</a>
        </p>
      </div>
      <div>
        <button class="btn btn-sm btn-outline-primary" onclick="location.reload()">
          <i class="bi bi-arrow-clockwise me-1"></i>Refresh now
        </button>
      </div>
    </div>

    <!-- Agents strip -->
    <h5 class="mt-2 mb-2"><i class="bi bi-people-fill me-2"></i>Active Agents</h5>
    <div class="row">{agent_cards}</div>

    <div class="row">

      <!-- Project heat table -->
      <div class="col-lg-8 mb-3">
        <div class="card h-100">
          <div class="card-header d-flex justify-content-between align-items-center">
            <strong><i class="bi bi-fire me-2 text-warning"></i>Project Heat — who's being touched</strong>
            <a href="/brain" class="btn btn-sm btn-outline-secondary">Open Brain →</a>
          </div>
          <div class="table-responsive">
            <table class="table table-sm mb-0">
              <thead><tr><th>Project</th><th>Status</th><th>Phase</th><th>Last Summary</th><th>Last Active</th></tr></thead>
              <tbody>{proj_rows}</tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Brain heartbeat -->
      <div class="col-lg-4 mb-3">
        <div class="card h-100">
          <div class="card-header"><strong><i class="bi bi-cpu me-2 text-info"></i>Brain Heartbeat</strong></div>
          <div class="card-body">
            <div class="mb-2">
              Poller: <span class="badge text-bg-{brain_color}">{'Running' if poller_alive else 'Stopped'}</span>
              {'<span class="badge text-bg-warning">Polling now</span>' if poller_running else ''}
            </div>
            <div class="small text-muted mb-1">Last poll: <strong>{last_poll}</strong></div>
            <div class="small text-muted mb-1">Projects checked: <strong>{proj_checked}</strong></div>
            <div class="small text-muted mb-3">Changes found: <strong>{changes}</strong></div>
            <h6 class="mt-3 mb-2">Recent Inbox</h6>
            {inbox_html}
            <a href="/brain#tab-inbox" class="btn btn-sm btn-outline-secondary mt-2">Open Inbox →</a>
          </div>
        </div>
      </div>

    </div>

    <!-- Dispatches -->
    <div class="card mb-3">
      <div class="card-header d-flex justify-content-between align-items-center">
        <strong><i class="bi bi-send-check me-2 text-success"></i>Dispatches in Flight</strong>
        <a href="/dispatch" class="btn btn-sm btn-outline-secondary">Open Dispatch Center →</a>
      </div>
      <div class="table-responsive">
        <table class="table table-sm mb-0">
          <thead><tr><th>Status</th><th>Project</th><th>Title</th><th>Agents</th><th>Created</th></tr></thead>
          <tbody>{disp_rows}</tbody>
        </table>
      </div>
    </div>

    <script>
      // Auto-refresh every 30s
      setTimeout(() => location.reload(), 30000);
    </script>
    """


@app.get("/mission-control", response_class=HTMLResponse)
def mission_control_page():
    return base_layout("Mission Control", render_mission_control(), "mission")


# Back-compat: old /warroom bookmarks now land on the CHAT (below). The monitoring
# board moved to /mission-control. Anyone deep-linking the old status board can use
# /mission-control directly.


# ── War Room — Phase N Stage 0: live multi-agent text chat ────────────────────
# Renne + every QI agent talk in one room. Messages live in qi_brain.db
# (warroom_messages). This page polls the dashboard's own /warroom/messages proxy
# (same-origin, so it works through the public tunnel). Avatars + voice = later
# stages — see Phase_N_War_Room_Spec_2026-06-18.md.

_WARROOM_LABELS = {
    "renne":       ("Renne",                "person-circle",     "warning"),
    "hive":        ("Hive (host)",          "hexagon-fill",      "info"),
    "claude_code": ("Claude Code",          "terminal",          "primary"),
    "claude":      ("Claude (Interactive)", "chat-square-dots",  "info"),
    "claude_work": ("Claude Work",          "window-desktop",    "secondary"),
    "cowork":      ("CoWork",               "people",            "success"),
    "architect":  ("Architect",  "compass",        "primary"),
    "builder":    ("Builder",    "hammer",         "success"),
    "inspector":  ("Inspector",  "search",         "danger"),
    "ops":        ("Ops",        "gear",           "secondary"),
    "scout":      ("Scout",      "binoculars",     "info"),
    "scribe":     ("Scribe",     "pencil",         "warning"),
    "tester":     ("Tester",     "bug",            "danger"),
}


def _warroom_meta(agent_id: str) -> tuple[str, str, str]:
    """(label, bootstrap-icon, color) for an agent_id; sensible fallback if unknown."""
    return _WARROOM_LABELS.get(agent_id, (agent_id, "robot", "secondary"))


def render_warroom_chat() -> str:
    """The War Room chat: text-only multi-way conversation between Renne and every
    QI agent. Phase N Stage 0 — the foundation for the avatar/voice vision."""

    rows = _brain_db_query(
        """SELECT id, agent_id, agent_label, body, project_id, ts
           FROM warroom_messages ORDER BY id DESC LIMIT 100"""
    )[::-1]

    bubbles = ""
    last_id = 0
    for m in rows:
        last_id = max(last_id, m.get("id") or 0)
        aid   = m.get("agent_id") or "?"
        _lbl, icon, color = _warroom_meta(aid)
        label = html.escape(m.get("agent_label") or _lbl)
        body  = html.escape(m.get("body") or "").replace("\n", "<br/>")
        ts    = html.escape((m.get("ts") or "")[:16])
        mine  = " warroom-mine" if aid == "renne" else ""
        bubbles += f"""
        <div class="warroom-msg{mine}">
          <div class="warroom-avatar text-bg-{color}"><i class="bi bi-{icon}"></i></div>
          <div class="warroom-bubble">
            <div class="warroom-meta"><strong>{label}</strong> <span class="text-muted small">{ts}</span></div>
            <div class="warroom-body">{body}</div>
          </div>
        </div>"""
    if not bubbles:
        bubbles = '<div class="text-muted text-center p-4">No messages yet. Say hello 👋</div>'

    return f"""
    <div class="content-header">
      <h1 class="fw-bold"><i class="bi bi-chat-dots me-2 text-info"></i>War Room</h1>
      <p class="text-muted mb-0">
        Live text chat between Renne and every QI agent — Claude Code, Claude Work,
        CoWork and the seven Hive agents. Phase N Stage 0 (avatars &amp; voice come later;
        see <a href="/mission-control">Mission Control</a> for the live status board).
      </p>
    </div>

    <style>
      #warroom-feed {{ max-height:62vh; overflow-y:auto; padding:1rem;
                       border:1px solid var(--bs-border-color); border-radius:.6rem; }}
      .warroom-msg {{ display:flex; gap:.6rem; margin-bottom:1rem; align-items:flex-start; }}
      .warroom-msg.warroom-mine {{ flex-direction:row-reverse; }}
      .warroom-avatar {{ width:38px; height:38px; min-width:38px; border-radius:50%;
                         display:flex; align-items:center; justify-content:center; font-size:1.1rem; }}
      .warroom-bubble {{ background:var(--bs-tertiary-bg); border-radius:.7rem; padding:.5rem .8rem; max-width:78%; }}
      .warroom-mine .warroom-bubble {{ background:var(--bs-warning-bg-subtle); }}
      .warroom-meta {{ margin-bottom:.15rem; }}
      .warroom-body {{ white-space:normal; word-break:break-word; }}
    </style>

    <div id="warroom-feed" data-last="{last_id}">{bubbles}</div>

    <form id="warroom-form" class="mt-3 d-flex gap-2" onsubmit="return warroomSend(event)">
      <input type="text" id="warroom-input" class="form-control"
             placeholder="Message the War Room as Renne…" autocomplete="off" maxlength="8000" />
      <button class="btn btn-info" type="submit"><i class="bi bi-send"></i> Send</button>
    </form>
    <div class="form-text">Posts as <strong>renne</strong>. The <strong>Hive</strong> host replies by
      default; address a specialist with <code>@architect</code>, <code>@builder</code>, <code>@inspector</code>,
      <code>@ops</code>, <code>@scout</code>, <code>@scribe</code> or <code>@tester</code>. Replies are generated
      by the local NEXUS LLM. Feed auto-refreshes every 4s.</div>

    <script>
      const feed = document.getElementById('warroom-feed');
      const AGENT_COLORS = {{
        renne:'warning', hive:'info', claude_code:'primary', claude:'info', claude_work:'secondary',
        cowork:'success', architect:'primary', builder:'success', inspector:'danger',
        ops:'secondary', scout:'info', scribe:'warning', tester:'danger'
      }};
      const AGENT_ICONS = {{
        renne:'person-circle', hive:'hexagon-fill', claude_code:'terminal', claude:'chat-square-dots',
        claude_work:'window-desktop', cowork:'people', architect:'compass',
        builder:'hammer', inspector:'search', ops:'gear', scout:'binoculars',
        scribe:'pencil', tester:'bug'
      }};
      function esc(s) {{ const d=document.createElement('div'); d.textContent=s||''; return d.innerHTML; }}
      function addMsg(m) {{
        const color = AGENT_COLORS[m.agent_id] || 'secondary';
        const icon  = AGENT_ICONS[m.agent_id]  || 'robot';
        const mine  = m.agent_id === 'renne' ? ' warroom-mine' : '';
        const div = document.createElement('div');
        div.className = 'warroom-msg' + mine;
        div.innerHTML =
          '<div class="warroom-avatar text-bg-'+color+'"><i class="bi bi-'+icon+'"></i></div>' +
          '<div class="warroom-bubble"><div class="warroom-meta"><strong>'+esc(m.agent_label||m.agent_id)+
          '</strong> <span class="text-muted small">'+esc((m.ts||'').slice(0,16))+'</span></div>' +
          '<div class="warroom-body">'+esc(m.body).replace(/\\n/g,'<br/>')+'</div></div>';
        feed.appendChild(div);
      }}
      async function poll() {{
        try {{
          const since = feed.dataset.last || 0;
          const r = await fetch('/warroom/messages?since_id='+since);
          const j = await r.json();
          if (j.messages && j.messages.length) {{
            const empty = feed.querySelector('.text-muted.text-center');
            if (empty) empty.remove();
            const atBottom = feed.scrollHeight - feed.scrollTop - feed.clientHeight < 80;
            j.messages.forEach(addMsg);
            feed.dataset.last = j.last_id;
            if (atBottom) feed.scrollTop = feed.scrollHeight;
          }}
        }} catch (e) {{ /* transient — keep polling */ }}
      }}
      async function warroomSend(ev) {{
        ev.preventDefault();
        const inp = document.getElementById('warroom-input');
        const text = inp.value.trim();
        if (!text) return false;
        inp.value = '';
        try {{
          await fetch('/warroom/send', {{
            method:'POST', headers:{{'Content-Type':'application/json'}},
            body: JSON.stringify({{ body: text }})
          }});
          await poll();
        }} catch (e) {{ inp.value = text; }}
        return false;
      }}
      feed.scrollTop = feed.scrollHeight;
      setInterval(poll, 4000);
    </script>
    """


@app.get("/warroom", response_class=HTMLResponse)
def warroom_page():
    return base_layout("War Room", render_warroom_chat(), "warroom")


@app.get("/warroom/messages")
def warroom_messages(since_id: int = 0, limit: int = 100):
    """Same-origin JSON feed for the War Room poller (reads Brain SQLite directly,
    so it works with no Brain restart and through the public tunnel)."""
    limit = max(1, min(limit, 500))
    rows = _brain_db_query(
        """SELECT id, agent_id, agent_label, body, project_id, ts
           FROM warroom_messages WHERE id > ? ORDER BY id DESC LIMIT ?""",
        (since_id, limit),
    )[::-1]
    return JSONResponse({"messages": rows, "last_id": (rows[-1]["id"] if rows else since_id)})


@app.post("/warroom/ingest")
async def warroom_ingest(request: Request):
    """Inbound bridge endpoint (e.g. Telegram via Tasuke in WSL). Writes the message
    on the Windows side — avoids SQLite-WAL-over-WSL-/mnt 'disk I/O error'. Tagged
    project_id='telegram_in' so the outbound relay never echoes it back."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    text = (body.get("text") or body.get("body") or "").strip()
    if not text:
        return JSONResponse({"ok": False, "error": "empty"}, status_code=400)
    label = body.get("label") or "Renne (Telegram)"
    new_id = _brain_db_execute(
        """INSERT INTO warroom_messages (agent_id, agent_label, body, project_id)
           VALUES ('renne', ?, ?, 'telegram_in')""",
        (label[:64], text[:8000]),
    )
    if new_id is None:
        return JSONResponse({"ok": False, "error": "write_failed"}, status_code=500)
    return JSONResponse({"ok": True, "id": new_id})


@app.post("/warroom/send")
async def warroom_send(request: Request):
    """Post a message to the War Room as Renne. Writes straight to qi_brain.db
    (WAL-safe) so the human chat never depends on a Brain restart."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    text = (body.get("body") or "").strip()
    if not text:
        return JSONResponse({"ok": False, "error": "empty"}, status_code=400)
    text = text[:8000]
    new_id = _brain_db_execute(
        """INSERT INTO warroom_messages (agent_id, agent_label, body, project_id)
           VALUES ('renne', 'Renne', ?, ?)""",
        (text, body.get("project_id")),
    )
    if new_id is None:
        return JSONResponse({"ok": False, "error": "write_failed"}, status_code=500)
    return JSONResponse({"ok": True, "id": new_id})


# ── Compliance proxy → Brain Inspector ────────────────────────────────────────
import urllib.request as _ureq
import urllib.error as _uerr

_BRAIN = "http://127.0.0.1:9011"


def _brain_request(method: str, path: str, body: dict | None = None, timeout: float = 30.0):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = _ureq.Request(
        f"{_BRAIN}{path}",
        data=data,
        headers={"Content-Type": "application/json"} if body is not None else {},
        method=method,
    )
    try:
        with _ureq.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except _uerr.HTTPError as e:
        return e.code, {"ok": False, "error": e.read().decode("utf-8", errors="replace")[:500]}
    except Exception as e:
        return 502, {"ok": False, "error": f"{type(e).__name__}: {e}"}


@app.get("/compliance", response_class=HTMLResponse)
def compliance_page():
    """Standards-compliance UI — talks to /api/compliance/* (proxied to Brain)."""
    p = Path(__file__).parent / "static" / "compliance.html"
    content = p.read_text(encoding="utf-8")
    return base_layout("Compliance", content, "compliance")


@app.get("/api/compliance/status")
def api_compliance_status():
    code, body = _brain_request("GET", "/api/compliance/status")
    return JSONResponse(content=body, status_code=code)


@app.get("/api/compliance/recent")
def api_compliance_recent(project_id: Optional[str] = None, limit: int = 50):
    qs = f"?limit={limit}" + (f"&project_id={project_id}" if project_id else "")
    code, body = _brain_request("GET", f"/api/compliance/recent{qs}")
    return JSONResponse(content=body, status_code=code)


class _ComplianceScanReq(BaseModel):
    project_id: Optional[str] = None
    mode: str = "fast"
    auto_fix: bool = True


@app.post("/api/compliance/scan")
def api_compliance_scan(req: _ComplianceScanReq):
    code, body = _brain_request("POST", "/api/compliance/scan",
                                {"project_id": req.project_id, "mode": req.mode, "auto_fix": req.auto_fix},
                                timeout=120.0)
    return JSONResponse(content=body, status_code=code)


# ── Agent HR — roster + metrics for QI Hive / Claude Code sub-agents ───────────
# Read-only against C:\QIH\engine\hive\agents\agent_hr.db (owned by agent_hr.py —
# seeded/backfilled/ingested by the CLI + the SubagentStop hook, not by the
# dashboard). Named /api/agent-hr* to avoid colliding with the existing
# /api/agents endpoint (Brain agent-team roster used by Mission Control).

_AGENT_HR_DB = r"C:\QIH\engine\hive\agents\agent_hr.db"


def _agent_hr_conn():
    import sqlite3
    return sqlite3.connect(f"file:{Path(_AGENT_HR_DB).as_posix()}?mode=ro", uri=True, timeout=2.0)


def _resolve_registry_project(path: str):
    """Longest-prefix match of a `runs.project` filesystem path against
    qi_registry.json project roots (same technique as doc_harvester.py /
    subagent_stop.py). Returns the registry project id, or None if the path
    doesn't fall under any registered project root — the caller renders those
    as plain text rather than a dead `/project/<id>` link."""
    if not path:
        return None
    import os
    try:
        reg = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    p_n = os.path.normcase(os.path.normpath(path))
    best, best_len = None, -1
    for proj in reg.get("projects", []):
        root = proj.get("path") or ""
        if not root:
            continue
        r_n = os.path.normcase(os.path.normpath(root))
        if (p_n == r_n or p_n.startswith(r_n + os.sep)) and len(r_n) > best_len:
            best, best_len = proj.get("id"), len(r_n)
    return best


@app.get("/api/agent-hr")
def api_agent_hr():
    if not Path(_AGENT_HR_DB).exists():
        return JSONResponse({"ok": False, "error": "agent_hr.db not found — run agent_hr.py --seed", "agents": []})
    try:
        conn = _agent_hr_conn()
        try:
            agents = conn.execute(
                "SELECT name, kind, model, description, first_seen, last_active, status FROM agents "
                "ORDER BY (last_active IS NULL), last_active DESC, name ASC"
            ).fetchall()
            out = []
            for name, kind, model, description, first_seen, last_active, status in agents:
                agg = conn.execute(
                    "SELECT COUNT(*), COALESCE(SUM(tokens),0), COALESCE(SUM(duration_ms),0) "
                    "FROM runs WHERE agent = ?", (name,)
                ).fetchone()
                runs_count, tokens_sum, ms_sum = agg
                recent = conn.execute(
                    "SELECT task_desc, project, started_at FROM runs WHERE agent = ? "
                    "ORDER BY started_at DESC LIMIT 3", (name,)
                ).fetchall()
                projects = conn.execute(
                    "SELECT DISTINCT project FROM runs WHERE agent = ? AND project IS NOT NULL", (name,)
                ).fetchall()
                out.append({
                    "name": name, "kind": kind, "model": model, "description": description,
                    "first_seen": first_seen, "last_active": last_active, "status": status,
                    "runs": runs_count,
                    "tokens": tokens_sum,
                    "tokens_k": round(tokens_sum / 1000, 1),
                    "hours": round(ms_sum / 3600000, 2),
                    "recent_tasks": [{"task_desc": t, "project": p, "project_id": _resolve_registry_project(p),
                                       "started_at": s} for t, p, s in recent],
                    "projects": [p for (p,) in projects],
                })
            return JSONResponse({"ok": True, "agents": out})
        finally:
            conn.close()
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e), "agents": []}, status_code=503)


@app.get("/api/agent-hr/runs")
def api_agent_hr_runs(agent: str):
    if not Path(_AGENT_HR_DB).exists():
        return JSONResponse({"ok": False, "error": "agent_hr.db not found", "runs": []})
    try:
        conn = _agent_hr_conn()
        try:
            rows = conn.execute(
                "SELECT project, task_desc, started_at, duration_ms, tokens, tool_uses, outcome, session_id "
                "FROM runs WHERE agent = ? ORDER BY started_at DESC LIMIT 50", (agent,)
            ).fetchall()
            runs = [{
                "project": p, "project_id": _resolve_registry_project(p), "task_desc": t,
                "started_at": s, "duration_ms": d,
                "tokens": tok, "tool_uses": tu, "outcome": o, "session_id": sid,
            } for p, t, s, d, tok, tu, o, sid in rows]
            return JSONResponse({"ok": True, "agent": agent, "runs": runs})
        finally:
            conn.close()
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e), "runs": []}, status_code=503)


@app.get("/agents", response_class=HTMLResponse)
def agent_hr_page():
    p = Path(__file__).parent / "static" / "agent_hr.html"
    content = p.read_text(encoding="utf-8")
    return base_layout("Agent HR", content, "agent_hr")


# ── Brain reverse-proxy (tunnel parity) ──────────────────────────────────────
# Lets the dashboard's browser code reach the Brain API (:9011) through the
# dashboard's OWN origin, so it behaves identically on localhost and over the
# public HTTPS tunnel (no mixed-content block, no "127.0.0.1 = the viewer's
# machine" problem). GET is open (read-only views). Mutating verbs still pass
# through the tunnel_write_guard middleware above, so they remain token-gated
# when they arrive via the tunnel — security posture is unchanged.

def _brain_proxy_raw(method: str, path: str, query: str, body: bytes | None, ctype: str | None):
    url = f"{_BRAIN}/{path}"
    if query:
        url += "?" + query
    headers = {"Content-Type": ctype} if ctype else {}
    req = _ureq.Request(url, data=body, headers=headers, method=method)
    try:
        with _ureq.urlopen(req, timeout=60) as r:
            return r.status, r.read(), r.headers.get("Content-Type", "application/json")
    except _uerr.HTTPError as e:
        return e.code, e.read(), e.headers.get("Content-Type", "application/json")
    except Exception as e:
        import json as _json
        return 502, _json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}).encode(), "application/json"


@app.get("/brain/docs", response_class=HTMLResponse)
def brain_docs_proxy():
    """Proxy Brain's Swagger UI, rewriting its spec URL to the proxied path so it
    renders over the tunnel (swagger-ui assets come from a CDN and load fine)."""
    status, raw, _ = _brain_proxy_raw("GET", "docs", "", None, None)
    html_text = raw.decode("utf-8", errors="replace").replace("/openapi.json", "/brain/openapi.json")
    return HTMLResponse(content=html_text, status_code=status)


@app.get("/brain-search")
def brain_search_proxy(q: str, collection: str = "decisions", n: int = 10):
    """Read-only Brain memory search usable over the tunnel (GET → not gated)."""
    code, body = _brain_request("POST", "/api/search_memory",
                                {"query": q, "collection": collection, "n": n})
    return JSONResponse(content=body, status_code=code)


@app.api_route("/brain/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def brain_proxy(path: str, request: Request):
    raw_body = await request.body()
    status, raw, ctype = _brain_proxy_raw(
        request.method, path, request.url.query,
        raw_body if raw_body else None,
        request.headers.get("content-type"),
    )
    return Response(content=raw, status_code=status, media_type=ctype)


# ── Ops Control Panel (added 2026-07-27) ─────────────────────────────────────
# Run the manual maintenance scripts (supervisor, snapshots, self-audit, service
# restarts, ...) from the dashboard instead of a terminal. Actions run in a
# background thread; the page polls /api/ops/status for live state + output.
# POSTs are covered by the tunnel_write_guard middleware (token required via
# tunnel; localhost/LAN unaffected).

import threading as _ops_threading

OPS_HISTORY_FILE = _PROJECT_DIR / "data" / "ops_history.json"
_OPS_PY = sys.executable

# Ordered, safe (read-only / diagnostic) actions for the one-click sequence.
# Service restarts and apply-mode actions are deliberately NOT in it.
OPS_SEQUENCE = ["supervisor", "snapshots", "self_audit", "voice_bridge_health", "headroom_status"]

OPS_ACTIONS = {
    "run_sequence": {
        "label": "Run Full Maintenance Sequence",
        "desc":  "Runs the safe diagnostics one at a time, in order: Supervisor → Brain Snapshots → Self-Audit → Voice Bridge Health → Headroom Status. Each step finishes before the next starts; the output shows a per-step log. Schedulable like any card (e.g. daily 06:00).",
        "icon":  "bi-collection-play", "group": "Monitoring", "confirm": True, "timeout": 4000,
        "special": "sequence",
        "cmd":   [],  # handled internally
    },
    "supervisor": {
        "label": "Run Supervisor",
        "desc":  "Full ecosystem drift scan — regenerates C:\\APPS\\CLAUDE\\DASHBOARD.md, report.json and the Hive status feed. Takes a few minutes (walks every project, services + scheduled tasks).",
        "icon":  "bi-radar", "group": "Monitoring", "confirm": False, "timeout": 1800,
        "cmd":   [_OPS_PY, r"C:\APPS\CLAUDE\supervisor\supervisor.py"],
    },
    "snapshots": {
        "label": "Refresh Brain Snapshots",
        "desc":  "Runs gen_latest.py — rebuilds C:\\APPS\\CLAUDE\\status.json and Session Summaries\\LATEST.md from QI Brain (:9011, falls back to :9010).",
        "icon":  "bi-arrow-repeat", "group": "Monitoring", "confirm": False, "timeout": 120,
        "cmd":   [_OPS_PY, r"C:\APPS\CLAUDE\gen_latest.py"],
    },
    "self_audit": {
        "label": "Self-Audit (report only)",
        "desc":  "qi_self_audit.py without --apply-safe — reports orphaned processes, stale worktrees, config bloat. Read-only.",
        "icon":  "bi-clipboard-check", "group": "Monitoring", "confirm": False, "timeout": 900,
        "cmd":   [_OPS_PY, r"C:\APPS\CLAUDE\Tools\qi_self_audit.py"],
    },
    "self_audit_apply": {
        "label": "Self-Audit + Safe Fixes",
        "desc":  "qi_self_audit.py --apply-safe — also auto-fixes the safe items (kills orphans, prunes clean worktrees, trims .claude.json bloat).",
        "icon":  "bi-tools", "group": "Maintenance", "confirm": True, "timeout": 900,
        "cmd":   [_OPS_PY, r"C:\APPS\CLAUDE\Tools\qi_self_audit.py", "--apply-safe"],
    },
    "lock_scan": {
        "label": "Claude Lock Scan",
        "desc":  "claude_restart_guard.ps1 -Scan — read-only report of Claude/MCP processes holding locks on the install. Does not kill anything.",
        "icon":  "bi-search", "group": "Maintenance", "confirm": False, "timeout": 300,
        "cmd":   ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                  "-File", r"C:\APPS\CLAUDE\Tools\claude_restart_guard.ps1", "-Scan"],
    },
    "maia_restart": {
        "label": "Restart Maia Services",
        "desc":  "maia_restart_services.py — bounces QI MaiaTunnel + MaiaBot via sc.exe (needs the one-time service-rights grant; no admin prompt).",
        "icon":  "bi-bootstrap-reboot", "group": "Services", "confirm": True, "timeout": 300,
        "cmd":   [_OPS_PY, r"C:\APPS\CLAUDE\Tools\maia_restart_services.py"],
    },
    "voice_bridge_health": {
        "label": "Claude Voice Bridge Health",
        "desc":  "bridge_health.py — checks the Claude Voice services/bridge and writes data\\bridge_health.json.",
        "icon":  "bi-mic", "group": "Services", "confirm": False, "timeout": 300,
        "cmd":   [_OPS_PY, r"C:\APPS\CLAUDE\Claude Voice\bridge_health.py"],
        "cwd":   r"C:\APPS\CLAUDE\Claude Voice",
    },
    "tasuke_test": {
        "label": "Test Tasuke Notification",
        "desc":  "Sends a test push through the Tasuke LINE channel. NOTE: broadcast — every follower of the Tasuke OA receives it.",
        "icon":  "bi-bell", "group": "Services", "confirm": True, "timeout": 60,
        "cmd":   [_OPS_PY, r"C:\APPS\CLAUDE\Tools\qi_tasuke_notify.py",
                  "Test notification from the QI Hive Ops panel."],
    },
    "restart_dashboard": {
        "label": "Restart Dashboard (this app)",
        "desc":  "Restarts QI_Dashboard by exiting the process — NSSM auto-restarts it. The page goes dark for ~10–20s; reload the browser after. Use after server.py updates.",
        "icon":  "bi-arrow-clockwise", "group": "Services", "confirm": True, "timeout": 30,
        "special": "self_restart",
        "cmd":   [],  # handled internally
    },
    "restart_brain": {
        "label": "Restart Brain API",
        "desc":  "Bounces QI_BrainAPI (:9011) via sc.exe. Needs the one-time service-rights grant (same as Maia restart); agents lose Brain briefly.",
        "icon":  "bi-cpu", "group": "Services", "confirm": True, "timeout": 120,
        "cmd":   ["powershell.exe", "-NoProfile", "-Command",
                  "sc.exe stop QI_BrainAPI; Start-Sleep 4; sc.exe start QI_BrainAPI; Start-Sleep 3; "
                  "(Get-Service QI_BrainAPI).Status"],
    },
    "headroom_status": {
        "label": "Headroom Status",
        "desc":  "Is the compression proxy alive on :9020? Runs doctor + a port check. (Doctor's own 'proxy' line checks its default 8787 — trust the :9020 port check line.)",
        "icon":  "bi-heart-pulse", "group": "Headroom", "confirm": False, "timeout": 120,
        "cmd":   ["powershell.exe", "-NoProfile", "-Command",
                  "$p = Get-NetTCPConnection -LocalPort 9020 -State Listen -ErrorAction SilentlyContinue; "
                  "if ($p) { Write-Output ':9020 proxy: LISTENING (pid ' + ($p | Select-Object -First 1 -ExpandProperty OwningProcess) + ')' } "
                  "else { Write-Output ':9020 proxy: NOT RUNNING' }; "
                  "& 'C:\\APPS\\CLAUDE\\Tools\\headroom_env\\Scripts\\headroom.exe' doctor"],
    },
    "headroom_proxy_start": {
        "label": "Start Headroom Proxy",
        "desc":  "Launches the compression proxy on :9020 in front of Ollama (:11434) from the isolated venv. Detached — keeps running after this job finishes.",
        "icon":  "bi-play-circle", "group": "Headroom", "confirm": False, "timeout": 60,
        "cmd":   ["powershell.exe", "-NoProfile", "-Command",
                  "$env:OPENAI_API_BASE='http://localhost:11434/v1'; "
                  "Start-Process -FilePath 'C:\\APPS\\CLAUDE\\Tools\\headroom_env\\Scripts\\headroom.exe' "
                  "-ArgumentList 'proxy','--port','9020' -WindowStyle Hidden; "
                  "Start-Sleep 3; "
                  "$p = Get-NetTCPConnection -LocalPort 9020 -State Listen -ErrorAction SilentlyContinue; "
                  "if ($p) { Write-Output 'Proxy started on :9020' } else { Write-Output 'Launch attempted - port not up yet, run Headroom Status to re-check' }"],
    },
    "headroom_proxy_stop": {
        "label": "Stop Headroom Proxy",
        "desc":  "Kills the headroom.exe proxy process. Clients pointed at :9020 will fail until restarted.",
        "icon":  "bi-stop-circle", "group": "Headroom", "confirm": True, "timeout": 60,
        "cmd":   ["powershell.exe", "-NoProfile", "-Command",
                  "taskkill /IM headroom.exe /F 2>&1; Write-Output 'Stopped (or was not running).'"],
    },
}

_ops_lock = _ops_threading.Lock()
_ops_state: dict = {}   # action_id -> {running, started, finished, rc, output}


def _ops_load_history() -> dict:
    if OPS_HISTORY_FILE.exists():
        try:
            return json.loads(OPS_HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _ops_save_history():
    try:
        keep = {k: {kk: vv for kk, vv in v.items() if kk != "running"}
                for k, v in _ops_state.items() if not v.get("running")}
        merged = _ops_load_history()
        merged.update(keep)
        OPS_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        OPS_HISTORY_FILE.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    except Exception:
        logger.exception("ops: failed to persist history")


# Seed state from disk so "last run" survives dashboard restarts
_ops_state.update(_ops_load_history())


def _ops_worker(action_id: str):
    action = _ops_resolve(action_id)
    if action is None:
        return
    if action.get("special") == "sequence":
        import time as _time
        total = len(OPS_SEQUENCE)
        lines, overall = [], 0
        for i, sub_id in enumerate(OPS_SEQUENCE, 1):
            sub = _ops_resolve(sub_id)
            if sub is None:
                lines.append(f"[{i}/{total}] {sub_id}: SKIPPED (unknown action)")
                continue
            label = sub.get("label", sub_id)
            lines.append(f"[{i}/{total}] {label}: running…")
            with _ops_lock:
                _ops_state[action_id]["output"] = "\n".join(lines)
            if not _ops_start(sub_id):
                lines[-1] = f"[{i}/{total}] {label}: SKIPPED (already running)"
                continue
            t0 = _time.time()
            limit = sub.get("timeout", 600) + 90
            while _time.time() - t0 < limit:
                with _ops_lock:
                    if not _ops_state.get(sub_id, {}).get("running"):
                        break
                _time.sleep(2)
            with _ops_lock:
                rc = _ops_state.get(sub_id, {}).get("rc")
            dur = int(_time.time() - t0)
            if rc == 0:
                lines[-1] = f"[{i}/{total}] {label}: OK ({dur}s)"
            else:
                overall = 1
                lines[-1] = f"[{i}/{total}] {label}: FAIL rc={rc} ({dur}s) — see its card's output"
            with _ops_lock:
                _ops_state[action_id]["output"] = "\n".join(lines)
        lines.append("")
        lines.append("Sequence complete: " + ("all steps OK ✓" if overall == 0 else "one or more steps FAILED ✗"))
        with _ops_lock:
            _ops_state[action_id].update({
                "running": False,
                "finished": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "rc": overall,
                "output": "\n".join(lines),
            })
            _ops_save_history()
        return
    if action.get("special") == "self_restart":
        # Exit the process; NSSM's restart policy relaunches QI_Dashboard.
        import os as _os
        with _ops_lock:
            _ops_state[action_id].update({
                "running": False,
                "finished": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "rc": 0,
                "output": "Dashboard exiting — NSSM will auto-restart it. Reload the page in ~15s.",
            })
            _ops_save_history()
        _ops_threading.Timer(1.5, lambda: _os._exit(1)).start()
        return
    try:
        proc = subprocess.run(
            action["cmd"], cwd=action.get("cwd"),
            capture_output=True, text=True, timeout=action.get("timeout", 600),
            encoding="utf-8", errors="replace",
        )
        rc, output = proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        rc, output = -1, f"TIMED OUT after {action.get('timeout', 600)}s"
    except Exception as exc:
        rc, output = -1, f"launcher error: {exc}"
    with _ops_lock:
        _ops_state[action_id].update({
            "running": False,
            "finished": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "rc": rc,
            "output": output[-8000:],
        })
        _ops_save_history()


# ── Dynamic per-service restart actions ──────────────────────────────────────
# Any QI_* Windows service gets a virtual action id "restart_svc_<ServiceName>".
# The service list is discovered live (cached 60s) so new services appear
# automatically. Requires the one-time service-rights grant for no-admin sc.exe.

_qi_svc_cache = {"services": [], "ts": 0.0}   # [{"name":..., "status":...}]


def _qi_services_detail() -> list[dict]:
    import time as _time
    if _time.time() - _qi_svc_cache["ts"] < 30 and _qi_svc_cache["services"]:
        return _qi_svc_cache["services"]
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command",
             "Get-Service QI_* | ForEach-Object { $_.Name + '|' + $_.Status }"],
            capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace")
        services = []
        for ln in (proc.stdout or "").splitlines():
            ln = ln.strip()
            if ln.startswith("QI_") and "|" in ln:
                name, status = ln.split("|", 1)
                services.append({"name": name.strip(), "status": status.strip()})
        services.sort(key=lambda s: s["name"])
    except Exception:
        services = []
    if services:
        _qi_svc_cache.update({"services": services, "ts": _time.time()})
    return services


def _qi_service_names() -> list[str]:
    return [s["name"] for s in _qi_services_detail()]


import re as _ops_re

_QI_APP_FAMILIES = [  # ordered prefix map: service stem -> app label
    ("ClaudeVoice", "Claude Voice"), ("AutoPDF", "AutoPDF"), ("Brain", "QI Brain"),
    ("Dashboard", "QI Hive"), ("Hive", "QI Hive"), ("Caddy", "Infrastructure"),
    ("Elevate", "Infrastructure"), ("CogniBase", "CogniBase"), ("CypherMiner", "CypherMiner"),
    ("Gamez", "Gamez (WC2026)"), ("Kaze", "OpenClaw / Kaze"), ("LotteryWiz", "LotteryWiz"),
    ("M2V", "M2V"), ("Maia", "Maia"), ("MapSnap", "MapSnap"), ("MQ", "MQ"),
    ("Naya", "Naya"), ("NEXUS", "NEXUS"), ("RetirementAnalyzer", "RetirementAnalyzer"),
    ("TubeScout", "TubeScout"), ("AvatarStudio", "AvatarStudio"), ("Headroom", "Headroom"),
]


def _qi_app_for_service(name: str) -> str:
    stem = name[3:] if name.startswith("QI_") else name
    for prefix, label in _QI_APP_FAMILIES:
        if stem.lower().startswith(prefix.lower()):
            return label
    # fallback: first CamelCase token
    m = _ops_re.match(r"([A-Z][a-z0-9]+)", stem)
    return m.group(1) if m else stem


def _ops_resolve(action_id: str) -> dict | None:
    """Return the action definition for a static or dynamic action id."""
    if action_id in OPS_ACTIONS:
        return OPS_ACTIONS[action_id]
    if action_id.startswith("restart_svc_"):
        svc = action_id[len("restart_svc_"):]
        if svc in _qi_service_names():   # validate against real services (no injection)
            return {
                "label": f"Restart {svc}", "group": "Services", "confirm": True,
                "timeout": 180, "icon": "bi-bootstrap-reboot",
                "desc": f"sc.exe stop/start {svc}",
                "cmd": ["powershell.exe", "-NoProfile", "-Command",
                        f"sc.exe stop {svc}; Start-Sleep 4; sc.exe start {svc}; Start-Sleep 3; "
                        f"(Get-Service {svc}).Status"],
            }
    return None


def _ops_start(action_id: str) -> bool:
    """Begin an action if not already running. Returns True if launched."""
    if _ops_resolve(action_id) is None:
        return False
    with _ops_lock:
        if _ops_state.get(action_id, {}).get("running"):
            return False
        _ops_state[action_id] = {
            "running": True,
            "started": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "finished": None, "rc": None, "output": "",
        }
    _ops_threading.Thread(target=_ops_worker, args=(action_id,), daemon=True).start()
    return True


@app.post("/api/ops/run/{action_id}")
def api_ops_run(action_id: str):
    if _ops_resolve(action_id) is None:
        raise HTTPException(404, f"Unknown ops action: {action_id}")
    if not _ops_start(action_id):
        return JSONResponse({"ok": False, "error": "already running"}, status_code=409)
    return JSONResponse({"ok": True, "action": action_id, "started": True})


@app.get("/api/ops/status")
def api_ops_status():
    with _ops_lock:
        return JSONResponse({"actions": _ops_state, "schedules": _ops_schedules})


# ── Ops scheduling ────────────────────────────────────────────────────────────
# Each action can run on a schedule: every N hours, or daily at HH:MM.
# Schedules persist in data/ops_schedules.json and are executed by a
# background thread inside this (24/7 NSSM) dashboard process.

OPS_SCHEDULES_FILE = _PROJECT_DIR / "data" / "ops_schedules.json"
_ops_schedules: dict = {}   # action_id -> {mode, every_minutes?|at?, last_auto_run?}


def _ops_load_schedules():
    global _ops_schedules
    if OPS_SCHEDULES_FILE.exists():
        try:
            _ops_schedules = json.loads(OPS_SCHEDULES_FILE.read_text(encoding="utf-8"))
        except Exception:
            _ops_schedules = {}


def _ops_save_schedules():
    try:
        OPS_SCHEDULES_FILE.parent.mkdir(parents=True, exist_ok=True)
        OPS_SCHEDULES_FILE.write_text(json.dumps(_ops_schedules, indent=2), encoding="utf-8")
    except Exception:
        logger.exception("ops: failed to persist schedules")


_ops_load_schedules()


def _ops_sched_describe(s: dict) -> str:
    if not s or s.get("mode") == "off":
        return ""
    if s.get("mode") == "interval":
        h = s.get("every_minutes", 0) / 60
        return f"every {h:g}h"
    if s.get("mode") == "daily":
        return f"daily at {s.get('at', '?')}"
    return ""


def _ops_sched_due(action_id: str, s: dict, now: datetime) -> bool:
    last = s.get("last_auto_run")
    last_dt = None
    if last:
        try:
            last_dt = datetime.strptime(last, "%Y-%m-%d %H:%M:%S")
        except Exception:
            last_dt = None
    if s.get("mode") == "interval":
        mins = float(s.get("every_minutes", 0))
        if mins <= 0:
            return False
        return last_dt is None or (now - last_dt).total_seconds() >= mins * 60
    if s.get("mode") == "daily":
        at = s.get("at", "")
        try:
            hh, mm = at.split(":")
            due_today = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
        except Exception:
            return False
        if now < due_today:
            return False
        return last_dt is None or last_dt < due_today
    return False


def _ops_scheduler_loop():
    while True:
        try:
            now = datetime.now()
            for aid, s in list(_ops_schedules.items()):
                if s.get("mode") in (None, "off") or _ops_resolve(aid) is None:
                    continue
                if _ops_sched_due(aid, s, now):
                    if _ops_start(aid):
                        logger.info("ops scheduler: launched %s (%s)", aid, _ops_sched_describe(s))
                    # stamp even if already running, so we don't re-fire every 30s
                    s["last_auto_run"] = now.strftime("%Y-%m-%d %H:%M:%S")
                    _ops_save_schedules()
        except Exception:
            logger.exception("ops scheduler loop error")
        import time as _time
        _time.sleep(30)


_ops_threading.Thread(target=_ops_scheduler_loop, daemon=True).start()


class OpsScheduleBody(BaseModel):
    mode: str            # "off" | "interval" | "daily"
    value: str = ""      # interval: hours (e.g. "6" or "0.5"); daily: "HH:MM"


@app.post("/api/ops/schedule/{action_id}")
def api_ops_set_schedule(action_id: str, body: OpsScheduleBody):
    if _ops_resolve(action_id) is None:
        raise HTTPException(404, f"Unknown ops action: {action_id}")
    mode = body.mode.strip().lower()
    if mode == "off":
        _ops_schedules.pop(action_id, None)
        _ops_save_schedules()
        return JSONResponse({"ok": True, "action": action_id, "schedule": "off"})
    if mode == "interval":
        try:
            hours = float(body.value)
            assert 0.1 <= hours <= 168
        except Exception:
            raise HTTPException(400, "interval value must be hours between 0.1 and 168 (e.g. 6)")
        _ops_schedules[action_id] = {"mode": "interval", "every_minutes": hours * 60}
    elif mode == "daily":
        try:
            hh, mm = body.value.strip().split(":")
            assert 0 <= int(hh) <= 23 and 0 <= int(mm) <= 59
        except Exception:
            raise HTTPException(400, "daily value must be HH:MM 24h (e.g. 07:30)")
        _ops_schedules[action_id] = {"mode": "daily", "at": f"{int(hh):02d}:{int(mm):02d}"}
    else:
        raise HTTPException(400, "mode must be off | interval | daily")
    _ops_save_schedules()
    return JSONResponse({"ok": True, "action": action_id,
                         "schedule": _ops_sched_describe(_ops_schedules[action_id])})


def render_ops() -> str:
    groups: dict = {}
    for aid, a in OPS_ACTIONS.items():
        groups.setdefault(a["group"], []).append((aid, a))

    cards_html = ""
    for group_name in ("Monitoring", "Maintenance", "Services", "Headroom"):
        items = groups.get(group_name, [])
        if not items:
            continue
        row = ""
        for aid, a in items:
            st = _ops_state.get(aid, {})
            sched = _ops_schedules.get(aid, {})
            if sched.get("mode") == "interval":
                sched_value = f"{sched.get('every_minutes', 0) / 60:g}"
            elif sched.get("mode") == "daily":
                sched_value = sched.get("at", "")
            else:
                sched_value = ""
            sched_desc = _ops_sched_describe(sched)
            if sched_desc and sched.get("last_auto_run"):
                sched_desc += f" · last auto-run {sched['last_auto_run']}"
            if st.get("running"):
                badge = '<span class="badge text-bg-info">running…</span>'
            elif st.get("rc") is None:
                badge = '<span class="badge text-bg-secondary">never run</span>'
            elif st.get("rc") == 0:
                badge = f'<span class="badge text-bg-success">OK · {st.get("finished","")}</span>'
            else:
                badge = f'<span class="badge text-bg-danger">exit {st.get("rc")} · {st.get("finished","")}</span>'
            confirm_attr = "true" if a.get("confirm") else "false"
            row += f"""
            <div class="col-md-6 col-xl-4">
              <div class="card h-100" id="card-{aid}">
                <div class="card-header d-flex justify-content-between align-items-center">
                  <span><i class="bi {a['icon']} me-2"></i><strong>{a['label']}</strong></span>
                  <span id="badge-{aid}">{badge}</span>
                </div>
                <div class="card-body"><p class="mb-0 text-muted" style="font-size:.85rem">{a['desc']}</p></div>
                <div class="card-footer d-flex gap-2">
                  <button class="btn btn-sm btn-primary" id="btn-{aid}"
                          onclick="opsRun('{aid}', {confirm_attr})">
                    <i class="bi bi-play-fill me-1"></i>Run
                  </button>
                  <button class="btn btn-sm btn-outline-secondary" onclick="opsToggleOut('{aid}')">
                    <i class="bi bi-terminal me-1"></i>Output
                  </button>
                </div>
                <div class="card-footer d-flex gap-1 align-items-center flex-wrap" style="font-size:.78rem">
                  <i class="bi bi-alarm text-muted"></i>
                  <select id="sch-mode-{aid}" class="form-select form-select-sm" style="width:auto"
                          onchange="opsSchedHint('{aid}')">
                    <option value="off" {"selected" if sched.get("mode") in (None, "off") else ""}>No schedule</option>
                    <option value="interval" {"selected" if sched.get("mode") == "interval" else ""}>Every N hours</option>
                    <option value="daily" {"selected" if sched.get("mode") == "daily" else ""}>Daily at</option>
                  </select>
                  <input id="sch-val-{aid}" class="form-control form-control-sm" style="width:80px"
                         placeholder="6 / 07:30" value="{sched_value}">
                  <button class="btn btn-sm btn-outline-primary" onclick="opsSaveSched('{aid}')">Set</button>
                  <span id="sch-info-{aid}" class="text-info ms-1">{sched_desc}</span>
                </div>
                <pre id="out-{aid}" class="m-0 p-2 bg-black text-success"
                     style="display:none;max-height:280px;overflow:auto;font-size:.72rem;border-radius:0 0 6px 6px">{html.escape(st.get("output") or "(no output yet)")}</pre>
              </div>
            </div>"""
        cards_html += f"""
        <h5 class="mt-3 mb-2 text-muted text-uppercase" style="font-size:.8rem;letter-spacing:.08em">{group_name}</h5>
        <div class="row g-3">{row}</div>"""

    # ── Service Control: every QI_* service, grouped by app ──────────────────
    services = _qi_services_detail()
    apps: dict = {}
    for s in services:
        apps.setdefault(_qi_app_for_service(s["name"]), []).append(s)

    svc_html = ""
    if services:
        app_blocks = ""
        for app_name in sorted(apps):
            rows = ""
            for s in apps[app_name]:
                name = s["name"]
                running = s["status"].lower() == "running"
                dot = "text-success" if running else "text-danger"
                status_lbl = s["status"]
                aid = f"restart_svc_{name}"
                sched = _ops_schedules.get(aid, {})
                sd = _ops_sched_describe(sched)
                rows += f"""
                <tr>
                  <td style="width:1%"><i class="bi bi-circle-fill {dot}" style="font-size:.6rem"></i></td>
                  <td><code>{name}</code></td>
                  <td><small class="text-muted">{status_lbl}</small></td>
                  <td style="width:1%">
                    <button class="btn btn-xs btn-sm btn-outline-warning py-0" onclick="svcRestart('{name}')">
                      <i class="bi bi-bootstrap-reboot"></i> Restart
                    </button>
                  </td>
                  <td><span id="svcb-{name}" class="badge text-bg-secondary" style="font-size:.65rem">{sd or '—'}</span></td>
                  <td style="width:1%">
                    <button class="btn btn-sm btn-outline-secondary py-0" style="font-size:.7rem"
                            onclick="svcSchedPrompt('{name}')"><i class="bi bi-alarm"></i></button>
                  </td>
                </tr>"""
            app_blocks += f"""
            <div class="col-md-6 col-xxl-4">
              <div class="card h-100">
                <div class="card-header py-2"><strong>{app_name}</strong>
                  <span class="badge text-bg-secondary float-end">{len(apps[app_name])}</span></div>
                <div class="card-body p-0">
                  <table class="table table-sm mb-0" style="font-size:.8rem"><tbody>{rows}</tbody></table>
                </div>
              </div>
            </div>"""
        svc_html = f"""
        <h5 class="mt-4 mb-2 text-muted text-uppercase" style="font-size:.8rem;letter-spacing:.08em">
          Service Control — all QI apps</h5>
        <div class="callout callout-warning py-2 mb-2" style="font-size:.8rem">
          Restarting a service interrupts its users (e.g. Maia bot drops LINE/Telegram briefly).
          The alarm button schedules a recurring restart for that service. Statuses refresh on page reload.
        </div>
        <div class="row g-3">{app_blocks}</div>"""
    else:
        svc_html = """
        <h5 class="mt-4 mb-2 text-muted text-uppercase" style="font-size:.8rem;letter-spacing:.08em">
          Service Control — all QI apps</h5>
        <div class="alert alert-secondary">No QI_* services detected (service query failed or none installed).</div>"""

    return f"""
    <div class="callout callout-info mb-3">
      <i class="bi bi-info-circle me-2"></i>Maintenance scripts run here in the background —
      buttons stay disabled while a job runs, and the badge + output update live.
      Actions marked with a confirmation touch services or make changes.
    </div>
    {cards_html}
    {svc_html}

    <script>
    const OPS_IDS = {json.dumps(list(OPS_ACTIONS.keys()))};
    let opsPoll = null;

    function opsRun(id, needsConfirm) {{
      if (needsConfirm && !confirm('Run "' + id + '"? This action makes changes / touches services.')) return;
      document.getElementById('btn-' + id).disabled = true;
      document.getElementById('badge-' + id).innerHTML = '<span class="badge text-bg-info">starting…</span>';
      fetch('/api/ops/run/' + id, {{method: 'POST'}})
        .then(r => r.json())
        .then(() => {{ if (!opsPoll) opsPoll = setInterval(opsRefresh, 2000); }})
        .catch(err => {{
          document.getElementById('badge-' + id).innerHTML = '<span class="badge text-bg-danger">launch failed</span>';
          document.getElementById('btn-' + id).disabled = false;
          console.log(err);
        }});
    }}

    function opsToggleOut(id) {{
      const el = document.getElementById('out-' + id);
      el.style.display = (el.style.display === 'none') ? 'block' : 'none';
    }}

    function opsSchedHint(id) {{
      const mode = document.getElementById('sch-mode-' + id).value;
      const inp  = document.getElementById('sch-val-' + id);
      inp.placeholder = (mode === 'daily') ? '07:30' : (mode === 'interval') ? '6' : '';
      inp.style.display = (mode === 'off') ? 'none' : '';
    }}

    function svcRestart(name) {{
      if (!confirm('Restart ' + name + '? Its users are interrupted briefly.')) return;
      const b = document.getElementById('svcb-' + name);
      if (b) {{ b.textContent = 'restarting…'; b.className = 'badge text-bg-info'; }}
      fetch('/api/ops/run/restart_svc_' + name, {{method: 'POST'}})
        .then(r => r.json())
        .then(() => {{ if (!opsPoll) opsPoll = setInterval(opsRefresh, 2000); }})
        .catch(err => {{ if (b) {{ b.textContent = 'launch failed'; b.className = 'badge text-bg-danger'; }} }});
    }}

    function svcSchedPrompt(name) {{
      const v = prompt('Schedule recurring restart for ' + name + ':\\n' +
                       '  - hours between restarts (e.g. 24 or 6)\\n' +
                       '  - or a daily time HH:MM (e.g. 03:30)\\n' +
                       '  - or "off" to clear', '');
      if (v === null) return;
      const val = v.trim();
      const mode = (val.toLowerCase() === 'off') ? 'off' : (val.includes(':') ? 'daily' : 'interval');
      fetch('/api/ops/schedule/restart_svc_' + name, {{
        method: 'POST', headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{mode: mode, value: val}})
      }})
        .then(r => r.json().then(d => ({{ok: r.ok, d: d}})))
        .then(({{ok, d}}) => {{
          const b = document.getElementById('svcb-' + name);
          if (b) {{
            b.textContent = ok ? (d.schedule === 'off' ? '—' : d.schedule) : 'invalid';
            b.className = ok ? 'badge text-bg-success' : 'badge text-bg-danger';
          }}
        }});
    }}

    function opsSaveSched(id) {{
      const mode  = document.getElementById('sch-mode-' + id).value;
      const value = document.getElementById('sch-val-' + id).value.trim();
      const info  = document.getElementById('sch-info-' + id);
      info.textContent = 'saving…';
      fetch('/api/ops/schedule/' + id, {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{mode: mode, value: value}})
      }})
        .then(r => r.json().then(d => ({{ok: r.ok, d: d}})))
        .then(({{ok, d}}) => {{
          info.textContent = ok ? (d.schedule === 'off' ? 'schedule cleared' : '✓ ' + d.schedule)
                                : '✗ ' + (d.detail || 'invalid value');
          info.className = ok ? 'text-success ms-1' : 'text-danger ms-1';
        }})
        .catch(err => {{ info.textContent = '✗ ' + err; info.className = 'text-danger ms-1'; }});
    }}

    function opsRefresh() {{
      fetch('/api/ops/status').then(r => r.json()).then(data => {{
        let anyRunning = false;
        Object.keys(data.actions || {{}}).forEach(id => {{
          const st = data.actions[id];
          if (!st) return;
          if (st.running) anyRunning = true;
          if (id.startsWith('restart_svc_')) {{
            // dynamic service-restart rows
            const b = document.getElementById('svcb-' + id.substring('restart_svc_'.length));
            if (b) {{
              if (st.running) {{ b.textContent = 'restarting…'; b.className = 'badge text-bg-info'; }}
              else if (st.rc === 0) {{ b.textContent = 'restarted ' + (st.finished || ''); b.className = 'badge text-bg-success'; }}
              else if (st.rc !== null) {{ b.textContent = 'failed (exit ' + st.rc + ')'; b.className = 'badge text-bg-danger'; }}
            }}
            return;
          }}
          const badge = document.getElementById('badge-' + id);
          const btn   = document.getElementById('btn-' + id);
          const out   = document.getElementById('out-' + id);
          if (!badge || !btn) return;
          if (st.running) {{
            badge.innerHTML = '<span class="badge text-bg-info">running… (started ' + st.started + ')</span>';
            btn.disabled = true;
          }} else if (st.rc === 0) {{
            badge.innerHTML = '<span class="badge text-bg-success">OK · ' + (st.finished || '') + '</span>';
            btn.disabled = false;
          }} else if (st.rc !== null && st.rc !== undefined) {{
            badge.innerHTML = '<span class="badge text-bg-danger">exit ' + st.rc + ' · ' + (st.finished || '') + '</span>';
            btn.disabled = false;
          }}
          if (out && st.output) out.textContent = st.output;
        }});
        if (!anyRunning && opsPoll) {{ clearInterval(opsPoll); opsPoll = null; }}
      }});
    }}

    // one refresh on load to sync state, and keep polling if something is mid-run
    opsRefresh();
    setTimeout(() => {{
      fetch('/api/ops/status').then(r => r.json()).then(data => {{
        const running = Object.values(data.actions || {{}}).some(s => s.running);
        if (running && !opsPoll) opsPoll = setInterval(opsRefresh, 2000);
      }});
    }}, 500);
    </script>"""


# ── Claude Voice panel ───────────────────────────────────────────────────────
# Claude Voice's moving parts (mic loop, bridge responder, session trigger,
# floating buttons, tray icon) are detached desktop processes tracked in
# pidfiles, not listeners on a port — so /services and /ops (which control
# components by port) can't see or drive them. Ported 2026-08-08 from BU
# Hive's Ops -> "Voice & assistant" tab (app/voiceops.py + ops.html in
# C:\QIH\BU Administrative Backups\BU Hive (control plane)\, 2026-08-06 —
# the only surviving full copy after D:\BU Edition\AI\BU Hive was cleaned up
# the same day). Same design; reads qi_registry.json (id "claude_voice")
# instead of BU's own registry module, and renders with QI Hive's own
# card/badge idiom instead of BU's .panel/.dot CSS.

_VOICE_NO_WINDOW = 0x08000000  # CREATE_NO_WINDOW

VOICE_ACTIONS: dict = {
    # verb -> (argv relative to the project, human label)
    "trigger_on":  (["session_watch.py", "start"], "Session trigger enabled"),
    "trigger_off": (["session_watch.py", "stop"], "Session trigger disabled"),
    "voice_up":    (["session_watch.py", "up"], "Voice stack started"),
    "voice_down":  (["session_watch.py", "down"], "Voice stack stopped"),
    "greet_now":   (["session_watch.py", "--greet"], "Morning brief on its way"),
    "mic_on":      (["voice_mic.py", "--on"], "Microphone listening"),
    "mic_off":     (["voice_mic.py", "--off"], "Microphone stopped"),
    "buttons_on":  (["voice_button.py", "--show"], "Floating buttons shown"),
    "buttons_off": (["voice_button.py", "--hide"], "Floating buttons hidden"),
    "tray_on":     (["voice_tray.py", "--show"], "Tray icon shown"),
    "tray_off":    (["voice_tray.py", "--quit"], "Tray icon removed"),
    "brief_speak": (["morning_brief.py", "--fresh", "--speak"], "Morning brief spoken"),
    "brief_test":  (["morning_brief.py", "--fresh"], "Morning brief preview"),
}
_VOICE_SLOW = {"brief_speak", "brief_test"}  # network + a Claude call; must not block the request


def _voice_home() -> Path | None:
    try:
        reg = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    for p in reg.get("projects", []):
        if p.get("id") == "claude_voice":
            path = p.get("path")
            return Path(path) if path and Path(path).is_dir() else None
    return None


def _voice_python(base: Path) -> Path:
    exe = base / ".venv" / "Scripts" / "python.exe"
    return exe if exe.exists() else Path("python")


def _voice_read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _voice_pid_alive(pid) -> bool:
    if not pid:
        return False
    try:
        import psutil  # optional; falls back to tasklist below
        return psutil.pid_exists(int(pid))
    except Exception:
        pass
    try:
        out = subprocess.run(["tasklist", "/FI", f"PID eq {int(pid)}", "/NH", "/FO", "CSV"],
                             capture_output=True, text=True, timeout=5,
                             creationflags=_VOICE_NO_WINDOW).stdout
        return str(int(pid)) in (out or "")
    except Exception:
        return False


def _voice_pidfile(path: Path) -> int | None:
    """A bare-integer pidfile (the tray and floating buttons both use this form)."""
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _voice_startup_lnk(name: str) -> bool:
    import os
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return False
    return (Path(appdata) / "Microsoft/Windows/Start Menu/Programs/Startup" / name).exists()


def _voice_desktop_running() -> bool | None:
    """Is Claude Desktop up? None when the probe itself failed, so the UI can say
    'unknown' instead of asserting a state it doesn't have."""
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Claude.exe", "/NH", "/FO", "CSV"],
                             capture_output=True, text=True, timeout=8,
                             creationflags=_VOICE_NO_WINDOW).stdout
    except Exception:
        return None
    return "claude.exe" in (out or "").lower()


def _voice_age(ts: float) -> str:
    import time as _time
    mins = max(0, int((_time.time() - ts) / 60))
    if mins < 1:
        return "just now"
    if mins < 60:
        return f"{mins} min ago"
    return f"{mins // 60}h {mins % 60}m ago"


def _voice_speech_trace(base: Path) -> dict:
    """Today's speech events, and specifically whether anything was said twice
    (the echo detector — see voiceops.py's original docstring for the incident
    this caught: two processes voicing the same morning brief seconds apart)."""
    from collections import defaultdict
    path = base / "data" / "speech_trace.jsonl"
    today = datetime.now().strftime("%Y-%m-%d")
    events, played = [], defaultdict(list)
    try:
        for line in path.read_text(encoding="utf-8").splitlines()[-4000:]:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not r.get("ts", "").startswith(today):
                continue
            events.append(r)
            if r.get("event") == "played":
                played[r.get("sha8")].append(r)
    except OSError:
        return {"available": False}
    dupes = [{"opening": rows[0].get("opening", ""), "count": len(rows),
              "pids": [r.get("pid") for r in rows]}
             for rows in played.values() if len(rows) > 1]
    suppressed = sum(1 for r in events if r.get("event") == "suppressed")
    return {
        "available": True,
        "spoken": sum(len(v) for v in played.values()),
        "suppressed": suppressed,
        "dupes": dupes,
        "ok": not dupes,
    }


def voice_state() -> dict:
    """Everything the Claude Voice panel needs, read straight from Claude
    Voice's own files. No subprocess, so rendering the page costs nothing and
    can't hang on a wedged child."""
    base = _voice_home()
    if not base:
        return {"available": False,
                "why": "Claude Voice isn't registered in qi_registry.json (id "
                       "\"claude_voice\"), or its folder is missing on this machine."}

    cfg = _voice_read_json(base / "config.json", {})
    pids = _voice_read_json(base / "data" / "control_pids.json", {})
    auto = cfg.get("automation", {})
    brief_cfg = cfg.get("morning_brief", {})
    trig = cfg.get("session_trigger", {})

    realtime = _voice_pid_alive(pids.get("realtime"))
    responder = _voice_pid_alive(pids.get("responder"))
    watcher = _voice_pid_alive(pids.get("session"))
    desktop = _voice_desktop_running()
    brain = cfg.get("brain_mode", "bridge")

    sess_dir = base / "data" / "claude_sessions"
    code_sessions = len(list(sess_dir.glob("*.json"))) if sess_dir.is_dir() else 0

    greet_mark = _voice_read_json(base / "data" / "last_greeting.json", {})
    greeted = greet_mark.get("date") == datetime.now().strftime("%Y-%m-%d")

    if not realtime:
        listening = ("Not listening", "down", "The mic loop is stopped — nothing will hear you.")
    elif brain == "bridge" and not responder:
        listening = ("Listening, but nothing answers", "idle",
                     "Bridge mode needs the responder; without it questions hang and time out.")
    else:
        listening = ("Listening and ready", "up", "Say \u201cMorning, Claude\u201d for the daily brief.")

    cache = _voice_read_json(base / "data" / "morning_brief_cache.json", {})
    cached_at = cache.get("at")

    return {
        "available": True,
        "home": str(base),
        "headline": {"text": listening[0], "status": listening[1], "detail": listening[2]},
        "desktop_open": desktop,
        "trigger": {
            "watcher": watcher,
            "code_sessions": code_sessions,
            "signals": ([f"{code_sessions} Claude Code session{'s' if code_sessions != 1 else ''}"]
                       if code_sessions else []) + (["Claude Desktop"] if desktop else []),
        },
        "greeted_today": greeted,
        "speech": _voice_speech_trace(base),
        "desktop": {
            "buttons": _voice_pid_alive(_voice_pidfile(base / "data" / "voice_button.pid")),
            "buttons_autostart": _voice_startup_lnk("Claude Voice Button.lnk"),
            "tray": _voice_pid_alive(_voice_pidfile(base / "data" / "voice_tray.pid")),
            "tray_autostart": _voice_startup_lnk("Claude Voice Tray.lnk"),
        },
        "services": [
            {"key": "realtime", "name": "Microphone loop", "up": realtime,
             "detail": "Records, transcribes and answers what you say.",
             "on": "mic_on", "off": "mic_off"},
            {"key": "responder", "name": "Claude responder", "up": responder,
             "detail": "Answers questions in bridge mode. Without it, nothing replies.",
             "on": "voice_up", "off": None},
        ],
        "brain": {
            "mode": brain,
            "ok": brain != "bridge" or responder,
            "detail": ("Real Claude via the Claude Code CLI" if brain == "bridge" and responder
                       else "Bridge mode with NO responder — nothing will reply" if brain == "bridge"
                       else brain),
        },
        "reply_mode": auto.get("mic_reply_mode", "always"),
        "brief": {
            "enabled": bool(brief_cfg.get("enabled", True)),
            "phrasing": brief_cfg.get("phrasing", "claude"),
            "cities": [c.get("name") for c in brief_cfg.get("weather", [])],
            "sections": list((brief_cfg.get("news") or {}).keys()),
            "cached": _voice_age(cached_at) if cached_at else None,
            "ttl_min": brief_cfg.get("cache_ttl_min", 30),
        },
    }


def voice_run(verb: str) -> tuple[bool, str]:
    """Perform one allowlisted action. Never raises — this is a control surface.
    The client sends a verb from a fixed vocabulary, never a command, so this
    can't become arbitrary execution."""
    if verb not in VOICE_ACTIONS:
        return False, f"Unknown voice action '{verb}'."
    base = _voice_home()
    if not base:
        return False, "Claude Voice is not available on this machine."
    argv, label = VOICE_ACTIONS[verb]
    cmd = [str(_voice_python(base)), *argv]
    try:
        if verb in _VOICE_SLOW:
            if verb == "brief_speak":
                # Fire and forget: a fresh brief takes ~25s, which would hold the request.
                subprocess.Popen(cmd, cwd=str(base), stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 close_fds=True, creationflags=0x00000008 | _VOICE_NO_WINDOW)
                return True, "Building the brief now \u2014 it'll speak in about 25 seconds."
            proc = subprocess.run(cmd, cwd=str(base), capture_output=True, text=True,
                                  timeout=90, creationflags=_VOICE_NO_WINDOW)
            text = (proc.stdout or "").strip()
            return (bool(text), text or "The brief came back empty — check the log.")
        proc = subprocess.run(cmd, cwd=str(base), capture_output=True, text=True,
                              timeout=30, creationflags=_VOICE_NO_WINDOW)
    except subprocess.TimeoutExpired:
        return False, f"{label}: timed out."
    except (OSError, ValueError) as exc:
        return False, f"Could not run {verb}: {exc}"
    if proc.returncode != 0:
        return False, f"{verb} failed: {(proc.stderr or '').strip()[:200]}"
    return True, label


def _voice_dot(status: str) -> str:
    color = {"up": "success", "idle": "warning", "down": "danger"}.get(status, "secondary")
    return f'<i class="bi bi-circle-fill text-{color} me-1" style="font-size:.6rem"></i>'


def _voice_badge(text: str, kind: str = "secondary") -> str:
    return f'<span class="badge text-bg-{kind} me-1">{html.escape(str(text))}</span>'


def render_voice() -> str:
    v = voice_state()

    if not v.get("available"):
        return f"""
        <div class="callout callout-info mb-3">
          <i class="bi bi-info-circle me-2"></i>Claude Voice's mic loop, responder, session
          trigger, floating buttons and tray icon are detached desktop processes — they hold
          no port, so <a href="/services">Services</a> and <a href="/ops">Ops</a> can't see or
          drive them. This panel talks to them directly.
        </div>
        <div class="alert alert-secondary">{html.escape(v.get("why", "Claude Voice is unavailable."))}</div>"""

    hl = v["headline"]
    desktop_txt = "Unknown" if v["desktop_open"] is None else ("Open" if v["desktop_open"] else "Closed")
    trig_up = v["trigger"]["watcher"]

    signals_html = "".join(_voice_badge(s) for s in v["trigger"]["signals"]) \
        or _voice_badge("no Claude session open")
    greeted_badge = _voice_badge("greeted today" if v["greeted_today"] else "not greeted yet today")

    trig_btn = (
        f'<button class="btn btn-sm btn-outline-danger" onclick="voiceRun(\'trigger_off\',false)">'
        f'<i class="bi bi-pause-fill"></i> Disarm</button>' if trig_up else
        f'<button class="btn btn-sm btn-primary" onclick="voiceRun(\'trigger_on\',false)">'
        f'<i class="bi bi-shield-check"></i> Arm trigger</button>'
    )

    svc_rows = ""
    for svc in v["services"]:
        dot = _voice_dot("up" if svc["up"] else "down")
        if not svc["up"] and svc["on"]:
            btn = (f'<button class="btn btn-sm btn-primary" onclick="voiceRun(\'{svc["on"]}\',false)">'
                   f'<i class="bi bi-play-fill"></i> Start</button>')
        elif svc["up"] and svc["off"]:
            btn = (f'<button class="btn btn-sm btn-outline-danger" onclick="voiceRun(\'{svc["off"]}\',false)">'
                   f'<i class="bi bi-stop-fill"></i> Stop</button>')
        else:
            btn = ""
        svc_rows += f"""
        <tr>
          <td style="width:1%">{dot}</td>
          <td><strong>{html.escape(svc["name"])}</strong><div class="text-muted small">{html.escape(svc["detail"])}</div></td>
          <td>{"Running" if svc["up"] else "Stopped"}</td>
          <td style="width:1%;white-space:nowrap">{btn}</td>
        </tr>"""

    if v["desktop"]["buttons"]:
        buttons_btn = ('<button class="btn btn-sm btn-outline-danger" onclick="voiceRun(\'buttons_off\',false)">'
                       '<i class="bi bi-eye-slash"></i> Hide</button>')
    else:
        buttons_btn = ('<button class="btn btn-sm btn-primary" onclick="voiceRun(\'buttons_on\',false)">'
                       '<i class="bi bi-eye"></i> Show</button>')
    if v["desktop"]["tray"]:
        tray_btn = ('<button class="btn btn-sm btn-outline-danger" '
                    'onclick="voiceRun(\'tray_off\',true,\'Remove the tray icon? It is what arms the mic after a reboot.\')">'
                    '<i class="bi bi-x-lg"></i> Remove</button>')
    else:
        tray_btn = ('<button class="btn btn-sm btn-primary" onclick="voiceRun(\'tray_on\',false)">'
                    '<i class="bi bi-app-indicator"></i> Show</button>')

    desktop_rows = f"""
        <tr>
          <td style="width:1%">{_voice_dot("up" if v["desktop"]["buttons"] else "down")}</td>
          <td><strong>Floating buttons</strong>
            <div class="text-muted small">The draggable mic and speaker pills on the desktop.
              {_voice_badge("starts with Windows" if v["desktop"]["buttons_autostart"] else "will NOT return after a reboot")}</div>
          </td>
          <td>{"Showing" if v["desktop"]["buttons"] else "Hidden"}</td>
          <td style="width:1%;white-space:nowrap">{buttons_btn}</td>
        </tr>
        <tr>
          <td style="width:1%">{_voice_dot("up" if v["desktop"]["tray"] else "down")}</td>
          <td><strong>Tray icon</strong>
            <div class="text-muted small">The speaker glyph in the taskbar — also what starts
              the trigger after a reboot.
              {_voice_badge("starts with Windows" if v["desktop"]["tray_autostart"] else "will NOT return after a reboot")}</div>
          </td>
          <td>{"Showing" if v["desktop"]["tray"] else "Hidden"}</td>
          <td style="width:1%;white-space:nowrap">{tray_btn}</td>
        </tr>"""

    speech = v["speech"]
    speech_html = ""
    if speech.get("available"):
        dupe_badges = "".join(
            f'<span class="badge text-bg-danger me-1" title="pids {", ".join(str(p) for p in d["pids"])}">'
            f'voiced {d["count"]}\u00d7: {html.escape(d["opening"][:34])}\u2026</span>'
            for d in speech["dupes"])
        speech_html = f"""
        <div class="card mb-3">
          <div class="card-header d-flex justify-content-between align-items-center">
            <span><i class="bi bi-soundwave me-2"></i>Speech trace <span class="text-muted small">— the echo detector</span></span>
            <span>{_voice_dot("up" if speech["ok"] else "down")}{"No echo" if speech["ok"] else "Echo detected"}</span>
          </div>
          <div class="card-body">
            <p class="text-muted small mb-2">Every attempt to speak today, with the process that made it and a
              hash of what was said. <strong>Voiced twice</strong> should always be zero.</p>
            {_voice_badge(f'{speech["spoken"]} spoken today')}
            {_voice_badge(f'{speech["suppressed"]} duplicates blocked')}
            {dupe_badges}
          </div>
        </div>"""

    brief = v["brief"]
    brief_facts = (_voice_badge(" \u00b7 ".join(brief["cities"]) or "no cities configured")
                   + _voice_badge(" \u00b7 ".join(brief["sections"]) or "no sections configured")
                   + _voice_badge("written fresh by Claude" if brief["phrasing"] == "claude" else "fixed template"))
    if brief["cached"]:
        brief_facts += _voice_badge(f'cached {brief["cached"]}')

    return f"""
    <div class="callout callout-info mb-3">
      <i class="bi bi-info-circle me-2"></i>Claude Voice's mic loop, responder, session trigger,
      floating buttons and tray icon are detached desktop processes — they hold no port, so
      <a href="/services">Services</a> and <a href="/ops">Ops</a> can't see or drive them. This
      panel talks to them directly (ported from BU Hive's Ops → Voice &amp; assistant tab).
    </div>

    <div id="voice-flash" class="mb-3" style="display:none"></div>

    <div class="row g-3 mb-3">
      <div class="col-md-4"><div class="card h-100"><div class="card-body">
        <div class="text-muted small">Talking to Claude</div>
        <div class="fw-bold mt-1">{_voice_dot(hl["status"])}{html.escape(hl["text"])}</div>
        <div class="text-muted small mt-1">{html.escape(hl["detail"])}</div>
      </div></div></div>
      <div class="col-md-4"><div class="card h-100"><div class="card-body">
        <div class="text-muted small">Claude Desktop</div>
        <div class="fw-bold mt-1">{desktop_txt}</div>
      </div></div></div>
      <div class="col-md-4"><div class="card h-100"><div class="card-body">
        <div class="text-muted small">Brain</div>
        <div class="fw-bold mt-1">{_voice_dot("up" if v["brain"]["ok"] else "down")}<span class="text-uppercase">{html.escape(v["brain"]["mode"])}</span></div>
        <div class="text-muted small mt-1">{html.escape(v["brain"]["detail"])}</div>
      </div></div></div>
    </div>

    <div class="card mb-3">
      <div class="card-header d-flex justify-content-between align-items-center">
        <span><i class="bi bi-shield-check me-2"></i>Claude session trigger</span>
        <span>{_voice_dot("up" if trig_up else "down")}{"Armed" if trig_up else "Not running"}</span>
      </div>
      <div class="card-body">
        <p class="text-muted small mb-2">Opening Claude anywhere — a Claude Code session or Claude
          Desktop — turns the microphone and spoken replies on and speaks the morning brief once a
          day; closing everything stands it back down. Signals are redundant on purpose.</p>
        {signals_html}{greeted_badge}
      </div>
      <div class="card-footer">{trig_btn}</div>
    </div>

    <div class="card mb-3">
      <div class="card-header"><i class="bi bi-mic me-2"></i>Voice services</div>
      <div class="card-body p-0">
        <table class="table table-sm mb-0"><tbody>{svc_rows}</tbody></table>
      </div>
      <div class="card-footer d-flex gap-2">
        <button class="btn btn-sm btn-primary" onclick="voiceRun('voice_up',false)">
          <i class="bi bi-play-circle"></i> Start listening</button>
        <button class="btn btn-sm btn-outline-danger"
                onclick="voiceRun('voice_down',true,'Stop the microphone loop and the responder?')">
          <i class="bi bi-stop-circle"></i> Stop</button>
      </div>
    </div>

    <div class="card mb-3">
      <div class="card-header"><i class="bi bi-display me-2"></i>On-screen controls</div>
      <div class="card-body p-0">
        <table class="table table-sm mb-0"><tbody>{desktop_rows}</tbody></table>
      </div>
    </div>

    {speech_html}

    <div class="card mb-3">
      <div class="card-header d-flex justify-content-between align-items-center">
        <span><i class="bi bi-body-text me-2"></i>Morning brief</span>
        <span>{_voice_dot("up" if brief["enabled"] else "idle")}{"Enabled" if brief["enabled"] else "Off"}</span>
      </div>
      <div class="card-body">
        <p class="text-muted small mb-2">Speaks itself once a day when you open Claude. Say
          "Morning, Claude" any time to hear it again.</p>
        {brief_facts}
      </div>
      <div class="card-footer d-flex gap-2 flex-wrap">
        <button class="btn btn-sm btn-primary" onclick="voiceRun('brief_speak',false)"
                title="Builds a fresh brief and speaks it aloud">
          <i class="bi bi-volume-up"></i> Speak it now</button>
        <button class="btn btn-sm btn-outline-secondary" onclick="voiceRun('greet_now',false)"
                title="Re-run today's greeting, ignoring the once-a-day guard">
          <i class="bi bi-arrow-repeat"></i> Re-greet</button>
        <button class="btn btn-sm btn-outline-secondary" onclick="voiceRun('brief_test',false)"
                title="Builds a fresh brief and shows the text, silently">
          <i class="bi bi-eye"></i> Preview text</button>
      </div>
      <div class="card-body border-top" id="voice-preview" style="display:none">
        <div class="text-muted small mb-1">Preview — not spoken</div>
        <div id="voice-preview-text" style="white-space:pre-wrap"></div>
      </div>
    </div>

    <script>
    function voiceToast(ok, msg, sticky) {{
      const el = document.getElementById('voice-flash');
      el.className = 'alert ' + (ok ? 'alert-success' : 'alert-danger');
      el.textContent = msg;
      el.style.display = '';
      // Errors stay on screen — only a confirmed success is safe to auto-clear
      // via reload. Silently reloading past an error is what made failures
      // (e.g. the tunnel write-token gate) look like the button did nothing.
      if (ok && !sticky) setTimeout(() => location.reload(), 900);
    }}
    function voiceRun(verb, needsConfirm, confirmMsg) {{
      if (needsConfirm && !confirm(confirmMsg || 'Are you sure?')) return;
      fetch('/api/voice/run/' + verb, {{method: 'POST'}})
        .then(r => r.json().catch(() => ({{}})).then(data => ({{status: r.status, ok: r.ok, data: data}})))
        .then(res => {{
          if (!res.ok) {{
            // Two shapes can land here: the tunnel write-token guard
            // ({{status:"error", error:...}}) and FastAPI's own 404/500
            // ({{detail:...}}). Neither is this endpoint's own {{ok,message}}.
            const why = res.data.error || res.data.detail
              || ('HTTP ' + res.status);
            const hint = res.status === 403
              ? ' — click the lock icon (top right) and enter the write token from C:\\\\QIH\\\\secrets\\\\dashboard_write_token.txt'
              : '';
            voiceToast(false, why + hint, true);
            return;
          }}
          if (verb === 'brief_test') {{
            document.getElementById('voice-preview-text').textContent = res.data.message;
            document.getElementById('voice-preview').style.display = '';
            return;
          }}
          voiceToast(res.data.ok, res.data.message, !res.data.ok);
        }})
        .catch(err => voiceToast(false, 'Request failed: ' + err, true));
    }}
    </script>"""


@app.get("/api/voice/state")
def api_voice_state():
    return JSONResponse(voice_state())


@app.post("/api/voice/run/{verb}")
def api_voice_run(verb: str):
    if verb not in VOICE_ACTIONS:
        raise HTTPException(404, f"Unknown voice action: {verb}")
    ok, message = voice_run(verb)
    return JSONResponse({"ok": ok, "message": message})


@app.get("/voice", response_class=HTMLResponse)
def voice_page():
    return base_layout("Claude Voice", render_voice(), "voice")


@app.get("/ops", response_class=HTMLResponse)
def ops_page():
    return base_layout("Ops Control Panel", render_ops(), "ops")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    # Loopback only (2026-08-08). Public access is via the Cloudflare tunnel ->
    # QI Gate (Caddy :9040) at hive.quiddityinnovations.com, which also sits behind
    # Cloudflare Access. Binding 0.0.0.0 published the dashboard — ecosystem snapshot,
    # service control and Brain data — to the whole LAN with NO authentication of any
    # kind, since this app has no login of its own.
    uvicorn.run("server:app", host="127.0.0.1", port=8600, reload=False)

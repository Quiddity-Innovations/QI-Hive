# -*- coding: utf-8 -*-
"""
QI Hive Dashboard — port 8600
AdminLTE v4 + Bootstrap 5 + SortableJS kanban
Powered by QI Brain (port 9010) as the hive's nervous system.
"""
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

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

_PROJECT_DIR = Path(__file__).parent.parent.parent.parent  # C:\QIH
STATUS_FILE  = _PROJECT_DIR / "data" / "status.json"
TASKS_FILE   = _PROJECT_DIR / "data" / "tasks.json"
AGENTS_DIR   = _PROJECT_DIR / "hive" / "Agents"  # legacy agents folder — stays for now
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

# Wire up QI Logger
sys.path.insert(0, str(_PROJECT_DIR))
from engine.common.qi_logger import get_logger, set_level, list_services
from engine.common import usage_stats
log = get_logger("dashboard")

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
          <li><strong>Brain status</strong> — shows whether QI Brain (port 9010) is online. If offline, agents fall back gracefully but session logging and cross-project memory are suspended.</li>
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
          <li>Content is loaded from <code>C:\\UNIVERSAL\\QI_Claude_Manager_Guide.md</code> and rendered as formatted HTML.</li>
          <li>Use <code>Ctrl+F</code> to search within the page — the guide is fully text-searchable.</li>
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


VALID_THEMES = {"dark", "light", "auto"}

def _get_theme() -> str:
    return _load_hive_config().get("theme", "dark")

def _theme_icon(theme: str) -> str:
    return {"dark": "bi-moon-stars-fill", "light": "bi-sun-fill", "auto": "bi-circle-half"}.get(theme, "bi-circle-half")


def base_layout(title: str, content: str, active: str = "") -> str:
    nav_items = [
        ("dashboard", "/",        "bi-speedometer2",  "Dashboard"),
        ("launcher",  "/launcher","bi-grid-3x3-gap",  "Launcher"),
        ("hive",      "/hive",    "bi-hexagon",       "The Hive"),
        ("health",    "/health",  "bi-heart-pulse",   "Health Check"),
        ("board",     "/board",   "bi-kanban",        "Task Board"),
        ("tests",     "/tests",   "bi-bug",           "Tests"),
        ("projects",  "/projects/status", "bi-clipboard-data", "Project Status"),
        ("services",  "/services","bi-gear-wide-connected", "Services"),
        ("tasks",     "/tasks",   "bi-calendar-event",      "Scheduled Tasks"),
        ("usage",     "/usage",   "bi-graph-up-arrow","LLM Usage"),
        ("news",      "/news",    "bi-newspaper",     "Headlines"),
        ("activity",  "/activity","bi-activity",      "Activity"),
        ("dispatch",  "/dispatch","bi-send-check",    "CoWork Dispatch"),
        ("brain",     "/brain",   "bi-cpu",           "QI Brain"),
        ("warroom",   "/warroom", "bi-broadcast-pin", "War Room"),
        ("logs",      "/logs",    "bi-journal-text",  "Logs"),
        ("config",    "/config",  "bi-sliders",       "Config"),
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
    # 'auto' maps to no data-bs-theme (Bootstrap auto-detects from OS)
    bs_theme_attr = f'data-bs-theme="{theme}"' if theme != "auto" else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{title} | QI Claude Manager</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/overlayscrollbars@2.11.0/styles/overlayscrollbars.min.css"/>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/font/bootstrap-icons.min.css"/>
  <link rel="stylesheet" href="/static/css/adminlte.min.css"/>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  <script src="/static/js/adminlte.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js"></script>
  <style>
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
  </style>
</head>
<body class="layout-fixed sidebar-expand-lg bg-body-tertiary" {bs_theme_attr}>
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
            <i class="bi {t_icon}"></i>
          </a>
          <ul class="dropdown-menu dropdown-menu-end" style="min-width:120px">
            <li><a class="dropdown-item {'fw-bold' if theme=='dark' else ''}"
                   href="#" onclick="setTheme('dark');return false;">
              <i class="bi bi-moon-stars-fill me-2"></i>Dark</a></li>
            <li><a class="dropdown-item {'fw-bold' if theme=='light' else ''}"
                   href="#" onclick="setTheme('light');return false;">
              <i class="bi bi-sun-fill me-2"></i>Light</a></li>
            <li><a class="dropdown-item {'fw-bold' if theme=='auto' else ''}"
                   href="#" onclick="setTheme('auto');return false;">
              <i class="bi bi-circle-half me-2"></i>System</a></li>
          </ul>
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

<script src="https://cdn.jsdelivr.net/npm/overlayscrollbars@2.11.0/browser/overlayscrollbars.browser.es5.min.js"></script>
<script>
function setTheme(t) {{
  fetch('/api/theme', {{method:'POST', headers:{{'Content-Type':'application/json'}},
    body: JSON.stringify({{theme: t}})
  }}).then(() => location.reload());
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
        c = sqlite3.connect("file:C:/QI/maia.db?mode=ro", uri=True, timeout=2.0)
        try:
            total_convs = c.execute("SELECT COUNT(DISTINCT conv_key) FROM conversations").fetchone()[0]
            last_ts = c.execute("SELECT MAX(ts) FROM conversations").fetchone()[0]
            msgs_7d = c.execute("SELECT COUNT(*) FROM conversations WHERE ts >= datetime('now','-7 days')").fetchone()[0]
            overrides["maia"] = {
                "count": total_convs,
                "last_seen": last_ts,
                "label": f"{total_convs} conv · {msgs_7d} msgs 7d",
                "source": "C:/QI/maia.db conversations",
                "unit": "conversations",
            }
        finally:
            c.close()
    except Exception:
        pass

    # Naya: same shape
    try:
        c = sqlite3.connect("file:C:/NAYA/naya.db?mode=ro", uri=True, timeout=2.0)
        try:
            total_convs = c.execute("SELECT COUNT(DISTINCT conv_key) FROM conversations").fetchone()[0]
            last_ts = c.execute("SELECT MAX(ts) FROM conversations").fetchone()[0]
            msgs_7d = c.execute("SELECT COUNT(*) FROM conversations WHERE ts >= datetime('now','-7 days')").fetchone()[0]
            overrides["naya"] = {
                "count": total_convs,
                "last_seen": last_ts,
                "label": f"{total_convs} conv · {msgs_7d} msgs 7d",
                "source": "C:/NAYA/naya.db conversations",
                "unit": "conversations",
            }
        finally:
            c.close()
    except Exception:
        pass

    # NEXUS: scout digests + synthesis sessions
    try:
        c = sqlite3.connect("file:C:/NEXUS/nexus.db?mode=ro", uri=True, timeout=2.0)
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
                "source": "C:/NEXUS/nexus.db",
                "unit": "digests + sessions",
            }
        finally:
            c.close()
    except Exception:
        pass

    # OpenClaw: count log files per known agent folder + latest mtime
    try:
        oc_logs = Path(r"C:\OC\runtime\logs\agents")
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
                "source": "C:/OC/runtime/logs/agents",
                "unit": "log files",
            }
    except Exception:
        pass

    return overrides

def _get_project_llms() -> list[dict]:
    """Read each project's Ollama model usage from its own config.
    Returns list of {project, models: [{name, role, notes}], source}."""
    import sqlite3
    out = []

    # Maia + Naya: both have llm_chain tables with the same schema
    for proj, db_path in [("Maia", r"C:\QI\maia.db"), ("Naya", r"C:\NAYA\naya.db")]:
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
        with urllib.request.urlopen("http://localhost:8010/providers", timeout=2.0) as r:
            prov = _j.loads(r.read().decode()).get("providers", [])
        models = []
        if "ollama" in prov:
            models.append({"name": "ollama (provider configured)", "role": "router", "notes": "specific models chosen per request"})
        if "gemma4" in prov:
            models.append({"name": "gemma4:* (provider alias)", "role": "router", "notes": ""})
        out.append({"project": "NEXUS", "source": "http://localhost:8010/providers", "models": models})
    except Exception as e:
        out.append({"project": "NEXUS", "source": "API", "models": [], "error": str(e)})

    # CogniBase: settings.json → vendors[id=ollama]
    try:
        cb_cfg = json.loads(Path(r"C:\CogniBase\Settings\settings.json").read_text(encoding="utf-8"))
        ollama_vendors = [v for v in cb_cfg.get("vendors", []) if "ollama" in (v.get("id") or "").lower()]
        models = []
        for v in ollama_vendors:
            active = "✅ active" if v.get("active") else "⚪ configured"
            for m in (v.get("models_chat") or []):
                models.append({"name": m, "role": v.get("id"), "notes": active})
            if not v.get("models_chat"):
                models.append({"name": f"({v.get('id')}: no models defined)", "role": v.get("id"), "notes": active})
        out.append({"project": "CogniBase", "source": r"C:\CogniBase\Settings\settings.json", "models": models})
    except Exception as e:
        out.append({"project": "CogniBase", "source": "settings.json", "models": [], "error": str(e)})

    # AutoPDF: autopdf-settings.json
    try:
        ap = json.loads(Path(r"C:\AutoPDF\Application\autopdf-settings.json").read_text(encoding="utf-8"))
        m = ap.get("ollamaModel")
        models = [{"name": m, "role": "smart-mapping", "notes": "AI template authoring + field extract"}] if m else []
        out.append({"project": "AutoPDF", "source": r"C:\AutoPDF\Application\autopdf-settings.json", "models": models})
    except Exception as e:
        out.append({"project": "AutoPDF", "source": "settings", "models": [], "error": str(e)})

    # OpenClaw: documented in OC repo (router fallback + vision). Hardcoded from repo docs.
    out.append({"project": "OpenClaw", "source": r"C:\OC\repo\agents (docs)", "models": [
        {"name": "qwen3:8b",      "role": "kaze-router-fallback", "notes": "activates when Cloudflare Workers AI fails"},
        {"name": "qwen3-vl:8b",   "role": "vision (default)",     "notes": "Playwright NLM element location, fast"},
        {"name": "qwen3-vl:32b",  "role": "vision (--accurate)",  "notes": "slower, excellent accuracy"},
    ]})

    # MapSnap: confirmed no LLM usage (static schema browser)
    out.append({"project": "MapSnap", "source": r"C:\MapSnap (no LLM)", "models": []})

    # EasyFlow: no Ollama usage detected in source
    out.append({"project": "EasyFlow", "source": r"C:\EasyFlow (Gmail tooling, no LLM)", "models": []})

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
        "deprecated":                           ("secondary", "bi-archive-fill"),
    }

    # Project small-boxes
    project_cards = ""
    for name, p in status.get("projects", {}).items():
        st = p.get("status","unknown")
        # Case-insensitive lookup so "Active Dev" matches "active dev". Unknown
        # statuses fall through to INFO (blue) — never to secondary (grey),
        # which is reserved for retired/merged per the sidebar legend.
        color, icon = proj_colors.get(st.lower() if isinstance(st, str) else st,
                                       ("info", "bi-question-circle"))
        # qi-purple uses a custom CSS class (text-bg-* doesn't have purple in Bootstrap 5).
        # Inject inline style fallback so it works even without the CSS class loading first.
        bg_attr = f'class="small-box bg-qi-purple text-white"' if color == "qi-purple" else f'class="small-box text-bg-{color}"'
        task = p.get("current_task") or "—"
        notes = p.get("notes","")
        open_tasks = sum(1 for t in tasks if t.get("project")==name and t.get("column")!="done")
        project_cards += f"""
        <div class="col-lg-4 col-md-6 col-sm-12">
          <div {bg_attr}>
            <div class="inner">
              <h4>{name}</h4>
              <p>{st.replace("_"," ").title()}</p>
            </div>
            <i class="small-box-icon bi {icon}"></i>
            <div class="small-box-footer d-flex justify-content-between">
              <a href="/project/{name}" class="text-white text-decoration-none">
                <i class="bi bi-box-arrow-up-right"></i> Details
              </a>
              <span>{open_tasks} open tasks</span>
              <a href="/board?project={name}" class="text-white text-decoration-none">
                Board <i class="bi bi-arrow-right"></i>
              </a>
            </div>
          </div>
        </div>"""

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

    # Claude usage snapshot
    try:
        u_today = usage_stats.today()
        u_30    = usage_stats.totals(30)
        tokens_today   = f'{u_today["tokens"]/1_000_000:.1f}M'
        cost_today     = f'${u_today["cost_usd"]:.2f}'
        sessions_today = u_today["sessions"]
        turns_today    = u_today["assistant_turns"]
        cost_30        = f'${u_30["cost_usd"]:,.0f}'
    except Exception as e:
        tokens_today = cost_today = sessions_today = turns_today = cost_30 = "—"
        log.warning(f"usage_stats failed: {e}")

    return f"""
    <!-- Summary row -->
    <div class="row">
      <div class="col-12 mb-3">
        <div class="d-flex gap-3 flex-wrap">
          <span class="badge text-bg-warning fs-6"><i class="bi bi-inbox me-1"></i> Backlog: {col_counts.get("backlog",0)}</span>
          <span class="badge text-bg-success fs-6"><i class="bi bi-play-circle me-1"></i> In Progress: {col_counts.get("in_progress",0)}</span>
          <span class="badge text-bg-info fs-6"><i class="bi bi-search me-1"></i> Review: {col_counts.get("review",0)}</span>
          <span class="badge text-bg-success fs-6"><i class="bi bi-check-circle me-1"></i> Done: {col_counts.get("done",0)}</span>
          <a href="/board" class="btn btn-sm btn-outline-primary ms-2"><i class="bi bi-kanban me-1"></i> Open Board</a>
          <a href="/health" class="btn btn-sm btn-outline-success"><i class="bi bi-heart-pulse me-1"></i> Health Check</a>
        </div>
      </div>
    </div>

    <!-- Claude usage strip (today + 30d) — API list-price equivalents; MAX plan covers actual cost -->
    <div class="row mb-1">
      <div class="col-lg-3 col-md-6 col-sm-12">
        <div class="small-box text-bg-primary">
          <div class="inner"><h4>{tokens_today}</h4><p>Tokens Today <span class="opacity-75" style="font-size:.7rem">(fresh, ex-cache-reads)</span></p></div>
          <i class="small-box-icon bi bi-lightning-charge-fill"></i>
          <a href="/usage" class="small-box-footer text-white text-decoration-none">
            Details <i class="bi bi-arrow-right"></i>
          </a>
        </div>
      </div>
      <div class="col-lg-3 col-md-6 col-sm-12">
        <div class="small-box text-bg-success">
          <div class="inner"><h4>{cost_today}</h4><p>API Equiv. Today <span class="opacity-75" style="font-size:.7rem">(MAX plan covers)</span></p></div>
          <i class="small-box-icon bi bi-currency-dollar"></i>
          <a href="/usage" class="small-box-footer text-white text-decoration-none">
            Details <i class="bi bi-arrow-right"></i>
          </a>
        </div>
      </div>
      <div class="col-lg-3 col-md-6 col-sm-12">
        <div class="small-box text-bg-info">
          <div class="inner"><h4>{sessions_today} · {turns_today}</h4><p>Sessions · Turns Today</p></div>
          <i class="small-box-icon bi bi-chat-left-dots"></i>
          <a href="/usage" class="small-box-footer text-white text-decoration-none">
            Details <i class="bi bi-arrow-right"></i>
          </a>
        </div>
      </div>
      <div class="col-lg-3 col-md-6 col-sm-12">
        <div class="small-box text-bg-warning">
          <div class="inner"><h4>{cost_30}</h4><p>API Equiv. (30d) <span class="opacity-75" style="font-size:.7rem">(list-price)</span></p></div>
          <i class="small-box-icon bi bi-calendar-range"></i>
          <a href="/usage" class="small-box-footer text-dark text-decoration-none">
            Breakdown <i class="bi bi-arrow-right"></i>
          </a>
        </div>
      </div>
    </div>

    <!-- Project cards -->
    <div class="row">{project_cards}</div>

    <!-- Agents + Sessions -->
    <div class="row mt-2">
      <div class="col-lg-6">
        <div class="card">
          <div class="card-header d-flex align-items-center">
            <h3 class="card-title mb-0"><i class="bi bi-people me-2"></i>Agent Team</h3>
            <span class="ms-auto text-muted" style="font-size:.7rem">live from qi_brain.db</span>
          </div>
          <div class="card-body p-0">
            <table class="table table-sm table-hover mb-0">
              <thead><tr><th>Agent</th><th>Last Active</th><th>Activity <small class="text-muted fw-normal">(unit varies)</small></th><th>Model</th><th>Scope</th></tr></thead>
              <tbody>{agent_rows}</tbody>
            </table>
          </div>
        </div>
      </div>
      <div class="col-lg-6">
        <div class="card">
          <div class="card-header d-flex align-items-center">
            <h3 class="card-title mb-0"><i class="bi bi-journal-text me-2"></i>Session Log</h3>
            <span class="ms-auto text-muted" style="font-size:.7rem">live from qi_brain.db</span>
          </div>
          <div class="card-body p-0">
            <table class="table table-sm table-hover mb-0">
              <thead><tr><th>Session</th><th>Summary</th></tr></thead>
              <tbody>{session_rows}</tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    {render_project_llms()}
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
        '<span class="badge text-bg-success"><i class="bi bi-circle-fill me-1"></i>Online :9010</span>'
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

    stats_html = f"""
    <div class="row mb-3">
      <div class="col-lg-3 col-md-6">
        <div class="small-box text-bg-primary">
          <div class="inner"><h3>{n_projects}</h3><p>Active Projects</p></div>
          <i class="small-box-icon bi bi-folder2-open"></i>
        </div>
      </div>
      <div class="col-lg-3 col-md-6">
        <div class="small-box text-bg-success">
          <div class="inner"><h3>{n_decisions}</h3><p>Decisions Logged</p></div>
          <i class="small-box-icon bi bi-journal-check"></i>
        </div>
      </div>
      <div class="col-lg-3 col-md-6">
        <div class="small-box text-bg-warning">
          <div class="inner"><h3>{n_features}</h3><p>Features Tracked</p></div>
          <i class="small-box-icon bi bi-stars"></i>
        </div>
      </div>
      <div class="col-lg-3 col-md-6">
        <div class="small-box text-bg-info">
          <div class="inner"><h3>{n_sessions}</h3><p>Sessions Logged</p></div>
          <i class="small-box-icon bi bi-calendar2-check"></i>
        </div>
      </div>
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

    # Recent sessions
    sessions = snap.get("recent_sessions", [])[:6]
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
        <a href="http://127.0.0.1:9010/docs" target="_blank" class="btn btn-sm btn-outline-secondary">
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
      fetch('http://127.0.0.1:9010/api/poll/status')
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
      fetch('http://127.0.0.1:9010/api/poll/trigger', {{method:'POST'}})
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

      fetch('http://127.0.0.1:9010/api/distill', {{
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

# Known Cloudflare tunnels. Each entry maps a local port to either:
#   - "json":  path to a tunnel_manager.py-style status file (preferred)
#   - "log":   path to raw cloudflared log; URL extracted via regex
# To add a new project's tunnel, point it at one of these and the launcher picks it up.
_TRYCF_RE = __import__("re").compile(r"https://[a-z0-9-]+\.trycloudflare\.com")

KNOWN_TUNNELS = [
    {"port": 8600, "label": "Hive Dashboard",
     "json": r"C:\QIH\engine\hive\tunnel\status\tunnel.json"},
    {"port": 8001, "label": "Maia API",
     "log":  r"C:\QI\LOGS\tunnel_log.txt"},
    {"port": 7860, "label": "Maia Demo (Gradio)",
     "log":  r"C:\QI\LOGS\Maia_Gradio_Tunnel_Log.txt"},
    {"port": 7861, "label": "Naya UI",
     "log":  r"C:\NAYA\LOGS\QI_NayaTunnel.stderr.log"},
    {"port": 7880, "label": "NEXUS UI",
     "log":  r"C:\NEXUS\LOGS\QI_NEXUSTunnel.stderr.log"},
    {"port": 8650, "label": "CogniBase",
     "log":  r"C:\CogniBase\LOGS\QI_CogniBaseTunnel.stderr.log"},
    {"port": 9876, "label": "MapSnap",
     "log":  r"C:\MapSnap\LOGS\QI_MapSnapTunnel.stderr.log"},
]

def _get_tunnels() -> dict[int, dict]:
    """Return {port: {url, status, source, updated_at}} for every known tunnel."""
    out: dict[int, dict] = {}
    for spec in KNOWN_TUNNELS:
        port = int(spec["port"])
        entry = {"url": None, "status": "unknown", "source": None,
                 "updated_at": None, "label": spec.get("label", "")}
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

def _project_tiles(role: str, port: int):
    """Tiles for one (role, port). Returns list of (label, href, port_display)."""
    base = f"http://localhost:{port}"
    role_l = (role or "").lower()
    if role_l == "api":
        return [
            ("API",    base,             f"{port}"),
            ("Docs",   f"{base}/docs",   f"{port}/docs"),
            ("Health", f"{base}/health", f"{port}/health"),
        ]
    if role_l == "ui":
        return [("UI", base, f"{port}")]
    if role_l == "dashboard":
        return [("Dashboard", base, f"{port}")]
    if role_l == "launcher":
        return [("Launcher", base, f"{port}")]
    if role_l in ("http", "gateway"):
        return [(role.title(), base, f"{port}")]
    # Generic: just expose the root with the role label.
    return [(role.title() or "Open", base, f"{port}")]

def render_launcher() -> str:
    try:
        reg = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        reg = {"projects": []}
        load_err = str(e)
    else:
        load_err = None

    projects = reg.get("projects", []) or []

    # Gather every numeric port across all projects + extras for parallel probing.
    all_ports = []
    for proj in projects:
        if not isinstance(proj, dict): continue
        for info in (proj.get("ports") or {}).values():
            if isinstance(info, dict) and str(info.get("current","")).isdigit():
                all_ports.append(int(info["current"]))
    for _, links in LAUNCHER_EXTRAS:
        for _, _, p, _ in links:
            all_ports.append(int(p))
    port_status = _probe_ports_parallel(all_ports)

    # Tunnel state per port — used to surface public Cloudflare URLs.
    tunnels = _get_tunnels()

    def status_badge(status: str) -> str:
        s = (status or "").lower()
        if ("production" in s) or ("active" in s and "dev" not in s and "paused" not in s):
            cls = "text-bg-success"
        elif "dev" in s or "pilot" in s or "ready" in s:
            cls = "text-bg-primary"
        elif "paused" in s or "pending" in s:
            cls = "text-bg-warning"
        elif "merged" in s or "deprecated" in s or "retired" in s:
            cls = "text-bg-secondary"
        else:
            cls = "text-bg-light"
        return f'<span class="badge {cls} ms-2" style="font-size:.65rem;font-weight:500">{status}</span>' if status else ""

    def render_tile(label, href, port_display, up):
        cls = "btn-outline-success" if up else "btn-outline-secondary"
        dot = "🟢" if up else "⚪"
        return (
            f'<a href="{href}" target="_blank" rel="noopener" '
            f'class="btn {cls} btn-sm me-2 mb-2">'
            f'<span class="me-1" style="font-size:.7rem">{dot}</span>{label} '
            f'<span class="text-muted ms-1" style="font-family:Consolas,monospace;font-size:.72rem">:{port_display}</span>'
            f'</a>'
        )

    groups_html = ""

    for proj in projects:
        if not isinstance(proj, dict): continue
        pid    = proj.get("id") or "?"
        name   = proj.get("name") or pid
        status = proj.get("status") or ""
        path   = proj.get("path") or ""
        ports  = proj.get("ports") or {}

        tiles_html = ""
        public_tiles_html = ""
        for role, info in ports.items():
            if not isinstance(info, dict): continue
            current = info.get("current")
            if not (isinstance(current, int) or (isinstance(current, str) and current.isdigit())):
                continue
            port = int(current)
            up   = port_status.get(port, False)
            for label, href, port_display in _project_tiles(role, port):
                tiles_html += render_tile(label, href, port_display, up)
            # If a Cloudflare tunnel maps to this port, emit a Public tile.
            tinfo = tunnels.get(port)
            if tinfo and tinfo.get("url") and tinfo.get("status") == "running":
                public_url = tinfo["url"]
                tlabel = (tinfo.get("label") or role.title())
                public_tiles_html += (
                    f'<a href="{public_url}" target="_blank" rel="noopener" '
                    f'class="btn btn-success btn-sm me-2 mb-2" '
                    f'title="{public_url}">'
                    f'<i class="bi bi-globe2 me-1"></i>Public · {tlabel} '
                    f'<span class="ms-1 opacity-75" style="font-family:Consolas,monospace;font-size:.7rem">:{port}</span>'
                    f'</a>'
                )

        if public_tiles_html:
            tiles_html = public_tiles_html + tiles_html

        if not tiles_html:
            tiles_html = '<span class="text-muted fst-italic" style="font-size:.8rem">No HTTP port registered</span>'

        groups_html += f"""
        <div class="mb-4">
          <div class="d-flex align-items-center mb-2">
            <span class="text-uppercase fw-bold" style="font-size:.78rem;letter-spacing:.08em">{name}</span>
            <span class="text-muted ms-2" style="font-size:.7rem;font-family:Consolas,monospace">{pid}</span>
            {status_badge(status)}
            <span class="text-muted ms-auto" style="font-size:.7rem;font-family:Consolas,monospace">{path}</span>
          </div>
          <div>{tiles_html}</div>
        </div>"""

    # Extras (non-registry shared services)
    for group_name, links in LAUNCHER_EXTRAS:
        tiles_html = ""
        for label, host, port, suffix in links:
            up = port_status.get(int(port), False)
            href = f"{host}:{port}{suffix}"
            tiles_html += render_tile(label, href, f"{port}{suffix}", up)
        groups_html += f"""
        <div class="mb-4">
          <div class="d-flex align-items-center mb-2">
            <span class="text-uppercase fw-bold" style="font-size:.78rem;letter-spacing:.08em">{group_name}</span>
            <span class="badge text-bg-light ms-2" style="font-size:.65rem;font-weight:500">extra</span>
          </div>
          <div>{tiles_html}</div>
        </div>"""

    # Headline: how many public URLs are live right now
    public_live = sum(1 for t in tunnels.values() if t.get("url") and t.get("status") == "running")
    note = (
        '<div class="alert alert-info py-2 mb-3 d-flex align-items-center" style="font-size:.85rem">'
        '<i class="bi bi-info-circle me-2"></i>'
        '<div>Tiles auto-generated from <code>C:\\QIH\\ecosystem\\qi_registry.json</code>. '
        '🟢 = local port responding · '
        f'<i class="bi bi-globe2 mx-1"></i><strong>{public_live}</strong> public Cloudflare URL(s) live — green tiles open from any machine. '
        'Quick Tunnel URLs rotate on restart; this page reads the current value live, no edit needed.</div>'
        '</div>'
    )
    err_html = ""
    if load_err:
        err_html = f'<div class="alert alert-danger py-2 mb-3"><i class="bi bi-exclamation-triangle me-1"></i>Registry load failed: {load_err}</div>'

    return f"""
    <div class="card">
      <div class="card-header d-flex align-items-center">
        <h5 class="mb-0"><i class="bi bi-grid-3x3-gap me-2"></i>QI Launcher</h5>
        <span class="ms-auto text-muted" style="font-size:.75rem">{len(projects)} projects from registry</span>
      </div>
      <div class="card-body">
        {note}
        {err_html}
        {groups_html}
      </div>
    </div>"""

@app.get("/launcher", response_class=HTMLResponse)
def launcher_page():
    return base_layout("Launcher", render_launcher(), "launcher")

@app.get("/api/tunnels")
def api_tunnels():
    """Live aggregate of Cloudflare tunnel state across all known QI tunnels."""
    return JSONResponse({"tunnels": {str(p): v for p, v in _get_tunnels().items()}})

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
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/github-markdown-css@5.5.1/github-markdown-dark.min.css"/>
    <style>
      .markdown-body {{ background:transparent!important; color:inherit!important; }}
      .markdown-body table {{ width:100%; }}
      .markdown-body pre {{ background:#0d1117; border-radius:6px; padding:16px; }}
      .markdown-body h1,.markdown-body h2 {{ border-bottom:1px solid #30363d; padding-bottom:.3em; }}
      .markdown-body h1 {{ font-size:1.6rem; }}
      .markdown-body h2 {{ font-size:1.25rem; margin-top:1.5rem; }}
      .markdown-body h3 {{ font-size:1rem; color:#58a6ff; }}
    </style>
    <script src="https://cdn.jsdelivr.net/npm/marked@9.1.6/marked.min.js"></script>
    <script>
      document.getElementById('guide-content').innerHTML =
        '<div class="markdown-body p-2">' + marked.parse(`{md_escaped}`) + '</div>';
    </script>"""
    return base_layout("Guide", content, "guide")


@app.get("/api/guide/raw")
def api_guide_raw():
    text = GUIDE_FILE.read_text(encoding="utf-8") if GUIDE_FILE.exists() else "# Guide not found"
    return Response(content=text, media_type="text/plain")

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
                            "warroom", "cowork_dispatch", "themes", "scheduled_tasks"],
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
    return JSONResponse(load_agents())

@app.get("/api/health")
def api_health():
    data = run_health_check()
    sync_tasks(data)   # keep board in sync with reality
    return JSONResponse(data)

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

# ── Tests Page ───────────────────────────────────────────────────────────────

TESTS_RESULTS = Path(r"C:\Claude\Tests\results\latest.json")
TESTS_RUNNER  = Path(r"C:\Claude\Tests\run_tests.py")

HIVE_CONFIG        = _PROJECT_DIR / "data" / "hive_config.json"
_EF_WORKTREE       = Path(r"C:\EasyFlow\tester_builds\beta_unpacked")
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
    ("maia",      "Maia"),
    ("naya",      "Naya"),
    ("nexus",     "NEXUS"),
    ("openclaw",  "OpenClaw"),
    ("mq",        "MQ"),
    ("easyflow",  "EasyFlow"),
    ("qi_hive",   "QI Hive"),
    ("qi_brain",  "QI Brain"),
    ("universal", "QI-Universal"),
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


def render_config() -> str:
    return render_gsudo_config() + render_gsudo_profiles() + render_log_config()


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
    theme = body.get("theme", "dark")
    if theme not in VALID_THEMES:
        raise HTTPException(400, f"theme must be one of {sorted(VALID_THEMES)}")
    cfg = _load_hive_config()
    cfg["theme"] = theme
    _save_hive_config(cfg)
    return JSONResponse({"ok": True, "theme": theme})


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
                    "http://127.0.0.1:9010/api/inbox",
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


# ── /logs — tail viewer ───────────────────────────────────────────────────────

LOGS_ROOT = _PROJECT_DIR / "logs"


def _list_log_files() -> list[dict]:
    if not LOGS_ROOT.exists():
        return []
    out = []
    for p in LOGS_ROOT.rglob("*.log"):
        try:
            st = p.stat()
            out.append({
                "path": str(p.relative_to(LOGS_ROOT)).replace("\\", "/"),
                "size": st.st_size,
                "mtime": st.st_mtime,
            })
        except OSError:
            pass
    out.sort(key=lambda x: x["mtime"], reverse=True)
    return out


def _tail_file(path: Path, lines: int = 200) -> str:
    if not path.exists():
        return ""
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            block = 8192
            data = b""
            while size > 0 and data.count(b"\n") <= lines:
                read = min(block, size)
                size -= read
                f.seek(size)
                data = f.read(read) + data
        text = data.decode("utf-8", errors="replace")
        return "\n".join(text.splitlines()[-lines:])
    except OSError as e:
        return f"[error reading log: {e}]"


def render_logs() -> str:
    files = _list_log_files()
    options = "".join(
        f'<option value="{f["path"]}">{f["path"]}  ({f["size"]//1024} KB)</option>'
        for f in files
    ) or '<option value="">(no logs yet)</option>'
    return f"""
    <div class="card">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h5 class="mb-0"><i class="bi bi-journal-text"></i> Logs</h5>
        <div class="d-flex gap-2 align-items-center">
          <select id="log-file" class="form-select form-select-sm" style="width:320px"
                  onchange="loadLog()">{options}</select>
          <select id="log-lines" class="form-select form-select-sm" style="width:110px"
                  onchange="loadLog()">
            <option value="100">100 lines</option>
            <option value="200" selected>200 lines</option>
            <option value="500">500 lines</option>
            <option value="1000">1000 lines</option>
          </select>
          <input type="text" id="log-filter" class="form-control form-control-sm"
                 placeholder="filter (substring)" style="width:180px" oninput="applyFilter()">
          <label class="form-check form-switch small mb-0 ms-2">
            <input class="form-check-input" type="checkbox" id="log-auto" checked> auto
          </label>
          <button class="btn btn-sm btn-outline-secondary" onclick="loadLog()">
            <i class="bi bi-arrow-clockwise"></i>
          </button>
        </div>
      </div>
      <div class="card-body p-0">
        <pre id="log-content" style="max-height:70vh;overflow:auto;padding:12px;margin:0;
             background:#0e0e10;color:#c9d1d9;font-size:12px;line-height:1.4;">loading...</pre>
      </div>
    </div>
    <script>
    let _lastRaw = "";
    async function loadLog() {{
      const f = document.getElementById('log-file').value;
      const n = document.getElementById('log-lines').value;
      if (!f) return;
      const r = await fetch(`/api/logs/tail?path=${{encodeURIComponent(f)}}&lines=${{n}}`);
      const j = await r.json();
      _lastRaw = j.content || "";
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
    loadLog();
    </script>
    """


@app.get("/logs", response_class=HTMLResponse)
def logs_page():
    return base_layout("Logs", render_logs() + render_log_config(), "logs")


@app.get("/api/logs")
def api_list_logs():
    return {"logs": _list_log_files(), "root": str(LOGS_ROOT)}


@app.get("/api/logs/tail")
def api_tail_log(path: str, lines: int = 200):
    full = (LOGS_ROOT / path).resolve()
    try:
        full.relative_to(LOGS_ROOT.resolve())
    except ValueError:
        raise HTTPException(400, "path must be under logs/")
    return {"path": path, "lines": lines, "content": _tail_file(full, lines)}


# ── /project/{id} — per-project detail page ─────────────────────────────────

def render_project(pid: str) -> str:
    status = load_status()
    proj = status.get("projects", {}).get(pid)
    if not proj:
        return f'<div class="alert alert-warning">Project <code>{pid}</code> not found in status.json</div>'

    registry_path = _PROJECT_DIR / "ecosystem" / "qi_registry.json"
    services = []
    try:
        if registry_path.exists():
            reg = json.loads(registry_path.read_text(encoding="utf-8"))
            p = next((x for x in reg.get("projects", []) if x.get("id", "").lower() == pid.lower()), {})
            services = p.get("services", []) or []
    except Exception:
        pass

    svc_rows = "".join(
        f"<tr><td><code>{s}</code></td>"
        f"<td><button class='btn btn-sm btn-outline-secondary' onclick=\"checkSvcStatus(this,'{s}')\">status</button></td></tr>"
        for s in services
    ) or '<tr><td colspan="2" class="text-muted">No services registered</td></tr>'

    sessions = status.get("session_log", [])
    sess_rows = "".join(
        f"<tr><td><small>{s.get('session','')}</small></td>"
        f"<td class='text-muted small'>{(s.get('summary','') or '')[:200]}</td></tr>"
        for s in sessions[-5:][::-1]
    ) or '<tr><td colspan="2" class="text-muted">No sessions logged</td></tr>'

    return f"""
    <div class="row g-3">
      <div class="col-12">
        <div class="card"><div class="card-body">
          <div class="d-flex justify-content-between align-items-start">
            <div>
              <h4 class="mb-0">{pid}</h4>
              <div class="text-muted small"><code>{proj.get('path','(no path)')}</code></div>
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
    function checkSvcStatus(btn, name) {{
      btn.disabled = true;
      btn.textContent = '...';
      fetch('/api/services/' + encodeURIComponent(name) + '/status')
        .then(r => r.json())
        .then(d => {{
          const s = d.status;
          btn.textContent = s;
          btn.className = s === 'running' ? 'btn btn-sm btn-success'
                        : s === 'stopped' ? 'btn btn-sm btn-danger'
                        : 'btn btn-sm btn-warning';
          btn.disabled = false;
        }})
        .catch(() => {{ btn.textContent = 'err'; btn.disabled = false; }});
    }}
    </script>
    """


@app.get("/project/{pid}", response_class=HTMLResponse)
def project_page(pid: str):
    return base_layout(pid, render_project(pid), "dashboard")


@app.get("/api/services/{name}/status")
def api_service_status(name: str):
    import subprocess
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


@app.get("/project/{pid}/status", response_class=HTMLResponse)
def project_status_page(pid: str, tab: str = "overview"):
    title, body = render_project_status(pid, tab)
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
    $patterns = @('QI-','OC-','Maia','Naya','NEXUS','openclaw','claude','nlm')
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
    return JSONResponse({"days": days, "rows": usage_stats.by_project(days)})

@app.get("/api/usage/by_model")
def api_usage_by_model(days: int = 30):
    return JSONResponse({"days": days, "rows": usage_stats.by_model(days)})

@app.get("/api/usage/savings")
def api_usage_savings(days: int = 30):
    return JSONResponse(usage_stats.savings(days))

@app.get("/api/usage/savings/today")
def api_usage_savings_today():
    return JSONResponse(usage_stats.savings_today())

@app.get("/api/usage/savings/by_model")
def api_usage_savings_by_model(days: int = 30):
    return JSONResponse({"days": days, "rows": usage_stats.savings_by_model(days)})


def render_usage() -> str:
    t = usage_stats.today()
    t7 = usage_stats.totals(7)
    t30 = usage_stats.totals(30)
    daily = usage_stats.daily(30)
    projects_sav = usage_stats.savings_by_project(30)
    s_models = usage_stats.savings_by_model(30)

    # What-if optimization numbers
    s_today = usage_stats.savings_today()
    s_7  = usage_stats.savings(7)
    s_30 = usage_stats.savings(30)

    # Daily chart: 3 thin bars per day (Actual / w-Local / w-Combined)
    max_cost = max((d["cost_usd"] for d in daily), default=0) or 1
    daily_bars = ""
    for d in daily:
        ha = int((d["cost_usd"]          / max_cost) * 100) if max_cost else 0
        hl = int((d["local_cost_usd"]    / max_cost) * 100) if max_cost else 0
        hc = int((d["combined_cost_usd"] / max_cost) * 100) if max_cost else 0
        tip = (f"{d['date']} — Actual ${d['cost_usd']:.2f} · "
               f"w/ Local ${d['local_cost_usd']:.2f} · "
               f"w/ Batch ${d['batch_cost_usd']:.2f} · "
               f"Combined ${d['combined_cost_usd']:.2f}")
        daily_bars += f'''
        <div class="daily-bar-wrap" title="{tip}">
          <div class="daily-trio">
            <div class="daily-bar bar-actual"   style="height:{ha}%;"></div>
            <div class="daily-bar bar-local"    style="height:{hl}%;"></div>
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
        width: 30%; border-radius: 2px 2px 0 0; min-height: 2px;
      }}
      .bar-actual   {{ background: linear-gradient(to top, #6366f1, #a5b4fc); }}
      .bar-local    {{ background: linear-gradient(to top, #0dcaf0, #7fdfff); }}
      .bar-combined {{ background: linear-gradient(to top, #198754, #6fd2a0); }}
      .daily-label {{
        position: absolute; bottom: -22px; font-size: 10px;
        color: #6c757d; white-space: nowrap;
        transform: rotate(-45deg); transform-origin: center;
      }}
      .chart-legend {{ font-size: .8rem; }}
      .chart-legend .sw {{ display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:4px; vertical-align:middle; }}
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

    <!-- Row 1: actual spend -->
    <div class="row row-compact mb-1">
      <div class="col-md-3"><div class="small-box text-bg-primary">
        <div class="inner">
          <h4>{t['tokens']/1_000_000:.1f}M</h4>
          <p>Tokens Today <span class="opacity-75" style="font-size:.65rem">(+ {t.get('cache_reads',0)/1_000_000:.0f}M cache re-reads)</span></p>
        </div>
        <i class="small-box-icon bi bi-lightning-charge-fill"></i>
      </div></div>
      <div class="col-md-3"><div class="small-box text-bg-success">
        <div class="inner">
          <h4>${t['cost_usd']:.2f}</h4>
          <p>API Equiv. Today <span class="opacity-75" style="font-size:.65rem">(MAX plan covers this)</span></p>
        </div>
        <i class="small-box-icon bi bi-currency-dollar"></i>
      </div></div>
      <div class="col-md-3"><div class="small-box text-bg-info">
        <div class="inner">
          <h4>${t7['cost_usd']:,.0f}</h4>
          <p>API Equiv. (7d) <span class="opacity-75" style="font-size:.65rem">(list-price)</span></p>
        </div>
        <i class="small-box-icon bi bi-calendar-week"></i>
      </div></div>
      <div class="col-md-3"><div class="small-box text-bg-warning">
        <div class="inner">
          <h4>${t30['cost_usd']:,.0f}</h4>
          <p>API Equiv. (30d) <span class="opacity-75" style="font-size:.65rem">(list-price)</span></p>
        </div>
        <i class="small-box-icon bi bi-calendar-range"></i>
      </div></div>
    </div>

    <!-- Row 2: Local FREE LLMs (Ollama) -->
    <div class="row row-compact mb-1">
      <div class="col-12"><p class="mb-1 mt-2 text-secondary small text-uppercase fw-bold" style="letter-spacing:.05em">
        <i class="bi bi-cpu me-1"></i> Local FREE LLMs (via OLLAMA)
        <span class="text-muted text-lowercase fw-normal ms-2" style="letter-spacing:0">
          — Haiku → gemma4 / qwen3:8b · Sonnet → gpt-oss-20b / gemma4:31b · Opus → stays on Claude
        </span>
      </p></div>
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

    <!-- Row 3: Claude Batch API -->
    <div class="row row-compact mb-3">
      <div class="col-12"><p class="mb-1 mt-2 text-secondary small text-uppercase fw-bold" style="letter-spacing:.05em">
        <i class="bi bi-moon-stars me-1"></i> Claude Batch API (Deferred to 00:00–06:00, 50% OFF)
        <span class="text-muted text-lowercase fw-normal ms-2" style="letter-spacing:0">
          — applies to Opus · Sonnet · Haiku · 24h async SLA
        </span>
      </p></div>
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

    <!-- Daily chart (3 series: Actual / w-Local / Combined) -->
    <div class="card mb-3">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h3 class="card-title mb-0"><i class="bi bi-graph-up me-2"></i>Daily Spend — Last 30 Days</h3>
        <div class="chart-legend">
          <span><i class="sw bar-actual"></i>Actual</span>
          <span class="ms-3"><i class="sw bar-local"></i>w/ Local</span>
          <span class="ms-3"><i class="sw bar-combined"></i>Combined</span>
        </div>
      </div>
      <div class="card-body">
        <div class="daily-bars">{daily_bars}</div>
      </div>
    </div>

    <div class="row">
      <!-- By project -->
      <div class="col-lg-12">
        <div class="card mb-3">
          <div class="card-header">
            <h3 class="card-title"><i class="bi bi-folder2-open me-2"></i>By Project (30d) — Claude API vs Local + Batch</h3>
          </div>
          <div class="card-body p-0">
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
          </div>
        </div>
      </div>

      <!-- By model -->
      <div class="col-lg-12">
        <div class="card mb-3">
          <div class="card-header">
            <h3 class="card-title"><i class="bi bi-cpu me-2"></i>By Model (30d) — Claude API vs Local + Batch</h3>
          </div>
          <div class="card-body p-0">
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
          </div>
        </div>
      </div>
    </div>

    <!-- Savings By Model -->
    <div class="card mb-3">
      <div class="card-header">
        <h3 class="card-title"><i class="bi bi-stars me-2"></i>Savings by Model (30d) — Claude API vs Local + Batch</h3>
      </div>
      <div class="card-body p-0">
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
      </div>
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
            f"http://127.0.0.1:9010{path}", data=data,
            headers={"Content-Type": "application/json"}, method="PATCH"
        )
        with urllib.request.urlopen(req, timeout=3) as r:
            return _json.loads(r.read().decode())
    except Exception:
        return None


def _brain_post_dispatch(payload: dict) -> dict | None:
    import urllib.request, json as _json
    try:
        data = _json.dumps(payload).encode()
        req  = urllib.request.Request(
            "http://127.0.0.1:9010/api/dispatch", data=data,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=3) as r:
            return _json.loads(r.read().decode())
    except Exception:
        return None


def _get_dispatches(status_filter: str | None = None) -> list[dict]:
    import urllib.request, json as _json
    try:
        url = "http://127.0.0.1:9010/api/dispatches?limit=100"
        if status_filter:
            url += f"&status={status_filter}"
        with urllib.request.urlopen(url, timeout=3) as r:
            return _json.loads(r.read().decode()).get("dispatches", [])
    except Exception:
        return []


def render_dispatch() -> str:
    import json as _json
    all_dispatches = _get_dispatches()
    pending    = [d for d in all_dispatches if d["status"] == "pending"]
    discussing = [d for d in all_dispatches if d["status"] == "discussing"]
    resolved   = [d for d in all_dispatches if d["status"] in ("approved", "declined", "executed")]

    SOURCE_BADGES = {
        "cowork":      ("bg-primary",  "CoWork"),
        "claude_code": ("bg-warning text-dark", "Claude Code"),
        "renne":       ("bg-success",  "Renne"),
        "maia":        ("bg-info text-dark", "Maia"),
        "naya":        ("bg-secondary","Naya"),
    }
    TYPE_ICONS = {
        "report":   "bi-file-text",
        "brief":    "bi-file-earmark-text",
        "decision": "bi-lightning",
        "task":     "bi-check2-square",
        "review":   "bi-search",
        "proposal": "bi-lightbulb",
        "request":  "bi-arrow-right-circle",
    }
    PRIORITY_COLORS = {"high": "danger", "normal": "secondary", "low": "success"}

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
            "queued":        '<span class="badge bg-secondary ms-1" title="Apply: queued">Apply: queued</span>',
            "in_progress":   '<span class="badge bg-info text-dark ms-1" title="Apply: in progress">Apply: in&nbsp;progress</span>',
            "review":        '<span class="badge bg-warning text-dark ms-1" title="Apply: needs review">Apply: review</span>',
            "applied":       '<span class="badge bg-success ms-1" title="Apply: applied">Apply: applied</span>',
            "failed":        '<span class="badge bg-danger ms-1" title="Apply: failed">Apply: failed</span>',
            "rejected_auto": '<span class="badge bg-dark ms-1" title="Apply: rejected automatically">Apply: rejected</span>',
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
            </div>
          </div>
        </div>
      </div>

      <div class="row">
        <div class="col-lg-6">
          {section("Pending — Awaiting Review", "bi-hourglass-split", pending, True)}
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
        url = f"http://127.0.0.1:9010{path}"
        if params:
            url += "?" + urllib.parse.urlencode({k:v for k,v in params.items() if v is not None})
        now = _t.time()
        hit = _BRAIN_CACHE.get(url)
        if hit and (now - hit[0]) < _BRAIN_CACHE_TTL:
            return hit[1]
        with urllib.request.urlopen(url, timeout=3) as r:
            data = _json.loads(r.read().decode())
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
        Brain API v{ver} on :9010 ·
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
          💡 Drop JSON messages in <code>C:\\QIH\\brain\\inbox\\</code> or POST to <code>/api/inbox</code>.
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
        const r = await fetch('http://127.0.0.1:9010/api/search_memory', {{
          method: 'POST', headers: {{'Content-Type':'application/json'}},
          body: JSON.stringify({{query: q, collection: col, n: 10}})
        }});
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


# ── War Room — live view of every agent, project, and dispatch ────────────────

def render_warroom() -> str:
    """The War Room: single-pane-of-glass showing all agents, projects, and
    dispatches in flight. Refreshes every 30s. Data from Brain + Hive registry."""

    snap    = _brain_get("/api/ecosystem_snapshot") or {}
    poll    = _brain_get("/api/poll/status") or {}
    inbox   = _brain_get("/api/inbox/log", {"limit": 5}) or {}
    disp    = _brain_get("/api/dispatches", {"limit": 20}) or {}

    projects    = snap.get("projects", []) if isinstance(snap, dict) else []
    dispatches  = disp.get("dispatches", []) if isinstance(disp, dict) else []
    inbox_items = inbox.get("entries", []) if isinstance(inbox, dict) else []

    # ── Agents panel (Claude Code, Claude Work, CoWork, Claude Chat) ──
    # Infer "last seen" per agent_id from project.last_session/last_active.
    # Without a dedicated sessions endpoint we aggregate from snapshot.
    agent_types = [
        ("claude_code",  "Claude Code",  "bi-terminal",      "primary"),
        ("claude_work",  "Claude Work",  "bi-window-desktop","info"),
        ("cowork",       "CoWork",       "bi-people",        "success"),
        ("claude_chat",  "Claude Chat",  "bi-chat-dots",     "secondary"),
    ]
    agent_cards = ""
    for aid, label, icon, color in agent_types:
        # Find most recent project.last_active that mentions this agent — best effort
        last_touch = "never"
        active_proj = "-"
        for p in sorted(projects, key=lambda x: x.get("last_active","") or "", reverse=True):
            if p.get("last_active"):
                last_touch = (p["last_active"] or "")[:16]
                active_proj = p.get("display_name", p.get("project_id","?"))
                break
        agent_cards += f"""
        <div class="col-md-6 col-xl-3 mb-3">
          <div class="card h-100 border-start border-4 border-{color}">
            <div class="card-body p-3">
              <div class="d-flex justify-content-between align-items-start">
                <h5 class="mb-1"><i class="bi {icon} me-2 text-{color}"></i>{label}</h5>
                <span class="badge text-bg-{color}">agent</span>
              </div>
              <div class="small text-muted mb-1">ID: <code>{aid}</code></div>
              <div class="small">Last active: <strong>{last_touch}</strong></div>
              <div class="small text-muted">on: {active_proj}</div>
            </div>
          </div>
        </div>"""

    # ── Project heat map ──
    # Sort projects by last_active desc
    sorted_proj = sorted(projects, key=lambda p: (p.get("last_active") or ""), reverse=True)
    proj_rows = ""
    for p in sorted_proj:
        pid   = p.get("project_id", "?")
        name  = p.get("display_name", pid)
        phase = p.get("last_phase", "-") or "-"
        stat  = p.get("last_status", "-") or "-"
        last  = (p.get("last_active") or "")[:16] or "never"
        summary = (p.get("last_summary") or "")[:140]
        color = {"active":"success","paused":"secondary","blocked":"danger",
                 "complete":"info"}.get(stat, "secondary")
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
        status = d.get("status", "?")
        badge = {"pending":"warning","approved":"success","rejected":"danger",
                 "discussing":"info","in_progress":"primary","done":"secondary"}.get(status, "secondary")
        disp_rows += f"""
        <tr>
          <td><span class="badge text-bg-{badge}">{status}</span></td>
          <td>{d.get('project_id','-')}</td>
          <td class="small">{(d.get('title','') or '')[:60]}</td>
          <td class="small text-muted">{d.get('from_agent','-')} → {d.get('to_agent','-')}</td>
          <td class="small text-muted">{(d.get('created_at','') or '')[:16]}</td>
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
        inbox_html += f"""
        <div class="border-start border-4 border-{b} ps-2 mb-2 small">
          <span class="badge text-bg-{b}">{i.get('status','?')}</span>
          {i.get('source','-')} · {i.get('kind','-')}
          <span class="text-muted">· {(i.get('received_at','') or '')[:16]}</span>
        </div>"""
    if not inbox_html:
        inbox_html = '<div class="text-muted small">No recent inbox activity.</div>'

    return f"""
    <div class="content-header d-flex justify-content-between align-items-start">
      <div>
        <h1 class="fw-bold"><i class="bi bi-broadcast-pin me-2 text-danger"></i>War Room</h1>
        <p class="text-muted mb-0">
          Single-pane-of-glass across every QI agent, project, and dispatch in flight.
          Auto-refreshes every 30s.
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


@app.get("/warroom", response_class=HTMLResponse)
def warroom_page():
    return base_layout("War Room", render_warroom(), "warroom")


# ── Compliance proxy → Brain Inspector ────────────────────────────────────────
import urllib.request as _ureq
import urllib.error as _uerr

_BRAIN = "http://127.0.0.1:9010"


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


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8600, reload=False)

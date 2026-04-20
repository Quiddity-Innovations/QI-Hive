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

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
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

def base_layout(title: str, content: str, active: str = "") -> str:
    nav_items = [
        ("dashboard", "/",        "bi-speedometer2",  "Dashboard"),
        ("hive",      "/hive",    "bi-hexagon",       "The Hive"),
        ("health",    "/health",  "bi-heart-pulse",   "Health Check"),
        ("board",     "/board",   "bi-kanban",        "Task Board"),
        ("tests",     "/tests",   "bi-bug",           "Tests"),
        ("services",  "/services","bi-gear-wide-connected", "Services"),
        ("tasks",     "/tasks",   "bi-calendar-event",      "Scheduled Tasks"),
        ("usage",     "/usage",   "bi-graph-up-arrow","LLM Usage"),
        ("activity",  "/activity","bi-activity",      "Activity"),
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

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{title} | QI Claude Manager</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/overlayscrollbars@2.11.0/styles/overlayscrollbars.min.css"/>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/font/bootstrap-icons.min.css"/>
  <link rel="stylesheet" href="/static/css/adminlte.min.css"/>
  <style>
    .priority-high   {{ border-left: 4px solid #dc3545 !important; }}
    .priority-medium {{ border-left: 4px solid #ffc107 !important; }}
    .priority-low    {{ border-left: 4px solid #198754 !important; }}
    .kanban-col      {{ min-height: 200px; }}
    .task-card       {{ cursor: grab; margin-bottom: 10px; }}
    .task-card:active{{ cursor: grabbing; }}
    .col-header      {{ font-size: .75rem; font-weight: 700; text-transform: uppercase;
                        letter-spacing: .08em; padding: 8px 12px; border-radius: 6px 6px 0 0; }}
    .badge-agent     {{ font-size: .68rem; }}
    .health-ok       {{ color: #198754; }}
    .health-warn     {{ color: #ffc107; }}
    .health-bad      {{ color: #dc3545; }}
    .sortable-ghost  {{ opacity: .4; }}
  </style>
</head>
<body class="layout-fixed sidebar-expand-lg bg-body-tertiary" data-bs-theme="dark">
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
        <li class="nav-item">
          <a class="nav-link" href="/health" title="Run Health Check">
            <i class="bi bi-heart-pulse"></i>
          </a>
        </li>
      </ul>
    </div>
  </nav>

  <!-- Sidebar -->
  <aside class="app-sidebar bg-body-secondary shadow" data-bs-theme="dark">
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
        <div class="d-flex align-items-center mb-1"><span class="badge text-bg-success me-2" style="width:14px;height:14px;padding:0;">&nbsp;</span><span>Complete</span></div>
        <div class="d-flex align-items-center mb-1"><span class="badge text-bg-warning me-2" style="width:14px;height:14px;padding:0;">&nbsp;</span><span>In Progress</span></div>
        <div class="d-flex align-items-center mb-1"><span class="badge text-bg-danger me-2" style="width:14px;height:14px;padding:0;">&nbsp;</span><span>Backlog</span></div>
        <div class="d-flex align-items-center mb-1"><span class="badge text-bg-success-subtle me-2" style="width:14px;height:14px;padding:0;">&nbsp;</span><span>New</span></div>
        <div class="d-flex align-items-center"><span class="badge text-bg-secondary me-2" style="width:14px;height:14px;padding:0;">&nbsp;</span><span>Retired</span></div>
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
        {content}
      </div>
    </div>
  </main>

  <footer class="app-footer">
    <div class="float-end d-none d-sm-inline">QI Hive v3.0 — Powered by QI Brain</div>
    <strong>Quiddity Innovations</strong>
  </footer>
</div>

<script src="https://cdn.jsdelivr.net/npm/overlayscrollbars@2.11.0/browser/overlayscrollbars.browser.es5.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js"></script>
<script src="/static/js/adminlte.min.js"></script>
</body>
</html>"""

# ── Main Dashboard ────────────────────────────────────────────────────────────

def render_dashboard() -> str:
    status  = load_status()
    agents  = load_agents()
    tasks   = load_tasks()

    proj_colors = {
        "complete":           ("success",         "bi-check-circle-fill"),
        "in_progress":        ("warning",         "bi-play-circle-fill"),
        "backlog":            ("danger",          "bi-inbox-fill"),
        "new":                ("success-subtle",  "bi-stars"),
        "retired":            ("secondary",       "bi-archive-fill"),
        "idle":               ("secondary",       "bi-dash-circle"),
        "active_production":  ("success",         "bi-check-circle-fill"),
        "active_development": ("warning",         "bi-play-circle-fill"),
        "in_development":     ("warning",         "bi-play-circle-fill"),
    }

    # Project small-boxes
    project_cards = ""
    for name, p in status.get("projects", {}).items():
        st = p.get("status","unknown")
        color, icon = proj_colors.get(st, ("secondary","bi-circle"))
        task = p.get("current_task") or "—"
        notes = p.get("notes","")
        open_tasks = sum(1 for t in tasks if t.get("project")==name and t.get("column")!="done")
        project_cards += f"""
        <div class="col-lg-4 col-md-6 col-sm-12">
          <div class="small-box text-bg-{color}">
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

    # Agent table
    model_colors = {
        "claude-haiku-4-5-20251001": "secondary",
        "claude-sonnet-4-6":         "primary",
        "claude-opus-4-6":           "danger",
    }
    agent_rows = ""
    for name, cfg in sorted(agents.items()):
        st  = cfg.get("status","idle")
        mdl = cfg.get("model_default","—")
        mshort = mdl.replace("claude-","").replace("-4-6","").replace("-4-5-20251001","")
        bcol = model_colors.get(mdl,"secondary")
        st_badge = "success" if st=="active" else "secondary"
        scope = cfg.get("scope","—")
        agent_rows += f"""<tr>
          <td><strong>{name.title()}</strong></td>
          <td><span class="badge text-bg-{st_badge}">{st}</span></td>
          <td><span class="badge text-bg-{bcol}">{mshort}</span></td>
          <td class="text-muted">{scope}</td>
        </tr>"""

    # Recent sessions
    session_rows = ""
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
          <span class="badge text-bg-danger fs-6"><i class="bi bi-inbox me-1"></i> Backlog: {col_counts.get("backlog",0)}</span>
          <span class="badge text-bg-warning fs-6"><i class="bi bi-play-circle me-1"></i> In Progress: {col_counts.get("in_progress",0)}</span>
          <span class="badge text-bg-info fs-6"><i class="bi bi-search me-1"></i> Review: {col_counts.get("review",0)}</span>
          <span class="badge text-bg-success fs-6"><i class="bi bi-check-circle me-1"></i> Done: {col_counts.get("done",0)}</span>
          <a href="/board" class="btn btn-sm btn-outline-primary ms-2"><i class="bi bi-kanban me-1"></i> Open Board</a>
          <a href="/health" class="btn btn-sm btn-outline-success"><i class="bi bi-heart-pulse me-1"></i> Health Check</a>
        </div>
      </div>
    </div>

    <!-- Claude usage strip (today + 30d) -->
    <div class="row mb-1">
      <div class="col-lg-3 col-md-6 col-sm-12">
        <div class="small-box text-bg-primary">
          <div class="inner"><h4>{tokens_today}</h4><p>Tokens Today</p></div>
          <i class="small-box-icon bi bi-lightning-charge-fill"></i>
          <a href="/usage" class="small-box-footer text-white text-decoration-none">
            Details <i class="bi bi-arrow-right"></i>
          </a>
        </div>
      </div>
      <div class="col-lg-3 col-md-6 col-sm-12">
        <div class="small-box text-bg-success">
          <div class="inner"><h4>{cost_today}</h4><p>Spend Today</p></div>
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
          <div class="inner"><h4>{cost_30}</h4><p>Spend (30d)</p></div>
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
          <div class="card-header"><h3 class="card-title"><i class="bi bi-people me-2"></i>Agent Team</h3></div>
          <div class="card-body p-0">
            <table class="table table-sm table-hover mb-0">
              <thead><tr><th>Agent</th><th>Status</th><th>Model</th><th>Scope</th></tr></thead>
              <tbody>{agent_rows}</tbody>
            </table>
          </div>
        </div>
      </div>
      <div class="col-lg-6">
        <div class="card">
          <div class="card-header"><h3 class="card-title"><i class="bi bi-journal-text me-2"></i>Session Log</h3></div>
          <div class="card-body p-0">
            <table class="table table-sm table-hover mb-0">
              <thead><tr><th>Session</th><th>Summary</th></tr></thead>
              <tbody>{session_rows}</tbody>
            </table>
          </div>
        </div>
      </div>
    </div>"""

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
        ("backlog",     "Backlog",     "danger"),
        ("in_progress", "In Progress", "warning"),
        ("review",      "Review",      "info"),
        ("done",        "Done",        "success"),
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
            <div class="card task-card priority-{pri}" data-id="{t['id']}">
              <div class="card-body p-2">
                <div class="d-flex justify-content-between align-items-start mb-1">
                  <span class="badge text-bg-{pri_color} badge-agent">{pri}</span>
                  <button class="btn btn-sm btn-link p-0 text-danger" onclick="deleteTask('{t['id']}')" title="Delete">
                    <i class="bi bi-x"></i>
                  </button>
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
      <div class="col-md-8 text-end">
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

    <script>
    // Initialise SortableJS on each column
    document.querySelectorAll('.kanban-col').forEach(col => {{
      Sortable.create(col, {{
        group: 'tasks',
        animation: 150,
        ghostClass: 'sortable-ghost',
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
            ss = _Path(r"C:\UNIVERSAL\DOCUMENTATION\Session_Summaries")
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
        agent_cards = '<div class="col-12"><div class="alert alert-warning">QI Brain offline — agent profiles unavailable.</div></div>'

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
        <a href="http://localhost:9010/docs" target="_blank" class="btn btn-sm btn-outline-secondary">
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
    </div>"""


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

@app.get("/health", response_class=HTMLResponse)
def health_page():
    return base_layout("Health Check", render_health(), "health")

@app.get("/board", response_class=HTMLResponse)
def board_page(project: str = "All"):
    return base_layout("Task Board", render_board(project), "board")

GUIDE_FILE = Path(r"C:\UNIVERSAL\QI_Claude_Manager_Guide.md")

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
            <a href="/static/guide.md" class="btn btn-sm btn-outline-secondary">
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

@app.get("/api/scout/digest")
def api_scout_digest():
    """Fetch AI news digest from NEXUS and return top items."""
    import urllib.request, json as _json
    try:
        with urllib.request.urlopen("http://localhost:8010/scout/digest", timeout=10) as resp:
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
    column: Optional[str] = None
    title: Optional[str] = None
    agent: Optional[str] = None
    priority: Optional[str] = None

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
            if update.column   is not None: t["column"]   = update.column
            if update.title    is not None: t["title"]    = update.title
            if update.agent    is not None: t["agent"]    = update.agent
            if update.priority is not None: t["priority"] = update.priority
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
    return base_layout("Tests", render_tests(), "tests")


# ── /config — log level management ────────────────────────────────────────────

LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def render_config() -> str:
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
    <div class="card">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h5 class="mb-0"><i class="bi bi-sliders"></i> Logging Configuration</h5>
        <span class="badge bg-secondary">Default: {cfg['default_level']}</span>
      </div>
      <div class="card-body">
        <p class="text-muted small mb-3">
          Adjust log verbosity per service. Changes persist to
          <code>config/logging.json</code> and apply immediately to new log
          statements in this Dashboard process. Other services (Brain, tunnels)
          pick up changes on next restart.
        </p>
        <table class="table table-sm table-hover align-middle">
          <thead>
            <tr><th>Service</th><th>Log file</th><th style="width:180px">Level</th></tr>
          </thead>
          <tbody>{table_body}</tbody>
        </table>
        <div id="config-toast" class="text-success small"></div>
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
      const toast = document.getElementById('config-toast');
      toast.textContent = j.ok ? `✓ ${{service}} → ${{level}}` : `✗ Failed`;
      setTimeout(() => toast.textContent = '', 3000);
    }}
    </script>
    """


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
    return base_layout("Logs", render_logs(), "logs")


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
            p = reg.get("projects", {}).get(pid.lower(), {})
            services = p.get("services", []) or []
    except Exception:
        pass

    svc_rows = "".join(
        f"<tr><td><code>{s}</code></td>"
        f"<td><button class='btn btn-sm btn-outline-secondary' onclick=\"alert('service control coming in Session 06')\">status</button></td></tr>"
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
            <span class="badge bg-info">{proj.get('status','?')}</span>
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
    """


@app.get("/project/{pid}", response_class=HTMLResponse)
def project_page(pid: str):
    return base_layout(pid, render_project(pid), "dashboard")


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

    <!-- Row 1: actual spend -->
    <div class="row row-compact mb-1">
      <div class="col-md-3"><div class="small-box text-bg-primary">
        <div class="inner"><h4>{t['tokens']/1_000_000:.1f}M</h4><p>Tokens Today</p></div>
        <i class="small-box-icon bi bi-lightning-charge-fill"></i>
      </div></div>
      <div class="col-md-3"><div class="small-box text-bg-success">
        <div class="inner"><h4>${t['cost_usd']:.2f}</h4><p>Spend Today</p></div>
        <i class="small-box-icon bi bi-currency-dollar"></i>
      </div></div>
      <div class="col-md-3"><div class="small-box text-bg-info">
        <div class="inner"><h4>${t7['cost_usd']:,.0f}</h4><p>Spend (7d)</p></div>
        <i class="small-box-icon bi bi-calendar-week"></i>
      </div></div>
      <div class="col-md-3"><div class="small-box text-bg-warning">
        <div class="inner"><h4>${t30['cost_usd']:,.0f}</h4><p>Spend (30d)</p></div>
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


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8600, reload=False)

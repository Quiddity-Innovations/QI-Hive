# -*- coding: utf-8 -*-
"""
qi_web_panel.py — QI UNIVERSAL WEB CONTROL PANEL
Single web page with internal tabs for every QI project that has a control panel.

Launch:   python C:\\UNIVERSAL\\ECOSYSTEM\\qi_web_panel.py
Open:     http://localhost:8651
Port:     8651  (universal block, adjacent to launcher 8650)

Design:
- Single HTML page. Internal tabs (no new windows).
- Home tab = ecosystem overview (health dots for every project).
- One tab per project: Maia · Naya · NEXUS · OC
- Each project tab: status card, service controls, live log tail.
- Driven by the PROJECTS config below — add a project by adding an entry.

This does NOT replace the project-specific control panels. It's a superset
that wraps them in a single browser tab so you stop juggling command windows.
"""
from __future__ import annotations

import os, re, sys, time, json, socket, subprocess
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
import uvicorn

# ─────────────────────────────────────────────────────────────────────────────
# PROJECT REGISTRY — add new projects here
# ─────────────────────────────────────────────────────────────────────────────
PROJECTS = {
    "maia": {
        "name": "Maia",
        "subtitle": "AI assistant platform · multi-channel",
        "path": r"C:\QI",
        "color": "#6366f1",
        "ports": [
            {"label": "API",       "port": 8001, "url": "http://localhost:8001/health"},
            {"label": "Gradio UI", "port": 7860, "url": "http://localhost:7860"},
        ],
        "services": [
            {"name": "MaiaBot",         "label": "Maia server (FastAPI 8001)"},
            {"name": "MaiaTunnel",      "label": "Cloudflare tunnel (webhooks)"},
            {"name": "MaiaDemoTunnel",  "label": "Demo tunnel (exposes 7860)"},
        ],
        "logs": [
            {"label": "maia_log.txt",         "path": r"C:\QI\logs\maia_log.txt"},
            {"label": "tunnel_log.txt",       "path": r"C:\QI\logs\tunnel_log.txt"},
            {"label": "demo_tunnel_log.txt",  "path": r"C:\QI\logs\demo_tunnel_log.txt"},
            {"label": "maia_error.txt",       "path": r"C:\QI\logs\maia_error.txt"},
        ],
        "tunnel_log":    r"C:\QI\logs\tunnel_log.txt",
        "tunnels": [
            {"label": "Webhooks tunnel (MaiaTunnel)", "serves_port": 8001, "log": r"C:\QI\logs\tunnel_log.txt"},
            {"label": "Demo tunnel (MaiaDemoTunnel)", "serves_port": 7860, "log": r"C:\QI\LOGS\Maia_Gradio_Tunnel_Log.txt"},
        ],
        "pages": [
            {"label": "Gradio Chat UI",       "url": "http://localhost:7860",                    "desc": "Main chat interface"},
            {"label": "Native Control Panel", "url": "http://localhost:8001/control",             "desc": "Maia's built-in web controls"},
            {"label": "Memory Panel",         "url": "http://localhost:8001/panel",               "desc": "Browse facts / people / messages"},
            {"label": "Memory JSON",          "url": "http://localhost:8001/memory",              "desc": "Raw memory dump"},
            {"label": "Conversation History", "url": "http://localhost:8001/history",             "desc": "Recent chat log"},
            {"label": "Cache View",           "url": "http://localhost:8001/cache",               "desc": "LLM response cache"},
            {"label": "Export all memory",    "url": "http://localhost:8001/export",              "desc": "Download memory as JSON"},
            {"label": "Info",                 "url": "http://localhost:8001/info",                "desc": "Project registry info"},
            {"label": "FastAPI Docs",         "url": "http://localhost:8001/docs",                "desc": "Interactive API docs"},
        ],
    },
    "naya": {
        "name": "Naya",
        "subtitle": "File intelligence + brain · sibling bot",
        "path": r"C:\NAYA",
        "color": "#22c55e",
        "ports": [
            {"label": "API",        "port": 8002, "url": "http://localhost:8002/health"},
            {"label": "Gradio UI",  "port": 7861, "url": "http://localhost:7861"},
            {"label": "FileHQ",     "port": 8200, "url": "http://localhost:8200"},
        ],
        "services": [
            {"name": "NayaBot",     "label": "Naya server (Flask 8002)"},
            {"name": "NayaGradio",  "label": "Naya Gradio UI (7861)"},
            {"name": "NayaTunnel",  "label": "Naya Cloudflare tunnel"},
        ],
        "logs": [
            {"label": "naya log",  "path": r"C:\NAYA\logs\naya_log.txt"},
            {"label": "tunnel log","path": r"C:\NAYA\logs\tunnel_log.txt"},
        ],
        "tunnel_log": r"C:\NAYA\logs\tunnel_log.txt",
        "tunnels": [
            {"label": "Gradio tunnel (NayaTunnel)", "serves_port": 7861, "log": r"C:\NAYA\LOGS\naya_tunnel_error.txt"},
        ],
        "pages": [
            {"label": "Gradio UI",     "url": "http://localhost:7861",         "desc": "Main Naya chat/admin"},
            {"label": "API root",      "url": "http://localhost:8002",         "desc": "Flask API"},
            {"label": "API health",    "url": "http://localhost:8002/health",  "desc": "Liveness"},
            {"label": "FileHQ Web UI", "url": "http://localhost:8200",         "desc": "File intelligence engine"},
        ],
    },
    "nexus": {
        "name": "NEXUS",
        "subtitle": "Multi-AI orchestration · scout/synthesize",
        "path": r"C:\NEXUS",
        "color": "#f59e0b",
        "ports": [
            {"label": "API", "port": 8010, "url": "http://localhost:8010/health"},
            {"label": "UI",  "port": 7880, "url": "http://localhost:7880"},
        ],
        "services": [
            {"name": "NEXUSService", "label": "NEXUS server (API 8010 + UI 7880)"},
            {"name": "NEXUSTunnel",  "label": "NEXUS Cloudflare tunnel"},
        ],
        "logs": [
            {"label": "nexus log",  "path": r"C:\NEXUS\logs\nexus_log.txt"},
            {"label": "tunnel log", "path": r"C:\NEXUS\logs\tunnel_log.txt"},
        ],
        "tunnel_log": r"C:\NEXUS\logs\tunnel_log.txt",
        "tunnels": [
            {"label": "UI tunnel (NEXUSTunnel)", "serves_port": 7880, "log": r"C:\NEXUS\LOGS\nexus_tunnel.log"},
        ],
        "pages": [
            {"label": "NEXUS UI",      "url": "http://localhost:7880",        "desc": "Main interface"},
            {"label": "API root",      "url": "http://localhost:8010",        "desc": "FastAPI"},
            {"label": "API health",    "url": "http://localhost:8010/health", "desc": "Liveness"},
            {"label": "API docs",      "url": "http://localhost:8010/docs",   "desc": "Interactive API docs"},
        ],
    },
    "oc": {
        "name": "OpenClaw (OC)",
        "subtitle": "Autonomous orchestrator · WSL-based",
        "path": r"C:\OC",
        "color": "#ec4899",
        "ports": [
            {"label": "Gateway",   "port": 18789, "url": "http://127.0.0.1:18789"},
            {"label": "Dashboard", "port": 18800, "url": "http://127.0.0.1:18800"},
        ],
        "services": [
            {"name": "OC-Keepalive-Service", "label": "OC keepalive monitor"},
        ],
        "logs": [
            {"label": "keepalive daemon",  "path": r"C:\OC\logs\keepalive.log"},
            {"label": "ChatGPT keepalive", "path": r"C:\OC\logs\chatgpt_keepalive.log"},
            {"label": "WSL watchdog",      "path": r"C:\OC\logs\wsl_watchdog.log"},
            {"label": "Kaze digest",       "path": r"C:\OC\logs\kaze_digest.log"},
        ],
        "tunnel_log": None,
        "tunnels": [],
        "pages": [
            {"label": "OC Dashboard", "url": "http://127.0.0.1:18800", "desc": "Main OC dashboard"},
            {"label": "OC Gateway",   "url": "http://127.0.0.1:18789", "desc": "Internal gateway"},
        ],
    },
    "ecosystem": {
        "name": "Ecosystem",
        "subtitle": "Cross-project tools · launchers · QI internals",
        "path": r"C:\UNIVERSAL",
        "color": "#8b5cf6",
        "ports": [
            {"label": "QI Launcher",   "port": 8650, "url": "http://localhost:8650"},
            {"label": "Web Panel",     "port": 8651, "url": "http://localhost:8651"},
        ],
        "services": [],  # none — these are ad-hoc tools
        "logs": [],
        "tunnel_log": None,
        "tunnels": [],
        "pages": [
            {"label": "QI Launcher",        "url": "http://localhost:8650",  "desc": "Project launcher menu"},
            {"label": "QI Web Panel (this)","url": "http://localhost:8651",  "desc": "This very page"},
        ],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.4) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        return s.connect_ex((host, int(port))) == 0
    finally:
        s.close()


def sc_query(service: str) -> str:
    try:
        out = subprocess.run(
            ["sc", "query", service],
            capture_output=True, text=True, timeout=5
        )
        if "does not exist" in (out.stdout + out.stderr).lower():
            return "NOT_INSTALLED"
        m = re.search(r"STATE\s+:\s+\d+\s+(\w+)", out.stdout)
        return m.group(1) if m else "UNKNOWN"
    except Exception as e:
        return f"ERR:{e.__class__.__name__}"


def sc_action(service: str, action: str) -> tuple[bool, str]:
    if action not in ("start", "stop"):
        return False, "invalid action"
    try:
        out = subprocess.run(
            ["sc", action, service],
            capture_output=True, text=True, timeout=20
        )
        combined = (out.stdout + out.stderr)
        ok = out.returncode == 0 or "already" in combined.lower()
        return ok, combined.strip()
    except Exception as e:
        return False, str(e)


def spawn_detached(cmd: str) -> None:
    DETACHED = 0x00000008 | 0x00000200
    subprocess.Popen(
        cmd, shell=True, creationflags=DETACHED,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        close_fds=True,
    )


def tail_file(path: str, max_lines: int = 200) -> str:
    p = Path(path)
    if not p.exists():
        return f"(file not found: {path})"
    try:
        size = p.stat().st_size
        with open(p, "rb") as f:
            f.seek(max(0, size - 131072))
            data = f.read()
        text = data.decode("utf-8", errors="replace")
        lines = text.splitlines()
        return "\n".join(lines[-max_lines:])
    except Exception as e:
        return f"(read error: {e})"


_TUNNEL_URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com", re.I)

def current_tunnel_url(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
        matches = _TUNNEL_URL_RE.findall(text)
        return matches[-1] if matches else None
    except Exception:
        return None


def project_status(pid: str) -> dict:
    cfg = PROJECTS[pid]
    ports = [
        {**p, "open": port_open(p["port"])}
        for p in cfg["ports"]
    ]
    services = [
        {**s, "state": sc_query(s["name"])}
        for s in cfg["services"]
    ]
    healthy = (
        any(p["open"] for p in ports)
        and all(s["state"] in ("RUNNING", "NOT_INSTALLED") for s in services)
        and any(s["state"] == "RUNNING" for s in services if s["state"] != "NOT_INSTALLED")
    ) if services else any(p["open"] for p in ports)

    # Resolve tunnel URLs, indexed by the port each tunnel serves
    tunnels_resolved = []
    tunnel_by_port: dict[int, dict] = {}
    for t in cfg.get("tunnels", []) or []:
        url = current_tunnel_url(t.get("log"))
        entry = {
            "label":       t.get("label", "tunnel"),
            "serves_port": t.get("serves_port"),
            "url":         url,
        }
        tunnels_resolved.append(entry)
        if entry["serves_port"] is not None:
            tunnel_by_port[int(entry["serves_port"])] = entry

    # For each page, attach its tunnel entry (if any tunnel serves its port)
    port_re = re.compile(r":(\d+)")
    pages_out = []
    for pg in cfg.get("pages", []) or []:
        page = dict(pg)  # copy
        m = port_re.search(pg.get("url", ""))
        page_port = int(m.group(1)) if m else None
        tun = tunnel_by_port.get(page_port) if page_port else None
        page["tunnel"] = tun  # None or {label, url, serves_port}
        pages_out.append(page)

    # Legacy single tunnel_url: use the first tunnel that resolved (for header/tiles display)
    legacy_tunnel_url = None
    for t in tunnels_resolved:
        if t.get("url"):
            legacy_tunnel_url = t["url"]
            break
    if legacy_tunnel_url is None:
        # fall back to old "tunnel_log" if still set (pre-migration projects)
        legacy_tunnel_url = current_tunnel_url(cfg.get("tunnel_log"))

    return {
        "id": pid,
        "name":     cfg["name"],
        "subtitle": cfg["subtitle"],
        "color":    cfg["color"],
        "path":     cfg["path"],
        "ports":    ports,
        "services": services,
        "logs":     [{"label": l["label"], "path": l["path"]} for l in cfg["logs"]],
        "tunnel_url": legacy_tunnel_url,
        "tunnels":  tunnels_resolved,
        "pages":    pages_out,
        "healthy":  bool(healthy),
    }


# ─────────────────────────────────────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(title="QI Universal Web Control Panel")


@app.get("/health")
def health():
    return {"status": "ok", "app": "qi_web_panel", "port": 8651}


@app.get("/api/projects")
def api_projects():
    """List of project IDs + names (for tab construction)."""
    return [
        {"id": pid, "name": cfg["name"], "subtitle": cfg["subtitle"], "color": cfg["color"]}
        for pid, cfg in PROJECTS.items()
    ]


@app.get("/api/status")
def api_status():
    """Full ecosystem snapshot — used by the Home tab and every project tab."""
    return {
        "projects": [project_status(pid) for pid in PROJECTS.keys()],
        "ts": int(time.time()),
    }


@app.get("/api/status/{pid}")
def api_status_one(pid: str):
    if pid not in PROJECTS:
        raise HTTPException(404, "unknown project")
    return project_status(pid)


@app.get("/api/logs/{pid}")
def api_logs(pid: str, idx: int = Query(0, ge=0), lines: int = Query(200, ge=10, le=2000)):
    if pid not in PROJECTS:
        raise HTTPException(404, "unknown project")
    logs = PROJECTS[pid]["logs"]
    if idx >= len(logs):
        raise HTTPException(400, "log index out of range")
    return PlainTextResponse(tail_file(logs[idx]["path"], lines))


@app.post("/api/action")
def api_action(payload: dict):
    """
    Actions:
      service.start   {pid, service}
      service.stop    {pid, service}
      service.restart {pid, service}       (detached)
      project.restart {pid}                 (stop all services in project, start all)
      project.stop    {pid}
      project.start   {pid}
    """
    action = (payload or {}).get("action", "")
    pid = (payload or {}).get("pid", "")
    if pid not in PROJECTS:
        raise HTTPException(400, "unknown or missing pid")
    services = PROJECTS[pid]["services"]

    # Service-level
    if action in ("service.start", "service.stop"):
        svc = payload.get("service", "")
        if svc not in [s["name"] for s in services]:
            raise HTTPException(400, f"service {svc!r} not in project {pid}")
        verb = action.split(".")[1]
        ok, msg = sc_action(svc, verb)
        return {"ok": ok, "message": msg}

    if action == "service.restart":
        svc = payload.get("service", "")
        if svc not in [s["name"] for s in services]:
            raise HTTPException(400, f"service {svc!r} not in project {pid}")
        spawn_detached(f'cmd /c "sc stop {svc} & timeout /t 3 >nul & sc start {svc}"')
        return {"ok": True, "message": f"{svc} restart scheduled"}

    if action == "project.start":
        for s in services:
            sc_action(s["name"], "start")
        return {"ok": True, "message": f"started all services in {pid}"}

    if action == "project.stop":
        # Stop in reverse order (so tunnels drop before server)
        for s in reversed(services):
            sc_action(s["name"], "stop")
        return {"ok": True, "message": f"stopped all services in {pid}"}

    if action == "project.restart":
        names = [s["name"] for s in services]
        # Stop in reverse, start in order
        stop_chain = " & ".join(f"sc stop {n}" for n in reversed(names))
        start_chain = " & ".join(f"sc start {n}" for n in names)
        spawn_detached(f'cmd /c "{stop_chain} & timeout /t 4 >nul & {start_chain}"')
        return {"ok": True, "message": f"{pid} restart scheduled"}

    raise HTTPException(400, f"unknown action {action!r}")


# ─────────────────────────────────────────────────────────────────────────────
# HTML PAGE — single page, internal tabs, no new windows opened
# ─────────────────────────────────────────────────────────────────────────────
_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>QI Orchestrator</title>
<style>
:root{
  --bg:#0a0f1e; --bg2:#0d1328; --card:#121a33; --muted:#8a93a6; --text:#e8ecf4;
  --ok:#22c55e; --warn:#f59e0b; --bad:#ef4444; --accent:#6366f1; --accent2:#8b5cf6;
  --border:#263053; --ink:#0a0f22;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--bg);color:var(--text);font:14px/1.45 system-ui,Segoe UI,Roboto,sans-serif;min-height:100vh}
header{padding:12px 20px;background:linear-gradient(90deg,#1a1f3a,#2a1550);border-bottom:1px solid var(--border);display:flex;align-items:center;gap:14px;flex-wrap:wrap;position:sticky;top:0;z-index:20}
header h1{margin:0;font-size:18px;font-weight:700;letter-spacing:.4px}
header .meta{color:var(--muted);font-size:12px}
header .sub{color:#b8c0d9;font-size:12px;margin-left:6px}

.tabs{display:flex;gap:2px;padding:0 20px;background:var(--bg2);border-bottom:1px solid var(--border);overflow-x:auto;position:sticky;top:48px;z-index:19}
.tab{padding:12px 18px;color:#b8c0d9;cursor:pointer;font-weight:600;font-size:13px;letter-spacing:.3px;border-bottom:3px solid transparent;white-space:nowrap;display:flex;align-items:center;gap:8px;transition:all .15s}
.tab:hover{color:#fff;background:rgba(255,255,255,.03)}
.tab.active{color:#fff;border-bottom-color:var(--accent)}
.tab .dot{width:8px;height:8px;border-radius:50%;background:var(--muted)}
.tab .dot.ok{background:var(--ok);box-shadow:0 0 6px var(--ok)}
.tab .dot.bad{background:var(--bad);box-shadow:0 0 6px var(--bad)}
.tab .dot.warn{background:var(--warn);box-shadow:0 0 6px var(--warn)}

main{max-width:1400px;margin:0 auto;padding:18px}
.page{display:none}
.page.active{display:block}

.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px;margin-bottom:18px}
.tile{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:14px 16px 12px;cursor:pointer;transition:all .15s;position:relative;overflow:hidden;display:flex;flex-direction:column;min-height:128px}
.tile:hover{transform:translateY(-2px);border-color:var(--accent)}
.tile .stripe{position:absolute;left:0;top:0;bottom:0;width:4px}
.tile h3{margin:0 0 4px;padding-left:8px;font-size:15px;display:flex;align-items:center;gap:10px}
.tile .sub{color:var(--muted);font-size:12px;padding-left:8px;margin-bottom:10px;min-height:18px}
.tile .stats{display:grid;grid-template-columns:1fr 1fr;gap:6px 14px;padding-left:8px;margin-top:auto}
.tile .stat{display:flex;align-items:center;gap:6px;font-size:11.5px;color:#c7cde0;white-space:nowrap}
.tile .stat b{color:#fff;font-weight:700}
.tile .stat .pill{font-size:9.5px;font-weight:700;letter-spacing:.4px;padding:1px 5px;border-radius:99px;text-transform:uppercase}
.tile .stat .pill.ok{background:rgba(34,197,94,.18);color:var(--ok)}
.tile .stat .pill.bad{background:rgba(239,68,68,.18);color:var(--bad)}
.tile .stat .pill.warn{background:rgba(245,158,11,.18);color:var(--warn)}
.tile .stat .pill.muted{background:#1f2744;color:var(--muted)}

.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media (max-width:900px){.grid{grid-template-columns:1fr}}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
@media (max-width:1100px){.grid3{grid-template-columns:1fr 1fr}}
@media (max-width:700px){.grid3{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px}
.card h2{margin:0 0 10px;font-size:13px;color:#c7cde0;letter-spacing:.5px;text-transform:uppercase;display:flex;align-items:center;gap:8px}
.card h2 .sub{font-size:11px;color:var(--muted);text-transform:none;letter-spacing:0;font-weight:normal}
.row{display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:7px;border:1px solid transparent;margin:1px 0}
.row + .row{border-top:1px dashed #1f2744;border-radius:0 0 7px 7px}
.row .label{flex:1;color:#c7cde0;font-size:13px}
.row .label .sub{display:block;color:var(--muted);font-size:11px;margin-top:1px;font-weight:normal}
.row .val{font-family:ui-monospace,Consolas,monospace;color:#a8b0c8;font-size:13px}
.row.empty{color:var(--muted);font-size:12px;padding:10px;font-style:italic}

.badge{padding:2px 7px;border-radius:999px;font-size:10px;font-weight:700;letter-spacing:.4px;text-transform:uppercase}
.badge.ok{background:rgba(34,197,94,.15);color:var(--ok);border:1px solid rgba(34,197,94,.3)}
.badge.bad{background:rgba(239,68,68,.15);color:var(--bad);border:1px solid rgba(239,68,68,.3)}
.badge.warn{background:rgba(245,158,11,.15);color:var(--warn);border:1px solid rgba(245,158,11,.3)}
.badge.info{background:rgba(99,102,241,.15);color:#a5b4fc;border:1px solid rgba(99,102,241,.3)}

.btnrow{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
button{background:var(--accent);color:white;border:0;padding:7px 12px;border-radius:7px;cursor:pointer;font-weight:600;font-size:12.5px;transition:all .12s}
button:hover{background:var(--accent2)}
button.ghost{background:transparent;border:1px solid var(--border);color:#c7cde0}
button.ghost:hover{background:#1f2744}
button.danger{background:#b91c1c}
button.danger:hover{background:#ef4444}
button.small{padding:4px 10px;font-size:11.5px}

pre.log{margin:0;padding:12px;background:var(--ink);border:1px solid var(--border);border-radius:8px;font:12px/1.45 ui-monospace,Consolas,monospace;color:#a8b0c8;max-height:320px;overflow:auto;white-space:pre-wrap;word-break:break-word}

.urlbox{display:flex;gap:6px;align-items:center;margin-top:6px}
.urlbox input{flex:1;background:var(--ink);border:1px solid #1f2744;color:#e8ecf4;padding:5px 8px;border-radius:6px;font-family:ui-monospace,monospace;font-size:12px}
select,input[type=text]{background:var(--ink);border:1px solid #1f2744;color:#e8ecf4;padding:6px 10px;border-radius:6px;font-size:13px}

.toast{position:fixed;right:20px;bottom:20px;background:#141a2e;border:1px solid var(--border);border-left:4px solid var(--accent);padding:10px 16px;border-radius:8px;font-size:13px;max-width:420px;box-shadow:0 10px 30px rgba(0,0,0,.4);opacity:0;transform:translateY(10px);transition:all .25s;z-index:100}
.toast.show{opacity:1;transform:translateY(0)}
.toast.err{border-left-color:var(--bad)}

.service-row{display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:7px;margin:1px 0;border:1px solid transparent;transition:background .12s}
.service-row + .service-row{border-top:1px dashed #1f2744;border-radius:0 0 7px 7px}
.service-row:hover{background:#1a2243}
.service-row .info{flex:1;min-width:0}
.service-row .name{color:#e8ecf4;font-weight:600;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.service-row .desc{color:var(--muted);font-size:11px;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}

.quick{display:flex;flex-wrap:wrap;gap:6px}

/* Pages / URL directory */
.page-list{display:flex;flex-direction:column;gap:4px}
.page-item{display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:7px;cursor:pointer;transition:all .12s;border:1px solid transparent}
.page-item:hover{background:#1f2744;border-color:var(--border)}
.page-item.active{background:rgba(99,102,241,.12);border-color:rgba(99,102,241,.5)}
.page-item .pl-label{flex:1;min-width:0}
.page-item .pl-name{color:#e8ecf4;font-weight:600;font-size:13px}
.page-item .pl-url{color:var(--muted);font-size:11px;font-family:ui-monospace,monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.page-item .pl-desc{color:#a0a8c0;font-size:11px;margin-top:2px}
.pl-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.pl-dot.ok{background:var(--ok)}
.pl-dot.bad{background:var(--bad);opacity:.5}
.pl-arrow{color:var(--muted);font-size:14px;width:16px;text-align:center;flex-shrink:0}
.tunnel-subrow{margin-left:22px;background:rgba(139,92,246,0.05);border-left:2px solid rgba(139,92,246,0.35)}
.tunnel-subrow .tunnel-badge{font-size:9px;padding:2px 6px}
.tunnel-subrow.tunnel-down{border-left-color:rgba(245,158,11,0.35);background:rgba(245,158,11,0.04)}
.tunnel-subrow:hover{background:rgba(139,92,246,0.10)}

/* Inline iframe viewer */
.viewer{margin-top:14px;border:1px solid var(--border);border-radius:12px;overflow:hidden;background:var(--card)}
.viewer-bar{display:flex;align-items:center;gap:10px;padding:8px 12px;background:#0f1528;border-bottom:1px solid var(--border)}
.viewer-bar .vtitle{flex:1;font-size:12.5px;color:#c7cde0;font-weight:600}
.viewer-bar .vurl{font-family:ui-monospace,monospace;font-size:11px;color:var(--muted);max-width:50%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.viewer-frame{display:block;width:100%;height:600px;background:#fff;border:0}
.viewer-empty{padding:40px;text-align:center;color:var(--muted);font-size:13px;background:#0f1528}

a.link{color:#a5b4fc;text-decoration:none;font-size:12px;margin-right:12px;cursor:pointer}
a.link:hover{text-decoration:underline}
.footer{text-align:center;color:var(--muted);font-size:11px;padding:16px}

.url-group{margin-top:10px}
.url-group-title{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;padding:6px 2px 4px;display:flex;align-items:center;gap:8px}
.url-group-title .color-dot{width:8px;height:8px;border-radius:50%}
</style>
</head>
<body>

<header>
  <h1>🎛️ QI Orchestrator</h1>
  <span class="sub">all projects · all pages · one window · no new tabs</span>
  <span style="flex:1"></span>
  <span class="meta" id="hdr-ts">—</span>
</header>

<nav class="tabs" id="tabs">
  <div class="tab active" data-tab="orch"><span class="dot" id="dot-orch"></span>🎛️ Orchestrator</div>
  <!-- project tabs inserted here -->
</nav>

<main>
  <!-- ORCHESTRATOR PAGE -->
  <section class="page active" id="page-orch">
    <div class="tiles" id="tiles"></div>

    <div class="card" style="margin-bottom:14px">
      <h2>Web Page Directory <span class="sub">click any to open inline · nothing spawns a new tab</span></h2>
      <div id="orch-url-dir"></div>
    </div>

    <div id="orch-viewer-wrap"></div>
    <div class="footer">Running on <span class="val">http://localhost:8651</span> · QI Orchestrator · all-in-one</div>
  </section>
  <!-- project pages inserted here -->
</main>

<div class="toast" id="toast"></div>

<script>
const qs = id => document.getElementById(id);
let PROJECTS = [];
let LAST_DATA = null;

function toast(msg, isErr=false){
  const t = qs('toast'); t.textContent = msg;
  t.classList.toggle('err', !!isErr);
  t.classList.add('show');
  clearTimeout(window._toastT);
  window._toastT = setTimeout(()=>t.classList.remove('show'), 2500);
}

function badge(state){
  const s = (state||'').toUpperCase();
  if(s==='RUNNING') return '<span class="badge ok">RUNNING</span>';
  if(s==='STOPPED') return '<span class="badge bad">STOPPED</span>';
  if(s==='NOT_INSTALLED') return '<span class="badge warn">NOT INSTALLED</span>';
  if(s.startsWith('ERR')) return '<span class="badge bad">'+s+'</span>';
  return '<span class="badge warn">'+(s||'UNKNOWN')+'</span>';
}
function portBadge(open){ return open ? '<span class="badge ok">LIVE</span>' : '<span class="badge bad">DOWN</span>'; }

function healthClass(p){
  const anyOpen    = (p.ports||[]).some(x=>x.open);
  const anyRunning = (p.services||[]).some(x=>x.state==='RUNNING');
  if(p.services.length===0) return anyOpen ? 'ok' : 'warn';
  if(anyOpen && anyRunning) return 'ok';
  if(!anyOpen && !anyRunning) return 'bad';
  return 'warn';
}

/* ── Tabs ── */
function buildTabs(){
  const tabs = qs('tabs');
  PROJECTS.forEach(p => {
    const el = document.createElement('div');
    el.className = 'tab';
    el.dataset.tab = p.id;
    el.innerHTML = '<span class="dot" id="dot-'+p.id+'"></span>'+p.name;
    el.addEventListener('click', ()=>showTab(p.id));
    tabs.appendChild(el);
  });
  tabs.querySelectorAll('.tab').forEach(t=>{
    if(t.dataset.tab==='orch') t.addEventListener('click', ()=>showTab('orch'));
  });
}

function buildPages(){
  const main = document.querySelector('main');
  PROJECTS.forEach(p=>{
    const hasServices = true;  // all project tabs get service section (if pure "ecosystem", just empty)
    const page = document.createElement('section');
    page.className = 'page';
    page.id = 'page-' + p.id;
    page.innerHTML = `
      <div style="margin-bottom:12px;display:flex;align-items:center;gap:12px;flex-wrap:wrap">
        <h2 style="margin:0;font-size:20px">${p.name}</h2>
        <span style="color:var(--muted);font-size:13px">${p.subtitle}</span>
      </div>
      <div class="grid3">
        <div class="card">
          <h2>Status <span class="sub">ports &amp; tunnels</span></h2>
          <div id="${p.id}-ports"></div>
          <div id="${p.id}-tunnels-status" style="margin-top:6px"></div>
        </div>
        <div class="card">
          <h2>Services <span class="sub">start · stop · restart</span></h2>
          <div class="quick" style="margin-bottom:8px">
            <button class="small" onclick="projectAction('${p.id}','project.restart','Restart ALL ${p.name} services?')">⟳ All</button>
            <button class="ghost small" onclick="projectAction('${p.id}','project.start')">▶ Start All</button>
            <button class="danger small" onclick="projectAction('${p.id}','project.stop','Stop ALL ${p.name} services?')">■ Stop All</button>
          </div>
          <div id="${p.id}-svc-controls"></div>
        </div>
        <div class="card">
          <h2>Web Pages <span class="sub">click to open inline</span></h2>
          <div class="page-list" id="${p.id}-pages"></div>
        </div>
      </div>

      <div id="${p.id}-viewer-wrap"></div>

      <div class="card" style="margin-top:14px">
        <h2>Live Log <span class="sub">auto 5s</span></h2>
        <div class="btnrow" style="margin-bottom:6px">
          <select id="${p.id}-logsel"></select>
          <button class="ghost small" onclick="loadLog('${p.id}')">Refresh</button>
          <label style="color:var(--muted);font-size:12px"><input type="checkbox" id="${p.id}-logauto" checked /> auto</label>
        </div>
        <pre class="log" id="${p.id}-logbody">select a log above…</pre>
      </div>
    `;
    main.appendChild(page);
  });
}

function showTab(tabId){
  document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active', t.dataset.tab===tabId));
  document.querySelectorAll('.page').forEach(p=>p.classList.toggle('active', p.id==='page-'+tabId));
  if(tabId!=='orch') loadLog(tabId);
}

/* ── Home tiles ── */
function renderTiles(data){
  const tiles = qs('tiles');
  tiles.innerHTML = '';
  // Render in registry order — matches QI_Universal_Control_Panel.bat:
  //   [1] Maia · [2] Naya · [3] NEXUS · [4] OC · then Ecosystem
  data.projects.forEach(p=>{
    const h = healthClass(p);
    const portsOpen   = p.ports.filter(x=>x.open).length;
    const portsTotal  = p.ports.length;
    const svcRunning  = p.services.filter(x=>x.state==='RUNNING').length;
    const svcTotal    = p.services.length;
    const pagesTotal  = (p.pages||[]).length;
    const tunnelsUp   = (p.tunnels||[]).filter(t=>!!t.url).length;
    const tunnelsTotal= (p.tunnels||[]).length;

    // Helper for a uniform stat pill
    const statPill = (label, ratio, kind) => {
      const cls = (kind==='off') ? 'muted'
                : (ratio === 'ok' ? 'ok' : ratio === 'bad' ? 'bad' : 'warn');
      return `<div class="stat">${label} <span class="pill ${cls}">${kind}</span></div>`;
    };
    const fracPill = (label, have, total, alwaysShow=true) => {
      if(total===0 && !alwaysShow) return '';
      const cls = total===0 ? 'muted'
                : have===total ? 'ok'
                : have===0 ? 'bad' : 'warn';
      const txt = total===0 ? '—' : `${have}/${total}`;
      return `<div class="stat"><span style="color:var(--muted)">${label}</span> <span class="pill ${cls}">${txt}</span></div>`;
    };

    const t = document.createElement('div');
    t.className = 'tile';
    t.dataset.pid = p.id;
    const dotColor = h==='ok' ? 'var(--ok)' : h==='bad' ? 'var(--bad)' : 'var(--warn)';
    t.innerHTML = `
      <div class="stripe" style="background:${p.color}"></div>
      <h3><span style="width:10px;height:10px;border-radius:50%;background:${dotColor};display:inline-block"></span>${p.name}</h3>
      <div class="sub">${p.subtitle}</div>
      <div class="stats">
        ${fracPill('Ports',    portsOpen,   portsTotal)}
        ${fracPill('Services', svcRunning,  svcTotal)}
        ${fracPill('Tunnels',  tunnelsUp,   tunnelsTotal)}
        <div class="stat"><span style="color:var(--muted)">Pages</span> <span class="pill ${pagesTotal>0?'ok':'muted'}">${pagesTotal||'—'}</span></div>
      </div>
    `;
    t.addEventListener('click', ()=>showTab(p.id));
    tiles.appendChild(t);
  });
  // Tab dots
  const allOk = data.projects.every(p=>healthClass(p)==='ok');
  const anyBad = data.projects.some(p=>healthClass(p)==='bad');
  const homeDot = qs('dot-orch');
  if(homeDot) homeDot.className = 'dot ' + (allOk?'ok':(anyBad?'bad':'warn'));
  data.projects.forEach(p=>{
    const d = qs('dot-'+p.id);
    if(d) d.className = 'dot ' + healthClass(p);
  });
}

/* ── Build the DOM for a single "Web Pages" list item.
   Also emits a sub-row for the matching Cloudflare tunnel, if any. ── */
function buildPageRow(viewerPid, project, pg, portMap){
  const out = document.createDocumentFragment();
  const m = pg.url.match(/:(\d+)/);
  const port = m ? parseInt(m[1],10) : null;
  const live = port ? portMap[port] !== false : true;

  // Main row (localhost URL)
  const row = document.createElement('div');
  row.className = 'page-item';
  row.innerHTML = `
    <span class="pl-dot ${live ? 'ok':'bad'}"></span>
    <div class="pl-label">
      <div class="pl-name">${pg.label}</div>
      <div class="pl-url">${pg.url}${pg.desc?(' <span style=\"color:#8a93a6\">— '+pg.desc+'</span>'):''}</div>
    </div>
    <button class="ghost small" onclick="event.stopPropagation();copyText('${pg.url}')">Copy</button>
  `;
  row.addEventListener('click', ()=>{
    openInViewer(viewerPid, pg.url, project.name+' · '+pg.label);
    document.querySelectorAll('.page-item').forEach(x=>x.classList.remove('active'));
    row.classList.add('active');
  });
  out.appendChild(row);

  // Tunnel sub-row (directly below), only if a tunnel serves this page's port
  const tun = pg.tunnel;
  if(tun && tun.url){
    const trow = document.createElement('div');
    trow.className = 'page-item tunnel-subrow';
    trow.innerHTML = `
      <span class="pl-arrow">↳</span>
      <span class="badge info tunnel-badge">TUNNEL</span>
      <div class="pl-label">
        <div class="pl-name" style="font-size:12px;color:#c7cde0">${tun.label || 'Public tunnel'}</div>
        <div class="pl-url">${tun.url}</div>
      </div>
      <button class="ghost small" onclick="event.stopPropagation();copyText('${tun.url}')">Copy</button>
    `;
    trow.addEventListener('click', ()=>{
      openInViewer(viewerPid, tun.url, project.name+' · '+pg.label+' (tunnel)');
      document.querySelectorAll('.page-item').forEach(x=>x.classList.remove('active'));
      trow.classList.add('active');
    });
    out.appendChild(trow);
  } else if(tun && !tun.url){
    // Tunnel configured but URL not yet captured (tunnel service may be stopped)
    const trow = document.createElement('div');
    trow.className = 'page-item tunnel-subrow tunnel-down';
    trow.innerHTML = `
      <span class="pl-arrow">↳</span>
      <span class="badge warn tunnel-badge">TUNNEL</span>
      <div class="pl-label">
        <div class="pl-name" style="font-size:12px;color:var(--muted)">${tun.label || 'Public tunnel'}</div>
        <div class="pl-url" style="color:var(--muted)">(no URL yet — tunnel stopped or log empty)</div>
      </div>
    `;
    out.appendChild(trow);
  }
  return out;
}

/* ── Master URL directory (Orchestrator tab) ── */
function renderDirectory(data){
  const dir = qs('orch-url-dir');
  dir.innerHTML = '';
  data.projects.forEach(p=>{
    const portOpenMap = {};
    p.ports.forEach(x=>{ portOpenMap[x.port] = x.open; });
    const pages = p.pages || [];
    if(pages.length===0) return;
    const group = document.createElement('div');
    group.className = 'url-group';
    const title = document.createElement('div');
    title.className = 'url-group-title';
    title.innerHTML = `<span class="color-dot" style="background:${p.color}"></span>${p.name} · ${p.subtitle}`;
    group.appendChild(title);
    pages.forEach(pg => group.appendChild(buildPageRow('orch', p, pg, portOpenMap)));
    dir.appendChild(group);
  });
}

/* ── Project tab pages list ── */
function renderProjectPages(p){
  const host = qs(p.id+'-pages');
  if(!host) return;
  host.innerHTML = '';
  const portMap = {}; p.ports.forEach(x=>{ portMap[x.port] = x.open; });
  (p.pages||[]).forEach(pg => host.appendChild(buildPageRow(p.id, p, pg, portMap)));
}

/* ── Inline viewer (iframe) ── */
function openInViewer(pid, url, title){
  const wrap = qs((pid==='orch'?'orch':pid)+'-viewer-wrap');
  wrap.innerHTML = `
    <div class="viewer">
      <div class="viewer-bar">
        <span class="vtitle">${title}</span>
        <span class="vurl">${url}</span>
        <button class="ghost small" onclick="copyText('${url}')">Copy URL</button>
        <button class="ghost small" onclick="document.getElementById('v-${pid}').src=document.getElementById('v-${pid}').src">Reload</button>
        <button class="ghost small" onclick="closeViewer('${pid}')">Close</button>
      </div>
      <iframe id="v-${pid}" class="viewer-frame" src="${url}" referrerpolicy="no-referrer"></iframe>
    </div>
  `;
  // Scroll the iframe into view so they don't have to hunt for it
  wrap.scrollIntoView({behavior:'smooth', block:'start'});
}
function closeViewer(pid){
  const wrap = qs((pid==='orch'?'orch':pid)+'-viewer-wrap');
  wrap.innerHTML = '';
}

/* ── Project status cards ── */
function renderProject(p){
  // Status card — Ports
  const portsEl = qs(p.id+'-ports');
  if(portsEl){
    portsEl.innerHTML = p.ports.length === 0
      ? '<div class="row empty">(no ports configured)</div>'
      : p.ports.map(x=>
          `<div class="row"><span class="label">${x.label}<span class="sub">localhost:${x.port}</span></span>${portBadge(x.open)}</div>`
        ).join('');
  }
  // Status card — Tunnels (compact, read-only summary)
  const tunEl = qs(p.id+'-tunnels-status');
  if(tunEl){
    const tunnels = p.tunnels || [];
    if(tunnels.length === 0){
      tunEl.innerHTML = '<div class="row empty">(no public tunnels)</div>';
    } else {
      tunEl.innerHTML = tunnels.map(t=>{
        const live = !!t.url;
        const badgeHtml = live
          ? '<span class="badge ok">PUBLIC</span>'
          : '<span class="badge warn">DOWN</span>';
        const subTxt = live ? t.url : '(no URL — tunnel stopped or log empty)';
        return `<div class="row">
          <span class="label">${t.label||'tunnel'}<span class="sub">serves :${t.serves_port||'?'} · ${subTxt}</span></span>
          ${badgeHtml}
        </div>`;
      }).join('');
    }
  }

  // Services card — controls
  const ctrl = qs(p.id+'-svc-controls');
  if(ctrl){
    ctrl.innerHTML = p.services.length === 0
      ? '<div class="row empty">(no managed services)</div>'
      : p.services.map(s=>`
          <div class="service-row">
            <div class="info">
              <div class="name">${s.name}</div>
              <div class="desc">${s.label}</div>
            </div>
            ${badge(s.state)}
            <div class="btnrow">
              <button class="ghost small" onclick="svcAction('${p.id}','${s.name}','service.start')">Start</button>
              <button class="ghost small" onclick="svcAction('${p.id}','${s.name}','service.restart')">⟳</button>
              <button class="danger small" onclick="svcAction('${p.id}','${s.name}','service.stop')">Stop</button>
            </div>
          </div>
        `).join('');
  }

  const sel = qs(p.id+'-logsel');
  if(sel && sel.options.length !== p.logs.length){
    if(p.logs.length===0){
      sel.innerHTML = '<option>(no logs configured)</option>';
    } else {
      sel.innerHTML = p.logs.map((l,i)=>`<option value="${i}">${l.label}</option>`).join('');
    }
  }

  renderProjectPages(p);
}

/* ── Actions ── */
async function svcAction(pid, service, action){
  try{
    const r = await fetch('/api/action', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({action, pid, service})});
    const d = await r.json();
    if(!r.ok) throw new Error(d.detail||('HTTP '+r.status));
    toast('✓ '+service+' '+action.split('.')[1]);
    setTimeout(refresh, 500);
    setTimeout(refresh, 3500);
  }catch(e){ toast('✗ '+e.message, true); }
}

async function projectAction(pid, action, confirmMsg){
  if(confirmMsg && !confirm(confirmMsg)) return;
  try{
    const r = await fetch('/api/action', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({action, pid})});
    const d = await r.json();
    if(!r.ok) throw new Error(d.detail||('HTTP '+r.status));
    toast('✓ '+pid+' '+action.split('.')[1]);
    setTimeout(refresh, 500);
    setTimeout(refresh, 4000);
  }catch(e){ toast('✗ '+e.message, true); }
}

function copyText(url){
  navigator.clipboard.writeText(url);
  toast('copied '+url);
}

async function loadLog(pid){
  const sel = qs(pid+'-logsel');
  if(!sel || sel.options.length===0) return;
  const idx = sel.value || 0;
  try{
    const r = await fetch('/api/logs/'+pid+'?idx='+idx+'&lines=200');
    if(!r.ok){ qs(pid+'-logbody').textContent = '(HTTP '+r.status+')'; return; }
    const t = await r.text();
    const el = qs(pid+'-logbody');
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 30;
    el.textContent = t;
    if(atBottom) el.scrollTop = el.scrollHeight;
  }catch(e){ qs(pid+'-logbody').textContent = '(error: '+e.message+')'; }
}

/* ── Refresh loop ── */
async function refresh(){
  try{
    const r = await fetch('/api/status');
    if(!r.ok) throw new Error('HTTP '+r.status);
    const d = await r.json();
    LAST_DATA = d;
    qs('hdr-ts').textContent = new Date(d.ts*1000).toLocaleTimeString();
    renderTiles(d);
    renderDirectory(d);
    d.projects.forEach(renderProject);
  }catch(e){ console.error(e); }
}

/* ── Boot ── */
(async function init(){
  const r = await fetch('/api/projects');
  PROJECTS = await r.json();
  buildTabs();
  buildPages();
  // ensure Orchestrator tab has a viewer wrap host
  if(!qs('orch-viewer-wrap')){
    const host = document.createElement('div');
    host.id = 'orch-viewer-wrap';
    document.querySelector('#page-orch').appendChild(host);
  }
  PROJECTS.forEach(p=>{
    const sel = qs(p.id+'-logsel');
    if(sel) sel.addEventListener('change', ()=>loadLog(p.id));
  });
  await refresh();
  setInterval(refresh, 5000);
  setInterval(()=>{
    const active = document.querySelector('.tab.active')?.dataset.tab;
    if(!active || active==='orch') return;
    const auto = qs(active+'-logauto');
    if(auto && auto.checked) loadLog(active);
  }, 5000);
})();
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(_HTML)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("QI_PANEL_PORT", "8651"))
    print(f"[qi_web_panel] starting on http://localhost:{port}")
    print(f"[qi_web_panel] projects: {list(PROJECTS.keys())}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

# -*- coding: utf-8 -*-
"""
qi_context_loader.py — Core project context engine for QI Session Intelligence.

Given a project_id, returns a formatted briefing string containing:
  - Last session summary (from Brain API)
  - Current project state (phase, status, version)
  - Pending decisions / feature reviews
  - Next Up list
  - Key file paths Claude needs to know
  - Recent doc excerpts (Implementation Log, Meeting Minutes)

Called by both hooks:
  - session_context.py     (SessionStart — loads global ecosystem map)
  - user_prompt_hook.py    (UserPromptSubmit — loads per-project context)
"""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BRAIN_URL   = "http://127.0.0.1:9010"  # 127.0.0.1 not localhost — avoids Windows IPv6 2s fallback
MEM_DIR     = r"C:\Users\renne\.claude\projects\C--Users-renne-Downloads\memory"
SESSION_STATE = Path(r"C:\QIH\qi_session\session_state.json")  # migrated 2026-04-22 from C:\UNIVERSAL\qi_session

# ── Project registry ───────────────────────────────────────────────────────────
# Maps every recognisable keyword to a canonical project entry.
# "keywords"  → words that, if found in a user message, identify this project
# "brain_id"  → project_id in the Brain DB (qi_brain.db)
# "path"      → root folder on disk
# "doc_dir"   → where Implementation Log / Meeting Minutes live (may not exist)
# "memory_file" → Claude memory file name inside MEM_DIR
# "logs"      → key log files for quick tailing
# "services"  → QI_ NSSM service names
PROJECTS = {
    "maia": {
        "name": "Maia",
        "keywords": ["maia", "mai", "line bot", "telegram bot", "gradio", "maia_server"],
        "brain_id": "maia",
        "path": r"C:\QI",
        "doc_dir": r"C:\QI\DOCUMENTATION",
        "memory_file": "project_maia_bot.md",
        "logs": [r"C:\QI\LOGS\maia_log.txt", r"C:\QI\LOGS\maia_service_log.txt"],
        "services": ["QI_MaiaBot", "QI_MaiaTunnel", "QI_MaiaDemoTunnel"],
        "version": "0.2",
        "doc_names": {
            "impl": "Quiddity Innovations - Maia Implementation Log.md",
            "minutes": "Quiddity Innovations - Maia Meeting Minutes.md",
            "status": "Quiddity Innovations - Maia Master Status Report.md",
        },
    },
    "naya": {
        "name": "Naya",
        "keywords": ["naya", "personal assistant", "file scout", "filehq", "file hq"],
        "brain_id": "naya",
        "path": r"C:\NAYA",
        "doc_dir": r"C:\NAYA\DOCUMENTATION",
        "memory_file": "project_naya.md",
        "logs": [r"C:\NAYA\LOGS\naya_service_log.txt"],
        "services": ["QI_NayaBot", "QI_NayaGradio"],
        "version": "0.2",
        "doc_names": {
            "impl":    "Naya_Implementation_Log.md",
            "minutes": "Naya_Meeting_Minutes.md",
            "version": "Naya_Version_History.md",
            "status":  "Naya_Master_Status_Report.md",
        },
    },
    "nexus": {
        "name": "NEXUS",
        "keywords": ["nexus", "orchestration", "multi-ai", "multi ai", "nexus ai"],
        "brain_id": "nexus",
        "path": r"C:\NEXUS",
        "doc_dir": r"C:\NEXUS\Quiddity Innovations - NEXUS Documentation",
        "memory_file": "project_nexus.md",
        "logs": [r"C:\NEXUS\LOGS\nexus_service.log"],
        "services": ["QI_NEXUS"],
        "version": "0.1",
        "doc_names": {
            "impl":    "NEXUS_Implementation_Log.docx",
            "minutes": "NEXUS_Meeting_Minutes.docx",
            "version": "NEXUS_Version_History.docx",
            "status":  "NEXUS_Master_Status_Report.md",
        },
    },
    "openclaw": {
        "name": "OpenClaw",
        "keywords": ["openclaw", "open claw", "claw", "kaze", "tasuke", "sentry", "seiri", "yubin", "koe"],
        "brain_id": "openclaw",
        "path": r"C:\OC",
        "doc_dir": r"C:\OC\DOCUMENTATION",
        "memory_file": "openclaw_project.md",
        "logs": [],
        "services": [],
        "version": "0.1",
        "doc_names": {
            "impl":    "OpenClaw_Implementation_Log.md",
            "minutes": "OpenClaw_Meeting_Minutes.md",
            "version": "OpenClaw_Version_History.md",
            "status":  "OpenClaw_Master_Status_Report.md",
        },
    },
    "easyflow": {
        "name": "EasyFlow",
        # EasyFlow is a Chrome Extension for Gmail label management (Manifest V3)
        "keywords": ["easyflow", "easy flow", "gmail label", "gmail extension",
                     "chrome extension", "email triage", "label management"],
        "brain_id": "easyflow",
        "path": r"C:\EasyFlow",
        "doc_dir": r"C:\EasyFlow\DOCUMENTATION",
        "memory_file": None,
        "logs": [],
        "services": [],  # No NSSM service yet — Chrome extension
        "version": "1.1.9.10",
        "doc_names": {
            "impl":    "EasyFlow_Implementation_Log.md",
            "minutes": "EasyFlow_Meeting_Minutes.md",
            "version": "EasyFlow_Version_History.md",
            "status":  "EasyFlow_Master_Status_Report.md",
        },
        "notes": "Chrome Extension (Manifest V3). Gmail/People API. AI triage via GPT/Gemini/Claude. Phase 1 complete, Phase 2 (Outlook/Teams) next.",
    },
    "universal": {
        "name": "QI Orchestrator (migrated into QIH on 2026-04-22)",
        "keywords": ["orchestrator", "dashboard", "brain", "qi brain", "qi dashboard",
                     "universal", "ecosystem", "nightly backup", "training"],
        "brain_id": "universal",
        "path": r"C:\QIH",  # was C:\UNIVERSAL — migrated 2026-04-22, see docs/UNIVERSAL_MIGRATION_PLAN.md
        "doc_dir": r"C:\QIH\shared\documentation",
        "memory_file": "project_qi_orchestrator.md",
        "logs": [r"C:\QIH\engine\hive\dashboard\LOGS\dashboard.log",
                 r"C:\QIH\engine\hive\tunnel\LOGS\tunnel_manager.log"],
        "services": ["QI_Dashboard", "QI_DashboardTunnel", "QI_BrainAPI"],
        "version": "1.2",
        "doc_names": {},
    },
}

# Flat keyword → project_id lookup (longest match wins)
KEYWORD_MAP = {}
for pid, cfg in PROJECTS.items():
    for kw in cfg["keywords"]:
        KEYWORD_MAP[kw.lower()] = pid


# ── Public helpers ─────────────────────────────────────────────────────────────

def detect_project(message: str) -> str | None:
    """Return project_id if a known keyword appears in message, else None."""
    msg = message.lower()
    # Sort by keyword length descending so "qi brain" beats "brain"
    for kw in sorted(KEYWORD_MAP, key=len, reverse=True):
        if kw in msg:
            return KEYWORD_MAP[kw]
    return None


def load_session_state() -> dict:
    if SESSION_STATE.exists():
        try:
            return json.loads(SESSION_STATE.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {}


def save_session_state(project_id: str, project_name: str) -> None:
    SESSION_STATE.write_text(json.dumps({
        "project_id": project_id,
        "project_name": project_name,
        "briefed_at": datetime.now(timezone.utc).isoformat(),
    }, indent=2), encoding='utf-8')


def _brain_post(endpoint: str, payload: dict) -> dict | None:
    """POST to Brain API. Returns parsed JSON or None on failure."""
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            f"{BRAIN_URL}{endpoint}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def _read_tail(path: str, lines: int = 50) -> str:
    """Read last N non-empty lines from a text file."""
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            all_lines = [l.rstrip() for l in f if l.strip()]
        return "\n".join(all_lines[-lines:])
    except Exception:
        return ""


def _read_memory_file(filename: str) -> str:
    if not filename:
        return ""
    path = os.path.join(MEM_DIR, filename)
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            return f.read().strip()
    except Exception:
        return ""


def _audit_project_docs(cfg: dict) -> list[str]:
    """Return list of missing standard doc labels for this project."""
    doc_dir = cfg.get("doc_dir", "")
    doc_names = cfg.get("doc_names", {})
    if not doc_dir:
        return []
    missing = []
    labels = {
        "impl":    "Implementation Log",
        "minutes": "Meeting Minutes",
        "version": "Version History",
        "status":  "Master Status Report",
    }
    for key, label in labels.items():
        fname = doc_names.get(key)
        if not fname:
            missing.append(f"{label} (not registered in doc_names)")
            continue
        full_path = os.path.join(doc_dir, fname)
        if not os.path.exists(full_path):
            missing.append(f"{label} (file missing: {fname})")
    return missing


def build_briefing(project_id: str) -> str:
    """Build a complete context briefing for a project. Returns a formatted string."""
    cfg = PROJECTS.get(project_id)
    if not cfg:
        return f"[QI Session] Unknown project: {project_id}"

    lines = []
    sep = "═" * 54

    lines.append(f"\n{sep}")
    lines.append(f"  🤖  QI SESSION BRIEF — {cfg['name'].upper()}")
    lines.append(sep)

    # ── Brain API: context (state + decisions + pending) ──────────────────────
    ctx = _brain_post("/api/context", {"project_id": cfg["brain_id"]})

    if ctx:
        state = ctx.get("current_state") or {}
        if state:
            phase   = state.get("phase", "—")
            status  = state.get("status", "—")
            summary = state.get("summary", "")
            lines.append(f"\n📊 CURRENT STATE")
            lines.append(f"   Phase:  {phase}")
            lines.append(f"   Status: {status}  |  v{cfg['version']}")
            if summary:
                lines.append(f"   {summary[:200]}")
        else:
            lines.append(f"\n📊 CURRENT STATE  v{cfg['version']}  (state not yet recorded in Brain)")

        # Recent sessions
        sessions = ctx.get("recent_sessions") or []
        if sessions:
            last = sessions[0]
            lines.append(f"\n📅 LAST SESSION")
            lines.append(f"   {last.get('session_title','—')}")
            s = last.get('summary','')
            if s:
                lines.append(f"   {s[:300]}")
            ns = last.get('next_steps','')
            if ns:
                lines.append(f"\n🔄 NEXT UP (from last session)")
                for i, step in enumerate(ns.split('|'), 1):
                    step = step.strip()
                    if step:
                        lines.append(f"   {i}. {step}")

        # Pending feature reviews
        pending = ctx.get("pending_features") or []
        if pending:
            lines.append(f"\n⚠️  PENDING FEATURE REVIEWS: {len(pending)}")
            for pf in pending[:3]:
                lines.append(f"   • {pf.get('feature_name','?')}  [{pf.get('recommendation','?')}  score={pf.get('relevance_score',0):.2f}]")
            if len(pending) > 3:
                lines.append(f"   … and {len(pending)-3} more")

    else:
        lines.append(f"\n⚠️  Brain API offline — loading from memory files only")

    # ── Memory file ───────────────────────────────────────────────────────────
    mem = _read_memory_file(cfg.get("memory_file"))
    if mem:
        # Extract just the first 60 lines (high-density summary)
        mem_lines = [l for l in mem.splitlines() if l.strip()][:60]
        lines.append(f"\n📋 PROJECT MEMORY SNAPSHOT")
        lines.append("\n".join(mem_lines))

    # ── Key docs (last 40 lines each) ────────────────────────────────────────
    doc_dir = cfg.get("doc_dir", "")
    doc_names = cfg.get("doc_names", {})
    for key in ("impl", "minutes"):
        dname = doc_names.get(key)
        if not dname or not doc_dir:
            continue
        path = os.path.join(doc_dir, dname)
        tail = _read_tail(path, 40)
        if tail:
            label = "IMPLEMENTATION LOG (recent)" if key == "impl" else "MEETING MINUTES (recent)"
            lines.append(f"\n📄 {label}")
            lines.append(tail)

    # ── Doc audit ─────────────────────────────────────────────────────────────
    missing_docs = _audit_project_docs(cfg)
    if missing_docs:
        lines.append(f"\n⚠️  MISSING STANDARD DOCS — CREATE BEFORE STARTING WORK")
        for d in missing_docs:
            lines.append(f"   ❌ {d}")
    else:
        lines.append(f"\n✅ All standard docs present")

    # ── Key paths ─────────────────────────────────────────────────────────────
    lines.append(f"\n📁 KEY PATHS")
    lines.append(f"   Code root:   {cfg['path']}")
    if doc_dir:
        lines.append(f"   Docs:        {doc_dir}")
    if cfg.get("logs"):
        lines.append(f"   Primary log: {cfg['logs'][0]}")
    if cfg.get("services"):
        lines.append(f"   Services:    {', '.join(cfg['services'])}")

    lines.append(f"\n{sep}")
    lines.append(f"  Context loaded at {datetime.now().strftime('%H:%M:%S')}  |  Brain: {'✅' if ctx else '❌ offline'}")
    lines.append(sep + "\n")

    return "\n".join(lines)


def build_global_briefing() -> str:
    """Minimal ecosystem-level briefing for SessionStart (no project yet known)."""
    lines = ["[QI Ecosystem — Session Start]"]

    # Read MEMORY.md index
    mem_index = os.path.join(MEM_DIR, "MEMORY.md")
    try:
        with open(mem_index, encoding='utf-8', errors='replace') as f:
            lines.append("\n=== MEMORY INDEX ===\n" + f.read().strip())
    except Exception:
        pass

    # Read user profile
    user_mem = os.path.join(MEM_DIR, "user_renne.md")
    try:
        with open(user_mem, encoding='utf-8', errors='replace') as f:
            lines.append("\n=== USER PROFILE ===\n" + f.read().strip())
    except Exception:
        pass

    # Read feedback rules (all feedback_*.md)
    for fname in sorted(os.listdir(MEM_DIR)):
        if fname.startswith("feedback_") and fname.endswith(".md"):
            path = os.path.join(MEM_DIR, fname)
            try:
                with open(path, encoding='utf-8', errors='replace') as f:
                    lines.append(f"\n=== {fname} ===\n" + f.read().strip())
            except Exception:
                pass

    lines.append("\n[Waiting for project selection — say which project to load full context]")
    return "\n\n".join(lines)


def build_new_project_prompt(name: str) -> str:
    """Return a briefing string for an unrecognised project name."""
    registered = [f"{pid} ({cfg['name']})" for pid, cfg in PROJECTS.items()]
    return (
        f"\n{'═'*54}\n"
        f"  🆕  UNRECOGNISED PROJECT: \"{name}\"\n"
        f"{'═'*54}\n"
        f"\nThis doesn't match any registered QI project.\n"
        f"Registered: {', '.join(registered)}\n\n"
        f"OPTIONS:\n"
        f"  A) Scaffold a new QI project (standard structure + memory file + Brain registration)\n"
        f"  B) It's a sub-feature of an existing project (tell me which)\n"
        f"  C) It was a typo — let me know the correct name\n\n"
        f"If this is a NEW project, I will create:\n"
        f"  C:\\{{Name}}\\ with DOCUMENTATION\\ LOGS\\ TOOLS\\ CLAUDE.md\n"
        f"  Memory file in C:\\Users\\renne\\.claude\\projects\\...\\memory\\\n"
        f"  Brain DB registration + qi_registry.json entry\n"
        f"{'═'*54}\n"
    )

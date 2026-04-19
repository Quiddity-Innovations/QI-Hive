"""
Quiddity Innovations — New Project Wizard
Creates a fully compliant QI project scaffold from day one.

Usage:
    python qi_new_project.py
    python qi_new_project.py --name HERALD --desc "AI news aggregator" --path C:\\HERALD

What it does:
  1. Validates the name/path don't conflict with existing projects
  2. Assigns the next available port from the correct block
  3. Registers the project in qi_registry.json
  4. Scaffolds all folders per QI_Standards.md
  5. Creates CLAUDE.md with ecosystem safety rules
  6. Creates requirements.txt, .gitignore, secrets template
  7. Creates FastAPI skeleton with /health, /version, /info
  8. Creates Gradio UI skeleton (optional)
  9. Initializes git repo
 10. Runs qi_validator.py to confirm compliance
"""
import sys
import os
import json
import argparse
import subprocess
import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ECOSYSTEM_DIR = Path(__file__).parent
REGISTRY_PATH = ECOSYSTEM_DIR / "qi_registry.json"


def load_registry() -> dict:
    """Load and return the QI ecosystem registry from qi_registry.json."""
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_registry(registry: dict):
    """Write the updated registry back to qi_registry.json."""
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
    print(f"  [OK] Registry updated: {REGISTRY_PATH}")


def next_available_port_block(registry: dict, service: str = "api") -> tuple[int, str]:
    """Find the next available port block for a new project."""
    used_ports = set()
    for proj in registry["projects"]:
        for svc, info in proj.get("ports", {}).items():
            p = info.get("current")
            if p:
                used_ports.add(p)

    blocks = registry["port_strategy"]["api_blocks"]
    for block_range, owner in blocks.items():
        if "Reserved" in owner or "Overflow" in owner:
            if "Reserved" in owner:
                # Use reserved block for new project
                start = int(block_range.split("-")[0])
                for port in range(start, start + 10):
                    if port not in used_ports:
                        return port, block_range
    # Fallback: find any free port above 8500
    for port in range(8500, 9000):
        if port not in used_ports:
            return port, "8500-8599"
    raise ValueError("No available ports found")


def next_available_ui_port(registry: dict) -> int:
    """Find the next unused Gradio UI port in the 7840-7899 range."""
    used = set()
    for proj in registry["projects"]:
        for svc, info in proj.get("ports", {}).items():
            if svc == "ui":
                p = info.get("current")
                if p:
                    used.add(p)
    for port in range(7840, 7900):
        if port not in used:
            return port
    raise ValueError("No available UI ports")


def scaffold_project(name: str, project_id: str, description: str,
                     path: Path, api_port: int, ui_port: int, family_tier: str):
    """Create all folders and files for a new QI project."""
    doc_folder = path / f"Quiddity Innovations - {name} Documentation"

    folders = [
        path / "config",
        path / "shared",
        path / "secrets",
        path / "data" / "logs",
        path / "api",
        path / "ui",
        doc_folder / "User Documentation",
        doc_folder / "Technical Documentation",
        doc_folder / "Business Documentation",
        doc_folder / "Cheatsheets",
        doc_folder / "Session Summaries",
        doc_folder / "Meeting Minutes",
        doc_folder / "Implementation Log",
    ]
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)
    print(f"  [OK] Folder structure created")

    # .gitignore
    (path / ".gitignore").write_text(f"""# {name} — Git Ignore
secrets/
*.env
{project_id}.db
*.db-wal
*.db-shm
data/logs/
data/responses/
__pycache__/
*.pyc
.venv/
venv/
.vscode/
.idea/
Thumbs.db
""", encoding="utf-8")
    print(f"  [OK] .gitignore created")

    # secrets template
    (path / "secrets" / f"{project_id}.env.template").write_text(f"""# {name} API Keys — DO NOT COMMIT THIS FILE
# Copy to secrets/{project_id}.env and fill in values

# Add your API keys here
""", encoding="utf-8")
    print(f"  [OK] secrets/{project_id}.env.template created")

    # requirements.txt
    (path / "requirements.txt").write_text(f"""# {name} Requirements
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
gradio>=5.0.0
httpx>=0.27.0
python-dotenv>=1.0.0
python-docx>=1.1.0
pydantic>=2.7.0
""", encoding="utf-8")
    print(f"  [OK] requirements.txt created")

    # config/project.json
    (path / "config" / f"{project_id}.json").write_text(json.dumps({
        "app": {"name": name, "version": "0.1.0", "description": description},
        "server": {"api_port": api_port, "ui_port": ui_port, "host": "127.0.0.1"},
        "logging": {"level": "INFO", "log_dir": "data/logs"}
    }, indent=2), encoding="utf-8")
    print(f"  [OK] config/{project_id}.json created")

    # CLAUDE.md
    all_projects = load_registry()["projects"]
    other_ports = "\n".join(
        f"| {p['name']} | {p['path']} | "
        f"{p.get('ports',{}).get('api',{}).get('current','—')} | "
        f"{p.get('ports',{}).get('ui',{}).get('current','—')} |"
        for p in all_projects if p["id"] != project_id
    )
    (path / "CLAUDE.md").write_text(f"""# {name} — Claude Project Instructions
# Quiddity Innovations

## READ BEFORE ACTING
This is the {name} project. You are operating inside the QI ecosystem.
Before any structural change (ports, folders, configs, new files), read:
- `C:\\QI\\ECOSYSTEM\\QI_Standards.md` — all naming/folder/code conventions
- `C:\\QI\\ECOSYSTEM\\qi_registry.json` — all ports and project relationships
- `C:\\QI\\ECOSYSTEM\\QI_Architecture_Principles.md` — the governing law

## What {name} Is
{description}
Family tier: **{family_tier}**

## Paths
- Code home: `{path}`
- Documentation: `{path}\\Quiddity Innovations - {name} Documentation\\`

## Ports (DO NOT CHANGE without updating qi_registry.json first)
- API: **{api_port}** (block: 8500-8599)
- UI:  **{ui_port}**

## Parallel Projects — Do Not Break
| Project | Path | API | UI |
|---|---|---|---|
{other_ports}
""", encoding="utf-8")
    print(f"  [OK] CLAUDE.md created")

    # shared/config.py
    (path / "shared" / "config.py").write_text(f"""\"\"\"
{name} — Config loader
\"\"\"
import json, os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "config" / "{project_id}.json"
SECRETS_PATH = ROOT / "secrets" / "{project_id}.env"
_cache = None

def load_config() -> dict:
    global _cache
    if _cache: return _cache
    if SECRETS_PATH.exists():
        load_dotenv(SECRETS_PATH)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        _cache = json.load(f)
    return _cache

def get(key_path: str, default=None):
    cfg = load_config()
    for part in key_path.split("."):
        if isinstance(cfg, dict) and part in cfg:
            cfg = cfg[part]
        else:
            return default
    return cfg
""", encoding="utf-8")
    (path / "shared" / "__init__.py").write_text("", encoding="utf-8")

    # api/main.py — FastAPI with required contract endpoints
    (path / "api" / "main.py").write_text(f"""\"\"\"
{name} — FastAPI REST API (Port {api_port})
Quiddity Innovations

Implements the QI Module Interface Contract:
  GET /health  — liveness check
  GET /version — identity
  GET /info    — full self-description
\"\"\"
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    sys.path.insert(0, r"C:\\QI\\ECOSYSTEM")
    from qi_registry import QI
    _cors = QI.cors_origins()
except Exception:
    _cors = ["http://localhost:{api_port}", "http://localhost:{ui_port}"]

app = FastAPI(
    title="{name} API",
    description="{description} — Quiddity Innovations",
    version="0.1.0"
)
app.add_middleware(CORSMiddleware, allow_origins=_cors,
                   allow_methods=["GET", "POST"], allow_headers=["*"])

# ── QI Module Interface Contract (required) ──────────────────────

@app.get("/health")
async def health():
    return {{"status": "ok"}}

@app.get("/version")
async def version():
    return {{"project": "{project_id}", "version": "0.1.0", "status": "development"}}

@app.get("/info")
async def info():
    try:
        sys.path.insert(0, r"C:\\QI\\ECOSYSTEM")
        from qi_registry import QI
        return QI.project("{project_id}")
    except Exception:
        return {{"project": "{project_id}", "name": "{name}"}}

# ── Add your endpoints below this line ───────────────────────────
""", encoding="utf-8")
    (path / "api" / "__init__.py").write_text("", encoding="utf-8")
    print(f"  [OK] api/main.py created (with /health, /version, /info)")

    # ui/app.py — Gradio skeleton
    (path / "ui" / "app.py").write_text(f"""\"\"\"
{name} — Gradio UI (Port {ui_port})
Quiddity Innovations
\"\"\"
import gradio as gr
import httpx
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

API_BASE = "http://127.0.0.1:{api_port}"

def check_status():
    try:
        r = httpx.get(f"{{API_BASE}}/health", timeout=3)
        return "Online" if r.status_code == 200 else "Error"
    except Exception:
        return "Offline"

def build_ui():
    with gr.Blocks(title="{name} — Quiddity Innovations") as demo:
        gr.Markdown("# {name}\\n*Quiddity Innovations*")
        with gr.Tab("Status"):
            status_btn = gr.Button("Check Status")
            status_out = gr.Textbox(label="API Status")
            status_btn.click(fn=check_status, outputs=status_out)
        with gr.Tab("About"):
            gr.Markdown(\"\"\"
**{name}** v0.1.0
{description}
Quiddity Innovations AI Platform
\"\"\")
    return demo

if __name__ == "__main__":
    build_ui().launch(server_port={ui_port}, server_name="127.0.0.1")
""", encoding="utf-8")
    (path / "ui" / "__init__.py").write_text("", encoding="utf-8")
    print(f"  [OK] ui/app.py created")

    # main.py entry point
    (path / "main.py").write_text(f"""\"\"\"
{name} — Main Entry Point
Quiddity Innovations AI Platform
Usage: python main.py
\"\"\"
import sys, os, threading, logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(ROOT, "data", "logs"), exist_ok=True)
logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(ROOT, "data", "logs", "{project_id}.log"), encoding="utf-8")
    ])
logger = logging.getLogger("{project_id}.main")

def start_api():
    import uvicorn
    logger.info("Starting {name} API on http://127.0.0.1:{api_port}")
    uvicorn.run("api.main:app", host="127.0.0.1", port={api_port}, log_level="warning")

def start_ui():
    from ui.app import build_ui
    logger.info("Starting {name} UI on http://127.0.0.1:{ui_port}")
    build_ui().launch(server_port={ui_port}, server_name="127.0.0.1", quiet=True)

if __name__ == "__main__":
    logger.info("{'='*50}")
    logger.info("{name} - Quiddity Innovations")
    logger.info("{'='*50}")
    threading.Thread(target=start_api, daemon=True).start()
    start_ui()
""", encoding="utf-8")
    print(f"  [OK] main.py created")

    # Startup bat
    (path / f"Start_{name}.bat").write_text(f"""@echo off
title {name} — Quiddity Innovations
echo.
echo  {name} — Quiddity Innovations
echo  API: http://localhost:{api_port}
echo  UI:  http://localhost:{ui_port}
echo.
cd /d {path}
python main.py
pause
""", encoding="utf-8")
    print(f"  [OK] Start_{name}.bat created")


def register_project(registry: dict, project_id: str, name: str, description: str,
                     path: str, api_port: int, ui_port: int, family_tier: str):
    """Add the new project to qi_registry.json."""
    new_entry = {
        "id": project_id,
        "name": name,
        "description": description,
        "path": path,
        "github": "TBD",
        "status": "new",
        "primary_language": "Python",
        "ports": {
            "api": {"current": api_port, "block": "8500-8599"},
            "ui":  {"current": ui_port,  "block": "7840-7849"}
        },
        "family_tier": family_tier,
        "family_notes": f"New project — family role to be determined as it develops.",
        "integrates_with": [],
        "exposes_to_ecosystem": [
            "GET /health",
            "GET /version",
            "GET /info"
        ],
        "consumes_from_ecosystem": []
    }
    registry["projects"].append(new_entry)
    registry["_meta"]["last_updated"] = datetime.date.today().isoformat()
    save_registry(registry)


def main():
    """Interactive wizard: gather project info, register, scaffold, and validate."""
    parser = argparse.ArgumentParser(description="QI New Project Wizard")
    parser.add_argument("--name", help="Project name (e.g. HERALD)")
    parser.add_argument("--desc", help="Short description")
    parser.add_argument("--path", help="Full path (e.g. C:\\HERALD)")
    parser.add_argument("--tier", default="cousin",
                        choices=["core","backbone","sibling","sibling_candidate","cousin","marriage_candidate"],
                        help="Family tier")
    args = parser.parse_args()

    print("=" * 60)
    print("  Quiddity Innovations — New Project Wizard")
    print("=" * 60)
    print()

    # Gather inputs
    name = args.name or input("  Project name (e.g. HERALD): ").strip()
    if not name:
        print("  Name is required."); sys.exit(1)

    project_id = name.lower()
    description = args.desc or input(f"  Description for {name}: ").strip()
    path_str = args.path or input(f"  Root path (e.g. C:\\{name.upper()}): ").strip()
    path = Path(path_str)
    family_tier = args.tier

    registry = load_registry()

    # Conflict checks
    existing_ids = [p["id"] for p in registry["projects"]]
    if project_id in existing_ids:
        print(f"\n  [FAIL] Project '{project_id}' already exists in the registry.")
        sys.exit(1)
    if path.exists():
        print(f"\n  [WARN] Path {path} already exists — scaffolding into it.")

    # Assign ports
    api_port, block = next_available_port_block(registry)
    ui_port = next_available_ui_port(registry)

    print(f"\n  Project ID:   {project_id}")
    print(f"  Name:         {name}")
    print(f"  Path:         {path}")
    print(f"  API port:     {api_port} (block {block})")
    print(f"  UI port:      {ui_port}")
    print(f"  Family tier:  {family_tier}")
    print()

    confirm = input("  Proceed? (y/n): ").strip().lower()
    if confirm != "y":
        print("  Cancelled.")
        sys.exit(0)

    print("\n  [ Step 1: Register in qi_registry.json ]")
    register_project(registry, project_id, name, description,
                     str(path), api_port, ui_port, family_tier)

    print("\n  [ Step 2: Scaffold project structure ]")
    path.mkdir(parents=True, exist_ok=True)
    scaffold_project(name, project_id, description, path,
                     api_port, ui_port, family_tier)

    print("\n  [ Step 3: Initialize git ]")
    try:
        subprocess.run(["git", "init"], cwd=str(path), capture_output=True)
        subprocess.run(["git", "config", "user.name", "Renne Santiago"], cwd=str(path), capture_output=True)
        subprocess.run(["git", "config", "user.email", "renne@quiddityinnovations.com"], cwd=str(path), capture_output=True)
        print("  [OK] Git initialized")
    except Exception as e:
        print(f"  [WARN] Git init failed: {e}")

    print("\n  [ Step 4: Validate compliance ]")
    result = subprocess.run(
        [sys.executable, str(ECOSYSTEM_DIR / "qi_validator.py"), "--project", project_id],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    print(result.stdout)

    print("\n" + "="*60)
    print(f"  Project '{name}' created successfully!")
    print(f"  Path:    {path}")
    print(f"  API:     http://localhost:{api_port}")
    print(f"  UI:      http://localhost:{ui_port}")
    print(f"\n  Next steps:")
    print(f"  1. cd {path}")
    print(f"  2. pip install -r requirements.txt")
    print(f"  3. python main.py")
    print("=" * 60)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
Deploy the Hive reporter kit into every known project's .claude folder.

For each project in status.json:
  1. mkdir <project_path>\\.claude if missing
  2. write/merge CLAUDE.md — append the hive obligation block
  3. write/merge settings.json — merge hooks without clobbering existing ones

Safe to re-run. Reports what it did.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\QIH")
STATUS = ROOT / "data" / "status.json"
KIT = ROOT / "templates" / "claude_hookkit"

HIVE_MARK_START = "<!-- QI_HIVE_REPORT_BLOCK_START -->"
HIVE_MARK_END = "<!-- QI_HIVE_REPORT_BLOCK_END -->"


def render_claude_md(project_id: str) -> str:
    body = (KIT / "CLAUDE.md").read_text(encoding="utf-8")
    body = body.replace("<PROJECT_ID>", project_id)
    return f"\n\n{HIVE_MARK_START}\n{body}\n{HIVE_MARK_END}\n"


def render_settings(project_id: str) -> dict:
    raw = (KIT / "settings.json").read_text(encoding="utf-8")
    raw = raw.replace("{{PROJECT_ID}}", project_id)
    return json.loads(raw)


def upsert_claude_md(claude_dir: Path, project_id: str) -> str:
    path = claude_dir / "CLAUDE.md"
    block = render_claude_md(project_id)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if HIVE_MARK_START in existing:
            # Replace existing block
            start = existing.index(HIVE_MARK_START)
            end = existing.index(HIVE_MARK_END) + len(HIVE_MARK_END)
            new = existing[:start] + block.strip() + existing[end:]
            path.write_text(new, encoding="utf-8")
            return "updated"
        path.write_text(existing + block, encoding="utf-8")
        return "appended"
    path.write_text(block.lstrip(), encoding="utf-8")
    return "created"


def upsert_settings(claude_dir: Path, project_id: str) -> str:
    path = claude_dir / "settings.json"
    new_hooks = render_settings(project_id)["hooks"]
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
        existing.setdefault("hooks", {})
        for event, entries in new_hooks.items():
            existing["hooks"].setdefault(event, [])
            # Idempotent: skip if a hook with our hive_report command already exists
            has_hive = any(
                "hive_report.py" in (h.get("command") or "")
                for entry in existing["hooks"][event]
                for h in entry.get("hooks", [])
            )
            if not has_hive:
                existing["hooks"][event].extend(entries)
        path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
        return "merged"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"hooks": new_hooks}, indent=2, ensure_ascii=False), encoding="utf-8")
    return "created"


def main() -> None:
    if not STATUS.exists():
        print(f"[ERROR] {STATUS} not found")
        sys.exit(1)
    s = json.loads(STATUS.read_text(encoding="utf-8"))
    projects = s.get("projects", {})
    print(f"Deploying hive reporter kit to {len(projects)} projects...")
    print()
    results = []
    for pid, meta in projects.items():
        if meta.get("status") == "retired":
            results.append((pid, "skipped", "retired"))
            continue
        proj_path = Path(meta.get("path", ""))
        if not proj_path.exists():
            results.append((pid, "skipped", f"path missing: {proj_path}"))
            continue
        claude_dir = proj_path / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        md = upsert_claude_md(claude_dir, pid)
        sj = upsert_settings(claude_dir, pid)
        results.append((pid, "ok", f"CLAUDE.md={md}, settings.json={sj}"))

    print(f"{'PROJECT':<22} {'STATUS':<10} DETAIL")
    print("-" * 70)
    for pid, status, detail in results:
        print(f"{pid:<22} {status:<10} {detail}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
Project Status renderer — Maia-style tabbed page for any QI project.

Each project's INTRO dir contains 6 files:
    status_intro.md
    status_documentation.json
    status_features_business.json
    status_features_dev.json
    status_future.json
    status_techstack.json

This module reads those files and emits HTML matching Maia's Gradio Project
Status tab (Overview & Features, Overview & Blueprint, Feature Status
Business, Feature Status Dev, Future Enhancements, Technology Stack,
Docs & Demo Guide).

For projects where an INTRO dir is missing or partial, render a friendly
"not yet populated" card so the page still works.
"""
from __future__ import annotations
import html
import json
from pathlib import Path

# Project id -> (display_name, INTRO dir). Single source of truth for which
# projects get a Project Status page.
PROJECT_INTRO: dict[str, tuple[str, Path]] = {
    "maia":     ("Maia",      Path(r"C:\QI\INTRO")),
    "naya":     ("Naya",      Path(r"C:\NAYA\INTRO")),
    "nexus":    ("NEXUS",     Path(r"C:\NEXUS\INTRO")),
    "easyflow": ("EasyFlow",  Path(r"C:\EasyFlow\INTRO")),
    "qi_hive":  ("QI Hive",   Path(r"C:\QIH\INTRO")),
    "qi_brain": ("QI Brain",  Path(r"C:\QIH\engine\brain\INTRO")),
}

STATUS_BADGE = {
    "live":     '<span class="badge bg-success">Live</span>',
    "partial":  '<span class="badge bg-warning text-dark">Partial</span>',
    "planned":  '<span class="badge bg-info text-dark">Planned</span>',
    "disabled": '<span class="badge bg-secondary">Disabled</span>',
    "pending":  '<span class="badge bg-warning text-dark">Pending</span>',
}

PRIORITY_BADGE = {
    "high":   '<span class="badge bg-danger">HIGH PRIORITY</span>',
    "medium": '<span class="badge bg-warning text-dark">MEDIUM PRIORITY</span>',
    "low":    '<span class="badge bg-secondary">LOW PRIORITY</span>',
}


def list_projects() -> list[dict]:
    """List projects whose INTRO dir exists, for the selector nav."""
    out = []
    for pid, (name, intro) in PROJECT_INTRO.items():
        out.append({
            "pid": pid,
            "name": name,
            "ready": intro.exists() and any(intro.iterdir()),
            "intro": str(intro),
        })
    return out


def _read_json(intro: Path, name: str):
    p = intro / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return {"_error": f"parse error: {e}"}


def _read_md(intro: Path, name: str) -> str | None:
    p = intro / name
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8")


# ── Tab renderers ─────────────────────────────────────────────────────────────

def _tab_overview(intro: Path) -> str:
    md = _read_md(intro, "status_intro.md")
    if not md:
        return _empty("status_intro.md not found in " + str(intro))
    # Minimal Markdown -> HTML
    import re
    out = []
    for line in md.splitlines():
        if line.startswith("# "):
            out.append(f"<h3 class='text-primary'>{html.escape(line[2:])}</h3>")
        elif line.startswith("## "):
            out.append(f"<h5 class='text-primary mt-4'>{html.escape(line[3:])}</h5>")
        elif line.startswith("### "):
            out.append(f"<h6 class='mt-3'>{html.escape(line[4:])}</h6>")
        elif line.startswith("- "):
            out.append(f"<li>{_inline_md(line[2:])}</li>")
        elif line.strip().startswith("|"):
            out.append(_render_md_table_row(line))
        elif not line.strip():
            out.append("<br/>")
        else:
            out.append(f"<p>{_inline_md(line)}</p>")
    html_body = "\n".join(out)
    # Wrap consecutive <li> in <ul>
    html_body = re.sub(r"(<li>.*?</li>\s*)+", lambda m: "<ul>" + m.group(0) + "</ul>", html_body, flags=re.DOTALL)
    return f"<div class='card'><div class='card-body'>{html_body}</div></div>"


def _tab_blueprint(intro: Path, project_name: str) -> str:
    """Blueprint tab — shows architecture diagrams if present."""
    svgs = sorted(intro.glob("*.svg"))
    if not svgs:
        return _empty(f"No SVG diagrams in {intro} — drop architecture/schema SVGs here.")
    parts = []
    for svg in svgs:
        try:
            svg_body = svg.read_text(encoding="utf-8")
            parts.append(
                f"<div class='card mb-3'><div class='card-header'>"
                f"<i class='bi bi-diagram-3'></i> {html.escape(svg.stem)}</div>"
                f"<div class='card-body text-center'>{svg_body}</div></div>"
            )
        except Exception as e:
            parts.append(_empty(f"Could not read {svg.name}: {e}"))
    return "\n".join(parts)


def _tab_features_business(intro: Path) -> str:
    data = _read_json(intro, "status_features_business.json")
    if data is None:
        return _empty("status_features_business.json not found")
    if isinstance(data, dict) and "_error" in data:
        return _empty(data["_error"])

    # Count totals
    live = partial = planned = total = 0
    for cat in data:
        for f in cat.get("features", []):
            total += 1
            s = f.get("status", "").lower()
            if s == "live":    live += 1
            elif s == "partial": partial += 1
            elif s == "planned": planned += 1

    header = f"""
    <div class='row g-2 mb-3'>
      <div class='col'><div class='card text-center'><div class='card-body py-2'>
        <div class='h4 text-success mb-0'>{live}</div><small>Live</small></div></div></div>
      <div class='col'><div class='card text-center'><div class='card-body py-2'>
        <div class='h4 text-warning mb-0'>{partial}</div><small>Partial / Built</small></div></div></div>
      <div class='col'><div class='card text-center'><div class='card-body py-2'>
        <div class='h4 text-info mb-0'>{planned}</div><small>Planned</small></div></div></div>
      <div class='col'><div class='card text-center'><div class='card-body py-2'>
        <div class='h4 mb-0'>{total}</div><small>Total Features</small></div></div></div>
    </div>"""

    blocks = []
    for cat in data:
        rows = []
        for f in cat.get("features", []):
            notes = html.escape(f.get("notes", "") or "")
            desc = html.escape(f.get("description", ""))
            desc_full = desc + (f"<br><small class='text-muted'>{notes}</small>" if notes else "")
            badge = STATUS_BADGE.get(f.get("status", "").lower(), html.escape(f.get("status", "")))
            rows.append(
                f"<tr><td><strong>{html.escape(f.get('name',''))}</strong></td>"
                f"<td>{desc_full}</td><td style='width:110px'>{badge}</td></tr>"
            )
        blocks.append(f"""
        <div class='card mb-3'><div class='card-header'><strong>{html.escape(cat.get('category',''))}</strong></div>
        <table class='table table-sm mb-0'>
          <thead><tr><th>Capability</th><th>What it does</th><th>Status</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table></div>""")
    return header + "\n".join(blocks)


def _tab_features_dev(intro: Path) -> str:
    data = _read_json(intro, "status_features_dev.json")
    if data is None:
        return _empty("status_features_dev.json not found")
    if isinstance(data, dict) and "_error" in data:
        return _empty(data["_error"])

    blocks = []
    for cat in data:
        rows = []
        for f in cat.get("features", []):
            badge = STATUS_BADGE.get(f.get("status", "").lower(), html.escape(f.get("status", "")))
            rows.append(
                f"<tr>"
                f"<td><strong>{html.escape(f.get('name',''))}</strong></td>"
                f"<td><code>{html.escape(f.get('file',''))}</code></td>"
                f"<td style='width:110px'>{badge}</td>"
                f"<td class='small text-muted'>{html.escape(f.get('detail',''))}</td>"
                f"</tr>"
            )
        blocks.append(f"""
        <div class='card mb-3'><div class='card-header'><strong>{html.escape(cat.get('category',''))}</strong></div>
        <table class='table table-sm mb-0'>
          <thead><tr><th>Component</th><th>File / Function</th><th>Status</th><th>Technical Detail</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table></div>""")
    return "\n".join(blocks)


def _tab_future(intro: Path) -> str:
    data = _read_json(intro, "status_future.json")
    if data is None:
        return _empty("status_future.json not found")
    if isinstance(data, dict) and "_error" in data:
        return _empty(data["_error"])

    blocks = []
    for cat in data.get("categories", []):
        priority = PRIORITY_BADGE.get(cat.get("priority", "").lower(), "")
        items = []
        for item in cat.get("items", []):
            items.append(
                f"<li class='list-group-item'>"
                f"<strong>{html.escape(item.get('title',''))}</strong>"
                f"<div class='small text-muted mt-1'>{html.escape(item.get('detail',''))}</div>"
                f"</li>"
            )
        blocks.append(f"""
        <div class='card mb-3'>
          <div class='card-header d-flex align-items-center gap-2'>
            <strong>{html.escape(cat.get('name',''))}</strong> {priority}
          </div>
          <ul class='list-group list-group-flush'>{''.join(items)}</ul>
        </div>""")
    return "\n".join(blocks)


def _tab_techstack(intro: Path) -> str:
    data = _read_json(intro, "status_techstack.json")
    if data is None:
        return _empty("status_techstack.json not found")
    if isinstance(data, dict) and "_error" in data:
        return _empty(data["_error"])

    rows = []
    last_layer = None
    for r in data.get("table", []):
        layer = r.get("layer", "")
        layer_cell = layer if layer != last_layer else ""
        last_layer = layer
        rows.append(
            f"<tr>"
            f"<td><strong>{html.escape(layer_cell)}</strong></td>"
            f"<td>{html.escape(r.get('technology',''))}</td>"
            f"<td class='small'>{html.escape(r.get('role',''))}</td>"
            f"<td class='small text-muted'>{html.escape(r.get('license',''))}</td>"
            f"<td class='small text-muted'>{html.escape(r.get('version',''))}</td>"
            f"</tr>"
        )
    table = f"""
    <div class='card mb-3'><div class='card-header'><strong>Technology Summary</strong></div>
    <table class='table table-sm mb-0'>
      <thead><tr><th>Layer</th><th>Technology</th><th>Role</th><th>License</th><th>Version</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table></div>"""

    dives = []
    for d in data.get("descriptions", []):
        dives.append(
            f"<div class='card mb-2'><div class='card-body'>"
            f"<h6 class='mb-2'>{html.escape(d.get('title',''))}</h6>"
            f"<div class='small'>{html.escape(d.get('body',''))}</div>"
            f"</div></div>"
        )
    dive_section = ("<h6 class='mt-3 mb-2'>Technology Deep Dives</h6>" + "\n".join(dives)) if dives else ""
    return table + dive_section


def _tab_docs(intro: Path) -> str:
    data = _read_json(intro, "status_documentation.json")
    if data is None:
        return _empty("status_documentation.json not found")
    if isinstance(data, dict) and "_error" in data:
        return _empty(data["_error"])

    blocks = []
    for section in data.get("sections", []):
        items = []
        for doc in section.get("documents", []):
            items.append(
                f"<div class='mb-3 pb-2 border-bottom'>"
                f"<div><strong>{html.escape(doc.get('title',''))}</strong> "
                f"<span class='badge bg-light text-dark'>{html.escape(doc.get('type',''))}</span></div>"
                f"<div class='small text-muted'><code>{html.escape(doc.get('location',''))}{html.escape(doc.get('file',''))}</code></div>"
                f"<div class='small mt-1'>{html.escape(doc.get('description',''))}</div>"
                f"</div>"
            )
        blocks.append(
            f"<div class='card mb-3'><div class='card-header'><strong>{html.escape(section.get('name',''))}</strong></div>"
            f"<div class='card-body'>{''.join(items)}</div></div>"
        )
    return "\n".join(blocks)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _empty(msg: str) -> str:
    return (f"<div class='alert alert-warning'><i class='bi bi-info-circle'></i> "
            f"{html.escape(msg)}</div>")


def _inline_md(text: str) -> str:
    import re
    out = html.escape(text)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    return out


def _render_md_table_row(line: str) -> str:
    # Very small md-table handler: | a | b | -> <tr><td>...
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if all(c.strip("- :") == "" for c in cells):
        return ""  # separator row
    tds = "".join(f"<td>{_inline_md(c)}</td>" for c in cells)
    return f"<tr>{tds}</tr>"


# ── Main render ───────────────────────────────────────────────────────────────

def render_project_status(pid: str, tab: str = "overview") -> tuple[str, str]:
    """Return (page_title, html_body) for /project/<pid>/status."""
    entry = PROJECT_INTRO.get(pid.lower())
    if not entry:
        return (
            pid,
            _empty(f"No Project Status mapping for '{pid}'. "
                   "Add it to PROJECT_INTRO in project_status.py."),
        )
    name, intro = entry
    if not intro.exists():
        return (
            f"{name} — Project Status",
            _empty(f"INTRO folder not found: {intro}\n"
                   f"Seed it with status_*.json + status_intro.md "
                   f"(copy the shape from C:\\QI\\INTRO\\)."),
        )

    tabs = [
        ("overview",  "bi-clipboard-data", "Overview & Features"),
        ("blueprint", "bi-diagram-3",      "Overview & Blueprint"),
        ("business",  "bi-check2-square",  "Feature Status (Business)"),
        ("dev",       "bi-braces-asterisk","Feature Status (Dev)"),
        ("future",    "bi-fire",           "Future Enhancements"),
        ("techstack", "bi-cpu",            "Technology Stack"),
        ("docs",      "bi-journal-text",   "Docs & Demo Guide"),
    ]
    nav = "".join(
        f"<li class='nav-item'>"
        f"<a class='nav-link {'active' if t==tab else ''}' "
        f"href='/project/{pid}/status?tab={t}'>"
        f"<i class='bi {icon}'></i> {label}</a></li>"
        for t, icon, label in tabs
    )

    body_map = {
        "overview":  lambda: _tab_overview(intro),
        "blueprint": lambda: _tab_blueprint(intro, name),
        "business":  lambda: _tab_features_business(intro),
        "dev":       lambda: _tab_features_dev(intro),
        "future":    lambda: _tab_future(intro),
        "techstack": lambda: _tab_techstack(intro),
        "docs":      lambda: _tab_docs(intro),
    }
    body = body_map.get(tab, body_map["overview"])()

    # Project selector (top bar) so you can jump between projects
    selector_links = []
    for p in list_projects():
        active = " fw-bold text-primary" if p["pid"] == pid else ""
        ready = "" if p["ready"] else " text-muted"
        selector_links.append(
            f"<a href='/project/{p['pid']}/status' class='me-3{active}{ready}'>"
            f"{html.escape(p['name'])}</a>"
        )
    selector = (
        "<div class='card mb-3'><div class='card-body py-2 small'>"
        "<strong class='me-3'>Project:</strong>"
        f"{''.join(selector_links)}"
        "</div></div>"
    )

    page = f"""
    <div class='d-flex justify-content-between align-items-center mb-3'>
      <div><h3 class='mb-0'>{html.escape(name)} — Project Status</h3>
        <small class='text-muted'>Source: <code>{html.escape(str(intro))}</code></small></div>
      <a href='/project/{pid}' class='btn btn-sm btn-outline-secondary'>
        <i class='bi bi-arrow-left'></i> Back to project overview</a>
    </div>
    {selector}
    <ul class='nav nav-tabs mb-3'>{nav}</ul>
    {body}
    """
    return (f"{name} — Project Status", page)

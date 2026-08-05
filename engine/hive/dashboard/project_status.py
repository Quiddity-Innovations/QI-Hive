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

_REGISTRY_PATH = Path(r"C:\QIH\ecosystem\qi_registry.json")

# Hardcoded overrides: pid -> (display_name, INTRO dir).
# These take precedence over registry-derived paths. Keep as-is — do not delete.
PROJECT_INTRO: dict[str, tuple[str, Path]] = {
    "maia":      ("Maia",      Path(r"C:\QI\INTRO")),
    "naya":      ("Naya",      Path(r"C:\NAYA\INTRO")),
    "nexus":     ("NEXUS",     Path(r"C:\NEXUS\INTRO")),
    "easyflow":  ("EasyFlow",  Path(r"C:\EasyFlow\INTRO")),
    "qi_hive":   ("QI Hive",   Path(r"C:\QIH\INTRO")),
    "qi_brain":  ("QI Brain",  Path(r"C:\QIH\engine\brain\INTRO")),
    "filehq":    ("FileHQ",    Path(r"C:\NAYA\filehq\INTRO")),
    "openclaw":  ("OpenClaw",  Path(r"C:\OC\INTRO")),
    "mq":        ("MQ",        Path(r"C:\MQ\INTRO")),
    "autopdf":   ("AutoPDF",   Path(r"C:\AutoPDF\INTRO")),
    "cognibase": ("CogniBase", Path(r"C:\CogniBase\INTRO")),
    "mapsnap":   ("MapSnap",   Path(r"C:\MapSnap\INTRO")),
}


def _load_registry() -> dict[str, dict]:
    """Return {pid: registry_entry} for every project in qi_registry.json."""
    try:
        data = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
        return {p["id"].lower(): p for p in data.get("projects", []) if "id" in p}
    except Exception:
        return {}


# Registry snapshot loaded once at import time.
_REGISTRY: dict[str, dict] = _load_registry()


def _registry_intro(pid: str) -> tuple[str, Path] | None:
    """Derive (display_name, INTRO dir) from the registry for a given pid.

    Tries <path>\\INTRO first, then the project root itself as a fallback so
    the page at least has something to show even when INTRO hasn't been seeded.
    Returns None if pid is not in the registry.
    """
    entry = _REGISTRY.get(pid.lower())
    if not entry:
        return None
    name = entry.get("name", pid)
    proj_path = entry.get("path", "")
    if not proj_path:
        return None
    intro = Path(proj_path) / "INTRO"
    return (name, intro)

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


def _all_project_entries() -> list[tuple[str, str, Path]]:
    """Return (pid, display_name, intro_path) for every known project.

    Registry drives the full list. PROJECT_INTRO overrides name/path where
    it has an explicit entry. Projects only in PROJECT_INTRO (not in registry)
    are appended at the end so they are never silently dropped.
    """
    seen: set[str] = set()
    result: list[tuple[str, str, Path]] = []

    # Registry order first (canonical source for all 22 projects).
    for pid, reg_entry in _REGISTRY.items():
        seen.add(pid)
        if pid in PROJECT_INTRO:
            name, intro = PROJECT_INTRO[pid]
        else:
            name = reg_entry.get("name", pid)
            proj_path = reg_entry.get("path", "")
            intro = Path(proj_path) / "INTRO" if proj_path else Path("")
        result.append((pid, name, intro))

    # Append anything in the hardcoded dict that the registry doesn't know yet.
    for pid, (name, intro) in PROJECT_INTRO.items():
        if pid not in seen:
            result.append((pid, name, intro))

    return result


def list_projects() -> list[dict]:
    """List all known projects (registry + overrides) for the selector nav."""
    out = []
    for pid, name, intro in _all_project_entries():
        ready = False
        try:
            ready = intro.exists() and any(intro.iterdir())
        except Exception:
            pass
        out.append({
            "pid": pid,
            "name": name,
            "ready": ready,
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
    _descs = data.get("descriptions", [])
    # Tolerate a {name: text} mapping as well as the canonical list-of-dicts.
    # A malformed file previously raised AttributeError here, which 500s the
    # whole tab — strictly worse than rendering what can be understood.
    if isinstance(_descs, dict):
        _descs = [{"title": k, "body": v} for k, v in _descs.items()]
    for d in _descs:
        if isinstance(d, str):
            d = {"title": "", "body": d}
        elif not isinstance(d, dict):
            continue
        # Tolerate both key conventions: title/body (standard) and technology/text (Maia)
        dive_title = d.get("title") or d.get("technology") or ""
        dive_body = d.get("body") or d.get("text") or ""
        dives.append(
            f"<div class='card mb-2'><div class='card-body'>"
            f"<h6 class='mb-2'>{html.escape(dive_title)}</h6>"
            f"<div class='small'>{html.escape(dive_body)}</div>"
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


def _tab_code(intro: Path) -> str:
    """Code Explained tab — annotated source snippets mapped to features.

    Reads status_code.json: {"intro": "...", "sections": [
        {"category": "...", "snippets": [
            {"title","feature","file","language","code","explanation"} ]} ]}
    """
    data = _read_json(intro, "status_code.json")
    if data is None:
        return _empty(
            "status_code.json not found in " + str(intro) + " — add it to document "
            "which part of the code implements each feature (code → feature)."
        )
    if isinstance(data, dict) and "_error" in data:
        return _empty(data["_error"])

    sections = data.get("sections", [])
    total = sum(len(s.get("snippets", [])) for s in sections)
    intro_txt = html.escape(data.get("intro", "") or "")
    header = (
        f"<div class='alert alert-info py-2'><i class='bi bi-braces'></i> "
        f"<strong>Code &rarr; Feature.</strong> {total} annotated snippets across "
        f"{len(sections)} areas, drawn from the project's actual source — each shows "
        f"the code that creates a feature and explains what it does. {intro_txt}</div>"
    )

    blocks = []
    for sec in sections:
        snips = []
        for s in sec.get("snippets", []):
            lang = html.escape((s.get("language", "") or "").lower())
            feature = html.escape(s.get("feature", "") or "")
            feat_badge = (
                f"<span class='badge bg-success-subtle text-success border border-success-subtle'>"
                f"implements: {feature}</span>" if feature else ""
            )
            code = html.escape(s.get("code", "") or "")
            snips.append(
                f"<div class='mb-3 pb-3 border-bottom'>"
                f"<div class='d-flex justify-content-between align-items-start flex-wrap gap-2'>"
                f"<div><strong>{html.escape(s.get('title',''))}</strong> "
                f"<code class='small text-muted'>{html.escape(s.get('file',''))}</code></div>"
                f"<div>{feat_badge}</div></div>"
                f"<pre style='background:#0f172a;color:#e2e8f0;padding:12px;border-radius:6px;"
                f"overflow-x:auto;margin:.5rem 0 .35rem;font-size:12px;line-height:1.45'>"
                f"<code class='language-{lang}'>{code}</code></pre>"
                f"<div class='small'>{html.escape(s.get('explanation',''))}</div>"
                f"</div>"
            )
        blocks.append(
            f"<div class='card mb-3'><div class='card-header'><strong>"
            f"{html.escape(sec.get('category',''))}</strong></div>"
            f"<div class='card-body'>{''.join(snips)}</div></div>"
        )
    return header + "\n".join(blocks)


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

def render_project_status(pid: str, tab: str = "overview", embed: bool = False) -> tuple[str, str]:
    """Return (page_title, html_body) for /project/<pid>/status."""
    pid = pid.lower()
    entry = PROJECT_INTRO.get(pid)
    if not entry:
        # Fall back to registry-derived path/name.
        reg = _registry_intro(pid)
        if reg is None:
            return (
                pid,
                _empty(f"Unknown project '{pid}': not found in PROJECT_INTRO or "
                       f"qi_registry.json."),
            )
        name, intro = reg
    else:
        name, intro = entry

    if not intro.exists():
        # Render a minimal informational page from registry metadata instead of
        # an opaque error so new projects at least have a usable status page.
        reg_entry = _REGISTRY.get(pid, {})
        desc = html.escape(reg_entry.get("description", "No description available."))
        path_val = html.escape(reg_entry.get("path", str(intro.parent)))
        status_val = html.escape(str(reg_entry.get("status", "unknown")))
        minimal_body = (
            f"<div class='card mb-3'><div class='card-body'>"
            f"<h5 class='text-primary'>{html.escape(name)}</h5>"
            f"<p>{desc}</p>"
            f"<table class='table table-sm'><tbody>"
            f"<tr><th>Path</th><td><code>{path_val}</code></td></tr>"
            f"<tr><th>Status</th><td>{status_val}</td></tr>"
            f"</tbody></table>"
            f"</div></div>"
            + _empty(
                f"INTRO folder not found: {intro} — "
                f"seed it with status_*.json + status_intro.md "
                f"(copy the shape from C:\\QI\\INTRO\\) to unlock all tabs."
            )
        )
        return (f"{name} — Project Status", minimal_body)

    tabs = [
        ("overview",  "bi-clipboard-data", "Overview & Features"),
        ("blueprint", "bi-diagram-3",      "Overview & Blueprint"),
        ("business",  "bi-check2-square",  "Feature Status (Business)"),
        ("dev",       "bi-braces-asterisk","Feature Status (Dev)"),
        ("code",      "bi-file-earmark-code","Code Explained"),
        ("future",    "bi-fire",           "Future Enhancements"),
        ("techstack", "bi-cpu",            "Technology Stack"),
        ("docs",      "bi-journal-text",   "Docs & Demo Guide"),
    ]
    embed_qs = "&embed=1" if embed else ""
    embed_q = "?embed=1" if embed else ""
    nav = "".join(
        f"<li class='nav-item'>"
        f"<a class='nav-link {'active' if t==tab else ''}' "
        f"href='/project/{pid}/status?tab={t}{embed_qs}'>"
        f"<i class='bi {icon}'></i> {label}</a></li>"
        for t, icon, label in tabs
    )

    body_map = {
        "overview":  lambda: _tab_overview(intro),
        "blueprint": lambda: _tab_blueprint(intro, name),
        "business":  lambda: _tab_features_business(intro),
        "dev":       lambda: _tab_features_dev(intro),
        "code":      lambda: _tab_code(intro),
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
            f"<a href='/project/{p['pid']}/status{embed_q}' class='me-3{active}{ready}'>"
            f"{html.escape(p['name'])}</a>"
        )
    selector = (
        "<div class='card mb-3'><div class='card-body py-2 small'>"
        "<strong class='me-3'>Project:</strong>"
        f"{''.join(selector_links)}"
        "</div></div>"
    )

    back_btn = ("" if embed else
                f"<a href='/project/{pid}' class='btn btn-sm btn-outline-secondary'>"
                f"<i class='bi bi-arrow-left'></i> Back to project overview</a>")
    page = f"""
    <div class='d-flex justify-content-between align-items-center mb-3'>
      <div><h3 class='mb-0'>{html.escape(name)} — Project Status</h3>
        <small class='text-muted'>Source: <code>{html.escape(str(intro))}</code></small></div>
      {back_btn}
    </div>
    {selector}
    <ul class='nav nav-tabs mb-3'>{nav}</ul>
    {body}
    """
    return (f"{name} — Project Status", page)

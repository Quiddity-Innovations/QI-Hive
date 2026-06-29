# -*- coding: utf-8 -*-
"""
QI Hive — Project Status Library builder.

For each project: copy the raw INTRO source set (status_*.json/.md + *.svg) into
  project_library\<Name>\source\
and compile a polished Word document
  project_library\<Name>\<Name>_ProjectStatus_<DATE>.docx
mirroring the 7-tab dashboard Project Status page (Overview, Blueprint,
Feature Status Business, Feature Status Dev, Future Enhancements, Tech Stack, Docs).

Reusable for the remaining QI projects — add entries to PROJECTS and re-run.
"""
from __future__ import annotations
import json, os, re, shutil, sys, tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

DATE = "2026-06-29"
LIB = Path(r"C:\QIH\shared\documentation\project_library")

# pid -> (display_name, intro_dir). Builds only those whose INTRO has status_intro.md
# (skip-if-not-ready guard in __main__), so this can be re-run safely each wave.
PROJECTS = {
    # Batch 1
    "autopdf": ("AutoPDF", Path(r"C:\AutoPDF\INTRO")),
    "mapsnap": ("MapSnap", Path(r"C:\MapSnap\INTRO")),
    "nexus":   ("NEXUS",   Path(r"C:\NEXUS\INTRO")),
    "qi_hive": ("QI Hive", Path(r"C:\QIH\INTRO")),
    # Ecosystem
    "naya":         ("Naya",                 Path(r"C:\NAYA\INTRO")),
    "qi_brain":     ("QI Brain",             Path(r"C:\QIH\engine\brain\INTRO")),
    "easyflow":     ("EasyFlow",             Path(r"C:\EasyFlow\INTRO")),
    "openclaw":     ("OpenClaw",             Path(r"C:\OC\INTRO")),
    "tubescout":    ("TubeScout",            Path(r"C:\TUBESCOUT\INTRO")),
    "cognibase":    ("CogniBase",            Path(r"C:\CogniBase\INTRO")),
    "personalsong": ("PersonalSong Studio",  Path(r"C:\PersonalSong\INTRO")),
    "avatarstudio": ("AvatarStudio",         Path(r"C:\1-AI\APPS\AvatarStudio\INTRO")),
    "akiyascout":   ("AkiyaScout",           Path(r"C:\AkiyaScout\INTRO")),
    "lotterywiz":   ("LotteryWiz",           Path(r"C:\Lottery Wiz\INTRO")),
    "claude_voice": ("Claude Voice",         Path(r"C:\CLAUDE\Claude Voice\INTRO")),
    "claude_manager":("Claude Manager",      Path(r"C:\CLAUDE\INTRO")),
    "mq":           ("MQ",                   Path(r"C:\MQ\INTRO")),
    "m2v":          ("M2V",                  Path(r"C:\M2V\INTRO")),
    "gamez":        ("Gamez",                Path(r"C:\Gamez\INTRO")),
    "filehq":       ("FileHQ",               Path(r"C:\NAYA\filehq\INTRO")),
    "cypherminer":  ("CypherMiner",          Path(r"C:\CypherMiner\INTRO")),
    "digitization": ("Digitization Cost Tool", Path(r"C:\Users\renne\Downloads\DIGITIZATION COSTS\INTRO")),
}

STATUS_LABEL = {
    "live": "Live", "partial": "Partial", "planned": "Planned",
    "disabled": "Disabled", "pending": "Pending",
}
STATUS_RGB = {
    "live": RGBColor(0x1B, 0x7A, 0x33), "partial": RGBColor(0xB8, 0x7A, 0x00),
    "planned": RGBColor(0x0D, 0x6E, 0xA6), "disabled": RGBColor(0x66, 0x66, 0x66),
    "pending": RGBColor(0xB8, 0x7A, 0x00),
}

# ── inline markdown (**bold**, `code`) ─────────────────────────────────────────
def add_inline(par, text):
    for piece in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text):
        if not piece:
            continue
        if piece.startswith("**") and piece.endswith("**"):
            r = par.add_run(piece[2:-2]); r.bold = True
        elif piece.startswith("`") and piece.endswith("`"):
            r = par.add_run(piece[1:-1]); r.font.name = "Consolas"; r.font.size = Pt(9.5)
        else:
            par.add_run(piece)

# ── markdown table block -> docx table ─────────────────────────────────────────
def flush_md_table(doc, rows):
    if not rows:
        return
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    # drop separator rows (---)
    cells = [c for c in cells if not all(set(x) <= set("-: ") and x for x in c)]
    if not cells:
        return
    ncol = max(len(c) for c in cells)
    t = doc.add_table(rows=0, cols=ncol)
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    for i, row in enumerate(cells):
        tr = t.add_row().cells
        for j in range(ncol):
            val = row[j] if j < len(row) else ""
            p = tr[j].paragraphs[0]
            add_inline(p, val)
            if i == 0:
                for run in p.runs:
                    run.bold = True
    doc.add_paragraph()

# ── status_intro.md -> docx ────────────────────────────────────────────────────
def render_intro_md(doc, md_path: Path):
    text = md_path.read_text(encoding="utf-8")
    tbl_buf = []
    for line in text.splitlines():
        s = line.rstrip("\n")
        if s.lstrip().startswith("|"):
            tbl_buf.append(s); continue
        if tbl_buf:
            flush_md_table(doc, tbl_buf); tbl_buf = []
        if s.startswith("# "):
            doc.add_heading(s[2:].strip(), level=1)
        elif s.startswith("## "):
            doc.add_heading(s[3:].strip(), level=2)
        elif s.startswith("### "):
            doc.add_heading(s[4:].strip(), level=3)
        elif s.startswith("- "):
            p = doc.add_paragraph(style="List Bullet"); add_inline(p, s[2:])
        elif s.strip().startswith("*") and s.strip().endswith("*") and not s.strip().startswith("**"):
            p = doc.add_paragraph(); r = p.add_run(s.strip().strip("*")); r.italic = True
            r.font.size = Pt(8.5); r.font.color.rgb = RGBColor(0x80, 0x80, 0x80)
        elif s.strip():
            p = doc.add_paragraph(); add_inline(p, s)
    if tbl_buf:
        flush_md_table(doc, tbl_buf)

# ── status badge run ───────────────────────────────────────────────────────────
def status_run(cell, status):
    s = (status or "").lower()
    p = cell.paragraphs[0]
    r = p.add_run(STATUS_LABEL.get(s, status or ""))
    r.bold = True
    r.font.color.rgb = STATUS_RGB.get(s, RGBColor(0, 0, 0))

def header_row(t, labels):
    cells = t.add_row().cells
    for c, lab in zip(cells, labels):
        run = c.paragraphs[0].add_run(lab); run.bold = True

def shade_cell(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:fill"), fill_hex)
    tcPr.append(shd)

def add_code_block(doc, code, language=""):
    """Render a code excerpt as a shaded, monospaced single-cell table."""
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    cell = t.cell(0, 0)
    shade_cell(cell, "1E293B")  # slate-900 to match the dashboard code block
    cell.paragraphs[0].text = ""
    lines = (code or "").split("\n")
    for i, line in enumerate(lines):
        p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
        p.paragraph_format.space_after = Pt(0); p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        r = p.add_run(line if line else " ")
        r.font.name = "Consolas"; r.font.size = Pt(8.5)
        r.font.color.rgb = RGBColor(0xE2, 0xE8, 0xF0)  # slate-200
    return t

# ── SVG embed (svglib best-effort, else reference path) ────────────────────────
def embed_svg(doc, svg_path: Path, tmpdir: str):
    try:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPM
        drawing = svg2rlg(str(svg_path))
        png = os.path.join(tmpdir, svg_path.stem + ".png")
        renderPM.drawToFile(drawing, png, fmt="PNG")
        width = min(6.3, (drawing.width or 600) / 96.0)
        doc.add_picture(png, width=Inches(width))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap = doc.add_paragraph(); rr = cap.add_run(svg_path.name)
        rr.italic = True; rr.font.size = Pt(8.5); cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        return True
    except Exception as e:
        p = doc.add_paragraph()
        r = p.add_run(f"[Diagram: {svg_path.name} — view in the dashboard Blueprint tab or open ")
        r.font.size = Pt(9)
        r2 = p.add_run(str(svg_path)); r2.font.name = "Consolas"; r2.font.size = Pt(9)
        p.add_run("]").font.size = Pt(9)
        return False

# ── per-project build ──────────────────────────────────────────────────────────
def build(pid, name, intro: Path):
    out_dir = LIB / name
    src_dir = out_dir / "source"
    src_dir.mkdir(parents=True, exist_ok=True)

    # 1) copy raw source set
    copied = []
    for f in sorted(intro.glob("*.json")) + sorted(intro.glob("status_intro.md")) + sorted(intro.glob("*.svg")):
        shutil.copy2(f, src_dir / f.name); copied.append(f.name)

    # 2) load data
    def rj(n):
        p = intro / n
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    biz = rj("status_features_business.json") or []
    dev = rj("status_features_dev.json") or []
    code_data = rj("status_code.json") or {}
    fut = rj("status_future.json") or {}
    tech = rj("status_techstack.json") or {}
    docs = rj("status_documentation.json") or {}

    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10.5)

    # cover
    title = doc.add_heading(f"{name} — Project Status", level=0)
    sub = doc.add_paragraph()
    r = sub.add_run("QI Hive — Project Documentation Library")
    r.bold = True; r.font.size = Pt(12); r.font.color.rgb = RGBColor(0x0D, 0x6E, 0xA6)
    meta = doc.add_paragraph()
    meta.add_run(f"Generated: {DATE}    •    Source: ").font.size = Pt(9)
    meta.add_run(str(intro)).font.name = "Consolas"
    doc.add_paragraph(
        "This document mirrors the live Project Status page in the QI Hive dashboard "
        "(7 tabs). It is generated from the project's INTRO source set; the raw "
        "status_*.json / .md / .svg files are in the accompanying source\\ folder."
    ).italic = True
    doc.add_page_break()

    # 1. Overview & Features
    render_intro_md(doc, intro / "status_intro.md")
    doc.add_page_break()

    # 2. Blueprint
    doc.add_heading("Architecture & Blueprint", level=1)
    svgs = sorted(intro.glob("*.svg"))
    with tempfile.TemporaryDirectory() as tmp:
        if not svgs:
            doc.add_paragraph("No architecture diagrams available.")
        for svg in svgs:
            doc.add_heading(svg.stem.replace("_", " ").title(), level=2)
            embed_svg(doc, svg, tmp)
            doc.add_paragraph()
        doc.add_page_break()

        # 3. Feature Status (Business)
        doc.add_heading("Feature Status — Business", level=1)
        for cat in biz:
            doc.add_heading(cat.get("category", ""), level=2)
            t = doc.add_table(rows=0, cols=3); t.style = "Light Grid Accent 1"
            header_row(t, ["Capability", "What it does", "Status"])
            for f in cat.get("features", []):
                c = t.add_row().cells
                c[0].paragraphs[0].add_run(f.get("name", "")).bold = True
                desc = f.get("description", "")
                if f.get("notes"):
                    desc += f"\n({f['notes']})"
                c[1].text = desc
                status_run(c[2], f.get("status"))
            doc.add_paragraph()
        doc.add_page_break()

        # 4. Feature Status (Dev)
        doc.add_heading("Feature Status — Developer / Technical", level=1)
        for cat in dev:
            doc.add_heading(cat.get("category", ""), level=2)
            t = doc.add_table(rows=0, cols=4); t.style = "Light Grid Accent 1"
            header_row(t, ["Component", "File / Function", "Status", "Detail"])
            for f in cat.get("features", []):
                c = t.add_row().cells
                c[0].paragraphs[0].add_run(f.get("name", "")).bold = True
                fr = c[1].paragraphs[0].add_run(f.get("file", "")); fr.font.name = "Consolas"; fr.font.size = Pt(8.5)
                status_run(c[2], f.get("status"))
                c[3].text = f.get("detail", "")
            doc.add_paragraph()
        doc.add_page_break()

        # 5. Code Explained (code -> feature)
        doc.add_heading("Code Explained — Code → Feature", level=1)
        csecs = code_data.get("sections", [])
        intro_note = doc.add_paragraph(
            code_data.get("intro")
            or "Real source excerpts showing which part of the code creates each feature."
        )
        intro_note.runs[0].italic = True
        if not csecs:
            doc.add_paragraph("No annotated code snippets available for this project.")
        for sec in csecs:
            doc.add_heading(sec.get("category", ""), level=2)
            for sn in sec.get("snippets", []):
                p = doc.add_paragraph()
                p.add_run(sn.get("title", "")).bold = True
                if sn.get("feature"):
                    rr = p.add_run("   implements: " + sn["feature"])
                    rr.font.size = Pt(9); rr.font.color.rgb = RGBColor(0x1B, 0x7A, 0x33)
                if sn.get("file"):
                    fp = doc.add_paragraph()
                    fr = fp.add_run(sn["file"]); fr.font.name = "Consolas"
                    fr.font.size = Pt(8.5); fr.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
                add_code_block(doc, sn.get("code", ""), sn.get("language", ""))
                ep = doc.add_paragraph(); ep.add_run(sn.get("explanation", "")).font.size = Pt(9.5)
                doc.add_paragraph()
        doc.add_page_break()

        # 6. Future Enhancements
        doc.add_heading("Future Enhancements", level=1)
        for cat in fut.get("categories", []):
            h = doc.add_heading(level=2)
            h.add_run(cat.get("name", ""))
            pr = (cat.get("priority", "") or "").upper()
            if pr:
                rr = h.add_run(f"   [{pr} PRIORITY]"); rr.font.size = Pt(10)
                rr.font.color.rgb = {"HIGH": RGBColor(0xC0, 0x20, 0x20),
                                     "MEDIUM": RGBColor(0xB8, 0x7A, 0x00),
                                     "LOW": RGBColor(0x66, 0x66, 0x66)}.get(pr, RGBColor(0, 0, 0))
            for item in cat.get("items", []):
                p = doc.add_paragraph(style="List Bullet")
                p.add_run(item.get("title", "")).bold = True
                if item.get("detail"):
                    p.add_run(" — " + item["detail"])
        doc.add_page_break()

        # 6. Technology Stack
        doc.add_heading("Technology Stack", level=1)
        t = doc.add_table(rows=0, cols=5); t.style = "Light Grid Accent 1"
        header_row(t, ["Layer", "Technology", "Role", "License", "Version"])
        last = None
        for row in tech.get("table", []):
            c = t.add_row().cells
            layer = row.get("layer", "")
            c[0].paragraphs[0].add_run("" if layer == last else layer).bold = True
            last = layer
            c[1].paragraphs[0].add_run(row.get("technology", "")).bold = True
            c[2].text = row.get("role", "")
            c[3].text = row.get("license", "")
            c[4].text = row.get("version", "")
        doc.add_paragraph()
        descs = tech.get("descriptions", [])
        if descs:
            doc.add_heading("Technology Deep Dives", level=2)
            for d in descs:
                ttl = d.get("title") or d.get("technology") or ""
                body = d.get("body") or d.get("text") or ""
                doc.add_heading(ttl, level=3)
                doc.add_paragraph(body)
        doc.add_page_break()

        # 7. Documentation index
        doc.add_heading("Documentation & Source Index", level=1)
        for sec in docs.get("sections", []):
            doc.add_heading(sec.get("name", ""), level=2)
            for d in sec.get("documents", []):
                p = doc.add_paragraph(style="List Bullet")
                p.add_run(d.get("title", "")).bold = True
                typ = d.get("type", "")
                if typ:
                    rr = p.add_run(f"  [{typ}]"); rr.font.size = Pt(8.5); rr.font.color.rgb = RGBColor(0x66,0x66,0x66)
                loc = (d.get("location", "") or "") + (d.get("file", "") or "")
                if loc:
                    p2 = doc.add_paragraph(); p2.paragraph_format.left_indent = Inches(0.5)
                    rr = p2.add_run(loc); rr.font.name = "Consolas"; rr.font.size = Pt(8.5)
                if d.get("description"):
                    p3 = doc.add_paragraph(); p3.paragraph_format.left_indent = Inches(0.5)
                    p3.add_run(d["description"]).font.size = Pt(9)

        out_path = out_dir / f"{name.replace(' ', '_')}_ProjectStatus_{DATE}.docx"
        doc.save(str(out_path))
    return out_path, copied, {
        "biz_cats": len(biz), "biz_feats": sum(len(c.get("features", [])) for c in biz),
        "dev_cats": len(dev), "dev_feats": sum(len(c.get("features", [])) for c in dev),
        "tech_rows": len(tech.get("table", [])), "svgs": len(svgs),
        "doc_count": sum(len(s.get("documents", [])) for s in docs.get("sections", [])),
    }


if __name__ == "__main__":
    LIB.mkdir(parents=True, exist_ok=True)
    for pid, (name, intro) in PROJECTS.items():
        if not (intro / "status_intro.md").exists():
            print(f"SKIP {name}: not ready ({intro}\\status_intro.md missing)")
            continue
        try:
            out, copied, stats = build(pid, name, intro)
            print(f"OK  {name}: {out}")
            print(f"    source files copied: {len(copied)}  | {stats}")
        except Exception as e:
            import traceback
            print(f"FAIL {name}: {e}")
            traceback.print_exc()

# -*- coding: utf-8 -*-
"""
brain_backfill_sessions.py — one-shot backfill of historical session summaries
into QI Brain.

Scans C:\\UNIVERSAL\\DOCUMENTATION\\Session_Summaries\\*.docx, parses each,
maps its filename prefix to a brain project_id, and POSTs to /api/log_session.
Deduplicates against sessions already in the brain.

Safe to re-run: skips anything whose (project_id, session_title, date) is
already logged.
"""
from __future__ import annotations
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import requests
from docx import Document

SUMMARY_DIR = Path(r"C:\UNIVERSAL\DOCUMENTATION\Session_Summaries")
BRAIN_DB    = Path(r"C:\QIH\data\qi_brain.db")
BRAIN_URL   = "http://localhost:9010"

# Filename prefix → brain project_id
PREFIX_MAP = {
    "AutoPDF":           "universal",
    "Claude":            "universal",
    "Dashboard":         "universal",
    "EasyFlow":          "easyflow",
    "GMAIL":             "universal",
    "Maia":              "maia",
    "Naya":              "naya",
    "NEXUS":             "nexus",
    "OpenClaw":          "openclaw",
    "QI-Dashboard":      "universal",
    "QI-Ecosystem":      "universal",
    "QIBrain":           "qi_brain",
    "QIDashboard":       "universal",
    "QIHive":            "universal",  # no qi_hive project yet; bucket into universal
    "QIOrchestrator":    "universal",
    "QI_DocInfra":       "universal",
    "QI_Ecosystem":      "universal",
    "QI_FullSweep":      "universal",
    "QI_NextSession":    "qi_brain",
    "QI_ServiceRename":  "universal",
    "QI_SessionIntel":   "universal",
    "QI_Universal":      "universal",
}

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})(?:_(\d{4}))?")


def parse_filename(name: str) -> tuple[str | None, str, str]:
    """Return (project_id, session_title, started_at_iso)."""
    stem = name[:-5] if name.lower().endswith(".docx") else name

    m = DATE_RE.search(stem)
    if m:
        date_str = m.group(1)
        time_str = m.group(2) or "0000"
        started = f"{date_str}T{time_str[:2]}:{time_str[2:]}:00"
    else:
        started = None

    # Derive prefix: longest key that the stem starts with
    project = None
    for key in sorted(PREFIX_MAP.keys(), key=len, reverse=True):
        if stem.startswith(key + "_") or stem.startswith(key + "-"):
            project = PREFIX_MAP[key]
            break

    # Build a title from the stem (drop _Summary_date_time)
    title = re.sub(r"_Summary(_\d{4}-\d{2}-\d{2}(_\d{4}|_[A-Za-z]+)?)?$", "", stem)
    title = re.sub(r"_\d{4}-\d{2}-\d{2}(_\d{4}|_[A-Za-z]+)?$", "", title)
    title = title.replace("_", " ")

    return project, title, started


def extract_summary(path: Path, max_chars: int = 1500) -> str:
    try:
        doc = Document(str(path))
        paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        text = "\n".join(paras)
        return text[:max_chars]
    except Exception as e:
        return f"(could not parse docx: {e})"


def existing_session_keys() -> set[tuple[str, str]]:
    conn = sqlite3.connect(str(BRAIN_DB))
    try:
        rows = conn.execute("SELECT project_id, session_title FROM session_log").fetchall()
    finally:
        conn.close()
    return {(r[0], (r[1] or "").lower().strip()) for r in rows}


def main() -> int:
    if not SUMMARY_DIR.exists():
        print(f"Summary dir missing: {SUMMARY_DIR}")
        return 2

    existing = existing_session_keys()
    print(f"Brain currently has {len(existing)} sessions.")

    logged = 0
    skipped = 0
    skipped_noproj = 0
    errors = 0

    for path in sorted(SUMMARY_DIR.glob("*.docx")):
        if path.name.startswith("~$"):
            continue  # Word lock files

        project, title, started = parse_filename(path.name)
        if not project:
            print(f"  SKIP (no project mapping): {path.name}")
            skipped_noproj += 1
            continue

        key = (project, title.lower().strip())
        if key in existing:
            skipped += 1
            continue

        summary = extract_summary(path)

        payload = {
            "project_id":    project,
            "session_title": title,
            "summary":       summary,
            "agent_id":      "claude",
            "model_used":    "claude-opus-or-sonnet",
            "started_at":    started,
        }

        try:
            r = requests.post(f"{BRAIN_URL}/api/log_session", json=payload, timeout=30)
            if r.status_code == 200:
                logged += 1
                existing.add(key)
                print(f"  + [{project}] {title} ({started or 'no-date'})")
            else:
                errors += 1
                print(f"  ERR {r.status_code}: {path.name}: {r.text[:200]}")
        except Exception as e:
            errors += 1
            print(f"  EXC: {path.name}: {e}")

    print(f"\nResult: logged={logged}  skipped_dup={skipped}  skipped_noproj={skipped_noproj}  errors={errors}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

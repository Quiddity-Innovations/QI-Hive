# -*- coding: utf-8 -*-
"""
Backfill decisions + features into QI Brain from session summary .docx files.

Strategy:
  1. Read each .docx in Session_Summaries/ with python-docx
  2. Send text to local ollama qwen2.5:7b for structured extraction
  3. POST each extracted item to Brain /api/log_decision or /api/log_feature

Designed for one-time backfill; safe to re-run (Brain dedupes by title).

Usage:
    python C:\\QIH\\tools\\backfill_decisions.py [--dry-run] [--project <pid>]
"""
from __future__ import annotations
import argparse, json, re, sys, time, urllib.request, urllib.error
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from docx import Document as DocxDocument
except ImportError:
    print("pip install python-docx")
    sys.exit(1)

SUMMARIES_DIR = Path(r"C:\UNIVERSAL\DOCUMENTATION\Session_Summaries")
BRAIN_URL = "http://127.0.0.1:9011"
OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "qwen2.5:7b"

# Map filename prefix → project_id
PROJECT_MAP = {
    "Maia": "maia", "MAIA": "maia",
    "Naya": "naya", "NAYA": "naya",
    "NEXUS": "nexus", "Nexus": "nexus",
    "EasyFlow": "easyflow", "EASYFLOW": "easyflow",
    "QIHive": "qi_hive", "QI_Hive": "qi_hive",
    "QIDashboard": "qi_hive", "Dashboard": "qi_hive",
    "QI_": "universal", "QI": "universal",
    "Claude": "universal", "AutoPDF": "universal",
}

DECISION_PROMPT_TPL = (
    "You are a structured-data extractor for an AI project management system.\n\n"
    "Read the session summary below and extract a list of ARCHITECTURAL DECISIONS made.\n\n"
    "Rules:\n"
    "- Only extract real decisions (choices made, not observations or tasks)\n"
    "- Each decision needs: title (short imperative), rationale (why chosen), project_id\n"
    "- project_id must be one of: maia, naya, nexus, easyflow, qi_hive, universal\n"
    "- Use 'universal' for cross-project or infrastructure decisions\n"
    "- Limit to the 8 most important decisions\n"
    '- Output ONLY valid JSON (no markdown): {"decisions": [{"title": "...", "rationale": "...", "project_id": "...", "tags": ["tag1"]}]}\n\n'
    "Session summary:\n{text}"
)

FEATURE_PROMPT_TPL = (
    "You are a structured-data extractor for an AI project management system.\n\n"
    "Read the session summary below and extract a list of FEATURES that were implemented or completed.\n\n"
    "Rules:\n"
    "- Only extract features that were fully built or merged (not planned/future)\n"
    "- Each feature needs: name, description (1 sentence), project_id, domain (api/ui/infra/auth/general)\n"
    "- project_id must be one of: maia, naya, nexus, easyflow, qi_hive, universal\n"
    '- Output ONLY valid JSON (no markdown): {"features": [{"name": "...", "description": "...", "project_id": "...", "domain": "..."}]}\n\n'
    "Session summary:\n{text}"
)


def read_docx(path: Path) -> str:
    try:
        doc = DocxDocument(str(path))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        return ""


def ollama_extract(prompt: str, timeout: int = 45) -> dict:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 800},
    }
    try:
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.loads(r.read().decode("utf-8", errors="replace"))
        raw = resp.get("response", "")
        # extract JSON block
        m = re.search(r'(\{.*\})', raw, re.DOTALL)
        if not m:
            return {}
        candidate = m.group(1)
        # try direct parse
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
        # repair: strip invalid backslash escapes
        repaired = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', candidate)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass
        # last resort: extract individual items line by line
        return {}
    except Exception as e:
        print(f"  [ollama error] {e}")
    return {}


def brain_post(endpoint: str, body: dict) -> bool:
    try:
        req = urllib.request.Request(
            f"{BRAIN_URL}{endpoint}",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return 200 <= r.status < 300
    except Exception as e:
        print(f"  [brain error] {e}")
        return False


def guess_project(filename: str) -> str:
    for prefix, pid in PROJECT_MAP.items():
        if filename.startswith(prefix):
            return pid
    return "universal"


def already_logged(title: str) -> bool:
    try:
        req = urllib.request.Request(
            f"{BRAIN_URL}/api/context",
            data=json.dumps({"project_id": "universal"}).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=3) as r:
            ctx = json.loads(r.read().decode("utf-8", errors="replace"))
        existing = [d.get("title", "") for d in (ctx.get("recent_decisions") or [])]
        return title in existing
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Extract but don't post")
    ap.add_argument("--project", default=None, help="Limit to project_id")
    ap.add_argument("--limit", type=int, default=0, help="Max files to process")
    args = ap.parse_args()

    files = sorted(SUMMARIES_DIR.glob("*.docx"))
    if args.limit:
        files = files[:args.limit]

    total_decisions = 0
    total_features = 0

    for i, f in enumerate(files):
        print(f"\n[{i+1}/{len(files)}] {f.name}")
        text = read_docx(f)
        if len(text) < 200:
            print("  skip — too short")
            continue

        text_trunc = text[:4000]
        pid_guess = guess_project(f.name)

        # --- decisions ---
        print(f"  extracting decisions (qwen2.5:7b)...", end="", flush=True)
        dec_data = ollama_extract(DECISION_PROMPT_TPL.replace("{text}", text_trunc))
        decisions = dec_data.get("decisions") or []
        print(f" {len(decisions)} found")
        for d in decisions:
            if args.project and d.get("project_id") != args.project:
                continue
            title = (d.get("title") or "").strip()
            rationale = (d.get("rationale") or "").strip()
            if not title or len(title) < 5:
                continue
            if args.dry_run:
                print(f"  [DRY] decision: {title}")
            else:
                ok = brain_post("/api/log_decision", {
                    "project_id": d.get("project_id") or pid_guess,
                    "title": title[:200],
                    "rationale": rationale[:800],
                    "impact_scope": "project",
                    "tags": d.get("tags") or ["backfill"],
                })
                print(f"  {'OK' if ok else 'ERR'} decision: {title[:80]}")
                if ok:
                    total_decisions += 1
                time.sleep(0.05)

        # --- features ---
        print(f"  extracting features (qwen2.5:7b)...", end="", flush=True)
        feat_data = ollama_extract(FEATURE_PROMPT_TPL.replace("{text}", text_trunc))
        features = feat_data.get("features") or []
        print(f" {len(features)} found")
        for feat in features:
            if args.project and feat.get("project_id") != args.project:
                continue
            name = (feat.get("name") or "").strip()
            desc = (feat.get("description") or "").strip()
            if not name or len(name) < 4:
                continue
            if args.dry_run:
                print(f"  [DRY] feature: {name}")
            else:
                ok = brain_post("/api/log_feature", {
                    "source_project": feat.get("project_id") or pid_guess,
                    "name": name[:200],
                    "description": desc[:600],
                    "domain": feat.get("domain") or "general",
                })
                print(f"  {'OK' if ok else 'ERR'} feature: {name[:80]}")
                if ok:
                    total_features += 1
                time.sleep(0.05)

    print(f"\n{'='*60}")
    print(f"DONE — {total_decisions} decisions + {total_features} features posted to Brain")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
One-shot repair: normalise non-canonical project_id values in qi_brain.db.

Background (2026-08-17 audit)
----------------------------
Project ids were written inconsistently by different producers, so the same
project accumulated history under several spellings:

    agent_heartbeats : 5231 rows under 'qihive'   (canonical: 'qi_hive')
    session_log      : 'QI_Hive', 'qihive', 'NEXUS', 'OpenClaw', 'OC',
                       'Maia', 'ClaudeVoice'

This is why the compliance Inspector kept filing "no session activity" and
"brain drift" dispatches against projects that were in fact active — the
activity was logged under a spelling the freshness query never looked at.

Only ids that map unambiguously onto a registry id are rewritten. 'unknown'
and retired ids (fidelityanalyzer) are deliberately left alone, and the e2e
test fixtures are handled separately by the dispatch cleanup.

Takes a real online backup first. Safe to re-run: idempotent.
"""
from __future__ import annotations
import json, re, sqlite3, sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\QIH")
DB = ROOT / "data" / "qi_brain.db"
REGISTRY = ROOT / "ecosystem" / "qi_registry.json"

# Explicit mappings for ids that normalisation alone cannot resolve.
MANUAL = {
    "OC": "openclaw",       # C:\APPS\OC
}

# Never touch these — genuinely unattributable, or retired projects whose
# history should stay under its own name.
LEAVE_ALONE = {"unknown", "fidelityanalyzer", "qi_e2e_test", "qi_e2e_sanity"}


def norm(v) -> str:
    return re.sub(r"[^a-z0-9]", "", str(v or "").lower())


def backup(db: Path) -> Path:
    dest = db.with_name(f"{db.name}.bak-idfix-{datetime.now():%Y%m%d-%H%M%S}")
    src = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    dst = sqlite3.connect(dest)
    with dst:
        src.backup(dst)      # online backup API — consistent even with WAL active
    src.close(); dst.close()
    return dest


def main(apply: bool) -> int:
    reg_ids = {p["id"] for p in json.loads(REGISTRY.read_text(encoding="utf-8"))["projects"]}
    by_norm = {norm(i): i for i in reg_ids}

    con = sqlite3.connect(DB)
    tables = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]

    plan = []   # (table, column, old, new, count)
    for t in tables:
        cols = [r[1] for r in con.execute(f'PRAGMA table_info("{t}")')]
        col = "project_id" if "project_id" in cols else ("project" if "project" in cols else None)
        if not col:
            continue
        for val, n in con.execute(f'select "{col}", count(*) from "{t}" group by "{col}"'):
            if val is None or val in reg_ids or val in LEAVE_ALONE:
                continue
            target = MANUAL.get(val) or by_norm.get(norm(val))
            if target:
                plan.append((t, col, val, target, n))

    if not plan:
        print("nothing to normalise — all project ids are canonical")
        return 0

    total = sum(p[4] for p in plan)
    print(f"{len(plan)} rewrite(s), {total} rows:")
    for t, col, old, new, n in sorted(plan, key=lambda x: -x[4]):
        print(f"  {t:20} {col:11} {old:14} -> {new:14} ({n} rows)")

    if not apply:
        print("\nDRY RUN — pass --apply to write.")
        return 0

    dest = backup(DB)
    print(f"\nbackup -> {dest}")

    with con:
        for t, col, old, new, n in plan:
            con.execute(f'update "{t}" set "{col}" = ? where "{col}" = ?', (new, old))
    print(f"rewrote {total} rows across {len({p[0] for p in plan})} table(s)")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main("--apply" in sys.argv))

# -*- coding: utf-8 -*-
"""
One-shot repair: collapse the display-name project namespace in data/status.json
into the canonical registry-id namespace.

Background (2026-08-17 audit)
----------------------------
status.json accumulated two parallel key namespaces:
  * canonical registry ids  ("maia")   — written by nightly_reconcile / hive_ingest
  * display names           ("Maia")   — written by C:\\APPS\\CLAUDE\\supervisor\\supervisor.py

The supervisor is not scheduled anywhere and last ran 2026-07-28, so its 27 rows
sat frozen while the canonical rows stayed live. The dashboard papered over this
with merge_status_projects() at render time, and project_readiness.json (keyed
canonically) could never match the display-name rows.

supervisor.py has been fixed to key by registry id. This script cleans up the
residue it left behind: the supervisor-owned health fields are merged onto the
matching canonical row, then the ghost row is dropped.

Identity is resolved on normalised `path` first (strongest signal — both rows
point at the same directory), falling back to a normalised id, mirroring the
logic the dashboard already uses.

Safe to re-run: it is idempotent. Backup is written next to the file.
"""
from __future__ import annotations
import json, re, shutil, sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\QIH")
STATUS = ROOT / "data" / "status.json"
REGISTRY = ROOT / "ecosystem" / "qi_registry.json"

# Fields the supervisor owns — these get carried onto the canonical row.
SUPERVISOR_FIELDS = ("severity", "supervisor_findings", "git")


def norm_path(v) -> str:
    return re.sub(r"[\\/]+$", "", str(v or "")).replace("/", "\\").upper()


def norm_id(v) -> str:
    return re.sub(r"[^a-z0-9]", "", str(v or "").lower())


def main(apply: bool) -> int:
    status = json.loads(STATUS.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    projects = status.get("projects", {})

    reg_ids = {p["id"] for p in registry.get("projects", [])}
    # canonical path -> id, so a ghost row carrying only a path can be resolved
    reg_by_path = {
        norm_path(p["path"]): p["id"]
        for p in registry.get("projects", [])
        if p.get("id") and p.get("path")
    }

    canonical = {k: v for k, v in projects.items() if k in reg_ids}
    ghosts = {k: v for k, v in projects.items() if k not in reg_ids}

    # Index canonical rows by path and by normalised id for matching.
    canon_by_path, canon_by_nid = {}, {}
    for k, v in canonical.items():
        if v.get("path"):
            canon_by_path[norm_path(v["path"])] = k
        canon_by_nid[norm_id(k)] = k

    # Registry ids indexed by normalised form, so a ghost row can be promoted
    # to its canonical id even when no canonical row exists yet.
    reg_by_nid = {norm_id(i): i for i in reg_ids}

    merged, promoted, orphaned = [], [], []
    for gkey, gval in ghosts.items():
        target = None
        gpath = norm_path(gval.get("path"))
        if gpath:
            target = canon_by_path.get(gpath) or reg_by_path.get(gpath)
        if not target:
            target = canon_by_nid.get(norm_id(gkey))

        if target and target in canonical:
            row = canonical[target]
            for f in SUPERVISOR_FIELDS:
                # Only carry the field over if the canonical row lacks it —
                # never let a 20-day-old supervisor value overwrite live data.
                if f in gval and f not in row:
                    row[f] = gval[f]
            merged.append(f"{gkey} -> {target}")
            continue

        # No canonical row exists, but the project IS registered — promote the
        # ghost row to its canonical id rather than discarding it.
        pid = target or reg_by_nid.get(norm_id(gkey))
        if pid:
            canonical[pid] = dict(gval)
            canon_by_nid[norm_id(pid)] = pid
            promoted.append(f"{gkey} -> {pid}")
        else:
            orphaned.append(gkey)

    print(f"canonical rows : {len(canonical)}")
    print(f"ghost rows     : {len(ghosts)}")
    print(f"  merged       : {len(merged)}")
    print(f"  promoted     : {len(promoted)}  {promoted}")
    print(f"  orphaned     : {len(orphaned)}  {orphaned}")
    for m in sorted(merged):
        print(f"    {m}")

    if not apply:
        print("\nDRY RUN — pass --apply to write.")
        return 0

    # Orphans have no canonical counterpart (retired projects such as
    # 'fidelityanalyzer'). Park them rather than delete, so nothing is lost.
    status["projects"] = canonical
    if orphaned:
        status["_retired_projects"] = {k: ghosts[k] for k in orphaned}

    bak = STATUS.with_suffix(f".json.bak-idfix-{datetime.now():%Y%m%d-%H%M%S}")
    shutil.copy2(STATUS, bak)
    STATUS.write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(f"\nbackup  -> {bak}")
    print(f"written -> {STATUS}  ({len(canonical)} projects)")
    return 0


if __name__ == "__main__":
    sys.exit(main("--apply" in sys.argv))

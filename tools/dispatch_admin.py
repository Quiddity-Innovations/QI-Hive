#!/usr/bin/env python
"""
dispatch_admin.py — Claude/Renne admin tool for the CoWork Dispatch queue.

Lets Claude approve / decline / resolve dispatches on Renne's behalf, and clean up
inspector compliance noise. Talks to the Brain API (http://127.0.0.1:9011) so the full
apply pipeline runs on approval; falls back to direct DB writes for bulk cleanup.

Usage:
    python dispatch_admin.py list                      # genuine CoWork/Renne/Claude pending items
    python dispatch_admin.py list --all                # include inspector compliance findings
    python dispatch_admin.py approve <dispatch_id>     # approve (queues Claude Code execution)
    python dispatch_admin.py decline <dispatch_id> "reason"
    python dispatch_admin.py resolve <dispatch_id> "note"
    python dispatch_admin.py clean-inspector           # resolve ALL stale inspector pending dispatches
    python dispatch_admin.py clean-inspector --dry-run

Created 2026-06-17 to end the inspector-flood problem and give Claude approval authority.
"""
from __future__ import annotations
import sys, json, urllib.request, urllib.error, sqlite3, os
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

API = "http://127.0.0.1:9011"
DB  = os.environ.get("QI_BRAIN_DB", r"C:\QIH\data\qi_brain.db")
ACTOR = "claude"   # Claude approving on Renne's behalf


# ── HTTP helpers ────────────────────────────────────────────────────────────────
def _get(path: str) -> dict:
    with urllib.request.urlopen(API + path, timeout=8) as r:
        return json.loads(r.read().decode("utf-8"))


def _send(method: str, path: str, body: dict) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(API + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def _is_human(d: dict) -> bool:
    return not (d.get("source") == "hive_inspector" or d.get("type") == "compliance")


# ── Commands ────────────────────────────────────────────────────────────────────
def cmd_list(show_all: bool) -> None:
    rows = _get("/api/dispatches?status=pending&limit=500").get("dispatches", [])
    human = [d for d in rows if _is_human(d)]
    insp  = [d for d in rows if not _is_human(d)]
    print(f"\nPending — genuine CoWork/Renne/Claude items: {len(human)}")
    for d in human:
        try:
            p = json.loads(d["payload"]) if isinstance(d["payload"], str) else d["payload"]
        except Exception:
            p = d["payload"]
        title = (p or {}).get("title") if isinstance(p, dict) else None
        print(f"  • {d['dispatch_id']}  [{d['source']}/{d['type']}]  {title or ''}")
    print(f"\nInspector compliance findings (separate channel): {len(insp)}")
    if show_all:
        for d in insp:
            print(f"  · {d['dispatch_id']}  {d.get('project_id')}  {d['payload'][:80]}")
    else:
        print("  (use --all to list them; manage on the /compliance board)")
    print()


def cmd_review(dispatch_id: str, status: str, note: str | None) -> None:
    body = {"status": status, "reviewed_by": ACTOR}
    if note:
        body["note"] = note
    res = _send("PATCH", f"/api/dispatch/{dispatch_id}", body)
    print(json.dumps(res, indent=2))
    if status == "approved":
        print(f"\n✅ Approved {dispatch_id} — queued for Claude Code execution (apply pipeline).")


def cmd_clean_inspector(dry_run: bool) -> None:
    """Bulk-resolve stale inspector pending dispatches directly in the DB.
    Marked 'resolved' (NOT 'approved') so no apply-pipeline runs are created."""
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    n = con.execute(
        "SELECT COUNT(*) FROM dispatches WHERE source='hive_inspector' AND status='pending'"
    ).fetchone()[0]
    print(f"Stale inspector pending dispatches: {n}")
    if dry_run:
        print("[dry-run] no changes made.")
        con.close()
        return
    if n == 0:
        con.close()
        return
    now = datetime.now().isoformat()
    note = json.dumps([{"by": ACTOR, "at": now,
                        "note": "bulk-resolved: stale inspector duplicate; superseded by "
                                "idempotent file_dispatch() dedup (2026-06-17)"}])
    con.execute(
        "UPDATE dispatches SET status='resolved', reviewed_by=?, reviewed_at=?, notes=? "
        "WHERE source='hive_inspector' AND status='pending'",
        (ACTOR, now, note)
    )
    con.commit()
    remaining = con.execute(
        "SELECT COUNT(*) FROM dispatches WHERE source='hive_inspector' AND status='pending'"
    ).fetchone()[0]
    con.close()
    print(f"✅ Resolved {n} inspector dispatches. Remaining inspector pending: {remaining}")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    try:
        if cmd == "list":
            cmd_list("--all" in sys.argv)
        elif cmd == "approve":
            cmd_review(sys.argv[2], "approved", None)
        elif cmd == "decline":
            cmd_review(sys.argv[2], "declined", sys.argv[3] if len(sys.argv) > 3 else "declined by Claude")
        elif cmd == "resolve":
            cmd_review(sys.argv[2], "resolved", sys.argv[3] if len(sys.argv) > 3 else None)
        elif cmd == "clean-inspector":
            cmd_clean_inspector("--dry-run" in sys.argv)
        else:
            print(f"Unknown command: {cmd}")
            print(__doc__)
            return 1
    except urllib.error.HTTPError as e:
        print(f"API error {e.code}: {e.read().decode('utf-8', 'replace')}")
        return 2
    except Exception as e:
        print(f"Error: {e!r}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

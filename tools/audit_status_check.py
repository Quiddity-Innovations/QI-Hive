# -*- coding: utf-8 -*-
"""
Assess every item raised by the 2026-08-17 audit against live state.

Read-only. Prints DONE / LAGGING / N/A per item so it is obvious what still
needs work. Re-runnable — this is the audit's own regression check.
"""
from __future__ import annotations
import json, re, sqlite3, subprocess, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\QIH")
DB = ROOT / "data" / "qi_brain.db"

results: list[tuple[str, str, str]] = []


def check(name: str, ok: bool, detail: str, na: bool = False):
    results.append((name, "N/A" if na else ("DONE" if ok else "LAGGING"), detail))


def q(sql, params=()):
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    try:
        return c.execute(sql, params).fetchall()
    finally:
        c.close()


def ps(cmd: str) -> str:
    return subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                          capture_output=True, text=True, timeout=120).stdout


# ── 1. nightly git sync covers the Hive ──────────────────────────────────────
src = (ROOT / "tools" / "nightly_git_sync.py").read_text(encoding="utf-8")
check("git sync includes C:\\QIH", r"C:\QIH" in src.split("EXTERNALLY_SYNCED")[0],
      "REPOS list")
check("git sync has coverage_check", "def coverage_check" in src, "drift guard present")
check("git sync publishes qi-apply branches", "def publish_qi_apply_branches" in src,
      "Option B publisher")

# ── 2. project-ID namespace ──────────────────────────────────────────────────
status = json.loads((ROOT / "data" / "status.json").read_text(encoding="utf-8"))
reg = json.loads((ROOT / "ecosystem" / "qi_registry.json").read_text(encoding="utf-8"))
ids = {p["id"] for p in reg["projects"]}
ghosts = [k for k in status.get("projects", {}) if k not in ids]
check("status.json namespace clean", not ghosts,
      f"{len(status.get('projects', {}))} projects, {len(ghosts)} non-registry: {ghosts[:4]}")

bad = []
for tbl, col in (("session_log", "project_id"), ("agent_heartbeats", "project_id")):
    for r in q(f'SELECT DISTINCT "{col}" AS v FROM "{tbl}"'):
        if r["v"] and r["v"] not in ids and r["v"] != "unknown":
            bad.append(f"{tbl}:{r['v']}")
check("Brain project ids canonical", not bad, f"non-canonical: {bad or 'none (excl. unknown)'}")

# ── 3. auto-apply pipeline ───────────────────────────────────────────────────
runs = q("SELECT state, COUNT(*) n FROM dispatch_runs GROUP BY state")
smap = {r["state"]: r["n"] for r in runs}
ever = q("SELECT COUNT(*) n FROM dispatch_runs WHERE state IN ('applied','applied_local')")[0]["n"]
check("auto-apply has ever applied", ever > 0, f"states={smap}")
disp_src = (ROOT / "engine/hive/apply/dispatcher.py").read_text(encoding="utf-8")
check("stale-lock timeout present", "_STALE_RUN_MINUTES" in disp_src, "mutex expires")
run_src = (ROOT / "engine/hive/apply/runner.py").read_text(encoding="utf-8")
check("git calls non-interactive", "GIT_TERMINAL_PROMPT" in run_src, "no credential hang")
check("resolve race guarded", "state='resolving'" in run_src, "compare-and-swap claim")
check("safe.directory wildcard dropped",
      not re.search(r'^_GIT\s*=.*safe\.directory=\*', run_src, re.M),
      "explicit --system entry instead (comment may still mention the old form)")

# ── 4. dispatch queue ────────────────────────────────────────────────────────
open_d = q("SELECT project_id, payload FROM dispatches WHERE status IN ('pending','approved')")
by_check: dict[str, int] = {}
for r in open_d:
    try:
        cid = (json.loads(r["payload"]) or {}).get("check_id", "?")
    except Exception:
        cid = "?"
    by_check[cid] = by_check.get(cid, 0) + 1
check("dispatch queue drained", len(open_d) < 10,
      f"{len(open_d)} open: {dict(sorted(by_check.items(), key=lambda x: -x[1]))}")

# ── 5. dashboard endpoints ───────────────────────────────────────────────────
import urllib.request
def http(path, timeout=20):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:8600{path}", timeout=timeout) as r:
            return r.status, r.read(400).decode("utf-8", "replace")
    except Exception as e:
        return 0, str(e)

s, body = http("/api/agents")
check("/api/agents serves roster", s == 200 and '"agents"' in body and body.strip() != "{}",
      f"HTTP {s}")
s, body = http("/api/health")
check("/api/health responds fast", s == 200, f"HTTP {s}")

# ── 6. services & tunnels ────────────────────────────────────────────────────
svc = ps("Get-Service QI_* | Select-Object Name,Status | ConvertTo-Json -Compress")
try:
    svcs = {d["Name"]: d["Status"] for d in json.loads(svc)}
except Exception:
    svcs = {}
# Status 4 == Running in the serialized form
def running(n):
    v = svcs.get(n)
    return v in (4, "Running")
check("QI_AutoPDF running", running("QI_AutoPDF"), "public URL origin alive")
check("QI_M2VTunnel stopped", not running("QI_M2VTunnel"), "was publishing a dead origin")
for n in ("QI_HiveApply", "QI_HiveIngest", "QI_HiveInspectorDrain", "QI_Elevate",
          "QI_BrainAPI", "QI_Dashboard"):
    check(f"{n} running", running(n), "")

# ── 7. scheduled tasks ───────────────────────────────────────────────────────
raw = ps("Get-ScheduledTask | Where-Object {$_.TaskName -like 'QI_*' -or $_.TaskName -like 'Maia*'} | "
         "ForEach-Object { $i=$_|Get-ScheduledTaskInfo; "
         "'{0}|{1}|{2}|{3}' -f $_.TaskName,$_.State,$i.LastTaskResult,$i.NextRunTime }")
tasks = [l.split("|") for l in raw.strip().splitlines() if "|" in l]
broken = [t[0] for t in tasks if t[2].strip() not in ("0", "267009", "267011")]
orphan = [t[0] for t in tasks if not t[3].strip() and t[1].strip() != "Disabled"]
check("no broken scheduled tasks", not broken, f"nonzero LastTaskResult: {broken}")
check("no orphaned one-shot tasks", not orphan, f"no NextRunTime: {orphan}")

reg_doc = (ROOT / "ecosystem" / "QI_Scheduled_Tasks_Registry.md").read_text(encoding="utf-8", errors="replace")
undocumented = [t[0] for t in tasks if t[0] not in reg_doc]
check("scheduled tasks documented", not undocumented,
      f"{len(tasks)} tasks, {len(undocumented)} undocumented: {undocumented[:6]}")

# ── 8. inbox / reporting ─────────────────────────────────────────────────────
inbox = ROOT / "shared" / "reports" / "inbox"
strays = [p.name for p in inbox.iterdir() if p.is_file() and p.suffix.lower() != ".json"] if inbox.exists() else []
check("report inbox has no strays", not strays, f"strays: {strays}")

# ── 9. repo hygiene ──────────────────────────────────────────────────────────
baks = subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True,
                      text=True, encoding="utf-8", errors="replace").stdout.splitlines()
tracked_baks = [f for f in baks if re.search(r"\.bak[-_.]|\.bak$", f)]
check("no backup files tracked in git", not tracked_baks, f"{len(tracked_baks)} tracked .bak* files")
check("legacy shadow tree gone", not (ROOT / "hive").exists(), "C:\\QIH\\hive archived")

# ── 10. task board ───────────────────────────────────────────────────────────
tasks_json = json.loads((ROOT / "data" / "tasks.json").read_text(encoding="utf-8"))
tl = tasks_json.get("tasks", [])
open_tasks = [t for t in tl if t.get("column") != "done"]
seen, dupes = set(), 0
for t in open_tasks:
    k = (t.get("project"), t.get("title"))
    if k in seen:
        dupes += 1
    seen.add(k)
check("task board deduped", dupes == 0, f"{len(open_tasks)} open, {dupes} duplicate title+project")

# ── report ───────────────────────────────────────────────────────────────────
w = max(len(n) for n, _, _ in results)
done = sum(1 for _, s, _ in results if s == "DONE")
lag = sum(1 for _, s, _ in results if s == "LAGGING")
print(f"{'ITEM'.ljust(w)}  STATUS   DETAIL")
print("-" * (w + 40))
for n, s, d in results:
    mark = "OK " if s == "DONE" else ("!! " if s == "LAGGING" else "-- ")
    print(f"{mark}{n.ljust(w)}  {s:8} {d}")
print("-" * (w + 40))
print(f"{done} done · {lag} lagging · {len(results)} checks")

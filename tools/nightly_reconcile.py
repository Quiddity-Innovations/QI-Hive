# -*- coding: utf-8 -*-
"""
Nightly Hive reconciler — the safety net.

Runs once per day via Windows Scheduled Task. Scans every registered project
for git activity and .docx summaries since the last reconcile, and inserts
session_log + project_state entries for anything Brain doesn't already know.

This guarantees that if a Stop hook misses (Claude crashes, worktree fails,
project unregistered, network blip), Brain still catches up within 24h.

Logs to C:\\QIH\\logs\\nightly_reconcile.log.
"""
from __future__ import annotations
import sqlite3, json, sys, subprocess, re
from pathlib import Path
from datetime import datetime, timedelta

LOG = Path(r'C:\QIH\logs\nightly_reconcile.log')
LOG.parent.mkdir(parents=True, exist_ok=True)

def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

DB = r'C:\QIH\data\qi_brain.db'
SUMMARIES = Path(r'C:\QIH\shared\documentation\session_summaries')
LATEST_MD = Path(r'C:\QIH\LATEST.md')
STATUS_JSON = Path(r'C:\QIH\status.json')

PROJECT_PREFIX = {
    'CogniBase': 'cognibase', 'MapSnapOnBase': 'cognibase',
    'MapSnap': 'mapsnap', 'AutoPDF': 'autopdf', 'EasyFlow': 'easyflow',
    'Maia': 'maia', 'Naya': 'naya', 'NEXUS': 'nexus',
    'MQ': 'mq', 'QIHive': 'qi_hive',
}

GIT_PROJECTS = {
    'cognibase': r'C:\CogniBase', 'mapsnap': r'C:\MapSnap',
    'autopdf': r'C:\Users\renne\Downloads\AUTOPDF',
    'easyflow': r'C:\EasyFlow', 'maia': r'C:\QI', 'naya': r'C:\NAYA',
    'nexus': r'C:\NEXUS', 'mq': r'C:\MQ', 'qi_hive': r'C:\QIH',
}

def main():
    log("=== Nightly reconciler START ===")
    con = sqlite3.connect(DB)
    cur = con.cursor()

    # last 7 days window — covers weekend/long gaps
    cutoff_dt = datetime.now() - timedelta(days=7)
    cutoff = cutoff_dt.strftime('%Y-%m-%d')

    existing = set()
    for r in cur.execute("SELECT project_id, session_title FROM session_log WHERE started_at >= ?", (cutoff,)):
        existing.add((r[0], (r[1] or '')[:80]))

    docx_added = 0
    for f in sorted(SUMMARIES.glob('*.docx')):
        m = re.match(r'^([A-Za-z]+)_(.+)_(\d{4}-\d{2}-\d{2})_(\d{4})\.docx$', f.name)
        if not m: continue
        prefix, mid, date_str, time_str = m.groups()
        if date_str < cutoff: continue
        pid = PROJECT_PREFIX.get(prefix)
        if not pid: continue
        title = mid.replace('_',' ').strip()
        key = (pid, title[:80])
        if key in existing: continue
        started = f"{date_str} {time_str[:2]}:{time_str[2:]}:00"
        cur.execute(
            "INSERT INTO session_log (project_id, agent_id, session_title, summary, decisions_made, features_logged, files_changed, next_steps, model_used, started_at, ended_at) VALUES (?,?,?,?,0,0,?,?,?,?,?)",
            (pid, 'nightly', title, f"Backfilled from {f.name}", '[]', '', 'unknown', started, started)
        )
        existing.add(key)
        docx_added += 1

    git_added = 0
    for pid, path in GIT_PROJECTS.items():
        if not Path(path,'.git').exists(): continue
        try:
            out = subprocess.run(
                ['git','-C',path,'log',f'--since={cutoff}','--format=%ai|%s'],
                capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=15
            )
        except Exception as e:
            log(f"  git error {pid}: {e}")
            continue
        if out.returncode != 0: continue
        for line in out.stdout.splitlines():
            if '|' not in line: continue
            when, msg = line.split('|',1)
            when = when.strip()[:19]
            msg = msg.strip()
            title = f"commit: {msg[:100]}"
            key = (pid, title[:80])
            if key in existing: continue
            cur.execute(
                "INSERT INTO session_log (project_id, agent_id, session_title, summary, decisions_made, features_logged, files_changed, next_steps, model_used, started_at, ended_at) VALUES (?,'git-nightly',?,?,0,0,'[]','','git-only',?,?)",
                (pid, title, f"Git commit: {msg}", when, when)
            )
            existing.add(key)
            git_added += 1

    con.commit()
    log(f"  docx-backfilled: {docx_added}, git-backfilled: {git_added}")

    # Regenerate LATEST.md + status.json
    states = {}
    for r in cur.execute("SELECT project_id, phase, status, summary, next_steps, recorded_at FROM project_state ORDER BY recorded_at DESC"):
        if r[0] not in states: states[r[0]] = r
    sc = {r[0]: r[1] for r in cur.execute("SELECT project_id, COUNT(*) FROM session_log GROUP BY project_id")}
    last = {r[0]: r[1] for r in cur.execute("SELECT project_id, MAX(started_at) FROM session_log GROUP BY project_id")}

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    md = [f"# QI Hive — LATEST", "", f"_Auto-generated: {now} (nightly reconciler)_", "",
          "| Project | Phase | Status | Sessions | Last |", "|---|---|---|---|---|"]
    for pid in sorted(states):
        _,phase,status,_,_,_ = states[pid]
        md.append(f"| {pid} | {phase} | {status} | {sc.get(pid,0)} | {last.get(pid,'—')} |")
    md += ["", "## Per-project", ""]
    for pid in sorted(states):
        _,phase,status,summary,nxt,_ = states[pid]
        md += [f"### {pid}", f"- **Phase:** {phase}", f"- **Status:** {status}",
               f"- **Summary:** {summary}", f"- **Next:** {nxt}", ""]
    LATEST_MD.write_text("\n".join(md), encoding='utf-8')

    obj = {"_meta": {"generated": now, "source": "nightly_reconcile.py"},
           "projects": {pid: {"phase": s[1], "status": s[2], "summary": s[3],
                              "next_steps": s[4], "recorded_at": s[5],
                              "session_count": sc.get(pid,0), "last_session": last.get(pid)}
                        for pid, s in states.items()}}
    STATUS_JSON.write_text(json.dumps(obj, indent=2), encoding='utf-8')
    log(f"  Wrote LATEST.md and status.json")

    con.close()

    # Deep compliance scan — fold-in
    try:
        sys.path.insert(0, r'C:\QIH\engine\hive')
        from inspector.inspector import run_scan as _run_scan
        res = _run_scan(project_id=None, mode='deep', auto_fix=True)
        s = res['summary']
        log(f"  Compliance deep-scan: pass={s['pass']} fail={s['fail']} warn={s['warn']} "
            f"skip={s['skip']} auto_fixed={s['auto_fixed']} dispatched={s['dispatched']}")
    except Exception as e:
        log(f"  Compliance deep-scan FAILED: {type(e).__name__}: {e}")

    log("=== Nightly reconciler END ===\n")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        log(f"FATAL: {type(e).__name__}: {e}")
        sys.exit(1)

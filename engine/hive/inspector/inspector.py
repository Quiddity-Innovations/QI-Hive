# -*- coding: utf-8 -*-
"""
QI Hive Inspector — Standards Enforcement agent.

Runs compliance checks against every QI project. Fixes deterministic
issues automatically. Files dispatches for ambiguous ones.

Modes:
    fast — cheap checks only (file existence, JSON parse, hook references).
           Used by the real-time poller trigger and the 4-hour safety net.
    deep — fast checks + HTTP probes + git log scan + NSSM probes.
           Used by the nightly reconciler.

Usage:
    python -m inspector.inspector                       # scan all, fast, auto-fix on
    python -m inspector.inspector --project maia
    python -m inspector.inspector --mode deep
    python -m inspector.inspector --no-auto-fix         # audit-only
    python -m inspector.inspector --project mapsnap --mode deep
"""
from __future__ import annotations
import argparse, json, sqlite3, subprocess, sys, urllib.request, urllib.error, uuid, re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\QIH\data\qi_brain.db'
REGISTRY = r'C:\QIH\ecosystem\qi_registry.json'
HOOKS_DIR = Path(r'C:\QIH\hooks')
NSSM = r'C:\QIH\engine\bin\nssm.exe'
PYTHON = r'C:\1-AI\APPS\PYTHON\python.exe'
BOOTSTRAP = r'C:\QIH\engine\common\session_bootstrap.py'
SESSION_STOP = r'C:\QIH\engine\common\session_stop.py'

# Projects we expect on disk (project_id -> path)
PROJECT_PATHS = {
    'maia':      r'C:\QI',
    'naya':      r'C:\NAYA',
    'nexus':     r'C:\NEXUS',
    'easyflow':  r'C:\EasyFlow',
    'mq':        r'C:\MQ',
    'cognibase': r'C:\CogniBase',
    'mapsnap':   r'C:\MapSnap',
    'autopdf':   r'C:\Users\renne\Downloads\AUTOPDF',
    'qi_hive':   r'C:\QIH',
}

# Skip hook checks for these (adjacent / external / retired)
SKIP_HOOKS = {'openclaw', 'filehq', 'qi_brain', 'universal'}


@dataclass
class CheckResult:
    check_id: str
    project_id: str
    status: str        # 'pass' | 'fail' | 'warn' | 'skip'
    severity: str      # 'critical' | 'high' | 'medium' | 'low' | 'info'
    auto_fixable: bool
    message: str
    fix_action: Optional[str] = None      # description of fix that ran/would run
    fixed: bool = False
    dispatch_id: Optional[int] = None


# ─────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────

def db():
    return sqlite3.connect(DB)


def ensure_schema():
    with db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS compliance_log (
                log_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id        TEXT NOT NULL,
                project_id    TEXT NOT NULL,
                check_id      TEXT NOT NULL,
                status        TEXT NOT NULL,
                severity      TEXT NOT NULL,
                auto_fixable  INTEGER NOT NULL DEFAULT 0,
                action_taken  TEXT NOT NULL DEFAULT 'none',
                message       TEXT,
                fix_action    TEXT,
                dispatch_id   INTEGER,
                mode          TEXT NOT NULL DEFAULT 'fast',
                recorded_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        con.execute("CREATE INDEX IF NOT EXISTS idx_compliance_run ON compliance_log(run_id)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_compliance_project ON compliance_log(project_id, recorded_at DESC)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_compliance_check ON compliance_log(check_id, project_id)")
        con.commit()


def get_registered_projects() -> list[str]:
    with db() as con:
        return [r[0] for r in con.execute("SELECT project_id FROM projects WHERE active=1")]


def file_dispatch(project_id: str, check_id: str, message: str, fix_action: str) -> int:
    """Write to dispatches table, return dispatch_id."""
    with db() as con:
        cur = con.execute(
            "INSERT INTO dispatches (source, type, priority, project_id, payload, status, created_at) "
            "VALUES (?,?,?,?,?, 'pending', ?)",
            ('hive_inspector', 'compliance', 'medium', project_id,
             json.dumps({'check_id': check_id, 'message': message, 'suggested_fix': fix_action}),
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        con.commit()
        return cur.lastrowid


def write_log(run_id: str, mode: str, results: list[CheckResult]):
    with db() as con:
        for r in results:
            action = 'fixed' if r.fixed else ('dispatched' if r.dispatch_id else 'none')
            con.execute(
                "INSERT INTO compliance_log (run_id, project_id, check_id, status, severity, "
                "auto_fixable, action_taken, message, fix_action, dispatch_id, mode) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (run_id, r.project_id, r.check_id, r.status, r.severity,
                 1 if r.auto_fixable else 0, action, r.message, r.fix_action, r.dispatch_id, mode)
            )
        con.commit()


# ─────────────────────────────────────────────────────────────
# Checks — each returns CheckResult or None (skip)
# Auto-fix happens inside the check when auto_fix=True.
# ─────────────────────────────────────────────────────────────

def _settings_json_template(project_id: str) -> str:
    return json.dumps({
        "hooks": {
            "SessionStart": [
                {"hooks": [{"type": "command", "command": f"cmd /c \"C:\\\\QIH\\\\hooks\\\\{project_id}_start.bat\""}]}
            ],
            "Stop": [
                {"hooks": [{"type": "command", "command": f"cmd /c \"C:\\\\QIH\\\\hooks\\\\{project_id}_stop.bat\""}]}
            ]
        }
    }, indent=2)


def _bat_template(project_id: str, kind: str) -> str:
    """kind is 'start' or 'stop'."""
    target = BOOTSTRAP if kind == 'start' else SESSION_STOP
    pretty = {'maia':'Maia','naya':'Naya','nexus':'NEXUS','easyflow':'EasyFlow',
              'mq':'MQ','cognibase':'CogniBase','mapsnap':'MapSnap','autopdf':'AutoPDF',
              'qi_hive':'QIHive'}.get(project_id, project_id)
    return f'@echo off\n"{PYTHON}" "{target}" --project {pretty} --project-id {project_id}\n'


def check_settings_json(pid: str, path: Path, auto_fix: bool) -> Optional[CheckResult]:
    if pid in SKIP_HOOKS:
        return None
    cfg = path / '.claude' / 'settings.json'
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text(encoding='utf-8'))
            has_stop = bool(data.get('hooks', {}).get('Stop'))
            has_start = bool(data.get('hooks', {}).get('SessionStart'))
            if has_stop and has_start:
                return CheckResult('hooks_settings_json_exists', pid, 'pass', 'high', True,
                                   '.claude/settings.json present with both hooks')
            return CheckResult('hooks_settings_json_exists', pid, 'fail', 'high', True,
                               f"settings.json missing hooks (Stop={has_stop}, Start={has_start})",
                               'Regenerate .claude/settings.json with default Stop+Start hooks',
                               fixed=False) if not auto_fix else _do_fix_settings(pid, cfg)
        except json.JSONDecodeError as e:
            return CheckResult('hooks_settings_json_exists', pid, 'fail', 'high', False,
                               f"settings.json malformed: {e}",
                               'Manual review required (auto-fix would clobber a possibly-customized file)')
    if not auto_fix:
        return CheckResult('hooks_settings_json_exists', pid, 'fail', 'high', True,
                           '.claude/settings.json missing',
                           f"Create .claude/settings.json with Stop+Start hooks for '{pid}'")
    return _do_fix_settings(pid, cfg)


def _do_fix_settings(pid: str, cfg: Path) -> CheckResult:
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(_settings_json_template(pid), encoding='utf-8')
    return CheckResult('hooks_settings_json_exists', pid, 'fail', 'high', True,
                       f"Created .claude/settings.json for {pid}",
                       'Generated from template', fixed=True)


def check_hook_bats(pid: str, path: Path, auto_fix: bool) -> list[CheckResult]:
    if pid in SKIP_HOOKS:
        return []
    out = []
    for kind in ('start', 'stop'):
        bat = HOOKS_DIR / f'{pid}_{kind}.bat'
        check_id = f'hook_bat_{kind}_exists'
        if bat.exists():
            content = bat.read_text(encoding='utf-8', errors='replace')
            if re.search(r'(?im)^python ', content):
                if auto_fix:
                    new = re.sub(r'(?im)^python ', f'"{PYTHON}" ', content)
                    bat.write_text(new, encoding='utf-8')
                    out.append(CheckResult(f'hook_bat_{kind}_python_path', pid, 'fail', 'medium',
                                           True, f"{bat.name} used bare 'python', replaced with full path",
                                           'Replaced bare python', fixed=True))
                else:
                    out.append(CheckResult(f'hook_bat_{kind}_python_path', pid, 'fail', 'medium', True,
                                           f"{bat.name} uses bare 'python' instead of full path",
                                           'Replace with full Python path'))
            else:
                out.append(CheckResult(f'hook_bat_{kind}_python_path', pid, 'pass', 'medium', True,
                                       f"{bat.name} uses full Python path"))
            out.append(CheckResult(check_id, pid, 'pass', 'high', True, f"{bat.name} exists"))
        else:
            if auto_fix:
                bat.write_text(_bat_template(pid, kind), encoding='utf-8')
                out.append(CheckResult(check_id, pid, 'fail', 'high', True,
                                       f"{bat.name} was missing, generated from template",
                                       'Generated default bat', fixed=True))
            else:
                out.append(CheckResult(check_id, pid, 'fail', 'high', True,
                                       f"{bat.name} missing", 'Generate from template'))
    return out


def check_brain_registered(pid: str, path: Path, auto_fix: bool) -> CheckResult:
    with db() as con:
        row = con.execute("SELECT 1 FROM projects WHERE project_id=?", (pid,)).fetchone()
    if row:
        return CheckResult('brain_registered', pid, 'pass', 'high', True,
                           'Project registered in qi_brain.db.projects')
    if auto_fix:
        with db() as con:
            con.execute(
                "INSERT INTO projects (project_id, display_name, tagline, path, tier, active, created_at) "
                "VALUES (?,?,?,?, 'project', 1, ?)",
                (pid, pid.title(), 'Auto-registered by Inspector', str(path),
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            con.commit()
        return CheckResult('brain_registered', pid, 'fail', 'high', True,
                           'Project missing from Brain; auto-registered',
                           'Inserted into projects table', fixed=True)
    return CheckResult('brain_registered', pid, 'fail', 'high', True,
                       'Project not in Brain', 'Auto-register on next run')


DECOY_DOC_PATTERNS = (
    "Quiddity Innovations - ", "DOCUMENTATION", "Documentation",
    "Doc", "Docs",
)


def check_canonical_docs(pid: str, path: Path, auto_fix: bool) -> list[CheckResult]:
    """Enforce single canonical `docs/` folder. Flag doc-shaped decoys."""
    out = []
    docs = path / 'docs'

    if not docs.exists():
        out.append(CheckResult('canonical_docs_exists', pid, 'fail', 'medium', False,
                               'docs/ folder missing at project root',
                               'Manual: create docs/ and move documentation there '
                               '(or run scripts/migrate_docs.py)'))
        return out
    out.append(CheckResult('canonical_docs_exists', pid, 'pass', 'medium', False,
                           'docs/ folder present at project root'))

    # README.md inside docs/
    readme = docs / 'README.md'
    if not readme.exists():
        out.append(CheckResult('docs_readme_exists', pid, 'fail', 'low', False,
                               'docs/README.md index missing',
                               'Auto-generatable by inspector — run with --auto-fix'))
    else:
        out.append(CheckResult('docs_readme_exists', pid, 'pass', 'low', False,
                               'docs/README.md present'))

    # Decoy detection — sibling dirs that look like doc folders
    suspects = []
    for d in path.iterdir():
        if not d.is_dir() or d.name == 'docs':
            continue
        n = d.name
        if any(n.startswith(p) or n == p for p in DECOY_DOC_PATTERNS):
            suspects.append(d)
    if not suspects:
        out.append(CheckResult('docs_no_decoys', pid, 'pass', 'medium', False,
                               'No decoy doc folders alongside docs/'))
    else:
        for s in suspects:
            try:
                files = sum(1 for _ in s.rglob('*') if _.is_file())
            except Exception:
                files = -1
            msg = f"Doc-shaped folder '{s.name}' at root ({files} files) — should be merged into docs/"
            fix = f"Move contents of '{s.name}' into docs/, then delete the empty folder."
            did = file_dispatch(pid, 'docs_no_decoys', msg, fix)
            out.append(CheckResult('docs_no_decoys', pid, 'fail', 'medium', False,
                                   msg, fix, dispatch_id=did))
    return out


def check_claudemd_exists(pid: str, path: Path, auto_fix: bool) -> CheckResult:
    cm = path / 'CLAUDE.md'
    if cm.exists():
        return CheckResult('claudemd_exists', pid, 'pass', 'medium', False,
                           'CLAUDE.md present at project root')
    return CheckResult('claudemd_exists', pid, 'fail', 'medium', False,
                       'CLAUDE.md missing at project root',
                       'Manual: write project-specific CLAUDE.md (cannot auto-generate meaningfully)')


def check_gitignore_secrets(pid: str, path: Path, auto_fix: bool) -> Optional[CheckResult]:
    gi = path / '.gitignore'
    if not (path / '.git').exists():
        return None
    if not gi.exists():
        return CheckResult('gitignore_secrets', pid, 'warn', 'medium', False,
                           '.gitignore missing entirely',
                           'Manual: create .gitignore with secrets/, chroma/, *.env')
    content = gi.read_text(encoding='utf-8', errors='replace')
    missing = []
    for needle, label in (('secrets/', 'secrets/'), ('.env', '.env'), ('chroma', 'chroma vector store')):
        if needle not in content:
            missing.append(label)
    if not missing:
        return CheckResult('gitignore_secrets', pid, 'pass', 'medium', False,
                           '.gitignore covers secrets/, .env, chroma')
    # dispatch — never auto-edit .gitignore
    msg = f".gitignore is missing entries for: {', '.join(missing)}"
    fix = f"Append these lines to .gitignore: {', '.join(missing)}"
    did = file_dispatch(pid, 'gitignore_secrets', msg, fix)
    return CheckResult('gitignore_secrets', pid, 'warn', 'medium', False, msg, fix, dispatch_id=did)


def check_session_freshness(pid: str, path: Path, auto_fix: bool) -> CheckResult:
    """Stale = no session_log row in 14 days AND project not paused/blocked/retired."""
    with db() as con:
        last = con.execute(
            "SELECT MAX(started_at) FROM session_log WHERE project_id=?", (pid,)
        ).fetchone()[0]
        state = con.execute(
            "SELECT status FROM project_state WHERE project_id=? ORDER BY recorded_at DESC LIMIT 1",
            (pid,)
        ).fetchone()
    state_val = (state[0] if state else '') or ''
    if state_val in ('paused', 'blocked', 'retired', 'active_external'):
        return CheckResult('session_freshness', pid, 'skip', 'low', False,
                           f"Project status='{state_val}' — silence is intentional")
    if not last:
        msg = "No session_log entries ever for this project"
        did = file_dispatch(pid, 'session_freshness', msg, 'Decide: paused, abandoned, or never logged?')
        return CheckResult('session_freshness', pid, 'fail', 'medium', False, msg, dispatch_id=did)
    last_dt = datetime.strptime(last[:10], '%Y-%m-%d')
    days = (datetime.now() - last_dt).days
    if days > 14:
        msg = f"No session activity in {days} days (status={state_val or 'unknown'})"
        fix = "Mark project paused/blocked, or run a session"
        did = file_dispatch(pid, 'session_freshness', msg, fix)
        return CheckResult('session_freshness', pid, 'warn', 'medium', False, msg, fix, dispatch_id=did)
    return CheckResult('session_freshness', pid, 'pass', 'low', False,
                       f"Last session {days}d ago")


# ── DEEP-only checks ──

def check_module_interface(pid: str, path: Path, auto_fix: bool) -> Optional[list[CheckResult]]:
    """HTTP probe /health, /version, /info — only for projects with an api_port."""
    with db() as con:
        row = con.execute("SELECT api_port FROM projects WHERE project_id=?", (pid,)).fetchone()
    if not row or not row[0]:
        return None
    port = row[0]
    out = []
    for endpoint, severity in (('/health', 'high'), ('/version', 'medium'), ('/info', 'low')):
        url = f'http://127.0.0.1:{port}{endpoint}'
        try:
            with urllib.request.urlopen(url, timeout=4) as r:
                code = r.status
                body = r.read(500).decode('utf-8', errors='replace')
                if 200 <= code < 300:
                    out.append(CheckResult(f'module_interface{endpoint.replace("/","_")}',
                                           pid, 'pass', severity, False,
                                           f"{endpoint} returned {code}"))
                else:
                    out.append(CheckResult(f'module_interface{endpoint.replace("/","_")}',
                                           pid, 'fail', severity, False,
                                           f"{endpoint} returned {code}: {body[:120]}"))
        except urllib.error.HTTPError as e:
            out.append(CheckResult(f'module_interface{endpoint.replace("/","_")}',
                                   pid, 'fail', severity, False,
                                   f"{endpoint} HTTP {e.code}"))
        except Exception as e:
            out.append(CheckResult(f'module_interface{endpoint.replace("/","_")}',
                                   pid, 'warn', severity, False,
                                   f"{endpoint} unreachable: {type(e).__name__}"))
    return out


# ─────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────

def run_scan(project_id: Optional[str] = None, mode: str = 'fast', auto_fix: bool = True) -> dict:
    ensure_schema()
    run_id = str(uuid.uuid4())
    started = datetime.now()
    targets = [project_id] if project_id else list(PROJECT_PATHS.keys())

    all_results: list[CheckResult] = []

    for pid in targets:
        path_str = PROJECT_PATHS.get(pid)
        if not path_str:
            all_results.append(CheckResult('project_known', pid, 'fail', 'high', False,
                                           f"Unknown project_id; not in PROJECT_PATHS"))
            continue
        path = Path(path_str)
        if not path.exists():
            all_results.append(CheckResult('project_path_exists', pid, 'fail', 'critical', False,
                                           f"Project path missing on disk: {path}"))
            continue
        all_results.append(CheckResult('project_path_exists', pid, 'pass', 'critical', False,
                                       'Project directory exists'))

        # Fast checks
        try:
            all_results.extend(check_canonical_docs(pid, path, auto_fix))
        except Exception as e:
            all_results.append(CheckResult('check_canonical_docs', pid, 'fail', 'low', False,
                                           f"check raised: {type(e).__name__}: {e}"))

        for fn in (check_brain_registered, check_settings_json,
                   check_claudemd_exists, check_gitignore_secrets, check_session_freshness):
            try:
                r = fn(pid, path, auto_fix)
                if r is None:
                    continue
                all_results.append(r)
            except Exception as e:
                all_results.append(CheckResult(fn.__name__, pid, 'fail', 'low', False,
                                               f"check raised: {type(e).__name__}: {e}"))
        try:
            for r in check_hook_bats(pid, path, auto_fix):
                all_results.append(r)
        except Exception as e:
            all_results.append(CheckResult('check_hook_bats', pid, 'fail', 'low', False,
                                           f"check raised: {type(e).__name__}: {e}"))

        # Deep checks
        if mode == 'deep':
            try:
                deep = check_module_interface(pid, path, auto_fix)
                if deep:
                    all_results.extend(deep)
            except Exception as e:
                all_results.append(CheckResult('module_interface', pid, 'fail', 'low', False,
                                               f"check raised: {type(e).__name__}: {e}"))

    write_log(run_id, mode, all_results)

    summary = {
        'run_id': run_id,
        'mode': mode,
        'auto_fix': auto_fix,
        'started_at': started.isoformat(timespec='seconds'),
        'finished_at': datetime.now().isoformat(timespec='seconds'),
        'projects_scanned': len(targets),
        'checks_run': len(all_results),
        'pass':       sum(1 for r in all_results if r.status == 'pass'),
        'fail':       sum(1 for r in all_results if r.status == 'fail'),
        'warn':       sum(1 for r in all_results if r.status == 'warn'),
        'skip':       sum(1 for r in all_results if r.status == 'skip'),
        'auto_fixed': sum(1 for r in all_results if r.fixed),
        'dispatched': sum(1 for r in all_results if r.dispatch_id),
    }
    return {'summary': summary, 'results': [r.__dict__ for r in all_results]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', dest='project_id', default=None,
                    help='Single project_id to scan (default: all)')
    ap.add_argument('--mode', choices=['fast', 'deep'], default='fast')
    ap.add_argument('--no-auto-fix', dest='auto_fix', action='store_false', default=True,
                    help='Audit-only mode — no fixes, no dispatches')
    ap.add_argument('--json', action='store_true', help='Emit full JSON to stdout')
    args = ap.parse_args()

    res = run_scan(args.project_id, args.mode, args.auto_fix)
    s = res['summary']
    print(f"Run {s['run_id']} [{s['mode']}, auto_fix={s['auto_fix']}]")
    print(f"  Projects: {s['projects_scanned']}  Checks: {s['checks_run']}")
    print(f"  pass={s['pass']}  fail={s['fail']}  warn={s['warn']}  skip={s['skip']}")
    print(f"  auto_fixed={s['auto_fixed']}  dispatched={s['dispatched']}")
    if not args.json:
        for r in res['results']:
            if r['status'] in ('fail', 'warn'):
                tag = '✓fixed' if r['fixed'] else (f"→disp{r['dispatch_id']}" if r['dispatch_id'] else r['status'].upper())
                print(f"  [{tag}] {r['project_id']:10} {r['check_id']:32} {r['message']}")
    else:
        print(json.dumps(res, indent=2))


if __name__ == '__main__':
    main()

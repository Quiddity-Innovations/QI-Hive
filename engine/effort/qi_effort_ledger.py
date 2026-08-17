#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QI Effort Ledger
================
Forensic reconstruction + ongoing daily tracking of development effort
(hours, tokens, code volume) per project, from independently verifiable
timestamped artifacts on this machine.

Design principles (these exist because the output may be scrutinised):
  1. Every hour traces back to a raw artifact (a git SHA, a transcript line).
  2. Nothing is inferred about *purpose*. Only *when* and *how much*.
  3. Assumptions are parameters, printed in every report, never hidden.
  4. Conservative bias: when uncertain, credit less rather than more.
  5. Append-only, hash-chained ledger so history cannot be silently rewritten.

Usage:
    python qi_effort_ledger.py --backfill     # scan all history
    python qi_effort_ledger.py --daily        # incremental; for scheduled task
    python qi_effort_ledger.py --report       # CSV + JSON + summary
"""

import argparse
import csv
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta, date, time as dtime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ----------------------------------------------------------------------------
# CONFIGURATION -- all assumptions live here and are printed in every report
# ----------------------------------------------------------------------------

LOCAL_TZ = ZoneInfo("America/New_York")   # DST-aware; git already carries offset

BUSINESS_START = dtime(8, 0)     # weekday business hours begin
BUSINESS_END   = dtime(17, 30)   # <-- the 5:30 PM line

# Session reconstruction
IDLE_GAP_MIN   = 30   # gap > this starts a new work session
LEAD_IN_MIN    = 6    # credit before the first artifact of a session
MAX_SESSION_HR = 6    # safety cap on any single reconstructed session

DATA_DIR   = Path(r"C:\QIH\data\effort")
DB_PATH    = DATA_DIR / "effort_ledger.db"
REPORT_DIR = DATA_DIR / "reports"
LOG_PATH   = Path(r"C:\QIH\logs\effort_ledger.log")

CLAUDE_PROJECTS = Path(r"C:\Users\renne\.claude\projects")
SUMMARY_DIR     = Path(r"C:\QIH\shared\documentation\session_summaries")

# Repo roots scanned, in priority order. Earlier roots win project attribution
# when the same commit SHA appears in several clones/worktrees.
REPO_ROOTS = [Path(r"C:\APPS"), Path(r"C:\QIH"), Path(r"C:\FileHQ"), Path(r"D:\Dev")]

# Third-party / vendored repos: never counted as authored work.
# NOTE: OC\repo / OpenClaw\repo is NOT listed here. It is a fork containing
# the owner's own commits, so it is counted (attributed to OpenClaw).
VENDOR_PATTERNS = [
    r"seed-vc", r"hallo2", r"OpenSpace", r"ComfyUI",
    r"node_modules", r"site-packages", r"\\venv\\", r"\\.venv\\",
]

# US federal holidays (weekday holidays are bucketed separately, not as
# ordinary business hours). Extend as needed.
HOLIDAYS = {
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-05-25", "2026-06-19",
    "2026-07-03", "2026-11-11", "2026-11-26", "2026-12-25",
}

# API list-price replacement cost, USD per 1M tokens (input, output).
# NOTE: this is REPLACEMENT COST at public list rates, NOT money paid.
PRICING = {
    "fable":  (10.0, 50.0),
    "opus":   (5.0,  25.0),
    "sonnet": (3.0,  15.0),
    "haiku":  (1.0,   5.0),
}
CACHE_WRITE_MULT = 1.25   # cache creation billed at 1.25x input
CACHE_READ_MULT  = 0.10   # cache read billed at 0.10x input

BUCKETS = ["business", "after_hours", "early_morning", "weekend", "holiday"]

# ---------------------------------------------------------------------------
# GOVERNANCE CLASSIFICATION -- owner-declared, not machine-inferred.
# These are statements of fact by the owner. The tooling records them and does
# not attempt to verify, contradict or extend them. Edit here to update.
# ---------------------------------------------------------------------------
DECLARED_ON = "2026-08-13"

# Built independently by the owner; shared with or demonstrated to a third
# party (Boston University).
DECLARED_SHARED = ["CogniBase", "QI Hive", "NEXUS", "MapSnap", "AutoPDF"]

# Built independently by the owner but applied to employer data. Ownership is
# genuinely arguable; disclosed rather than quietly included or excluded.
MIXED_PROVENANCE = ["Note Discovery", "OnBase DNA"]

# Work performed for the employer. Excluded from personal-effort totals.
# (None declared as at DECLARED_ON.)
EMPLOYER_WORK = []


def governance(project):
    """Owner-declared governance status for a project."""
    if project in EMPLOYER_WORK:
        return "Employer work"
    if project in MIXED_PROVENANCE:
        return "Mixed provenance"
    if project in DECLARED_SHARED:
        return "Shared with BU"
    return "Personal"


# ----------------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------------

def log(msg):
    line = f"[{datetime.now(LOCAL_TZ).isoformat(timespec='seconds')}] {msg}"
    print(line)
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def is_vendor(path_str):
    return any(re.search(p, path_str, re.I) for p in VENDOR_PATTERNS)


# Path noise words stripped from transcript slugs before naming a project.
_NOISE = {"c", "d", "users", "renne", "downloads", "apps", "dev", "qip",
          "engine", "hive"}

# Canonical names. Keys are lowercase, spaces/underscores/hyphens removed.
_ALIASES = {
    "qi": "Maia", "appsqi": "Maia", "maia": "Maia",
    "qih": "QI Hive", "qihive": "QI Hive", "universal": "QI Hive (legacy)",
    "mapsnap": "MapSnap", "naya": "Naya", "nexus": "NEXUS",
    "oc": "OpenClaw", "openclaw": "OpenClaw", "ocrepo": "OpenClaw",
    "openclawrepo": "OpenClaw",
    "claude": "Claude Manager", "appsclaude": "Claude Manager",
    "claudemanager": "Claude Manager",
    "claudevoice": "Claude Voice", "claudeclaudevoice": "Claude Voice",
    "retirementanalyzer": "Retirement Analyzer",
    "notediscovery": "Note Discovery",
    "autopdf": "AutoPDF", "cognibase": "CogniBase", "easyflow": "EasyFlow",
    "filehq": "FileHQ", "tubescout": "TubeScout", "playdeck": "PlayDeck",
    "akiyascout": "AkiyaScout", "personalsong": "PersonalSong",
    "lotterywiz": "Lottery Wiz", "mediastudio": "Media Studio",
    "m2v": "M2V", "filmforge": "FilmForge", "gamez": "Gamez",
    "cypherminer": "CypherMiner", "mailbrain": "MailBrain", "mq": "MQ",
    "connector": "QI Connector", "bakeoff": "Bakeoff",
    "avatarstudio": "AvatarStudio", "voicestudio": "Voice Studio",
    "onbasedna": "OnBase DNA", "digitizationcosts": "Digitization Costs",
    "gmailbeyond": "Gmail & Beyond", "fidelityanalyzer": "Fidelity Analyzer",
    "aicomfyuiwindowsportable": "ComfyUI (third-party tooling)",
    "": "Ad-hoc (C:\\ root)",
}

# Generic directory names that never identify a project on their own.
_GENERIC = {"repo", "src", "app", "main", "code"}


def normalise_project(raw):
    """Map a repo path or transcript slug to a stable project name.

    Handles both real paths (C:\\APPS\\MapSnap) and Claude transcript slugs
    (C--APPS-MapSnap), strips worktree suffixes, drops path noise words, and
    resolves a generic leaf like 'repo' to its parent so that
    D:\\Dev\\OpenClaw\\repo does not become a project called 'repo'.
    """
    s = str(raw)
    s = re.sub(r"--claude-worktrees-[a-z\-0-9]+$", "", s, flags=re.I)

    if "\\" in s or "/" in s:                       # a real filesystem path
        parts = [p for p in re.split(r"[\\/]+", s.rstrip("\\/")) if p]
        parts = [p for p in parts if not re.match(r"^[A-Za-z]:$", p)]
        if parts and parts[-1].lower() in _GENERIC and len(parts) > 1:
            leaf = parts[-2] + parts[-1]            # OpenClaw + repo
        else:
            leaf = parts[-1] if parts else ""
    else:                                            # a transcript slug
        s = re.sub(r"^[A-Za-z]--", "", s)
        toks = [t for t in re.split(r"[-_]+", s) if t]
        kept = [t for t in toks if t.lower() not in _NOISE]
        leaf = "".join(kept) if kept else ""

    key = re.sub(r"[\s_\-]+", "", leaf).lower()
    if key in _ALIASES:
        return _ALIASES[key]
    if not leaf:
        return "Ad-hoc (C:\\ root)"
    # Split camel/pascal case into words for anything unmapped.
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", leaf).strip()


def classify_minute(dt):
    """Bucket a single local-time minute. Never guesses purpose -- clock only."""
    if dt.strftime("%Y-%m-%d") in HOLIDAYS and dt.weekday() < 5:
        return "holiday"
    if dt.weekday() >= 5:
        return "weekend"
    t = dt.time()
    if t >= BUSINESS_END:
        return "after_hours"
    if t < BUSINESS_START:
        return "early_morning"
    return "business"


def price_for_model(model):
    m = (model or "").lower()
    for key in PRICING:
        if key in m:
            return PRICING[key]
    return PRICING["sonnet"]   # conservative mid-tier default for unknown ids


# ----------------------------------------------------------------------------
# DATABASE
# ----------------------------------------------------------------------------

def connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS events (
        event_id   TEXT PRIMARY KEY,
        ts_utc     TEXT NOT NULL,
        ts_local   TEXT NOT NULL,
        day_local  TEXT NOT NULL,
        bucket     TEXT NOT NULL,
        project    TEXT NOT NULL,
        source     TEXT NOT NULL,
        ref        TEXT,
        author     TEXT,
        author_class TEXT DEFAULT 'owner',
        files      INTEGER DEFAULT 0,
        insertions INTEGER DEFAULT 0,
        deletions  INTEGER DEFAULT 0,
        model      TEXT,
        tok_in     INTEGER DEFAULT 0,
        tok_out    INTEGER DEFAULT 0,
        tok_cw     INTEGER DEFAULT 0,
        tok_cr     INTEGER DEFAULT 0,
        cost_usd   REAL DEFAULT 0.0
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        project    TEXT, day_local TEXT,
        start_local TEXT, end_local TEXT,
        minutes REAL, n_events INTEGER,
        min_business REAL, min_after_hours REAL,
        min_early_morning REAL, min_weekend REAL, min_holiday REAL
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS ledger (
        seq INTEGER PRIMARY KEY AUTOINCREMENT,
        day_local TEXT, payload TEXT,
        prev_hash TEXT, hash TEXT, created_at TEXT
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS excluded_authors (
        author TEXT PRIMARY KEY, commits INTEGER, repos TEXT
    )""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_ev_day ON events(day_local)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_ev_proj ON events(project)")
    con.commit()
    return con


def add_event(con, **kw):
    cols = ",".join(kw.keys())
    marks = ",".join("?" * len(kw))
    con.execute(f"INSERT OR IGNORE INTO events ({cols}) VALUES ({marks})",
                list(kw.values()))


# ----------------------------------------------------------------------------
# SOURCE 1: GIT
# ----------------------------------------------------------------------------

def find_repos():
    repos, seen = [], set()
    for root in REPO_ROOTS:
        if not root.exists():
            continue
        for git_dir in root.rglob(".git"):
            if git_dir.parent.name.startswith("."):
                continue
            repo = git_dir.parent
            rs = str(repo)
            if is_vendor(rs) or rs in seen:
                continue
            depth = len(repo.relative_to(root).parts)
            if depth > 3:
                continue
            seen.add(rs)
            repos.append(repo)
    return repos


def detect_identities(repos):
    """Discover the author identities belonging to the machine owner."""
    counts = defaultdict(int)
    for repo in repos:
        out = run_git(repo, ["log", "--all", "--format=%an <%ae>"])
        for line in out.splitlines():
            if line.strip():
                counts[line.strip()] += 1
    owner, agent, other = set(), set(), {}
    for ident, n in counts.items():
        low = ident.lower()
        is_agent = ("claude" in low or "anthropic" in low)
        is_owner = ("renne" in low or "rennesan" in low or "santiago" in low
                    or "qi@quiddityinnovations" in low)
        if is_agent:
            # Commits written by the AI agent while the owner was driving the
            # session. Counted as ACTIVITY (proves the machine was in use at
            # that timestamp) but reported separately from human AUTHORSHIP,
            # because they are not the owner's keystrokes.
            agent.add(ident)
        elif is_owner:
            owner.add(ident)
        else:
            other[ident] = n
    return owner, agent, other


def run_git(repo, args):
    try:
        r = subprocess.run(["git", "-C", str(repo)] + args,
                           capture_output=True, text=True, timeout=180,
                           encoding="utf-8", errors="replace")
        return r.stdout if r.returncode == 0 else ""
    except (subprocess.TimeoutExpired, OSError):
        return ""


def scan_git(con, seen_sha):
    repos = find_repos()
    log(f"git: scanning {len(repos)} repositories")
    owner, agent, other = detect_identities(repos)
    log(f"git: OWNER (human) identities  = {sorted(owner)}")
    log(f"git: AGENT identities (activity, not authorship) = {sorted(agent)}")
    if other:
        log(f"git: EXCLUDED non-owner authors = "
            f"{sorted(other.items(), key=lambda x: -x[1])[:10]}")
        for ident, n in other.items():
            con.execute("INSERT OR REPLACE INTO excluded_authors VALUES (?,?,?)",
                        (ident, n, ""))

    SEP, REC = "\x1f", "RECORD"
    added = 0
    for repo in repos:
        project = normalise_project(repo)
        fmt = f"{REC}{SEP}%H{SEP}%aI{SEP}%an <%ae>{SEP}%s"
        out = run_git(repo, ["log", "--all", "--no-merges",
                             f"--format={fmt}", "--numstat"])
        cur = None
        for line in out.splitlines():
            if line.startswith(REC + SEP):
                if cur:
                    added += commit_flush(con, cur, seen_sha, owner, agent,
                                          project)
                p = line.split(SEP)
                cur = {"sha": p[1], "ts": p[2], "author": p[3],
                       "subject": p[4] if len(p) > 4 else "",
                       "files": 0, "ins": 0, "dele": 0}
            elif cur and "\t" in line:
                a, d, _ = (line.split("\t") + ["", "", ""])[:3]
                cur["files"] += 1
                cur["ins"] += int(a) if a.isdigit() else 0
                cur["dele"] += int(d) if d.isdigit() else 0
        if cur:
            added += commit_flush(con, cur, seen_sha, owner, agent, project)
        con.commit()
    log(f"git: {added} unique commits recorded (owner + agent activity)")
    return added


def commit_flush(con, c, seen_sha, owner, agent, project):
    if c["sha"] in seen_sha:
        return 0
    if c["author"] in owner:
        cls = "owner"
    elif c["author"] in agent:
        cls = "agent"
    else:
        return 0
    seen_sha.add(c["sha"])
    try:
        dt = datetime.fromisoformat(c["ts"])       # carries original offset
    except ValueError:
        return 0
    loc = dt.astimezone(LOCAL_TZ)
    add_event(con,
              event_id="git:" + c["sha"],
              ts_utc=dt.astimezone(ZoneInfo("UTC")).isoformat(),
              ts_local=loc.isoformat(),
              day_local=loc.strftime("%Y-%m-%d"),
              bucket=classify_minute(loc),
              project=project, source="git", ref=c["sha"][:12],
              author=c["author"], author_class=cls, files=c["files"],
              insertions=c["ins"], deletions=c["dele"])
    return 1


# ----------------------------------------------------------------------------
# SOURCE 2: CLAUDE CODE TRANSCRIPTS  (times + tokens)
# ----------------------------------------------------------------------------

def scan_transcripts(con, since=None):
    if not CLAUDE_PROJECTS.exists():
        log("transcripts: directory not found -- skipped")
        return 0
    files = list(CLAUDE_PROJECTS.rglob("*.jsonl"))
    log(f"transcripts: scanning {len(files)} files")
    added = 0
    for fp in files:
        try:
            rel = fp.relative_to(CLAUDE_PROJECTS)
            project = normalise_project(rel.parts[0])
        except ValueError:
            project = "unknown"
        try:
            with open(fp, "r", encoding="utf-8", errors="replace") as fh:
                for i, line in enumerate(fh):
                    if '"timestamp"' not in line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    ts = rec.get("timestamp")
                    if not ts:
                        continue
                    try:
                        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    except ValueError:
                        continue
                    loc = dt.astimezone(LOCAL_TZ)
                    if since and loc.strftime("%Y-%m-%d") < since:
                        continue

                    msg = rec.get("message") or {}
                    usage = msg.get("usage") or {}
                    model = msg.get("model") or rec.get("model") or ""
                    ti = int(usage.get("input_tokens") or 0)
                    to = int(usage.get("output_tokens") or 0)
                    cw = int(usage.get("cache_creation_input_tokens") or 0)
                    cr = int(usage.get("cache_read_input_tokens") or 0)

                    # Keep token-bearing records and human turns; skip the rest
                    # so idle telemetry cannot inflate reconstructed sessions.
                    if not (ti or to or cw or cr):
                        if rec.get("type") not in ("user", "queue-operation"):
                            continue

                    pin, pout = price_for_model(model)
                    cost = ((ti * pin) + (to * pout)
                            + (cw * pin * CACHE_WRITE_MULT)
                            + (cr * pin * CACHE_READ_MULT)) / 1_000_000

                    eid = "cc:" + hashlib.sha256(
                        f"{fp.name}:{i}:{ts}".encode()).hexdigest()[:24]
                    add_event(con, event_id=eid,
                              ts_utc=dt.astimezone(ZoneInfo("UTC")).isoformat(),
                              ts_local=loc.isoformat(),
                              day_local=loc.strftime("%Y-%m-%d"),
                              bucket=classify_minute(loc),
                              project=project, source="claude_code",
                              ref=fp.stem[:12], author="renne",
                              model=model, tok_in=ti, tok_out=to,
                              tok_cw=cw, tok_cr=cr, cost_usd=cost)
                    added += 1
        except OSError:
            continue
        con.commit()
    log(f"transcripts: {added} events recorded")
    return added


# ----------------------------------------------------------------------------
# SOURCE 3: SESSION SUMMARY DOCUMENTS
# ----------------------------------------------------------------------------

def scan_summaries(con):
    if not SUMMARY_DIR.exists():
        log("summaries: directory not found -- skipped")
        return 0
    pat = re.compile(r"^(?P<proj>.+?)_Summary_(?P<d>\d{4}-\d{2}-\d{2})_"
                     r"(?P<hm>\d{4})\.docx$", re.I)
    added = 0
    for fp in SUMMARY_DIR.glob("*.docx"):
        m = pat.match(fp.name)
        if not m:
            continue
        try:
            loc = datetime.strptime(m["d"] + m["hm"], "%Y-%m-%d%H%M").replace(
                tzinfo=LOCAL_TZ)
        except ValueError:
            continue
        add_event(con,
                  event_id="doc:" + hashlib.sha256(
                      fp.name.encode()).hexdigest()[:24],
                  ts_utc=loc.astimezone(ZoneInfo("UTC")).isoformat(),
                  ts_local=loc.isoformat(),
                  day_local=loc.strftime("%Y-%m-%d"),
                  bucket=classify_minute(loc),
                  project=normalise_project(m["proj"]),
                  source="session_doc", ref=fp.name, author="renne")
        added += 1
    con.commit()
    log(f"summaries: {added} events recorded")
    return added


# ----------------------------------------------------------------------------
# SESSION RECONSTRUCTION  (minute-level bucketing)
# ----------------------------------------------------------------------------

def rebuild_sessions(con):
    con.execute("DELETE FROM sessions")
    rows = con.execute(
        "SELECT project, ts_local FROM events ORDER BY project, ts_local"
    ).fetchall()

    by_proj = defaultdict(list)
    for proj, ts in rows:
        by_proj[proj].append(datetime.fromisoformat(ts))

    n = 0
    for proj, times in by_proj.items():
        times.sort()
        group = []
        for t in times:
            if group and (t - group[-1]) > timedelta(minutes=IDLE_GAP_MIN):
                n += flush_session(con, proj, group)
                group = []
            group.append(t)
        if group:
            n += flush_session(con, proj, group)
    con.commit()
    log(f"sessions: {n} work sessions reconstructed")
    return n


def union_buckets(con, day=None, exclude=None):
    """True wall-clock hours, with concurrent work counted once.

    Sessions are reconstructed PER PROJECT, so a single hour spent moving
    between three projects produces three project-sessions covering the same
    wall-clock minutes. Summing them overstates elapsed time -- and can exceed
    the 9.5h business window in a day, which is self-evidently impossible.

    This merges every session interval into non-overlapping wall-clock spans
    before bucketing, so each real minute is counted exactly once.
    Per-project figures remain un-merged for attribution purposes; the two
    are reported side by side and the difference is concurrency.
    """
    sql = "SELECT start_local, end_local FROM sessions"
    where, params = [], []
    if day:
        where.append("day_local=?")
        params.append(day)
    if exclude:
        where.append("project NOT IN (%s)" % ",".join("?" * len(exclude)))
        params.extend(exclude)
    if where:
        sql += " WHERE " + " AND ".join(where)
    params = tuple(params)
    spans = [(datetime.fromisoformat(a), datetime.fromisoformat(b))
             for a, b in con.execute(sql + " ORDER BY start_local", params)]
    merged = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])

    mins = defaultdict(float)
    for s, e in merged:
        cur = s
        while cur < e:
            step = min(1.0, (e - cur).total_seconds() / 60.0)
            mins[classify_minute(cur)] += step
            cur += timedelta(minutes=step)
    mins["_total"] = sum(v for k, v in mins.items() if not k.startswith("_"))
    mins["_spans"] = len(merged)
    return mins


def flush_session(con, proj, times):
    start = times[0] - timedelta(minutes=LEAD_IN_MIN)
    end = times[-1]
    span = (end - start).total_seconds() / 60.0
    span = max(span, LEAD_IN_MIN)
    span = min(span, MAX_SESSION_HR * 60)
    end = start + timedelta(minutes=span)

    # Walk the session minute by minute so a session that straddles 17:30
    # (or midnight, or into Saturday) is split accurately rather than
    # attributed wholesale to whichever bucket it happened to begin in.
    mins = defaultdict(float)
    cur, remaining = start, span
    while remaining > 0:
        step = min(1.0, remaining)
        mins[classify_minute(cur)] += step
        cur += timedelta(minutes=step)
        remaining -= step

    sid = hashlib.sha256(
        f"{proj}|{start.isoformat()}|{end.isoformat()}".encode()).hexdigest()[:20]
    con.execute("INSERT OR REPLACE INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (sid, proj, start.strftime("%Y-%m-%d"),
                 start.isoformat(), end.isoformat(), span, len(times),
                 mins["business"], mins["after_hours"], mins["early_morning"],
                 mins["weekend"], mins["holiday"]))
    return 1


# ----------------------------------------------------------------------------
# HASH-CHAINED LEDGER
# ----------------------------------------------------------------------------

def append_ledger(con, day):
    row = con.execute(
        "SELECT hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
    prev = row[0] if row else "GENESIS"

    stats = con.execute("""
        SELECT project,
               SUM(minutes), SUM(min_business), SUM(min_after_hours),
               SUM(min_early_morning), SUM(min_weekend), SUM(min_holiday)
        FROM sessions WHERE day_local=? GROUP BY project""", (day,)).fetchall()
    toks = con.execute("""
        SELECT project, SUM(tok_in), SUM(tok_out), SUM(tok_cw), SUM(tok_cr),
               SUM(cost_usd), COUNT(*)
        FROM events WHERE day_local=? GROUP BY project""", (day,)).fetchall()

    payload = json.dumps({
        "day": day,
        "sessions": [dict(zip(
            ["project", "minutes", "business", "after_hours",
             "early_morning", "weekend", "holiday"], s)) for s in stats],
        "tokens": [dict(zip(
            ["project", "in", "out", "cache_write", "cache_read",
             "cost_usd", "events"], t)) for t in toks],
        "params": {"business_end": BUSINESS_END.strftime("%H:%M"),
                   "idle_gap_min": IDLE_GAP_MIN,
                   "lead_in_min": LEAD_IN_MIN, "tz": str(LOCAL_TZ)},
    }, sort_keys=True)

    seq = (con.execute("SELECT COALESCE(MAX(seq),0) FROM ledger").fetchone()[0]) + 1
    h = hashlib.sha256(f"{seq}|{day}|{payload}|{prev}".encode()).hexdigest()
    con.execute("INSERT INTO ledger (seq,day_local,payload,prev_hash,hash,created_at)"
                " VALUES (?,?,?,?,?,?)",
                (seq, day, payload, prev, h,
                 datetime.now(LOCAL_TZ).isoformat(timespec="seconds")))
    con.commit()
    return h


def verify_chain(con):
    rows = con.execute(
        "SELECT seq,day_local,payload,prev_hash,hash FROM ledger ORDER BY seq"
    ).fetchall()
    prev = "GENESIS"
    for seq, day, payload, ph, h in rows:
        if ph != prev:
            return False, f"seq {seq}: prev_hash mismatch"
        calc = hashlib.sha256(f"{seq}|{day}|{payload}|{ph}".encode()).hexdigest()
        if calc != h:
            return False, f"seq {seq}: payload altered after the fact"
        prev = h
    return True, f"chain intact across {len(rows)} entries"


# ----------------------------------------------------------------------------
# REPORTING
# ----------------------------------------------------------------------------

def report(con):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d_%H%M")

    per_project = con.execute("""
        SELECT project,
               SUM(minutes)/60.0, SUM(min_business)/60.0,
               SUM(min_after_hours)/60.0, SUM(min_early_morning)/60.0,
               SUM(min_weekend)/60.0, SUM(min_holiday)/60.0,
               COUNT(*), MIN(start_local), MAX(end_local)
        FROM sessions GROUP BY project ORDER BY SUM(minutes) DESC""").fetchall()

    # index map: 0 tok_in  1 tok_out  2 cache_w  3 cache_r  4 cost
    #            5 insertions  6 deletions  7 commits_owner  8 commits_agent
    tok = {r[0]: r[1:] for r in con.execute("""
        SELECT project, SUM(tok_in), SUM(tok_out), SUM(tok_cw), SUM(tok_cr),
               SUM(cost_usd), SUM(insertions), SUM(deletions),
               SUM(CASE WHEN source='git' AND author_class='owner'
                        THEN 1 ELSE 0 END),
               SUM(CASE WHEN source='git' AND author_class='agent'
                        THEN 1 ELSE 0 END)
        FROM events GROUP BY project""").fetchall()}
    EMPTY = (0,) * 9

    csv_path = REPORT_DIR / f"effort_by_project_{stamp}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["project", "governance", "total_hours", "business_hours",
                    "after_hours_hours", "early_morning_hours",
                    "weekend_hours", "holiday_hours", "off_hours_total",
                    "off_hours_pct", "sessions", "first_activity",
                    "last_activity", "commits_authored_by_owner",
                    "commits_by_ai_agent", "lines_added", "lines_removed",
                    "tokens_in", "tokens_out", "cache_write", "cache_read",
                    "api_list_cost_usd"])
        for (p, tot, bus, aft, em, wknd, hol, ns, first, last) in per_project:
            t = tok.get(p, EMPTY)
            off = (aft or 0) + (em or 0) + (wknd or 0) + (hol or 0)
            pct = (off / tot * 100) if tot else 0
            w.writerow([p, governance(p), f"{tot:.2f}", f"{bus:.2f}",
                        f"{aft:.2f}",
                        f"{em:.2f}", f"{wknd:.2f}", f"{hol:.2f}",
                        f"{off:.2f}", f"{pct:.1f}", ns, first, last,
                        t[7] or 0, t[8] or 0, t[5] or 0, t[6] or 0,
                        t[0] or 0, t[1] or 0, t[2] or 0, t[3] or 0,
                        f"{(t[4] or 0):.2f}"])

    ev_path = REPORT_DIR / f"raw_events_{stamp}.csv"
    with open(ev_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["ts_local", "day", "bucket", "project", "source", "ref",
                    "author", "author_class", "files", "insertions",
                    "deletions", "model", "tok_in", "tok_out", "cache_w",
                    "cache_r", "cost_usd"])
        for r in con.execute("""SELECT ts_local,day_local,bucket,project,source,
                ref,author,author_class,files,insertions,deletions,model,
                tok_in,tok_out,tok_cw,tok_cr,cost_usd
                FROM events ORDER BY ts_local"""):
            w.writerow(r)

    ok, msg = verify_chain(con)

    totals = con.execute("""SELECT SUM(minutes)/60.0, SUM(min_business)/60.0,
        SUM(min_after_hours)/60.0, SUM(min_early_morning)/60.0,
        SUM(min_weekend)/60.0, SUM(min_holiday)/60.0 FROM sessions""").fetchone()
    tk = con.execute("""SELECT SUM(tok_in), SUM(tok_out), SUM(tok_cw),
        SUM(tok_cr), SUM(cost_usd) FROM events""").fetchone()
    tt = (sum(x or 0 for x in tk[:4]), tk[4])

    print("\n" + "=" * 78)
    print("QI EFFORT LEDGER -- SUMMARY")
    print("=" * 78)
    print(f"Timezone          : {LOCAL_TZ}  (DST-aware)")
    print(f"After-hours line  : weekdays from {BUSINESS_END.strftime('%H:%M')}")
    print(f"Session model     : {IDLE_GAP_MIN}-min idle gap, "
          f"{LEAD_IN_MIN}-min lead-in, {MAX_SESSION_HR}h cap")
    print(f"Chain integrity   : {'OK' if ok else 'FAILED'} -- {msg}")
    print("-" * 78)
    u = union_buckets(con)
    ut = u["_total"] / 60.0
    uoff = (u["after_hours"] + u["early_morning"]
            + u["weekend"] + u["holiday"]) / 60.0
    print("ELAPSED WALL-CLOCK HOURS (concurrent work counted once) <-- headline")
    print(f"  TOTAL           : {ut:.1f}")
    print(f"  business        : {u['business'] / 60.0:.1f}")
    print(f"  after 17:30     : {u['after_hours'] / 60.0:.1f}")
    print(f"  early morning   : {u['early_morning'] / 60.0:.1f}")
    print(f"  weekend         : {u['weekend'] / 60.0:.1f}")
    print(f"  holiday         : {u['holiday'] / 60.0:.1f}")
    print(f"  OFF-HOURS TOTAL : {uoff:.1f}  ({uoff / ut * 100:.1f}%)")
    if totals and totals[0]:
        off = sum(x or 0 for x in totals[2:6])
        print("-" * 78)
        print("PER-PROJECT ATTRIBUTED HOURS (sums concurrent work; for "
              "attribution only)")
        print(f"  TOTAL           : {totals[0]:.1f}  "
              f"(= {totals[0] / ut:.2f}x elapsed; the excess is concurrency)")
        print(f"  business        : {totals[1] or 0:.1f}")
        print(f"  after 17:30     : {totals[2] or 0:.1f}")
        print(f"  weekend         : {totals[4] or 0:.1f}")
        print(f"  OFF-HOURS TOTAL : {off:.1f}  "
              f"({off / totals[0] * 100:.1f}%)")
    print("-" * 78)
    print("TOKENS -- broken out, because the gross figure misleads:")
    print(f"  generated (output)   : {tk[1] or 0:>16,}  <-- work produced")
    print(f"  prompt (input)       : {tk[0] or 0:>16,}")
    print(f"  cache write          : {tk[2] or 0:>16,}")
    print(f"  cache read (re-read) : {tk[3] or 0:>16,}  <-- NOT new work")
    print(f"  gross total          : {tt[0] or 0:>16,}")
    print(f"API list cost     : ${tt[1] or 0:,.2f}  (replacement cost, not paid)")
    print("-" * 78)
    print(f"{'PROJECT':<24}{'TOTAL':>8}{'BUS':>8}{'AFT':>8}"
          f"{'WKND':>8}{'OFF%':>7}{'COMMITS':>9}")
    for (p, tot, bus, aft, em, wknd, hol, ns, first, last) in per_project[:30]:
        t = tok.get(p, EMPTY)
        off = (aft or 0) + (em or 0) + (wknd or 0) + (hol or 0)
        print(f"{p[:23]:<24}{tot:>8.1f}{bus or 0:>8.1f}{aft or 0:>8.1f}"
              f"{wknd or 0:>8.1f}{(off / tot * 100) if tot else 0:>6.0f}%"
              f"{t[7] or 0:>9}")
    print("-" * 78)
    ac = con.execute("""SELECT author_class, COUNT(*) FROM events
                        WHERE source='git' GROUP BY author_class""").fetchall()
    print("AUTHORSHIP DISCLOSURE (git commits):")
    for cls, n in ac:
        label = ("committed by owner" if cls == "owner"
                 else "committed by AI agent during owner's session")
        print(f"  {n:>5}  {label}")
    print("  Both are counted as ACTIVITY evidence (the machine was in use at")
    print("  that timestamp). Only 'owner' rows evidence human authorship.")
    print("=" * 78)
    print(f"\nCSV  : {csv_path}\nRAW  : {ev_path}\n")
    return csv_path, ev_path


# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill", action="store_true")
    ap.add_argument("--daily", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()

    con = connect()

    if args.backfill:
        log("=== BACKFILL START ===")
        seen = {r[0][4:] for r in con.execute(
            "SELECT event_id FROM events WHERE source='git'")}
        scan_git(con, seen)
        scan_transcripts(con)
        scan_summaries(con)
        rebuild_sessions(con)
        for (d,) in con.execute(
                "SELECT DISTINCT day_local FROM sessions ORDER BY day_local"):
            append_ledger(con, d)
        log("=== BACKFILL COMPLETE ===")

    if args.daily:
        today = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
        log(f"=== DAILY RUN {today} ===")
        seen = {r[0][4:] for r in con.execute(
            "SELECT event_id FROM events WHERE source='git'")}
        scan_git(con, seen)
        scan_transcripts(con, since=(datetime.now(LOCAL_TZ)
                                     - timedelta(days=3)).strftime("%Y-%m-%d"))
        scan_summaries(con)
        rebuild_sessions(con)
        h = append_ledger(con, today)
        log(f"ledger entry sealed: {h[:16]}...")

    if args.verify:
        ok, msg = verify_chain(con)
        print(("OK   " if ok else "FAIL ") + msg)

    if args.report or args.backfill:
        report(con)

    con.close()


if __name__ == "__main__":
    main()

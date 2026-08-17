# -*- coding: utf-8 -*-
"""
secret_audit.py — QI ecosystem secret-leak & git-hygiene scanner.

For every QI git repo:
  1. Inspect the origin remote URL for embedded credentials (ghp_, pat, user:pass@).
  2. Scan the WORKING TREE for real secret values.
  3. Scan FULL GIT HISTORY (git log -p --all) for real secret values, recording
     whether a hit is still present at the tip or only buried in history.
  4. Record repo visibility (public/private) via `gh repo view` when available.

No credentials are rotated — that is the owner's step. This only reports.

Output:
  - JSON  -> C:\\QIH\\logs\\secret_audit\\audit_<run>.json
  - console summary table

Run:  python C:\\QIH\\tools\\secret_audit.py
"""
from __future__ import annotations
import json
import re
import subprocess
import sys
import os
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# (id, path) — authoritative list from qi_registry.json (git repos only)
REPOS = [
    ("maia",            r"C:\APPS\QI"),
    ("naya",            r"C:\APPS\NAYA"),
    ("nexus",           r"C:\APPS\NEXUS"),
    ("openclaw",        r"C:\APPS\OC"),
    ("mq",              r"C:\APPS\MQ"),
    ("easyflow",        r"C:\APPS\EasyFlow"),
    ("qi_hive",         r"C:\QIH"),
    ("autopdf",         r"C:\APPS\AutoPDF"),
    ("personalsong",    r"C:\APPS\PersonalSong"),
    ("m2v",             r"C:\APPS\M2V"),
    ("cognibase",       r"C:\APPS\CogniBase"),
    ("mapsnap",         r"C:\APPS\MapSnap"),
    ("cypherminer",     r"C:\APPS\CypherMiner"),
    ("lotterywiz",      r"C:\APPS\Lottery Wiz"),
    ("tubescout",       r"C:\APPS\TUBESCOUT"),
    ("avatarstudio",    r"C:\1-AI\APPS\AvatarStudio"),
    ("claude_manager",  r"C:\APPS\CLAUDE"),
]

OUT_DIR = Path(r"C:\QIH\logs\secret_audit")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# High-signal secret patterns. Each: (name, severity, compiled regex)
PATTERNS = [
    ("github_pat_classic", "CRITICAL", re.compile(r"ghp_[A-Za-z0-9]{36}")),
    ("github_pat_fine",    "CRITICAL", re.compile(r"github_pat_[A-Za-z0-9_]{60,}")),
    ("github_oauth",       "CRITICAL", re.compile(r"gh[ousr]_[A-Za-z0-9]{36}")),
    ("openai_key",         "CRITICAL", re.compile(r"sk-(?:proj-)?[A-Za-z0-9_\-]{20,}")),
    ("anthropic_key",      "CRITICAL", re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")),
    ("aws_access_key",     "CRITICAL", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("google_api_key",     "HIGH",     re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("slack_token",        "CRITICAL", re.compile(r"xox[baprs]-[0-9A-Za-z\-]{10,}")),
    ("slack_webhook",      "HIGH",     re.compile(r"hooks\.slack\.com/services/[A-Za-z0-9/]{20,}")),
    ("telegram_bot_token", "HIGH",     re.compile(r"\b\d{8,10}:[A-Za-z0-9_\-]{35}\b")),
    ("plex_token",         "HIGH",     re.compile(r"(?i)(?:x-plex-token|plex[_-]?token)['\"\s:=]+[A-Za-z0-9_\-]{18,}")),
    ("private_key",        "CRITICAL", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----")),
    ("jwt",                "MEDIUM",   re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}")),
    ("url_with_creds",     "HIGH",     re.compile(r"https?://[A-Za-z0-9._\-]+:[^/\s:@'\"]{6,}@[A-Za-z0-9.\-]+")),
    ("generic_secret",     "MEDIUM",   re.compile(
        r"(?i)(api[_-]?key|secret|client[_-]?secret|access[_-]?token|auth[_-]?token|"
        r"password|passwd|\bpwd\b)['\"\s]*[:=]\s*['\"][A-Za-z0-9_\-/+=.]{12,}['\"]")),
]

# Placeholder / obvious-non-secret markers that disqualify a generic match.
PLACEHOLDER = re.compile(
    r"(?i)(your[_-]?|xxx+|<[^>]+>|example|changeme|placeholder|dummy|sample|"
    r"replace[_-]?me|todo|fixme|none|null|true|false|enter[_-]?your|\.\.\.|"
    r"sk-\.\.\.|ghp_\.\.\.|test[_-]?key|fake|redacted|\*{4,})")

# Working-tree scan: skip these dirs and binary-ish extensions.
SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "env", "__pycache__",
             "models", "model", "checkpoints", "weights", "dist", "build",
             ".next", "site-packages", "chroma", "chroma_db", "vectorstore"}
BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".gz",
              ".tar", ".7z", ".exe", ".dll", ".so", ".bin", ".pyd", ".mp3",
              ".mp4", ".wav", ".flac", ".safetensors", ".ckpt", ".pt", ".pth",
              ".onnx", ".db", ".sqlite", ".woff", ".woff2", ".ttf", ".jar",
              ".class", ".pkl", ".npy", ".npz", ".webp", ".mov", ".avi"}

MAX_HISTORY_BYTES = 250 * 1024 * 1024  # cap git log -p stream


def git(repo: str, *args: str, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", repo, *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace",
                          timeout=kw.get("timeout", 600))


def disqualify(line: str, match: str, pat_name: str) -> bool:
    """Filter obvious false positives for the looser patterns."""
    if pat_name in ("generic_secret", "jwt"):
        if PLACEHOLDER.search(match):
            return True
    if PLACEHOLDER.search(match):
        return True
    return False


def scan_text(text: str, source: str, where: str):
    hits = []
    for ln_no, line in enumerate(text.splitlines(), 1):
        if len(line) > 4000:
            line = line[:4000]
        for name, sev, rx in PATTERNS:
            for m in rx.finditer(line):
                val = m.group(0)
                if disqualify(line, val, name):
                    continue
                hits.append({
                    "pattern": name, "severity": sev, "where": where,
                    "source": source, "line": ln_no,
                    "match": val[:80], "context": line.strip()[:160],
                })
    return hits


def scan_worktree(repo: str):
    hits = []
    root = Path(repo)
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            ext = Path(fn).suffix.lower()
            if ext in BINARY_EXT:
                continue
            fp = Path(dirpath) / fn
            try:
                if fp.stat().st_size > 5 * 1024 * 1024:
                    continue
                text = fp.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            rel = str(fp.relative_to(root))
            hits.extend(scan_text(text, rel, "worktree"))
    return hits


def scan_history(repo: str):
    """Stream `git log -p --all` and regex added/context lines."""
    hits = []
    proc = subprocess.Popen(
        ["git", "-C", repo, "log", "-p", "--all", "--no-color",
         "--format=COMMIT:%H %ad", "--date=short"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, encoding="utf-8", errors="replace", bufsize=1 << 20)
    cur_commit = "?"
    read = 0
    seen = set()
    assert proc.stdout is not None
    for line in proc.stdout:
        read += len(line)
        if read > MAX_HISTORY_BYTES:
            proc.kill()
            hits.append({"pattern": "_truncated", "severity": "INFO",
                         "where": "history", "source": "(stream cap reached)",
                         "line": 0, "match": "", "context": ""})
            break
        if line.startswith("COMMIT:"):
            cur_commit = line[7:].strip()
            continue
        if not (line.startswith("+") or line.startswith("-")):
            continue
        payload = line[1:]
        for name, sev, rx in PATTERNS:
            for m in rx.finditer(payload):
                val = m.group(0)
                if disqualify(payload, val, name):
                    continue
                key = (name, val)
                if key in seen:
                    continue
                seen.add(key)
                hits.append({
                    "pattern": name, "severity": sev, "where": "history",
                    "source": cur_commit, "line": 0,
                    "match": val[:80], "context": payload.strip()[:160],
                })
    try:
        proc.wait(timeout=10)
    except Exception:
        proc.kill()
    return hits


def repo_visibility(repo: str, remote: str):
    if not remote:
        return "no-remote"
    try:
        r = subprocess.run(["gh", "repo", "view", "--json", "visibility",
                            "-q", ".visibility"], cwd=repo,
                           capture_output=True, text=True, timeout=30)
        v = (r.stdout or "").strip()
        return v.lower() if v else "unknown"
    except Exception:
        return "unknown"


def audit_repo(rid: str, path: str):
    rec = {"id": rid, "path": path, "remote": "", "remote_has_creds": False,
           "visibility": "unknown", "worktree_hits": [], "history_hits": [],
           "error": None}
    if not Path(path, ".git").exists():
        rec["error"] = "not a git repo"
        return rec
    remote = git(path, "remote", "get-url", "origin").stdout.strip()
    rec["remote"] = re.sub(r"(:)([^/@:]{4})[^/@:]+(@)", r"\1\2***\3", remote)  # mask
    rec["remote_has_creds"] = bool(re.search(r"https?://[^/\s]+:[^/\s@]+@", remote)
                                   or "ghp_" in remote or "github_pat_" in remote)
    rec["visibility"] = repo_visibility(path, remote)
    print(f"  scanning {rid} ({path}) ...", flush=True)
    rec["worktree_hits"] = scan_worktree(path)
    rec["history_hits"] = scan_history(path)
    return rec


def main():
    results = []
    print("=== QI ecosystem secret audit ===", flush=True)
    for rid, path in REPOS:
        results.append(audit_repo(rid, path))

    out = OUT_DIR / "audit_latest.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print("\n=== SUMMARY ===")
    print(f"{'repo':16} {'vis':9} {'remoteCreds':11} {'wt':>4} {'hist':>5}")
    for r in results:
        wt = len([h for h in r["worktree_hits"] if h["pattern"] != "_truncated"])
        hi = len([h for h in r["history_hits"] if h["pattern"] != "_truncated"])
        err = f"  ERR:{r['error']}" if r["error"] else ""
        print(f"{r['id']:16} {r['visibility']:9} "
              f"{str(r['remote_has_creds']):11} {wt:>4} {hi:>5}{err}")

    # Detail of every non-generic / high-sev hit
    print("\n=== NOTABLE HITS (CRITICAL/HIGH) ===")
    for r in results:
        for h in r["worktree_hits"] + r["history_hits"]:
            if h["severity"] in ("CRITICAL", "HIGH"):
                print(f"[{h['severity']:8}] {r['id']:14} {h['where']:8} "
                      f"{h['pattern']:18} {h['source'][:40]:40} :: {h['match']}")
    print(f"\nJSON written: {out}")


if __name__ == "__main__":
    main()

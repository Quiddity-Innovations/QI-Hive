# -*- coding: utf-8 -*-
"""
secret_gate.py — pre-push secret gate for QI nightly sync scripts.

Importable guard that scans what git is ABOUT to commit/push (the staged diff)
for real secret values. Returns the list of findings; the caller aborts the
commit/push if the list is non-empty.

Usage in a sync script:
    from secret_gate import scan_staged
    findings = scan_staged(repo_path)
    if findings:
        log("ABORT: staged secret(s) detected: " + "; ".join(f["match"] for f in findings))
        return   # do NOT commit/push

Shares the same pattern set philosophy as secret_audit.py but operates only on
the staged diff so it is fast enough to run on every nightly sync.
"""
from __future__ import annotations
import re
import subprocess

PATTERNS = [
    ("github_pat_classic", re.compile(r"ghp_[A-Za-z0-9]{36}")),
    ("github_pat_fine",    re.compile(r"github_pat_[A-Za-z0-9_]{60,}")),
    ("github_oauth",       re.compile(r"gh[ousr]_[A-Za-z0-9]{36}")),
    ("openai_key",         re.compile(r"sk-(?:proj-)?[A-Za-z0-9_\-]{20,}")),
    ("anthropic_key",      re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")),
    ("aws_access_key",     re.compile(r"AKIA[0-9A-Z]{16}")),
    ("google_api_key",     re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("slack_token",        re.compile(r"xox[baprs]-[0-9A-Za-z\-]{10,}")),
    ("telegram_bot_token", re.compile(r"\b\d{8,10}:[A-Za-z0-9_\-]{35}\b")),
    ("plex_token",         re.compile(r"(?i)plex[_-]?token['\"\s:=]+[A-Za-z0-9_\-]{18,}")),
    ("private_key",        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----")),
    ("url_with_creds",     re.compile(r"https?://[A-Za-z0-9._\-]+:[^/\s:@'\"]{6,}@[A-Za-z0-9.\-]+")),
    ("generic_secret",     re.compile(
        r"(?i)(api[_-]?key|secret|client[_-]?secret|access[_-]?token|auth[_-]?token|"
        r"password|passwd|\bpwd\b)['\"\s]*[:=]\s*['\"][A-Za-z0-9_\-/+=.]{12,}['\"]")),
]

PLACEHOLDER = re.compile(
    r"(?i)(your[_-]?|xxx+|<[^>]+>|example|changeme|placeholder|dummy|sample|"
    r"replace[_-]?me|todo|fixme|none|null|true|false|enter[_-]?your|\.\.\.|"
    r"test[_-]?key|fake|redacted|\*{4,})")


def scan_staged(repo: str):
    """Scan the staged diff (git diff --cached) for secret values."""
    diff = subprocess.run(
        ["git", "-C", repo, "diff", "--cached", "--no-color", "-U0"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=120).stdout
    return _scan_diff(diff)


def scan_range(repo: str, rev_range: str):
    """Scan an arbitrary diff range, e.g. 'origin/main..HEAD', before a push."""
    diff = subprocess.run(
        ["git", "-C", repo, "diff", "--no-color", "-U0", rev_range],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=120).stdout
    return _scan_diff(diff)


def _scan_diff(diff: str):
    findings = []
    for line in diff.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        payload = line[1:]
        for name, rx in PATTERNS:
            for m in rx.finditer(payload):
                val = m.group(0)
                if PLACEHOLDER.search(val):
                    continue
                findings.append({"pattern": name, "match": val[:80],
                                 "line": payload.strip()[:160]})
    return findings


if __name__ == "__main__":
    import sys
    repo = sys.argv[1] if len(sys.argv) > 1 else "."
    hits = scan_staged(repo)
    if hits:
        print(f"BLOCKED: {len(hits)} secret(s) in staged diff:")
        for h in hits:
            print(f"  [{h['pattern']}] {h['match']}")
        sys.exit(1)
    print("OK: no secrets in staged diff")
    sys.exit(0)

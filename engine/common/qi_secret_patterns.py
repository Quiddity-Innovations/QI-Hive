# -*- coding: utf-8 -*-
"""
qi_secret_patterns — the ONE list of secret-detection patterns for QI Hive.

Two tiers, because they answer different questions:

  TOKEN_SHAPES     precise credential shapes ("this IS a key"). Kept as plain
                   POSIX-ERE strings so they work unchanged with `git grep -E`
                   (no \\b, \\d, (?:...), lookarounds). Case-sensitive.
                   Consumer: inspector.check_secrets_in_source (nightly deep scan).
  TOKEN_SHAPES_RE  the same shapes, compiled for Python callers.

  REDACTION_HINTS  broader "this line might carry a secret" hints, IGNORECASE,
                   deliberately over-matching (a false positive costs a re-run,
                   a false negative leaks). Consumers: qi_handoff.scan_secrets
                   (exported there as SECRET_PATTERNS), qi_trinity_onboarding
                   (nightly ONBOARDING.md via QI_NightlyReconcile), QI Decide guard.

Consolidated 2026-09-22: the two lists had drifted apart, and qi_handoff's
`sk-[A-Za-z0-9]{20,}` missed modern Anthropic/OpenAI keys (`sk-ant-api03-...`,
`sk-proj-...`) because a hyphen follows the prefix. The hyphen is only allowed
after a known prefix: a bare `sk-[A-Za-z0-9_-]{20,}` would also fire on prose
like "task-scheduler-window-policy" and over-redact the onboarding briefs.

Standard library only. Self-check: python qi_secret_patterns.py
"""
from __future__ import annotations

import re

# (name, ERE pattern, human label) — ERE-compatible, see module docstring.
TOKEN_SHAPES = [
    ("telegram_bot_token", r"[0-9]{8,10}:AA[A-Za-z0-9_-]{30,}", "Telegram bot token"),
    ("anthropic_key",      r"sk-ant-[A-Za-z0-9_-]{20,}",        "Anthropic API key"),
    ("openai_project_key", r"sk-proj-[A-Za-z0-9_-]{20,}",       "OpenAI API key"),
    ("google_api_key",     r"AIza[0-9A-Za-z_-]{30,}",           "Google API key"),
    ("meta_token",         r"EAA[A-Za-z0-9]{60,}",              "Meta page/access token"),
    ("github_token",       r"gh[ops]_[A-Za-z0-9]{30,}",         "GitHub token"),
]

TOKEN_SHAPES_RE = [(name, re.compile(ere), label) for name, ere, label in TOKEN_SHAPES]

# (name, compiled regex) — names are part of the contract: qi_handoff prints
# them and QI Decide logs them as "hint:<name>". Non-capturing groups only,
# so re.findall() still returns one whole match per hit.
REDACTION_HINTS = [
    ("api_key", re.compile(r"api[_-]?key", re.IGNORECASE)),
    ("sk_key", re.compile(
        r"sk-(?:[A-Za-z0-9]{20,}|(?:ant|proj|svcacct|admin)-[A-Za-z0-9_-]{20,})",
        re.IGNORECASE)),
    ("google_key", re.compile(r"AIza[0-9A-Za-z_-]{30,}", re.IGNORECASE)),
    ("github_token", re.compile(r"ghp_[A-Za-z0-9]{30,}", re.IGNORECASE)),
    ("bearer", re.compile(r"Bearer [A-Za-z0-9._-]{20,}", re.IGNORECASE)),
    ("client_secret", re.compile(r"client_secret", re.IGNORECASE)),
    ("token_json", re.compile(r"token_[a-z]+\.json", re.IGNORECASE)),
    ("secrets_path", re.compile(r"secrets\\", re.IGNORECASE)),
]

# Constructs Python accepts but POSIX ERE (git grep -E) does not.
_NON_ERE = re.compile(r"\\[bBdDsSwW]|\(\?|\\[AZz]")


def _self_check() -> list[str]:
    problems = []
    for name, ere, _label in TOKEN_SHAPES:
        if _NON_ERE.search(ere):
            problems.append(f"TOKEN_SHAPES[{name}] is not ERE-compatible: {ere}")
    for name, rx in REDACTION_HINTS:
        if rx.groups:
            problems.append(f"REDACTION_HINTS[{name}] has capturing groups (breaks findall counts)")
    return problems


if __name__ == "__main__":
    import sys
    issues = _self_check()
    for msg in issues:
        print("FAIL", msg)
    print("ok" if not issues else f"{len(issues)} problem(s)")
    sys.exit(1 if issues else 0)

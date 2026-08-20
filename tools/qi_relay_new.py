#!/usr/bin/env python3
"""
QI Relay - compose an outbound message with a valid envelope.

So that no Claude session (or human) ever hand-writes frontmatter and gets it subtly
wrong. Writes to outbox/<self>/ (or _drafts/ with --draft, which is the L2 default for
anything generated automatically).

Examples:
    python qi_relay_new.py --to urcil --project onbase-dna --type status \\
        --body "## What changed\\n- Baseline decoder shipped"

    echo "## What I need from you\\n- Confirm the doctype list" | \\
        python qi_relay_new.py --to urcil --project onbase-dna --type question --reply

    python qi_relay_new.py --to urcil --project onbase-dna --type ack \\
        --reply-to msg_20260818T1830Z_a1b2 --body-file reply.md --draft
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

RELAY_ROOT = Path(os.environ.get("QI_RELAY_ROOT", r"C:\QI-RELAY"))
SELF_PEER = os.environ.get("QI_RELAY_PEER", "renne")

KNOWN_TYPES = ["status", "fyi", "question", "request", "decision", "handoff", "ack", "blocked"]

# Cheap tripwire for PROTOCOL.md 7.5 - secrets must never enter a repo every peer reads.
SECRET_PATTERNS = [
    (re.compile(r"\b(?:sk|pk|ghp|gho|github_pat)_[A-Za-z0-9_]{16,}"), "API key / token literal"),
    (re.compile(r"(?i)\b(password|passwd|api[_-]?key|secret|bearer)\s*[:=]\s*\S+"), "credential assignment"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key block"),
    (re.compile(r"(?i)\b(?:mongodb|postgres(?:ql)?|mysql|redis)://[^\s:]+:[^\s@]+@"), "connection string with password"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Compose a QI Relay message")
    ap.add_argument("--to", required=True, help="peer_id or 'all'")
    ap.add_argument("--project", required=True)
    ap.add_argument("--type", required=True, choices=KNOWN_TYPES)
    ap.add_argument("--body", help="message body (markdown)")
    ap.add_argument("--body-file", help="read body from a file; '-' for stdin")
    ap.add_argument("--reply", action="store_true", help="set requires_reply: true")
    ap.add_argument("--reply-to", help="id of the message this answers")
    ap.add_argument("--priority", default="normal", choices=["low", "normal", "high"])
    ap.add_argument("--via", default="claude-code",
                    choices=["claude-code", "web", "cowork", "email-bridge"])
    ap.add_argument("--from", dest="sender", default=SELF_PEER)
    ap.add_argument("--draft", action="store_true",
                    help="write to _drafts/ (unapproved; never read by peers)")
    ap.add_argument("--force", action="store_true", help="bypass the secret scan")
    args = ap.parse_args()

    # body
    if args.body_file == "-":
        body = sys.stdin.read()
    elif args.body_file:
        body = Path(args.body_file).read_text(encoding="utf-8")
    elif args.body:
        body = args.body.replace("\\n", "\n")
    else:
        body = sys.stdin.read()
    body = body.strip()
    if not body:
        print("[FATAL] empty body", file=sys.stderr)
        return 1

    peers_cfg = json.loads((RELAY_ROOT / "peers.json").read_text(encoding="utf-8"))
    peers = peers_cfg["peers"]
    if args.sender not in peers:
        print(f"[FATAL] unknown sender {args.sender!r}", file=sys.stderr)
        return 1
    if args.to != "all" and args.to not in peers:
        print(f"[FATAL] unknown recipient {args.to!r} (known: {list(peers)})", file=sys.stderr)
        return 1

    # Soft project scoping. Peers scoped to "*" accept anything; once the shared project
    # list is narrowed in peers.json this starts catching messages sent to the wrong person.
    scope = peers[args.to].get("projects", ["*"]) if args.to != "all" else ["*"]
    if "*" not in scope and args.project not in scope:
        print(f"[WARN] {args.to} is not scoped to project {args.project!r} (scoped to: {scope}). "
              "Sending anyway — narrow or widen peers.json if this is wrong.", file=sys.stderr)

    # PROTOCOL.md 7.5
    for pattern, label in SECRET_PATTERNS:
        if pattern.search(body):
            msg = f"[BLOCKED] body looks like it contains a {label}. Link to the location instead."
            if not args.force:
                print(msg + " Use --force to override.", file=sys.stderr)
                return 1
            print(msg + " (--force given, proceeding)", file=sys.stderr)

    # PROTOCOL.md 6 - transcription is not authority
    if args.via == "email-bridge" and args.type == "decision":
        print("[FATAL] an email-bridge message may not carry type 'decision' (PROTOCOL.md §6).",
              file=sys.stderr)
        return 1

    words = len(body.split())
    limit = peers_cfg.get("config", {}).get("max_message_words", 400)
    if words > limit:
        print(f"[WARN] body is {words} words (guideline {limit}) — link to docs instead of pasting.",
              file=sys.stderr)

    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%MZ")
    short = uuid.uuid4().hex[:4]
    msg_id = f"msg_{stamp}_{short}"

    fm = [
        "---",
        f"id: {msg_id}",
        f"from: {args.sender}",
        f"to: {args.to}",
        f"project: {args.project}",
        f"type: {args.type}",
        f"requires_reply: {'true' if args.reply else 'false'}",
    ]
    if args.reply_to:
        fm.append(f"reply_to: {args.reply_to}")
    fm += [
        f"priority: {args.priority}",
        f"created: {now.isoformat(timespec='seconds')}",
        f"via: {args.via}",
        "---",
        "",
    ]

    safe_project = re.sub(r"[^A-Za-z0-9._-]", "-", args.project)
    name = f"{stamp}__{safe_project}__{args.type}__{short}.md"
    dest = RELAY_ROOT / "outbox" / args.sender / ("_drafts" if args.draft else "") / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(fm) + body + "\n", encoding="utf-8")

    state = "DRAFT (not visible to peers until approved)" if args.draft else "QUEUED (ships next sync)"
    print(f"{state}\n  id:   {msg_id}\n  file: {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

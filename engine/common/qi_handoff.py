"""
QI Handoff — plain-file packet exchange for app-only assistant features
(ChatGPT Deep Research/voice/Custom GPTs, Gemini Workspace/Gems/NotebookLM)
where no MCP tool exists yet. Phase 0 of
C:\\QIH\\shared\\documentation\\plans\\QI_TriPlatform_AI_Orchestration_Plan_2026-09-08.md

Python 3.11, stdlib only.

Subcommands:
  new     --to chatgpt|gemini --title "..." [--body file.md]
  redact  <file or ->
  ingest  <RETURN file or ->
  list
"""

import argparse
import csv
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HANDOFF_DIR = Path(r"C:\QIH\shared\handoff")
OUTBOX = HANDOFF_DIR / "outbox"
INBOX = HANDOFF_DIR / "inbox"
ARCHIVE = HANDOFF_DIR / "archive"
LEDGER = HANDOFF_DIR / "ledger.csv"

# Conservative secret redactor — false positive costs a re-run, false
# negative costs a leaked key, so every pattern below runs case-insensitive
# even where the real-world prefix is fixed-case (AIza, ghp_, sk-).
SECRET_PATTERNS = [
    ("api_key", re.compile(r"api[_-]?key", re.IGNORECASE)),
    ("sk_key", re.compile(r"sk-[A-Za-z0-9]{20,}", re.IGNORECASE)),
    ("google_key", re.compile(r"AIza[0-9A-Za-z_-]{30,}", re.IGNORECASE)),
    ("github_token", re.compile(r"ghp_[A-Za-z0-9]{30,}", re.IGNORECASE)),
    ("bearer", re.compile(r"Bearer [A-Za-z0-9._-]{20,}", re.IGNORECASE)),
    ("client_secret", re.compile(r"client_secret", re.IGNORECASE)),
    ("token_json", re.compile(r"token_[a-z]+\.json", re.IGNORECASE)),
    ("secrets_path", re.compile(r"secrets\\", re.IGNORECASE)),
]

ID_RE = r"\d{8}-\d{3}"
HANDOFF_NAME_RE = re.compile(rf"HANDOFF-({ID_RE})-([A-Za-z0-9]+)\.md")
RETURN_NAME_RE = re.compile(rf"RETURN-({ID_RE})-([A-Za-z0-9]+)")


def scan_secrets(text: str):
    """Return [(line_no, pattern_name), ...] for every secret-pattern hit."""
    hits = []
    for i, line in enumerate(text.splitlines(), start=1):
        for name, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                hits.append((i, name))
    return hits


def parse_front_matter(text: str):
    """Minimal YAML-front-matter reader (stdlib only, no PyYAML dependency).
    Handles simple scalars and one level of `- ` list items."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = {}
    current_list_key = None
    for line in parts[1].splitlines():
        stripped = line.rstrip()
        if not stripped.strip():
            continue
        if stripped.startswith("  - ") and current_list_key:
            meta.setdefault(current_list_key, []).append(stripped.strip()[2:].strip())
            continue
        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.split(" #")[0].strip()
            if val == "":
                current_list_key = key
                meta[key] = []
            else:
                current_list_key = None
                meta[key] = val
    body = parts[2].lstrip("\n")
    return meta, body


def build_packet(to: str, title: str, body_text: str | None) -> str:
    created_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    front = (
        "---\n"
        "from: claude\n"
        f"to: {to}\n"
        f"created: {created_iso}\n"
        "task_type: general\n"
        "inputs:\n"
        "  - (none)\n"
        f"expected_output: {title}\n"
        f"return_path: {INBOX}\\\n"
        "redacted: true\n"
        "---\n"
    )
    if body_text:
        sections = body_text
    else:
        sections = (
            "## Goal\n\n"
            f"{title}\n\n"
            "## Context\n\n\n\n"
            "## Constraints\n\n\n\n"
            "## Acceptance\n\n"
        )
    return front + "\n" + sections


def next_number(date_str: str) -> int:
    pattern = re.compile(rf"(?:HANDOFF|RETURN)-{date_str}-(\d{{3}})-")
    nums = [0]
    for folder in (OUTBOX, INBOX, ARCHIVE):
        for f in folder.glob("*.md"):
            m = pattern.match(f.name)
            if m:
                nums.append(int(m.group(1)))
    return max(nums) + 1


def copy_to_clipboard(text: str):
    try:
        subprocess.run(["clip.exe"], input=text.encode("utf-8"), check=True)
    except Exception as exc:
        print(f"(clipboard copy failed: {exc})", file=sys.stderr)


def open_packets():
    """Outbox packets that have no matching RETURN-<id>-* in inbox yet."""
    inbox_ids = set()
    for f in INBOX.glob("RETURN-*.md"):
        m = RETURN_NAME_RE.match(f.name)
        if m:
            inbox_ids.add(m.group(1))
    result = []
    for f in sorted(OUTBOX.glob("HANDOFF-*.md")):
        m = HANDOFF_NAME_RE.match(f.name)
        if not m:
            continue
        pid, to = m.groups()
        if pid not in inbox_ids:
            result.append((pid, to, f))
    return sorted(result, key=lambda t: t[0])


def cmd_new(args):
    date_str = datetime.now().strftime("%Y%m%d")
    n = next_number(date_str)
    packet_id = f"{date_str}-{n:03d}"
    filename = f"HANDOFF-{packet_id}-{args.to}.md"
    path = OUTBOX / filename

    body_text = None
    if args.body:
        body_text = Path(args.body).read_text(encoding="utf-8")

    packet_text = build_packet(args.to, args.title, body_text)

    hits = scan_secrets(packet_text)
    if hits:
        print("REDACTION FAILED — packet NOT written. Secret patterns found:")
        for line_no, name in hits:
            print(f"  line {line_no}: {name}")
        sys.exit(1)

    path.write_text(packet_text, encoding="utf-8")
    copy_to_clipboard(packet_text)
    print(str(path))


def cmd_redact(args):
    if args.file == "-":
        text = sys.stdin.read()
        label = "<stdin>"
    else:
        text = Path(args.file).read_text(encoding="utf-8")
        label = args.file

    hits = scan_secrets(text)
    if hits:
        print(f"REDACTION HIT in {label}:")
        for line_no, name in hits:
            print(f"  line {line_no}: {name}")
        sys.exit(1)

    print(f"clean: {label}")


def cmd_ingest(args):
    if args.file == "-":
        content = sys.stdin.read()
        src_name = None
    else:
        p = Path(args.file)
        content = p.read_text(encoding="utf-8")
        src_name = p.name

    m = RETURN_NAME_RE.match(src_name) if src_name else None
    if m:
        packet_id, from_vendor = m.groups()
    else:
        opens = open_packets()
        if not opens:
            print("No open packets to match this return against.")
            sys.exit(1)
        packet_id, from_vendor, _ = opens[0]

    outbox_match = list(OUTBOX.glob(f"HANDOFF-{packet_id}-*.md"))
    if outbox_match:
        fm, _ = parse_front_matter(outbox_match[0].read_text(encoding="utf-8"))
        to_val = fm.get("to", from_vendor)
        title = fm.get("expected_output", "")
        created = fm.get("created", "")
    else:
        to_val, title, created = from_vendor, "", ""

    dest_path = INBOX / f"RETURN-{packet_id}-{from_vendor}.md"
    dest_path.write_text(content, encoding="utf-8")

    returned_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    ledger_exists = LEDGER.exists()
    with open(LEDGER, "a", newline="", encoding="utf-8") as lf:
        writer = csv.writer(lf)
        if not ledger_exists:
            writer.writerow(["id", "to", "title", "created", "returned", "chars"])
        writer.writerow([packet_id, to_val, title, created, returned_iso, len(content)])

    print(str(dest_path))


def cmd_list(args):
    opens = open_packets()
    if not opens:
        print("No open packets.")
        return
    print(f"{'ID':<14} {'TO':<10} TITLE")
    for pid, to, f in opens:
        fm, _ = parse_front_matter(f.read_text(encoding="utf-8"))
        title = fm.get("expected_output", "")
        print(f"{pid:<14} {to:<10} {title}")


def main():
    parser = argparse.ArgumentParser(description="QI Handoff packet manager")
    sub = parser.add_subparsers(dest="command", required=True)

    p_new = sub.add_parser("new", help="create a packet in outbox")
    p_new.add_argument("--to", required=True, choices=["chatgpt", "gemini"])
    p_new.add_argument("--title", required=True)
    p_new.add_argument("--body", help="path to a Markdown body to insert")
    p_new.set_defaults(func=cmd_new)

    p_redact = sub.add_parser("redact", help="scan a file for secret patterns")
    p_redact.add_argument("file", help="file path or - for stdin")
    p_redact.set_defaults(func=cmd_redact)

    p_ingest = sub.add_parser("ingest", help="store a RETURN into inbox + ledger")
    p_ingest.add_argument("file", help="RETURN file path or - for stdin")
    p_ingest.set_defaults(func=cmd_ingest)

    p_list = sub.add_parser("list", help="show open packets awaiting return")
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

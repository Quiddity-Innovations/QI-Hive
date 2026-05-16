#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QI Hive — emergency bot-message purge for Telegram.

Deletes Tasuke + Kaze (and optionally Maia + Naya) messages from a given chat
by calling Telegram Bot API deleteMessage with each bot's own token. Bots can
delete their own messages within 48h without admin privileges.

Usage (via .bat wrapper):
  emergency-purge.bat <chat_id> <start_msg_id> <end_msg_id>
  emergency-purge.bat <chat_id> --ids 904 918 941 945

Examples:
  emergency-purge.bat -5161268852 900 1000
  emergency-purge.bat -1003942950097 1 100

Notes:
  * Tries every (token, message_id) pair. Whichever bot owns the msg succeeds;
    the others return "message can't be deleted" / "message not found" — ignored.
  * Basic-group + supergroup both supported by Bot API.
  * Read-only on disk. Writes nothing.
"""
import argparse
import json
import pathlib
import sqlite3
import sys
import time
import urllib.request
import urllib.error

# Token sources — paths inside WSL. Run this script via WSL python.
TOKEN_FILES = [
    ("Tasuke", pathlib.Path.home() / ".openclaw" / "openclaw.json"),
    ("Kaze",   pathlib.Path.home() / ".openclaw-kaze" / "openclaw.json"),
]
MAIA_DB = pathlib.Path("/mnt/c/QI/maia.db")
MAIA_DB_KEYS = [
    ("Maia",   "channel.telegram_token"),
    ("Naya",   "naya.telegram_token"),
    ("Tasuke", "tasuke.telegram_token"),
    ("Kaze",   "kaze.telegram_token"),
]

def extract_telegram_token(jsonpath: pathlib.Path):
    """Pull the first botToken value from an openclaw.json."""
    if not jsonpath.exists():
        return None
    try:
        cfg = json.loads(jsonpath.read_text(encoding="utf-8"))
    except Exception:
        return None
    # Walk nested structure looking for "botToken"
    found = []
    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "botToken" and isinstance(v, str) and ":" in v:
                    found.append(v)
                else:
                    walk(v)
        elif isinstance(obj, list):
            for x in obj: walk(x)
    walk(cfg)
    return found[0] if found else None

def delete_msg(token: str, chat_id: int, message_id: int, timeout: float = 5.0):
    """Call Telegram deleteMessage. Returns (ok, description)."""
    url = f"https://api.telegram.org/bot{token}/deleteMessage"
    data = json.dumps({"chat_id": chat_id, "message_id": message_id}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body.get("ok", False), body.get("description", "")
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8"))
            return False, body.get("description", str(e))
        except Exception:
            return False, str(e)
    except Exception as e:
        return False, str(e)

def main():
    p = argparse.ArgumentParser(description="Emergency Telegram message purge for QI bots.")
    p.add_argument("chat_id", type=int, help="Target chat_id (e.g. -5161268852)")
    p.add_argument("start", type=int, nargs="?", help="First message_id in range")
    p.add_argument("end", type=int, nargs="?", help="Last message_id in range (inclusive)")
    p.add_argument("--ids", type=int, nargs="+", help="Explicit message_id list (alternative to range)")
    p.add_argument("--dry-run", action="store_true", help="Print plan, don't call API")
    p.add_argument("--sleep-ms", type=int, default=80, help="Sleep between API calls (ms)")
    args = p.parse_args()

    if args.ids:
        ids = sorted(set(args.ids))
    elif args.start is not None and args.end is not None:
        lo, hi = sorted((args.start, args.end))
        ids = list(range(lo, hi + 1))
    else:
        p.error("provide either start+end or --ids")

    tokens = []
    seen = set()
    def add(label, tok, source):
        if not tok or tok in seen:
            return
        seen.add(tok)
        tokens.append((label, tok))
        print(f"  loaded token: {label:8} ({tok[:10]}...)  [{source}]")
    for label, path in TOKEN_FILES:
        add(label, extract_telegram_token(path), f"openclaw:{path.name}")
    if MAIA_DB.exists():
        try:
            con = sqlite3.connect(f"file:{MAIA_DB}?mode=ro&immutable=1", uri=True)
            for label, key in MAIA_DB_KEYS:
                row = con.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
                if row and row[0] and ":" in row[0]:
                    add(label, row[0], f"maia.db:{key}")
            con.close()
        except Exception as e:
            print(f"  WARN: couldn't read maia.db: {e}")
    if not tokens:
        print("ERROR: no tokens found. Aborting.")
        sys.exit(1)

    print(f"\nTarget chat_id : {args.chat_id}")
    print(f"Message_id span: {ids[0]}..{ids[-1]}  (count={len(ids)})")
    print(f"Bots to try    : {[t[0] for t in tokens]}")
    if args.dry_run:
        print("\n[dry-run] no API calls made.")
        return

    print()
    summary = {label: {"deleted": 0, "not_mine": 0, "errors": 0} for label, _ in tokens}
    for mid in ids:
        for label, tok in tokens:
            ok, desc = delete_msg(tok, args.chat_id, mid)
            if ok:
                summary[label]["deleted"] += 1
                print(f"  DELETED  {label}  msg={mid}")
            else:
                d = desc.lower()
                if "message to delete not found" in d or "message can't be deleted" in d or "message_id_invalid" in d:
                    summary[label]["not_mine"] += 1
                else:
                    summary[label]["errors"] += 1
                    print(f"  err      {label}  msg={mid}: {desc}")
            time.sleep(args.sleep_ms / 1000.0)

    print("\n=== Summary ===")
    for label, s in summary.items():
        print(f"  {label:20}  deleted={s['deleted']:4}  not-mine={s['not_mine']:4}  errors={s['errors']:4}")
    total_deleted = sum(s['deleted'] for s in summary.values())
    print(f"\nTotal messages purged: {total_deleted}")

if __name__ == "__main__":
    main()

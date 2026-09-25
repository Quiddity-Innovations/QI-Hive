# -*- coding: utf-8 -*-
"""
QI Tasuke Notifier
Pushes a short notification to Renne via the Tasuke LINE Official Account
(broadcast to followers, so no stored userId is required).

Usage:
  python qi_tasuke_notify.py "message text"
Reads the channel token from C:\OC\secrets\tasuke-line.env (LINE_CHANNEL_TOKEN).
"""
import sys, os, json, urllib.request
sys.stdout.reconfigure(encoding="utf-8")

ENV = r"C:\OC\secrets\tasuke-line.env"
MSG = sys.argv[1] if len(sys.argv) > 1 else "QI notification"

def load_token():
    for line in open(ENV, encoding="utf-8", errors="replace"):
        line = line.strip()
        if line.startswith("LINE_CHANNEL_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"')
    return None

def main():
    token = load_token()
    if not token:
        print("ERROR: LINE_CHANNEL_TOKEN not found in", ENV); return 1
    body = json.dumps({"messages": [{"type": "text", "text": MSG[:4900]}]}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.line.me/v2/bot/message/broadcast",
        data=body, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print("Tasuke notify OK:", r.status)
            return 0
    except urllib.error.HTTPError as e:
        print("Tasuke notify FAILED:", e.code, e.read().decode("utf-8", "replace")[:300])
        return 1
    except Exception as e:
        print("Tasuke notify FAILED:", e)
        return 1

if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""
QI War Room — Telegram OUTBOUND relay (Phase N Stage 0.6).

Mirrors new War Room messages to Renne's Telegram DM via the Tasuke bot, so the
room is visible from his phone. Inbound (Telegram -> War Room) is handled on the
OpenClaw/Tasuke side, which posts back into the room tagged project_id='telegram_in';
those are skipped here so Renne's own Telegram messages are never echoed back.

Token + chat id come from C:\\QIH\\config\\warroom_telegram.env (never hard-coded).

Imported:   start_in_thread()   (dashboard runs this on startup)
Standalone: python qi_warroom_telegram.py            # one-shot: send unsent
            python qi_warroom_telegram.py --test      # send a labelled test DM
"""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

CONFIG     = Path(r"C:\QIH\config\warroom_telegram.env")
BRAIN_DB   = Path(r"C:\QIH\data\qi_brain.db")
STATE_FILE = Path(r"C:\QIH\data\warroom_tg_state.json")
POLL_SECS  = 4.0
TG_TAG     = "telegram_in"          # project_id marker for inbound-from-TG messages


def _load_cfg() -> dict:
    cfg = {}
    try:
        for ln in CONFIG.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                cfg[k.strip()] = v.strip()
    except Exception:
        pass
    return cfg


def _tg_send(token: str, chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text,
                                   "disable_web_page_preview": "true"}).encode()
    try:
        with urllib.request.urlopen(url, data=data, timeout=15) as r:
            return json.loads(r.read().decode()).get("ok", False)
    except Exception:
        return False


def _state() -> int:
    try:
        return int(json.loads(STATE_FILE.read_text(encoding="utf-8")).get("last_sent", 0))
    except Exception:
        return 0


def _save(v: int) -> None:
    try:
        STATE_FILE.write_text(json.dumps({"last_sent": v}), encoding="utf-8")
    except Exception:
        pass


def _unsent(last_sent: int) -> list[dict]:
    import sqlite3
    if not BRAIN_DB.exists():
        return []
    try:
        conn = sqlite3.connect(f"file:{BRAIN_DB}?mode=ro", uri=True, timeout=3.0)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """SELECT id, agent_id, agent_label, body, project_id
                   FROM warroom_messages
                   WHERE id > ? AND COALESCE(project_id,'') != ?
                   ORDER BY id ASC LIMIT 25""",
                (last_sent, TG_TAG)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
    except Exception:
        return []


def send_new(cfg: dict | None = None) -> int:
    """Send any War Room messages newer than last_sent to Renne's Telegram. Returns count sent."""
    cfg = cfg or _load_cfg()
    token, chat = cfg.get("WARROOM_TG_BOT_TOKEN"), cfg.get("WARROOM_TG_RENNE_CHAT_ID")
    if not token or not chat:
        return 0
    last = _state()
    sent = 0
    for m in _unsent(last):
        label = m.get("agent_label") or m.get("agent_id") or "?"
        text = f"💬 {label}\n{m.get('body') or ''}"
        if _tg_send(token, chat, text):
            sent += 1
        _save(m["id"])      # advance even on send-failure to avoid hammering one bad row
        last = m["id"]
    return sent


def loop():
    cfg = _load_cfg()
    # First run: don't blast history — start from the current max id.
    if _state() == 0:
        import sqlite3
        try:
            conn = sqlite3.connect(f"file:{BRAIN_DB}?mode=ro", uri=True, timeout=3.0)
            mx = conn.execute("SELECT COALESCE(MAX(id),0) FROM warroom_messages").fetchone()[0]
            conn.close()
            _save(int(mx))
        except Exception:
            pass
    while True:
        try:
            send_new(cfg)
        except Exception:
            pass
        time.sleep(POLL_SECS)


def start_in_thread():
    import threading
    t = threading.Thread(target=loop, name="warroom-telegram", daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = _load_cfg()
    if "--test" in sys.argv:
        ok = _tg_send(cfg.get("WARROOM_TG_BOT_TOKEN", ""), cfg.get("WARROOM_TG_RENNE_CHAT_ID", ""),
                      "🛰️ QI War Room bridge test — outbound relay is live. Reply here once inbound is wired.")
        print("test DM ok =", ok)
    else:
        print("sent", send_new(cfg))

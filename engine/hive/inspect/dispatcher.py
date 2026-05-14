# -*- coding: utf-8 -*-
"""
QI_HiveInspectorDrain — dispatcher.

Called by main.py every 60 seconds. Drains up to 20 envelopes per tick
from C:/QIH/inbox/hive_inspector/, computes a deterministic verdict, and
POSTs it to the Brain API.

Escalated envelopes (confidence in gray zone) are left in place for human
review. Quarantined envelopes are moved to quarantine/ for investigation.
"""
import json
import logging
import sqlite3
import urllib.request
from pathlib import Path

from verdict_engine import compute_verdict

_INBOX      = Path(r"C:\QIH\inbox\hive_inspector")
_DONE       = _INBOX / "done"
_QUARANTINE = _INBOX / "quarantine"
_DB_PATH    = Path(r"C:\QIH\data\qi_brain.db")
_BRAIN_URL  = "http://127.0.0.1:9011/api/dispatch/{dispatch_id}/inspector_verdict"
_PER_TICK   = 20

log = logging.getLogger("hive_inspector_drain.dispatcher")


def _ensure_dirs() -> None:
    _DONE.mkdir(parents=True, exist_ok=True)
    _QUARANTINE.mkdir(parents=True, exist_ok=True)


def _move_to_done(env_path: Path) -> None:
    dest = _DONE / env_path.name
    env_path.replace(dest)
    log.debug("moved to done: %s", env_path.name)


def _move_to_quarantine(env_path: Path, reason: str) -> None:
    dest = _QUARANTINE / env_path.name
    env_path.replace(dest)
    log.warning("quarantined %s: %s", env_path.name, reason)


def _is_already_resolved(dispatch_id: str) -> bool:
    """Return True if this dispatch_run already has a verdict set in the DB."""
    try:
        conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 3000")
        row = conn.execute(
            """SELECT inspector_verdict FROM dispatch_runs
               WHERE dispatch_id=? AND state='pending_review'
               ORDER BY id DESC LIMIT 1""",
            (dispatch_id,),
        ).fetchone()
        conn.close()
        return bool(row and row["inspector_verdict"])
    except Exception as e:
        log.warning("DB check failed for %s: %s", dispatch_id, e)
        # Assume not resolved so we don't silently skip.
        return False


def _post_verdict(dispatch_id: str, verdict: str, reasons: list[str], confidence: float) -> int:
    """POST verdict to Brain API. Returns HTTP status code, or 0 on network error."""
    # Map verdict+confidence to severity for Brain schema.
    severity = "info" if verdict == "pass" else "major"
    body = json.dumps({
        "verdict": verdict,
        "reasons": reasons[:20],
        "severity": severity,
        "reviewer": "deterministic_auto_v1",
    }).encode("utf-8")

    url = _BRAIN_URL.format(dispatch_id=dispatch_id)
    try:
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        log.warning("network error posting verdict for %s: %s", dispatch_id, e)
        return 0


def run_once() -> None:
    """Drain up to _PER_TICK envelopes from the inspector inbox."""
    _ensure_dirs()

    envelopes = sorted(_INBOX.glob("*.json"))[:_PER_TICK]
    if not envelopes:
        return

    log.info("drain tick: %d envelope(s) found", len(envelopes))

    for env_path in envelopes:
        # Parse envelope JSON.
        try:
            env = json.loads(env_path.read_text(encoding="utf-8"))
        except Exception as e:
            _move_to_quarantine(env_path, f"JSON parse error: {e}")
            continue

        dispatch_id = env.get("dispatch_id")
        if not dispatch_id:
            _move_to_quarantine(env_path, "missing dispatch_id field")
            continue

        # Idempotency: skip if verdict already recorded in DB.
        if _is_already_resolved(dispatch_id):
            log.debug("verdict already set for %s — moving to done", dispatch_id)
            _move_to_done(env_path)
            continue

        verdict, confidence, reasons = compute_verdict(env)
        log.info(
            "dispatch=%s verdict=%s confidence=%.2f reasons=%s",
            dispatch_id, verdict, confidence, reasons,
        )

        if verdict == "escalate":
            # Leave envelope in place; human or Phase-3 LLM drain picks it up.
            log.info("escalated %s (confidence=%.2f) — leaving for human review", dispatch_id, confidence)
            continue

        # POST to Brain API.
        status = _post_verdict(dispatch_id, verdict, reasons, confidence)

        if status in (200, 201):
            log.info("verdict posted: %s -> %s (HTTP %d)", dispatch_id, verdict, status)
            _move_to_done(env_path)
        elif status == 404:
            # Brain doesn't know about this dispatch_id — orphaned envelope.
            _move_to_quarantine(env_path, f"Brain returned 404 for dispatch_id={dispatch_id}")
        elif 400 <= status < 500:
            # Schema mismatch or bad request — quarantine for investigation.
            _move_to_quarantine(env_path, f"Brain returned {status} (schema/request error)")
        else:
            # 5xx or network error — leave envelope for retry next tick.
            log.warning(
                "verdict POST failed for %s (status=%s) — will retry next tick",
                dispatch_id, status,
            )

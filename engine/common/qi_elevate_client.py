# -*- coding: utf-8 -*-
"""
QI Elevation Broker — client helper.

Drops a request into the broker queue, waits for completion, returns
the result. Any QI agent (or I, from a non-admin shell) can call this.

Usage:
    from engine.common.qi_elevate_client import run_elevated
    r = run_elevated("nssm", ["restart", "QI_Dashboard"], submitted_by="claude")
    print(r["status"], r["stdout"])

Returns the result dict verbatim from the broker. Raises TimeoutError
if the broker doesn't respond within `timeout` seconds.
"""
import json
import time
import uuid
from datetime import datetime
from pathlib import Path

CMD_DIR = Path(r"C:\QIH\commands")
PENDING = CMD_DIR / "pending"
COMPLETED = CMD_DIR / "completed"


def run_elevated(
    cmd: str,
    args: list[str],
    submitted_by: str = "unknown",
    timeout: float = 30.0,
    poll_interval: float = 0.5,
) -> dict:
    """Submit a command to the elevation broker and wait for the result."""
    PENDING.mkdir(parents=True, exist_ok=True)
    COMPLETED.mkdir(parents=True, exist_ok=True)

    rid = f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    request = {
        "id": rid,
        "cmd": cmd,
        "args": args,
        "submitted_by": submitted_by,
        "timestamp": datetime.now().isoformat(),
    }
    req_path = PENDING / f"{rid}.json"
    req_path.write_text(json.dumps(request, indent=2), encoding="utf-8")

    result_path = COMPLETED / f"{rid}.json"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if result_path.exists():
            return json.loads(result_path.read_text(encoding="utf-8"))
        time.sleep(poll_interval)

    raise TimeoutError(
        f"elevation broker did not respond within {timeout}s "
        f"(request {rid} still in {PENDING}). "
        f"Is the QI_Elevate service running?"
    )


if __name__ == "__main__":
    # Smoke test — safe no-op: nssm status QI_BrainAPI
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    r = run_elevated("nssm", ["status", "QI_BrainAPI"], submitted_by="smoke_test")
    print(json.dumps(r, indent=2, ensure_ascii=False))

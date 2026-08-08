# -*- coding: utf-8 -*-
"""QI Ollama Watchdog — keeps the Ollama engine alive.

One-shot check: if the Ollama API at 127.0.0.1:11434 is not responding, relaunch
the Ollama desktop app (which runs in the user session with full GPU + the
user's model library). Designed to be run on a 1-minute schedule by the
'QI_Ollama_Watchdog' scheduled task.

Why the desktop app and not a LocalSystem service: the desktop app runs in the
interactive user session, so it gets the GPU and ~/.ollama models for free. A
LocalSystem service can silently fall back to CPU and the wrong models dir.
"""
import sys
import time
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path

OLLAMA_URL = "http://127.0.0.1:11434/api/tags"
OLLAMA_APP = Path.home() / "AppData" / "Local" / "Programs" / "Ollama" / "ollama app.exe"
LOG = Path(r"C:\QIH\logs\ollama_watchdog.log")


def log(msg: str) -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')}  {msg}\n")
    except Exception:
        pass


def is_up() -> bool:
    try:
        with urllib.request.urlopen(OLLAMA_URL, timeout=4) as r:
            return r.status == 200
    except Exception:
        return False


def main() -> int:
    if is_up():
        return 0  # healthy — stay quiet
    log("Ollama DOWN — relaunching desktop app")
    if not OLLAMA_APP.exists():
        log(f"ERROR: ollama app not found at {OLLAMA_APP}")
        return 1
    try:
        subprocess.Popen([str(OLLAMA_APP)], close_fds=True)
    except Exception as e:
        log(f"ERROR launching: {e}")
        return 1
    # Give it up to ~25s to come back, then report
    for _ in range(12):
        time.sleep(2)
        if is_up():
            log("Ollama recovered")
            return 0
    log("WARNING: Ollama did not recover within 25s")
    return 1


if __name__ == "__main__":
    sys.exit(main())

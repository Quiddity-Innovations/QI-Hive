# -*- coding: utf-8 -*-
"""
QI_HiveApply — entry point.

Runs the dispatcher loop forever. Logs to C:\\QIH\\logs\\hive_apply.log.
NSSM keeps it alive on the machine; kill switch via HALT file or nssm stop.
"""
import sys
import logging
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

_LOG_PATH = Path(r"C:\QIH\logs\hive_apply.log")
_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(str(_LOG_PATH), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

log = logging.getLogger("hive_apply.main")


def main() -> None:
    log.info("QI_HiveApply starting - inbox-fallback mode (Phase 1)")
    from dispatcher import run_once

    while True:
        try:
            run_once()
        except Exception as exc:
            log.exception("Unhandled error in run_once: %s", exc)
        time.sleep(10)


if __name__ == "__main__":
    main()

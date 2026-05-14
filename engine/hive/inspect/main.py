# -*- coding: utf-8 -*-
"""
QI_HiveInspectorDrain — entry point.

Runs the drain dispatcher loop every 60 seconds.
Logs to C:\\QIH\\logs\\hive_inspector_drain.log.
NSSM keeps it alive; kill switch: stop QI_HiveInspectorDrain via NSSM.

Usage:
  python main.py          — run forever (service mode)
  python main.py --once   — run one tick and exit (smoke test / manual drain)
"""
import sys
import logging
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

_LOG_PATH     = Path(r"C:\QIH\logs\hive_inspector_drain.log")
_TICK_SECONDS = 60

_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(str(_LOG_PATH), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

log = logging.getLogger("hive_inspector_drain.main")


def main() -> None:
    once = "--once" in sys.argv

    log.info("QI_HiveInspectorDrain starting — mode=%s tick=%ds", "once" if once else "loop", _TICK_SECONDS)

    from dispatcher import run_once

    if once:
        run_once()
        log.info("--once mode complete")
        return

    while True:
        try:
            run_once()
        except Exception as exc:
            log.exception("Unhandled error in run_once: %s", exc)
        time.sleep(_TICK_SECONDS)


if __name__ == "__main__":
    main()

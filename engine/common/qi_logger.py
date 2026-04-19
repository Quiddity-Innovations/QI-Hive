# -*- coding: utf-8 -*-
"""
QI Logger — standardized logging factory for all QI projects.

Reads config/logging.json, creates a RotatingFileHandler + console handler per
service, and supports runtime log-level changes (called by /config Dashboard
page via set_level()).

Usage:
    from engine.common.qi_logger import get_logger
    log = get_logger("brain_api")
    log.info("starting service")
    log.debug("detailed trace")

Env overrides:
    QI_CONFIG_DIR   override the config/ folder location
    QI_LOG_DIR      override the logs/ folder location
"""
import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Lock

# ── Path resolution ────────────────────────────────────────────────────────────
_THIS_DIR     = Path(__file__).parent                          # engine/common/
_PROJECT_DIR  = _THIS_DIR.parent.parent                        # C:\QIH
_CONFIG_DIR   = Path(os.environ.get("QI_CONFIG_DIR", str(_PROJECT_DIR / "config")))
_DEFAULT_LOG_DIR = Path(os.environ.get("QI_LOG_DIR", str(_PROJECT_DIR / "logs")))
_CONFIG_PATH  = _CONFIG_DIR / "logging.json"

_LEVELS = {
    "DEBUG":    logging.DEBUG,
    "INFO":     logging.INFO,
    "WARNING":  logging.WARNING,
    "ERROR":    logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

_loggers: dict[str, logging.Logger] = {}
_lock = Lock()


def _load_config() -> dict:
    if not _CONFIG_PATH.exists():
        return {
            "default_level": "INFO",
            "log_dir": str(_DEFAULT_LOG_DIR),
            "rotation": {"max_bytes": 5_242_880, "backup_count": 5},
            "format": "%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
            "date_format": "%Y-%m-%d %H:%M:%S",
            "services": {},
        }
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_logger(name: str, cfg: dict) -> logging.Logger:
    svc = cfg.get("services", {}).get(name, {})
    level_name = svc.get("level", cfg.get("default_level", "INFO")).upper()
    level = _LEVELS.get(level_name, logging.INFO)

    log_dir = Path(cfg.get("log_dir", str(_DEFAULT_LOG_DIR)))
    rel_file = svc.get("file", f"{name}.log")
    file_path = log_dir / rel_file
    file_path.parent.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter(
        cfg.get("format", "%(asctime)s  %(levelname)-7s  %(name)s  %(message)s"),
        cfg.get("date_format", "%Y-%m-%d %H:%M:%S"),
    )

    rot = cfg.get("rotation", {})
    file_handler = RotatingFileHandler(
        str(file_path),
        maxBytes=rot.get("max_bytes", 5_242_880),
        backupCount=rot.get("backup_count", 5),
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)

    logger = logging.getLogger(f"qi.{name}")
    logger.setLevel(level)
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False
    return logger


def get_logger(name: str) -> logging.Logger:
    """Return (or create) a logger for the named service. Thread-safe."""
    with _lock:
        if name in _loggers:
            return _loggers[name]
        cfg = _load_config()
        logger = _build_logger(name, cfg)
        _loggers[name] = logger
        return logger


def set_level(service: str, level: str) -> bool:
    """
    Change a service's log level at runtime AND persist to config/logging.json.
    Called by the /config Dashboard page.
    Returns True on success.
    """
    level = level.upper()
    if level not in _LEVELS:
        return False

    # Persist to config
    cfg = _load_config()
    cfg.setdefault("services", {}).setdefault(service, {})["level"] = level
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

    # Hot-apply if logger already exists in this process
    with _lock:
        if service in _loggers:
            _loggers[service].setLevel(_LEVELS[level])

    return True


def list_services() -> dict:
    """Return current config for all services — used by /config page."""
    cfg = _load_config()
    return {
        "default_level": cfg.get("default_level", "INFO"),
        "log_dir": cfg.get("log_dir", str(_DEFAULT_LOG_DIR)),
        "services": cfg.get("services", {}),
    }


if __name__ == "__main__":
    # Smoke test: python -m engine.common.qi_logger
    log = get_logger("qi_logger_test")
    log.debug("debug visible only if level=DEBUG")
    log.info("info message")
    log.warning("warning message")
    log.error("error message")
    print("Services:", list(list_services()["services"].keys()))

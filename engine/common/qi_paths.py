"""qi_paths - the single place a QI app asks where its files live.

Phase 4 of the 2026-08 migration separates code from data. Apps currently write
beside their own source (C:\\APPS\\QI\\LOGS, C:\\APPS\\NEXUS\\LOGS, C:\\APPS\\QI\\maia.db), which
makes them impossible to install under C:\\Program Files, where a non-elevated
process cannot write.

This module is the contract. An app never builds a data path by joining onto
__file__ again; it asks here.

    from qi_paths import paths
    p = paths("maia")

    p.code        -> where the app's source/binaries live (read-only in prod)
    p.data        -> C:\\ProgramData\\Quiddity Innovations\\maia
    p.config      -> %APPDATA%\\Quiddity Innovations\\maia
    p.cache       -> %LOCALAPPDATA%\\Quiddity Innovations\\maia\\Cache
    p.logs        -> %LOCALAPPDATA%\\Quiddity Innovations\\maia\\Logs
    p.db("maia.db") -> full path inside p.data

Every accessor creates the directory on first use, so callers never mkdir.

Overrides, highest precedence first:
  1. QI_<APP>_DATA_DIR / QI_<APP>_LOG_DIR / ...   (per-app, e.g. QI_MAIA_DATA_DIR)
  2. QI_DATA_DIR / QI_CONFIG_DIR / QI_CACHE_DIR / QI_LOG_DIR  (all apps)
  3. The defaults above.

Overrides matter for two cases: a service running as LocalSystem (whose %APPDATA%
is inside the system profile, which is not where an admin expects to find config),
and dev machines that want everything under one scratch tree.

Frozen builds: when running under PyInstaller, `code` resolves to sys._MEIPASS so
bundled read-only assets are found, while data/config/cache/logs are unaffected.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

VENDOR = "Quiddity Innovations"

__all__ = ["AppPaths", "paths", "VENDOR"]


def _env(*names: str) -> str | None:
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    return None


def _programdata() -> Path:
    return Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))


def _appdata() -> Path:
    v = os.environ.get("APPDATA")
    if v:
        return Path(v)
    return Path.home() / "AppData" / "Roaming"


def _localappdata() -> Path:
    v = os.environ.get("LOCALAPPDATA")
    if v:
        return Path(v)
    return Path.home() / "AppData" / "Local"


class AppPaths:
    """Resolved locations for one app. Directories are created on access."""

    def __init__(self, app: str, code: Path | str | None = None) -> None:
        if not app or not app.strip():
            raise ValueError("app name is required")
        self.app = app.strip()
        self._slug = self.app.upper().replace("-", "_").replace(" ", "_")
        self._code = Path(code) if code else None

    # -- internals ---------------------------------------------------------

    def _override(self, kind: str) -> Path | None:
        v = _env(f"QI_{self._slug}_{kind}_DIR", f"QI_{kind}_DIR")
        if not v:
            return None
        # A shared QI_<KIND>_DIR is a root for all apps, so scope it per app.
        # A per-app override is used verbatim.
        if os.environ.get(f"QI_{self._slug}_{kind}_DIR"):
            return Path(v)
        return Path(v) / self.app

    @staticmethod
    def _ensure(p: Path) -> Path:
        p.mkdir(parents=True, exist_ok=True)
        return p

    # -- locations ---------------------------------------------------------

    @property
    def code(self) -> Path:
        """Read-only application directory. Never write here."""
        if self._code:
            return self._code
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:                      # frozen by PyInstaller
            return Path(meipass)
        return Path(sys.argv[0]).resolve().parent

    @property
    def data(self) -> Path:
        """Machine-wide state: databases, shared indexes. Survives uninstall."""
        return self._ensure(self._override("DATA")
                            or _programdata() / VENDOR / self.app)

    @property
    def config(self) -> Path:
        """Per-user settings."""
        return self._ensure(self._override("CONFIG")
                            or _appdata() / VENDOR / self.app)

    @property
    def cache(self) -> Path:
        """Disposable. Anything here must be safe to delete at any moment."""
        return self._ensure(self._override("CACHE")
                            or _localappdata() / VENDOR / self.app / "Cache")

    @property
    def logs(self) -> Path:
        return self._ensure(self._override("LOG")
                            or _localappdata() / VENDOR / self.app / "Logs")

    # -- helpers -----------------------------------------------------------

    def db(self, name: str) -> Path:
        """Full path to a database file inside the data directory."""
        return self.data / name

    def log(self, name: str) -> Path:
        return self.logs / name

    def __repr__(self) -> str:                                # pragma: no cover
        return f"<AppPaths {self.app!r}>"

    def describe(self) -> str:
        """Human-readable dump - useful in a --paths CLI flag or health endpoint."""
        rows = [
            ("code", self.code),
            ("data", self.data),
            ("config", self.config),
            ("cache", self.cache),
            ("logs", self.logs),
        ]
        w = max(len(k) for k, _ in rows)
        return "\n".join(f"  {k.ljust(w)} : {v}" for k, v in rows)


_cache: dict[str, AppPaths] = {}


def paths(app: str, code: Path | str | None = None) -> AppPaths:
    """Return the (memoised) AppPaths for an app."""
    key = f"{app}|{code}"
    if key not in _cache:
        _cache[key] = AppPaths(app, code)
    return _cache[key]


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "example"
    print(f"qi_paths for {name!r}:")
    print(paths(name).describe())

# -*- coding: utf-8 -*-
"""
QI Gate — identity store (users, passwords, sessions).

Deliberately modelled on C:\\APPS\\MapSnap\\Application\\auth.py, which is the
strongest auth implementation in the QI ecosystem (pbkdf2-sha256 @ 200k
iterations, opaque session tokens, last-admin guards). This module keeps the
same crypto and session semantics but drops MapSnap's per-tab/feature RBAC —
the gate answers one question only: "is this person allowed through?"

Storage: data/gate_users.db (SQLite). Nothing is stored in the repo.
"""

import hashlib
import hmac
import json
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

GATE_DIR = Path(__file__).parent.resolve()
USERS_DB = GATE_DIR / "data" / "gate_users.db"

# pbkdf2 @ 200k iterations — OWASP minimum for SHA-256 (matches MapSnap).
PBKDF2_ITERS = 200_000

SESSION_COOKIE = "qi_gate_session"
SESSION_TTL_SECONDS = 12 * 3600          # 12h — short: this guards the whole estate
REMEMBER_TTL_SECONDS = 30 * 24 * 3600    # 30d when "remember this device" is ticked

# Brute-force throttle. Counted per (username, client-ip).
MAX_FAILS = 5
LOCKOUT_SECONDS = 15 * 60


# ── DB ────────────────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    USERS_DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(USERS_DB), timeout=10.0)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    c.execute("PRAGMA journal_mode = WAL")
    return c


def init_db() -> None:
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                username        TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash   TEXT NOT NULL,
                role            TEXT NOT NULL DEFAULT 'user',
                disabled        INTEGER NOT NULL DEFAULT 0,
                must_change_pw  INTEGER NOT NULL DEFAULT 0,
                created_at      TEXT NOT NULL,
                last_login_at   TEXT
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token       TEXT PRIMARY KEY,
                user_id     INTEGER NOT NULL,
                created_at  INTEGER NOT NULL,
                expires_at  INTEGER NOT NULL,
                client_ip   TEXT,
                user_agent  TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS login_failures (
                username    TEXT NOT NULL,
                client_ip   TEXT NOT NULL,
                failed_at   INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_fail_lookup
                ON login_failures(username, client_ip, failed_at);
            CREATE INDEX IF NOT EXISTS idx_sess_expiry ON sessions(expires_at);
        """)
        # Added 2026-08-07: per-user host scoping. Empty/NULL means "every host
        # we front", which is what every account created before this migration
        # had implicitly -- so existing logins are unaffected.
        cols = {r["name"] for r in c.execute("PRAGMA table_info(users)")}
        if "allowed_hosts" not in cols:
            c.execute("ALTER TABLE users ADD COLUMN allowed_hosts TEXT NOT NULL DEFAULT ''")


def _parse_hosts(raw: str) -> list:
    """'' / None -> [] (unrestricted). Otherwise a lowercased hostname list."""
    if not raw:
        return []
    return [h.strip().lower() for h in str(raw).split(",") if h.strip()]


def user_may_access(user: dict, host: str) -> bool:
    """A user with no allowed_hosts reaches everything. Otherwise the requested
    host must be named explicitly. Unknown/blank host fails closed for scoped
    users -- we would rather deny than leak a host we could not identify."""
    allowed = user.get("allowed_hosts") or []
    if not allowed:
        return True
    h = (host or "").split(":")[0].strip().lower()
    return bool(h) and h in allowed


# ── password hashing ─────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERS)
    return f"pbkdf2_sha256${PBKDF2_ITERS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters_s, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                 bytes.fromhex(salt_hex), int(iters_s))
        return hmac.compare_digest(dk, bytes.fromhex(hash_hex))
    except Exception:
        return False


# ── users ────────────────────────────────────────────────────────────────────

def _row_to_user(row: sqlite3.Row) -> dict:
    return {
        "id":             row["id"],
        "username":       row["username"],
        "role":           row["role"],
        "disabled":       bool(row["disabled"]),
        "must_change_pw": bool(row["must_change_pw"]),
        "created_at":     row["created_at"],
        "last_login_at":  row["last_login_at"],
        "allowed_hosts":  _parse_hosts(
            row["allowed_hosts"] if "allowed_hosts" in row.keys() else ""),
    }


def has_any_user() -> bool:
    init_db()
    with _conn() as c:
        return c.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0


def list_users() -> list:
    init_db()
    with _conn() as c:
        return [_row_to_user(r) for r in
                c.execute("SELECT * FROM users ORDER BY username").fetchall()]


def get_user(user_id: int) -> Optional[dict]:
    init_db()
    with _conn() as c:
        row = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    return _row_to_user(row) if row else None


def create_user(username: str, password: str, role: str = "user",
                must_change_pw: bool = False, allowed_hosts=None) -> dict:
    init_db()
    username = (username or "").strip()
    if not username:
        raise ValueError("username required")
    if len(password) < 10:
        # Longer than MapSnap's 6: this one password fronts the whole estate.
        raise ValueError("password must be at least 10 characters")
    if role not in ("admin", "user"):
        raise ValueError(f"unknown role: {role}")
    hosts = _normalise_hosts(allowed_hosts)
    if role == "admin" and hosts:
        # An admin that cannot reach every host would be a trap: they manage
        # accounts but could lock themselves out of the tool that does it.
        raise ValueError("admin accounts cannot be host-scoped")
    with _conn() as c:
        try:
            cur = c.execute(
                "INSERT INTO users(username,password_hash,role,must_change_pw,"
                "created_at,allowed_hosts) VALUES(?,?,?,?,?,?)",
                (username, hash_password(password), role,
                 1 if must_change_pw else 0,
                 datetime.now(timezone.utc).isoformat(), hosts))
            uid = cur.lastrowid
        except sqlite3.IntegrityError:
            raise ValueError(f"username already exists: {username}")
    return get_user(uid)


def _normalise_hosts(allowed_hosts) -> str:
    """Accepts a list or a comma string; returns the stored comma form."""
    if not allowed_hosts:
        return ""
    if isinstance(allowed_hosts, str):
        allowed_hosts = allowed_hosts.split(",")
    return ",".join(sorted({h.strip().lower() for h in allowed_hosts if h.strip()}))


def set_allowed_hosts(user_id: int, allowed_hosts) -> list:
    """Re-scope a user. Passing nothing clears the scope (full access).
    Existing sessions stay valid -- the check happens per request, so a
    narrowed scope takes effect on the user's very next page load."""
    init_db()
    hosts = _normalise_hosts(allowed_hosts)
    with _conn() as c:
        row = c.execute("SELECT role FROM users WHERE id=?", (user_id,)).fetchone()
        if row is None:
            raise ValueError(f"no such user id: {user_id}")
        if row["role"] == "admin" and hosts:
            raise ValueError("admin accounts cannot be host-scoped")
        c.execute("UPDATE users SET allowed_hosts=? WHERE id=?", (hosts, user_id))
    return _parse_hosts(hosts)


def set_password(user_id: int, password: str) -> None:
    if len(password) < 10:
        raise ValueError("password must be at least 10 characters")
    init_db()
    with _conn() as c:
        c.execute("UPDATE users SET password_hash=?, must_change_pw=0 WHERE id=?",
                  (hash_password(password), user_id))


def set_disabled(user_id: int, disabled: bool) -> None:
    """Disabling also kills every live session for that user."""
    init_db()
    with _conn() as c:
        if disabled:
            admins = c.execute(
                "SELECT COUNT(*) FROM users WHERE role='admin' AND disabled=0"
            ).fetchone()[0]
            row = c.execute("SELECT role FROM users WHERE id=?", (user_id,)).fetchone()
            if row and row["role"] == "admin" and admins <= 1:
                raise ValueError("cannot disable the last active admin")
        c.execute("UPDATE users SET disabled=? WHERE id=?",
                  (1 if disabled else 0, user_id))
        if disabled:
            c.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))


def delete_user(user_id: int) -> None:
    init_db()
    with _conn() as c:
        admins = c.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0]
        row = c.execute("SELECT role FROM users WHERE id=?", (user_id,)).fetchone()
        if row and row["role"] == "admin" and admins <= 1:
            raise ValueError("cannot delete the last admin account")
        c.execute("DELETE FROM users WHERE id=?", (user_id,))


# ── brute-force throttle ─────────────────────────────────────────────────────

def _purge_old_failures(c: sqlite3.Connection) -> None:
    c.execute("DELETE FROM login_failures WHERE failed_at < ?",
              (int(time.time()) - LOCKOUT_SECONDS,))


def lockout_remaining(username: str, client_ip: str) -> int:
    """Seconds left on a lockout, or 0 if not locked out."""
    init_db()
    with _conn() as c:
        _purge_old_failures(c)
        rows = c.execute(
            "SELECT failed_at FROM login_failures WHERE username=? AND client_ip=?"
            " ORDER BY failed_at DESC", (username, client_ip)).fetchall()
    if len(rows) < MAX_FAILS:
        return 0
    unlock_at = rows[MAX_FAILS - 1]["failed_at"] + LOCKOUT_SECONDS
    return max(0, unlock_at - int(time.time()))


def record_failure(username: str, client_ip: str) -> None:
    init_db()
    with _conn() as c:
        _purge_old_failures(c)
        c.execute("INSERT INTO login_failures(username,client_ip,failed_at) VALUES(?,?,?)",
                  (username, client_ip, int(time.time())))


def clear_failures(username: str, client_ip: str) -> None:
    init_db()
    with _conn() as c:
        c.execute("DELETE FROM login_failures WHERE username=? AND client_ip=?",
                  (username, client_ip))


# ── sessions ─────────────────────────────────────────────────────────────────

def _purge_expired(c: sqlite3.Connection) -> None:
    c.execute("DELETE FROM sessions WHERE expires_at < ?", (int(time.time()),))


def create_session(user_id: int, client_ip: str = "", user_agent: str = "",
                   remember: bool = False) -> tuple:
    """Returns (token, ttl_seconds)."""
    init_db()
    ttl = REMEMBER_TTL_SECONDS if remember else SESSION_TTL_SECONDS
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    with _conn() as c:
        _purge_expired(c)
        c.execute("INSERT INTO sessions(token,user_id,created_at,expires_at,client_ip,user_agent)"
                  " VALUES(?,?,?,?,?,?)",
                  (token, user_id, now, now + ttl, client_ip, (user_agent or "")[:300]))
        c.execute("UPDATE users SET last_login_at=? WHERE id=?",
                  (datetime.now(timezone.utc).isoformat(), user_id))
    return token, ttl


def lookup_session(token: str) -> Optional[dict]:
    if not token:
        return None
    init_db()
    with _conn() as c:
        row = c.execute(
            "SELECT u.* FROM sessions s JOIN users u ON s.user_id=u.id"
            " WHERE s.token=? AND s.expires_at>? AND u.disabled=0",
            (token, int(time.time()))).fetchone()
    return _row_to_user(row) if row else None


def destroy_session(token: str) -> None:
    if not token:
        return
    init_db()
    with _conn() as c:
        c.execute("DELETE FROM sessions WHERE token=?", (token,))


def list_sessions() -> list:
    init_db()
    with _conn() as c:
        _purge_expired(c)
        rows = c.execute(
            "SELECT s.token, s.created_at, s.expires_at, s.client_ip, s.user_agent,"
            "       u.username, u.role"
            "  FROM sessions s JOIN users u ON s.user_id=u.id"
            " ORDER BY s.created_at DESC").fetchall()
    return [{
        "handle":     r["token"][:12],
        "display":    r["token"][:8] + "\u2026",
        "username":   r["username"],
        "role":       r["role"],
        "client_ip":  r["client_ip"],
        "user_agent": r["user_agent"],
        "created_at": r["created_at"],
        "expires_at": r["expires_at"],
    } for r in rows]


def revoke_all_sessions(except_token: str = None) -> int:
    """Panic button — log every device out. Returns how many were killed."""
    init_db()
    with _conn() as c:
        before = c.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        if except_token:
            c.execute("DELETE FROM sessions WHERE token<>?", (except_token,))
        else:
            c.execute("DELETE FROM sessions")
        after = c.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    return before - after


def revoke_by_handle(handle: str) -> int:
    init_db()
    if not handle or len(handle) < 8:
        return 0
    esc = handle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    with _conn() as c:
        before = c.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        c.execute("DELETE FROM sessions WHERE token LIKE ? ESCAPE '\\'", (esc + "%",))
        after = c.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    return before - after


def authenticate(username: str, password: str) -> Optional[dict]:
    init_db()
    with _conn() as c:
        row = c.execute("SELECT * FROM users WHERE username=? COLLATE NOCASE",
                        (username,)).fetchone()
    if not row:
        hash_password(password)   # burn equivalent time so absent users aren't detectable
        return None
    if row["disabled"]:
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    return _row_to_user(row)


# ── cookie helpers ───────────────────────────────────────────────────────────

def parse_cookie(cookie_header: str) -> Optional[str]:
    if not cookie_header:
        return None
    for part in cookie_header.split(";"):
        k, _, v = part.strip().partition("=")
        if k == SESSION_COOKIE:
            return v
    return None


def set_cookie_header(token: str, ttl: int, domain: str = "") -> str:
    # Secure: every public host is HTTPS via Cloudflare.
    # SameSite=Lax (not Strict) so following a link into an app keeps you logged in.
    dom = f" Domain={domain};" if domain else ""
    return (f"{SESSION_COOKIE}={token}; HttpOnly; Secure; Path=/;{dom} "
            f"Max-Age={ttl}; SameSite=Lax")


def clear_cookie_header(domain: str = "") -> str:
    dom = f" Domain={domain};" if domain else ""
    return f"{SESSION_COOKIE}=; HttpOnly; Secure; Path=/;{dom} Max-Age=0; SameSite=Lax"

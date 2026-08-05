# -*- coding: utf-8 -*-
"""
QI Gate — the login wall in front of every internet-exposed QI application.

Architecture
------------
    internet -> Cloudflare tunnel -> Caddy :9040 -> app port
                                       |
                                       +-- forward_auth --> QI Gate :9041

Caddy owns the proxying (it handles websockets, SSE and Gradio queues
transparently, which a hand-rolled Python proxy would not). QI Gate owns
identity only: it answers "is this caller logged in?" and serves the login
page. Nothing else changes about the apps themselves -- no app code is
touched, which is what makes this safe to roll out across 20+ services at once.

Fail-closed by design: if this service is down, Caddy's forward_auth fails and
protected sites return 502 rather than opening up. Webhook paths are matched in
Caddy *before* forward_auth, so machine callbacks keep working even if the gate
is stopped.

Run:  python qi_gate.py          (NSSM service QI_Gate)
"""

import json
import logging
import sys
import time
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.parse import urlparse, quote

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
import uvicorn

sys.path.insert(0, str(Path(__file__).parent))
import gate_auth as ga

GATE_DIR = Path(__file__).parent.resolve()
CONFIG_FILE = GATE_DIR / "config" / "gate.json"

CFG = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
G = CFG["gate"]
AUTH_PREFIX = G.get("auth_prefix", "/qi-auth")
COOKIE_DOMAIN = G.get("cookie_domain", "")
BRAND = G.get("brand", "Quiddity Innovations")

# Hosts we are willing to redirect back to after login. Anything else is an
# open-redirect attempt and gets sent to the safe default instead.
KNOWN_HOSTS = {h["host"].lower() for h in CFG.get("hosts", [])}

# ── access log ───────────────────────────────────────────────────────────────
# Renne had no request-level logging anywhere in the estate before this, which
# is why "is someone accessing my apps?" was unanswerable. Every gate decision
# now lands here as one JSON line.

ACCESS_LOG = Path(G.get("access_log", str(GATE_DIR / "LOGS" / "access.log")))
ACCESS_LOG.parent.mkdir(parents=True, exist_ok=True)

_access = logging.getLogger("qi_gate.access")
_access.setLevel(logging.INFO)
_access.propagate = False
_h = logging.FileHandler(ACCESS_LOG, encoding="utf-8")
_h.setFormatter(logging.Formatter("%(message)s"))
_access.addHandler(_h)

log = logging.getLogger("qi_gate")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")


def client_ip(request: Request) -> str:
    """Real caller IP. Behind cloudflared, CF-Connecting-IP is the only header
    that reflects the actual internet client -- everything else is the tunnel."""
    return (request.headers.get("cf-connecting-ip")
            or request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or (request.client.host if request.client else "?"))


def audit(event: str, request: Request, **extra) -> None:
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "ip": client_ip(request),
        "host": request.headers.get("x-forwarded-host") or request.headers.get("host", ""),
        "uri": request.headers.get("x-forwarded-uri") or str(request.url.path),
        "method": request.headers.get("x-forwarded-method") or request.method,
        "ua": (request.headers.get("user-agent") or "")[:200],
        "cf_country": request.headers.get("cf-ipcountry", ""),
    }
    rec.update(extra)
    _access.info(json.dumps(rec, ensure_ascii=False))


app = FastAPI(title="QI Gate", version="1.0.0", docs_url=None, redoc_url=None)


# ── helpers ──────────────────────────────────────────────────────────────────

def _safe_redirect(rd: str, fallback_host: str) -> str:
    """Only ever redirect back to a host we actually front. Without this check,
    ?rd=https://evil.example would turn the login page into an open redirect
    and a convincing phishing hop."""
    default = f"https://{fallback_host}/" if fallback_host else "/"
    if not rd:
        return default
    try:
        p = urlparse(rd)
    except Exception:
        return default
    if p.scheme not in ("https", "http") or not p.netloc:
        return default
    if p.netloc.split(":")[0].lower() not in KNOWN_HOSTS:
        return default
    # Always hand back an https:// URL. The hop from cloudflared to Caddy is
    # plain HTTP, so X-Forwarded-Proto says "http" even though the caller
    # arrived over TLS -- echoing that back would bounce the user through an
    # insecure scheme after login.
    return p._replace(scheme="https").geturl()


def _cookie_domain_for(host: str) -> str:
    """Share one session across *.quiddityinnovations.com; anything else (e.g.
    quiddam.com) gets a host-only cookie and its own login."""
    h = (host or "").split(":")[0].lower()
    if COOKIE_DOMAIN and h.endswith(COOKIE_DOMAIN.lstrip(".")):
        return COOKIE_DOMAIN
    return ""


def _req_host(request: Request) -> str:
    return (request.headers.get("x-forwarded-host")
            or request.headers.get("host", "")).split(":")[0]


# ── first-run setup protection ───────────────────────────────────────────────
# Until an admin exists, the setup screen can mint one. Left open to the
# internet that is a land-grab waiting to happen: whoever reaches it first owns
# the gate and everything behind it. So setup is allowed only from the machine
# or LAN, or with the one-time token written below.

SETUP_TOKEN_FILE = GATE_DIR / "data" / "setup_token.txt"


def setup_token() -> str:
    """Read (or mint) the one-time bootstrap token."""
    SETUP_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    if SETUP_TOKEN_FILE.exists():
        tok = SETUP_TOKEN_FILE.read_text(encoding="utf-8").strip()
        if tok:
            return tok
    import secrets as _s
    tok = _s.token_urlsafe(24)
    SETUP_TOKEN_FILE.write_text(tok, encoding="utf-8")
    return tok


def via_tunnel(request: Request) -> bool:
    """cloudflared stamps these on everything it forwards; a direct
    localhost/LAN request has neither. Same signal the Hive dashboard already
    uses for its write guard."""
    return bool(request.headers.get("cf-ray")
                or request.headers.get("cf-connecting-ip"))


def setup_allowed(request: Request, token: str = "") -> bool:
    if not via_tunnel(request):
        return True
    # Compare unconditionally rather than short-circuiting on an empty token:
    # setup_token() is what mints the file, so skipping it left the token
    # non-existent until someone happened to guess one.
    expected = setup_token()
    return hmac_compare(token, expected) and bool(token)


def hmac_compare(a: str, b: str) -> bool:
    import hmac as _h
    return _h.compare_digest(a or "", b or "")


# ── login page ───────────────────────────────────────────────────────────────

def _page(*, title: str, body: str, status: int = 200) -> HTMLResponse:
    html = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>{escape(title)} &middot; {escape(BRAND)}</title>
<style>
  *{{box-sizing:border-box}}
  body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
       background:#0b0e14;color:#e8eaf0;
       font-family:"Segoe UI",system-ui,-apple-system,sans-serif;padding:24px}}
  .card{{width:100%;max-width:400px;background:#141821;border:1px solid #232936;
        border-radius:14px;padding:34px 32px;box-shadow:0 18px 50px rgba(0,0,0,.55)}}
  .logo{{display:flex;align-items:center;gap:11px;margin-bottom:6px}}
  .dot{{width:11px;height:11px;border-radius:50%;background:#7eb4ea;
       box-shadow:0 0 14px #7eb4ea}}
  h1{{font-size:19px;margin:0;font-weight:600;letter-spacing:-.01em}}
  .sub{{color:#79839a;font-size:13px;margin:8px 0 26px;line-height:1.5}}
  label{{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.06em;
        color:#8891a4;font-weight:600;margin-bottom:7px}}
  input[type=text],input[type=password]{{width:100%;background:#0b0e14;
        border:1px solid #2b3242;border-radius:8px;padding:11px 13px;font-size:14px;
        color:#e8eaf0;margin-bottom:17px;outline:none;transition:border-color .15s}}
  input:focus{{border-color:#4a7fb5}}
  .row{{display:flex;align-items:center;gap:8px;margin-bottom:21px}}
  .row label{{margin:0;text-transform:none;letter-spacing:0;font-size:12.5px;
             color:#a6afc2;font-weight:400;cursor:pointer}}
  button{{width:100%;background:#2563eb;color:#fff;border:0;border-radius:8px;
         padding:12px;font-size:14.5px;font-weight:600;cursor:pointer;
         transition:background .15s}}
  button:hover{{background:#1d4ed8}}
  .err{{background:#2a1416;border:1px solid #5c2126;color:#f2a1a8;font-size:13px;
       border-radius:8px;padding:11px 13px;margin-bottom:19px;line-height:1.45}}
  .ok{{background:#0f2018;border:1px solid #1f4d33;color:#86e0ab;font-size:13px;
      border-radius:8px;padding:11px 13px;margin-bottom:19px;line-height:1.45}}
  .foot{{margin-top:24px;text-align:center;color:#565f73;font-size:11px;line-height:1.6}}
  a{{color:#7eb4ea}}
</style></head><body><div class="card">
  <div class="logo"><span class="dot"></span><h1>{escape(BRAND)}</h1></div>
  {body}
  <div class="foot">QI Gate &middot; protected access<br>All access attempts are logged.</div>
</div></body></html>"""
    return HTMLResponse(html, status_code=status)


def _login_form(rd: str, error: str = "", notice: str = "") -> str:
    err = f'<div class="err">{escape(error)}</div>' if error else ""
    note = f'<div class="ok">{escape(notice)}</div>' if notice else ""
    return f"""
  <div class="sub">Sign in to continue.</div>
  {err}{note}
  <form method="post" action="{escape(AUTH_PREFIX)}/login">
    <input type="hidden" name="rd" value="{escape(rd)}">
    <label for="u">Username</label>
    <input id="u" name="username" type="text" autocomplete="username" autofocus required>
    <label for="p">Password</label>
    <input id="p" name="password" type="password" autocomplete="current-password" required>
    <div class="row">
      <input type="checkbox" id="r" name="remember" value="1">
      <label for="r">Remember this device for 30 days</label>
    </div>
    <button type="submit">Sign in</button>
  </form>"""


def _setup_form(rd: str, error: str = "", token: str = "") -> str:
    err = f'<div class="err">{escape(error)}</div>' if error else ""
    return f"""
  <div class="sub">First run &mdash; create the administrator account that will
  protect every Quiddity application exposed to the internet.</div>
  {err}
  <form method="post" action="{escape(AUTH_PREFIX)}/setup">
    <input type="hidden" name="rd" value="{escape(rd)}">
    <input type="hidden" name="token" value="{escape(token)}">
    <label for="u">Username</label>
    <input id="u" name="username" type="text" autocomplete="username" autofocus required>
    <label for="p">Password (minimum 10 characters)</label>
    <input id="p" name="password" type="password" autocomplete="new-password" required>
    <label for="p2">Confirm password</label>
    <input id="p2" name="password2" type="password" autocomplete="new-password" required>
    <button type="submit">Create account</button>
  </form>"""


# ── forward_auth target ──────────────────────────────────────────────────────

@app.api_route(AUTH_PREFIX + "/verify", methods=["GET", "HEAD"])
async def verify(request: Request):
    """Caddy calls this before proxying. A 2xx lets the request through; any
    other response is copied back to the caller verbatim -- so returning a 302
    here is what actually puts the login screen in front of the user, and keeps
    the Caddyfile free of redirect plumbing.

    Kept deliberately cheap: one indexed SQLite lookup per request."""
    token = ga.parse_cookie(request.headers.get("cookie", ""))
    user = ga.lookup_session(token) if token else None
    if user:
        return Response(status_code=200, headers={
            "X-Qi-User": user["username"],
            "X-Qi-Role": user["role"],
        })

    audit("deny", request, reason="no_session")

    host = _req_host(request)
    uri = request.headers.get("x-forwarded-uri", "/")
    rd = f"https://{host}{uri}" if host else ""
    login_url = f"{AUTH_PREFIX}/login"
    if rd:
        login_url += f"?rd={quote(rd, safe='')}"
    return Response(status_code=302, headers={
        "Location": login_url,
        "Cache-Control": "no-store",
    })


# ── login ────────────────────────────────────────────────────────────────────

@app.get(AUTH_PREFIX + "/login")
async def login_page(request: Request, rd: str = "", e: str = "", token: str = ""):
    host = _req_host(request)
    target = _safe_redirect(rd, host)
    if not ga.has_any_user():
        if not setup_allowed(request, token):
            audit("setup_blocked", request, reason="no_token")
            return _page(title="Setup pending", status=403, body=(
                '<div class="sub">This system is not yet configured.<br><br>'
                'Setup can only be completed from the Quiddity machine itself, '
                'or with the one-time setup link.</div>'))
        return _page(title="Set up", body=_setup_form(target, token=token))
    token = ga.parse_cookie(request.headers.get("cookie", ""))
    if token and ga.lookup_session(token):
        return RedirectResponse(target, status_code=303)
    errors = {
        "bad":    "Incorrect username or password.",
        "locked": "Too many failed attempts. Try again in a few minutes.",
        "origin": "Request blocked for security reasons. Please try again.",
    }
    return _page(title="Sign in", body=_login_form(target, errors.get(e, "")))


@app.post(AUTH_PREFIX + "/login")
async def login_submit(request: Request,
                       username: str = Form(""),
                       password: str = Form(""),
                       rd: str = Form(""),
                       remember: str = Form("")):
    host = _req_host(request)
    target = _safe_redirect(rd, host)
    ip = client_ip(request)

    # CSRF: the form is same-origin, so a cross-site POST is never legitimate.
    origin = request.headers.get("origin") or request.headers.get("referer") or ""
    if origin:
        oh = urlparse(origin).netloc.split(":")[0].lower()
        if oh and oh not in KNOWN_HOSTS:
            audit("login_blocked", request, user=username, reason="bad_origin")
            return RedirectResponse(
                f"{AUTH_PREFIX}/login?e=origin&rd={quote(target, safe='')}",
                status_code=303)

    username = (username or "").strip()

    wait = ga.lockout_remaining(username, ip)
    if wait > 0:
        audit("login_locked", request, user=username, retry_in_s=wait)
        return RedirectResponse(
            f"{AUTH_PREFIX}/login?e=locked&rd={quote(target, safe='')}",
            status_code=303)

    user = ga.authenticate(username, password)
    if not user:
        ga.record_failure(username, ip)
        audit("login_fail", request, user=username)
        time.sleep(0.4)   # blunt the rate of online guessing
        return RedirectResponse(
            f"{AUTH_PREFIX}/login?e=bad&rd={quote(target, safe='')}",
            status_code=303)

    ga.clear_failures(username, ip)
    token, ttl = ga.create_session(
        user["id"], client_ip=ip,
        user_agent=request.headers.get("user-agent", ""),
        remember=bool(remember))
    audit("login_ok", request, user=user["username"], role=user["role"],
          remember=bool(remember))

    resp = RedirectResponse(target, status_code=303)
    resp.headers["Set-Cookie"] = ga.set_cookie_header(
        token, ttl, _cookie_domain_for(host))
    return resp


# ── first-run setup ──────────────────────────────────────────────────────────

@app.post(AUTH_PREFIX + "/setup")
async def setup_submit(request: Request,
                       username: str = Form(""),
                       password: str = Form(""),
                       password2: str = Form(""),
                       rd: str = Form(""),
                       token: str = Form("")):
    host = _req_host(request)
    target = _safe_redirect(rd, host)
    if ga.has_any_user():
        # Setup is a one-shot. Once an admin exists this endpoint is inert,
        # otherwise anyone could mint themselves an account.
        return RedirectResponse(f"{AUTH_PREFIX}/login", status_code=303)
    if not setup_allowed(request, token):
        audit("setup_blocked", request, reason="no_token", user=username)
        return _page(title="Setup pending", status=403, body=(
            '<div class="sub">Setup is not available from this location.</div>'))
    if password != password2:
        return _page(title="Set up",
                     body=_setup_form(target, "Passwords do not match.", token))
    try:
        user = ga.create_user(username, password, role="admin")
    except ValueError as exc:
        return _page(title="Set up", body=_setup_form(target, str(exc), token))
    # Bootstrap token is single-use — burn it the moment an admin exists.
    try:
        SETUP_TOKEN_FILE.unlink(missing_ok=True)
    except Exception:
        pass

    token, ttl = ga.create_session(
        user["id"], client_ip=client_ip(request),
        user_agent=request.headers.get("user-agent", ""))
    audit("setup_admin", request, user=user["username"])
    resp = RedirectResponse(target, status_code=303)
    resp.headers["Set-Cookie"] = ga.set_cookie_header(
        token, ttl, _cookie_domain_for(host))
    return resp


# ── logout ───────────────────────────────────────────────────────────────────

@app.get(AUTH_PREFIX + "/logout")
async def logout(request: Request):
    token = ga.parse_cookie(request.headers.get("cookie", ""))
    user = ga.lookup_session(token) if token else None
    ga.destroy_session(token)
    audit("logout", request, user=(user or {}).get("username", ""))
    host = _req_host(request)
    resp = _page(title="Signed out", body=(
        '<div class="sub">You are signed out.</div>'
        f'<form method="get" action="{escape(AUTH_PREFIX)}/login">'
        '<button type="submit">Sign in again</button></form>'))
    resp.headers["Set-Cookie"] = ga.clear_cookie_header(_cookie_domain_for(host))
    return resp


# ── ops ──────────────────────────────────────────────────────────────────────

@app.get(AUTH_PREFIX + "/health")
async def health():
    return JSONResponse({
        "status": "ok",
        "service": "QI Gate",
        "version": app.version,
        "users": len(ga.list_users()),
        "active_sessions": len(ga.list_sessions()),
        "hosts_fronted": len(CFG.get("hosts", [])),
    })


@app.get(AUTH_PREFIX + "/whoami")
async def whoami(request: Request):
    token = ga.parse_cookie(request.headers.get("cookie", ""))
    user = ga.lookup_session(token) if token else None
    if not user:
        return JSONResponse({"logged_in": False}, status_code=401)
    return JSONResponse({"logged_in": True, "user": user["username"],
                         "role": user["role"]})


if __name__ == "__main__":
    ga.init_db()
    port = int(G.get("auth_port", 9041))
    log.info("QI Gate starting on 127.0.0.1:%s (prefix %s)", port, AUTH_PREFIX)
    log.info("Fronting %d public hosts", len(CFG.get("hosts", [])))
    if not ga.has_any_user():
        tok = setup_token()
        log.warning("No admin account yet. Set one up from this machine at "
                    "http://127.0.0.1:%s%s/login", port, AUTH_PREFIX)
        log.warning("Or remotely, once, with: "
                    "https://<any-protected-host>%s/login?token=%s",
                    AUTH_PREFIX, tok)
        log.warning("Bootstrap token file: %s (deleted automatically after "
                    "the admin account is created)", SETUP_TOKEN_FILE)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

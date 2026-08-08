# QI Gate — the login wall for everything facing the internet

**Location:** `C:\QIH\engine\gate\`
**Services:** `QI_Gate` (:9041, identity) + `QI_Caddy` (:9040, public edge)
**Built:** 2026-08-05 — see [`QI_Public_Exposure_Hardening_2026-08-05.md`](../../shared/documentation/security/QI_Public_Exposure_Hardening_2026-08-05.md) for why.

---

## What it does

Before this existed, every Cloudflare tunnel pointed straight at an app port.
Anyone who knew (or guessed) a hostname got the app — no password, anywhere.
QI Gate puts one login screen in front of all of them without touching a single
line of any application's code.

```
  internet
     |
     v
  Cloudflare tunnel  (cloudflared, 16 named tunnels)
     |
     v
  Caddy  :9040        <- routes on the Host header, does the actual proxying
     |    |
     |    +-- forward_auth --> QI Gate :9041   "is this caller signed in?"
     |                              |
     |                              +-- 2xx  -> allowed, request continues
     |                              +-- 302  -> browser lands on the login page
     v
  the app (:8600, :9876, :8001, ...)
```

**Why Caddy does the proxying and not Python:** websockets, SSE and Gradio
queues pass through Caddy transparently. A hand-rolled Python proxy would have
had to reimplement all of that, and would have broken every Gradio UI in the
estate.

**Why the gate returns a 302 rather than a 401:** Caddy copies any non-2xx
response from the auth service straight back to the caller, so returning a
redirect is what actually puts the login screen in front of the user — and it
keeps redirect plumbing out of the Caddyfile.

---

## The one file that matters

`config/gate.json` is the single source of truth for what the internet may
reach. Everything else is generated from it.

Each host declares a `mode`:

| Mode | Meaning |
|---|---|
| `protected` | Login required for every path. Default for anything with a UI. |
| `mixed` | Login required **except** the paths in `public_paths` — machine callbacks that authenticate themselves by signature (LINE, Telegram, MCP). |
| `open` | No gate at all. Only for endpoints carrying their own strong auth, or ones not yet verified. Every `open` host must carry a `why`. |

Path convention in `public_paths`: a **trailing `/` means prefix** (`/maia/` →
Caddy `/maia/*`); anything else is matched **exactly** (`/health`).

> Note this means `/maia/` does **not** match a bare `/maia` — only paths under
> it. That is deliberate: the webhooks live under the prefix, and the bare path
> should stay behind the wall.

### After editing gate.json

```bash
python C:\QIH\engine\gate\gen_caddyfile.py
C:\QIH\engine\bin\caddy.exe reload --config C:\QIH\engine\proxy\Caddyfile
python C:\QIH\engine\gate\verify_gate.py
```

`Caddyfile.gate` is **generated — never edit it by hand.** The main
`C:\QIH\engine\proxy\Caddyfile` imports it; the `*.qi.local` blocks in that file
are LAN-only and intentionally stay unauthenticated.

---

## Day-to-day operations

All commands run from `C:\QIH\engine\gate\tools\`.

```bash
python gate_admin.py users                    # list accounts (shows each one's host scope)
python gate_admin.py adduser <name> <pw> user # add someone (role: admin|user)
python gate_admin.py adduser demo <pw> user maia-demo.quiddityinnovations.com
                                              # ...scoped to a single site
python gate_admin.py hosts   <name>           # show which hosts they may reach
python gate_admin.py hosts   <name> a.com,b.com   # re-scope
python gate_admin.py hosts   <name> all       # clear the scope (full access)
python gate_admin.py passwd  <name> <pw>      # rotate a password (signs them out)
python gate_admin.py disable <name>           # kill access + all their sessions
python gate_admin.py sessions                 # who is signed in right now, from where
python gate_admin.py revoke  <handle>         # kill one session
python gate_admin.py revokeall                # PANIC: sign everyone out everywhere
python gate_admin.py suspects 24              # security review of the last 24h
python gate_admin.py log 100                  # raw access log
```

### If you think someone is in

```bash
python gate_admin.py suspects 72     # failed logins, blocked attempts, source IPs
python gate_admin.py sessions        # any session you don't recognise?
python gate_admin.py revokeall       # log everyone out
python gate_admin.py passwd Admin <new-strong-password>
```

---

## Verification

`verify_gate.py` hits every hostname over the real internet and asserts the
policy actually holds — including that declared webhook paths still answer, so
a false "secure" that is really "broken" cannot pass unnoticed.

```bash
python verify_gate.py                                   # anonymous checks
python verify_gate.py --user Admin --password '<pw>'    # + signed-in pass-through
```

`verify_design.py` checks the other half: that the gate did not *break* anything.
It fetches every host both through the gate and straight at its app port and diffs
them, and flags absolute `http://` URLs (mixed content).

```bash
python verify_design.py --user Admin --password '<pw>'
```

Run **both** after any change to tunnels, ports, or `gate.json`.

> ⚠️ **Neither script is sufficient on its own for JS-heavy apps.** The NEXUS
> regression on 2026-08-05 was byte-identical at the HTTP level and only visible at
> runtime in a browser. After any edge change, load at least one Gradio app in a real
> browser and check the console. See §5a of the hardening record.

### The `X-Forwarded-Proto` trap

The cloudflared → Caddy hop is plain HTTP, so without an explicit override Caddy
tells apps the client is on `http`. Any app that builds absolute URLs then emits
`http://` links on an `https://` page, and the browser blocks them as mixed content.
`gen_caddyfile.py` forces `header_up X-Forwarded-Proto https` on every upstream.
**Do not remove it** — it silently breaks every Gradio UI.

---

## Failure behaviour (verified 2026-08-05)

| Situation | Result |
|---|---|
| `QI_Gate` stopped | Protected hosts return **502 — fail closed**, never open. |
| `QI_Gate` stopped | Webhook paths **keep working** (matched in Caddy before `forward_auth`), so LINE/Telegram bots survive a gate outage. |
| `QI_Gate` restarted | Wall comes straight back, existing sessions still valid (they live in SQLite, not memory). |
| `QI_Caddy` stopped | Everything public is down. Both services are `Automatic` start. |

Caddy is now a single point of failure for 18 hostnames — that is the deliberate
trade for having one auditable front door. Watch `QI_Caddy` accordingly.

---

## Security properties

- **Passwords:** pbkdf2-sha256, 200,000 iterations, per-user random salt
  (same construction as MapSnap's `auth.py`, the strongest in the estate).
- **Sessions:** 256-bit opaque tokens in SQLite. 12h default, 30d with
  "remember this device". Never a JWT — revocation must be instant.
- **Cookie:** `HttpOnly`, `Secure`, `SameSite=Lax`, scoped to
  `.quiddityinnovations.com` so one login covers every QI subdomain.
  `quiddam.com` is a separate registrable domain and needs its own sign-in
  (same account).
- **Brute force:** 5 failures per (user, IP) → 15 minute lockout, plus a
  deliberate delay on every failure.
- **User enumeration:** a login for a non-existent user burns the same hashing
  time as a real one, so response timing doesn't leak which accounts exist.
- **Open redirect:** `?rd=` is validated against the known host list and forced
  to `https` — otherwise the login page would be a convincing phishing hop.
- **CSRF:** cross-origin POSTs to the login endpoint are rejected.
- **First-run setup:** the account-creation screen is reachable only from the
  machine/LAN, or once with a bootstrap token (`data/setup_token.txt`), which is
  deleted the moment an admin exists. Without this, whoever found the setup
  screen first would have owned the entire estate.
- **Audit:** every allow, deny, login, failure and lockout is one JSON line in
  `LOGS/access.log`, with the real client IP from `CF-Connecting-IP` and the
  country from `CF-IPCountry`.

---

## Known gaps / next steps

1. **Four hosts are still `open`** — see the `why` on each in `gate.json`.
   `connector` is a deliberate permanent exception (it carries its own bearer
   auth and an MCP client cannot log in through a browser). The other three
   (`claudevoice`, `oc-line`, `api.quiddam`) were left untouched because their
   routes were not enumerated and breaking a live bot overnight was the worse
   risk. **Enumerate their routes and move them to `mixed`.**
2. **No MFA.** A password is a single factor in front of the whole estate.
   The natural upgrade is Cloudflare Access (Zero Trust) in front of the
   tunnels — free for up to 50 users, blocks at Cloudflare's edge so hostile
   traffic never reaches the house at all, and adds email OTP or SSO. QI Gate
   would stay as the second layer.
3. **No password self-service.** Rotation is `gate_admin.py passwd` today.
4. **`quiddam.com` needs a separate login** from the `*.quiddityinnovations.com`
   family — unavoidable with cookies, but worth knowing before it confuses
   someone.
5. **Rotate the bootstrap admin password.** The initial one was set over a
   chat session and should not stay in place long-term.

## Per-host scoping (added 2026-08-07)

Until 2026-08-07 any valid session reached every host the gate fronts — one
login was all-or-nothing, which made "share just the Maia demo" impossible.

Accounts now carry an `allowed_hosts` list:

- **Empty = every host.** Every account created before this change is empty, so
  nothing about existing access changed.
- **Non-empty = only those hostnames**, matched exactly and case-insensitively.
  Anything else returns **403** — deliberately not a redirect to the login page,
  which would loop forever for someone who already holds a valid session.
- **Admins cannot be scoped.** An admin who could not reach every host could
  lock themselves out of the tool that fixes it.
- Scope is re-read on every request, so widening or narrowing takes effect on
  the user's next page load — no need to sign them out.

A typo'd hostname silently scopes the account to nothing reachable, so
`adduser` and `hosts` both warn when a name is not one the gate fronts.

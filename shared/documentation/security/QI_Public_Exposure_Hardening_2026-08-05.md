# QI Public Exposure Hardening — audit record

**Date:** 2026-08-05
**Trigger:** Owner (Renne Santiago) reported a suspicion that someone was accessing
internet-exposed QI applications "with not so honourable intentions" and asked for a
password screen on every tunnelled application.
**Performed by:** Claude (Claude Code), on the QI machine
**Scope:** Every Cloudflare tunnel hostname in the QI estate
**Outcome:** 18 of 22 public hostnames moved behind a single authenticated gate.
4 documented exceptions remain.

---

## 1. Executive summary

The QI estate published **22 hostnames** to the internet through **16 Cloudflare
tunnels**. Each tunnel pointed **directly at an application port with no
authentication of any kind**. Anyone who knew or guessed a hostname reached the
application.

The most serious case was `hive.quiddityinnovations.com` — the QI Hive Dashboard —
which exposed the ecosystem snapshot, service inventory, QI Brain data, session
history and the War Room to any anonymous caller. It had a write-token guard on
mutating requests (added 2026-06-12) but **no read protection at all**.

A single authentication layer (**QI Gate**) now fronts the estate. No application
code was modified.

### Honest limitation, stated plainly

**We cannot prove whether anyone got in.** Cloudflare tunnel logs record only
*failed* origin connections; successful requests to running applications were never
logged anywhere. For every app that was up, there is no record of who reached it.
That absence of evidence is itself the most important finding, and QI Gate's access
log is the fix. **Nothing below should be read as "we were not breached" — only as
"here is what the surviving evidence shows."**

---

## 2. Evidence found

Tunnel error logs covering roughly **2026-08-01 → 2026-08-05** contain **1,580
hostile probe requests across 783 distinct attack paths**.

Targets by hostname:

| Hostname | Failed requests logged |
|---|---:|
| `quiddam.com` | 1,758 |
| `autopdf.quiddityinnovations.com` | 1,203 |
| `worldcup.quiddityinnovations.com` | 23 |
| `m2v.quiddityinnovations.com` | 7 |
| `api.quiddam.com` | 3 |
| `dev.quiddam.com` | 1 |

### Confirmed hostile: automated mass-exploitation scanning

Representative paths probed against `quiddam.com`:

```
/wp-admin                                          /.env
/xmlrpc.php                                        /sym403
/wp-content/plugins/hellopress/wp_filemanager.php  /this_is_a_new_hello_world.php
/1.php  /8.php  /k.php  /p.php  /wp.php  /ops.php  /file5.php  /info.php  /ioxi-o.php
```

This is a textbook signature set: WordPress credential and admin-panel hunting,
`.env` secret harvesting, and **webshell/backdoor drop attempts**
(`hellopress/wp_filemanager.php` and `this_is_a_new_hello_world.php` are both known
mass-campaign markers).

**Assessment:** opportunistic, automated, internet-wide scanning — not evidence of a
targeted human adversary. **These specific probes all failed**, but only because the
app on `:7840` happened to be stopped, not because anything defended it. Had it been
running, they would have received real responses.

### Not hostile — recorded to prevent a false alarm

The 1,203 `autopdf.quiddityinnovations.com` entries are almost entirely
`/api/status` and `/api/log?offset=<incrementing>`. That is **AutoPDF's own web UI
polling its log endpoint** — a browser tab left open, retrying against a stopped
service. This is benign and should not be counted as an attack.

---

## 3. Exposure before / after

| # | Hostname | App | Port | Before | After |
|---:|---|---|---:|---|---|
| 1 | hive.quiddityinnovations.com | QI Hive Dashboard | 8600 | **open (reads)** | protected |
| 2 | cognibase.quiddityinnovations.com | CogniBase | 8650 | open | protected |
| 3 | mapsnap.quiddityinnovations.com | MapSnap | 9876 | app login only | protected + `/mcp` |
| 4 | tubescout.quiddityinnovations.com | TubeScout | 8503 | open | protected |
| 5 | nexus.quiddityinnovations.com | NEXUS UI | 7880 | open | protected |
| 6 | naya.quiddityinnovations.com | Naya UI | 7861 | open | protected |
| 7 | lottery.quiddityinnovations.com | LotteryWiz | 8777 | open | protected |
| 8 | cypher.quiddityinnovations.com | CypherMiner | 7842 | open | protected |
| 9 | worldcup.quiddityinnovations.com | Gamez | 8710 | open | protected |
| 10 | m2v.quiddityinnovations.com | M2V | 7841 | open | protected |
| 11 | autopdf.quiddityinnovations.com | AutoPDF | 6969 | open | protected |
| 12 | maia-demo.quiddityinnovations.com | Maia Gradio | 7860 | open | protected |
| 13 | kaze.quiddityinnovations.com | Kaze | 18800 | open | protected |
| 14 | quiddam.com | MQ UI | 7840 | open | protected |
| 15 | dev.quiddam.com | MQ dev | 7849 | open | protected |
| 16 | maia.quiddityinnovations.com | Maia API | 8001 | **open** | mixed |
| 17 | maia.quiddam.com | Maia API alias | 8001 | **open** | mixed |
| 18 | naya-line.quiddityinnovations.com | Naya webhook | 8002 | open | mixed |
| 19 | connector.quiddityinnovations.com | QI Connector MCP | 9030 | bearer/capability | open *(by design)* |
| 20 | claudevoice.quiddityinnovations.com | Claude Voice | 8721 | open | open *(pending)* |
| 21 | oc-line.quiddityinnovations.com | OpenClaw gateway | 18789 | open | open *(pending)* |
| 22 | api.quiddam.com | MQ API | 8500 | open | open *(pending)* |

### Specifically notable

`maia.quiddityinnovations.com` (:8001) published far more than its webhooks. These
paths were **anonymously readable** and are now behind the login wall:

`/panel` · `/panel/api/threads` · `/panel/api/conversation` · `/panel/api/people` ·
`/memory` · `/history` · `/cache` · `/export` · `/admin/scan-groups`

That is conversation history, contact data and a full data export endpoint, publicly
readable on a host that also receives LINE traffic. This was the highest-value
unlogged exposure in the estate after the Hive dashboard.

---

## 4. What was built

**QI Gate** — `C:\QIH\engine\gate\`. Full technical runbook:
[`C:\QIH\engine\gate\README.md`](../../../engine/gate/README.md)

```
internet -> Cloudflare tunnel -> Caddy :9040 -> app port
                                   |
                                   +-- forward_auth --> QI Gate :9041
```

- **Caddy (`QI_Caddy`, :9040)** routes on the `Host` header and does the proxying.
  Chosen over a Python proxy because it passes websockets, SSE and Gradio queues
  through transparently — every Gradio UI in the estate would otherwise have broken.
- **QI Gate (`QI_Gate`, :9041)** answers one question: is this caller signed in?
  It serves the login page and writes the audit log.
- **No application code was modified.** This is what made a 22-host rollout safe to
  do in a single session.

Ports `9040`/`9041` are inside the QI Hive family block (`9000–9099`) per
`qi_registry.json`, alongside Brain (9011) and Connector (9030).

### Security properties

| Control | Implementation |
|---|---|
| Password storage | pbkdf2-sha256, 200,000 iterations, per-user random salt |
| Sessions | 256-bit opaque tokens in SQLite; 12h, or 30d with "remember". Not JWTs — revocation must be instant |
| Cookie | `HttpOnly`, `Secure`, `SameSite=Lax`, scoped `.quiddityinnovations.com` |
| Brute force | 5 failures per (user, IP) → 15 min lockout + per-failure delay |
| User enumeration | Absent users burn identical hashing time |
| Open redirect | `?rd=` validated against the known-host list, forced to `https` |
| CSRF | Cross-origin POSTs to the login endpoint rejected |
| First-run setup | Reachable only from LAN, or once with a bootstrap token that self-deletes |
| Audit | Every allow/deny/login/failure as JSON, with real client IP + country |

The password and session design is lifted deliberately from
`C:\MapSnap\Application\auth.py`, which was the strongest existing implementation in
the estate — the per-tab/feature RBAC was dropped as unnecessary for a gate.

**The first-run setup lock deserves particular note.** Without it, the
account-creation screen would have been reachable by anyone on the internet during
the rollout window: whoever found it first would have owned the gate and everything
behind it. It is restricted to LAN, or to a single-use bootstrap token that is
deleted the moment an administrator account exists.

---

## 5. Verification performed

All checks were run against the **real public URLs over the internet**, not
localhost. Reproduce with `python C:\QIH\engine\gate\verify_gate.py`.

| Check | Result |
|---|---|
| 18/18 protected + mixed hosts bounce anonymous callers to the login page | **Pass** |
| 18/18 reachable when signed in (proves the wall opens, not just that it blocks) | **Pass** |
| `POST /maia/webhook`, `/maia/tg-webhook` still reach Maia | **Pass** — HTTP 400/200 from Maia's own signature check, not the gate |
| `POST /webhook/telegram` still reaches Naya | **Pass** |
| `/panel`, `/memory`, `/history`, `/export`, `/admin/scan-groups` | **Pass** — all now redirect to login |
| Unknown `Host` header | **Pass** — 404, no app reached |
| Wrong password | **Pass** — rejected |
| `QI_Gate` stopped → protected hosts | **Pass** — 502, fails **closed**, never open |
| `QI_Gate` stopped → webhook paths | **Pass** — still 400 from Maia, bots survive a gate outage |
| `QI_Gate` restarted | **Pass** — wall returns, sessions survive (SQLite, not memory) |
| Both services set to `Automatic` start | **Pass** |

---

## 5a. Regression found and fixed during rollout — mixed content

**Reported by the owner mid-rollout:** NEXUS rendered unstyled through the tunnel
and showed *"Connection to the server was lost. Attempting reconnection…"*. It was
correct on `http://localhost:7880`. **The gate caused this.**

**Root cause.** Every public host is HTTPS at the Cloudflare edge, but the
cloudflared → Caddy hop is plain HTTP. Caddy therefore passed
`X-Forwarded-Proto: http` to the app. Gradio builds absolute asset URLs from that
header, so on an `https://` page it emitted:

```
http://nexus.quiddityinnovations.com/theme.css?v=...
```

Browsers block that as mixed content. The result was a failed CSS preload **and** a
failed heartbeat stream — the app never hydrated. Diagnosed from the browser console;
the `403` on `/queue/join` was a red herring (identical with and without the gate).

**Fix.** Force the header on every upstream, in `gen_caddyfile.py`:

```
reverse_proxy <app> {
    header_up X-Forwarded-Proto https
    header_up X-Forwarded-Host {http.request.host}
}
```

**Why it matters beyond NEXUS.** This was latent for *every* app that builds absolute
URLs — all four Gradio UIs (NEXUS, Naya, Maia demo, M2V). Only NEXUS was noticed.
The same root cause had already been fixed inside the gate's own login redirect
earlier in the session; it was not initially generalised to the upstreams.

**Lesson for future edge changes:** an HTTP-level check (status codes, byte sizes)
would **not** have caught this — the HTML was byte-identical. It only appeared at
runtime in a browser. `verify_design.py` was written in response, and a browser pass
over every JS-heavy app is now part of the procedure.

### Post-fix design verification (all 11 running apps, in a real browser)

| App | CSS rules loaded | `http://` refs | Runtime errors |
|---|---:|---:|---|
| QI Hive | 3,988 | 0 | none |
| NEXUS | 1,642 | 0 | none *(was: broken)* |
| Naya | 1,914 | 0 | none |
| MapSnap | 366 | 0 | none |
| Maia demo | 449 | 0 | none *(shows its own login — layered auth)* |
| CogniBase | 168 | 0 | none |
| TubeScout | 72 | 0 | none |
| LotteryWiz | 297 | 0 | none |
| CypherMiner | 165 | 0 | none |
| Gamez / World Cup | 310 | 0 | none |
| Kaze | 100 | 0 | none |

`verify_design.py` additionally fetches every host both through the gate and
straight at its app port and diffs them — all running apps match (deltas of 15–20
bytes on Gradio hosts are its per-request session hash).

M2V, AutoPDF, `quiddam.com` and `dev.quiddam.com` return 502 because **those apps
were already stopped before this work began** — not a regression.

---

## 5b. Separate finding — the QI-Hive GitHub repository is PUBLIC

Discovered while preparing to commit this work.

`https://github.com/Quiddity-Innovations/QI-Hive` is **public**, with **797 files
published**. Among them, the full internet-facing topology:

| Published file | Public hostnames named |
|---|---:|
| `ecosystem/qi_registry.json` | 20 |
| `ecosystem/QI_Service_Registry.md` | 17 |
| `engine/tunnels/2_REGISTER_WEBHOOKS.bat` | 10 |
| `engine/tunnels/RUN_ALL.bat` | 8 |
| `shared/documentation/QI_Bot_Roster.md` | 7 |
| `engine/hive/dashboard/static/links.json` | 5 |
| `engine/tunnels/tunnels.json`, `static_urls.py`, `tunnel_manager.py`, others | 2 each |

**This is a plausible answer to "how did anyone find my applications?"** Nobody had
to guess hostnames — the complete inventory was published on GitHub, next to
applications that required no password. Search engines and the many bots that scrape
GitHub for infrastructure hostnames index exactly this.

**Credential scan of the public tree: clean.** No API keys, tokens, JWTs, AWS keys,
LINE channel secrets or Telegram bot tokens were found. The three pattern matches
were prose ("password manager:") and a Python variable reference
(`password=self.password`), not values.

### Action taken

**The commit for this work was deliberately NOT pushed.** It contains a precise map
of what is exposed, which four hosts remain unauthenticated, and how the defence is
built — a roadmap for an attacker if published. It is committed locally
(`10564f4`) and held.

Verified that `QI_NightlyGitSync` covers only `C:\AutoPDF`, `C:\PersonalSong` and
`C:\M2V`, so **`C:\QIH` will not be auto-pushed**. The commit will stay local until
the owner decides.

### Decision required from the owner

1. **Make `QI-Hive` private** (recommended — it is internal infrastructure, not a
   product), then push; **or**
2. **Keep it public** and first scrub hostnames/topology from the tracked files,
   keeping this security document out of the repository entirely.

Note that making the repo private does **not** unpublish what is already indexed;
the hostnames should be considered permanently known. That is acceptable now that
every one of them requires a login — which is precisely why the gate mattered.

Other Quiddity repositories should be reviewed for the same issue.

---

## 6. Residual risk

1. **Two hosts remain `open`** (down from four — see §9).
   - `connector.quiddityinnovations.com` — **permanent, deliberate exception.** It
     carries its own bearer/capability auth and an MCP client cannot log in through a
     browser.
   - `oc-line.quiddityinnovations.com` — **still genuinely open.** Probing found `/`,
     `/health`, `/webhook`, `/line/webhook` and `/status` all returning 200 while
     `/api` returns 404: that is a catch-all handler, so a path probe cannot separate
     real routes from a fallback, and the gateway may dispatch on request body rather
     than path. It fronts live OpenClaw agents (Tasuke, Kaze, Yubin, Sentry), so
     gating it on a guess risks breaking them. **Needs the Node routing table inside
     WSL (`~/.openclaw`) read before it can move to `mixed`.**

2. **Single factor.** One password now fronts the estate. The natural upgrade is
   **Cloudflare Access (Zero Trust)** in front of the tunnels — free to 50 users,
   adds email OTP or SSO, and blocks at Cloudflare's edge so hostile traffic never
   reaches the house. QI Gate would remain as the second layer. Not done here because
   it requires Cloudflare dashboard/API access with Access permissions.

3. **Caddy is now a single point of failure** for 18 hostnames. That is the accepted
   trade for one auditable front door. `QI_Caddy` needs monitoring.

4. **The bootstrap password was set over a chat session** and is therefore recorded
   in that transcript. It should be rotated:
   `python C:\QIH\engine\gate\tools\gate_admin.py passwd Admin <new-password>`

5. **No pre-gate history exists.** Any compromise that occurred before 2026-08-05
   would leave no trace in these logs. If there is reason to suspect one, application
   databases and credentials — not tunnel logs — are where to look.

---

## 7. Recommended next actions

| Priority | Action |
|---|---|
| High | Rotate the bootstrap admin password |
| High | Enumerate routes for Claude Voice, OpenClaw gateway and MQ API; move to `mixed` |
| High | Review `python gate_admin.py suspects 24` for a few days — this is the first real visibility into who is knocking |
| Medium | Add Cloudflare Access in front of the tunnels for MFA and edge blocking |
| Medium | Rotate any credential that was reachable from an exposed endpoint, on the assumption it may have been read |
| Medium | Add `QI_Gate` + `QI_Caddy` to the Hive health check and monthly self-audit |
| Low | Give the gate a password-change screen so rotation doesn't need the CLI |

---

## 8. Files created or modified

**Created**
- `C:\QIH\engine\gate\qi_gate.py` — identity service
- `C:\QIH\engine\gate\gate_auth.py` — users, passwords, sessions
- `C:\QIH\engine\gate\config\gate.json` — **the policy: single source of truth**
- `C:\QIH\engine\gate\config\Caddyfile.gate` — generated
- `C:\QIH\engine\gate\gen_caddyfile.py` — policy → Caddy config
- `C:\QIH\engine\gate\rollout_tunnels.py` — repoints tunnels from the policy
- `C:\QIH\engine\gate\verify_gate.py` — public verification
- `C:\QIH\engine\gate\install_qi_gate.py` — NSSM install via QI_Elevate
- `C:\QIH\engine\gate\tools\gate_admin.py` — user/session/audit CLI
- `C:\QIH\engine\gate\README.md` — runbook
- This document

**Modified**
- `C:\QIH\engine\proxy\Caddyfile` — imports `Caddyfile.gate`
- 13 tunnel configs in `C:\QIH\engine\tunnels\configs\` — repointed to `:9040`
  (originals backed up to `configs_backup_20260805\`)

**Services**
- `QI_Gate` — new, Automatic, `C:\QIH\engine\gate`, logs `C:\QIH\logs\qi_gate*.log`

---

## 9. Addendum — overnight continuation (2026-08-05, 01:00–01:35)

Two of the four `open` hosts were closed after their routes were enumerated. Final
state: **20 of 22 hostnames require a login** (14 `protected`, 6 `mixed`, 2 `open`).

| Host | Was | Now | Basis |
|---|---|---|---|
| `claudevoice.quiddityinnovations.com` | open | **mixed** | Routes read from `line_bot.py`: `/line/webhook`, `/health`, `/audio/{f}`, `/media/{f}` are all that exist. The media paths stay public because LINE's servers fetch from them to deliver replies; both use `os.path.basename()`, so traversal is already blocked. Its FastAPI `/docs` is now behind the wall. |
| `api.quiddam.com` | open | **mixed** | Routes read from `C:\MQ\api\main.py`: only `/health`, `/version`, `/info`. **No webhooks**, so nothing external needs to post here. `/health` left open for uptime monitoring. MQ was stopped, so the change carried no risk. |
| `oc-line.quiddityinnovations.com` | open | **open** | Catch-all handler — see §6.1. Not safe to allow-list without reading the WSL routing table. |
| `connector.quiddityinnovations.com` | open | **open** | Permanent exception — carries its own bearer auth. |

### Procedural bug found and fixed

`rollout_tunnels.py` repointed tunnels at `:9040` **without regenerating and
reloading Caddy first**, so traffic could arrive at a policy Caddy had not loaded yet.
This briefly left `claudevoice` proxying straight through unauthenticated after its
mode changed; caught in verification within seconds. The script now reloads Caddy
first and **aborts the rollout if the reload fails**, so the window cannot reopen.

### First external traffic observed at the gate

The access log recorded its first hits from outside the house — both **denied** at
the login wall:

| IP | Country | Path | Result |
|---|---|---|---|
| `43.164.1.211` | TH | `/` | denied |
| `43.166.224.244` | US | `/` | denied |

Both are Tencent Cloud ranges, consistent with the automated scanning in §2. **This is
exactly the visibility that did not exist before** — under the old setup these would
have reached the applications and left no record at all.

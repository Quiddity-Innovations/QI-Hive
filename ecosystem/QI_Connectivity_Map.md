# QI Connectivity & Endpoints Map

*Created 2026-08-07 · Owner: Renne Santiago / Quiddity Innovations*
*Every fact below was verified against the running machine on 2026-08-07, not copied from older docs.*

**Regenerate the mechanical parts:**
```
python C:\QIH\ecosystem\qi_collect_connectivity.py C:\QIH\ecosystem\connectivity.json
```
That dumps live services, listening ports, tunnel configs, gate hosts and hub usage to JSON.
The *analysis* sections (integration contracts, fallback posture, risks) are hand-derived —
re-check them by reading the code, not by re-running the collector.

**Companion documents**
- `QI_Ecosystem_Map.md` — family/taxonomy view and project profiles
- `QI_Service_Registry.md` — NSSM service parameters and symptom→log lookup
- `qi_registry.json` — machine-readable port allocations
- `C:\QIH\docs\QI_LLM_Hub.md` — per-tool LLM Hub adoption guide
- `C:\QIH\engine\gate\README.md` — QI Gate design and admin

---

## 1. The public path — how the internet reaches a QI app

```
Browser
  └─► Cloudflare edge  (DNS + TLS; Cloudflare Access on selected hosts)
        └─► cloudflared tunnel   (16 named tunnels, one per project)
              └─► Caddy :9040    ← QI Gate edge, host-based routing
                    ├─► forward_auth to QI Gate :9041   (is this caller signed in,
                    │                                    and allowed on THIS host?)
                    └─► reverse_proxy to 127.0.0.1:<app port>
```

Every public hostname except one terminates at **Caddy :9040**. Caddy asks
**QI Gate :9041** whether the caller may pass, then proxies to the app on loopback.

**The one exception:** `connector.quiddityinnovations.com` routes straight to
`127.0.0.1:9030`, bypassing the gate entirely. It is `mode: open` and carries its
own bearer token. This is the only host the internet reaches without the gate —
treat that token as a production credential.

---

## 2. Public hosts (22)

`protected` = sign-in required on every path.
`mixed` = sign-in required except the listed public paths (machine callbacks that
verify their own signatures).
`open` = no gate.

| Host | Mode | Upstream | App | Public paths | Tunnel |
|---|---|---|---|---|---|
| `hive.quiddityinnovations.com` | protected | `127.0.0.1:8600` | QI Hive Dashboard | — | `qi-hive` |
| `cognibase.quiddityinnovations.com` | protected | `127.0.0.1:8650` | CogniBase | — | `qi-cognibase` |
| `mapsnap.quiddityinnovations.com` | mixed | `127.0.0.1:9876` | MapSnap | `/mcp` | `qi-mapsnap` |
| `tubescout.quiddityinnovations.com` | protected | `127.0.0.1:8503` | TubeScout | — | `qi-tubescout` |
| `nexus.quiddityinnovations.com` | protected | `127.0.0.1:7880` | NEXUS Gradio UI | — | `qi-nexus` |
| `naya.quiddityinnovations.com` | protected | `127.0.0.1:7861` | Naya Gradio UI | — | `qi-naya` |
| `lottery.quiddityinnovations.com` | protected | `127.0.0.1:8777` | LotteryWiz | — | `qi-lotterywiz` |
| `cypher.quiddityinnovations.com` | protected | `127.0.0.1:7842` | CypherMiner | — | `qi-cypherminer` |
| `worldcup.quiddityinnovations.com` | protected | `127.0.0.1:8710` | Gamez / World Cup | — | `qi-gamez` |
| `m2v.quiddityinnovations.com` | protected | `127.0.0.1:7841` | M2V | — | `qi-m2v` |
| `autopdf.quiddityinnovations.com` | protected | `127.0.0.1:6969` | AutoPDF | — | `qi-autopdf` |
| `maia-demo.quiddityinnovations.com` | protected | `127.0.0.1:7860` | Maia Gradio demo | — | `qi-maia` |
| `kaze.quiddityinnovations.com` | protected | `127.0.0.1:18800` | Kaze (OpenClaw news) | — | `qi-kaze` |
| `quiddam.com` | protected | `127.0.0.1:7840` | Maia Quiddam UI | — | `qi-mq` |
| `dev.quiddam.com` | protected | `127.0.0.1:7849` | Maia Quiddam dev | — | `qi-mq` |
| `maia.quiddityinnovations.com` | mixed | `127.0.0.1:8001` | Maia API | `/maia/` `/health` `/version` | `qi-maia` |
| `maia.quiddam.com` | mixed | `127.0.0.1:8001` | Maia API (alias) | `/maia/` `/health` `/version` | `qi-mq` |
| `naya-line.quiddityinnovations.com` | mixed | `127.0.0.1:8002` | Naya webhook | `/webhook/` `/health` | `qi-naya` |
| `claudevoice.quiddityinnovations.com` | mixed | `127.0.0.1:8721` | Claude Voice (LINE) | `/line/webhook` `/health` `/audio/` `/media/` | `qi-claudevoice` |
| `oc-line.quiddityinnovations.com` | mixed | `127.0.0.1:18789` | OpenClaw gateway (WSL) | `/line/webhook` `/health` | `qi-kaze` |
| `api.quiddam.com` | mixed | `127.0.0.1:8500` | MQ API | `/health` | `qi-mq` |
| `connector.quiddityinnovations.com` | **open** | `127.0.0.1:9030` | QI Connector (remote MCP) | *(all — no gate)* | `qi-connector` |

**Cookie domains.** The gate session cookie is issued for `.quiddityinnovations.com`,
so one sign-in covers all 19 hosts on that domain. `quiddam.com`, `dev.quiddam.com`,
`maia.quiddam.com` and `api.quiddam.com` are a **separate registrable domain** and get
a host-only cookie — same username and password, but a second sign-in. Unavoidable
with cookies.

---

## 3. QI Gate

| Component | Port | Bind | Notes |
|---|---|---|---|
| Caddy edge | 9040 | **0.0.0.0** | All tunnels terminate here; host-based routing |
| QI Gate auth | 9041 | loopback | `forward_auth` target; FastAPI |

- Config: `C:\QIH\engine\gate\config\gate.json` (source of truth)
- Caddyfile is **generated** — never hand-edit:
  `python C:\QIH\engine\gate\gen_caddyfile.py`
- Users DB: `C:\QIH\engine\gate\data\gate_users.db`
- Admin CLI: `C:\QIH\engine\gate\tools\gate_admin.py`
- Sessions: 12 h default, 30 d with "remember this device". Not bound to client IP,
  so a rotating IPv6 does not sign you out.

**Per-host scoping (added 2026-08-07).** Accounts carry an `allowed_hosts` list.
Empty means every host — which is what every pre-existing account has, so the change
was backwards compatible. A scoped account gets **403** on any other host (deliberately
not a redirect, which would loop for someone already holding a valid session). Admin
accounts cannot be scoped.

```
gate_admin.py users                                    # incl. each account's scope
gate_admin.py adduser demo <pw> user maia-demo.quiddityinnovations.com
gate_admin.py hosts <name> [h1,h2 | all]
```

**Cloudflare Access sits in front of some hosts.** `hive.quiddityinnovations.com`
redirects to `quiddam.cloudflareaccess.com` *before* the request reaches the tunnel —
a second, stronger layer at Cloudflare's edge. Verify per host; it is not universal.

---

## 4. Internal service ports

NEXUS is correctly **loopback-only** — it is never tunneled directly:

| Port | Bind | Service |
|---|---|---|
| 8010 | loopback | NEXUS API / LLM Hub |
| 7880 | loopback | NEXUS Gradio UI |
| 8310 | loopback | NEXUS MCP Gateway (`QI_NexusMCP`) |

52 `QI_*` services are registered (47 running, 5 stopped as of 2026-08-07:
`QI_AutoPDF`, `QI_GamezQuantProxy`, `QI_MaiaDemoTunnel`, `QI_MapSnapBUSetup`,
`QI_RetirementAnalyzer`). Full parameters and symptom→log lookup live in
`QI_Service_Registry.md`. NSSM binary: `C:\QIH\engine\bin\nssm.exe`.

---

## 5. App-to-app connectivity — the QI LLM Hub

This is the only live app-to-app integration in the ecosystem. Every QI tool that
needs an LLM calls NEXUS instead of holding its own provider keys.

**Contract:** `POST http://127.0.0.1:8010/v1/chat/completions`
(OpenAI-compatible; any api_key; `model` = a provider id or `auto`)
Send `X-QI-App: <project>` for attribution — read it back at `GET /hub/usage`.
NEXUS also speaks **Ollama-native** (`/api/tags`, `/api/chat`, `/api/generate`), so
Ollama-based tools adopt the hub by changing one URL.

`model: "auto"` walks a benchmarked fastest-first order (measured 2026-07-02):
`cerebras → groq_gptoss → cloudflare → cf_kimi → groq → gemini → openrouter →
nim_qwen → gemma4 → nvidia_nim → cf_glm → mistral → chatgpt`

**API keys live ONLY in `C:\APPS\NEXUS\secrets\nexus.env`.** That is the point of the hub —
adopting it lets a tool drop its own keys. Never tunnel port 8010.

### Adoption and fallback posture (verified 2026-08-07)

The rule for adopting the hub is **try hub first, fall through to the tool's existing
path on any failure** — so hub mode can never make a tool less reliable than direct
mode. Not every tool honours it:

| App | How it calls NEXUS | Falls back if NEXUS is down? |
|---|---|---|
| **Maia** | `/v1/chat/completions`, `X-QI-App: maia` | ✅ Automatic — its own provider chain |
| **Naya** | same shape as Maia (+ `force_sonnet` bypass for explicit Anthropic) | ✅ Automatic — its own chain |
| **Retirement Analyzer** | hub as an entry in `config/ai_providers.json` | ✅ Automatic — one retry to local Ollama `:11434`, flagged `fallback_used` |
| **LotteryWiz** | `OLLAMA_URL` → hub, via the **Ollama shim** `/api/chat` | ✅ Automatic since 2026-08-08 — falls back to local Ollama `:11434`, emits a degraded notice (see §6.1) |
| **QI Brain** | `openai_hub` provider per agent profile | ❌ No fallback chain in the provider factory |
| **EasyFlow** | no hub code found in the repo | — not actually integrated |

**Maia's control keys** (`maia.db` config table) — the pattern others copy:

| Key | Value |
|---|---|
| `system.llm_hub_enabled` | `true` |
| `system.llm_hub_url` | `http://127.0.0.1:8010` |

### Built but never wired

`C:\APPS\QI\nexus_client.py` is a complete REST client for NEXUS `/synthesize` and
`/scout/digest`. **It is imported nowhere.** The only references are old
session-summary scripts listing it as a planned step.

Older versions of `QI_Ecosystem_Map.md` list these as live integration contracts:

| Listed as live | Reality |
|---|---|
| Maia → NEXUS `POST /synthesize` | ❌ never wired |
| Maia → NEXUS `GET /scout/digest` | ❌ never wired |
| Maia → NEXUS `GET /bench/recommend` | ❌ never wired |
| Naya → NEXUS `POST /synthesize` | ❌ never wired |

The multi-AI synthesis and Scout-digest integrations exist on **both** ends and were
never joined. Wiring `nexus_client.py` into Maia is the obvious next step if that
capability is wanted.

### MCP surface (separate from the hub)

`QI_NexusMCP` on **:8310** (loopback) exposes NEXUS to Claude and other agents —
not a Maia code path:

| Tool | Method | Path |
|---|---|---|
| `nexus_providers` | GET | `/providers` |
| `nexus_ai_digest` | GET | `/scout/digest` |
| `nexus_synthesize` | POST | `/synthesize` |

Config: `C:\APPS\NEXUS\config\mcp_gateway.json`. Sibling gateways: MapSnap `:8651`,
AutoPDF `:8701`.

---

## 6. Open risks

1. ~~**LotteryWiz is a hard dependency on NEXUS.**~~ ✅ **FIXED 2026-08-08.**
   `stream_ollama` in `C:\APPS\Lottery Wiz\server.py` is now hub-first with automatic
   fallback to local Ollama (`OLLAMA_FALLBACK_URL`, default `http://127.0.0.1:11434`;
   set empty to disable). `/api/ai/status` probes in the same order and reports
   `source: hub | local-fallback`, so a hub outage no longer makes the UI hide the
   AI feature.

   It only falls back **if no token has been emitted yet** — retrying after a partial
   stream would replay text the user already saw. A mid-stream failure surfaces as
   `stream interrupted`; both endpoints down surfaces one clear error naming both.

   Verified by simulated outage (12 checks): hub up → normal, no notice; hub dead →
   tokens still delivered from local Ollama plus a "answered by local Ollama" notice;
   both dead → single clear error, no crash; status probe falls back and reports
   `local-fallback`. Backup: `server.py.bak-fallback-20260808`.

   **All hub adopters now degrade gracefully.** QI Brain remains the exception —
   `openai_hub` per agent profile with no fallback chain — but it is barely exercised
   (2 calls logged).

2. ~~**Five gated apps also bind to `0.0.0.0`, so the LAN bypasses the gate.**~~
   ✅ **FIXED 2026-08-08** — all five rebound to `127.0.0.1`:

   | Port | App | File changed |
   |---|---|---|
   | 7860 | Maia Gradio | `C:\APPS\QI\maia_gradio.py` (`server_name`) |
   | 7861 | Naya Gradio | `C:\APPS\NAYA\naya_gradio.py` (`server_name`) |
   | 8001 | Maia API | `C:\APPS\QI\maia_server.py` (`uvicorn.run host`) |
   | 8002 | Naya webhook | `C:\APPS\NAYA\naya_server.py` (`app.run host`) |
   | 8600 | QI Hive Dashboard | `C:\QIH\engine\hive\dashboard\server.py` (`uvicorn.run host`) |

   The gate reaches all of them over loopback, so nothing public changed. Verified after
   the change: loopback 200 on all five; LAN connection refused on all five; public hosts
   still 302→login; `mixed`-mode webhook paths (`/maia/`, `/health`, `/version`,
   naya-line `/health`, claudevoice `/health`) still reach the app; `/panel` still gated.
   Backups: `*.bak-bind-20260808`. Restart is required after editing any of these —
   the bind is read at startup.

   **Standing rule:** a QI app should bind `127.0.0.1`. Public access is the gate's job.
   Binding `0.0.0.0` silently creates a second, ungated door on the LAN. Check with:
   `netstat -ano | findstr LISTENING | findstr ":<port>"` — the address must be `127.0.0.1`.

3. **`connector.quiddityinnovations.com` is `mode: open`** — the only host the internet
   reaches without the gate, protected solely by its own bearer token.

4. **One shared admin login fronts 21 of 22 hosts, no MFA.** Cloudflare Access is
   already live on `hive`; extending it to the rest is the natural upgrade.

---

## 7. Corrections to earlier documentation

Verified wrong on 2026-08-07 and superseded by this file:

| Claim | Where | Reality |
|---|---|---|
| "Only Maia has a Cloudflare Tunnel" | `QI_Ecosystem_Map.md` §Cloudflare Tunnel | 16 tunnels, 21 public hostnames |
| "Never add a tunnel to Naya, NEXUS or OC" | same | All three are already public through the gate |
| "External Access — Maia ONLY, others LAN-only" | same §Shared Infrastructure | 22 public hosts |
| NSSM binary `C:\UNIVERSAL\dashboard\nssm.exe` | same | `C:\QIH\engine\bin\nssm.exe` since 2026-04-22 |
| LotteryWiz / Retirement Analyzer "ready to flip" | same §Hub adoption | Both live — 7 and 12 hub calls logged |
| Maia/Naya → NEXUS `/synthesize` etc. | same §Integration Contracts | Never wired (see §5) |

The QI Gate (2026-08-05) was not documented in the ecosystem map at all before this file.

# QI Applications — Kubernetes Conversion Plan for BU

**Date:** 2026-08-17 · **Author:** Renne Santiago, Quiddity Innovations
**Scope:** CogniBase · MapSnap BU Edition · NEXUS — with further QI applications to follow
**Standard applied:** `QI_Kubernetes_Standard.md` (QKS) — twelve gates, one manifest shape

---

## Executive summary

BU is converting several applications to Kubernetes to leverage its AWS environment. Three QI
applications are candidates. All three are convertible. None requires a rewrite.

| Application | Convertible | Effort | Structural blocker | Ready at |
|---|---|---|---|---|
| **CogniBase** | ✅ Yes — manifests written | **Low** (days) | File-backed registries cap it at 1 replica | 1 replica, today |
| **MapSnap BU Edition** | ✅ Yes — mixed-OS | **Medium** | Unity Bridge is a Windows .NET Framework exe | 1 replica + Windows node group |
| **NEXUS** | ✅ Yes | **Medium-High** | In-process scheduler; subscription-CLI providers must be disabled | 1 replica after Phase 2 |

Rather than converting each app ad hoc, all three adopt one standard (QKS) so BU's platform team
reviews the pattern once and every subsequent QI application reuses it.

**The single most important thing to confirm with BU:** *does the EKS cluster have, or permit,
a Windows node group?* That one answer determines MapSnap BU Edition's architecture. Everything
else is ordinary engineering.

---

## 1. CogniBase — reference implementation

**Status: manifests written and committed to `C:\APPS\CogniBase\k8s\`.**

CogniBase was already built for portability: multi-stage Dockerfile, non-root user, `/health`
healthcheck, `0.0.0.0` bind, all state confined to four declared mount points. Ten of the twelve
QKS gates pass as-is.

Two facts make it the right app to lead with:

- **It already speaks both vector-store transports.** `chromadb.HttpClient(host, port)` is
  supported alongside the embedded client, so splitting the index into its own StatefulSet is a
  config change, not code.
- **It has no scheduler yet.** `Application/scheduler/runner.py` is still a placeholder, so
  scheduled work can be added as a Kubernetes `CronJob` from the start rather than untangled later.

**Outstanding before BU review** (all small, all contained):

| Item | Fix |
|---|---|
| Vendor keys live inside one `Settings/settings.json` | Add env-var override per vendor adapter — the pattern NEXUS already uses |
| Rotating logs written to `/app/LOGS` | Log to stdout |
| No `/ready` endpoint | Add one reporting vendor-registry + Chroma reachability |

**Ceiling:** one replica. The anchor, bridge and capability registries are deliberately
file-per-record JSON. This is not a defect — the workload is I/O-bound waiting on LLM calls, not
CPU-starved, so vertical scaling is appropriate. Moving those three registries to RDS Postgres is
the path to horizontal scaling when it is actually needed.

---

## 2. MapSnap BU Edition — mixed-OS deployment

MapSnap BU Edition is the most BU-relevant of the three: it already ships a real deployment
product with BU environments configured (`Product/BU_JENZABAR`, `ONBASE_GOV25`, `ONBASE_UT1_TEST`,
`ONBASE_UT2_DEV`, `JADU_GOV25`).

### 2.1 The abstraction that makes this cheap

`config/deploy.json` is already the single deployment-mode switch:

> *"THE single deployment config. Everything that varies between a laptop install and a shared
> server lives HERE; no code changes, no separate builds."*
> — `deploy_mode: "local"` (loopback, one user) · `"shared"` (IIS reverse proxy on 443)

Kubernetes becomes a **third mode**, `deploy_mode: "k8s"`. This is the extension point the file
was designed for. The security invariant of `shared` mode carries over exactly:

| `shared` mode | `k8s` mode |
|---|---|
| IIS is the only network-facing layer | Ingress is the only network-facing layer |
| IIS proxies the web UI only, never the MCP gateway | Only the web UI gets an Ingress; the MCP gateway gets a ClusterIP Service or none |
| `allowed_subnets` restricts callers | NetworkPolicy + ALB security group |
| Users authenticate against MapSnap's own accounts | Unchanged — but the session store must move (§2.4) |

### 2.2 The real constraint: the Unity Bridge is a Windows binary

MapSnap reaches BU's OnBase TEST and DEV through `kit/unity-bridge/MapSnapUnityBridge.exe`, and
this is not incidental. Per the bridge's own README, probing BU's environments on 2026-08-02 found
the App Server SOAP endpoint (`/251appserver/`) to be the **only live path** — no REST API Server,
no IdP, and because both are Hyland Cloud–hosted, **no SQL port at all**. Emulating the Unity
Client is the approach rather than a preference.

That binary is:

- **.NET Framework 4.x**, compiled with the in-box `csc.exe` — Windows-only, not .NET Core
- Dependent on **licensed Hyland assemblies** resolved from a Unity Client install folder,
  which must never be redistributed by QI
- Constrained to **one process per OnBase environment** at a time (`_EnvLock` in
  `onbase_unity.py`), because each session consumes a Unity Client licence seat

⚠️ This does not run in a Linux container, and no amount of engineering changes that.

### 2.3 Why it converts anyway

**The bridge is already invoked across a process boundary with a defined wire protocol.**
`Application/onbase_unity.py` calls it via `subprocess.Popen`, passes the password on stdin (never
argv), and reads **one JSON object per line from stdout with an explicit flush per line** — the
bridge's own comment reads *"the caller checkpoints per line."*

A subprocess boundary with a line-delimited JSON protocol converts to a network service boundary
cheaply. That is the whole conversion:

```
┌──────────────────────────────┐        ┌────────────────────────────────────┐
│  Linux node group            │        │  Windows node group (Server 2022)  │
│                              │        │                                    │
│  Deployment: mapsnap         │  HTTP  │  Deployment: mapsnap-unity-bridge  │
│  FastAPI (Python)            │ ─────► │  thin HTTP shim                    │
│  replicas: 1                 │  NDJSON│    └─ MapSnapUnityBridge.exe       │
│                              │ stream │  replicas: 1 PER ENVIRONMENT       │
│  Ingress ◄── users           │        │  (licence-seat lock)               │
└──────────────────────────────┘        └───────────────┬────────────────────┘
                                                        │ SOAP service.asmx
                                                        ▼  BU OnBase (Hyland Cloud)
```

**Work required:**

1. **HTTP shim around the bridge** — a small ASP.NET or Go wrapper that accepts the same argument
   set (`--url`, `--datasource`, `--user`, `--client-state`, `--pipeline`), takes the password in
   the request body rather than stdin, and streams the bridge's NDJSON straight through as
   `application/x-ndjson`. The bridge itself is not modified.
2. **Replace `subprocess.Popen` with an HTTP call** in `onbase_unity.py`, behind the existing
   function signatures, selected by `deploy_mode`. The `local`/`shared` subprocess path stays.
3. **`_EnvLock` becomes `replicas: 1` per environment** — one Deployment per OnBase environment,
   which enforces the licence-seat constraint structurally instead of by file lock. Cleaner than
   the current mechanism.
4. **Windows base image with the Hyland assemblies.** ⚠️ **BU must build this layer**, not QI —
   the Unity Client assemblies are Hyland-licensed and cannot be shipped by us. QI supplies the
   Dockerfile and the assembly manifest; BU supplies the DLLs from their own entitled install.
   This is a licensing conversation to open early.

**If BU has no Windows node group:** MapSnap still deploys Linux-only, serving every environment
reachable over **SQL** (pyodbc + `msodbcsql18`, which installs cleanly on Debian). BU's Hyland
Cloud TEST/DEV environments would be unavailable in-cluster until a Windows node group exists.
Note that SQL Server Integrated Auth (`Trusted_Connection=yes`) does not work from a Linux pod
without Kerberos keytab configuration — plan on SQL authentication with credentials from Secrets
Manager.

### 2.4 Other MapSnap work

| Item | Action |
|---|---|
| `Application/server.py` is **8,059 lines** in one file | Not a blocker; note it as technical debt. Do not refactor as part of this conversion. |
| Login sessions in local `mapsnap_users.db` | ⚠️ Move to RDS Postgres — this is what unlocks >1 replica for a multi-user BU deployment (QKS Gate 9) |
| `sqlite3.connect` scattered across many call sites | Consolidate into one module before the Postgres move (QKS Gate 8) |
| Chroma | ✅ Already supports `HttpClient` (`server.py:7139`) — split as per CogniBase |
| `config/secrets/onbase_service_account.json` | Replace with Secrets Manager via CSI driver |
| `blocked_environments: ["prod"]` + two-lock read-only policy | ✅ **Preserve verbatim and lead with it in security review.** A deliberate second lock, a view-only service account requirement, and a bridge binary that compiles in no write API is exactly the posture a platform team wants to see. |
| IIS, `nssm.exe`, `install.ps1`, `setup_iis.ps1` | Stay in the repo for the Windows install path; unused in-cluster |

---

## 3. NEXUS

NEXUS is the strongest architectural fit — provider fan-out orchestration — and its secrets
handling is the best of the three. It also has the most moving parts.

### 3.1 Already correct

- **Textbook 12-factor secrets.** All thirteen providers read their key from `os.environ`.
  Straight Secret injection, zero code changes. This is the pattern the other two should copy.
- **One database chokepoint.** `shared/db.py:20` is the only `sqlite3.connect` in 39k lines, so
  SQLite → RDS Postgres is a single-file change.
- **Versioned schema.** `CURRENT_VERSION = 5` + `schema.sql` maps directly onto a migration Job.
- **API and UI already separate processes.** `main.py --api-only` / `--ui-only` means two
  Deployments with no refactor.
- **`/health` exists** at `api/routers/core.py:85`.

### 3.2 The commercial decision, first

⚠️ NEXUS's `claude_max.py` and `openai_codex.py` providers shell out to the Claude Code and codex
CLIs specifically so that a **personal subscription OAuth session** carries the auth instead of a
metered API key. These cannot be containerized honestly: they depend on a user-bound session, and
mounting personal OAuth credentials into a shared cluster fails both licensing and security review.

**In-cluster, NEXUS runs on API-key providers only** — Gemini, Groq, Mistral, OpenAI, Anthropic,
Bedrock, Azure, Cloudflare. That is a per-token cost BU must accept. Raise it up front; it is a
budget conversation, not a technical surprise. Note that Bedrock via IRSA is likely the cheapest
and most BU-palatable option, since it keeps inference inside their AWS account.

### 3.3 Phased plan

**Phase 1 — runs in a pod (days)**
Write the Dockerfile (none exists). Redirect logging to stdout — `main.py` currently writes to
`data/logs/nexus.log` and the tree carries **177 MB of `LOGS/`**. Add `/ready`. Disable the
subscription-CLI providers in `config/providers.json`. Deploy API and UI as two Deployments at
`replicas: 1`, SQLite on an RWO PVC.

**Phase 2 — correct under Kubernetes (1–2 weeks)**
Extract the Scout daemon's `BackgroundScheduler` to `CronJob`s. This is mandatory before any
second replica: `core/scheduler.py` registers interval and cron jobs, and two replicas would
double every RSS, Reddit and YouTube fetch — doubling third-party quota consumption. Add the
`chromadb.HttpClient` branch to `shared/rag.py:49`, which is currently path-only. Migrate
`shared/db.py` to RDS Postgres with schema application as an initContainer.

**Phase 3 — scale (optional)**
Only if load justifies it. Note that `core/dispatcher.py:120` fans out with a single
`asyncio.gather` across providers and is I/O-bound waiting on provider HTTP — it already scales
well vertically. Distributing it across Kubernetes `Job`s would be a rewrite for little gain.
Prefer more CPU/memory per pod over more replicas.

---

## 4. Cross-cutting: what QI hands BU, and what BU supplies

**QI delivers per application:** a container image (or Dockerfile), a `k8s/` base with
Namespace/ServiceAccount/ConfigMap/PVC/Deployment/Service, a separate Ingress file BU can replace
wholesale, and a written gate audit listing every outstanding gap. No conversion is handed over
with undocumented known gaps.

**BU supplies:** ECR repositories, storage class names, ACM certificate ARNs and hostnames, IRSA
role ARNs, Secrets Manager paths, Ingress conventions, and — for MapSnap — the Windows node group
and the Hyland-licensed assembly layer.

## 5. Recommended sequence

1. **CogniBase first.** Manifests are written; it proves the QKS pattern end-to-end through BU's
   review process on the app with the fewest unknowns.
2. **Confirm the Windows node group question** in parallel — it gates MapSnap's design.
3. **MapSnap BU Edition second.** Highest business value at BU, and the `deploy_mode` abstraction
   plus the bridge's existing process boundary make it a genuine conversion rather than a rewrite.
4. **NEXUS third**, once the API-key cost position is agreed.

Every application after these three follows the same twelve gates and the same manifest shape.
That is the point of doing it this way.

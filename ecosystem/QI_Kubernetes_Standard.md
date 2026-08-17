# QI Kubernetes Standard (QKS)

**Status:** Active · **Created:** 2026-08-17 · **Owner:** Renne Santiago / Quiddity Innovations
**Applies to:** every QI application that is a candidate for deployment on a client Kubernetes
platform — starting with BU's AWS/EKS environment.

> **Why this document exists.** BU is converting several applications to Kubernetes to leverage
> their AWS environment. QI apps under evaluation: **CogniBase**, **MapSnap BU Edition**, **NEXUS** —
> with more to come. Rather than converting each app ad hoc, every QI app passes the same twelve
> gates below and ships the same manifest shape. One pattern, reviewed once by BU's platform team,
> reused by every subsequent QI app. This is the Kubernetes counterpart to `QI_Standards.md`.

---

## 0. The target platform (assumptions to confirm with BU)

| Assumption | Why it matters | Confirm with BU |
|---|---|---|
| Managed Kubernetes is **EKS** | Determines Ingress controller, storage classes, IAM model | ⬜ |
| Ingress is **AWS Load Balancer Controller** (ALB) | `ingressClassName: alb`, annotation dialect | ⬜ |
| Block storage is **EBS gp3** via `ebs.csi.aws.com` | Single-writer PVCs (RWO) | ⬜ |
| Shared storage is **EFS** via `efs.csi.aws.com` | Only needed if an app must scale past 1 replica while sharing a filesystem | ⬜ |
| Secrets come from **AWS Secrets Manager** + Secrets Store CSI driver, or External Secrets Operator | Replaces on-disk JSON secret files | ⬜ |
| Pod identity is **IRSA** (IAM Roles for Service Accounts) | No static AWS keys in the image | ⬜ |
| Registry is **ECR** | Image naming, pull secrets, scan policy | ⬜ |
| **Windows node group availability** | ⚠️ Decides MapSnap BU Edition's architecture — see its plan | ⬜ |
| Managed SQL is **RDS** (Postgres preferred) | Target for every SQLite migration | ⬜ |

Nothing below depends on these being true; they only change annotation values and storage class
names. Confirm them before writing the first manifest for a new app.

---

## 1. The Twelve Gates

An app is "QKS-compliant" and ready to hand to BU's platform team when all twelve pass.
Gates 1–6 are mandatory for *any* deployment. Gates 7–12 are required before an app may run
more than one replica.

### Gate 1 — Image
Multi-stage `Dockerfile`; a lean runtime stage; a pinned base tag (never `:latest`);
`USER` set to a non-root account; no build toolchain in the final layer.

**Reference:** `C:\APPS\CogniBase\Dockerfile` already satisfies this in full — copy its shape.

### Gate 2 — Config and secrets from the environment
Every credential is read from an environment variable. No secret is read from a file that
ships with, or is written beside, the code.

**Reference:** NEXUS is the gold standard — all thirteen providers read their key from
`os.environ` (`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `AWS_*`, `AZURE_*`, `CLOUDFLARE_*`).
Non-secret settings may come from a ConfigMap-mounted file; secrets may not.

⚠️ An app whose secrets live inside a single JSON blob (CogniBase's `Settings/settings.json`)
must gain env-var overrides before it passes this gate. That is a small, contained change and
it is not optional — mounting a whole settings file from a Secret works but fails BU review,
because rotating one key rewrites the entire file.

### Gate 3 — Bind `0.0.0.0`, one port per container
No `127.0.0.1` binds. The listen port comes from an env var with a sane default.
A container exposes exactly one port; a second port means a second container or Deployment.

### Gate 4 — Logs to stdout/stderr only
No `FileHandler` writing into the app directory. The cluster collects stdout.
An app carrying hundreds of megabytes of local `LOGS/` fails this gate.

### Gate 5 — Health endpoints
`GET /health` — liveness: process is up, no dependency checks, must never block.
`GET /ready` — readiness: dependencies (DB, vector store, provider registry) reachable.

If an app has only `/health`, add `/ready`. Using one endpoint for both causes rolling
deployments to send traffic to pods that cannot serve it.

### Gate 6 — Code directory is read-only
`readOnlyRootFilesystem: true` must hold. All writable state goes under a single path
supplied by one env var (`QI_DATA_DIR`), mounted as a volume.

⚠️ The most common violation: writing state into a directory that is also served as static
files. Audit for it explicitly.

### Gate 7 — No embedded scheduler
In-process `BackgroundScheduler` / `APScheduler` must be extracted to a Kubernetes `CronJob`,
or guarded by leader election. Two replicas running an in-process scheduler will double every
scheduled action — including paid API calls and third-party quota consumption.

### Gate 8 — Relational state in a managed database
SQLite (especially with `-wal`) is single-writer. Migrate to RDS Postgres before scaling.
Concentrate all connection handling in **one** module so the swap is one file.

**Reference:** NEXUS does this correctly — `shared/db.py:20` is the only `sqlite3.connect` in
39k lines. MapSnap and Lottery Wiz open connections in many places and need consolidating first.

### Gate 9 — Sessions are not local
Login sessions in a local SQLite table force sticky sessions. Move to the shared database,
or to signed stateless tokens.

### Gate 10 — Vector store is a network service
`chromadb.PersistentClient(path=...)` pins the app to one filesystem.
Use `chromadb.HttpClient(host, port)` against a Chroma StatefulSet.

**Reference:** CogniBase (`db_extractors.py:529`) and MapSnap (`server.py:7139`) already
support `HttpClient`. NEXUS (`shared/rag.py:49`) is path-only and needs the branch added.

### Gate 11 — Schema migrations are a Job
Versioned schema applied by an `initContainer` or a pre-install `Job`, never by racing
application replicas on startup.

**Reference:** NEXUS has `CURRENT_VERSION = 5` + `schema.sql` — the right foundation.

### Gate 12 — Resources, probes, and security context declared
Every container declares `requests` and `limits`, both probes, `runAsNonRoot`,
`allowPrivilegeEscalation: false`, and `capabilities: drop: [ALL]`.
BU's platform team will reject manifests without these, and they are the cheapest gate to pass.

---

## 2. Standard manifest shape

Every QI app ships a `k8s/` directory at its project root with this layout:

```
k8s/
  README.md                 how to deploy, and which gates are outstanding
  kustomization.yaml        base
  <app>-core.yaml           Namespace, ServiceAccount, ConfigMap, PVC, Deployment, Service
  <app>-ingress.yaml        Ingress (ALB) — separate so BU can substitute their own
  <app>-<dep>.yaml          one file per supporting service (chroma, worker, bridge)
  overlays/
    bu-dev/                 BU-supplied values
    bu-prod/
```

Rules:
- **Namespace per app**, named `qi-<app>`. Never deploy QI apps into `default`.
- **Every object carries** `app.kubernetes.io/name`, `app.kubernetes.io/part-of: quiddity`,
  and `app.kubernetes.io/version`.
- **Ingress lives in its own file.** BU's platform team owns ingress conventions, TLS, and
  hostnames; make it trivially replaceable without touching the workload.
- **No secrets in the repo.** Ship a `*.secret.example.yaml` with placeholder values and a
  comment naming the Secrets Manager path the real one comes from.
- **`imagePullPolicy: IfNotPresent`** with immutable, digest-or-version-tagged images.

---

## 3. Port and identity conventions

Container ports keep the app's registered QI port from `qi_registry.json` — this preserves
one mental model across the Windows install and the cluster, and keeps `QI_Ecosystem_Map.md`
authoritative in both worlds. The `Service` may expose 80 → containerPort.

| App | Registered port | Container port |
|---|---|---|
| CogniBase | 8650 | 8650 |
| MapSnap | 9876 (legacy) · MCP 8651 | 9876 |
| NEXUS | API 8010 · UI 7880 | 8010 / 7880 (two Deployments) |

Service DNS replaces loopback assumptions. Intra-app calls that currently use `127.0.0.1:<port>`
become `<service>.<namespace>.svc.cluster.local`. This is strictly cleaner than the current
arrangement and removes the port-collision class of problem entirely.

---

## 4. What does *not* go to Kubernetes

State the exclusions plainly; it builds credibility in a platform review.

- **NSSM services, `.bat` control scripts, `install_*.bat`** — replaced by Deployments. They
  stay in the repo for the Windows install path, which continues to exist.
- **Cloudflare tunnels** — replaced by ALB Ingress inside BU's network.
- **IIS reverse proxy** (MapSnap `shared` mode) — replaced by Ingress. The security property
  it enforces ("the proxy is the only network-facing layer") is preserved by not creating a
  Service for internal-only components.
- **Anything requiring a logged-in interactive Windows user session** — see §5.

---

## 5. The subscription-CLI constraint (read before promising a conversion)

Some QI providers reach a model through a **CLI carrying a personal OAuth session** rather
than a metered API key — NEXUS's `claude_max.py` shells out to the Claude Code CLI, and
`openai_codex.py` to the codex CLI, precisely so no `ANTHROPIC_API_KEY` is needed.

These do not survive containerization in any honest form. They depend on a user-bound
subscription session, and mounting personal OAuth credentials into a shared cluster is both
a licensing problem and a security-review failure.

**The rule:** any app offered to a client cluster must be fully functional with
**API-key providers only**. Subscription-CLI transports are a developer-workstation
optimization and must be disabled by config in the cluster build — never a dependency.
Say this to BU up front; it is a cost conversation, not a technical surprise.

---

## 6. Windows dependencies are a node-group question, not a blocker

A Windows-only component does not disqualify an app. EKS supports Windows node groups, and a
mixed-OS deployment is a normal pattern: the Linux pod runs the application, the Windows pod
runs the Windows-only component, and they talk over a `Service`.

**The prerequisite is that the component already sits behind a process boundary.** A component
invoked as a subprocess with a defined wire protocol converts to a network service cheaply. A
component called in-process via a native DLL binding does not.

MapSnap BU Edition's Unity Bridge is the former — see its conversion plan.

---

## 7. Adoption checklist for a new QI app

1. Run the twelve gates as an audit; record pass/fail per gate.
2. Fix Gates 1–6. Nothing else matters until an app runs correctly as one replica.
3. Write `k8s/` per §2 with `replicas: 1`.
4. Fix Gates 7–12 only when a second replica is actually needed.
5. Register the app's Kubernetes status in `qi_registry.json`.
6. Hand BU: the image, the `k8s/` base, and the outstanding-gate list. Never hand over a
   conversion whose known gaps are undocumented.

---

## Related

- `QI_Standards.md` — naming, folders, docs conventions
- `QI_Architecture_Principles.md` — The Six Laws
- `QI_Ecosystem_Map.md` — ports, families, integration contracts
- `QI_Service_Registry.md` — the Windows service estate this pattern does *not* replace

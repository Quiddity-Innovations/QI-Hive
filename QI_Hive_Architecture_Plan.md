# QI Hive — Architecture Overhaul Plan

**Status:** Living document · **Owner:** Renne Santiago · **Created:** 2026-09-02
**Canonical location:** `C:\QIH\QI_Hive_Architecture_Plan.md`
**Companion docs:** [QI_Architecture_Principles.md](ecosystem/QI_Architecture_Principles.md) · [QI_Standards.md](ecosystem/QI_Standards.md) · [qi_registry.json](ecosystem/qi_registry.json)

> This document is the single tracking surface for the modular overhaul.
> The calendar in §7 is **expected to change**. Reorder it freely — the wave
> structure in §6 is what matters, not the dates.

---

## 1. Executive summary

The QI ecosystem does **not** need a new architecture. It already has one: the Six
Laws and the `module_interface_contract` v1.0 in the registry. Those documents describe
exactly the hybrid independence/cooperation model being asked for.

The problem is that **nothing measures or enforces them**, so adoption has drifted:

| Measure | Reality found on 2026-09-02 |
|---|---|
| Projects fully honoring the contract (`/health` + `/version` + `/info`) | **17 of 29 evaluated** |
| Projects resolving peers through `qi_registry` instead of hardcoded ports | **14 of 29** |
| Projects with **zero** HTTP surface (contract is inapplicable as written) | **4** |
| Registry entries pointing at paths that no longer exist | **1 confirmed** (`playdeck`) |
| Real codebases missing from the registry entirely | **4** (MailBrain, Bakeoff, VLCDaemon, QI-RELAY) |
| Cross-project **direct database file reads** (no network boundary at all) | **1** (Gamez → `maia.db`) |
| Production files still hardcoding pre-migration `C:\QI\`-style paths | **5+** |

`qi_validator.py` — the existing enforcement tool — checks *file hygiene* (does
`CLAUDE.md` exist, is `secrets/` gitignored). **It never checks the contract itself.**
That is the root cause: the constitution is unmeasured, so it silently rotted. This is
the same failure mode as the 2026-08 Kaze outage — the check reported success while the
thing it guarded was dead.

**Therefore the overhaul is not a rewrite. It is: build the enforcement layer, then
adopt it app by app.**

---

## 2. Scope

### 2.1 In scope — 37 applications

**Tier 1 — Live products (registered, running, has a port)**

| # | App | Path | Ports | Contract |
|---|---|---|---|---|
| 1 | Maia | `C:\APPS\QI` | 8001 / 7860 | ✅ full + registry |
| 2 | NEXUS | `C:\APPS\NEXUS` | 8010 / 7880 / 8310 | ✅ full + registry |
| 3 | OpenClaw | `C:\APPS\OC` | 18789 (WSL) | ❌ none (Node product) |
| 4 | MapSnap | `C:\APPS\MapSnap` | 9876 / 8651 | ⚠️ sidecar only |
| 5 | AutoPDF | `C:\APPS\AutoPDF` | 6969 / 8701 | ⚠️ sidecar only, `/healthz` |
| 6 | CogniBase | `C:\APPS\CogniBase` | 8650 | ⚠️ partial |
| 7 | TubeScout | `C:\APPS\TUBESCOUT` | 8503 / 7843 | ✅ full + registry |
| 8 | NoosOrbis | `C:\APPS\NoosOrbis` | 8507 / 7847 | ✅ full + registry |
| 9 | Gamez | `C:\APPS\Gamez` | 8710 / 8712 | ⚠️ `/health` only |
| 10 | LotteryWiz | `C:\APPS\Lottery Wiz` | 8777 | ❌ tests only |
| 11 | PlayDeck | `C:\APPS\PlayDeck` | 8506 | ✅ full + registry |

**Tier 2 — Registered, idle or manual-start**

| # | App | Path | Ports | Contract |
|---|---|---|---|---|
| 12 | Naya | `C:\APPS\NAYA` | 8002 / 7861 | ✅ full + registry |
| 13 | FileHQ | `C:\APPS\NAYA\filehq` | 8000 | (absorbed into Naya) |
| 14 | Claude Voice | `C:\APPS\CLAUDE\Claude Voice` | 8720–8725 | ✅ full |
| 15 | Retirement Analyzer | `C:\APPS\Retirement Analyzer` | 8504 / 7844 | ✅ full, registry-free **by design** |
| 16 | MQ | `C:\APPS\MQ` | 8500 / 7840 | ✅ full + registry |
| 17 | M2V | `C:\APPS\M2V` | 8501 / 7841 | ✅ full |
| 18 | SynVox | `C:\APPS\SynVox` | 8751 / 8753 | ✅ full + registry (envelope cited by name) |
| 19 | MediaStudio | `C:\APPS\MediaStudio` | 7864 | ✅ full + registry |
| 20 | VoiceStudio | `C:\APPS\VoiceStudio` | 7863 | ✅ full + registry |
| 21 | FilmForge | `C:\APPS\FilmForge` | — (CLI) | ❌ no HTTP surface |
| 22 | PersonalSong | `C:\APPS\PersonalSong` | 8088 | ⚠️ `/health` only |
| 23 | AvatarStudio | `C:\APPS\AvatarStudio` | 7862 | ❌ Gradio only |
| 24 | AkiyaScout | `C:\APPS\AkiyaScout` | 8505 / 7845 | ✅ full + registry |
| 25 | EasyFlow | `C:\APPS\EasyFlow` | 8550 | ❌ asserted in tests, not implemented |
| 26 | Mythologies | `C:\APPS\Mythologies` | — (static) | ❌ no server |
| 27 | ComfyUI (QI Media Engine) | `D:\AI` | 8740 | ❌ third-party |

**Tier 3 — Infrastructure**

| # | Component | Path | Ports |
|---|---|---|---|
| 28 | QI Hive | `C:\QIH` | 8600 |
| 29 | QI Brain | `C:\QIH\engine\brain` | 9011 |
| 30 | QI Connector | `C:\APPS\QIP\Connector` | 9030 |
| 31 | QI Gate / Caddy | `C:\QIH\engine\gate` | 9040 / 9041 |
| 32 | Headroom | `C:\APPS\CLAUDE\Tools` | 9020 |
| 33 | Claude Manager | `C:\APPS\CLAUDE` | — |

**Tier 4 — Newly registered (were invisible to the registry)**

| # | App | Path | Note |
|---|---|---|---|
| 34 | MailBrain | `C:\APPS\MailBrain` | Gmail/Apps Script + Chrome & Edge extensions. 215 py / 73 js. Published product with an Operations Manual — and the registry had never heard of it. |
| 35 | Bakeoff | `C:\APPS\QIP\Bakeoff` | Hermes vs OpenClaw evaluation rig |
| 36 | VLCDaemon | `C:\APPS\VLCDaemon` | QVLC playback daemon |
| 37 | QI-RELAY | `C:\QI-RELAY` | Relay service |

### 2.2 Disregard List (owner decision, 2026-09-02)

Omitted entirely from all evaluation and planning. **Update this list at any time.**

- **Duplicates, backups & strays:** `AutoPDF_Portable_Dupe`, `RetirementAnalyzer-TEST`,
  `_RetirementAnalyzer_history_backup_20260826.git`, `C:\APPS\DeepSeek`, `C:\APPS\SCRIPTS`,
  `C:\APPS\config`, `C:\APPS\_hyland`, `C:\GOOSE`, `C:\1-AI`, `C:\ARCHIVE`, `C:\QI`, `C:\CLAUDE`
- **Completed / dead:** CypherMiner (`complete`), Digitization Cost Tool (`complete`),
  `universal` (zombie registry entry colliding with `qi_hive`), FileHQ (absorbed into Naya)
- **Document-only efforts:** OnBase DNA Program, Digitization Cost Tool

> `C:\OC` is **not** on this list and must never be deleted — it is a load-bearing NTFS
> junction to `C:\APPS\OC`; 386 files still hardcode the old path.

### 2.3 D:\Dev — in scope as separate copies

`D:\Dev` holds a parallel tree of ~24 of these projects. Owner decision: treat as
**separate copies requiring reconciliation**, not as a single worktree concern.
The audit in §5.5 confirmed this reading — **none are worktrees; all are independent
clones.** Reconciliation workstream and findings: §5.5.

---

## 3. Design constraints (restated as testable rules)

| # | Constraint | Testable form |
|---|---|---|
| **C1** | Absolute independence | With QI Hive, Brain, Gate, Connector and every peer **stopped**, the app starts, serves its primary user journey, and its smoke test passes. |
| **C2** | Cooperative integration | With the ecosystem up, the app is discoverable, health-aggregated, publishes its domain events, and answers capability queries — **without any code change between the two modes.** |

C1 and C2 must both be *automatically verified*, or they will rot again. That verification
is Wave 0's deliverable (§6).

### 3.1 C3 — The protection model (owner requirement, 2026-09-02)

> *"We have to protect C:\APPS and have GitHub up to date with the code, and have D:\Dev be
> another backup, in the 'just in case' scenario and also the source for installation and
> distribution beyond my environment."*

Three tiers, each with a distinct job. **GitHub is the durable protection; D:\Dev is a
convenience copy and the distribution artifact.**

```
  C:\APPS\<App>          THE GOLD — built, run and edited here.
       │                 Carries config, data, secrets, logs.
       │
       ├──► GitHub       DURABLE TRUTH. Code only, versioned, off-machine.
       │                 Survives disk loss. The real backup.
       │
       └──► D:\Dev\<App> PACKAGE. Clean, config-free, installable.
                         Local "just in case" copy AND the distribution
                         source for other environments.
```

**Testable form of C3:**

| # | Rule |
|---|---|
| C3.1 | Every in-scope project has a GitHub remote and is **0 ahead** of it. |
| C3.2 | No secret, credential, database, model weight or venv is tracked. |
| C3.3 | `D:\Dev\<App>` installs and runs on a machine that has never seen `C:\APPS` — no config, no absolute paths, no ecosystem assumed. |

**C3.3 is the same property as C1.** An app that runs with every peer down is an app whose
configuration is externalized — which is exactly what makes it installable elsewhere. The
`qi-spine` work in §4.1 therefore serves the distribution goal directly; it is not a
separate effort. Distribution is C1, observed from outside the machine.

#### Measured coverage — 28 gold projects, 2026-09-02

Audited with `git fetch` + `rev-list` against each live remote.

**✅ Protected and in sync — 19 of 28.** All at 0 ahead / 0 behind: Maia, NEXUS, MapSnap,
AutoPDF, CogniBase, TubeScout, NoosOrbis, Gamez, LotteryWiz, Naya, Retirement Analyzer, MQ,
M2V, SynVox, PersonalSong, AvatarStudio, EasyFlow, MailBrain\*, Claude Manager\*.
*Push discipline is good — the gap is coverage, not habit.*

#### ✅ Automated protection already exists — and it works

**`QI_NightlyGitSync`** (`C:\QIH\tools\nightly_git_sync.py`, scheduled 12:35 AM, after
MaiaNightlySync at 12:30) stages, commits and pushes **21 repos** every night, behind a
`secret_gate` that aborts a push if a real secret is staged. It ran successfully at
**2026-09-02 00:35** and pushed.

It also does the right thing at the end — names its own gaps rather than reporting success:

```
WARN 3 registry repo(s) sync nowhere: akiyascout (C:\APPS\AkiyaScout),
     claude_manager (C:\APPS\CLAUDE), openclaw (C:\APPS\OC)
```

Its `NOT_SYNCED` map states each exclusion and why — including that Claude Manager's 38,499
committed venv files need "a decided cleanup first — that is Renne's call, not a side effect
of enabling sync" (recorded 2026-08-27). **Wave 0.10 is therefore not a new discovery; it is
an already-diagnosed decision that has been waiting on the owner.**

#### ❌ The real gap — and why it stayed invisible

**OpenClaw is protected.** `C:\APPS\OC\repo\` is its own clone of
`rennesan/OC-Orchestrator` (master, HEAD `6569930`) and syncs there. The parent having no
remote is **by design**, documented in both `nightly_git_sync.py` and the 2026-08-27 task
health audit. *(Corrects an earlier 🔴 in this document — OpenClaw was never unprotected.
It does carry 49 dirty files in `repo/`.)*

**QI Connector and Mythologies are protected too** — via sub-repos an earlier pass missed
(`Quiddity-Innovations/QI-Connector`; `rennesan/mythologies-map` + `mythologies-pipeline`).

That leaves **two known gaps** the tool already reports:

| Project | Problem | Severity |
|---|---|---|
| **Claude Manager** | 38,499 committed venv files block sync; 6 unpushed commits, 80 real changes | 🟠 Blocked on a decision, not unknown |
| **AkiyaScout** | Repo, no remote, **zero commits ever**, 15 untracked | 🟠 |

…and **six that nothing has ever reported**, because they have no `.git` at all:

| Project | Problem | Severity |
|---|---|---|
| **MediaStudio** | No repo | 🔴 |
| **VoiceStudio** | No repo. Holds biometric voice samples | 🔴 |
| **FilmForge** | No repo | 🔴 |
| **PlayDeck** | Repo, no remote, 7 dirty | 🟠 |
| **Bakeoff** (`QIP\Bakeoff`) | Repo, no remote, 12 dirty | 🟠 |
| **VLCDaemon** | No repo | 🟢 |

> **🔎 Root cause — a blind spot in the coverage check.** `coverage_check()` enumerates
> *registry repos that sync nowhere*. A project with **no `.git` directory at all** is not a
> repo, so it is never counted, never warned about, and never appears in the nightly log.
> MediaStudio, VoiceStudio and FilmForge are all registered, all active, and all invisible
> to the very check designed to catch this.
>
> **Fix (Wave 0.9):** make the check assert on *registry membership*, not on repo-ness —
> "every in-scope registry project has a remote and is 0 ahead", so a missing `.git` is a
> loud failure rather than an absence. This is the same class of bug as the `conhost` exit
> codes: the monitor could only see the things that were already half-working.

**⚠️ Protected but compromised — 2:**

- **Claude Manager** — 6 unpushed commits and 937 dirty files. **But 38,499 venv files are
  tracked** (`Tools/headroom_env/Lib/site-packages/`), and 754 of the 834 "modified" are
  that venv churning against CRLF conversion with no `.gitattributes`. **Only 80 files are
  real changes.** Fix is `git rm -r --cached Tools/headroom_env` + `.gitignore` +
  `.gitattributes` — then 80 files and 6 commits to land. Violates **C3.2**.
- **MailBrain** — pushes to `Quiddity-Innovations/EasyFlow`, and is **2 commits behind it**.
  Confirms it is a stale EasyFlow clone, not a repo of its own (§5.5).

#### C3.4 — Remote ownership normalized under `Quiddity-Innovations` (owner decision, 2026-09-02)

All QI repositories live under the **`Quiddity-Innovations`** org. `rennesan/*` is retired
as a code home. Currently 21 org repos and 8 personal; **7 to transfer:**

| # | From | To | Note |
|---|---|---|---|
| 1 | `rennesan/mapsnap` | `Quiddity-Innovations/MapSnap` | private |
| 2 | `rennesan/cognibase` | `Quiddity-Innovations/CogniBase` | private |
| 3 | `rennesan/Gamez` | `Quiddity-Innovations/Gamez` | private |
| 4 | `rennesan/synvox` | `Quiddity-Innovations/SynVox` | private |
| 5 | `rennesan/OC-Orchestrator` | `Quiddity-Innovations/OpenClaw` | private; also wire the disconnected local (above) |
| 6 | `rennesan/mythologies-pipeline` | `Quiddity-Innovations/mythologies-pipeline` | private |
| 7 | `rennesan/mythologies-map` | `Quiddity-Innovations/mythologies-map` | ⚠️ **PUBLIC** — see below |

`MatrAIx-Persona-8B` is a fork of someone else's work; leave it on `rennesan`.

**Use GitHub's Transfer, not create-and-push.** Transfer preserves history, issues, stars
and — critically — installs a **redirect from the old URL**, so nothing breaks at the moment
of the move. Re-creating and pushing loses all of that.

**⚠️ Blast radius — 40+ references, not the 9 first reported.**

*(An earlier full-tree sweep returned "0 matches"; it had actually hit its timeout and the
zero was an artifact. A correct ripgrep sweep found the following. Do not trust that earlier
figure.)*

| Location | What | Impact |
|---|---|---|
| `C:\QIH\ecosystem\qi_registry.json` | 5 refs (`cognibase`, `mapsnap`, `mythologies-map` ×2, `mythologies-pipeline`) | Update **with** the change — Law 5 |
| `C:\QIH\tools\nightly_git_sync.py` | OC-Orchestrator exclusion comment | ⚠️ **Unattended job** — review so the nightly sync doesn't drift |
| `C:\QIH\landing\index.html` | 2 live links (cognibase, mapsnap) | Public landing page; `QI-Hive` repo is **PUBLIC** |
| `C:\APPS\CogniBase\pyproject.toml` | `Homepage`, `Issues` | **Ships in package metadata** — goes out with any distribution |
| `C:\APPS\CogniBase\` README, DEPLOYMENT, CHANGELOG | ~9 clone/install refs | User-facing install instructions |
| `C:\APPS\SynVox\docs\` + handoff/session prompts | **~18 refs** | ⚠️ See collaborator warning below |
| `C:\APPS\Mythologies\` CLAUDE.md, HANDOFF-PROMPT, packs README | 6 refs | Includes a `gh repo edit` command and dashboard Settings→Git path |
| `C:\APPS\OC\` tools + session summaries | 6 refs | Historical/log text, low impact |
| `...\migration_2026-08\phase2\rollback_requirements-old.txt` | `pip install -e git+…/cognibase.git` | A dependency pin |
| Local `.git/config` remotes | 7 | `git remote set-url` after transfer |

GitHub redirects keep everything **functional** through the move, so this is Tier 2 — warn,
then proceed. But redirects don't fix documentation, and two items need handling first.

**⚠️ SynVox has an external collaborator.** `rennesan/synvox` has **Urcil (UpStartGuy59)**
as a *read* collaborator (invited 2026-08-19), with a documented fork-and-PR workflow across
four files — `SynVox_Setup_Prompt_For_Urcil.md`, `SynVox_Install_For_Urcil.md`,
`HANDOFF_NEXT_SESSION.md`, `SESSION_3_PROMPT.md`. A transfer to the org **does not carry a
personal-repo collaborator grant forward the same way**, and his fork's `upstream` remote
plus any open PRs point at the old location. **Re-grant his access in the org and tell him
before transferring** — this one affects another person, not just a URL.

**⚠️ `mythologies-map` is PUBLIC and is the deployed site source.** If it is served via
GitHub Pages, confirm the Pages configuration and any custom domain survive the transfer
**before** moving it — Pages settings do not always follow a transfer cleanly. Move this one
last, on its own, after the other six are verified.

**⚠️ `mythologies-map` is PUBLIC and is the deployed site source.** If it is served via
GitHub Pages, confirm the Pages configuration and any custom domain survive the transfer
**before** moving it — Pages settings do not always follow a transfer cleanly. Move this one
last, on its own, after the other six are verified.

#### C3.5 — Is `rennesan/*` a valid backup of `Quiddity-Innovations/*`?

**Mechanically yes. As a backup, no — and it should not be relied on as one.**

| Failure it protects against | Covered? |
|---|---|
| Accidental force-push or history rewrite | ✅ Yes |
| Accidental repo deletion | ✅ Yes |
| Org billing lapse / plan change | ✅ Yes |
| **GitHub outage or data loss** | ❌ No — same provider |
| **Account compromise or suspension** | ❌ No — `rennesan` *owns* the org; one credential controls both |
| **Loss of access to GitHub entirely** | ❌ No |

The account that owns `rennesan/*` is the same account that owns the org. There is no second
account ([[project_github_account_2fa]]). A copy inside the same provider under the same
credential is a **mirror, not a backup**: mirrors protect against *your* mistakes, backups
protect against the *provider's*.

**Recommended instead — and it fits the existing tier model:**

`D:\Dev` is already the "just in case" tier on a **different physical disk**. Give it real
restore capability by writing a **`git bundle`** alongside each package:

```
git bundle create D:\Dev\<App>\<App>.bundle --all
```

One file, full history, all branches. Restores anywhere with `git clone <App>.bundle`. It is
independent of GitHub, independent of the account, and independent of the C: drive — which
is exactly the failure set the org-mirror cannot cover. Fold it into the Wave 0.12 packaging
refresh so every package ships with its own history.

*If a GitHub-side mirror is still wanted for the narrow cases it does cover, add it as a
second push remote — cheap and automatic. Just don't count it as the backup.*

---

## 4. Target architecture — the QI Mesh

Four layers. Nothing here replaces the Six Laws; it makes them executable.

```
┌────────────────────────────────────────────────────────────────┐
│  L3  QI HIVE — orchestrator                                    │
│      registry service · health aggregation · capability        │
│      catalog · event fan-out · MCP aggregation · unified shell │
│      ⚠️ CONSUMES apps. Is never a dependency of one.            │
└───────────────┬────────────────────────────────────────────────┘
                │  (optional — every arrow below degrades to a no-op)
┌───────────────┴────────────────────────────────────────────────┐
│  L2  THE BUS — file-backed event journal (C:\QIH\data\bus\)    │
│      append-only SQLite/WAL · fire-and-forget · no daemon      │
└───────────────┬────────────────────────────────────────────────┘
┌───────────────┴────────────────────────────────────────────────┐
│  L1  DISCOVERY & CONTRACT                                      │
│      /health /ready /version /info /capabilities · envelope    │
│      peers.json cache · env override · hardcoded fallback      │
└───────────────┬────────────────────────────────────────────────┘
┌───────────────┴────────────────────────────────────────────────┐
│  L0  qi-spine — ONE installable package + a vendored stub      │
│      contract · discovery · client · events · capability       │
└────────────────────────────────────────────────────────────────┘
        ▲            ▲            ▲            ▲
      Maia         NEXUS       MapSnap      …37 apps
   (each fully standalone if every layer above is absent)
```

### 4.1 L0 — `qi-spine`: one package, not 8 vendored copies

**The problem it fixes.** `qi_mcp_gateway.py` is currently *copy-pasted* into at least
eight projects. A fix in the canonical copy at `C:\QIH\engine\common\` does not reach any
of them. That is the vendoring anti-pattern, and it is how drift happens.

**The package.** `C:\QIH\engine\spine\` → `pip install -e` into each project's venv.

| Module | Responsibility |
|---|---|
| `qi_spine.contract` | Framework-agnostic mixin mounting `/health /ready /version /info /capabilities` + the standard envelope. Adapters for **FastAPI**, **Flask**, **Gradio**, and **raw `http.server`** (MapSnap, CogniBase need this one). |
| `qi_spine.discovery` | `QI.url("nexus")` — resolves via `config/peers.json` cache → registry → env var → **hardcoded default**. Never raises. |
| `qi_spine.client` | Peer HTTP client with a circuit breaker. **`fallback=` is a required argument** — you cannot construct a peer call without one. Law 3 enforced by the signature, not by discipline. |
| `qi_spine.events` | Bus publish/subscribe. Publish is fire-and-forget and never blocks. |
| `qi_spine.capability` | Declares what verbs this app exposes to the Hive. |
| `qi_spine.selftest` | The C1/C2 conformance suite the app runs against itself. |

**How C1 survives.** `qi-spine` is an **optional** dependency. Every repo also vendors a
~60-line `qi_spine_stub.py` implementing the same surface offline:

```python
try:
    from qi_spine import Spine
except ImportError:
    from qi_spine_stub import Spine     # standalone mode — identical surface

spine = Spine.attach(app, project="noosorbis", version=__version__)
```

The stub returns hardcoded local defaults for discovery, no-ops the bus, and still mounts
the contract endpoints. **An app with no ecosystem present behaves identically to one
with it, minus the cooperation.** That is C1 satisfied structurally rather than by
convention.

### 4.2 L1 — Contract v2

Additive over v1.0. Nothing existing breaks.

| Endpoint | New? | Returns |
|---|---|---|
| `GET /health` | v1 | `{"status":"ok"}` — liveness |
| `GET /ready` | **v2** | dependency readiness, each marked `required` or `optional`. A missing *optional* peer must still return `ready: true`. This is where C1 becomes observable. |
| `GET /version` | v1 | `{project, version, status}` |
| `GET /info` | v1 | registry entry |
| `GET /capabilities` | **v2** | verbs offered to the ecosystem, e.g. `{"verbs":[{"name":"summarize","path":"/api/summarize","method":"POST"}]}` |

**Sidecar rule.** Contract endpoints must live on the **app's own primary port**.
MapSnap, AutoPDF and CogniBase currently satisfy the contract only via a separate MCP
gateway sidecar on a different port — that answers an MCP client but not a peer doing a
plain health check. Wave 2 fixes this.

**Discovery cache.** `qi-spine sync` writes `config/peers.json` into each app from the
registry. The app reads the cache, not the registry, at runtime — so it starts fine when
`C:\QIH` is unreachable. Staleness is caught by the conformance test, not at runtime.

### 4.3 L2 — The bus: a file, not a server

Registry currently records *"No internal message bus today. Future: Redis Pub/Sub or a
simple SQLite queue."*

**Recommendation: the SQLite journal, explicitly not Redis.** Redis is another daemon
that can be down, and an app that needs it to publish is no longer independent — it
violates C1 at the infrastructure level. A file-backed journal cannot be "down" while the
filesystem exists.

- **Location:** `C:\QIH\data\bus\<topic>.db` — append-only, WAL mode
- **Publish:** append a row. Works with zero subscribers, zero Hive, zero network.
- **Subscribe:** long-poll the Hive `/bus/subscribe?topic=&after=<seq>`, or tail the file
  directly if the Hive is down.
- **Topic grammar:** `qi.<project>.<entity>.<verb>` — e.g. `qi.tubescout.video.discovered`,
  `qi.autopdf.document.extracted`, `qi.mapsnap.schema.changed`
- **Rule:** publishing is fire-and-forget. An app must never block, retry-loop, or fail a
  user request because of the bus.
- **Retention:** 30 days, trimmed by the existing `QI_TaskHealth` schedule.

This is what replaces patterns like Gamez opening `maia.db` directly.

### 4.4 L3 — QI Hive: orchestrator, never a dependency

Hive's job: serve the registry, aggregate health, catalog capabilities, fan out events,
aggregate MCP, and host the unified shell. Much of this already exists
(`engine/brain`, `engine/hive/inspector`, `engine/gate`, `engine/mcp`).

**The rule that keeps it honest — Chaos Hour.** A scheduled job that stops
`QI_Dashboard`, `QI_BrainAPI`, `QI_Gate`, `QI_Caddy` and `QI_ConnectorMCP`, then runs
every app's C1 smoke test, then restarts them. Any app that fails has violated
independence and gets a ticket.

⚠️ **This job must health-check its outcome artifact, not its exit code** — every QI
scheduled task runs under `conhost --headless`, which always returns 0. See
`check_digest_freshness()` in `C:\APPS\OC\tools\oc-keepalive-daemon.py` for the pattern.

---

## 5. Per-application evaluation

### 5.1 Structural classes

The 37 apps are not one problem. They are five, and each needs a different treatment:

| Class | Apps | Treatment |
|---|---|---|
| **A — Compliant FastAPI** | Maia, NEXUS, TubeScout, NoosOrbis, PlayDeck, MQ, M2V, AkiyaScout, MediaStudio, VoiceStudio, SynVox, Naya, Connector, Claude Voice, Retirement Analyzer | Swap hand-rolled endpoints for `qi-spine`. ~1 hour each, batchable 5–6 per sprint. |
| **B — Hand-rolled HTTP** | MapSnap, CogniBase, AutoPDF | Contract lives on a sidecar port. Needs the `http.server`/Electron adapter, then move endpoints onto the primary port. ~1 sprint each. |
| **C — Partial / missing** | Gamez, LotteryWiz, PersonalSong, EasyFlow | Contract absent or asserted-in-tests-only. Add spine + fix coupling. |
| **D — No HTTP surface** | FilmForge (CLI), Mythologies (static), AvatarStudio (Gradio), OpenClaw (Node), MailBrain (Apps Script/extension), VLCDaemon | **The REST contract does not apply.** They get the *sidecar-or-heartbeat* pattern (§5.3). |
| **E — Third-party** | ComfyUI | Wrap, never modify. A thin `qi-spine` shim in front of it. |

### 5.2 Specific technical improvements

| App | Finding | Recommended change |
|---|---|---|
| **Gamez** | `proxy/server.py:115` opens `C:\APPS\QI\maia.db` with `sqlite3.connect` — reads another project's live DB file with no network boundary. Silent breakage the moment Maia's schema moves. | **Highest-priority coupling fix.** Replace with a Maia HTTP endpoint + `qi_spine.client(fallback=...)`. Add `/version` `/info`. |
| **Claude Manager** | `health_check.py:23,33,43` hardcode `C:\QI\maia.db`, `C:\NAYA\naya.db`, `C:\NEXUS\nexus.db` — **pre-migration paths that no longer exist.** `Claude Voice/backends.py:50` has the same. | A health check pointing at dead paths is the Kaze failure mode again. Repoint via `qi_spine.discovery`; add an outcome-freshness assertion. |
| **LotteryWiz** | `/health` exists only in test expectations, not in `server.py`. `server.py:36` hardcodes NEXUS `127.0.0.1:8010`. No `CLAUDE.md`. | Implement the contract for real; route NEXUS through discovery. The test passing while the route is absent is itself the bug. |
| **EasyFlow** | Same pattern — `tests/test_smoke.py` asserts `/health`, `Tools/app.py` never implements it. | Flask spine adapter. |
| **MapSnap / CogniBase / AutoPDF** | Production server is raw `http.server` / Electron; contract satisfied only by a bolted-on MCP sidecar on another port. | Build the `http.server` spine adapter once, reuse three times. Move contract onto the primary port; keep the MCP gateway as-is. |
| **MailBrain** | Unregistered entirely. No `CLAUDE.md`, no `requirements.txt`, no `.gitignore`-protected structure gaps — secrets *are* correctly gitignored (`client_secret*.json`, `token_*.json`, `keys/`). **13 abandoned Claude worktrees** under `.claude/worktrees/`, one containing an EasyFlow copy that pollutes greps with phantom `:8550` hits. | Register it. Scaffold to QI standard. Delete the stray worktrees. Integration is via the bus (Gmail events), not a port. |
| **PersonalSong** | Hardcodes NEXUS `8010`, MediaStudio `8740`, and an orphaned Plex module on `8050`. `/health` only. No `CLAUDE.md`. | Full spine; remove the orphaned Plex reference or register it. |
| **NoosOrbis / VoiceStudio / FilmForge / Mythologies** | All four independently hardcode MediaStudio `127.0.0.1:8740`. | Single fix via `QI.url("mediastudio")`. Worth doing as one batched change. |
| **CypherMiner frontend** | `frontend/src/core/config.ts` hardcodes `localhost:8777` (LotteryWiz) — **client-side TypeScript, out of reach of any Python fix.** | Needs a JS discovery shim (`/config.json` served by the backend from `peers.json`). *(CypherMiner is on the Disregard List — the pattern still applies to any future TS frontend.)* |
| **Retirement Analyzer** | A test explicitly asserts it must **not** import `qi_registry`. | **Leave it.** This is a deliberate independence choice and is exactly C1 done right. It should adopt the *stub*, not the package. Treat as the reference implementation for "maximum independence". |
| **NEXUS** | Registry fallback path is stale: `C:\APPS\QI\ECOSYSTEM\qi_registry.json`. | Repoint to `C:\QIH\ecosystem\`. |
| **OpenClaw** | Node product; Python present only as automation glue. `C:\OC` junction load-bearing for 386 files. | Sidecar pattern. **Do not restructure.** Do not remove the junction. |
| **ComfyUI** | Third-party, shared GPU resource, contended (measured RTF 0.83× idle vs 5.79× under load with 9 GB "free"). | Wrap with the FilmForge GPU broker as the single arbiter; never modify ComfyUI itself. |

### 5.3 Class D — apps with no HTTP surface

The REST contract is the wrong shape for a CLI, a static site, a browser extension or a
Node app. They cooperate through two lighter mechanisms:

1. **Heartbeat file.** `C:\QIH\data\heartbeat\<project>.json` — `{project, version, status,
   last_run, ok, detail}`, written at the end of every run. The Hive treats a fresh
   heartbeat as equivalent to a passing `/health`. This is the correct integration for
   FilmForge's night runner, Mythologies' build pipeline, MailBrain's Apps Script, and
   VLCDaemon.
2. **Bus publish.** They emit domain events (`qi.filmforge.render.completed`) even though
   nothing calls into them.

This also closes the "unattended jobs lie" gap: the heartbeat *is* the freshness check
that `conhost --headless` exit codes cannot provide.

### 5.4 Cross-cutting hygiene findings

| Finding | Measure | Action |
|---|---|---|
| **Abandoned Claude Code worktrees** in app trees | **37 across 8 projects** — MailBrain 13, MapSnap 7, Maia 6, CogniBase 4, OpenClaw 3 | They inflate the tree, confuse greps, and produce phantom findings. Sweep + add `.claude/worktrees/` to the baseline `.gitignore`. |
| **`.bak-*` litter** | **~1,300 files** — Maia 296, QIH 214, Claude Manager 105, Naya 95, OC 92 | `C:\QIH\ecosystem\` alone holds **40+ `qi_registry.json` backups**. Move to a dated archive; stop writing siblings next to the original. |
| **Registry drift** | `playdeck` → `C:\PlayDeck` (does not exist); `universal` collides with `qi_hive`; 4 real apps absent | Repair in Wave 0. |
| **Stale governing docs** | Law 1 cites `C:\APPS\QI\ECOSYSTEM\qi_registry.json`; `QI_Standards.md` §1 cites `C:\FileHQ\` and `C:\<PROJECT>\` | The constitution itself has stale paths. Fix in Wave 0. |
| **Production apps not under version control** | **3** — FilmForge, MediaStudio, VoiceStudio (`C:\APPS` copies are plain folders) + AkiyaScout has zero commits | 🔴 No history, no rollback, no remote for four active projects. **Wave 0.9.** |
| **MailBrain has no repo of its own** | Clone of `Quiddity-Innovations/EasyFlow`; 699 tracked files are EasyFlow's, 98 untracked are MailBrain's entire product | Create its own repo before any commit. §5.5. |
| **`D:\Dev` reconciliation** | 23 pairs, all separate clones, ~950 uncommitted files, no copy ahead of production | Harvest-then-retire recommended. §5.5, decision in §10. |

### 5.5 D:\Dev reconciliation — audit complete (2026-09-02)

**The worktree premise is false.** Not one of the 23 pairs is a linked git worktree. Every
pair with git on both sides has a **separate `.git`** — independent clones with independent
object stores. The owner's read was correct: these are separate copies.

**D:\Dev is abandoned, not diverged.** Every `dev` branch HEAD clusters in
**2026-08-05 → 2026-08-08** — the workshop was bulk-populated once in early August and left
untouched since, while `C:\APPS` kept receiving direct commits on `main`/`master` through
2026-09-02. **No D:\Dev copy is ahead of production** in any pair.

> *Method caveat:* no `git fetch` was run, so ahead/behind is inferred from HEAD commit
> **dates**, not a verified `rev-list`. A rigorous count needs `git fetch` per remote or the
> GitHub `compare/main...dev` view. The conclusion is robust — the direction is consistent
> across all 23 pairs — but the exact commit deltas are not established.

**The real risk is uncommitted work, which no commit-log comparison would ever show.**

| Rank | Pair | Uncommitted (APPS / Dev) | Note |
|---|---|---|---|
| 1 | **MailBrain** | 302 / 626 | See ⚠️ below — this is not a divergence problem |
| 2 | **EasyFlow** | 0 / **418** | Workshop work on a branch last committed 2026-07-02 |
| 3 | **OpenClaw** | **78** / 20 | Uncommitted changes accumulating on the **production** side |
| 4 | Naya | 0 / 35 | |
| 5 | NEXUS | 1 / 33 | |
| 6 | LotteryWiz | 0 / 21 | |

#### 🔴 Three production apps are not under version control at all

`C:\APPS\FilmForge`, `C:\APPS\MediaStudio` and `C:\APPS\VoiceStudio` **are plain untracked
folders.** Only their `D:\Dev` copies are git repos. This is the inverse of the expected
risk — production has no history, no rollback, and no remote for three active projects.
VoiceStudio additionally holds biometric voice samples.

Also: **`C:\APPS\AkiyaScout` has zero commits** — `git log` fails, `HEAD` is unborn. It has a
`.git` directory and 15 uncommitted files, so it has never been committed once.

#### ⚠️ MailBrain has no repository of its own

Verified directly, not inferred:

```
C:\APPS\MailBrain  origin → https://github.com/Quiddity-Innovations/EasyFlow.git
D:\Dev\MailBrain   origin → https://github.com/Quiddity-Innovations/EasyFlow.git
HEAD 278d926 — identical on both sides
699 tracked files — all EasyFlow's (Branding/easyflow_*.png, EasyFlow's Tools/app.py)
 98 untracked   — MailBrain's own product (Branding/mailbrain_*.png, extensions, Apps Script)
```

`C:\APPS\MailBrain` **is a clone of the EasyFlow repository** with the entire MailBrain
product sitting untracked on top of it. MailBrain — a published product with Chrome and Edge
extensions and an Operations Manual — has **never been committed anywhere**.

This also explains the phantom finding in §5.2: the "EasyFlow copy" inside MailBrain isn't a
stray worktree artifact, it is MailBrain's actual tracked content.

**Consequence:** `git add -A && git push` from that folder publishes MailBrain into the
EasyFlow repository. Mitigating factors — `Quiddity-Innovations/EasyFlow` is **private**
(verified), and MailBrain's `.gitignore` does correctly exclude `client_secret*.json`,
`token_*.json` and `keys/`. So this is a **provenance and data-loss** problem, not a
credential-exposure one. **Tier 2, not Tier 1.**

**Fix:** create `Quiddity-Innovations/MailBrain`, re-init `C:\APPS\MailBrain` against it,
commit the product. Do **not** `git push` from that folder before the remote is corrected.

#### Not under git on either side

- **Mythologies ↔ Mythos** — neither side is a repo. *(Note: `C:\APPS\Mythologies\site\` and
  `packs\` are separately-tracked repos per its `CLAUDE.md`; the parent folder is not.)*
- **QIP ↔ "BU Edition"** — neither side is a repo.

#### NoosOrbis — deliberately frozen, not diverged

`D:\Dev\NoosOrbis` has no origin remote, carries a `PROMOTED-DO-NOT-EDIT.md` marker, and sits
on `master` while production is on `main`. It was the promotion source and is correctly
frozen. **Leave it alone** — do not reconcile.

#### Resolved 2026-09-02 — C:\APPS is the gold, D:\Dev is derived

Owner ruling (D1): **`C:\APPS` is the source of truth.** It is where an app is built and
used. `D:\Dev` is the clean, config-free *packaged release* tier — what gets deployed to
other systems. The decisive test: *"if D:\Dev got deleted, I would simply recreate the
folder and copy all C:\APPS content to D:\Dev."*

**This dissolves most of the concern above, and re-weights the rest:**

| Earlier finding | Status under D1 |
|---|---|
| ~950 uncommitted files in D:\Dev | ⬇️ **Largely moot.** D:\Dev is derivable from gold. These are stale derivative state, not unique work. No per-project harvest needed. |
| D:\Dev a month stale | ⬇️ **Expected, not a defect.** It reflects the last packaging run, not neglect. |
| No D:\Dev copy ahead of production | ✅ **Exactly right for a derivative tier.** If one ever *were* ahead, that would be the anomaly. |
| 78 uncommitted files in `C:\APPS\OpenClaw` | ⬆️ **Now more serious** — that's uncommitted work in the gold tier. |
| FilmForge / MediaStudio / VoiceStudio: git only in D:\Dev | ⬆️ **Now clearly backwards.** The gold is unversioned while the derivative holds the history. |

**The reconciliation workstream is therefore cancelled** and replaced by a much smaller one:
**packaging refresh** — regenerate `D:\Dev\<App>` from `C:\APPS\<App>` (minus config, data,
secrets, logs) whenever an app reaches a releasable state. One-way, gold → package.

#### ⚠️ `qi_promote.py` runs the wrong way

`C:\APPS\CLAUDE\Tools\qi_promote.py` states in its own header:

```
QI promotion tool — D:\Dev\<App>  ->  C:\APPS\<App>
Promotion is deliberately ONE WAY. C:\APPS is treated as build output: never
edit there, because the next promote overwrites it.
```

That is the **opposite** of D1. Under the ruling, running it copies a month-old derivative
**over the gold**. Data, logs and secrets are protected by default; **code is not.**

Most likely explanation: the tool is a fossil of a workflow used around the D:\Dev bulk
population (2026-08-05/08) and abandoned soon after, since every commit since has landed
directly in `C:\APPS`. Memory records it as created 2026-08-13.

**Action → Wave 0.10.** Do not run it in the meantime.

#### One thing that is *not* derivable from gold

For **FilmForge, MediaStudio and VoiceStudio**, `C:\APPS` has no `.git` at all — the commit
history for those three exists **only** in their `D:\Dev` copies. That history is the single
piece of D:\Dev content that a recopy-from-gold would destroy.

**Turn it into the fix:** use each `D:\Dev` copy's `.git` as the **seed** for putting the
gold under version control — move the repo to `C:\APPS`, re-point it, commit the current
gold state as the next commit. History preserved, gold versioned, one step. This is Wave 0.9
for those three specifically, and it must happen **before** any packaging refresh overwrites
them.

---

### 5.6 QI Brain MCP bridge — inherited work (D6)

Designed and built in a **separate Claude session** (Chat tab, not this one). Documented
here from the owner's handoff brief on 2026-09-02. **Nothing below has been verified against
disk by this session** — verification is step 1 whenever this is picked up.

#### Problem it solves

QI Brain spoke MCP over **stdio only**, so every client spawned its own process and nothing
was shared. Cursor and Claude Code running side by side reasoned over two disconnected
brains. The bridge puts one Streamable-HTTP MCP endpoint in front of the single Brain.

```
   Cursor ──┐
            ├──►  127.0.0.1:9012/mcp  ──►  127.0.0.1:9011  (QI_BrainAPI)
Claude Code ┘        the bridge                SQLite + ChromaDB
                   x-brain-key auth
```

#### Rejected alternative — worth recording

**OB1 / Open Brain** (Nate B Jones) — Supabase + pgvector, OpenRouter embeddings, MCP over
HTTP. Rejected because it duplicates QI Brain functionally, starts empty, and moves memory
into someone else's cloud — contradicting the local-first thesis behind the Ollama stack and
the NEXUS Sovereign BYOK tier. **OB1's client-wiring pattern was kept** (one server, many MCP
clients) and applied to QI Brain instead. This is a good pattern to reuse ecosystem-wide.

#### The bundle

| File | Role |
|---|---|
| `qi_brain_mcp_http.py` | The bridge. FastAPI + httpx, ~670 lines, hand-rolled JSON-RPC |
| `Install-QIBrainMCP.ps1` | Non-interactive, idempotent installer + NSSM registration |
| `test_bridge.py` | 23-check offline E2E suite (fake Brain + real bridge) |
| `requirements.txt` | fastapi, uvicorn[standard], httpx |
| `.env.example` | Every environment variable, documented |
| `README.md` | Setup, client config, operations, env reference |

#### Conventions

| Item | Value |
|---|---|
| Port | **9012** (QI orchestration block 9000–9099, next to Brain 9011) |
| Service | `QI_BrainMCP` |
| Install dir | `C:\QIH\engine\brain\mcp_http` |
| Master log | `C:\QIH\logs\qi_brain_mcp_http.log` |
| Auth key | user env var `QI_MCP_KEY` |

#### Brain REST surface — verified 2026-06-15, do not re-derive

| Method | Path | Body |
|---|---|---|
| GET | `/health` | — |
| GET | `/api/ecosystem_snapshot` | — |
| GET | `/api/status` | — |
| GET | `/api/pending_features` | — |
| GET | `/api/archive/decisions` | — |
| POST | `/api/context` | `{project_id}` |
| POST | `/api/search_memory` | `{query, collection, n}` |

Collections: `decisions`, `features`, `sessions`, `docs`.
⚠️ Brain moved **9010 → 9011** on 2026-05-14 (Logitech G HUB squats 9010). **Never
reintroduce 9010.**

#### Three design decisions to preserve

1. **Read-only.** Seven tools, all reads. Writes stay on the existing `qi_log_decision` path
   so no agent can quietly rewrite decision history. *Adding a write tool is a deliberate
   change — raise it with the owner first.*
2. **Session-bound auth.** Cursor has an open bug where custom headers survive `initialize`
   but are dropped on `tools/call`. After a successful handshake the bridge accepts the
   minted `Mcp-Session-Id` as a bearer credential. **Do not "simplify" this away — it is
   load-bearing for Cursor.**
3. **No `mcp` SDK.** JSON-RPC is hand-rolled against the Streamable HTTP spec (2024-11-05,
   2025-03-26, 2025-06-18 negotiated) so an SDK version bump cannot take the bridge down.
   **Do not add the SDK as a dependency.**

#### Open items — the likely first tasks

| # | Item | Detail |
|---|---|---|
| 1 | **Route map is from docs, not a live schema** | The authoring session could not reach `:9011/openapi.json`. Run `.\.venv\Scripts\python.exe qi_brain_mcp_http.py --probe` and reconcile drift against the table above before trusting the bridge. |
| 2 | **NSSM registration untested against the real service account** | If `QI_BrainMCP` starts then immediately stops, read `C:\QIH\logs\qi_brain_mcp_service.err.log` first. Usual cause: venv path, or `AppEnvironmentExtra` not carrying `QI_MCP_KEY` into the service context. |
| 3 | **Client wiring unconfirmed end to end** | Once healthy, register with Claude Code and Cursor per `README.md`, then verify from **both** that `get_context` returns real project state — not merely that the tools list. |

#### Observations from this session

- **Not in the registry.** `qi_registry.json` records `qi_brain` with `mcp: "stdio" — no
  port`. Port **9012** and service `QI_BrainMCP` appear nowhere. Law 5 requires the registry
  entry **before** the code — this is already inverted, so registering it is part of picking
  this up, not a follow-up.
- **No port conflict.** 9012 sits correctly in the 9000–9099 orchestration block alongside
  Brain 9011, Headroom 9020, Connector 9030.
- **It overlaps the QI Mesh L3 design.** §4.4 gives QI Hive an MCP-aggregation role, and
  `C:\APPS\QIP\Connector` (:9030) already exposes Brain tools over Streamable HTTP with
  bearer auth. Whether the bridge and the Connector should converge — or deliberately stay
  separate, one for editors and one for claude.ai — is an open architectural question, **not
  a settled one.** It should be answered before Wave 6 builds any more MCP surface.
- **It is a candidate ecosystem pattern.** "One service, many MCP clients, read-only bridge"
  generalizes past Brain. If it proves out, it belongs in `qi-spine` rather than being
  hand-rolled per app — the same vendoring trap described in §4.1.

---

## 6. The overhaul plan

### 6.0 The rule that protects continuous development

**Every overhaul change is additive.** `qi-spine` *adds* endpoints and *adds* a discovery
path. It never renames, removes, or changes an existing route, response field, port, or
service. Feature work and overhaul work therefore cannot collide by construction — which
is a stronger guarantee than any branching discipline.

Where a change cannot be additive (moving MapSnap's contract off the sidecar port), it
goes behind the `QI_SPINE_ENABLED` flag, defaulting **off**, flipped per-app only after
conformance passes.

**Branching.**
- `main` — production, what `C:\APPS` runs
- `dev` — the workshop (`D:\Dev`)
- `arch/<app>` — short-lived, overhaul work only, merged within one sprint
- Feature branches never touch `arch/` and vice versa

**Rollback.** Every wave's rollback is one line: unset `QI_SPINE_ENABLED`, or
`pip uninstall qi-spine` (the vendored stub takes over). No app is ever left unable to run.

### 6.1 Wave 0 — Foundation (nothing else starts until this ships)

| # | Deliverable | Why |
|---|---|---|
| 0.1 | **Repair the registry** — fix `playdeck` path, retire `universal`, register MailBrain / Bakeoff / VLCDaemon / QI-RELAY | Law 1 is meaningless while the registry lies |
| 0.2 | **Fix the governing docs** — stale paths in `QI_Architecture_Principles.md` Law 1 and `QI_Standards.md` §1 | The constitution can't cite dead paths |
| 0.3 | **Build `qi-spine`** at `C:\QIH\engine\spine` + the vendored stub | L0 |
| 0.4 | **Extend `qi_validator.py` to check the contract** — live-probe `/health /ready /version /info /capabilities`, detect hardcoded peer ports, detect cross-project DB reads | **The single highest-value item in this plan.** Compliance drifted because nothing measured it. |
| 0.5 | **Conformance test harness** — `qi-spine selftest` proving C1 and C2 per app | Makes the constraints testable |
| 0.6 | **Chaos Hour** scheduled job, with outcome-freshness checking (not exit codes) | Keeps C1 honest forever |
| 0.7 | **Bus v1** — journal, topic grammar, publish/subscribe | L2 |
| 0.8 | **Hygiene sweep** — 37 stray worktrees, ~1,300 `.bak-*` files, 40+ registry backups | Clears the noise before app work starts |
| 0.9 | **🔴 Close the C3.1 gap — 6 projects with no repo + 2 the tool already flags.** No repo at all: **MediaStudio / VoiceStudio / FilmForge** (seed from their `D:\Dev` `.git` per §5.5 so history survives), **PlayDeck**, **Bakeoff**, **VLCDaemon**. Already flagged nightly: **AkiyaScout** (first commit ever), **Claude Manager** (unblocked by 0.10). Create `Quiddity-Innovations/MailBrain` and re-point that clone. All new repos created **in the org** per C3.4. Then **add each to `nightly_git_sync.py`'s `REPOS`**. | Six active projects exist **nowhere but this machine**. Outranks every architectural item. |
| 0.9a | **Fix the coverage-check blind spot** — `coverage_check()` in `nightly_git_sync.py` counts *registry repos that sync nowhere*, so a project with no `.git` is invisible to it. Re-base the assertion on **registry membership**: every in-scope project must have a remote and be 0 ahead, or fail loudly. | This blind spot is *why* MediaStudio, VoiceStudio and FilmForge went unprotected without a single warning. Same class as the `conhost` exit-code bug — fix the monitor, not just the symptom. |
| 0.9b | **Normalize remotes to `Quiddity-Innovations` (C3.4)** — transfer 7 repos, update the 9 enumerated references, `git remote set-url` locally. `mythologies-map` moves **last and alone** (public, possible Pages config). | Consistent provenance before D:\Dev ships anything outside this environment. |
| 0.10 | **Fix C3.2 violations before pushing anything** — `git rm -r --cached Tools/headroom_env` in Claude Manager (**38,499 tracked venv files**), add `.gitattributes` for line endings, extend `QI_baseline.gitignore` to cover venvs, `*.db`, model weights. Then land its 80 real changes + 6 unpushed commits. | Pushing first would publish a venv and 754 files of CRLF noise. Do this **before** 0.9's pushes, and apply the baseline to all 28. |
| 0.11 | **Neutralize `qi_promote.py`** — it copies `D:\Dev → C:\APPS`, i.e. stale derivative over gold (§5.5). Rename to `qi_promote.py.DISABLED` immediately, then either reverse it to `C:\APPS → D:\Dev` (the packaging refresh) or retire it. | A loaded gun pointed at the source of truth. Renaming is a 10-second Tier 3 change; the rewrite can follow. |
| 0.12 | **Build the packaging refresh** — one-way `C:\APPS → D:\Dev`, stripping config, data, secrets, logs and venvs; stamps provenance (source commit) into `RELEASE.json`; **writes `<App>.bundle` (`git bundle create --all`) alongside the package** per C3.5. Verifies **C3.3** by installing the package into a clean throwaway directory and running the app's smoke test. | Makes D:\Dev a real distribution artifact *and* a genuine off-GitHub restore point — the bundle covers the failure modes an org mirror cannot. The install-from-clean test is the same check that proves C1. |

**Exit criterion:** `qi_validator.py --project <any>` reports a contract score, and Chaos
Hour runs green or produces a real ticket list.

### 6.2 Waves 1–6 — Adoption

| Wave | Theme | Apps | Effort |
|---|---|---|---|
| **1** | Reference implementations | Maia, NEXUS, NoosOrbis | Prove the pattern on the best-prepared apps. NEXUS first — everything else points at it. |
| **2** | Class A batch | TubeScout, PlayDeck, MQ, M2V, AkiyaScout, Naya | Mechanical spine swaps, 5–6 per sprint |
| **3** | Class A batch + media cluster | MediaStudio, VoiceStudio, SynVox, Claude Voice, Connector | Includes the batched `8740` de-hardcoding fix |
| **4** | Class B — hand-rolled HTTP | MapSnap, CogniBase, AutoPDF | Build the `http.server` adapter once, apply three times |
| **5** | Class C — the coupling fixes | **Gamez** (the `maia.db` read), LotteryWiz, PersonalSong, EasyFlow, Claude Manager (stale health paths) | Highest risk-reduction wave |
| **6** | Class D + E — no HTTP surface | FilmForge, Mythologies, AvatarStudio, OpenClaw, MailBrain, VLCDaemon, Bakeoff, QI-RELAY, ComfyUI | Heartbeat + bus pattern |

Running in parallel from Wave 1: **D:\Dev reconciliation** (§5.5) and **Hive L3 build-out**
(capability catalog, event fan-out, unified shell).

---

## 7. Living calendar

Two-week sprints. **Reorder freely** — edit this table directly. The `Status` column is
the tracking surface.

| Sprint | Dates | Wave | Apps | Status | Notes |
|---|---|---|---|---|---|
| S0 | 2026-09-02 → 09-15 | 0 | Foundation 0.1–0.4 | ⏳ Not started | Registry repair + validator is the gate |
| S1 | 2026-09-16 → 09-29 | 0 | Foundation 0.5–0.8 | ⏳ Not started | Chaos Hour + bus + hygiene sweep |
| S2 | 2026-09-30 → 10-13 | 1 | NEXUS, Maia, NoosOrbis | ⏳ Not started | NEXUS first — it is the backbone |
| S3 | 2026-10-14 → 10-27 | 2 | TubeScout, PlayDeck, MQ | ⏳ Not started | |
| S4 | 2026-10-28 → 11-10 | 2 | M2V, AkiyaScout, Naya | ⏳ Not started | Naya is paused — confirm before scheduling |
| S5 | 2026-11-11 → 11-24 | 3 | MediaStudio, VoiceStudio, SynVox | ⏳ Not started | Batched `8740` de-hardcoding |
| S6 | 2026-11-25 → 12-08 | 3 | Claude Voice, Connector | ⏳ Not started | Claude Voice services currently stopped |
| S7 | 2026-12-09 → 12-22 | 4 | MapSnap | ⏳ Not started | Builds the `http.server` adapter |
| S8 | 2027-01-06 → 01-19 | 4 | CogniBase, AutoPDF | ⏳ Not started | Reuses S7's adapter |
| S9 | 2027-01-20 → 02-02 | 5 | **Gamez**, LotteryWiz | ⏳ Not started | Gamez `maia.db` fix — highest risk reduction |
| S10 | 2027-02-03 → 02-16 | 5 | PersonalSong, EasyFlow, Claude Manager | ⏳ Not started | Claude Manager stale health paths |
| S11 | 2027-02-17 → 03-02 | 6 | FilmForge, Mythologies, AvatarStudio | ⏳ Not started | Heartbeat pattern |
| S12 | 2027-03-03 → 03-16 | 6 | OpenClaw, MailBrain, VLCDaemon | ⏳ Not started | MailBrain also needs registering + scaffolding |
| S13 | 2027-03-17 → 03-30 | 6 | Bakeoff, QI-RELAY, ComfyUI wrapper | ⏳ Not started | |
| S14 | 2027-03-31 → 04-13 | — | Unified shell + retrospective | ⏳ Not started | |

**Continuous, every sprint:** D:\Dev reconciliation · Hive L3 build-out · Chaos Hour
results triage.

**Status legend:** ⏳ Not started · 🔄 In progress · ✅ Done · ⚠️ Blocked · ⏭️ Deferred

---

## 8. Risk register

| Risk | Tier | Mitigation |
|---|---|---|
| Overhaul work breaks a running production service | 🟠 2 | Additive-only rule + `QI_SPINE_ENABLED` flag default-off + one-line rollback |
| `pip install -e qi-spine` breaks an app's venv | 🟠 2 | Vendored stub means the import always resolves; spine is optional |
| Moving MapSnap/AutoPDF contract off the sidecar port breaks MCP clients | 🟠 2 | MCP gateway stays on its own port unchanged; only *adds* to the primary port |
| A wave silently does nothing and nobody notices | 🔴 1 | This is the documented QI failure mode. Chaos Hour + validator contract score make it loud. |
| **6 gold projects exist nowhere but this machine** — no `.git` at all | 🔴 1 | Violates C3.1. **Wave 0.9.** A single disk failure loses them. Highest-severity item in the plan. |
| **The coverage check cannot see them** — it only counts existing repos | 🔴 1 | Wave 0.9a. A monitor blind to the worst case is how this persisted silently. |
| Transferring `rennesan/synvox` revokes Urcil's collaborator access | 🟠 2 | Re-grant in the org and notify him **before** the move (C3.4). Affects another person, not just a URL. |
| Treating a `rennesan/*` org mirror as the backup | 🟠 2 | Same provider, same credential — covers accidental deletion, **not** provider loss or account compromise. C3.5: use `git bundle` on D:\Dev for real independence. |
| `mythologies-map` transfer breaks the deployed public site | 🟠 2 | Verify Pages config and any custom domain **before** moving. Transfer it last and alone (C3.4). |
| **`qi_promote.py` overwrites the gold tier with a month-old derivative** | 🔴 1 | D1 makes this concrete: the tool runs `D:\Dev → C:\APPS`. **Wave 0.11 — rename to `.DISABLED` first, redesign after.** Do not run it. |
| Pushing a tracked venv / secrets to GitHub while closing the coverage gap | 🟠 2 | Claude Manager already tracks 38,499 venv files. **Wave 0.10 runs before 0.9's pushes.** |
| A packaging refresh destroys the only copy of those three projects' git history | 🟠 2 | Their history lives **only** in `D:\Dev` (§5.5). Wave 0.9 must land before any refresh. |
| A `git push` from `C:\APPS\MailBrain` publishes MailBrain into the EasyFlow repo | 🟠 2 | EasyFlow repo is **private** and MailBrain's secrets are gitignored — provenance/data-loss, not exposure. Create the correct remote first (Wave 0.9). |
| ~950 uncommitted files in D:\Dev | 🟢 3 | ⬇️ Downgraded by D1 — D:\Dev is derived from gold, so these are stale derivative state, not unique work. No harvest needed. |
| `C:\OC` junction removed during hygiene sweep | 🔴 1 | Explicitly excluded. 386 files depend on it. |
| Calendar slips because feature work takes priority | 🟢 3 | Expected. That is why this is a living document. |

---

## 9. Change log

| Date | Change |
|---|---|
| 2026-09-02 | Document created. Phase 1 scan complete (37 in scope, Disregard List set by owner). Phase 2 design and Phase 3 plan drafted. |
| 2026-09-02 | D:\Dev audit complete (§5.5). Worktree premise disproven — all separate clones. Added Wave 0.9 (version control for 4 unprotected production projects + MailBrain repo). Risk register updated. |
| 2026-09-02 | Owner decisions D1–D6 recorded. D2/D3/D5 settled. D4 manifest generated. D6 added: QI Brain MCP bridge documented in §5.6 from a separate-session handoff, not started. |
| 2026-09-02 | **D1 settled — `C:\APPS` is the gold, D:\Dev is derived.** Reconciliation workstream cancelled and replaced by one-way packaging refresh. D:\Dev uncommitted-file risk downgraded 🔴→🟢. Wave 0.9 re-scoped to seed the unversioned projects from their D:\Dev git history. |
| 2026-09-02 | **Corrections after a proper full-tree sweep.** An earlier blast-radius grep timed out and its "0 matches" was an artifact — real count is **40+ references**, incl. `nightly_git_sync.py`, the public landing page, CogniBase's `pyproject.toml`, and ~18 SynVox files documenting an **external collaborator (Urcil)** whose access a transfer would revoke. Also: **OpenClaw is protected** — `C:\APPS\OC\repo\` is its own clone of OC-Orchestrator; the earlier 🔴 was wrong. **`QI_NightlyGitSync` already syncs 21 repos nightly with a secret gate** and already reports its own gaps; Wave 0.10's venv cleanup was diagnosed 2026-08-27 and deferred as the owner's call, not newly found here. Real gap: **6 projects with no `.git` at all**, invisible to `coverage_check()` because it only counts existing repos — added Wave 0.9a to fix that blind spot. |
| 2026-09-02 | **C3.4 / C3.5 added.** Owner: normalize all remotes under `Quiddity-Innovations` — 7 transfers enumerated with blast radius (9 file refs, all redirect-covered). Answered the `rennesan/*`-as-backup question: it's a mirror, not a backup — same provider, same credential; recommended `git bundle` on D:\Dev instead, folded into Wave 0.12. **Corrected the coverage count: 7 unprotected + 1 disconnected, not 9** — QI Connector and Mythologies are protected via sub-repos the first pass missed; Bakeoff was missed and is not. OpenClaw's repo exists (`rennesan/OC-Orchestrator`); the local gold copy just has no remote wired. |
| 2026-09-02 | **C3 protection model added (§3.1)** per owner requirement: protect C:\APPS, keep GitHub current, D:\Dev as backup + distribution source. GitHub coverage measured across 28 gold projects — **19 protected and in sync, 9 with no remote at all, 2 compromised.** Waves renumbered: 0.9 coverage gap, 0.10 gitignore/venv cleanup (before any push), 0.11 `qi_promote.py`, 0.12 packaging refresh. Established that **C3.3 (installs elsewhere) and C1 (runs standalone) are the same property** — the `qi-spine` work serves both. |

---

## 10. Open decisions — owner input needed

| # | Decision | Recommendation | Blocks |
|---|---|---|---|
| D1 | D:\Dev tier direction | ✅ **DECIDED 2026-09-02 — `C:\APPS` is the gold.** D:\Dev is the clean, config-free packaged release tier, **derived from** C:\APPS. Owner's test: *"if D:\Dev got deleted, I would simply recreate the folder and copy all C:\APPS content to D:\Dev."* Consequences in §5.5. **Side effect: `qi_promote.py` runs backwards — see Wave 0.10.** | — |
| D2 | Sprint length and calendar structure | ✅ **DECIDED 2026-09-02 — one calendar.** Architecture, features and sprints merged into a single timeline. No parallel tracks. | — |
| D3 | Event bus: SQLite journal or Redis | ✅ **DECIDED 2026-09-02 — SQLite journal.** File-backed, no daemon. | — |
| D4 | Hygiene sweep approval | ✅ **Manifest generated 2026-09-02** — [QI_Hygiene_Manifest_2026-09-02.md](QI_Hygiene_Manifest_2026-09-02.md). 37 worktrees (1.0 GB), 1,792 `.bak-*` files (520 MB, **59 orphaned**), 32 registry backups. **Awaiting per-section approval.** Permanent fix in §6.1 note. | Wave 0.8 |
| D5 | **Naya is `running_dev_paused`** and Claude Voice services are all stopped. Overhaul them on schedule, or defer? | ✅ **DECIDED 2026-09-02 — defer both.** Removed from S4/S6. | — |
| D6 | **QI Brain MCP bridge** (§5.6) — inherited from a separate Chat session. Three open items: live-probe the route map, test NSSM registration, confirm Cursor + Claude Code wiring end to end. | Documented, **not started** (owner instruction 2026-09-02). Needs a calendar slot and a ruling on whether it converges with QI Connector (:9030) or stays separate. Register port 9012 / `QI_BrainMCP` in the registry when picked up — Law 5 is already inverted here. | Wave 6 MCP work |

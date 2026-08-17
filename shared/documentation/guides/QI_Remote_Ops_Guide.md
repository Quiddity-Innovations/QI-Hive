# QI Remote Operations Guide
## Manage every project from any device you own — iPad, phone, glasses, any browser

**Pattern:** one brain (QI Brain), one voice (Claude on any surface), one pair of hands per
machine (the whitelisted executor). You talk anywhere; the machines do the work.

*Live on the PowerSpec since 2026-08-16. This guide records what is actually installed —
not a plan.*

---

## Quick reference: what runs where

| Layer | Lives at | Role |
|---|---|---|
| Claude (any device) | iPad / phone / browser / Desktop / Code | Voice & brain — plans, launches, interprets |
| QI Connector | `C:\APPS\QIP\Connector` — :9030, tunnel `qi-connector` | Front door — MCP tools |
| Executor | `qi_executor.py` inside the Connector | Hands — runs whitelisted scripts |
| **Whitelist** | `C:\QIH\dispatch\scripts\manifest.json` | **The security boundary** |
| Jobs & logs | `C:\QIH\dispatch\jobs\` | Status & audit trail |
| Master audit log | `C:\QIH\dispatch\executor_master.log` | Every LAUNCH / DENY / RESULT / TIMEOUT |
| QI Brain | `C:\QIH\engine\brain` — :9011 | Memory — decisions, registry, history |

Services are `QI_ConnectorMCP` (server) and `QI_ConnectorTunnel` (cloudflared). Restart
without admin through the QI_Elevate broker:
`run_elevated("nssm", ["restart", "QI_ConnectorMCP"])`.

---

## The remote workflow (from any device, forever after)

| You say | What happens on the PowerSpec |
|---|---|
| "List the scripts available on the QI machine" | `qi_list_scripts()` → the whitelist, with `exists` per script |
| "Run the SynVox setup" | `qi_execute_script("setup-synvox")` → background job, `job_id` back in seconds |
| "How's it going?" | `qi_script_status(job_id)` → status, exit code, last 40 log lines |
| "What have I run lately?" | `qi_script_status()` with no id → the 15 most recent jobs |
| "Log this decision" | `qi_log_decision` → permanent QI Brain record |
| "What's the state of the ecosystem?" | `qi_ecosystem_snapshot` / `qi_headlines` |
| "Is everything healthy?" | `qi_service_status`, or `qi_execute_script("qi-health-snapshot")` |

**Long jobs are fine.** The executor returns immediately and the job keeps running even if
you close the chat. Ask for status in a later conversation — job JSON and logs persist on
disk. A job whose watcher died with a Connector restart is reconciled from its pid on the
next status call.

---

## Onboarding a NEW project (repeatable for all)

1. **Registry entry** — add the project to `C:\QIH\ecosystem\qi_registry.json` (id, name,
   status, tier, ports, path), then `POST http://127.0.0.1:9011/api/admin/sync_projects`
   so the Brain accepts the new `project_id`. The Brain rejects unknown ids by design —
   that is good hygiene, not a bug.
2. **Bootstrap script** — one automated, master-logged, idempotent script per project
   (like `Setup-SynVox.ps1`) dropped into `C:\QIH\dispatch\scripts\`.
3. **Whitelist it** — add a manifest entry (`sha256: "ANY"` while iterating).
4. **Run it from anywhere** — "execute setup-\<project\>".
5. **Log the decision** — `qi_log_decision` with the new `project_id`, so the Brain's
   history starts on day one.

**Rule of thumb:** if a project action will ever be needed twice, it becomes a whitelisted
script. Deploy, restart, backup, test-run, report generation — all script-shaped.

---

## Writing a script that will be run remotely

The executor runs scripts as **NT AUTHORITY\SYSTEM**, because `QI_ConnectorMCP` runs as
LocalSystem. Everything below was learned the hard way on 2026-08-16, when a remote re-run
of a bootstrap that worked interactively failed five steps and left a venv renne could not
even delete.

- **Encoding.** Save `.ps1` as **UTF-8 with BOM, ASCII punctuation only**. Windows
  PowerShell 5.1 decodes a BOM-less UTF-8 em dash as a smart quote and the script fails to
  parse with a pile of misleading "unexpected token" errors.
- **Per-user toolchains diverge.** SYSTEM's profile is
  `C:\WINDOWS\system32\config\systemprofile`, so it will happily install a *second* uv and
  a *second* Python there and then fail to see the venv renne built. Pin uv's state to a
  machine-wide location at the top of the script:
  `UV_PYTHON_INSTALL_DIR`, `UV_CACHE_DIR`, `UV_TOOL_DIR` under `C:\QIH\shared\uv`.
- **Hand files back.** Anything SYSTEM creates is owned by SYSTEM and is read-only —
  often undeletable — for renne afterwards. End the script with
  `icacls <path> /grant "*S-1-5-32-545:(OI)(CI)M" /T /C /Q` (S-1-5-32-545 = BUILTIN\Users,
  locale-independent), guarded on actually running as SYSTEM.
- **Git ownership.** `git pull` on a repo cloned by renne fails as SYSTEM with "dubious
  ownership". Use `git -c safe.directory=<path>` **inline** — never `--global`.
- **Make it idempotent and self-healing.** Detect a broken venv by running its
  `python.exe`, and recreate with `--clear` rather than failing. Verify downloads against
  the publisher's manifest (size and shard count) instead of trusting an exit code.
- **No confirmation prompts, ever.** `$ProgressPreference = "SilentlyContinue"` keeps
  winget and huggingface progress bars out of the log.

---

## Security rules (non-negotiable)

1. **Whitelist only.** Never add a "run any command" tool to an internet-reachable
   connector. The manifest **is** the security boundary. Refusals implemented and tested:
   unknown key, path escape, missing file, sha256 mismatch, non-whitelisted argument,
   wrong machine, unsupported interpreter, malformed `job_id`.
2. **Pin hashes.** `sha256: "ANY"` is for development only. Pin the real hash once a
   script stabilises (`(Get-FileHash .\X.ps1).Hash`) — a modified script then refuses to
   run until re-approved.
3. **No secrets in scripts or the manifest.** API keys live in machine environment
   variables (`setx`), never in a whitelisted file.
4. **Args are whitelisted too.** Default `allowed_args: []`; add specific flags only when
   a script genuinely needs them.
5. **Everything logs.** `executor_master.log` plus per-job logs are the audit trail.
   Review `DENY` lines occasionally — they show attempted misuse.
6. **BU separation stands.** No BU machine ever becomes a node; no BU credential ever
   enters a manifest or an environment variable in this system.

⚠️ **Open decision for Renne:** scripts currently execute as **LocalSystem**, the highest
privilege on the box, because that is how `QI_ConnectorMCP` is installed. The whitelist
contains it, but running the service under a dedicated lower-privilege account — or a
service account with just the rights the scripts need — would shrink the blast radius.
Worth deciding before the whitelist grows.

---

## Extending to OTHER machines you own

**Tier A — full node (a machine that runs work):** deploy the same executor pattern — a
small FastMCP service with `qi_executor.py`, its own `dispatch\scripts` folder, registered
as an NSSM service and exposed the same way the Connector is. Add it as another connector
in Claude, or route through the main Connector using the manifest's per-script `machine`
tag (already enforced: a script tagged for another machine is refused here).

**Tier B — Claude Code node (interactive machine):** install Claude Code and drive it from
the Claude mobile app. Best for exploratory work. The PowerSpec runs both — executor for
repeatable ops, Claude Code for everything unscripted.

**Tier C — dumb node (rarely touched):** don't instrument it. Reach it from a Tier A/B
machine via PowerShell Remoting or SSH inside a script that lives on the Tier A whitelist.

**Networking:** machines not exposed via Cloudflare tunnels can join a private mesh (e.g.
Tailscale) so Tier A nodes reach them without opening ports to the internet.

---

## Retrofit checklist for existing projects

For each active project (NEXUS, Maia, EasyFlow/MailBrain, AutoPDF, OpenClaw, …):

- [ ] Registry entry current? *(`easyflow` still carries the old name — flagged 2026-08-16,
      awaiting Renne's go-ahead before anything is renamed.)*
- [ ] Three standard scripts created and whitelisted:
      `Restart-<Project>.ps1` (nssm restart + health probe),
      `Update-<Project>.ps1` (git pull + deps + restart + smoke check),
      `Backup-<Project>.ps1` (config/data snapshot).
- [ ] API/MCP port registered so `qi_service_status` probes it.

Once done, every project is restart-able, update-able and backup-able from your pocket.

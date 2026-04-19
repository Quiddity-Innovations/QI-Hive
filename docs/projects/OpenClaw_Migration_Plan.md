# OpenClaw → QI Standard — Migration Plan

**Status:** Deferred · **Priority:** Low (per Renne 2026-04-19: EasyFlow, NEXUS, QI Orchestrator come first)
**Current path:** `C:\OC` · **Target path:** `C:\QIP\OpenClaw`
**Onboarding tier completed 2026-04-19:** git init + CRLF protection + popup fix + registration in `status.json`

---

## Why we haven't physically moved it yet

OpenClaw has deep, hardcoded integration across multiple surfaces. Moving the folder without a coordinated sweep will silently break overnight tasks. Documented here so the migration is a checklist, not a recall of tribal knowledge.

## Hardcoded path surfaces (what must change together)

| Surface | Where | What points at `C:\OC` |
|---|---|---|
| **NSSM service** | `OC-Keepalive-Service` | `AppDirectory=C:\OC\tools`, `AppParameters=C:\OC\tools\oc-keepalive-daemon.py`, `AppStdout/Stderr=C:\OC\runtime\logs\keepalive\*.log` |
| **Task Scheduler** | `OC_WSL_KeepAlive` | Runs `powershell -File "C:\OC\keep-wsl-alive.ps1"` |
| **Task Scheduler** | `OC-ChatGPT-Keepalive` | Args `C:\OC\tools\oc-chatgpt-keepalive.py`, WorkingDirectory `C:\OC\tools` |
| **Task Scheduler** | Ubuntu yubin-daily task | `bash /mnt/c/OC/repo/scripts/yubin/yubin-daily.sh` |
| **PowerShell script** | `C:\OC\keep-wsl-alive.ps1` | `$LOG_DIR = "C:\OC\runtime\logs"` + `exec /mnt/c/OC/oc-watchdog.sh` |
| **Bash watchdog** | `C:\OC\oc-watchdog.sh` | `LOG=/mnt/c/OC/runtime/logs/wsl-watchdog.log` |
| **Python daemons** | `C:\OC\tools\*.py` | Multiple `Path(r"C:\OC\runtime\...")` |
| **WSL systemd unit** | `~/.config/systemd/user/openclaw-gateway.service` | May reference `/mnt/c/OC/...` paths — **inspect before moving** |
| **`.wslconfig` / `wsl.conf`** | Windows + WSL | None currently, but verify |
| **Storage state mirror** | Ubuntu cron: `cp ~/.notebooklm/storage_state.json /mnt/c/OC/runtime/nlm-storage-state.json` | Hardcoded target path |
| **Telegram creds** | `oc-keepalive-daemon.py`, `oc-chatgpt-keepalive.py` | Not path-related, but note for audit |

## Migration checklist (when priority shifts)

### Phase 1 — Preparation (no downtime)
- [ ] Stand up empty `C:\QIP\OpenClaw\` with QI 7-folder layout (`engine/`, `config/`, `data/`, `logs/`, `tests/`, `docs/`, `tools/`)
- [ ] Decide which existing `C:\OC\` subdirs map to which QI folders:
  - `C:\OC\tools\` → `C:\QIP\OpenClaw\tools\`
  - `C:\OC\repo\` → keep as submodule reference in engine/ or top-level
  - `C:\OC\runtime\` → `C:\QIP\OpenClaw\data\` + `logs\`
  - `C:\OC\Documentation\` → `C:\QIP\OpenClaw\docs\`
  - `C:\OC\secrets\` → **do not move; relocate to password manager + reference via env vars**
- [ ] Audit all `.py`, `.sh`, `.ps1`, `.bat` for hardcoded `C:\OC` → produce sed/replace script
- [ ] Check WSL systemd unit for `/mnt/c/OC` references
- [ ] Relocate plaintext credentials out of the repo entirely (already flagged)

### Phase 2 — Cutover (planned downtime, ~30 min)
- [ ] Stop services: `OC-Keepalive-Service`, disable `OC_WSL_KeepAlive`, `OC-ChatGPT-Keepalive`
- [ ] Stop WSL gateway: `wsl -u hyosuke -- systemctl --user stop openclaw-gateway`
- [ ] `robocopy C:\OC C:\QIP\OpenClaw /E /COPYALL` (excluding runtime/, __pycache__)
- [ ] Run the path-replacement script on all scripts inside the new location
- [ ] Update WSL systemd unit paths
- [ ] Reconfigure NSSM service via broker:
  - `nssm set OC-Keepalive-Service AppDirectory C:\QIP\OpenClaw\tools`
  - `nssm set OC-Keepalive-Service AppParameters C:\QIP\OpenClaw\tools\oc-keepalive-daemon.py`
  - (both paths allowed by existing whitelist regex `^C:\\(QIH|QIP)(\\...)*$`)
- [ ] **Rename NSSM service** `OC-Keepalive-Service` → `QI_OC_Keepalive` (requires install/remove — not yet whitelisted; add rule or do via one-off admin bat)
- [ ] Update Task Scheduler actions via `Set-ScheduledTaskAction` to new paths
- [ ] Verify gateway reachable on `127.0.0.1:18789`
- [ ] Restart services in order: NSSM keepalive → OC_WSL_KeepAlive → OC-ChatGPT-Keepalive

### Phase 3 — Verification (1 hour)
- [ ] Watch `C:\QIP\OpenClaw\logs\` for clean startup of all daemons
- [ ] Verify Telegram alerts still fire (trigger a test failure)
- [ ] Confirm WSL gateway survives > 30 min idle (no unexpected restart by keepalive)
- [ ] Remove or archive `C:\OC\` after 48h of stable operation on new path

### Phase 4 — Hardening
- [ ] Register `QI_OC_Keepalive` in `C:\UNIVERSAL\ECOSYSTEM\QI_Service_Registry.md`
- [ ] Update `status.json` `OpenClaw.path` to new location, flip `standard_compliance: full`
- [ ] Add `nssm install` rule to elevation broker whitelist (scoped to `QI_*` names + paths under `C:\QIH|C:\QIP`) so future service creations don't need a manual admin bat
- [ ] Initialize or link the OpenClaw git repo to a private GitHub remote

## What the 2026-04-19 safe-tier onboarding accomplished

- ✅ `git init` in `C:\OC` → future silent regressions (like the CRLF bug that ran for 11 days undetected) will surface in diffs
- ✅ `.gitattributes` forces LF for `*.sh`/`*.bash` → the specific CRLF class of bug cannot recur
- ✅ `.gitignore` excludes plaintext credential files at repo root → nothing sensitive will be accidentally committed
- ✅ Registered in `C:\QIH\data\status.json` with `standard_compliance: partial`, `priority: deferred`
- ✅ Popup annoyance fixed: `OC-ChatGPT-Keepalive` + `QI-UsageSync` tasks now use `pythonw.exe` with `Hidden=True`

## Security flags (worth addressing independent of migration)

The following plaintext credential files currently sit in `C:\OC\` root and are excluded from git but still present on disk. They should be moved to a password manager:

- `Maia Quiddam - App Password.txt`
- `MAIA Quiddam Recovery key.pdf`
- `Maia Quiddam - Backup codes for Maia.Quiddam@gmail.com.pdf`
- `Yubin - App Password.txt`
- `Yubin - App Password.png`

Recommend: move to 1Password/Bitwarden, delete from disk, reference via environment variables where scripts need them.

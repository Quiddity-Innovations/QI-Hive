# QI Ecosystem Audit — 2026-05-15

**Report ID:** ecosystem_audit_20260515_a7e03e69
**Auditor:** QI Hive Inspector (delegated via Claude Manager session)
**Scope:** All registered QI projects + Claude Manager worktrees
**Method:** Read-only. No code or config was modified by the audit.

---

## Executive Summary

The ecosystem is operationally healthy at the service layer: all 12 NSSM services are RUNNING and all expected ports are listening. No production outages. However the audit surfaces **one critical security finding requiring immediate action** (live credentials hardcoded in a tracked, GitHub-pushed file), **two additional critical findings** (cross-project service control violation, stale governance document), and a cluster of majors. The Brain knowledge coverage has 2-day blind spots on Maia, Naya, and MapSnap, plus an OpenClaw `project_id` casing inconsistency that orphaned yesterday's session log. 27 of 49 Claude Manager worktrees are stale (24–37 days old, never merged) and accumulating silently. QI Hive, EasyFlow, and MapSnap have no CLAUDE.md, meaning any Claude session on those projects runs without ecosystem safety guards. The governing document `QI_Architecture_Principles.md` points to a file path that has not existed since the 2026-04-22 migration.

---

## Critical Issues

### [CRITICAL-1] Live credentials hardcoded in `C:\APPS\QI\maia_server.py` (tracked by git)

Lines 175–189:
- LINE Channel Secret: `6b61b5c078ecbfc218ca137647b22044` — hardcoded as fallback default.
- LINE Channel Access Token: full 88-character bearer token across lines 177–179.
- Facebook Page Access Token: full live token (~256 chars, starts `EABLerZCxiis`) on line 188.

`maia_server.py` is confirmed tracked. The `_cfg()` function (line 141) prefers DB when `CONFIG_SOURCE='db'` — but when `CONFIG_SOURCE='file'` (or when the DB value is absent), the hardcoded value IS the live credential. These tokens are in git history and potentially pushed to `github.com/Quiddity-Innovations/MAIA`.

**Action required:** Rotate immediately via LINE Developer Console and Meta App Dashboard. Replace file values with empty strings. If MAIA repo is public, notify LINE and Meta that credentials were in commit history.

### [CRITICAL-2] OpenClaw directly controls Maia's NSSM service

File: `C:\APPS\OC\runtime\tmp\clean_restart_maia.ps1`

This script stops `QI_MaiaBot`, kills Python processes over 200 MB, clears Maia's pycache under `C:\APPS\QI`, and restarts `QI_MaiaBot`. Direct violation of `QI_Standards.md` Section 10: a project's control script must only start/stop/restart its own services. If run accidentally, it kills live LINE/Telegram sessions for all Maia users.

### [CRITICAL-3] QI_Architecture_Principles.md references retired paths (5 occurrences)

File: `C:\QIH\ecosystem\QI_Architecture_Principles.md` lines 28, 106, 198, 221, 254

All reference `C:\APPS\QI\ECOSYSTEM\`. The actual path since 2026-04-22 is `C:\QIH\ecosystem\`. Any agent reading Law 1 or the Compliance Checklist is directed to a path that does not exist. This is the **governing law document** — it must be accurate.

---

## Per-Project Findings

### Maia (C:\APPS\QI, ports 8001/7860)

- **Plan vs Reality:** Active. `maia_server.py` modified 2026-05-15 17:24. New files `qi_sibling_control.py` and `quiet.json` untracked. `docs/Sibling_Bot_Control.md` (2026-05-14) documents the feature; plan and code aligned.
- **Brain Coverage:** Last session `maia: 2026-05-13 09:27`. Last commit 2026-05-15 18:45. **Two-day blind spot.**
- **Standards:** 17 pass, 2 warn (no `requirements.txt`, non-standard doc folder).
- **Service Health:** All three QI_Maia* services RUNNING. Ports green.
- **Cross-project:** `qi_sibling_control.py` reads Naya/Kaze/Tasuke telegram + LINE tokens from `maia.db`. Deliberate but undocumented in `qi_registry.json`. Single-DB credential failure mode. Law 3 violation.
- **Uncommitted:** `.gitignore`; `qi_sibling_control.py`, `quiet.json`, `shared-chats.json` untracked.
- **Doc drift:** 0.7d.
- **Standing-rule violations:** Live credentials in tracked file (CRITICAL-1).

### Naya (C:\APPS\NAYA, ports 8002/7861)

- **Plan vs Reality:** Untracked `naya_line.py` (2026-05-14 20:57) is a LINE channel draft. Header: "DRAFT - Not wired yet. Renne reviews before integration." Registry still accurate.
- **Brain Coverage:** Last session 2026-05-13. Two-day gap.
- **Standards:** 17 pass, 2 warn.
- **Service Health:** QI_NayaBot + QI_NayaGradio RUNNING.
- **Uncommitted:** `.claude/settings.json`; `naya_line.py`, `naya_log.txt`, filehq status, tools script untracked.

### NEXUS (C:\APPS\NEXUS, ports 8010/7880)

**All clear.** Last commit 2026-05-13 (docs only). Brain in sync. Validator: 18 pass, 1 warn. QI_NEXUS RUNNING.

### OpenClaw (C:\APPS\OC, WSL 18789)

- **Plan vs Reality:** 62 files modified in last 72h. Koe voice work + Tasuke bridge updates. Matches plan.
- **Brain Coverage — SPLIT IDENTITY:** Two records in `session_log` — `openclaw` (last 2026-05-13 20:11) and `OpenClaw` capital-O (last 2026-05-14 18:27, orphan). Brain API normalizes to lowercase, so the May-14 session is unreachable via `qi.get_context('openclaw')`. **1-2 day effective blind spot.**
- **Standards:** 15 pass, 3 fail. `*.env` not in `.gitignore`; `C:\APPS\OC\LOGS` declared in registry but missing on disk; no `requirements.txt`.
- **Service Health:** QI_KazeConfigAPI (8401) + OC-Keepalive-Service RUNNING.
- **Cross-project contamination:**
  - `clean_restart_maia.ps1` controls Maia's service (CRITICAL-2).
  - `tear_down_bridge.bat` uses gsudo (superseded by QI_Elevate per 2026-05-14 memory).
  - Multiple `scripts/*.ps1` have gsudo in header comments.
- **Uncommitted:** `.claude/settings.json`; `INTRO/`, `scripts/`, `tools/oc_audit.sh` untracked.
- **Doc drift:** **26.2 days — STALE.** Only project with >14d gap.
- **Standing-rule violations:** gsudo in bat, controls Maia's service, `OC-Keepalive-Service` missing `QI_` prefix, no LOGS dir, casing inconsistency in Brain.

### EasyFlow (C:\APPS\EasyFlow, port 8550)

- Desktop tool, no service running. Correct.
- **Brain:** in sync.
- **Standards:** 7 pass, 8 FAIL — **worst score of active projects.** No CLAUDE.md, `secrets/` not in `.gitignore`, `*.env` not in `.gitignore`, no `secrets/`, no `requirements.txt`, no standard doc folder.
- **Other:** Root has mixed loose files. One filename `UNIVERSALDOCUMENTATIONSession_SummariesEasyFlow_Summary_2026-04-12_2200.docx` — collapsed-path artifact.

### FileHQ

Registry: `merged_into_naya`. Path no longer exists; module at `C:\APPS\NAYA\filehq\` confirmed. **No issues.**

### MapSnap (C:\APPS\MapSnap, port 9876)

- **Plan vs Reality:** Registry says `active_stable`. Today (2026-05-15): 19 file modifications, `server.py` +410/-153 lines, `build_browser.py` +176 lines. **Major work, not "stable."** All changes uncommitted. Brain has no record at audit time (logged manually post-audit as session_id 158).
- **Brain Coverage:** Last session before this one was 2026-05-13. Major work today.
- **Standards:** 8 pass, 6 fail. **No CLAUDE.md** — confirmed absent. `secrets/` not in `.gitignore`.
- **Service Health:** Port 9876 listening.
- **Cross-project:** None.
- **Uncommitted:** 7 modified source files + large untracked branding assets. All today's work uncommitted (held intentionally for owner review tomorrow).
- **Standing-rule violations:** Missing CLAUDE.md — a project with a 410-line server change today ran without ecosystem safety instructions loaded.

### QI Hive / QI Brain (C:\QIH, 8600/9011)

- **Plan vs Reality:** Most operationally active. 411 files modified in last 72h (mostly runtime state). Real source changes in `engine/bin/openclaw_qi_patches/`, `engine/hive/dashboard/project_status.py`, `engine/common/usage_stats.py`, `engine/hive/tunnel/tunnel_manager.py`.
- **Brain Coverage:** Last session 2026-05-14 23:51. Last commit 2026-05-15 19:07. ~1d gap. Acceptable.
- **Standards:** 11 pass, 6 fail. **No CLAUDE.md at C:\QIH** — ecosystem governance project does not follow its own Rule 1. `*.env` not in `.gitignore`. Port 9011 double-registered in both `qi_hive` and `qi_brain` entries.
- **Service Health:** All five QI_* services RUNNING.
- **Phantom Brain DB:** `C:\QIH\engine\brain\qi_brain.db` — **0 bytes**, touched today. Live DB at `C:\QIH\data\qi_brain.db` (4.1 MB, 155 sessions). Any CWD-relative open from `engine/brain/` silently gets the empty file.
- **Uncommitted:** `LATEST.md`, `commands/whitelist.json`, `qi_registry.json`, multiple engine scripts, `project_status.py`, `tunnel_manager.py`, `status.json`.

### AutoPDF (C:\APPS\AutoPDF)

Not a git repo. INTRO refreshed 2026-05-14. CHANGELOG 2026-05-13. Desktop tool. **Brain gap: 16 days.** Low concern (no server).

### CogniBase (C:\APPS\CogniBase)

`pre_poc`. No active dev. Brain last 2026-05-12. **Port conflict:** registers 8650, Universal/Launcher also uses 8650. Dormant. Validator: 8 pass, 6 fail. No CLAUDE.md.

### MQ (C:\APPS\MQ)

Registry `new`, awaiting Facebook credentials. **No audit concerns.**

### Claude Manager (C:\APPS\CLAUDE)

Main repo clean. **27 of 49 worktrees stale (>7 days):**

| Commit | Age | Count |
|---|---|---|
| b978379 (2026-04-08) | 37d | 7 |
| a6020fc (2026-04-14) | 31d | 1 |
| 521408e (2026-04-19) | 26d | 5 |
| 40ff927 (2026-04-21) | 24d | 14 |

All point to commits reachable from master. No unique work at risk.

---

## Cross-Cutting Issues

- **XC-1** Architecture Principles doc — 5 stale paths (CRITICAL-3).
- **XC-2** OC controls Maia's NSSM service (CRITICAL-2).
- **XC-3** `maia.db` stores other projects' bot tokens. Undocumented dependency. Single point of failure.
- **XC-4** Port 9011 double-registered.
- **XC-5** gsudo superseded but references persist in OC.
- **XC-6** Three projects have no CLAUDE.md (EasyFlow, MapSnap, QI Hive).
- **XC-7** Phantom empty `qi_brain.db` — silent failure mode.

---

## Brain Coverage Gap Analysis

| Project | Last Brain Session | Last Code Activity | Gap | Flag |
|---|---|---|---|---|
| claude_manager | 2026-05-15 22:08 | 2026-05-15 | 0d | In sync |
| qi_hive | 2026-05-14 23:51 | 2026-05-15 | 1d | Minor |
| OpenClaw (capital-O orphan) | 2026-05-14 18:27 | 2026-05-14 | 0d | Wrong project_id |
| openclaw (lowercase) | 2026-05-13 20:11 | 2026-05-14-15 | 1-2d | Casing split |
| maia | 2026-05-13 09:27 | 2026-05-15 | 2d | **Blind spot** |
| naya | 2026-05-13 09:27 | 2026-05-15 | 2d | **Blind spot** |
| nexus | 2026-05-13 09:27 | 2026-05-13 | 0d | In sync |
| easyflow | 2026-05-13 09:27 | 2026-05-13 | 0d | In sync |
| mapsnap | session 158 (post-audit) | 2026-05-15 (major) | 0d | Logged post-audit |
| cognibase | 2026-05-12 19:52 | ~2026-05-09 | 3d | Acceptable |
| autopdf | 2026-04-29 23:46 | 2026-05-14 | 16d | **Stale** |
| mq | None | N/A | N/A | Not started |

---

## NSSM Service Summary

All 12 services RUNNING. All expected ports listening. Detailed status per-project above.

---

## Recommended Next Steps (Prioritized)

**Immediate — before any development work:**

1. **[CRITICAL-1]** Rotate Maia LINE + Facebook credentials. Replace hardcoded values in `maia_server.py` lines 175–188 with empty strings.
2. **[CRITICAL-3]** Fix `QI_Architecture_Principles.md` — replace all 5 `C:\APPS\QI\ECOSYSTEM\` with `C:\QIH\ecosystem\`.
3. **[MAJOR]** Delete phantom 0-byte `C:\QIH\engine\brain\qi_brain.db`.

**This week:**

4. **[CRITICAL-2]** Remove `clean_restart_maia.ps1` from OC or move logic to `C:\APPS\QI\TOOLS\`. Replace `tear_down_bridge.bat` gsudo with QI_Elevate.
5. **[MAJOR]** Add CLAUDE.md to EasyFlow, MapSnap, QIH (copy from Maia/Naya).
6. **[MAJOR]** Fix OpenClaw Brain `project_id` casing. All future OC calls use lowercase.
7. **[MAJOR]** Prune 27 stale Claude Manager worktrees. Start with 7 oldest (37d, commit b978379).
8. **[MAJOR]** Commit today's work across Maia, Naya, MapSnap, QIH.
9. **[MAJOR]** Backfill Brain sessions for Maia, Naya, OpenClaw via `qi.log_session`.
10. **[MINOR]** Resolve port 9011 double-registration.
11. **[MINOR]** Resolve CogniBase / Universal port 8650 conflict.
12. **[MINOR]** Fix OpenClaw `.gitignore` — add `*.env`.
13. **[MINOR]** Create `C:\APPS\OC\LOGS\`.
14. **[MINOR]** Document `maia.db` sibling token dependency in `qi_registry.json`.
15. **[MINOR]** Update MapSnap registry status from `active_stable` to `active_development`.

---

*QI Hive Inspector | 2026-05-15 | Read-only audit*

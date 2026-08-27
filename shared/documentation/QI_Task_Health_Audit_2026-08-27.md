# QI Ecosystem — Scheduled-Task Health Audit
**Date:** 2026-08-27 · **Scope:** all 37 QI/OC/Maia Windows scheduled tasks · **Method:** output-artifact verification only

> **`LastTaskResult` was not used anywhere in this audit.** It is the signal that failed.
> Every verdict below rests on a produced artifact: a success marker inside a log, a git commit,
> a DB row, a written state file, or a delivered message.

---

## 1. The masking finding, re-verified and refined

Re-confirmed independently on this machine:

| Command | Real exit | Reported |
|---|---|---|
| `cmd /c "exit 42"` | 42 | **42** |
| `conhost --headless cmd /c "exit 42"` | 42 | **0** ❌ |
| `conhost --headless C:\NOPE\nothere.exe` | launch failure | **0** ❌ |
| `pythonw -c "sys.exit(42)"` | 42 | **42** ✅ |

**Refinement over the original finding:** `conhost --headless` masks even a *total launch failure* — a
nonexistent binary reports success. And the masking is **specific to `conhost`**: `pythonw.exe`
propagates exit codes correctly.

**Blast radius: 24 of 37 QI tasks are blind.** The other 13 (3 `pythonw`, 10 plain) still have a
trustworthy `LastTaskResult`.

### The mitigation currently in the registry is itself unsafe

`QI_Scheduled_Tasks_Registry.md` §3 already documents the conhost gotcha, but prescribes:

> *"verify a run by checking the log timestamp, not LastTaskResult."*

**This audit proves log-timestamp checking also fails**, and the two dead OC agents show why it
fails in opposite directions:

| Task | Wrapper log during 18-day outage | Would an mtime check have caught it? |
|---|---|---|
| **Kaze** | froze at 2026-08-09 06:00 | ✅ yes — log stopped growing |
| **Yubin** | grew daily with `No such file or directory` | ❌ **no** — log looked perfectly fresh |

Yubin's wrapper log was appended **35 times** while the job was completely dead, because the shell's
own error message is captured by the same `>> log 2>&1` redirect that was supposed to prove success.
**A growing log is not evidence of a successful run.** Only a success *marker* is.

---

## 2. Ranked findings

### 🔴 TIER 1 — DEAD RIGHT NOW (7 tasks)

| # | Task | Dead since | Days | Proof |
|---|---|---|---|---|
| 1 | **QI_TubeScout_AM / _PM** | 2026-06-22 | **66** | `videos.max(discovered_at)` = `2026-06-22T23:03:40`; last sweep = run_id 15 |
| 2 | **OC-Yubin-Daily-8AM / _6PM** | 2026-08-09 | 18 | `last-digest.json` frozen `2026-08-09 07:00:33`; 35 consecutive failure lines |
| 3 | **OC-Asa-Briefing-7AM** | 2026-08-09 | 18 | last `✅ Briefing sent` = 08-09 07:00:18; 18 consecutive failures incl. today |
| 4 | **OC-Sentry-Drift-Sunday-8PM** | *never worked* | ∞ | `REPORTS_DIR=/mnt/c/QIH/engine/hive/inspector/reports` **has never existed** |
| 5 | **OC-Kakei-Weekly-Sunday-7PM** | *never delivered* | ∞ | 11 of 11 logged runs hit `JSONDecodeError` — **and logged `✅ sent` anyway** |

**#1 TubeScout is the worst finding in this audit** — worse than Kaze, and entirely independent of it.
`sweep` and `reclassify` have failed with `invalid_grant: Token has been expired or revoked` on
**every cycle since 2026-06-23**, 222 occurrences, including today at 07:00:16. The cycle then
proceeds through `dedup` and `scout_refresh` on the same stale 4,014-video corpus and signs off with
`===== TubeScout cycle done in 166s =====`. **It reports success twice a day while feeding Kaze a
corpus that has not gained a single video in nine weeks.** Root cause is an expired Google OAuth
refresh token, not scheduling.

**#4 and #5 are a distinct and more troubling class than Kaze:** these never worked *at all*. Sentry
has been silently skipping on a "directory not found — skipping (no error)" guard since inception.
Kakei's Telegram step never checks curl's response, so it prints `✅ Weekly summary sent`
unconditionally. Both were **born dead and reported healthy** — no regression required.

### 🟠 TIER 2 — UNPROVEN (4 tasks)

**OC-Kaze-Digest-6AM/6PM · OC-Kaze-AI-Digest-6AM/6PM.** Repaired today, but **not yet proven via a
scheduled firing.** The only 08-27 artifacts (`AGT-kaze-20260827-delivery.log`, 11:40:43) came from a
*manual* run. Both wrapper logs are still frozen at 2026-08-09 06:00, meaning today's 06:00/06:05
scheduled firings produced nothing. **First real test is tonight 18:00/18:05.** New breakage also
surfaced during the manual run: NotebookLM push fails with `No module named 'playwright'`.

### 🟡 TIER 3 — DEGRADED (2 tasks)

- **QI_NightlyGitSync** — 3 of 4 repos fine. `C:\APPS\PersonalSong` has **ABORTed every night for 18+ runs** on `staged secret(s) detected [plex_token]`; last real commit 2026-07-02, 20 files uncommitted. Separately, **19 registry repos have no nightly sync task at all** (`C:\APPS\OC`, MapSnap, NEXUS, EasyFlow, TubeScout…). *Note: this one was logged correctly every night as `ABORT` — it was never read.*
- **MaiaNightlySync** — stages only `docs/ INTRO/ TOOLS/ MAIA_BUILD_QUEUE.md`, so **code is never staged**. `C:\APPS\QI` currently holds **86 uncommitted changes** including `channels/line.py`, `maia_auth.py`, `tunnel_watchdog.py`. Writes "Nothing staged — skipping commit" and exits clean. Real code has had no GitHub backup for ~2 months.

### 🟢 TIER 4 — HEALTHY, verified by artifact (8 tasks)

`MaiaReconcile` (differentiated per-run content + live batch id) · `QI_BrainBackfill` (row counter
advancing 1759→1767 today) · `QI_McpConnectorGuard` (heartbeat 14:55:01) · `QI_RelaySync` (real
commits + push per cycle) · `QI_EffortLedger_Daily` (**hash-chained DB row** — the best artifact in
the estate) · `QI_DomainDropWatch_Daily` · `QI_ClaudeUpdate_6AM` (structured ledger with an explicit
`noop` result — **correctly distinguishes deliberate no-op from failure**) · `QI_ClaudeSelfAudit`.

### ⚪ TIER 5 — DISABLED, correctly inert (3)

`OC_WSL_KeepAlive` · `QI_ClaudeVoiceBridgeCheck` · `QI_ClaudeVoiceMeeting_8AM` (last two restored by `QI_ClaudeVoiceRestore_20260919`).

---

## 3. Path rot (item 3)

**`C:\OC` junction — verified `LinkType=Junction → C:\APPS\OC`. Load-bearing. Do not remove.**

⚠️ **Correction to the prevailing assumption:** WSL's view of it, `/mnt/c/OC`, carries a creation
time of **2026-08-27 11:40** — roughly three hours before this audit. It did **not** resolve inside
WSL at any point during the 18-day outage. This is the actual mechanism of the OC family's death,
and it means the junction is a **3-hour-old, untested-under-schedule dependency**, not a settled one.

Every OC script hardcodes `/mnt/c/OC/...` internally even though the scripts themselves now live
under `/mnt/c/APPS/OC/`. Verified in `kaze-deliver-telegram.sh` (`LOG_DIR` line 14, `WEB_DIR` line 16,
`latest-digest.md` line 280), plus `kaze-ai-digest.sh`, `oc-morning-briefing.sh`, `kakei-weekly.sh`,
`sentry-weekly-drift.sh`, `yubin-daily.sh`. Two task definitions also still point at the old path
(`OC-Yubin-Daily-8AM`, `OC-Yubin-Daily-6PM`).

**All other referenced paths exist.** No `C:\UNIVERSAL` or `Downloads\LINE BOTS` references remain in
any active task. One latent issue: `maia_nightly_sync.py` writes to the legacy Downloads-slug memory
store (`C--Users-renne-Downloads`), which the 2026-08-22 split made GLOBAL-only.

---

## 4. Proposed pattern — one QI-wide freshness monitor

**Recommendation: a single central monitor, not per-task checks.** Per-task checks have the flaw that
killed Kaze — the check ships inside the thing being checked, so when the task dies the check dies
with it. A dead task cannot report itself dead.

**Host it in `QI_BrainAPI`** (Running/Auto, already always-on, already owns `qi_brain.db` and an HTTP
surface at :9011). Generalise the proven `check_digest_freshness()` in
`C:\APPS\OC\tools\oc-keepalive-daemon.py`, which already does exactly the right thing for one agent.

**Manifest-driven** — a new `C:\QIH\ecosystem\task_health_manifest.json`, sibling to the existing
window policy, one entry per task:

```json
"QI_TubeScout_AM": {
  "check": "sqlite",
  "target": "C:\\APPS\\TUBESCOUT\\tubescout.db",
  "query": "select max(discovered_at) from videos",
  "max_age_hours": 26,
  "owner": "TubeScout",
  "severity": "high"
}
```

Four check types cover the whole estate, ranked by strength — **prefer the strongest available**:

1. **`db`** — a row whose timestamp advances (EffortLedger's hash-chained row is the gold standard)
2. **`marker`** — a specific success string in today's log (`"Unified daily digest complete"`) — **never mere mtime**
3. **`git`** — real commit timestamp in a named repo
4. **`file`** — artifact mtime, only where nothing better exists

**Rules that fall out of this audit and must be encoded:**
- Never accept log *mtime* as proof (Yubin grew while dead).
- Never accept "wrapper exited" as proof (conhost returns 0 for a missing binary).
- A no-op must be *positively declared*, as `QI_ClaudeUpdate_6AM` already does with `result: "noop"` — silence must never be readable as success.
- **Alert on absence, not on error.** Every failure here was an absence.
- Compare against the task's *own* schedule from Task Scheduler, so a weekly task isn't judged on a daily clock.

Surface it as `GET /health/tasks` on Brain, a Mission Control tile, and one Telegram alert per
newly-stale task per day. **Bootstrap value: this manifest would have caught all 7 dead tasks —
including TubeScout, which nothing else was looking at.**

---

## 5. Recommended actions, in order

| # | Action | Tier |
|---|---|---|
| 1 | Re-authorize the TubeScout Google OAuth refresh token — **66 days of dead intake** | 🔴 |
| 2 | Verify tonight ≥18:10 that Kaze 6PM ×2 and Yubin 6PM actually produced artifacts | 🔴 |
| 3 | Repoint the 6 OC scripts + 2 Yubin task definitions to `/mnt/c/APPS/OC` — retire the junction *dependency* (keep the junction itself) | 🟠 |
| 4 | Fix Kakei's unconditional `✅ sent` and Sentry's never-existent reports dir | 🟠 |
| 5 | Untrack the `plex_token` file in PersonalSong + `.gitignore` it | 🟡 |
| 6 | Widen MaiaNightlySync staging to cover code — 86 files unbacked | 🟡 |
| 7 | Build the manifest monitor in Brain (§4) | 🟢 |
| 8 | `pip install playwright` in the OC WSL env | 🟢 |

---

## 6. REMEDIATION — completed 2026-08-27, same day

Renne authorised the full remediation. **8 of 9 items are done and verified; 1 is blocked on him.**

Every "fixed" claim below was proven by an artifact, not by an exit code.

| # | Item | Status | Proof |
|---|---|---|---|
| 1 | TubeScout OAuth | 🔴 **BLOCKED — needs Renne** | Requires interactive Google sign-in + a Cloud Console publishing change. See `C:\APPS\TUBESCOUT\REAUTH_YOUTUBE.md` |
| 2 | Verify Kaze/Yubin scheduled path | ✅ done | Fired the **real task definitions** via `Start-ScheduledTask` — no waiting for 18:00 |
| 3 | Repoint OC family off `/mnt/c/OC` | ✅ done | 15 refs across 6 scripts, all `bash -n` clean, all live-tested |
| 4 | Kakei unconditional success | ✅ verified | Code was already fixed; the path outage was what stopped it running. Now runs clean |
| 5 | Sentry never-existent reports dir | ✅ done | New `inspector_export_snapshot.py` bridges `compliance_log` → JSON. **First drift report in its life sent** |
| 6 | PersonalSong `plex_token` | ✅ done | `.bak-*` ignored; committed + pushed, first time since 2026-07-02 |
| 7 | MaiaNightlySync never stages code | ✅ done | Allowlist → `git add -A`; commit `8de5645`, **35 files pushed** |
| 8 | Central freshness monitor | ✅ done | `QI_TaskHealth` live, 22 tasks, 30-min cadence, Telegram alert **delivered** |
| 9 | playwright in OC WSL | ✅ done | 1.62.0 + chromium headless shell installed |

### What the artifacts say now

- **Kaze** — `cron.log` broke its 18-day freeze (2026-08-09 06:00 → 2026-08-27 16:20) and carries `✅ Unified daily digest complete`. `cron-ai.log` likewise.
- **Yubin** — `last-digest.json` moved from `2026-08-09 07:00:33` → `2026-08-27 16:22`. Was still failing at 07:00 that morning.
- **Asa** — `✅ Briefing sent`, first since 2026-08-09.
- **Sentry** — `✅ Drift report sent`, **first ever**.
- **Kakei** — `✅ Weekly summary sent`, and now only prints that on Telegram's `"ok":true`.

### Two things found during remediation that the audit missed

**1. TubeScout's real root cause is not just an expired token.** `token.json` was
issued 2026-06-15 and expired 2026-06-23 — **exactly 7 days**. That is the
signature of a Google Cloud consent screen still in **"Testing"** status, where
refresh tokens hard-expire at 7 days. Re-authing alone would buy another week and
then die silently again. The runbook therefore leads with publishing the app.

**2. The `nssm_install_qi` elevation rule is currently unsatisfiable.** It permits
python only at `C:\Windows\System32`, `C:\1-AI\APPS\PYTHON` or `C:\Python*` —
**none of which exist on this machine any more**; Python lives at
`C:\Program Files\Python311`. So the broker denies every QI service install. The
whitelist was **not** widened (security boundaries are Tier 1). `QI_TaskHealth`
runs as a user-level scheduled task in the meantime. To promote it, from an
**elevated** shell:

```bash
C:\QIH\engine\bin\nssm.exe install QI_TaskHealth "C:\Program Files\Python311\python.exe" "C:\QIH\tools\qi_task_health.py --daemon"
```

then `nssm set QI_TaskHealth AppDirectory C:\QIH` and `nssm start QI_TaskHealth`,
and delete the interim scheduled task. Either the rule's python paths need
updating or that promotion stays a manual step.

### Honest caveat on the interim host

The `QI_TaskHealth` scheduled task is itself wrapped in `conhost --headless`, so
its own `LastTaskResult` is meaningless — the very blindness this monitor exists
to compensate for. That is tolerable **only** because the monitor's product is a
Telegram alert plus `C:\QIH\data\task_health.json`, and the manifest contains a
self-watch entry on that file: if the monitor dies, its own staleness is visible
rather than reading as a healthy estate. Promoting it to a real service removes
the caveat entirely.

### Still open

- **TubeScout OAuth (item 1)** — the one genuinely blocked item, and still the highest-impact one.
- **19 registry repos have no nightly git sync at all** (`C:\APPS\OC`, MapSnap, NEXUS, EasyFlow, TubeScout…). Out of scope for this remediation; worth its own pass.
- **`noos.ai` silently dropped** from the domain watchlist ~2026-08-22 — confirm whether that was deliberate.

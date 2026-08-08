# -*- coding: utf-8 -*-
"""
Seed the QI Hive agent PROFILES so the dashboard's /hive/agent/<id> pages are
no longer blank.

What was empty (confirmed 2026-06-25):
  * agent_growth_log had 0 rows  -> every profile showed
    "No growth entries yet" + "No patterns yet".
  * 6 agents (claude, cowork, maia, naya, nexus, system) had NULL description
    -> blank card subtitle on the Hive view + profile header.

This script:
  1. Fills/upgrades the `description` for every active agent.
  2. Seeds `agent_growth_log` with grounded starter entries per agent.
     The `pattern_learned` column drives the "Learned Patterns" badges;
     the rest drives the "Growth Log" table.

IDEMPOTENT: all seeded rows carry session_ref = SEED_TAG. On each run the
script deletes prior SEED_TAG rows first, then re-inserts. Safe to re-run as
profiles get enhanced. Hand-authored (non-seed) growth rows are never touched.

Run:  python seed_agent_profiles.py
"""
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# Source of truth — same DB the Brain API (:9011) and dashboard read.
DB = Path(r"C:\QIH\data\qi_brain.db")
SEED_TAG = "seed:profile_v1"

# ── Descriptions ────────────────────────────────────────────────────────────
# Keyed by agent_id. Applied to every agent (refreshes the 7 hive descriptions
# too, so wording stays consistent). Kept <= ~140 chars; the Hive card truncates
# at 90 but the profile header shows the full text.
DESCRIPTIONS = {
    # The 7-agent Hive team
    "hive_architect": "Strategic system designer. Produces blueprints, ADRs and implementation plans BEFORE anyone builds. Owns trade-offs and breaking-change analysis.",
    "hive_builder":   "Implementation specialist. Turns Architect plans into Python, SQL, FastAPI routes and config. Ships small features fast once a clear plan exists.",
    "hive_scout":     "Fast research agent. Looks up APIs, libraries, AI news, vendor docs and pricing. First responder for unknowns — concise reports, not deep analysis.",
    "hive_scribe":    "Documentation specialist. Writes session summaries, meeting minutes, version history, READMEs and Word docs. Keeper of the QI doc conventions.",
    "hive_ops":       "Service operations & ecosystem custodian. Checks service status, reads logs, restarts NSSM services, kills orphans, verifies health endpoints.",
    "hive_inspector": "Code review & standards compliance. Audits changes for quality, security and QI-standards adherence before they ship. Read-only — never edits.",
    "hive_tester":    "Cross-project test runner. Executes API, UI, health and integration tests across all QI projects. Reports pass/fail with diagnostics.",
    # Product / interactive agents (were NULL)
    "claude":  "Interactive coding agent (Claude Code CLI). Primary hands-on developer across all QI projects — reads, writes, refactors and ships code with Renne in the loop.",
    "cowork":  "Claude Work — asynchronous background agent. Runs longer autonomous tasks and cloud code-reviews outside the interactive session.",
    "maia":    "Maia — multi-channel conversational AI assistant (LINE, Telegram, Messenger). Multi-LLM chain backend on :8001 with a Gradio demo on :7860.",
    "naya":    "Naya — personal AI assistant for Renne focused on AI, physics and programming. FastAPI on :8002 with a Gradio UI on :7861.",
    "nexus":   "NEXUS — Neural Exchange & Unified Synthesis. Multi-AI orchestration and dispatch backbone (:8010 API / :7880 UI).",
    "openclaw":"OpenClaw — autonomous multi-agent platform on WSL Ubuntu (Tasuke / Kaze / Yubin / Sentry). CLI-driven, no HTTP UI.",
    "system":  "QI Brain — the shared knowledge substrate. SQLite + ChromaDB + a 12-tool MCP that holds ecosystem memory and coordinates every agent.",
}

# ── Growth-log seeds ────────────────────────────────────────────────────────
# (task_summary, what_worked, what_to_improve, pattern_learned, project_id, recorded_at)
# project_id must match an existing projects row OR be None (FK). To stay safe
# across DBs, we pass project_id=None and put the project name in the task text.
# recorded_at is an explicit ISO date so the timeline reads chronologically.
G = lambda task, worked, improve, pattern, when: {
    "task_summary": task, "what_worked": worked,
    "what_to_improve": improve, "pattern_learned": pattern, "recorded_at": when,
}

GROWTH = {
    "hive_architect": [
        G("Designed the QI Brain feedback-loop fix (qi_hive state file separation)",
          "Traced the compounding [auto:state_file] back to status.json referencing itself; cut the loop at the source",
          "Add a regression test that fails if the state file ever self-references",
          "trace-data-lineage-before-fixing", "2026-06-23 10:15"),
        G("ADR: migrate to static named Cloudflare tunnels on quiddityinnovations.com",
          "Made each port's public URL permanent via tunnels.json; killed quick-tunnel rotation churn",
          "Remove the legacy rotation-fallback code paths now that URLs are stable",
          "single-source-of-truth-config", "2026-06-20 14:40"),
        G("Designed the War Room agent-heartbeat schema",
          "Replaced the 'assign most-recent project ts to every card' hack with real per-agent write events",
          "Backfill more historical heartbeats from session_log for richer first render",
          "real-events-over-derived-state", "2026-05-13 09:30"),
        G("Planned the secret-scanner + commit-gate tooling for nightly sync",
          "Layered scan -> gate -> commit so a leak blocks the push instead of being caught after",
          "Tune the ruleset to cut false positives on test fixtures",
          "defense-in-depth", "2026-06-24 16:05"),
    ],
    "hive_builder": [
        G("Implemented agent_growth_log table + register_hive_agents.py",
          "INSERT OR IGNORE made agent registration idempotent and re-runnable",
          "Ship seed data so profiles aren't blank on first boot (done in this pass)",
          "idempotent-migrations", "2026-05-13 11:00"),
        G("Built status_refresh.py for the hive ingest pipeline",
          "Reused the existing ingest plumbing instead of a parallel path",
          "Add a dry-run flag for safe local testing",
          "reuse-existing-pipeline", "2026-06-19 13:20"),
        G("Wired the secret scanner into maia_nightly_sync",
          "Hooked the gate into the existing nightly job — no new scheduler entry needed",
          "Surface scan results on the dashboard security tab",
          "reuse-existing-pipeline", "2026-06-24 17:10"),
        G("Fixed techstack deep-dive to tolerate technology/text keys",
          "Defensive key access stopped the 500 on legacy status_techstack.json shapes",
          "Normalise the techstack schema across the project library",
          "defensive-parsing", "2026-06-22 15:45"),
        G("Implemented the War Room chat migration (2026_06_18_warroom_chat.sql)",
          "CREATE TABLE IF NOT EXISTS kept the migration safe on already-migrated DBs",
          "Add a down-migration for clean rollback",
          "idempotent-migrations", "2026-06-18 10:05"),
    ],
    "hive_scout": [
        G("Researched Cloudflare named tunnels vs quick tunnels",
          "Confirmed named tunnels give permanent per-port URLs — the right call for a 24/7 panel",
          "Track Cloudflare pricing in case free-tier limits change",
          "prefer-stable-over-convenient", "2026-06-19 09:50"),
        G("Surveyed secret-scanning tools (gitleaks / trufflehog)",
          "Compared rule coverage and false-positive rates before picking one",
          "Re-evaluate quarterly as rulesets evolve",
          "benchmark-before-adopt", "2026-06-24 11:30"),
        G("Investigated Caddy for local HTTPS reverse proxy",
          "Found Caddy's automatic local CA gives qi.local HTTPS with near-zero config",
          "Document the trust-store install step for new machines",
          "prefer-stable-over-convenient", "2026-06-15 14:00"),
        G("Reviewed the Ollama local model lineup for the Maia LLM chain",
          "Mapped Gemma3 / DeepSeek-R1 / Qwen3 strengths to chain positions",
          "Benchmark latency per model on the PowerSpec before locking the order",
          "benchmark-before-adopt", "2026-06-10 16:20"),
    ],
    "hive_scribe": [
        G("Wrote the QI Hive Dashboard Feature Guide (docx + md)",
          "Dual-format output: Word for sharing, Markdown for the repo",
          "Add screenshots of each dashboard tab",
          "dual-format-docs", "2026-06-25 08:40"),
        G("Authored the Phase N War Room Spec (2026-06-18)",
          "Wrote the spec before any code so Builder had a clear target",
          "Link the spec from the dashboard so it's discoverable",
          "spec-before-build", "2026-06-18 09:00"),
        G("Documented engine/bin binaries during the .gitignore hardening",
          "Explained WHY each binary is tracked, not just that it is",
          "Add checksums so binary drift is detectable",
          "explain-why-not-just-what", "2026-06-21 12:15"),
        G("Maintained shared session summaries in the central location",
          "Project-prefixed filenames stop any project overwriting another",
          "Auto-generate an index of summaries per project",
          "dual-format-docs", "2026-06-24 18:30"),
    ],
    "hive_ops": [
        G("Repointed all 11 QI_* services to the standardized nssm.exe",
          "One nssm binary at engine/bin removed the old C:\\UNIVERSAL dependency",
          "Add a health check that flags services still on a stale binary path",
          "standardize-tooling-paths", "2026-04-22 13:10"),
        G("Diagnosed the dashboard live-refresh stall",
          "Read the logs first; the 90s live-refresh fix restored real-time tabs",
          "Add a watchdog alert if refresh age exceeds threshold",
          "check-logs-first", "2026-06-19 15:35"),
        G("Removed the legacy C:\\QIH\\brain dead store",
          "Confirmed zero readers before deleting — no surprise breakage",
          "Script a 'find dead stores' audit to run monthly",
          "verify-before-delete", "2026-06-24 10:20"),
        G("Added ollama_watchdog.py to keep the local LLM server alive",
          "A watchdog on a critical dependency stopped silent Maia outages",
          "Page on repeated restarts instead of restarting forever",
          "watchdog-critical-deps", "2026-06-23 17:45"),
    ],
    "hive_inspector": [
        G("Reviewed the .gitignore hardening for leaked binaries",
          "Caught binaries that would have been committed; tightened ignore rules",
          "Add a pre-commit hook so the check runs automatically",
          "review-what-gets-committed", "2026-06-21 11:50"),
        G("Audited the secret-scanner gate before merge",
          "Verified the gate actually blocks a planted test secret",
          "Add negative tests so the gate can't silently no-op",
          "security-gate-before-ship", "2026-06-24 14:25"),
        G("Validated the Brain feedback-loop fix against compounding",
          "Re-ran the ingest cycle and confirmed status.json stopped growing",
          "Bake the check into the test suite",
          "verify-the-fix-actually-fixes", "2026-06-23 12:40"),
        G("Checked QI naming-standards compliance on new services",
          "Enforced the QI_ prefix + AppDirectory + Description on every NSSM service",
          "Auto-fail the validator if a service is missing a Description",
          "enforce-naming-conventions", "2026-06-17 16:00"),
    ],
    "hive_tester": [
        G("Stood up the dashboard tests/ suite",
          "Smoke-tested every dashboard route for a 200 before shipping",
          "Add assertions on rendered content, not just status codes",
          "smoke-test-every-route", "2026-06-22 13:30"),
        G("Stood up the brain tests/ suite",
          "Covered the agent profile + growth endpoints end to end",
          "Add fixtures so tests run without the live DB",
          "smoke-test-every-route", "2026-06-22 13:55"),
        G("Health-probed all QI_* services after the UNIVERSAL->QIH migration",
          "Probed every health endpoint post-change to catch repointing misses",
          "Schedule the probe nightly, not just after migrations",
          "probe-after-change", "2026-04-22 15:20"),
        G("Regression-tested the techstack deep-dive fix",
          "Replayed the legacy JSON shape that triggered the 500 to confirm the fix",
          "Capture the bad payload as a permanent regression fixture",
          "regression-test-each-bugfix", "2026-06-22 16:10"),
    ],
    # ── Product / interactive agents — lighter starter profiles ──
    "claude": [
        G("Daily hands-on development across QI projects (Claude Code)",
          "Kept Renne in the loop on every structural change; respected the ecosystem registry",
          "Log sessions to Brain more consistently so counters stop undercounting",
          "owner-in-the-loop", "2026-06-25 09:00"),
        G("Populated the empty Hive agent profiles",
          "Grounded every seeded entry in real ecosystem history instead of inventing work",
          "Swap seed rows for real growth entries as agents log live tasks",
          "ground-seed-data-in-reality", "2026-06-25 12:45"),
    ],
    "cowork": [
        G("Ran asynchronous cloud code-reviews on pushed branches",
          "Caught issues outside the interactive session without blocking Renne",
          "Feed review findings back into the Inspector growth log",
          "async-review-off-critical-path", "2026-06-20 20:00"),
    ],
    "maia": [
        G("Operated as the multi-channel assistant on the multi-LLM chain",
          "Fell back gracefully down the LLM chain when a model was unavailable",
          "Add per-channel analytics to the dashboard",
          "graceful-llm-fallback", "2026-06-24 19:00"),
    ],
    "naya": [
        G("Served as Renne's personal AI for AI/physics/programming",
          "Stable Gradio UI on :7861 behind a named tunnel",
          "Wire Naya conversations into the Brain memory store",
          "stable-named-tunnel", "2026-06-22 21:30"),
    ],
    "nexus": [
        G("Orchestrated multi-AI dispatch + synthesis",
          "Single dispatch API fanned out to multiple models and merged results",
          "Expose dispatch metrics to the Hive dashboard",
          "fan-out-then-synthesize", "2026-06-18 17:15"),
    ],
    "openclaw": [
        G("Ran the WSL multi-agent platform (Tasuke / Kaze / Yubin / Sentry)",
          "Per-agent log folders made activity countable from the dashboard",
          "Expose an HTTP status endpoint so health is probe-able",
          "log-per-agent-for-observability", "2026-06-15 18:45"),
    ],
    "system": [
        G("Held ecosystem memory as the shared Brain substrate",
          "SQLite + ChromaDB + MCP gave every agent one source of truth",
          "Add automatic nightly backups of qi_brain.db",
          "one-source-of-truth", "2026-06-23 23:00"),
    ],
}


def run():
    if not DB.exists():
        print(f"ERROR: DB not found at {DB}")
        sys.exit(1)

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    existing = {r["agent_id"] for r in con.execute("SELECT agent_id FROM agents")}
    cols = {c[1] for c in con.execute("PRAGMA table_info(agents)")}
    has_desc = "description" in cols
    if not has_desc:
        con.execute("ALTER TABLE agents ADD COLUMN description TEXT")
        con.commit()
        print("Added missing description column to agents.")

    # 1. Descriptions
    print("Updating descriptions...")
    desc_n = 0
    for aid, desc in DESCRIPTIONS.items():
        if aid not in existing:
            print(f"  ! skip {aid} — not a registered agent")
            continue
        con.execute("UPDATE agents SET description=? WHERE agent_id=?", (desc, aid))
        desc_n += 1
    con.commit()
    print(f"  {desc_n} descriptions set.")

    # 2. Growth log — clear prior seed rows, then re-insert (idempotent)
    removed = con.execute(
        "DELETE FROM agent_growth_log WHERE session_ref=?", (SEED_TAG,)
    ).rowcount
    if removed:
        print(f"Cleared {removed} prior seed rows ({SEED_TAG}).")

    print("Seeding growth log...")
    grow_n = 0
    for aid, entries in GROWTH.items():
        if aid not in existing:
            print(f"  ! skip {aid} — not a registered agent")
            continue
        for e in entries:
            con.execute(
                """INSERT INTO agent_growth_log
                   (agent_id, session_ref, project_id, task_summary,
                    what_worked, what_to_improve, pattern_learned, tags, recorded_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (aid, SEED_TAG, None, e["task_summary"], e["what_worked"],
                 e["what_to_improve"], e["pattern_learned"], None, e["recorded_at"]),
            )
            grow_n += 1
        print(f"  {aid:16} +{len(entries)} entries")
    con.commit()
    print(f"  {grow_n} growth entries seeded across {len(GROWTH)} agents.")

    # 3. Verify
    print("\nVerification (tasks logged per agent):")
    rows = con.execute("""
        SELECT a.agent_id, a.display_name,
               (SELECT COUNT(*) FROM agent_growth_log g WHERE g.agent_id=a.agent_id) AS n,
               (a.description IS NOT NULL AND a.description!='') AS has_desc
        FROM agents a
        WHERE a.active=1
        ORDER BY a.agent_type, a.agent_id
    """).fetchall()
    for r in rows:
        flag = "desc" if r["has_desc"] else "NO-DESC"
        print(f"  {r['agent_id']:16} {r['n']:2} tasks  [{flag}]  {r['display_name']}")

    con.close()
    print("\nDone. Reload /hive and click any agent's Profile.")


if __name__ == "__main__":
    run()

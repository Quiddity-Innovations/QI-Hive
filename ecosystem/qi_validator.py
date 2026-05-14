"""
Quiddity Innovations — Project Compliance Validator
Checks any QI project against the Architecture Principles and Standards.

Usage:
    python qi_validator.py                    # check ALL registered projects
    python qi_validator.py --project nexus    # check one project
    python qi_validator.py --project nexus --live  # also ping live endpoints

Exit codes:  0 = all pass  |  1 = one or more failures
"""
import sys
import os
import json
import argparse
import httpx
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ECOSYSTEM_DIR = Path(__file__).parent
REGISTRY_PATH = ECOSYSTEM_DIR / "qi_registry.json"

PASS  = "[PASS]"
FAIL  = "[FAIL]"
WARN  = "[WARN]"
SKIP  = "[SKIP]"

with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
    REGISTRY = json.load(f)

PROJECTS = {p["id"]: p for p in REGISTRY["projects"]}


def check(label: str, condition: bool, critical: bool = True) -> bool:
    """Print a PASS/FAIL/WARN line and return whether the check passed."""
    icon = PASS if condition else (FAIL if critical else WARN)
    print(f"  {icon}  {label}")
    return condition


def validate_project(pid: str, live: bool = False) -> tuple[int, int]:
    """Returns (pass_count, fail_count)."""
    if pid not in PROJECTS:
        print(f"\n  {FAIL}  Project '{pid}' not found in qi_registry.json")
        return 0, 1

    proj = PROJECTS[pid]
    path = Path(proj.get("path", ""))
    passed = failed = 0

    print(f"\n{'='*60}")
    print(f"  Project: {proj['name']} ({pid})")
    print(f"  Path:    {path}")
    print(f"  Status:  {proj.get('status', 'unknown')}")
    print(f"{'='*60}")

    # ── Structural checks ─────────────────────────────────────────
    print("\n  [ Structure ]")

    def c(label, cond, critical=True):
        nonlocal passed, failed
        ok = check(label, cond, critical)
        if ok: passed += 1
        else: failed += 1
        return ok

    c("Project path exists", path.exists())
    c("CLAUDE.md exists at project root", (path / "CLAUDE.md").exists())
    c("requirements.txt exists", (path / "requirements.txt").exists(), critical=False)
    c(".gitignore exists", (path / ".gitignore").exists())
    c("secrets/ folder exists", (path / "secrets").exists(), critical=False)

    # secrets not committed
    gitignore_path = path / ".gitignore"
    if gitignore_path.exists():
        gi_content = gitignore_path.read_text(encoding="utf-8", errors="replace")
        c("secrets/ is in .gitignore", "secrets/" in gi_content or "secrets\\" in gi_content)
        c("*.env is in .gitignore", "*.env" in gi_content)
    else:
        c("secrets/ is in .gitignore", False)
        c("*.env is in .gitignore", False)

    # Documentation folder
    doc_folder_name = f"Quiddity Innovations - {proj['name']} Documentation"
    doc_path = path / doc_folder_name
    c(f"Documentation folder exists: '{doc_folder_name}'", doc_path.exists(), critical=False)
    if doc_path.exists():
        c("Session Summaries subfolder exists", (doc_path / "Session Summaries").exists(), critical=False)

    # ── Registry checks ────────────────────────────────────────────
    print("\n  [ Registry ]")

    ports = proj.get("ports", {})
    port_strategy = REGISTRY.get("port_strategy", {})

    c("Project has at least one port registered", len(ports) > 0, critical=False)

    for svc, port_info in ports.items():
        current = port_info.get("current")
        if current is None:
            c(f"Port '{svc}' has a current value", False, critical=False)
            continue
        c(f"Port '{svc}' ({current}) has a value", True)

        # Check no other project uses this port
        conflicts = []
        for other_id, other_proj in PROJECTS.items():
            if other_id == pid:
                continue
            for other_svc, other_info in other_proj.get("ports", {}).items():
                if other_info.get("current") == current:
                    conflicts.append(f"{other_id}.{other_svc}")
        c(f"Port {current} has no conflicts with other projects",
          len(conflicts) == 0,
          critical=True if conflicts else False)
        if conflicts:
            print(f"         !! Conflicts with: {', '.join(conflicts)}")

    c("family_tier declared", "family_tier" in proj)
    c("exposes_to_ecosystem declared", "exposes_to_ecosystem" in proj, critical=False)

    # paths.logs — warn if missing or non-existent (not a hard fail)
    logs_path_str = (proj.get("paths") or {}).get("logs")
    if logs_path_str:
        c(f"paths.logs exists on disk ({logs_path_str})", Path(logs_path_str).exists(), critical=False)
    else:
        check("paths.logs declared in registry", False, critical=False)

    # ── CLAUDE.md content checks ───────────────────────────────────
    print("\n  [ CLAUDE.md Content ]")
    claude_path = path / "CLAUDE.md"
    if claude_path.exists():
        content = claude_path.read_text(encoding="utf-8", errors="replace")
        c("References QI_Standards.md", "QI_Standards" in content)
        c("References qi_registry.json", "qi_registry" in content)
        c("Lists parallel projects with ports", any(
            str(p.get("ports", {}).get("api", {}).get("current", "")) in content
            for pid2, p in PROJECTS.items() if pid2 != pid and p.get("ports")
        ), critical=False)
    else:
        c("CLAUDE.md readable", False)

    # ── Live endpoint checks (optional) ───────────────────────────
    if live:
        print("\n  [ Live Endpoints ]")
        api_port = ports.get("api", {}).get("current")
        if api_port:
            base = f"http://127.0.0.1:{api_port}"
            for endpoint, expected_key in [("/health", "status"), ("/version", "project"), ("/info", None)]:
                try:
                    r = httpx.get(f"{base}{endpoint}", timeout=3)
                    if r.status_code == 200:
                        data = r.json()
                        if expected_key:
                            c(f"GET {endpoint} returns '{expected_key}' field",
                              expected_key in data)
                        else:
                            c(f"GET {endpoint} returns 200", True)
                    else:
                        c(f"GET {endpoint} returns 200 (got {r.status_code})", False, critical=False)
                except Exception as e:
                    c(f"GET {endpoint} reachable", False, critical=False)
        else:
            print(f"  {SKIP}  No API port registered — skipping live checks")

    print(f"\n  Result: {passed} passed, {failed} failed")
    return passed, failed


def main():
    """Parse arguments and run validation against one or all registered projects."""
    parser = argparse.ArgumentParser(description="QI Project Compliance Validator")
    parser.add_argument("--project", "-p", help="Project ID to validate (default: all)")
    parser.add_argument("--live", "-l", action="store_true", help="Ping live endpoints")
    args = parser.parse_args()

    print("=" * 60)
    print("  Quiddity Innovations — Project Compliance Validator")
    print("=" * 60)

    target_ids = [args.project] if args.project else list(PROJECTS.keys())
    total_pass = total_fail = 0

    for pid in target_ids:
        p, f = validate_project(pid, live=args.live)
        total_pass += p
        total_fail += f

    print(f"\n{'='*60}")
    print(f"  TOTAL: {total_pass} passed, {total_fail} failed across {len(target_ids)} project(s)")
    if total_fail == 0:
        print("  ALL PROJECTS COMPLIANT")
    else:
        print(f"  {total_fail} ISSUE(S) REQUIRE ATTENTION")
    print("=" * 60)

    sys.exit(0 if total_fail == 0 else 1)


if __name__ == "__main__":
    main()

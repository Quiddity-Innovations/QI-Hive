# -*- coding: utf-8 -*-
"""
QI Test Runner
Runs the full pytest suite, saves results JSON, and auto-creates kanban tasks for failures.

Usage:
  python C:\Claude\Tests\run_tests.py           # all tests
  python C:\Claude\Tests\run_tests.py smoke     # smoke only
  python C:\Claude\Tests\run_tests.py api       # API tests only
  python C:\Claude\Tests\run_tests.py ui        # UI tests only
  python C:\Claude\Tests\run_tests.py --no-tasks  # run tests, skip task creation
"""

import json
import sys
import subprocess
import uuid
from datetime import datetime
from pathlib import Path

TESTS_DIR   = Path(__file__).parent
RESULTS_DIR = TESTS_DIR / "results"
TASKS_FILE  = Path(r"C:\Claude\tasks.json")

RESULTS_DIR.mkdir(exist_ok=True)

SUITE_MAP = {
    "smoke": [str(TESTS_DIR / "test_smoke.py")],
    "api":   [
        str(TESTS_DIR / "test_maia_api.py"),
        str(TESTS_DIR / "test_naya_api.py"),
        str(TESTS_DIR / "test_nexus_api.py"),
        str(TESTS_DIR / "test_dashboard_api.py"),
    ],
    "ui":    [str(TESTS_DIR / "test_dashboard_ui.py")],
    "all":   [str(TESTS_DIR)],
}

# Exclude load tests from default runs
EXCLUDE = ["--ignore", str(TESTS_DIR / "load")]


def run_pytest(targets: list[str]) -> dict:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = RESULTS_DIR / f"run_{timestamp}.json"
    latest_file = RESULTS_DIR / "latest.json"

    cmd = [
        sys.executable, "-m", "pytest",
        *targets,
        *EXCLUDE,
        "-v",
        "--json-report",
        f"--json-report-file={result_file}",
        "--tb=short",
        "-q",
    ]

    print(f"\n{'='*60}")
    print(f"  QI TEST RUN — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    proc = subprocess.run(cmd, capture_output=False, text=True)

    # Copy to latest.json for dashboard to read
    if result_file.exists():
        import shutil
        shutil.copy(result_file, latest_file)
        with open(result_file, encoding="utf-8") as f:
            data = json.load(f)
        return data

    return {"summary": {"failed": 0, "passed": 0, "skipped": 0}, "tests": []}


def create_tasks_for_failures(results: dict) -> int:
    """Create kanban tasks for every test failure. Returns number of tasks created."""
    if not TASKS_FILE.exists():
        print("⚠️  tasks.json not found — skipping task creation")
        return 0

    with open(TASKS_FILE, encoding="utf-8") as f:
        tasks_data = json.load(f)
    tasks = tasks_data.get("tasks", [])

    open_titles = {t["title"].lower() for t in tasks if t.get("column") != "done"}
    today = datetime.now().strftime("%Y-%m-%d")
    created = 0

    failed_tests = [t for t in results.get("tests", []) if t.get("outcome") == "failed"]

    for test in failed_tests:
        test_name = test.get("nodeid", "unknown test")
        # Extract project name from test file name
        parts = test_name.split("::")
        file_part = parts[0] if parts else test_name
        project = "Claude_Manager"
        for proj_hint in ["maia", "naya", "nexus", "dashboard"]:
            if proj_hint in file_part.lower():
                project = proj_hint.capitalize()
                if proj_hint == "nexus":
                    project = "NEXUS"
                elif proj_hint == "dashboard":
                    project = "Claude_Manager"
                break

        title = f"Fix failing test: {parts[-1] if len(parts) > 1 else test_name}"
        if title.lower() in open_titles:
            continue  # already on board

        # Get failure message
        call = test.get("call", {})
        crash = call.get("crash", {})
        message = crash.get("message", "No details available")[:200]

        new_task = {
            "id": "t" + uuid.uuid4().hex[:6],
            "column": "backlog",
            "project": project,
            "title": title,
            "description": f"Test failure detected by Tester agent.\n\nTest: {test_name}\nError: {message}",
            "agent": "builder",
            "priority": "high",
            "created_at": today,
        }
        tasks.append(new_task)
        open_titles.add(title.lower())
        created += 1
        print(f"  📋 Task created: {title}")

    if created > 0:
        tasks_data["tasks"] = tasks
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks_data, f, indent=2)

    return created


def print_summary(results: dict):
    summary = results.get("summary", {})
    passed  = summary.get("passed", 0)
    failed  = summary.get("failed", 0)
    skipped = summary.get("skipped", 0)
    total   = summary.get("total", passed + failed + skipped)

    print(f"\n{'='*60}")
    print(f"  RESULTS: {passed}/{total} passed  |  {failed} failed  |  {skipped} skipped")
    print(f"{'='*60}\n")

    if failed:
        print("Failed tests:")
        for t in results.get("tests", []):
            if t.get("outcome") == "failed":
                print(f"  ❌ {t['nodeid']}")
        print()


def main():
    args = sys.argv[1:]
    create_tasks = "--no-tasks" not in args
    args = [a for a in args if a != "--no-tasks"]

    suite = args[0] if args else "all"
    targets = SUITE_MAP.get(suite, SUITE_MAP["all"])

    results = run_pytest(targets)
    print_summary(results)

    if create_tasks:
        n = create_tasks_for_failures(results)
        if n:
            print(f"✅ {n} new task(s) added to the kanban board for failures.\n")
        else:
            print("✅ No new tasks needed — all failures already on board or no failures.\n")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

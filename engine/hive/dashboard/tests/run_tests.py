"""Fallback test runner — only used when pytest-json-report is NOT installed.

Emits the same JSON shape server.py's render_tests()/api_run_tests() expect:
  {"created": <ts>, "summary": {"passed":, "failed":, "skipped":, "total":},
   "tests": [{"nodeid":, "outcome":, "call": {"duration":}}]}

Usage: python run_tests.py <suite>   where suite in smoke|api|ui|all
"""
import json
import sys
import time
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).parent
RESULTS_FILE = Path(r"C:\QIH\data\tests\latest.json")

_SUITE_PATTERNS = {
    "smoke": "test_smoke.py",
    "api": "test_api*.py",
    "ui": "test_ui*.py",
    "all": None,
}


class _JsonCollectorPlugin:
    def __init__(self):
        self.tests = []

    def pytest_runtest_logreport(self, report):
        if report.when != "call" and not (report.when == "setup" and report.outcome != "passed"):
            return
        self.tests.append({
            "nodeid": report.nodeid,
            "outcome": report.outcome,
            "call": {"duration": getattr(report, "duration", 0.0)},
        })


def main():
    suite = sys.argv[1] if len(sys.argv) > 1 else "all"
    pattern = _SUITE_PATTERNS.get(suite)
    target = str(TESTS_DIR)
    if pattern:
        matches = list(TESTS_DIR.glob(pattern))
        if matches:
            target = str(TESTS_DIR / pattern)

    collector = _JsonCollectorPlugin()
    pytest.main(["-q", target], plugins=[collector])

    passed = sum(1 for t in collector.tests if t["outcome"] == "passed")
    failed = sum(1 for t in collector.tests if t["outcome"] == "failed")
    skipped = sum(1 for t in collector.tests if t["outcome"] == "skipped")

    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "created": time.time(),
            "summary": {
                "passed": passed, "failed": failed, "skipped": skipped,
                "total": len(collector.tests),
            },
            "tests": collector.tests,
        }, f, indent=2)


if __name__ == "__main__":
    main()

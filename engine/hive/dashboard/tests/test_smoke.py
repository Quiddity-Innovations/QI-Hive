# -*- coding: utf-8 -*-
"""
Smoke tests for QI Hive Dashboard (FastAPI, port 8600).

Read-only contract checks only. No state-mutating endpoints are exercised.

Run:
    C:\\Program Files\\Python311\\python.exe -m pytest C:\\QIH\\engine\\hive\\dashboard\\tests -v
"""
import pytest
import requests

BASE = "http://127.0.0.1:8600"
TIMEOUT = 3
# The HTML pages render the whole dashboard (project table, agent roster, usage
# tiles, per-project LLM inventory) and are far heavier than the JSON probes.
# They are also the first thing touched after a QI_Dashboard restart, when no
# cache is warm. Sharing the 3s JSON budget made test_root_dashboard fail cold
# and pass warm; give the HTML its own headroom instead.
HTML_TIMEOUT = 30


def _service_up():
    for path, timeout in (("/health", TIMEOUT), ("/", HTML_TIMEOUT)):
        try:
            r = requests.get(f"{BASE}{path}", timeout=timeout)
            if r.status_code == 200:
                return True
        except requests.RequestException:
            continue
    return False


pytestmark = pytest.mark.skipif(
    not _service_up(),
    reason="QI Hive dashboard not running on 127.0.0.1:8600",
)


@pytest.fixture(scope="session", autouse=True)
def _warm_root():
    """Prime the root page before the assertions run.

    Keeps first-request cost out of the individual tests' budgets so a slow
    cold start shows up as a slow run, not a spurious failure. Errors are
    swallowed deliberately — the real test should report them, not the fixture.
    """
    try:
        requests.get(f"{BASE}/", timeout=HTML_TIMEOUT)
    except requests.RequestException:
        pass


def test_root_dashboard():
    r = requests.get(f"{BASE}/", timeout=HTML_TIMEOUT)
    assert r.status_code == 200


def test_health():
    """JSON probe: Hive /health negotiates on Accept; request JSON explicitly."""
    r = requests.get(
        f"{BASE}/health",
        headers={"Accept": "application/json"},
        timeout=TIMEOUT,
    )
    if r.status_code == 404:
        pytest.skip("/health not present")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    assert body.get("service") == "qi_hive"
    assert body.get("port") == 8600


def test_api_brain_status_readonly():
    """Read-only GET: /api/brain/status -> 200 + JSON shape."""
    r = requests.get(f"{BASE}/api/brain/status", timeout=TIMEOUT)
    if r.status_code == 404:
        pytest.skip("/api/brain/status not present")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_openapi_served():
    r = requests.get(f"{BASE}/openapi.json", timeout=TIMEOUT)
    if r.status_code == 404:
        pytest.skip("/openapi.json not served")
    assert r.status_code == 200
    assert "paths" in r.json()

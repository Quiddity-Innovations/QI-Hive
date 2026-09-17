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


# Pages whose first render after a QI_Dashboard restart pays a large one-off
# cost and is then served from a TTL cache. /health fans out sc / netstat / git
# probes across every registered project (~104s cold with 43 projects, ~0s once
# warm; health_check.HEALTH_CACHE_TTL and the 300s background refresh are what
# normally keep it warm). Timing that cold path is not what these tests are
# for, so prime it first.
COLD_PAGES = ["/", "/health", "/services", "/tasks"]
WARMUP_TIMEOUT = 240


@pytest.fixture(scope="session", autouse=True)
def _warm_root():
    """Prime the expensive pages before the assertions run.

    Keeps first-request cost out of the individual tests' budgets so a slow
    cold start shows up as a slow run, not a spurious failure. Errors are
    swallowed deliberately — the real test should report them, not the fixture.
    """
    for path in COLD_PAGES:
        try:
            requests.get(f"{BASE}{path}",
                         headers={"Accept": "text/html,application/xhtml+xml"},
                         timeout=WARMUP_TIMEOUT)
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

# ---------------------------------------------------------------------------
# Full nav-route and API coverage (added 2026-09-16, audit follow-up)
#
# The audit found tabs that had been broken for weeks without anything
# noticing, because the smoke suite only ever touched "/" and three JSON
# probes. These parametrised tests GET every tab in the left-hand nav and
# every read-only API the tabs depend on, so a route that starts 500-ing is a
# red test on the next run instead of a discovery during the next audit.
#
# Read-only GETs only: nothing here mutates state, so the suite stays safe to
# run against the live dashboard from the Tests tab.
# ---------------------------------------------------------------------------

# The 25 numbered tabs of PART 1 of ecosystem/QI_Claude_Manager_Guide.md, in
# nav order. Keep this list and the guide in step: if you add a tab, add it to
# both. /compliance is reachable from the Hive tab rather than the nav itself.
NAV_ROUTES = [
    "/", "/voice", "/launcher", "/tunnels", "/hive", "/health", "/board",
    "/tests", "/projects/status", "/services", "/ops", "/tasks", "/usage",
    "/effort", "/news", "/activity", "/dispatch", "/brain", "/mission-control",
    "/agents", "/warroom", "/logs", "/config", "/library", "/guide",
]
EXTRA_PAGES = ["/compliance"]

# Read-only JSON endpoints the tabs are built on. A tab can render an empty
# shell while its API is broken, so these are checked separately.
API_ROUTES = [
    "/api/status", "/api/health", "/api/ping",
    "/api/services", "/api/tasks", "/api/tasks/scheduled", "/api/tunnels",
    "/api/headlines", "/api/agents", "/api/agent-hr", "/api/effort",
    "/api/logs", "/api/brain/status", "/api/ops/status",
    "/api/compliance/status", "/api/compliance/recent",
    "/api/usage/today", "/api/usage/daily", "/api/usage/by_project",
    "/api/usage/by_model", "/api/usage/savings", "/api/usage/savings/today",
    "/api/usage/savings/by_model",
    "/api/activity/sessions", "/api/activity/hive_reports",
    "/api/scout/digest", "/api/theme", "/api/voice/state",
]


def test_nav_route_count():
    """The guide promises 25 tabs; keep the list from silently drifting."""
    assert len(NAV_ROUTES) == 25
    assert len(set(NAV_ROUTES)) == 25


# /health content-negotiates on Accept: it returns the Health Check page to a
# browser and a small JSON probe to anything else. Ask as a browser would, or
# the page test silently grades the JSON probe instead of the tab.
BROWSER_HEADERS = {"Accept": "text/html,application/xhtml+xml"}


@pytest.mark.parametrize("route", NAV_ROUTES + EXTRA_PAGES)
def test_nav_route_renders(route):
    """Every tab answers 200 with an HTML body."""
    r = requests.get(f"{BASE}{route}", headers=BROWSER_HEADERS, timeout=HTML_TIMEOUT)
    assert r.status_code == 200, f"{route} returned {r.status_code}"
    assert len(r.content) > 500, f"{route} returned a suspiciously small body"
    assert "<" in r.text[:2000], f"{route} did not return markup"


@pytest.mark.parametrize("route", API_ROUTES)
def test_api_route_returns_json(route):
    """Every read-only API answers 200 with parseable JSON."""
    r = requests.get(f"{BASE}{route}", timeout=HTML_TIMEOUT)
    assert r.status_code == 200, f"{route} returned {r.status_code}"
    body = r.json()
    assert isinstance(body, (dict, list)), f"{route} did not return a JSON body"


def test_api_usage_range_requires_start():
    """/api/usage/range takes a required `start`; check it works and validates.

    This is the endpoint behind clicking a bar in Daily Spend, which the audit
    found returning 'failed to load range'.
    """
    from datetime import date, timedelta
    end = date.today()
    start = end - timedelta(days=7)
    r = requests.get(
        f"{BASE}/api/usage/range",
        params={"start": start.isoformat(), "end": end.isoformat()},
        timeout=HTML_TIMEOUT,
    )
    assert r.status_code == 200
    assert isinstance(r.json(), dict)
    # Missing the required parameter must be a clean 422, not a 500.
    assert requests.get(f"{BASE}/api/usage/range", timeout=TIMEOUT).status_code == 422


def test_api_agent_hr_runs_requires_agent():
    """/api/agent-hr/runs takes a required `agent` filter."""
    r = requests.get(f"{BASE}/api/agent-hr/runs",
                     params={"agent": "claude"}, timeout=HTML_TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), (dict, list))
    assert requests.get(f"{BASE}/api/agent-hr/runs", timeout=TIMEOUT).status_code == 422

# -*- coding: utf-8 -*-
"""
Smoke tests for QI Brain API (FastAPI, port 9011).

Read-only contract checks only. WRITE endpoints (/api/log_decision,
/api/log_feature, /api/log_session, /api/agent/growth, /api/agent/heartbeat,
/api/decide_feature, /api/update_project_state, /api/supersede_decision,
/api/override_evaluation, /api/dispatch*, /api/config/*) are INTENTIONALLY
EXCLUDED because they mutate the brain DB / ChromaDB.

Run:
    C:\\Program Files\\Python311\\python.exe -m pytest C:\\QIH\\engine\\brain\\tests -v
"""
import pytest
import requests

BASE = "http://127.0.0.1:9011"
TIMEOUT = 3


def _service_up():
    try:
        r = requests.get(f"{BASE}/health", timeout=TIMEOUT)
        return r.status_code == 200
    except requests.RequestException:
        return False


pytestmark = pytest.mark.skipif(
    not _service_up(),
    reason="QI Brain not running on 127.0.0.1:9011",
)


def test_health():
    r = requests.get(f"{BASE}/health", timeout=TIMEOUT)
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    assert body.get("service") == "qi_brain"
    assert body.get("port") == 9011


def test_version():
    r = requests.get(f"{BASE}/version", timeout=TIMEOUT)
    if r.status_code == 404:
        pytest.skip("/version not present")
    assert r.status_code == 200
    body = r.json()
    assert body.get("service") == "qi_brain"
    assert "version" in body


def test_info():
    r = requests.get(f"{BASE}/info", timeout=TIMEOUT)
    if r.status_code == 404:
        pytest.skip("/info not present")
    assert r.status_code == 200
    body = r.json()
    assert body.get("service") == "qi_brain"
    assert isinstance(body.get("capabilities"), list)


def test_api_agents_readonly():
    """Read-only functional GET: /api/agents -> 200 + JSON list shape."""
    r = requests.get(f"{BASE}/api/agents", timeout=TIMEOUT)
    if r.status_code == 404:
        pytest.skip("/api/agents not present")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, dict)
    assert "agents" in body
    assert isinstance(body["agents"], list)


def test_openapi_served():
    r = requests.get(f"{BASE}/openapi.json", timeout=TIMEOUT)
    if r.status_code == 404:
        pytest.skip("/openapi.json not served")
    assert r.status_code == 200
    assert "paths" in r.json()

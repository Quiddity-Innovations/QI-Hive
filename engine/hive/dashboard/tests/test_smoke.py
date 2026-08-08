# -*- coding: utf-8 -*-
"""
Smoke tests for QI Hive Dashboard (FastAPI, port 8600).

Read-only contract checks only. No state-mutating endpoints are exercised.

Run:
    C:\\1-AI\\APPS\\PYTHON\\python.exe -m pytest C:\\QIH\\engine\\hive\\dashboard\\tests -v
"""
import pytest
import requests

BASE = "http://127.0.0.1:8600"
TIMEOUT = 3


def _service_up():
    for path in ("/health", "/"):
        try:
            r = requests.get(f"{BASE}{path}", timeout=TIMEOUT)
            if r.status_code == 200:
                return True
        except requests.RequestException:
            continue
    return False


pytestmark = pytest.mark.skipif(
    not _service_up(),
    reason="QI Hive dashboard not running on 127.0.0.1:8600",
)


def test_root_dashboard():
    r = requests.get(f"{BASE}/", timeout=TIMEOUT)
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

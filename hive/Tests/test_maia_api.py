# -*- coding: utf-8 -*-
"""
Maia API Tests — Tests for Maia's FastAPI server on port 8001.
Run: python -m pytest C:\Claude\Tests\test_maia_api.py -v

Notes:
- Maia is a production service — tests are READ-ONLY (no POST to bot endpoints).
- Tests skip gracefully if the service is offline.
"""
import pytest
import httpx

BASE = "http://localhost:8001"
TIMEOUT = httpx.Timeout(10.0, connect=3.0)


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE, timeout=TIMEOUT) as c:
        yield c


def skip_if_offline(client):
    try:
        client.get("/", timeout=httpx.Timeout(2.0))
    except (httpx.ConnectError, httpx.TimeoutException):
        pytest.skip("Maia is offline — skipping")


def test_maia_root_responds(client):
    """Maia API root must return HTTP 200."""
    skip_if_offline(client)
    r = client.get("/")
    assert r.status_code == 200


def test_maia_health_endpoint(client):
    """If Maia exposes /health or /status, it should return 200."""
    skip_if_offline(client)
    for path in ["/health", "/status", "/ping"]:
        r = client.get(path)
        if r.status_code == 200:
            return  # found a working health endpoint
    pytest.skip("Maia has no /health, /status, or /ping endpoint — add one")


def test_maia_docs_available(client):
    """FastAPI auto-docs should be accessible at /docs."""
    skip_if_offline(client)
    r = client.get("/docs")
    assert r.status_code == 200, "Maia /docs not accessible — FastAPI autodocs missing"


def test_maia_response_time(client):
    """Root endpoint should respond within 3 seconds."""
    skip_if_offline(client)
    import time
    start = time.time()
    client.get("/")
    elapsed = time.time() - start
    assert elapsed < 3.0, f"Maia root took {elapsed:.2f}s — too slow"

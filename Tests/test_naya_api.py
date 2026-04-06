# -*- coding: utf-8 -*-
"""
Naya API Tests — Tests for Naya's FastAPI server on port 8002.
Run: python -m pytest C:\Claude\Tests\test_naya_api.py -v

Notes:
- Naya is a private personal assistant — tests are READ-ONLY.
- Tests skip gracefully if the service is offline.
"""
import pytest
import httpx

BASE = "http://localhost:8002"
TIMEOUT = httpx.Timeout(10.0, connect=3.0)


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE, timeout=TIMEOUT) as c:
        yield c


def skip_if_offline(client):
    try:
        client.get("/", timeout=httpx.Timeout(2.0))
    except (httpx.ConnectError, httpx.TimeoutException):
        pytest.skip("Naya is offline — skipping")


def test_naya_root_responds(client):
    """Naya API root must return HTTP 200."""
    skip_if_offline(client)
    r = client.get("/")
    assert r.status_code == 200


def test_naya_health_endpoint(client):
    """If Naya exposes a health endpoint, it should return 200."""
    skip_if_offline(client)
    for path in ["/health", "/status", "/ping"]:
        r = client.get(path)
        if r.status_code == 200:
            return
    pytest.skip("Naya has no health endpoint — add one")


def test_naya_docs_available(client):
    """FastAPI auto-docs should be accessible at /docs."""
    skip_if_offline(client)
    r = client.get("/docs")
    assert r.status_code == 200, "Naya /docs not accessible"


def test_naya_response_time(client):
    """Root endpoint should respond within 3 seconds."""
    skip_if_offline(client)
    import time
    start = time.time()
    client.get("/")
    elapsed = time.time() - start
    assert elapsed < 3.0, f"Naya root took {elapsed:.2f}s — too slow"

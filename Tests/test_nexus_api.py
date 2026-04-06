# -*- coding: utf-8 -*-
"""
NEXUS API Tests — Tests for NEXUS multi-model synthesis server on port 8010.
Run: python -m pytest C:\Claude\Tests\test_nexus_api.py -v
"""
import pytest
import httpx

BASE = "http://localhost:8010"
TIMEOUT = httpx.Timeout(15.0, connect=3.0)  # synthesis can be slow


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE, timeout=TIMEOUT) as c:
        yield c


def skip_if_offline(client):
    try:
        client.get("/", timeout=httpx.Timeout(2.0))
    except (httpx.ConnectError, httpx.TimeoutException):
        pytest.skip("NEXUS is offline — skipping")


def test_nexus_root_responds(client):
    """NEXUS API root must return HTTP 200."""
    skip_if_offline(client)
    r = client.get("/")
    assert r.status_code == 200


def test_nexus_health_endpoint(client):
    """If NEXUS exposes a health endpoint, it should return 200."""
    skip_if_offline(client)
    for path in ["/health", "/status", "/ping"]:
        r = client.get(path)
        if r.status_code == 200:
            return
    pytest.skip("NEXUS has no health endpoint — add one")


def test_nexus_docs_available(client):
    """FastAPI auto-docs should be accessible."""
    skip_if_offline(client)
    r = client.get("/docs")
    assert r.status_code == 200, "NEXUS /docs not accessible"


def test_nexus_synthesize_endpoint_exists(client):
    """NEXUS /synthesize endpoint must exist (even if it needs auth/body)."""
    skip_if_offline(client)
    # A GET to a POST endpoint should return 405 Method Not Allowed, not 404
    r = client.get("/synthesize")
    assert r.status_code in (200, 405, 422), (
        f"/synthesize returned {r.status_code} — endpoint may not exist (404)"
    )


def test_nexus_scout_digest_endpoint_exists(client):
    """NEXUS /scout/digest endpoint must exist."""
    skip_if_offline(client)
    r = client.get("/scout/digest")
    assert r.status_code in (200, 405, 422), (
        f"/scout/digest returned {r.status_code} — endpoint may not exist (404)"
    )


def test_nexus_response_time(client):
    """Root endpoint should respond within 3 seconds."""
    skip_if_offline(client)
    import time
    start = time.time()
    client.get("/")
    elapsed = time.time() - start
    assert elapsed < 3.0, f"NEXUS root took {elapsed:.2f}s — too slow"

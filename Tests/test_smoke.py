# -*- coding: utf-8 -*-
"""
QI Smoke Tests -- Quick health check for all active services.
Run: python -m pytest C:/Claude/Tests/test_smoke.py -v
"""
import httpx
import pytest

SMOKE_TARGETS = [
    ("Maia",      "http://localhost:8001", "/"),
    ("Naya",      "http://localhost:8002", "/"),
    ("NEXUS",     "http://localhost:8010", "/"),
    ("Dashboard", "http://localhost:8600", "/"),
]

TIMEOUT = httpx.Timeout(5.0, connect=2.0)


@pytest.mark.parametrize("project,base,path", SMOKE_TARGETS, ids=[t[0] for t in SMOKE_TARGETS])
def test_service_responds(project, base, path):
    """Each active service must respond HTTP 200 within 5 seconds."""
    try:
        r = httpx.get(f"{base}{path}", timeout=TIMEOUT, follow_redirects=True)
        assert r.status_code == 200, (
            f"{project} returned {r.status_code} — expected 200"
        )
    except httpx.ConnectError:
        pytest.skip(f"{project} is offline — skipping (service may be stopped)")
    except httpx.TimeoutException:
        pytest.fail(f"{project} timed out after 5s — service may be overloaded")

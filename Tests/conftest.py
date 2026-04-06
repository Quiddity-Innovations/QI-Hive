# -*- coding: utf-8 -*-
"""
QI Test Suite — Shared Fixtures
Provides httpx clients pre-configured for each project's base URL.
"""
import pytest
import httpx

# Base URLs for all active QI projects
BASES = {
    "maia":      "http://localhost:8001",
    "naya":      "http://localhost:8002",
    "nexus":     "http://localhost:8010",
    "dashboard": "http://localhost:8600",
}

TIMEOUT = httpx.Timeout(10.0, connect=3.0)


@pytest.fixture(scope="session")
def maia_client():
    with httpx.Client(base_url=BASES["maia"], timeout=TIMEOUT) as c:
        yield c


@pytest.fixture(scope="session")
def naya_client():
    with httpx.Client(base_url=BASES["naya"], timeout=TIMEOUT) as c:
        yield c


@pytest.fixture(scope="session")
def nexus_client():
    with httpx.Client(base_url=BASES["nexus"], timeout=TIMEOUT) as c:
        yield c


@pytest.fixture(scope="session")
def dashboard_client():
    with httpx.Client(base_url=BASES["dashboard"], timeout=TIMEOUT) as c:
        yield c

# -*- coding: utf-8 -*-
"""
QI Load Tests — Locust performance tests for key QI endpoints.

Usage examples:
  # Dashboard load test (10 users, 30s, ramp 2/s):
  locust -f C:\Claude\Tests\load\locustfile.py --headless -u 10 -r 2 -t 30s --host http://localhost:8600

  # Maia load test:
  locust -f C:\Claude\Tests\load\locustfile.py MaiaLoadTest --headless -u 5 -r 1 -t 30s --host http://localhost:8001

  # Interactive UI mode (opens browser at http://localhost:8089):
  locust -f C:\Claude\Tests\load\locustfile.py --host http://localhost:8600
"""
from locust import HttpUser, task, between


class DashboardLoadTest(HttpUser):
    """Load test the Claude Manager dashboard."""
    wait_time = between(1, 3)
    host = "http://localhost:8600"

    @task(3)
    def home_page(self):
        self.client.get("/")

    @task(2)
    def board_page(self):
        self.client.get("/board")

    @task(2)
    def api_tasks(self):
        self.client.get("/api/tasks")

    @task(1)
    def api_status(self):
        self.client.get("/api/status")

    @task(1)
    def guide_page(self):
        self.client.get("/guide")


class MaiaLoadTest(HttpUser):
    """Load test Maia's API server."""
    wait_time = between(1, 5)
    host = "http://localhost:8001"

    @task
    def root(self):
        self.client.get("/")

    @task
    def docs(self):
        self.client.get("/docs")


class NayaLoadTest(HttpUser):
    """Load test Naya's API server."""
    wait_time = between(1, 5)
    host = "http://localhost:8002"

    @task
    def root(self):
        self.client.get("/")


class NEXUSLoadTest(HttpUser):
    """Load test NEXUS API server."""
    wait_time = between(2, 5)
    host = "http://localhost:8010"

    @task
    def root(self):
        self.client.get("/")

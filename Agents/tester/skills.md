# Tester Agent — Skills

## Trigger Phrases (when to invoke the Tester)
- "Run tests"
- "Test everything"
- "Check if X is working"
- "Run the test suite"
- "Is Maia / Naya / NEXUS up and responding?"
- "Load test port 8001"
- "Did the last build break anything?"
- "Run smoke tests"
- "Run full regression"

---

## Skill: API Smoke Test
**Trigger:** "Run smoke tests" / "Quick check"
**Tool:** pytest + httpx
**What it does:**
- Hits the health/root endpoint of every active project
- Asserts HTTP 200 in < 2 seconds
- Reports pass/fail per project
**Test file:** `C:\Claude\Tests\test_smoke.py`
**Run:** `python -m pytest C:\Claude\Tests\test_smoke.py -v`

---

## Skill: Full API Test Suite
**Trigger:** "Run full tests" / "Full regression"
**Tool:** pytest + httpx
**What it does:**
- Tests all registered API endpoints for each project
- Checks status codes, response schemas, error handling
- Saves results to `C:\Claude\Tests\results\api_YYYYMMDD_HHMMSS.json`
**Test files:**
- `C:\Claude\Tests\test_maia_api.py`
- `C:\Claude\Tests\test_naya_api.py`
- `C:\Claude\Tests\test_nexus_api.py`
- `C:\Claude\Tests\test_dashboard_api.py`
**Run:** `python -m pytest C:\Claude\Tests\ -v --ignore=C:\Claude\Tests\load\ --json-report --json-report-file=C:\Claude\Tests\results\latest.json`

---

## Skill: UI Test
**Trigger:** "Test the dashboard UI" / "Run Playwright tests"
**Tool:** Playwright (Python, Chromium headless)
**What it does:**
- Opens dashboard, health page, board page
- Verifies key elements render (cards, columns, sidebar)
- Checks drag-and-drop responds (Playwright click/drag)
- Screenshots on failure
**Test file:** `C:\Claude\Tests\test_dashboard_ui.py`
**Run:** `python -m pytest C:\Claude\Tests\test_dashboard_ui.py -v`

---

## Skill: Load Test
**Trigger:** "Load test" / "Stress test port XXXX"
**Tool:** Locust
**What it does:**
- Spawns N simulated users hitting target endpoints
- Reports RPS, response time p50/p95/p99, failure %
- Default: 10 users, 30s duration, ramp 2/s
**Test file:** `C:\Claude\Tests\load\locustfile.py`
**Run:** `locust -f C:\Claude\Tests\load\locustfile.py --headless -u 10 -r 2 -t 30s --host http://localhost:8001`

---

## Skill: Write Test Report
**Trigger:** After any test run
**What it does:**
- Reads latest results JSON
- Creates tasks on the kanban board for every FAILED test
- Prints summary table: project | endpoint | status | latency
- Marks task priority: critical if prod service, high if dev service

---

## Skill: Register New Test
**Trigger:** "Add a test for X endpoint"
**What it does:**
- Appends a new test function to the appropriate test file
- Follows the project's test pattern (pytest function, httpx client)
- Documents what the test checks in a docstring

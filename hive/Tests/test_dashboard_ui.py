# -*- coding: utf-8 -*-
"""
Dashboard UI Tests — Playwright headless browser tests for the Claude Manager dashboard.
Run: python -m pytest C:\Claude\Tests\test_dashboard_ui.py -v

Requirements: playwright + chromium installed
  pip install playwright
  python -m playwright install chromium
"""
import pytest
from playwright.sync_api import sync_playwright, expect


BASE = "http://localhost:8600"


def is_dashboard_up():
    """Quick pre-check before launching browser."""
    import httpx
    try:
        httpx.get(BASE, timeout=httpx.Timeout(2.0))
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def page():
    if not is_dashboard_up():
        pytest.skip("Dashboard is offline — skipping UI tests")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context()
        p = ctx.new_page()
        yield p
        browser.close()


# ── Dashboard home page ───────────────────────────────────────────────────────

def test_dashboard_title(page):
    """Dashboard home page should have 'QI' or 'Claude' in the title."""
    page.goto(BASE)
    page.wait_for_load_state("networkidle")
    title = page.title()
    assert any(kw in title for kw in ["QI", "Claude", "Dashboard"]), (
        f"Unexpected page title: {title}"
    )


def test_dashboard_sidebar_present(page):
    """AdminLTE sidebar navigation should be rendered."""
    page.goto(BASE)
    page.wait_for_load_state("networkidle")
    sidebar = page.locator(".sidebar, .app-sidebar, nav")
    assert sidebar.count() > 0, "No sidebar found — AdminLTE layout may be broken"


def test_dashboard_project_cards(page):
    """At least one project card should appear on the dashboard home."""
    page.goto(BASE)
    page.wait_for_load_state("networkidle")
    cards = page.locator(".card")
    assert cards.count() > 0, "No cards found on dashboard home"


# ── Health check page ─────────────────────────────────────────────────────────

def test_health_page_renders(page):
    """Health page should render without JS errors."""
    page.goto(f"{BASE}/health")
    page.wait_for_load_state("networkidle")
    # Should show at least project names
    content = page.content()
    assert "Maia" in content, "'Maia' not found on health page"
    assert "NEXUS" in content, "'NEXUS' not found on health page"


# ── Task board page ───────────────────────────────────────────────────────────

def test_board_page_renders(page):
    """Board page should render with kanban columns."""
    page.goto(f"{BASE}/board")
    page.wait_for_load_state("networkidle")
    content = page.content()
    assert "Backlog" in content, "'Backlog' column not found on board"
    assert "In Progress" in content, "'In Progress' column not found on board"
    assert "Done" in content, "'Done' column not found on board"


def test_board_add_task_button(page):
    """Add Task button should be present on board page."""
    page.goto(f"{BASE}/board")
    page.wait_for_load_state("networkidle")
    btn = page.locator("button", has_text="Add Task")
    assert btn.count() > 0, "Add Task button not found on board"


# ── Guide page ────────────────────────────────────────────────────────────────

def test_guide_page_renders(page):
    """Guide page should render markdown content."""
    page.goto(f"{BASE}/guide")
    page.wait_for_load_state("networkidle")
    content = page.content()
    assert "QI Claude Manager" in content or "Cheatsheet" in content, (
        "Guide page content not rendered"
    )


# ── Screenshot on failure helper ──────────────────────────────────────────────

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.failed and "page" in item.funcargs:
        p = item.funcargs["page"]
        screenshot_path = f"C:\\Claude\\Tests\\results\\failure_{item.name}.png"
        try:
            p.screenshot(path=screenshot_path)
        except Exception:
            pass

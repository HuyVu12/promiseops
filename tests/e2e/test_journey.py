"""Browser end-to-end test of the core journey (SE-1042). Skipped unless Playwright browsers are installed.

Run: python -m pytest tests/e2e
"""

import socket
import threading
import time

import pytest

playwright = pytest.importorskip("playwright.sync_api")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def base_url(tmp_path_factory):
    import uvicorn

    from promiseops.web import app as main
    from promiseops.web import deps

    deps.settings.db_path = tmp_path_factory.mktemp("e2e") / "e2e.db"
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture
def page(base_url):
    with playwright.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as exc:  # browsers not installed
            pytest.skip(f"Chromium unavailable: {exc}")
        pg = browser.new_page(viewport={"width": 1440, "height": 900})
        errors = []
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.goto(base_url + "/app")
        yield pg
        assert errors == []
        browser.close()


def go(page, selector):
    with page.expect_navigation():
        page.click(selector)


def test_core_journey_saves_the_promise(page, base_url):
    assert page.text_content("[data-testid=clock]") == "09:00"
    go(page, "[data-testid=adv-30]")
    assert page.is_visible("[data-testid=row-SE-1042]")
    assert page.is_visible("[data-testid=row-SE-1051]")

    go(page, "[data-testid=row-SE-1042] a.order-link")
    go(page, "[data-testid=ack]")
    # Coordinator cannot expedite: the option is disabled for this role.
    assert page.is_disabled("[data-testid=res-expedited]")
    page.fill("[data-testid=esc-note]", "Not picked, need a priority pick")
    go(page, "[data-testid=escalate]")
    assert "Erik Berg" in page.text_content("[data-testid=owner]")

    with page.expect_navigation():
        page.select_option("[data-testid=role]", "shift_lead")
    page.check("[data-testid=res-expedited]")
    # Choosing the expedite makes the intervention cost required.
    assert page.get_attribute("[data-testid=resolve-cost]", "required") is not None
    page.fill("[data-testid=resolve-note]", "Moved a picker, priority pick")
    page.fill("[data-testid=resolve-cost]", "40")
    go(page, "[data-testid=resolve]")
    assert "Expedited by shift lead" in page.text_content("[data-testid=state]")

    page.goto(base_url + "/orders")
    go(page, "[data-testid=adv-300]")
    go(page, "[data-testid=adv-60]")
    assert "on time" in page.text_content("[data-testid=order-SE-1042]")
    assert "late" in page.text_content("[data-testid=order-SE-1077]")

    page.goto(base_url + "/kpi")
    assert page.text_content("[data-testid=kpi-prevented] .stat-value").strip() == "1"

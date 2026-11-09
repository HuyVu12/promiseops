"""Captures the SE-1042 journey from a running PromiseOps for the User Journey PDF and the video slides.

Run against a separate server so nobody's session is disturbed:
  PROMISEOPS_DB=%TEMP%/journey.db python -m uvicorn --app-dir src promiseops.web.app:app --port 8766
  python scripts/capture_journey.py http://127.0.0.1:8766

The steps are the demo script in the README, so the screenshots, the PDF and the video tell one story.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8766"
OUT = Path(__file__).resolve().parents[1] / "docs" / "journey" / "shots"
OUT.mkdir(parents=True, exist_ok=True)

# The same notes the README and the video script use.
NOTES = {
    "esc": "Not picked: picker on break. Need a priority pick to make the 10:00 route.",
    "exp": "Moved a picker from aisle 3; priority pick, loaded on the 10:30 shuttle (last viable 11:30).",
    "cost": "10",
    "fa": "Picker Jonas: tote packed 09:20, handheld was offline. Scanner ticket raised.",
    "cs": "No vehicle until 11:50. Customer service called the site manager with a 14:35 ETA.",
}


def main() -> None:
    facts: dict[str, str] = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
        pg.on("dialog", lambda d: d.accept())

        def go(sel: str) -> None:
            with pg.expect_navigation():
                pg.click(sel)

        def as_role(role: str) -> None:
            with pg.expect_navigation():
                pg.select_option("[data-testid=role]", role)

        def snap(name: str, clip: dict | None = None, selector: str | None = None) -> None:
            """Screenshot without the demo bar and the flash message, then put them back."""
            pg.evaluate("""() => { const s = document.createElement('style'); s.id = 'snap';
                s.textContent = '.demo{display:none!important}.banner.ok{display:none!important}';
                document.head.appendChild(s); }""")
            if selector:
                pg.locator(selector).screenshot(path=OUT / name)
            else:
                pg.screenshot(path=OUT / name, clip=clip)
            pg.evaluate("() => document.getElementById('snap').remove()")

        def open_row(order_id: str) -> None:
            pg.goto(BASE + "/app")
            go(f"[data-testid=row-{order_id}] a.order-link")

        pg.goto(BASE + "/app?lang=en")
        as_role("coordinator")
        go("[data-testid=reset]")
        go("[data-testid=adv-30]")  # 09:30
        snap("1-queue-0930.png", {"x": 284, "y": 76, "width": 1124, "height": 250})

        # SE-1042: take ownership, escalate (coordinator), expedite with cost (shift lead).
        open_row("SE-1042")
        go("[data-testid=ack]")
        snap("2-detail-own.png", {"x": 284, "y": 60, "width": 1124, "height": 420})
        pg.fill("[data-testid=esc-note]", NOTES["esc"])
        go("[data-testid=escalate]")
        as_role("shift_lead")
        pg.check("[data-testid=res-expedited]")
        pg.fill("[data-testid=resolve-note]", NOTES["exp"])
        pg.fill("[data-testid=resolve-cost]", NOTES["cost"])
        snap("3-shiftlead-decides.png", selector="[data-testid=actions]")
        go("[data-testid=resolve]")
        snap("4-recorded.png", selector="section.card:has([data-testid=log])")
        facts["expedite_at"] = pg.text_content("[data-testid=clock]")
        as_role("coordinator")

        # SE-1051: false alarm with evidence.
        open_row("SE-1051")
        go("[data-testid=ack]")
        pg.check("[data-testid=res-false_alarm]")
        pg.fill("[data-testid=resolve-note]", NOTES["fa"])
        go("[data-testid=resolve]")

        # Feed outage: alerts pause, data task opens.
        pg.goto(BASE + "/app")
        go("[data-testid=feed-pause]")
        go("[data-testid=adv-30]")
        go("[data-testid=adv-15]")
        snap("5-stale-feed.png", {"x": 0, "y": 0, "width": 1440, "height": 560})
        go("[data-testid=feed-resume]")
        go("[data-testid=adv-5]")
        facts["after_resume"] = pg.text_content("[data-testid=clock]")

        # SE-1077: a real dispatch problem found on fresh data; handed to customer service.
        open_row("SE-1077")
        go("[data-testid=ack]")
        pg.check("[data-testid=res-customer_notified]")
        pg.fill("[data-testid=resolve-note]", NOTES["cs"])
        go("[data-testid=resolve]")

        # Afternoon: deliveries against the promise.
        pg.goto(BASE + "/orders")
        go("[data-testid=adv-300]")
        facts["measure_at"] = pg.text_content("[data-testid=clock]")
        snap("6-orders-delivered.png", {"x": 284, "y": 76, "width": 1124, "height": 470})
        pg.goto(BASE + "/kpi")
        snap("7-outcomes.png", {"x": 284, "y": 90, "width": 1124, "height": 300})
        facts["ontime_with"] = pg.text_content("[data-testid=kpi-ontime] .stat-value").strip()
        facts["prevented"] = pg.text_content("[data-testid=kpi-prevented] .stat-value").strip()
        facts["owned"] = pg.text_content("[data-testid=kpi-ack] .stat-value").strip()
        facts["actionable"] = pg.text_content("[data-testid=kpi-actionable] .stat-value").strip()

        # Counterfactual: the same morning when nobody acts.
        pg.goto(BASE + "/app")
        go("[data-testid=reset]")
        go("[data-testid=adv-30]")
        go("[data-testid=adv-300]")
        go("[data-testid=adv-60]")
        pg.goto(BASE + "/kpi")
        snap("8-outcomes-no-action.png", {"x": 284, "y": 90, "width": 1124, "height": 150})
        facts["ontime_without"] = pg.text_content("[data-testid=kpi-ontime] .stat-value").strip()
        pg.goto(BASE + "/app")
        go("[data-testid=reset]")
        b.close()
    (OUT / "facts.json").write_text(json.dumps(facts, indent=2), encoding="utf8")
    print(json.dumps(facts, indent=2))


if __name__ == "__main__":
    main()

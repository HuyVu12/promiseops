"""Captures the Round 3 MVP adjustments (shadow pilot, handoff by case reference) for the pitch deck.

Run against a separate server in shadow mode so nobody's session is disturbed:
  set PROMISEOPS_DB=%TEMP%/round3.db & set PROMISEOPS_SHADOW=1
  python -m uvicorn --app-dir src promiseops.web.app:app --port 8767
  python scripts/capture_round3.py http://127.0.0.1:8767

Same morning as the Round 2 journey: SE-1042 is decided by the shift lead, SE-1077 is handed to customer
service. Here every decision is recorded in shadow mode, so the Outcomes page claims no prevented lateness.
Writes docs/continuity/shots/*.png and facts.json (the numbers the deck quotes).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8767"
OUT = Path(__file__).resolve().parents[1] / "docs" / "continuity" / "shots"
OUT.mkdir(parents=True, exist_ok=True)

NOTES = {
    "esc": "Not picked: picker on break. Need a priority pick to make the 10:00 route.",
    "exp": "Would move a picker from aisle 3 for a priority pick. Floor lead decides through the usual call.",
    "cost": "10",
    "fa": "Picker Jonas: tote packed 09:20, handheld was offline. Scanner ticket raised.",
    "cs": "No vehicle until 11:50. Customer service will call the site manager with a 14:35 ETA.",
    "ref": "CS-48213",
}
HIDE = ".demo{display:none!important}.banner.ok{display:none!important}"


def box(pg: Page, selector: str) -> dict:
    b = pg.locator(selector).first.bounding_box()
    if b is None:
        raise SystemExit(f"Not on screen: {selector}")
    return b


def snap(pg: Page, name: str, clip: dict, extra_css: str = "") -> None:
    pg.evaluate("""css => { const s = document.createElement('style'); s.id = 'snap'; s.textContent = css;
        document.head.appendChild(s); }""", HIDE + extra_css)
    pg.screenshot(path=OUT / f"{name}.png", clip={k: round(v, 1) for k, v in clip.items()})
    pg.evaluate("() => document.getElementById('snap').remove()")


def around(*boxes: dict, pad: int = 10) -> dict:
    x1 = min(b["x"] for b in boxes) - pad
    y1 = min(b["y"] for b in boxes) - pad
    x2 = max(b["x"] + b["width"] for b in boxes) + pad
    y2 = max(b["y"] + b["height"] for b in boxes) + pad
    return {"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1}


def main() -> None:
    facts: dict[str, object] = {}
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

        def open_row(order_id: str) -> None:
            pg.goto(BASE + "/app")
            go(f"[data-testid=row-{order_id}] a.order-link")

        health = pg.request.get(BASE + "/api/health").json()
        if not health.get("shadow"):
            raise SystemExit("Start the server with PROMISEOPS_SHADOW=1")

        pg.goto(BASE + "/app?lang=en")
        as_role("coordinator")
        go("[data-testid=reset]")
        go("[data-testid=adv-30]")  # 09:30: SE-1042 and SE-1051 missed their pick
        # Narrow the banner so it wraps: on a slide, the text then reads at a projector-friendly size.
        pg.evaluate("() => { document.querySelector('[data-testid=shadow-banner]').style.width = '760px'; }")
        snap(pg, "1-banner", around(box(pg, "[data-testid=shadow-banner]"), pad=6))

        # SE-1042: coordinator owns and escalates; the shift lead records what they would do.
        open_row("SE-1042")
        go("[data-testid=ack]")
        pg.fill("[data-testid=esc-note]", NOTES["esc"])
        go("[data-testid=escalate]")
        as_role("shift_lead")
        pg.check("[data-testid=res-expedited]")
        pg.fill("[data-testid=resolve-note]", NOTES["exp"])
        pg.fill("[data-testid=resolve-cost]", NOTES["cost"])
        go("[data-testid=resolve]")
        as_role("coordinator")

        # SE-1051: a real false alarm.
        open_row("SE-1051")
        go("[data-testid=ack]")
        pg.check("[data-testid=res-false_alarm]")
        pg.fill("[data-testid=resolve-note]", NOTES["fa"])
        go("[data-testid=resolve]")

        # SE-1077: picked, no vehicle; handed to customer service by reference only.
        pg.goto(BASE + "/app")
        go("[data-testid=adv-30]")
        open_row("SE-1077")
        go("[data-testid=ack]")
        pg.check("[data-testid=res-customer_notified]")
        pg.fill("[data-testid=resolve-note]", NOTES["cs"])
        pg.fill("[data-testid=resolve-case-ref]", NOTES["ref"])
        pg.locator("[data-testid=actions]").scroll_into_view_if_needed()
        snap(pg, "2-case-ref", around(box(pg, "[data-testid=case-ref-field]"), pad=8))
        go("[data-testid=resolve]")
        pg.locator("[data-testid=log]").scroll_into_view_if_needed()
        # Only the last three log lines: the handoff, its case reference and the shadow mark.
        items = pg.locator("[data-testid=log] > li")
        n = items.count()
        card = box(pg, "section.card:has([data-testid=log])")
        first, last = items.nth(n - 3).bounding_box(), items.nth(n - 1).bounding_box()
        snap(pg, "3-log-shadow", {"x": card["x"] + 4, "y": first["y"] - 6, "width": card["width"] - 8,
                                  "height": last["y"] + last["height"] + 6 - (first["y"] - 6)})

        # Afternoon: outcomes against the original promise, nothing claimed for shadow decisions.
        pg.goto(BASE + "/orders")
        go("[data-testid=adv-300]")
        pg.goto(BASE + "/kpi")
        snap(pg, "4-prevented", around(box(pg, "[data-testid=kpi-prevented]"), pad=2))

        k = pg.request.get(BASE + "/api/outcomes").json()["rows"]
        facts["shadow_rows"] = sum(1 for r in k if r["shadow"])
        facts["prevented_text"] = pg.text_content("[data-testid=kpi-prevented] .stat-sub")
        facts["ontime"] = pg.text_content("[data-testid=kpi-ontime] .stat-value")
        b.close()
    (OUT / "facts.json").write_text(json.dumps(facts, indent=2), encoding="utf8")
    print(json.dumps(facts, indent=2))


if __name__ == "__main__":
    main()

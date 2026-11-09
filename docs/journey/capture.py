"""Captures the SE-1042 journey from a running PromiseOps (default http://127.0.0.1:8766) for the User Journey PDF."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8766"
OUT = Path(__file__).resolve().parent / "shots"
OUT.mkdir(exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 860}, device_scale_factor=1.5)
    pg.on("dialog", lambda d: d.accept())
    def go(sel):
        with pg.expect_navigation():
            pg.click(sel)
    def shot(name, clip=None):
        pg.screenshot(path=OUT / f"{name}.png", clip=clip)
    pg.goto(BASE + "/app?lang=en")
    go("[data-testid=reset]")
    go("[data-testid=adv-30]")                                   # 09:30
    shot("1-queue-0930", {"x": 280, "y": 20, "width": 640, "height": 426})
    go("[data-testid=row-SE-1042] a.order-link")
    shot("2-detail-open", {"x": 284, "y": 60, "width": 660, "height": 440})
    go("[data-testid=ack]")
    pg.fill("[data-testid=esc-note]", "Not picked: picker on break. Need a priority pick to make the 10:00 route.")
    go("[data-testid=escalate]")
    with pg.expect_navigation():
        pg.select_option("[data-testid=role]", "shift_lead")
    pg.check("[data-testid=res-expedited]")
    pg.fill("[data-testid=resolve-note]", "Moved a picker from aisle 3; priority pick for the 10:30 shuttle.")
    shot("3-shiftlead-decides", {"x": 1048, "y": 380, "width": 392, "height": 262})
    go("[data-testid=resolve]")
    pg.add_style_tag(content=".demo{display:none!important}")
    pg.locator("section.card:has([data-testid=log])").screenshot(path=OUT / "4-recorded.png")
    with pg.expect_navigation():
        pg.select_option("[data-testid=role]", "coordinator")
    pg.goto(BASE + "/orders?lang=en")
    go("[data-testid=adv-300]")                                  # 14:30
    shot("5-orders-delivered", {"x": 290, "y": 270, "width": 700, "height": 466})
    pg.goto(BASE + "/kpi?lang=en")
    shot("6-outcomes", {"x": 284, "y": 90, "width": 660, "height": 440})
    b.close()
print("ok")

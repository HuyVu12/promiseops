"""Captures the SE-1042 journey from a running PromiseOps for the User Journey PDF and the video slides.

Run against a separate server so nobody's session is disturbed:
  PROMISEOPS_DB=%TEMP%/journey.db python -m uvicorn --app-dir src promiseops.web.app:app --port 8766
  python scripts/capture_journey.py http://127.0.0.1:8766

The steps are the demo script in the README, so the screenshots, the PDF and the video tell one story.
Every clip is computed from the elements on screen and fitted to the aspect ratio of its frame in the
storyboard (FRAME_RATIOS), so the PDF shows each screenshot edge to edge, without white side bars.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8766"
OUT = Path(__file__).resolve().parents[1] / "docs" / "journey" / "shots"
OUT.mkdir(parents=True, exist_ok=True)

# Width / height of each storyboard frame's picture (build_user_journey.py uses the same numbers).
FRAME_W = 518
ROW_H = {1: 176, 2: 190, 3: 176}
FRAME_RATIOS = {name: FRAME_W / ROW_H[row] for name, row in {
    "1-queue-0930": 1, "2-detail-own": 1, "3-shiftlead-decides": 2, "4-recorded": 2,
    "6-orders-delivered": 3, "7-outcomes": 3}.items()}
PAGE_LEFT, PAGE_RIGHT = 284, 1408  # the content column at a 1440 px viewport

# The same notes the README and the video script use.
NOTES = {
    "esc": "Not picked: picker on break. Need a priority pick to make the 10:00 route.",
    "exp": "Moved a picker from aisle 3; priority pick, loaded on the 10:30 shuttle (last viable 11:30).",
    "cost": "10",
    "fa": "Picker Jonas: tote packed 09:20, handheld was offline. Scanner ticket raised.",
    "cs": "No vehicle until 11:50. Customer service called the site manager with a 14:35 ETA.",
}

HIDE = (".demo{display:none!important}.banner.ok{display:none!important}"
        ".board>.thead{box-shadow:none!important}")


def fit(x: float, y: float, w: float, h: float, ratio: float, anchor: str = "left") -> dict:
    """Clip around a content box with exactly the frame's aspect ratio, without cutting the box if possible."""
    if w / h > ratio:  # content is wide: keep its height, trim the far side
        nw = h * ratio
        return {"x": x + (w - nw if anchor == "right" else 0), "y": y, "width": nw, "height": h}
    nw = h * ratio     # content is tall: widen inside the page column, else trim the bottom
    if nw <= PAGE_RIGHT - PAGE_LEFT:
        if anchor == "right":
            x2 = min(PAGE_RIGHT, x + w)
            x1 = max(PAGE_LEFT, x2 - nw)
        else:
            x1 = max(PAGE_LEFT, min(x, PAGE_RIGHT - nw))
        return {"x": x1, "y": y, "width": nw, "height": h}
    return {"x": PAGE_LEFT, "y": y, "width": PAGE_RIGHT - PAGE_LEFT, "height": (PAGE_RIGHT - PAGE_LEFT) / ratio}


def box(pg: Page, selector: str) -> dict:
    b = pg.locator(selector).first.bounding_box()
    if b is None:
        raise SystemExit(f"Not on screen: {selector}")
    return b


def snap(pg: Page, name: str, clip: dict, extra_css: str = "") -> None:
    """Screenshot without the demo bar and the flash message, then put the page back."""
    pg.evaluate("""css => { const s = document.createElement('style'); s.id = 'snap'; s.textContent = css;
        document.head.appendChild(s); }""", HIDE + extra_css)
    pg.screenshot(path=OUT / f"{name}.png", clip={k: round(v, 1) for k, v in clip.items()})
    pg.evaluate("() => document.getElementById('snap').remove()")


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

        def open_row(order_id: str) -> None:
            pg.goto(BASE + "/app")
            go(f"[data-testid=row-{order_id}] a.order-link")

        def hide_flash() -> None:
            pg.evaluate("() => document.querySelectorAll('.banner.ok').forEach(e => e.remove())")

        pg.goto(BASE + "/app?lang=en")
        as_role("coordinator")
        go("[data-testid=reset]")
        go("[data-testid=adv-30]")  # 09:30
        hide_flash()
        top = box(pg, ".legend.compact")["y"]
        snap(pg, "1-queue-0930", fit(PAGE_LEFT, top, PAGE_RIGHT - PAGE_LEFT, 380, FRAME_RATIOS["1-queue-0930"]))

        # SE-1042: take ownership, escalate (coordinator), expedite with cost (shift lead).
        open_row("SE-1042")
        go("[data-testid=ack]")
        hide_flash()
        head, course = box(pg, ".page-head"), box(pg, "section.card:has(.course-big)")
        snap(pg, "2-detail-own", fit(PAGE_LEFT, head["y"] - 4, PAGE_RIGHT - PAGE_LEFT,
                                     course["y"] + course["height"] + 6 - (head["y"] - 4), FRAME_RATIOS["2-detail-own"]))
        pg.fill("[data-testid=esc-note]", NOTES["esc"])
        go("[data-testid=escalate]")
        as_role("shift_lead")
        pg.check("[data-testid=res-expedited]")
        pg.fill("[data-testid=resolve-note]", NOTES["exp"])
        pg.fill("[data-testid=resolve-cost]", NOTES["cost"])
        hide_flash()
        # The decision form, widened to the left over the page until its shape matches the frame.
        act_sel = "[data-testid=actions]"
        pg.locator(act_sel).scroll_into_view_if_needed()

        def form_box() -> dict:
            form, cost = box(pg, "[data-testid=resolve-form] fieldset"), box(pg, "[data-testid=resolve-cost]")
            card = box(pg, act_sel)
            return {"x": card["x"], "y": form["y"] - 10, "width": card["width"],
                    "height": cost["y"] + cost["height"] + 14 - (form["y"] - 10)}

        best = None
        for width in range(360, 1125, 12):
            pg.evaluate("""([sel, w]) => { const c = document.querySelector(sel); const base = c.parentElement.offsetWidth;
                c.style.width = w + 'px'; c.style.marginLeft = (base - w) + 'px'; c.style.position = 'relative';
                c.style.zIndex = 30; }""", [act_sel, width])
            fb = form_box()
            score = abs(fb["width"] / fb["height"] - FRAME_RATIOS["3-shiftlead-decides"])
            if best is None or score < best[0]:
                best = (score, width)
        pg.evaluate("""([sel, w]) => { const c = document.querySelector(sel); const base = c.parentElement.offsetWidth;
            c.style.width = w + 'px'; c.style.marginLeft = (base - w) + 'px'; }""", [act_sel, best[1]])
        fb = form_box()
        snap(pg, "3-shiftlead-decides", fit(fb["x"], fb["y"], fb["width"], fb["height"],
                                            FRAME_RATIOS["3-shiftlead-decides"], anchor="right"),
             ".cost-field .sub{visibility:hidden}")
        go("[data-testid=resolve]")
        hide_flash()
        # The activity log, widened until its shape matches the frame, so its text is large in the PDF.
        log_sel = "section.card:has([data-testid=log])"
        best = None
        for width in range(700, 1125, 12):
            pg.evaluate("""([sel, w]) => { const c = document.querySelector(sel); c.style.width = w + 'px';
                c.style.position = 'relative'; c.style.zIndex = 30; }""", [log_sel, width])
            lb = box(pg, log_sel)
            score = abs(lb["width"] / lb["height"] - FRAME_RATIOS["4-recorded"])
            if best is None or score < best[0]:
                best = (score, width)
        pg.evaluate("([sel, w]) => { document.querySelector(sel).style.width = w + 'px'; }", [log_sel, best[1]])
        lb = box(pg, log_sel)
        snap(pg, "4-recorded", fit(lb["x"], lb["y"], lb["width"], lb["height"], FRAME_RATIOS["4-recorded"]),
             ".col-side{visibility:hidden}")
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
        snap(pg, "5-stale-feed", {"x": 0, "y": 0, "width": 1440, "height": 560})
        go("[data-testid=feed-resume]")
        go("[data-testid=adv-5]")
        facts["after_resume"] = pg.text_content("[data-testid=clock]")

        # SE-1077: a real dispatch problem found on fresh data; handed to customer service.
        open_row("SE-1077")
        go("[data-testid=ack]")
        pg.check("[data-testid=res-customer_notified]")
        pg.fill("[data-testid=resolve-note]", NOTES["cs"])
        go("[data-testid=resolve]")

        # Afternoon: deliveries against the promise. Five rows from SE-1042, under the sticky axis.
        pg.goto(BASE + "/orders")
        go("[data-testid=adv-300]")
        facts["measure_at"] = pg.text_content("[data-testid=clock]")
        pg.evaluate("""() => { const r = document.querySelector('[data-testid=order-SE-1042]');
            const head = document.querySelector('.board > .thead');
            window.scrollTo(0, r.getBoundingClientRect().top + window.scrollY - head.offsetHeight); }""")
        pg.wait_for_timeout(200)
        thead = box(pg, ".board > .thead")
        snap(pg, "6-orders-delivered", fit(PAGE_LEFT, thead["y"], PAGE_RIGHT - PAGE_LEFT, 380, FRAME_RATIOS["6-orders-delivered"]))

        pg.goto(BASE + "/kpi")
        hide_flash()
        tiles = box(pg, ".stats")
        row3 = box(pg, "[data-testid=kpi-scorecard] tbody tr:nth-child(3)")
        # Full width (both cards keep their right edge); the height follows the frame and ends just under
        # the third scorecard row, so no line of text is cut in half.
        width = PAGE_RIGHT - PAGE_LEFT
        height = max(row3["y"] + row3["height"] + 4 - (tiles["y"] - 2), width / FRAME_RATIOS["7-outcomes"])
        snap(pg, "7-outcomes", fit(PAGE_LEFT, tiles["y"] - 2, width, height, FRAME_RATIOS["7-outcomes"]))
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
        tiles = box(pg, ".stats")
        snap(pg, "8-outcomes-no-action", {"x": tiles["x"], "y": tiles["y"], "width": tiles["width"], "height": tiles["height"]})
        facts["ontime_without"] = pg.text_content("[data-testid=kpi-ontime] .stat-value").strip()
        pg.goto(BASE + "/app")
        go("[data-testid=reset]")
        b.close()
    (OUT / "facts.json").write_text(json.dumps(facts, indent=2), encoding="utf8")
    print(json.dumps(facts, indent=2))


if __name__ == "__main__":
    main()

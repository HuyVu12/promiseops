"""Builds 'User Journey.pdf' (2 pages, A4 landscape) for order SE-1042.

Page 1 is the journey map; page 2 is a storyboard of real screens captured by capture_journey.py,
so the PDF, the README demo script and the video tell the same story with the same times.

Run: python scripts/build_user_journey.py [out.pdf]
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs" / "journey"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "User Journey.pdf"
W, H = 1123, 794
FACTS = json.loads((HERE / "shots" / "facts.json").read_text(encoding="utf8"))


def img(name: str) -> str:
    data = base64.b64encode((HERE / "shots" / f"{name}.png").read_bytes()).decode()
    return f"data:image/png;base64,{data}"


CSS = """
*{box-sizing:border-box}html,body{margin:0}body{font:12.5px/1.42 "Segoe UI",system-ui,sans-serif;color:#13202b}
.page{position:relative;width:1123px;height:794px;overflow:hidden;padding:22px 36px;page-break-after:always;background:#fff}
.page:last-child{page-break-after:auto}
.head{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:2px solid #13202b;padding-bottom:8px;margin-bottom:12px}
.head h1{margin:0;font-size:21px;font-weight:650}.head p{margin:2px 0 0;color:#536371}
.head .tag{font-size:11px;color:#536371;text-align:right}
.people{display:flex;gap:12px;margin-bottom:12px}
.who{flex:1;border:1px solid #dfe2dc;border-radius:8px;padding:8px 12px;display:flex;gap:10px;align-items:center}
.av{width:34px;height:34px;border-radius:50%;background:#0f3b5f;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;flex:none}
.who b{display:block;font-size:13px}.who span{color:#536371;font-size:11.8px}
.who.goal{background:#f6e9f6;border-color:#e3c3e4}.who.goal .av{background:#a626aa}
table{width:100%;border-collapse:collapse;table-layout:fixed}
th,td{border:1px solid #dfe2dc;padding:5px 7px;vertical-align:top;font-size:11.6px}
th{background:#0f3b5f;color:#fff;text-align:left;font-size:12.5px}
th small{display:block;color:#ffd27a;font-weight:700;font-size:12px}
td.rowh{background:#f5f6f3;font-weight:650;width:112px;font-size:12px}
tr.sys td{background:#fbf7fb}
.track{display:flex;align-items:center;margin:2px 0 0}
.c{width:14px;height:14px;border-radius:50%;border:2.5px solid #a626aa;background:#fff;flex:none}
.c.p{background:#a626aa}.c.l{background:#935300;border-color:#935300}.c.m{border-color:#c0392b}
.c.e{border-color:#c0392b;box-shadow:0 0 0 2px #fff,0 0 0 3.5px #c0392b}
.leg{height:3px;background:#a626aa;flex:1}
.mood{font-weight:650}.mood.mid{color:#935300}.mood.ok{color:#1b7350}
.compare{display:grid;grid-template-columns:1fr 1fr 1.3fr;gap:12px;margin-top:10px}
.box{border:1px solid #dfe2dc;border-radius:8px;padding:7px 11px}
.box h3{margin:0 0 4px;font-size:13px}.box p,.box li{margin:0;font-size:11.8px}.box ul{margin:0;padding-left:16px}
.box.bad{background:#fbe8e5;border-color:#f0c9c3}.box.ok{background:#e2f1e9;border-color:#bfe0cd}
.big{font-size:18px;font-weight:700;display:block;margin:1px 0}
.box.bad .big{color:#a32d21}.box.ok .big{color:#1b7350}
.story{display:grid;grid-template-columns:1fr 1fr 236px;grid-template-rows:auto auto auto;gap:10px 12px}
.frame{border:1px solid #dfe2dc;border-radius:8px;overflow:hidden;display:flex;flex-direction:column;background:#fff}
.frame img{display:block;width:100%;object-fit:contain;object-position:center center;background:#fff;border-bottom:1px solid #dfe2dc}
.frame .cap{padding:6px 10px 7px}.frame .cap b{display:block;font-size:12.5px}.frame .cap span{font-size:11.6px;color:#26343f}
.f1{grid-column:1/3}.f3{grid-column:3;grid-row:1/3}.f6{grid-column:2/4}
.n{display:inline-flex;width:18px;height:18px;border-radius:50%;background:#a626aa;color:#fff;font-size:11px;font-weight:700;align-items:center;justify-content:center;margin-right:6px}
.foot{position:absolute;left:36px;right:36px;bottom:14px;font-size:10.8px;color:#536371;display:flex;justify-content:space-between}
.keys{display:inline-flex;gap:12px;align-items:center}.keys i{display:inline-block;vertical-align:-2px;margin-right:4px}
"""

STAGES = [
    ("09:30", "Detect",
     "SE-1042 tops the queue: pick not confirmed, 30 min before the 10:00 route. It ties with SE-1051; B2B goes first.",
     "Pick milestone passed, and the warehouse feed was read after 09:30, so the gap is real. One exception, owner Anna, 15-min timer.",
     "The next order to save is first; no spreadsheet scanning.", "mid", "Alerted"),
    ("09:30", "Take ownership",
     "Anna opens the order and takes ownership; the course shows cutoff, last viable dispatch and promise.",
     "Stops the escalation timer; logs the owner and the response time.",
     "One accountable owner, visible to the whole shift.", "mid", "Owns it"),
    ("09:31", "Escalate",
     "Floor says: not picked, picker on break. An expedite is not her call, so she escalates with the reason.",
     "Expedite is locked for a coordinator; the case moves to the shift lead with Anna's note.",
     "Decision rights are explicit, not tribal.", "mid", "Needs a decision"),
    ("09:32", "Decide",
     "Erik, the shift lead, moves a picker and records Expedited with evidence and a EUR 10 cost.",
     "Requires evidence and the intervention cost; closes the case; logs who decided and why.",
     "Fast decision, audit trail, cost data for Finance.", "ok", "Decided"),
    ("09:52 - 12:32", "Follow through",
     "Nobody chases the order; Anna works the next case.",
     "Pick 09:52 and dispatch 10:17 arrive (late, brown, but before the 11:30 limit). Delivery 12:32 is matched to the promise.",
     "The system watches; people act only when needed.", "ok", "Calm"),
    (FACTS.get("measure_at", "15:27"), "Measure",
     "Shift lead and operations manager review the day on Outcomes.",
     f"On time vs the original promise: {FACTS.get('ontime_with', '93.3%')}. 1 late delivery prevented, "
     "EUR 25 at the Round 1 assumption vs EUR 10 logged; Round 1 scorecard.",
     "Measured honestly, ready for the pilot comparison.", "ok", "Proven"),
]
COURSE = ["m", "m", "e", "e", "l", "p"]


def page_map() -> str:
    head = ('<div class="head"><div><h1>User journey: protecting order SE-1042\'s 14:00 promise</h1>'
            '<p>One complete end-to-end journey through the MVP, with the times the app records. All data is fictional.</p></div>'
            '<div class="tag">PromiseOps MVP · team NgaChainAILayer2<br>User journey 1/2</div></div>')
    people = ('<div class="people">'
              '<div class="who"><div class="av">AL</div><div><b>Anna Lind, DC coordinator</b><span>DC Stockholm South office, full shift, on the phone with the floor.</span></div></div>'
              '<div class="who"><div class="av">EB</div><div><b>Erik Berg, shift lead</b><span>Takes escalations; the only role that may approve an expedite.</span></div></div>'
              '<div class="who goal"><div class="av">SE</div><div><b>Order SE-1042 · B2B site delivery, plasterboard</b><span>Pick 09:30 · route 10:00 · last viable 11:30 · promised 14:00 (Round 1 example).</span></div></div>'
              '</div>')
    ths = "".join(f"<th><small>{t}</small>{s}</th>" for t, s, *_ in STAGES)
    track = "".join(f'<td><div class="track"><span class="c {COURSE[i]}"></span><span class="leg"></span></div></td>' for i in range(6))
    rows = [
        ("Course", track, ""),
        ("User does", "".join(f"<td>{s[2]}</td>" for s in STAGES), ""),
        ("PromiseOps does", "".join(f"<td>{s[3]}</td>" for s in STAGES), "sys"),
        ("Value", "".join(f"<td>{s[4]}</td>" for s in STAGES), ""),
        ("How it feels", "".join(f'<td><span class="mood {s[5]}">{s[6]}</span></td>' for s in STAGES), ""),
    ]
    body = "".join(f'<tr class="{c}"><td class="rowh">{h}</td>{cells}</tr>' for h, cells, c in rows)
    table = f'<table><tr><th style="width:112px">Stage</th>{ths}</tr>{body}</table>'
    compare = (
        '<div class="compare">'
        '<div class="box bad"><h3>Same morning, nobody acts</h3>'
        '<p>The missing pick is found after the route leaves: picked 11:20, dispatched 11:55, delivered <b>14:25: late</b>.</p>'
        f'<span class="big">{FACTS.get("ontime_without", "86.7%")} on time</span><p>Outcomes at 15:30, against the original promise.</p></div>'
        '<div class="box ok"><h3>With PromiseOps</h3>'
        '<p>Owned at 09:30, shift lead decision 09:32, delivered <b>12:32: on time</b>. The promise was never moved.</p>'
        f'<span class="big">{FACTS.get("ontime_with", "93.3%")} on time</span><p>1 late delivery prevented; both runs replay in the demo.</p></div>'
        '<div class="box"><h3>Other paths in the same demo</h3><ul>'
        '<li><b>False alarm</b> (SE-1051): scanner synced late; closed with evidence to tune the rules.</li>'
        '<li><b>No vehicle</b> (SE-1077): handed to customer service with a new ETA; still counted late.</li>'
        '<li><b>No response</b>: after 15 min the case moves to the shift lead.</li>'
        '<li><b>Feed outage</b>: 30 min without data pauses alerts and opens a data task.</li>'
        '</ul></div></div>')
    keys = ('<span class="keys">Course row: <span><i class="c m" style="width:11px;height:11px"></i>missed</span>'
            '<span><i class="c e" style="width:11px;height:11px"></i>escalated</span>'
            '<span><i class="c l" style="width:11px;height:11px"></i>confirmed late</span>'
            '<span><i class="c p" style="width:11px;height:11px"></i>confirmed</span></span>')
    return (f'<section class="page">{head}{people}{table}{compare}<div class="foot">{keys}'
            '<span>Interface in English and Vietnamese · every time above is from the activity log</span></div></section>')


def page_story() -> str:
    head = ('<div class="head"><div><h1>Storyboard: the same journey on real MVP screens</h1>'
            '<p>Captured from the running application (local, demo harness on). Times are the simulated DC clock; each recorded action takes one minute.</p></div>'
            '<div class="tag">PromiseOps MVP · team NgaChainAILayer2<br>User journey 2/2</div></div>')
    frames = [
        ("1-queue-0930", "f1", 165, "1", "09:30 Detect", "SE-1042 (B2B) and SE-1051 missed the 09:30 pick: red ring at Pick, 30 min to act. Ties go to B2B."),
        ("3-shiftlead-decides", "f3", 326, "3", "09:32 Decide", "Signed in as shift lead: Expedited is allowed, with evidence and the intervention cost for Finance."),
        ("2-detail-own", "f2", 132, "2", "09:30 Take ownership", "The course at full size: pick missed, cutoff 10:00, last viable 11:30, promise 14:00."),
        ("4-recorded", "f4", 132, "4", "09:32 Recorded", "Activity log: who took it, who escalated, who decided, why, and the cost."),
        ("6-orders-delivered", "f5", 152, "5", "12:32 Follow through", "SE-1042 delivered 12:32, before 14:00; brown = confirmed late, black dot = actual time."),
        ("7-outcomes", "f6", 152, "6", f"{FACTS.get('measure_at', '15:27')} Measure", "On time against the original promise, late deliveries prevented, response time, Round 1 scorecard and value."),
    ]
    cells = "".join(
        f'<div class="frame {cls}"><img src="{img(f)}" style="height:{h}px" alt="">'
        f'<div class="cap"><b><span class="n">{n}</span>{t}</b><span>{c}</span></div></div>'
        for f, cls, h, n, t, c in frames)
    return (f'<section class="page">{head}<div class="story">{cells}</div>'
            '<div class="foot"><span>Try it: run.ps1, open http://127.0.0.1:8000/app, follow the demo script in the README.</span>'
            '<span>Repository: github.com/HuyVu12/promiseops</span></div></section>')


def main() -> None:
    doc = (f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><style>{CSS}"
           f"@page{{size:{W}px {H}px;margin:0}}</style></head><body>{page_map()}{page_story()}</body></html>")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
        pg.set_content(doc)
        overflow = pg.evaluate("""() => [...document.querySelectorAll('.page')].map(
            p => p.scrollHeight > p.clientHeight + 1)""")
        if any(overflow):
            raise SystemExit(f"Content overflows a page: {overflow}")
        pg.pdf(path=str(OUT), width=f"{W}px", height=f"{H}px", print_background=True)
        for i in range(2):
            pg.screenshot(path=str(HERE / f"journey-p{i + 1}.png"), clip={"x": 0, "y": i * H, "width": W, "height": H}, full_page=True)
        b.close()
    print(OUT)


if __name__ == "__main__":
    main()

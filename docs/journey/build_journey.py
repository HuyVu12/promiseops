"""Builds 'User Journey.pdf' (2 pages, A4 landscape): a journey map for order SE-1042 and a storyboard
of real screens captured by capture.py. Run: python docs/journey/build_journey.py <out.pdf>
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "User Journey.pdf"
W, H = 1123, 794


def img(name: str) -> str:
    data = base64.b64encode((HERE / "shots" / f"{name}.png").read_bytes()).decode()
    return f"data:image/png;base64,{data}"


CSS = """
*{box-sizing:border-box}html,body{margin:0}body{font:12px/1.4 "Segoe UI",system-ui,sans-serif;color:#13202b}
.page{position:relative;width:1123px;height:794px;overflow:hidden;padding:22px 36px;page-break-after:always;background:#fff}
.page:last-child{page-break-after:auto}
.head{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:2px solid #13202b;padding-bottom:8px;margin-bottom:12px}
.head h1{margin:0;font-size:21px;font-weight:650}.head p{margin:2px 0 0;color:#536371}
.head .tag{font-size:11px;color:#536371;text-align:right}
.people{display:flex;gap:12px;margin-bottom:12px}
.who{flex:1;border:1px solid #dfe2dc;border-radius:8px;padding:8px 12px;display:flex;gap:10px;align-items:center}
.av{width:34px;height:34px;border-radius:50%;background:#0f3b5f;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;flex:none}
.who b{display:block;font-size:13px}.who span{color:#536371;font-size:11.5px}
.who.goal{background:#f6e9f6;border-color:#e3c3e4}.who.goal .av{background:#a626aa}
table{width:100%;border-collapse:collapse;table-layout:fixed}
th,td{border:1px solid #dfe2dc;padding:6px 8px;vertical-align:top;font-size:11.3px}
th{background:#0f3b5f;color:#fff;text-align:left;font-size:11.5px}
th small{display:block;color:#ffd27a;font-weight:700;font-size:11px}
td.rowh{background:#f5f6f3;font-weight:650;width:118px;font-size:11.5px}
tr.sys td{background:#fbf7fb}
.track{display:flex;align-items:center;gap:0;margin:2px 0 0}
.c{width:13px;height:13px;border-radius:50%;border:2.5px solid #a626aa;background:#fff;flex:none}
.c.p{background:#a626aa}.c.l{background:#935300;border-color:#935300}.c.m{border-color:#c0392b}
.leg{height:3px;background:#a626aa;flex:1}
.mood{font-weight:600}.mood.bad{color:#c0392b}.mood.ok{color:#1b7350}.mood.mid{color:#935300}
.compare{display:grid;grid-template-columns:1fr 1fr 1.25fr;gap:12px;margin-top:12px}
.box{border:1px solid #dfe2dc;border-radius:8px;padding:9px 12px}
.box h3{margin:0 0 4px;font-size:12.5px}.box p,.box li{margin:0;font-size:11.3px}.box ul{margin:0;padding-left:16px}
.box.bad{border-left:0;background:#fbe8e5}.box.ok{background:#e2f1e9}
.grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}
.frame{border:1px solid #dfe2dc;border-radius:8px;overflow:hidden;display:flex;flex-direction:column}
.frame .pic{height:228px;background-size:cover;background-position:top left;border-bottom:1px solid #dfe2dc}
.frame .cap{padding:7px 10px}.frame .cap b{display:block;font-size:12px}.frame .cap span{font-size:11px;color:#26343f}
.n{display:inline-flex;width:18px;height:18px;border-radius:50%;background:#a626aa;color:#fff;font-size:11px;font-weight:700;align-items:center;justify-content:center;margin-right:6px}
.foot{position:absolute;left:36px;right:36px;bottom:16px;font-size:10.5px;color:#536371;display:flex;justify-content:space-between}
"""

STAGES = [
    ("09:30", "Detect", "Order appears at the top of the queue: SE-1042, pick not confirmed, 30 min before the 10:00 route.",
     "Sees the pick milestone pass with no confirmation, checks the feed was read after 09:30, creates one exception, assigns Anna, starts a 15-min timer.",
     "Exception queue: course with a red ring at Pick 09:30", "No more scanning spreadsheets; the next order to save is first.", "mid", "Alerted"),
    ("09:31", "Take ownership", "Anna opens the order and takes ownership; the escalation timer stops.",
     "Records owner and time to acknowledge in the audit log.",
     "Exception detail: the order's course, time left, actions", "One accountable owner, visible to the whole shift.", "mid", "Owns it"),
    ("09:33", "Verify and escalate", "Calls the floor: goods not picked, picker on break. Expedite is not her call, so she escalates with the reason.",
     "Blocks a coordinator from recording an expedite; moves the case to the shift lead with Anna's note.",
     "Expedite disabled for coordinator; escalate form", "Decision rights are explicit, not tribal.", "mid", "Needs a decision"),
    ("09:35", "Decide", "Erik (shift lead) reads the note, moves a picker, records Expedited with evidence.",
     "Requires written evidence; closes the exception; logs who decided and why.",
     "Shift lead view: Expedited enabled; evidence box", "Fast decision with an audit trail.", "ok", "Decided"),
    ("09:50 - 12:30", "Follow through", "Floor works as usual; nobody has to chase the order.",
     "Pick 09:50 and dispatch 10:15 arrive from the warehouse feed and mark the controls; delivery 12:30 is matched to the promise.",
     "Orders timetable: late punches, delivery before 14:00", "The system watches; people act only when needed.", "ok", "Calm"),
    ("14:30", "Measure", "Shift lead and COO review the day.",
     "Counts on-time against the original 14:00 promise (never edited), flagged orders still on time, time to ownership, false alarms; B2B and B2C apart.",
     "Outcomes: KPI tiles and delivery-margin strip", "Value is measured honestly, ready for the pilot comparison.", "ok", "Proven"),
]


def page_map() -> str:
    head = ('<div class="head"><div><h1>User journey: protecting order SE-1042\'s 14:00 promise</h1>'
            '<p>One complete end-to-end journey through the MVP, as recorded in the demo video. All data is fictional.</p></div>'
            '<div class="tag">PromiseOps MVP · team NgaChainAILayer2<br>User journey 1/2</div></div>')
    people = ('<div class="people">'
              '<div class="who"><div class="av">AL</div><div><b>Anna Lind, DC coordinator</b><span>DC Stockholm South, desk in the DC office, full shift. Handles exceptions while phoning the floor.</span></div></div>'
              '<div class="who"><div class="av">EB</div><div><b>Erik Berg, shift lead</b><span>Takes escalations; the only role allowed to spend capacity on an expedite.</span></div></div>'
              '<div class="who goal"><div class="av">SE</div><div><b>Order SE-1042, B2C, store S04 Nacka</b><span>Promised 14:00 · pick due 09:30 · route dispatches 10:00 · last viable dispatch 11:30.</span></div></div>'
              '</div>')
    ths = "".join(f"<th><small>{t}</small>{s}</th>" for t, s, *_ in STAGES)
    states = ["m", "m", "m", "p", "l", "p"]
    track = "".join(f'<td><div class="track"><span class="c {states[i]}"></span><span class="leg"></span></div></td>' for i in range(6))
    rows = [
        ("Course", track, ""),
        ("User does", "".join(f"<td>{s[2]}</td>" for s in STAGES), ""),
        ("PromiseOps does", "".join(f"<td>{s[3]}</td>" for s in STAGES), "sys"),
        ("Screen", "".join(f"<td>{s[4]}</td>" for s in STAGES), ""),
        ("Value", "".join(f"<td>{s[5]}</td>" for s in STAGES), ""),
        ("How it feels", "".join(f'<td><span class="mood {s[6]}">{s[7]}</span></td>' for s in STAGES), ""),
    ]
    body = "".join(f'<tr class="{c}"><td class="rowh">{h}</td>{cells}</tr>' for h, cells, c in rows)
    table = f'<table><tr><th style="width:118px">Stage</th>{ths}</tr>{body}</table>'
    compare = ('<div class="compare">'
               '<div class="box bad"><h3>Without PromiseOps (same scenario)</h3><p>Nobody notices the missing pick until the route leaves. '
               'The order is picked 11:20, dispatched 11:55 and delivered <b>14:25: late</b> against the 14:00 promise. The demo plays this branch when no one acts.</p></div>'
               '<div class="box ok"><h3>With PromiseOps</h3><p>Exception at 09:30, owner within a minute, shift lead decision at 09:35, '
               'delivered <b>12:30: on time</b>. The promise was never moved to make the KPI look better.</p></div>'
               '<div class="box"><h3>Other paths the MVP handles</h3><ul>'
               '<li><b>False alarm</b> (SE-1051): picked 09:20, scanner synced 09:55; coordinator records it with evidence, rules can be tuned.</li>'
               '<li><b>No response</b> (SE-1060): after 15 min the case moves to the shift lead automatically.</li>'
               '<li><b>Stale feed</b>: warehouse data older than 30 min pauses alerts and opens a data task; no false alarms.</li></ul></div>'
               '</div>')
    return f'<section class="page">{head}{people}{table}{compare}<div class="foot"><span>Legend for the course row: filled = confirmed, brown = confirmed late, red ring = missed.</span><span>Interface available in English and Vietnamese.</span></div></section>'


def page_story() -> str:
    head = ('<div class="head"><div><h1>Storyboard: the same journey on real MVP screens</h1>'
            '<p>Captured from the running application (local, demo harness on). Times are the simulated DC clock.</p></div>'
            '<div class="tag">PromiseOps MVP · team NgaChainAILayer2<br>User journey 2/2</div></div>')
    frames = [
        ("1-queue-0930", "1", "09:30 Detect", "Two open exceptions; SE-1042 and SE-1051 show a red ring at Pick 09:30 and 30 min to act."),
        ("2-detail-open", "2", "09:31 Take ownership", "The order's course at full size: two controls missed, last viable dispatch 11:30, promise 14:00."),
        ("3-shiftlead-decides", "3", "09:35 Decide", "Signed in as the shift lead, Expedited is enabled; evidence is required to record it."),
        ("4-recorded", "4", "09:35 Recorded", "Closed as Expedited; the activity log shows who escalated, who decided and why."),
        ("5-orders-delivered", "5", "12:30 Follow through", "SE-1042: pick and dispatch confirmed late (brown), delivered 12:30, before the 14:00 promise."),
        ("6-outcomes", "6", "14:30 Measure", "On time against the original promise, flagged orders still on time, ownership time, false alarms."),
    ]
    cells = "".join(
        f'<div class="frame"><div class="pic" style="background-image:url({img(f)}){";background-size:contain;background-repeat:no-repeat;background-position:center" if f.startswith("4") else ""}"></div>'
        f'<div class="cap"><b><span class="n">{n}</span>{t}</b><span>{c}</span></div></div>'
        for f, n, t, c in frames)
    return f'<section class="page">{head}<div class="grid">{cells}</div><div class="foot"><span>Try it: python -m uvicorn app.main:app, open /app, follow the demo script in the README.</span><span>Repository: github.com/HuyVu12/promiseops (private)</span></div></section>'


def main() -> None:
    doc = (f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><style>{CSS}"
           f"@page{{size:{W}px {H}px;margin:0}}</style></head><body>{page_map()}{page_story()}</body></html>")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H})
        pg.set_content(doc)
        pg.pdf(path=str(OUT), width=f"{W}px", height=f"{H}px", print_background=True)
        for i in range(2):
            pg.screenshot(path=str(HERE / f"journey-p{i + 1}.png"), clip={"x": 0, "y": i * H, "width": W, "height": H}, full_page=True)
        b.close()
    print(OUT)


if __name__ == "__main__":
    main()

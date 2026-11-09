"""Builds 'System Diagram.pdf' (2 pages, A4 landscape) from hand-placed C4 boxes and orthogonal arrows.

Mermaid's automatic C4 layout overlapped labels, so the PDF is laid out explicitly; the .mmd files in
this folder stay as the text source of the same model. Run: python scripts/build_system_diagram.py [out.pdf]
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parents[1] / "docs" / "architecture"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "System Diagram.pdf"
W, H = 1123, 794

CSS = """
*{box-sizing:border-box}html,body{margin:0}body{font:12px/1.35 "Segoe UI",system-ui,sans-serif;color:#13202b}
.page{position:relative;width:1123px;height:794px;overflow:hidden;page-break-after:always;background:#fff}
.page:last-child{page-break-after:auto}
.head{position:absolute;left:40px;top:22px;right:40px;display:flex;justify-content:space-between;align-items:flex-end;border-bottom:2px solid #13202b;padding-bottom:8px}
.head h1{margin:0;font-size:21px;font-weight:650}.head p{margin:2px 0 0;color:#536371;font-size:12px}
.head .tag{font-size:11px;color:#536371;text-align:right}
.box{position:absolute;border-radius:8px;padding:9px 12px;display:flex;flex-direction:column;justify-content:center;text-align:center}
.box b{font-size:14px;line-height:1.2}.box i{font-style:normal;font-size:10.5px;opacity:.85;margin:2px 0 4px}.box span{font-size:11.5px}
.person{background:#0f3b5f;color:#fff;border-radius:22px 22px 8px 8px}
.system{background:#1f5f8f;color:#fff;border:3px solid #a626aa}
.ext{background:#e9ecef;color:#13202b;border:1px solid #9aa4ae}
.dash{background:#fff8e1;color:#4d3b00;border:1.5px dashed #b38f1d}
.comp{background:#e3edf5;color:#0f3b5f;border:1px solid #7fa4c2}
.comp.mvp{background:#fff8e1;color:#4d3b00;border:1.5px dashed #b38f1d}
.db{background:#0f3b5f;color:#fff;border-radius:8px/18px}
.boundary{position:absolute;border:1.5px dashed #536371;border-radius:10px}
.boundary .bl{position:absolute;left:12px;top:-10px;background:#fff;padding:0 6px;font-weight:650;font-size:12px;color:#13202b}
.lbl{position:absolute;background:#fff;font-size:11px;line-height:1.25;padding:1px 4px;color:#13202b;white-space:nowrap;transform:translate(-50%,-50%)}
.lbl em{font-style:normal;color:#536371;display:block;font-size:10.5px}
svg{position:absolute;left:0;top:0}
.notes{position:absolute;left:40px;right:40px;display:grid;gap:16px}
.notes h3{margin:0 0 4px;font-size:12.5px}.notes p,.notes li{margin:0;font-size:11.5px;color:#26343f}.notes ul{margin:0;padding-left:16px}
.legend{position:absolute;display:flex;gap:16px;font-size:11px;color:#536371;align-items:center}
.legend s{display:inline-block;width:18px;height:12px;border-radius:3px;vertical-align:-2px;margin-right:5px;text-decoration:none}
"""


def box(cls: str, x: int, y: int, w: int, h: int, title: str, kind: str, desc: str) -> str:
    return (f'<div class="box {cls}" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px">'
            f'<b>{html.escape(title)}</b><i>[{html.escape(kind)}]</i><span>{html.escape(desc)}</span></div>')


def arrow(points: list[tuple[int, int]], dashed: bool = False) -> str:
    d = "M" + " L".join(f"{x},{y}" for x, y in points)
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    return f'<path d="{d}" fill="none" stroke="#13202b" stroke-width="1.6" marker-end="url(#a)"{dash}/>'


def label(x: int, y: int, text: str, tech: str = "", left: bool = False) -> str:
    tech_html = f"<em>{html.escape(tech)}</em>" if tech else ""
    shift = "transform:translate(0,-50%);" if left else ""
    return f'<div class="lbl" style="left:{x}px;top:{y}px;{shift}">{html.escape(text)}{tech_html}</div>'


def svg(paths: list[str]) -> str:
    return (f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}"><defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#13202b"/></marker></defs>'
            + "".join(paths) + "</svg>")


def head(title: str, sub: str, n: int) -> str:
    return (f'<div class="head"><div><h1>{html.escape(title)}</h1><p>{html.escape(sub)}</p></div>'
            f'<div class="tag">PromiseOps MVP · team NgaChainAILayer2<br>System diagram {n}/2 · C4 model</div></div>')


def page_context() -> str:
    parts = [head("System context: what is inside PromiseOps and what is outside",
                  "C4 level 1. Every arrow is an interaction the MVP actually performs.", 1)]
    parts.append(box("person", 40, 175, 220, 110, "DC coordinator", "Person",
                     "Triages exceptions, takes ownership, records evidence"))
    parts.append(box("person", 40, 380, 220, 110, "Shift lead", "Person",
                     "Receives escalations; the only role that may approve an expedite"))
    parts.append(box("system", 450, 190, 260, 290, "PromiseOps", "Software system - the MVP",
                     "Detects orders at risk of missing the original promise, shows time left, assigns one owner "
                     "with a 15-minute timer, records outcomes, measures against the promise"))
    parts.append(box("ext", 880, 140, 203, 110, "Order management system", "Existing system, external",
                     "Orders with the original promise and process milestones"))
    parts.append(box("ext", 880, 285, 203, 110, "Warehouse fulfilment system", "Existing system, external",
                     "Pick, dispatch and delivery events"))
    parts.append(box("dash", 880, 430, 203, 120, "Demo harness", "Stand-in, MVP only",
                     "Simulated clock and scripted OMS/WMS records; feed-outage switch"))
    paths = [
        arrow([(260, 250), (450, 250)]),
        arrow([(260, 420), (450, 420)]),
        arrow([(880, 215), (710, 215)]),
        arrow([(880, 340), (710, 340)]),
        arrow([(880, 460), (710, 460)], dashed=True),
    ]
    parts.append(svg(paths))
    parts += [
        label(355, 228, "Works the exception queue", "Browser, HTML pages and forms"),
        label(355, 398, "Takes escalations, approves expedites", "Browser, HTML pages and forms"),
        label(795, 193, "Sends orders + promise", "JSON, POST /api/orders"),
        label(795, 318, "Sends fulfilment events", "JSON, POST /api/events"),
        label(795, 486, "Scripted records every 5 min", "in-process; replaces both feeds"),
    ]
    parts.append(
        '<div class="notes" style="top:640px;grid-template-columns:1fr 1fr 1fr">'
        '<div><h3>Inside the boundary</h3><p>Exception rules, priority queue, ownership and escalation, '
        'evidence-backed outcomes, audit log, data-freshness guard, outcome measurement, English and Vietnamese UI.</p></div>'
        '<div><h3>Outside, read only</h3><p>Order and warehouse systems keep owning orders, stock and dispatch. '
        'PromiseOps never writes back; if it is down, staff use the current floor process.</p></div>'
        '<div><h3>Deliberately not in the MVP</h3><ul><li>Write-back, routing, replenishment, promise changes</li>'
        '<li>Customer messaging: "handed to customer service" is recorded, not sent</li><li>AI in the product (rules only)</li></ul></div>'
        '</div>')
    parts.append('<div class="legend" style="left:40px;top:762px"><span><s style="background:#0f3b5f"></s>Person</span>'
                 '<span><s style="background:#1f5f8f;outline:2px solid #a626aa"></s>System in scope</span>'
                 '<span><s style="background:#e9ecef;border:1px solid #9aa4ae"></s>Existing external system</span>'
                 '<span><s style="background:#fff8e1;border:1.5px dashed #b38f1d"></s>Demo stand-in (MVP only)</span>'
                 '<span>Dashed arrow: simulated interaction</span></div>')
    return '<section class="page">' + "".join(parts) + "</section>"


def page_inside() -> str:
    parts = [head("Inside PromiseOps: one container, seven components, one database",
                  "C4 levels 2 and 3. One Python service with clear modules, as proposed for the pilot; no microservices.", 2)]
    parts.append(box("ext", 90, 86, 220, 56, "OMS / WMS", "External systems", "Real feeds in production"))
    parts.append(box("person", 590, 86, 230, 56, "Coordinator / shift lead", "Person", "Web browser"))
    parts.append('<div class="boundary" style="left:60px;top:188px;width:1000px;height:386px">'
                 '<span class="bl">Web application [Container: Python 3.14, FastAPI, Jinja2, Uvicorn, one process]</span></div>')
    parts.append(box("comp", 90, 210, 220, 86, "Source adapter", "Component: ingest.py",
                     "Validates records; idempotent on source + event id; tracks feed freshness"))
    parts.append(box("comp mvp", 340, 210, 220, 86, "Demo harness", "Component: simulation.py, MVP only",
                     "Simulated clock; releases scripted records every 5 min"))
    parts.append(box("comp", 590, 210, 230, 86, "Pages and JSON API", "Component: main.py, templates",
                     "Queue, exception, orders, outcomes, data health; /api/*"))
    parts.append(box("comp", 850, 210, 180, 86, "Timetable", "Component: timetable.py",
                     "Draws each order as 4 controls on one time axis"))
    parts.append(box("comp", 850, 330, 180, 70, "Language", "Component: i18n.py",
                     "English and Vietnamese, system text by pattern"))
    parts.append(box("comp", 340, 460, 220, 90, "Rules engine", "Component: engine.py",
                     "2 exception rules, freshness guard, one per order and cause, 15-min escalation"))
    parts.append(box("comp", 590, 460, 230, 90, "Workflow", "Component: workflow.py",
                     "Take ownership, escalate, resolve with evidence; role checks"))
    parts.append(box("comp", 850, 460, 180, 90, "Outcomes", "Component: kpi.py",
                     "On time vs original promise; B2B and B2C apart"))
    parts.append('<div class="box db" style="left:90px;top:622px;width:940px;height:62px"><b>Database</b>'
                 '<i>[Container: SQLite]</i><span>orders (promise immutable) · events (unique per source + event id) · '
                 'exceptions (unique per order + cause) · audit log · data-quality tasks</span></div>')
    paths = [
        arrow([(200, 142), (200, 210)]),
        arrow([(705, 142), (705, 210)]),
        arrow([(340, 253), (310, 253)]),
        arrow([(450, 296), (450, 460)]),
        arrow([(705, 296), (705, 460)]),
        arrow([(820, 240), (850, 240)]),
        arrow([(820, 275), (835, 275), (835, 365), (850, 365)]),
        arrow([(835, 365), (835, 505), (850, 505)]),
        arrow([(200, 296), (200, 622)]),
        arrow([(450, 550), (450, 622)]),
        arrow([(705, 550), (705, 622)]),
        arrow([(940, 550), (940, 622)]),
    ]
    parts.append(svg(paths))
    parts += [
        label(210, 160, "Orders and events", "JSON POST /api/orders, /api/events", left=True),
        label(715, 160, "Uses", "HTTP, HTML forms, ?lang=en|vi", left=True),
        label(450, 380, "Runs a rules cycle", "after every poll"),
        label(705, 380, "Submits actions", "role from session cookie"),
        label(200, 450, "Writes events", "idempotent insert"),
        label(450, 590, "Creates, escalates exceptions", ""),
        label(705, 590, "Writes status and audit log", ""),
        label(940, 590, "Reads", ""),
    ]
    parts.append(
        '<div class="notes" style="top:700px;grid-template-columns:1fr">'
        '<div><h3>One cycle, every 5 minutes</h3><p>1 the adapter reads each live feed and records that the read succeeded · '
        '2 duplicates are ignored, bad records rejected and logged · 3 if the warehouse feed is older than 30 min, or was not read after a milestone, '
        'absence-based alerts pause and a data task opens · 4 otherwise the 2 rules create one exception per order and cause, owned by the coordinator, '
        'with a 15-minute response timer · 5 a person acts; expedite needs the shift lead; every outcome needs evidence · '
        '6 every change lands in the audit log · 7 outcomes are measured against the original promise.</p></div></div>')
    return '<section class="page">' + "".join(parts) + "</section>"


def main() -> None:
    doc = (f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><style>{CSS}"
           f"@page{{size:{W}px {H}px;margin:0}}</style></head><body>{page_context()}{page_inside()}</body></html>")
    (HERE / "system-diagram.html").write_text(doc, encoding="utf8")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H})
        pg.set_content(doc)
        pg.pdf(path=str(OUT), width=f"{W}px", height=f"{H}px", print_background=True)
        for i in range(2):
            pg.screenshot(path=str(HERE / f"system-diagram-p{i + 1}.png"), clip={"x": 0, "y": i * H, "width": W, "height": H},
                          full_page=True)
        b.close()
    print(OUT)


if __name__ == "__main__":
    main()

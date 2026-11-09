"""Builds 'System Diagram.pdf' (2 pages, A4 landscape) from hand-placed C4 boxes and orthogonal arrows.

Automatic layout (Mermaid C4) overlapped labels and routed lines through boxes, so the diagram is laid
out explicitly: no arrow crosses a box or another arrow. Every box names the module that implements it.
Run: python scripts/build_system_diagram.py [out.pdf]
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs" / "architecture"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "System Diagram.pdf"
W, H = 1123, 794

CSS = """
*{box-sizing:border-box}html,body{margin:0}body{font:12px/1.35 "Segoe UI",system-ui,sans-serif;color:#13202b}
.page{position:relative;width:1123px;height:794px;overflow:hidden;page-break-after:always;background:#fff}
.page:last-child{page-break-after:auto}
.head{position:absolute;left:40px;top:22px;right:40px;display:flex;justify-content:space-between;align-items:flex-end;border-bottom:2px solid #13202b;padding-bottom:8px}
.head h1{margin:0;font-size:21px;font-weight:650}.head p{margin:2px 0 0;color:#536371;font-size:12px}
.head .tag{font-size:11px;color:#536371;text-align:right}
.box{position:absolute;border-radius:8px;padding:7px 10px;display:flex;flex-direction:column;justify-content:center;text-align:center}
.box b{font-size:13.5px;line-height:1.2}.box i{font-style:normal;font-size:10.5px;opacity:.85;margin:2px 0 3px}.box span{font-size:11.2px;line-height:1.3}
.person{background:#0f3b5f;color:#fff;border-radius:22px 22px 8px 8px}
.person.demo{background:#fff8e1;color:#4d3b00;border:1.5px dashed #b38f1d}
.system{background:#0f3b5f;color:#fff;border:1.5px solid #09253c;border-top:5px solid #a626aa;box-shadow:0 6px 16px rgba(15,59,95,.12)}
.ext{background:#e9ecef;color:#13202b;border:1px solid #9aa4ae}
.dash{background:#fff8e1;color:#4d3b00;border:1.5px dashed #b38f1d}
.future{background:#fff;color:#536371;border:1.5px dotted #8a96a1}
.comp{background:#e3edf5;color:#0f3b5f;border:1px solid #7fa4c2}
.comp.mvp{background:#fff8e1;color:#4d3b00;border:1.5px dashed #b38f1d}
.db{background:#0f3b5f;color:#fff;border-radius:8px/18px}
.boundary{position:absolute;border:1.5px dashed #536371;border-radius:10px}
.bl{position:absolute;font-weight:650;font-size:11.5px;color:#13202b;background:#fff;padding:0 6px}
.lbl{position:absolute;background:#fff;font-size:10.8px;line-height:1.25;padding:1px 4px;color:#13202b;white-space:nowrap;transform:translate(-50%,-50%)}
.lbl em{font-style:normal;color:#536371;display:block;font-size:10.3px}
.lbl.left{transform:translate(0,-50%)}
.lbl.boxed{border:1px solid #dfe2dc;border-radius:3px;padding:1px 5px}
svg{position:absolute;left:0;top:0}
.notes{position:absolute;left:40px;right:40px;display:grid;gap:16px}
.notes h3{margin:0 0 4px;font-size:12.5px}.notes p,.notes li{margin:0;font-size:11.4px;color:#26343f}.notes ul{margin:0;padding-left:16px}
.cycle{position:absolute;left:40px;right:40px;display:grid;grid-template-columns:repeat(5,1fr);gap:18px}
.step{position:relative;border:1px solid #c3c9c1;border-top:3px solid #a626aa;border-radius:6px;padding:6px 9px;font-size:10.9px;line-height:1.3;color:#26343f}
.step b{display:block;font-size:11.5px;color:#13202b;letter-spacing:.04em}
.step:not(:last-child)::after{content:"";position:absolute;right:-13px;top:50%;border:6px solid transparent;border-left:8px solid #a626aa;transform:translateY(-50%)}
.legend{position:absolute;display:flex;gap:16px;font-size:11px;color:#536371;align-items:center}
.legend s{display:inline-block;width:18px;height:12px;border-radius:3px;vertical-align:-2px;margin-right:5px;text-decoration:none}
"""


def box(cls: str, x: int, y: int, w: int, h: int, title: str, kind: str, desc: str) -> str:
    return (f'<div class="box {cls}" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px">'
            f'<b>{html.escape(title)}</b><i>[{html.escape(kind)}]</i><span>{html.escape(desc)}</span></div>')


def arrow(points: list[tuple[int, int]], style: str = "solid") -> str:
    d = "M" + " L".join(f"{x},{y}" for x, y in points)
    dash = {"solid": "", "dashed": ' stroke-dasharray="5 4"', "dotted": ' stroke-dasharray="2 3"'}[style]
    color = "#8a96a1" if style == "dotted" else "#13202b"
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.6" marker-end="url(#a)"{dash}/>'


def label(x: int, y: int, text: str, tech: str = "", left: bool = False) -> str:
    tech_html = f"<em>{html.escape(tech)}</em>" if tech else ""
    return f'<div class="lbl{" left" if left else ""}" style="left:{x}px;top:{y}px">{html.escape(text)}{tech_html}</div>'


def svg(paths: list[str]) -> str:
    return (f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}"><defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#13202b"/></marker></defs>'
            + "".join(paths) + "</svg>")


def head(title: str, sub: str, n: int) -> str:
    return (f'<div class="head"><div><h1>{html.escape(title)}</h1><p>{html.escape(sub)}</p></div>'
            f'<div class="tag">PromiseOps MVP · team NgaChainAILayer2<br>System diagram {n}/2 · C4 model</div></div>')


def page_context() -> str:
    parts = [head("System context: what is inside PromiseOps and what is outside",
                  "C4 level 1. Solid arrows are implemented and tested interfaces; dashed is the demo stand-in, dotted is planned.", 1)]
    parts += [
        box("person", 40, 112, 220, 96, "DC coordinator", "Person",
            "Triages exceptions, takes ownership, records evidence, hands cases to customer service"),
        box("person", 40, 242, 220, 96, "Shift lead", "Person",
            "Takes escalations; the only role that may approve an expedite, and logs its cost"),
        box("person", 40, 372, 220, 96, "Integration desk", "Person, data owner",
            "Gets a data-quality task when the warehouse feed goes quiet; fixes the feed"),
        box("system", 450, 132, 260, 316, "PromiseOps", "Software system - the MVP",
            "Detects orders at risk of missing the original promise, shows time left, gives each case one owner "
            "with a 15-minute timer, records decisions and costs, and measures outcomes against the promise"),
        box("ext", 880, 102, 203, 96, "Order management system", "Existing system, external",
            "Orders with the original promise and process milestones"),
        box("ext", 880, 232, 203, 96, "Warehouse fulfilment system", "Existing system, external",
            "Pick, dispatch and delivery events"),
        box("dash", 880, 362, 203, 106, "Demo harness", "Stand-in, MVP only",
            "Simulated clock and scripted OMS/WMS records; feed-outage switch"),
        box("future", 450, 512, 260, 84, "Late-risk model", "Planned after Gate 2, not built",
            "Round 1 AI roadmap: trained on the labelled outcomes the pilot collects"),
    ]
    parts.append(svg([
        arrow([(260, 160), (450, 160)]),
        arrow([(260, 290), (450, 290)]),
        arrow([(260, 420), (450, 420)]),
        arrow([(880, 150), (710, 150)]),
        arrow([(880, 280), (710, 280)]),
        arrow([(880, 415), (710, 415)], "dashed"),
        arrow([(580, 448), (580, 512)], "dotted"),
    ]))
    parts += [
        label(355, 136, "Works the exception queue", "Browser: HTML pages and forms"),
        label(355, 266, "Decides escalations and expedites", "Browser: HTML pages and forms"),
        label(355, 396, "Sees data tasks, feed health", "Browser: Data health page"),
        label(795, 126, "Sends orders + promise", "JSON, POST /api/orders"),
        label(795, 256, "Sends events + heartbeats", "JSON, POST /api/events, /heartbeat"),
        label(795, 391, "Scripted records, 5-min polls", "in-process; replaces both feeds"),
        label(590, 480, "Reads labelled outcomes", "GET /api/outcomes -> training data", left=True),
    ]
    parts.append(
        '<div class="notes" style="top:628px;grid-template-columns:1fr 1fr 1fr">'
        '<div><h3>Inside the boundary</h3><p>Two exception rules, priority queue, ownership and escalation, '
        'evidence and cost on every decision, audit log, data-freshness guard, outcome measurement against the Round 1 '
        'pilot targets, English and Vietnamese UI.</p></div>'
        '<div><h3>Outside, read only</h3><p>Order and warehouse systems keep owning orders, stock and dispatch. '
        'PromiseOps never writes back; if it is down, staff use the current floor process. API calls need an '
        'X-API-Key when one is configured.</p></div>'
        '<div><h3>Deliberately not in the MVP</h3><ul><li>Write-back, routing, replenishment, promise changes</li>'
        '<li>Customer messaging: "handed to customer service" is recorded, not sent</li>'
        '<li>AI inside the product: rules first, as argued in Round 1</li><li>Company SSO: the demo uses a role switch</li></ul></div>'
        '</div>')
    parts.append('<div class="legend" style="left:40px;top:764px"><span><s style="background:#0f3b5f"></s>Person</span>'
                 '<span><s style="background:#0f3b5f;border-top:3px solid #a626aa"></s>System in scope</span>'
                 '<span><s style="background:#e9ecef;border:1px solid #9aa4ae"></s>Existing external system</span>'
                 '<span><s style="background:#fff8e1;border:1.5px dashed #b38f1d"></s>Demo stand-in (MVP only)</span>'
                 '<span><s style="background:#fff;border:1.5px dotted #8a96a1"></s>Planned, not built</span></div>')
    return '<section class="page">' + "".join(parts) + "</section>"


# Columns for page 2 (x, width): five lanes inside the container boundary.
C = {1: (76, 160), 2: (302, 160), 3: (528, 160), 4: (710, 160), 5: (892, 160)}


def cx(col: int) -> int:
    x, w = C[col]
    return x + w // 2


def page_inside() -> str:
    parts = [head("Inside PromiseOps: one container, three layers, one database",
                  "C4 levels 2 and 3. One Python service with clear modules, as proposed for the pilot; no microservices.", 2)]
    ty, th = 84, 52            # external actors
    by, bh = 192, 356          # container boundary (192 .. 548)
    wy, wh, cy, ch = 222, 82, 356, 104  # web row and core row
    dby = 576                  # database
    parts += [
        box("person demo", 76, ty, 160, th, "Presenter", "Demo only", "Moves the demo clock"),
        box("ext", 302, ty, 386, th, "Order management + warehouse systems", "External, read only", "Real feeds in the pilot"),
        box("person", 710, ty, 342, th, "Coordinator · shift lead · integration desk", "Persons", "Web browser"),
    ]
    parts.append(f'<div class="boundary" style="left:60px;top:{by}px;width:1008px;height:{bh}px"></div>')
    # The container's name sits on its top edge, between the presenter (x 156) and API (x 495) arrows.
    parts.append(f'<div class="bl" style="left:182px;top:{by - 9}px;z-index:2">Web application [Container: one Python process]</div>')
    parts += [
        box("comp mvp", C[1][0], wy, C[1][1], wh, "Demo controls", "routes/demo.py, MVP only", "Advance clock, pause feed, reset"),
        box("comp", 302, wy, 386, wh, "JSON API", "routes/api.py",
            "POST /api/orders, /api/events, /api/sources/{id}/heartbeat · GET /api/exceptions, /api/outcomes, /api/health"),
        box("comp", C[4][0], wy, C[4][1], wh, "Pages", "routes/pages.py, templates", "Queue, exception, orders, outcomes, data health; EN and VI"),
        box("comp", C[5][0], wy, C[5][1], wh, "Human actions", "routes/actions.py", "Take ownership, escalate, resolve, note, demo sign-in"),
        box("comp mvp", C[1][0], cy, C[1][1], ch, "Demo harness", "integration/simulation.py", "Sim clock; scripted feed on a 5-min poll grid; each action takes 1 min"),
        box("comp", C[2][0], cy, C[2][1], ch, "Source adapter", "integration/ingest.py", "Validates records; idempotent on source + event id; records feed reads"),
        box("comp", C[3][0], cy, C[3][1], ch, "Rules engine", "core/engine.py", "2 rules + false-alarm recheck, freshness guard, one exception per order and cause, escalation"),
        box("comp", C[4][0], cy, C[4][1], ch, "Read models", "core/queries.py, timetable.py, kpi.py", "Queue order, courses, outcomes, Round 1 scorecard"),
        box("comp", C[5][0], cy, C[5][1], ch, "Workflow", "core/workflow.py", "Role checks; evidence and cost required; audit trail"),
    ]
    parts.append(box("db", 76, dby, 976, 52, "Database", "Container: SQLite file; PostgreSQL in the pilot",
                     "orders (promise immutable) · events (unique per source + event id) · exceptions (unique per order + cause) "
                     "· audit log · data-quality tasks · ingest log"))
    mid = cy + ch // 2
    trunk, split = 881, 166    # one browser arrow that branches into Pages and Human actions
    parts.append(svg([
        arrow([(cx(1), ty + th), (cx(1), wy)], "dashed"),
        arrow([(495, ty + th), (495, wy)]),
        arrow([(trunk, ty + th), (trunk, split), (cx(4), split), (cx(4), wy)]),
        arrow([(trunk, split), (cx(5), split), (cx(5), wy)]),
        arrow([(cx(1), wy + wh), (cx(1), cy)], "dashed"),
        arrow([(cx(2), wy + wh), (cx(2), cy)]),
        arrow([(cx(4), wy + wh), (cx(4), cy)]),
        arrow([(cx(5), wy + wh), (cx(5), cy)]),
        arrow([(236, mid), (302, mid)], "dashed"),
        arrow([(462, mid), (528, mid)]),
        *[arrow([(cx(i), cy + ch), (cx(i), dby)], "dashed" if i == 1 else "solid") for i in range(1, 6)],
    ]))
    row_gap = (wy + wh + cy) // 2
    db_lbl = cy + ch + 52      # one line for all five database labels, inside the boundary
    parts += [
        label(505, 162, "Orders and events", "JSON over HTTP · X-API-Key", left=True),
        label(trunk + 8, 150, "HTTP, HTML forms", left=True),
        label(cx(1), row_gap, "clock, feed, reset"),
        label(cx(2), row_gap, "validate + store"),
        label(cx(4), row_gap, "reads"),
        label(cx(5), row_gap, "records a decision"),
        label(269, mid - 13, "feeds"),
        label(495, mid - 13, "runs rules"),
        *[f'<div class="lbl boxed" style="left:{cx(i)}px;top:{db_lbl}px">{html.escape(t)}</div>'
          for i, t in [(1, "clock, script"), (2, "writes events, feed reads"), (3, "reads events, writes exceptions"),
                       (4, "reads"), (5, "writes status, audit, cost")]],
    ]
    parts.append(
        '<div class="cycle" style="top:648px">'
        '<div class="step"><b>1 · READ</b>Demo: scripted feeds read every 5 min. Pilot: systems push records and heartbeats; rules run every minute.</div>'
        '<div class="step"><b>2 · CHECK</b>Duplicates ignored, bad records rejected. No read after a milestone, or a feed older than 30 min: alerts pause, a data task opens.</div>'
        '<div class="step"><b>3 · DETECT</b>Two rules raise one exception per order and cause, owned by the coordinator, 15-min timer, then escalation.</div>'
        '<div class="step"><b>4 · ACT</b>People decide. Expedite only by the shift lead; evidence on every outcome, cost on every expedite.</div>'
        '<div class="step"><b>5 · PROVE</b>Outcomes against the original promise; Round 1 scorecard; labelled data for the planned risk model.</div>'
        '</div>')
    parts.append('<div class="legend" style="left:40px;top:770px"><span><s style="background:#e3edf5;border:1px solid #7fa4c2"></s>Component (module named)</span>'
                 '<span><s style="background:#fff8e1;border:1.5px dashed #b38f1d"></s>Demo only; off in pilot mode (wall clock, scheduler)</span>'
                 '<span><s style="background:#0f3b5f"></s>Person / database</span>'
                 '<span>Same READ, CHECK, ACT, PROVE stages as Round 1, slide 5</span></div>')
    return '<section class="page">' + "".join(parts) + "</section>"


def main() -> None:
    doc = (f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><style>{CSS}"
           f"@page{{size:{W}px {H}px;margin:0}}</style></head><body>{page_context()}{page_inside()}</body></html>")
    (HERE / "system-diagram.html").write_text(doc, encoding="utf8")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
        pg.set_content(doc)
        pg.pdf(path=str(OUT), width=f"{W}px", height=f"{H}px", print_background=True)
        for i in range(2):
            pg.screenshot(path=str(HERE / f"system-diagram-p{i + 1}.png"), clip={"x": 0, "y": i * H, "width": W, "height": H},
                          full_page=True)
        b.close()
    print(OUT)


if __name__ == "__main__":
    main()

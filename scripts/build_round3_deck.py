"""Builds the Round 3 pitch deck: docs/continuity/Round 3 Pitch.pdf (12 slides, 16:9) and PNG previews.

Same pipeline as the Round 2 documents: hand-laid HTML, rendered by Chromium through Playwright, so the
deck opens offline on any laptop. Numbers come from docs/continuity/README.md; screenshots of the adjusted
MVP come from scripts/capture_round3.py. The script fails if any text overflows its box or the slide.
Run: python scripts/build_round3_deck.py
"""

from __future__ import annotations

import base64
import html
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "continuity"
SHOTS = DOCS / "shots"
PREVIEWS = DOCS / "slides"
OUT = DOCS / "Round 3 Pitch.pdf"
W, H = 1920, 1080
TOTAL = 12
TEAM = "PromiseOps · Round 3 · NgaChainAILayer2"

CSS = """
*{box-sizing:border-box}html,body{margin:0}
body{font-family:"Segoe UI",system-ui,sans-serif;color:#13202b;-webkit-font-smoothing:antialiased}
.slide{position:relative;width:1920px;height:1080px;overflow:hidden;page-break-after:always;background:#fff}
.slide:last-child{page-break-after:auto}
.dark{background:#0f3b5f;color:#fff}
.kicker{position:absolute;left:96px;top:72px;font-size:21px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:#a626aa}
.dark .kicker{color:#e7b8e8}
h2{position:absolute;left:96px;right:96px;top:108px;margin:0;font-size:52px;line-height:1.12;font-weight:700;letter-spacing:-.01em;text-wrap:balance}
.foot{position:absolute;left:96px;right:96px;bottom:36px;display:flex;justify-content:space-between;font-size:18px;color:#6b7a87}
.dark .foot{color:#a9bfd1}
.note{color:#536371;font-size:20px}
.card{background:#f5f6f3;border-radius:14px;padding:26px 30px}
.card h3{margin:0 0 10px;font-size:28px;line-height:1.2}
.card p{margin:0;font-size:23px;line-height:1.4;color:#26343f}
.num{display:inline-flex;align-items:center;justify-content:center;width:46px;height:46px;border-radius:50%;
  border:4px solid #a626aa;color:#a626aa;font-weight:700;font-size:22px;flex:none;background:#fff}
.dark .num{background:#0f3b5f;border-color:#e7b8e8;color:#fff}
.amount{font-size:26px;font-weight:700;color:#0f3b5f;margin-top:14px}
table{border-collapse:collapse;width:100%}
th,td{text-align:left;vertical-align:top;padding:12px 14px;border-bottom:1px solid #dfe2dc;font-size:21px;line-height:1.3}
th{font-size:17px;letter-spacing:.08em;text-transform:uppercase;color:#536371;border-bottom:2px solid #13202b;font-weight:600}
td.r,th.r{text-align:right}
table.big td{font-size:23.5px;padding:17px 14px}table.big th{font-size:18px}
.chip{display:inline-block;padding:3px 12px;border-radius:999px;font-size:17px;font-weight:600;letter-spacing:.02em}
.chip.new{background:#f6e9f6;color:#7c1c80}.chip.same{background:#eceee9;color:#536371}
/* the course motif from the product: controls on a line */
.course{position:absolute;display:flex;align-items:center}
.course .line{position:absolute;height:6px;background:#a626aa;left:0;right:0;top:50%;transform:translateY(-50%)}
.ctl{position:relative;width:38px;height:38px;border-radius:50%;border:6px solid #a626aa;background:#fff;flex:none}
.ctl.done{background:#a626aa}.ctl.now{border-color:#fff;box-shadow:0 0 0 6px #e7b8e8}
/* diagram */
.box{position:absolute;border-radius:12px;padding:10px 14px;display:flex;flex-direction:column;justify-content:center;text-align:center}
.box b{font-size:22px;line-height:1.2}.box i{font-style:normal;font-size:16px;opacity:.85;margin:3px 0 4px}.box span{font-size:17.5px;line-height:1.3}
.person{background:#0f3b5f;color:#fff;border-radius:30px 30px 12px 12px}
.system{background:#0f3b5f;color:#fff;border-top:7px solid #a626aa}
.ext{background:#e9ecef;color:#13202b;border:1.5px solid #9aa4ae}
.comp{background:#e3edf5;color:#0f3b5f;border:1.5px solid #7fa4c2}
.retire{background:#fff;color:#536371;border:2px dashed #9aa4ae}
.lane{position:absolute;border:2px solid #dfe2dc;border-radius:16px}
.lanelbl{position:absolute;font-size:19px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:#536371;background:#fff;padding:0 10px}
.lbl{position:absolute;font-size:16.5px;line-height:1.2;color:#13202b;text-align:center;transform:translate(-50%,-100%);white-space:nowrap}
svg.arrows{position:absolute;left:0;top:0;pointer-events:none}
.legend{position:absolute;display:flex;gap:30px;font-size:18px;color:#536371;align-items:center}
.legend s{display:inline-block;width:26px;height:16px;border-radius:4px;vertical-align:-2px;margin-right:8px;text-decoration:none}
"""


def esc(s: str) -> str:
    return html.escape(s)


def shot(name: str) -> str:
    data = base64.b64encode((SHOTS / name).read_bytes()).decode()
    return f"data:image/png;base64,{data}"


def slide(n: int, body: str, kicker: str = "", title: str = "", dark: bool = False, foot_note: str = "") -> str:
    k = f'<div class="kicker">{esc(kicker)}</div>' if kicker else ""
    t = f"<h2>{esc(title)}</h2>" if title else ""
    left = esc(TEAM) + (f" · {esc(foot_note)}" if foot_note else "")
    return (f'<section class="slide{" dark" if dark else ""}" id="s{n}">{k}{t}{body}'
            f'<div class="foot"><span>{left}</span><span>{n} / {TOTAL}</span></div></section>')


def problem_statement() -> str:
    phases = [
        ("Round 1", "Propose a solution", "Explain how Company A could catch delivery risks early enough for warehouse teams to act."),
        ("Round 2", "Build a working MVP", "Show how a coordinator spots an at-risk order, assigns an owner and records the outcome."),
        ("Round 3", "Revise the proposal", "Work within a 30% smaller budget and include a mandatory move from Dynamics 365 to Salesforce."),
    ]
    cards = "".join(
        f'<div class="card" style="padding:42px">'
        f'<div style="font-size:26px;font-weight:700;color:#7c1c80">{round_name}</div>'
        f'<h3 style="font-size:36px;margin:24px 0 18px">{title}</h3>'
        f'<p style="font-size:30px">{description}</p></div>'
        for round_name, title, description in phases
    )
    body = f"""
    <p style="position:absolute;left:96px;top:200px;width:1510px;font-size:38px;line-height:1.35">
      How can Company A give warehouse teams enough time to act before an order misses its delivery promise?
    </p>
    <div style="position:absolute;left:96px;right:96px;top:442px;bottom:182px;
                display:grid;grid-template-columns:repeat(3,1fr);gap:28px">{cards}</div>"""
    return slide(1, body, "IT Consultant Challenge 2026", "Problem statement")


# ---------- 1. Title ----------
def s1() -> str:
    stops = [("09:30", "Pick unconfirmed"), ("10:00", "Truck leaves"), ("14:00", "Delivery promised")]
    ctl = "".join(
        f'<div style="position:absolute;left:{i * 675}px;top:0;width:370px">'
        f'<div class="ctl {"now" if i == 0 else ""}"></div>'
        f'<div style="margin-top:18px;font-size:44px;font-weight:700">{a}</div>'
        f'<div style="font-size:30px;color:#cfe0ee">{b}</div></div>'
        for i, (a, b) in enumerate(stops))
    body = f"""
    <div style="position:absolute;left:96px;top:96px;font-size:22px;letter-spacing:.14em;color:#e7b8e8;font-weight:600">
      IT CONSULTANT CHALLENGE 2026 · ROUND 3 · TEAM NGACHAINAILAYER2</div>
    <div style="position:absolute;left:96px;top:210px;width:1500px">
      <div style="font-size:84px;line-height:1.05;font-weight:700;letter-spacing:-.015em">PromiseOps, revised:<br>keep the customer, keep the promise</div>
      <p style="font-size:34px;line-height:1.35;color:#cfe0ee;margin:36px 0 0;width:1300px">Company A cut the budget by 30% and made a CRM migration mandatory.
      This is how we would still deliver both, inside the same 12 weeks.</p>
    </div>
    <div style="position:absolute;left:96px;top:650px;right:96px;height:190px">
      <div style="position:absolute;left:16px;width:1350px;top:16px;height:6px;background:#a626aa"></div>
      {ctl}
    </div>"""
    return slide(2, body, dark=True)


# ---------- 2. Recommendation ----------
def s2() -> str:
    cards = [
        ("1", "Danish CRM to Salesforce first", "Mandatory: Dynamics 365 is being switched off. The cutover window and shared staff go to CRM first.", "EUR 66.6k + 18k shared"),
        ("2", "PromiseOps shadow pilot at one Swedish DC", "Runs on the Round 2 MVP. Coordinators work real exceptions; the usual floor process still decides.", "EUR 27k"),
        ("3", "Same 12 weeks, both Round 1 gates", "Gate 1 in week 2 checks money and deadline. Gate 2 in week 12 accepts CRM and decides the live phase.", "EUR 14.4k contingency"),
    ]
    items = "".join(
        f'<div class="card" style="display:flex;gap:24px;align-items:flex-start;height:200px">'
        f'<span class="num">{n}</span><div><h3>{esc(t)}</h3><p>{esc(d)}</p><div class="amount">{esc(a)}</div></div></div>'
        for n, t, d, a in cards)
    body = f"""
    <div style="position:absolute;left:96px;top:300px;width:540px">
      <div style="font-size:104px;font-weight:700;line-height:1;color:#0f3b5f;white-space:nowrap">EUR 126k</div>
      <p style="font-size:28px;line-height:1.4;margin:24px 0 0;color:#26343f">30% below the EUR 180k we asked for in Round 1.</p>
      <p style="font-size:28px;line-height:1.4;margin:18px 0 0;color:#26343f">Same 12 weeks. Same two gates. Nothing in CRM depends on PromiseOps, or the reverse.</p>
    </div>
    <div style="position:absolute;left:700px;right:96px;top:290px;display:grid;gap:26px">{items}</div>"""
    return slide(3, body, "Our recommendation", "Protect CRM continuity first, keep PromiseOps alive on what is already built",
                 foot_note="Team assumptions; no Company A figures were provided")


# ---------- 3. What changed and what we assume ----------
def s3() -> str:
    rows = [
        ("CRM country", "Denmark, apart from the Swedish pilot DC", "Sweden: shadow onboarding moves after cutover"),
        ("Salesforce", "Group org with sandbox; licences are the country's running cost", "New org or licences: sponsor decision"),
        ("Switch-off", "Dynamics readable until week 10, confirmed in writing", "Earlier: CRM-only fast track"),
        ("CRM scope", "Accounts, contacts, open opportunities, active cases; history to an archive", "More scope: paid from contingency first"),
        ("Rates", "EUR 550 per person-day, as in Round 1", "Same days, different euros"),
    ]
    tr = "".join(f"<tr><td><b>{esc(a)}</b></td><td>{esc(b)}</td><td>{esc(c)}</td></tr>" for a, b, c in rows)
    req = [
        ("Budget cut by 30%", "EUR 180k becomes EUR 126k. The EUR 120k Swedish cohort from Round 1 no longer fits."),
        ("CRM migration is a must-have", "One country moves from Dynamics 365 to Salesforce before the old system is switched off."),
    ]
    reqs = "".join(f'<div class="card" style="background:#f6e9f6"><h3>{esc(a)}</h3><p>{esc(b)}</p></div>' for a, b in req)
    body = f"""
    <div style="position:absolute;left:96px;top:290px;width:560px;display:grid;gap:26px">
      <div style="font-size:21px;font-weight:600;letter-spacing:.1em;color:#536371">THE CLIENT ASKED</div>{reqs}
    </div>
    <div style="position:absolute;left:730px;right:96px;top:290px">
      <div style="font-size:21px;font-weight:600;letter-spacing:.1em;color:#536371;margin-bottom:12px">WE PLAN ON</div>
      <table class="big"><thead><tr><th style="width:200px">Assumption</th><th>Value</th><th style="width:360px">If it is wrong</th></tr></thead><tbody>{tr}</tbody></table>
      <p class="note" style="margin:22px 0 0">Every assumption is checked at Gate 1 in week 2. The fallback order is on slide 11.</p>
    </div>"""
    return slide(4, body, "What changed", "Two client requests, and the assumptions we plan on",
                 foot_note="Team assumptions; no Company A figures were provided")


# ---------- 4. Budget ----------
def bar(segments: list[tuple[str, float, str, str]], scale: float) -> str:
    parts = "".join(
        f'<div style="width:{v * scale:.1f}px;height:72px;background:{c};{b}"></div>' for _, v, c, b in segments)
    legend = "".join(
        f'<div style="display:flex;align-items:center;gap:10px;font-size:21px"><s style="display:inline-block;width:22px;height:22px;border-radius:5px;background:{c};{b}"></s>'
        f'{esc(name)} <b style="margin-left:4px">EUR {v:g}k</b></div>' for name, v, c, b in segments)
    return (f'<div style="display:flex;gap:4px">{parts}</div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:10px 28px;margin-top:16px">{legend}</div>')


def s4() -> str:
    scale = 1000 / 180
    r1 = [("Validation", 10, "#7fa4c2", ""), ("Pilot", 50, "#174c76", ""), ("Swedish cohort", 120, "#0f3b5f", "")]
    r3 = [("CRM migration", 66.6, "#a626aa", ""), ("Shared services", 18, "#d59ad7", ""), ("PromiseOps pilot", 27, "#174c76", ""),
          ("Contingency", 14.4, "#fff", "border:3px dashed #9aa4ae")]
    days = [("Application", 24, 0, "built in Round 2"), ("Integration", 28, 22, "API exists; connect feeds, add SSO"),
            ("QA and data", 16, 8, "shadow scorecard only"), ("Business analysis", 12, 10, ""), ("Adoption", 8, 6, "")]
    highlight = ' style="background:#f6e9f6"'
    tr = "".join(
        f'<tr{highlight if a == "Application" else ""}><td><b>{a}</b>'
        f'{"<br><span class=note>" + esc(why) + "</span>" if why else ""}</td><td class="r">{d1}</td><td class="r"><b>{d3}</b></td></tr>'
        for a, d1, d3, why in days)
    body = f"""
    <div style="position:absolute;left:96px;top:300px;width:1020px">
      <div style="font-size:24px;font-weight:700;margin-bottom:14px">Round 1 ask: EUR 180k</div>{bar(r1, scale)}
      <div style="font-size:24px;font-weight:700;margin:56px 0 14px">Round 3: EUR 126k</div>{bar(r3, scale)}
      <p class="note" style="margin:34px 0 0;width:1000px">CRM gets the largest share because it is mandatory. Shared services cover
      licence overlap, secure staging, security and delivery management for both workstreams.</p>
    </div>
    <div class="card" style="position:absolute;left:1190px;right:96px;top:290px;background:#fff;border:2px solid #dfe2dc">
      <h3>Why PromiseOps fits in EUR 27k</h3>
      <table style="margin-top:6px"><thead><tr><th>Person-days</th><th class="r">Round 1</th><th class="r">Now</th></tr></thead>
      <tbody>{tr}<tr><td><b>Total</b></td><td class="r"><b>88</b></td><td class="r"><b>46</b></td></tr></tbody></table>
      <p style="font-size:20px;margin-top:16px">46 days x EUR 550 + EUR 1.6k infrastructure = EUR 27k</p>
    </div>"""
    return slide(5, body, "Budget", "EUR 126k: CRM takes the largest share, PromiseOps fits because the app exists",
                 foot_note="Team assumptions; no Company A figures were provided")


# ---------- 5. Keep, change, postpone ----------
def s5() -> str:
    cols = [
        ("Keep", "#e2f1e9", "#14533a", ["Two rules, deadline priority, one owner", "15-minute escalation to the shift lead",
                                        "Evidence and cost on every decision", "Outcomes against the original promise",
                                        "Single sign-on before any real data"]),
        ("Change", "#fdf0d8", "#7a4500", ["Live decisions from week 9 become shadow decisions until week 12",
                                          "The impact estimate becomes a shadow scorecard: coverage, actionable alerts, response time"]),
        ("Postpone", "#eceee9", "#36454f", ["6 vs 6 store difference-in-differences", "EUR 120k Swedish cohort and the EUR 354k/year case",
                                            "More sites, the risk model, CRM sync"]),
    ]
    cards = "".join(
        f'<div class="card" style="background:{bg}"><div style="font-size:30px;font-weight:700;color:{fg};margin-bottom:18px">{t}</div>'
        f'<ul style="margin:0;padding-left:26px">' + "".join(f'<li style="font-size:25px;line-height:1.38;margin-bottom:16px">{esc(i)}</li>' for i in items)
        + "</ul></div>" for t, bg, fg, items in cols)
    body = f"""
    <div style="position:absolute;left:96px;right:96px;top:310px;display:grid;gap:56px">
    <div style="display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:30px">{cards}</div>
    <div style="background:#0f3b5f;color:#fff;border-radius:14px;padding:26px 34px;display:flex;gap:26px;align-items:center">
      <span class="num" style="background:#0f3b5f;border-color:#e7b8e8;color:#fff">+</span>
      <div style="font-size:25px;line-height:1.4"><b>How the live phase comes back.</b> If CRM closes within its budget, the unspent EUR 14.4k
      contingency funds a 4-week live phase in weeks 13-16 on the Round 1 design. No new money, inside the original six-month window.</div>
    </div></div>"""
    return slide(6, body, "Trade-offs", "What we keep, change and postpone from Round 1")


# ---------- 6. System diagram ----------
def arrow(x1: int, y1: int, x2: int, y2: int, style: str = "solid") -> str:
    dash = {"solid": "", "dashed": ' stroke-dasharray="10 7"', "dotted": ' stroke-dasharray="3 6"'}[style]
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#13202b" stroke-width="2.5"{dash} marker-end="url(#ah)"/>'


def dbox(cls: str, x: int, y: int, w: int, h: int, title: str, kind: str, desc: str) -> str:
    return (f'<div class="box {cls}" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px">'
            f'<b>{esc(title)}</b><i>[{esc(kind)}]</i><span>{esc(desc)}</span></div>')


def lbl(x: int, y: int, text: str) -> str:
    return f'<div class="lbl" style="left:{x}px;top:{y}px">{text}</div>'


def s6() -> str:
    c1, c2, c3, c4 = 136, 556, 1036, 1486
    wa, wb, wc, wd = 270, 330, 300, 300
    a1, a2 = 306, 442          # lane A rows (top y), row height 104
    b1, b2 = 670, 806          # lane B rows
    rh = 104
    boxes = [
        dbox("ext", c1, a1, wa, rh, "Order system", "Existing, read only", "Orders, original promise"),
        dbox("ext", c1, a2, wa, rh, "Warehouse system", "Existing, read only", "Pick, dispatch, delivery"),
        dbox("system", c2, a1, wb, a2 + rh - a1, "PromiseOps", "Round 2 MVP, pilot + shadow mode",
             "Rules, queue, one owner, escalation, outcomes against the promise"),
        dbox("person", c3, a1, wc, rh, "Coordinator, shift lead", "People, Sweden", "Decisions recorded in shadow"),
        dbox("person", c3, a2, wc, rh, "Integration desk", "Person", "Task when a feed goes quiet"),
        dbox("ext", c4, a1, wd, rh, "Customer service", "Existing team and CRM", "Talks to the customer"),
        dbox("retire", c1, b1, wa, b2 + rh - b1, "Dynamics 365", "Denmark, switched off after cutover",
             "Scoped export of accounts, contacts, opportunities, cases"),
        dbox("comp", c2, b1, wb, b2 + rh - b1, "Restricted staging", "Migration only",
             "Validate, map source IDs, deduplicate, reconcile counts"),
        dbox("system", c3, b1, wc, rh, "Salesforce", "Target CRM", "Rehearsed in a sandbox first"),
        dbox("comp", c3, b2, wc, rh, "Legacy archive", "Read only, restricted", "Closed history kept for retention"),
        dbox("person", c4, b1, wd, b2 + rh - b1, "Danish CRM users", "People, Denmark", "Same business reference before and after"),
    ]
    ma, mb = lambda r: r + rh // 2, lambda r: r + rh // 2
    lines = [
        arrow(c1 + wa, ma(a1), c2 - 4, ma(a1)), arrow(c1 + wa, ma(a2), c2 - 4, ma(a2)),
        arrow(c2 + wb, ma(a1), c3 - 4, ma(a1)), arrow(c2 + wb, ma(a2), c3 - 4, ma(a2)),
        arrow(c3 + wc, ma(a1), c4 - 4, ma(a1), "dashed"),
        arrow(c1 + wa, (b1 + b2 + rh) // 2, c2 - 4, (b1 + b2 + rh) // 2),
        arrow(c2 + wb, mb(b1), c3 - 4, mb(b1)), arrow(c2 + wb, mb(b2), c3 - 4, mb(b2)),
        arrow(c3 + wc, mb(b1), c4 - 4, mb(b1)), arrow(c3 + wc, mb(b2), c4 - 4, mb(b2), "dotted"),
    ]
    g1, g2, g3 = (c1 + wa + c2) // 2, (c2 + wb + c3) // 2, (c3 + wc + c4) // 2
    labels = [
        lbl(g1, ma(a1) - 8, "orders,<br>promise"), lbl(g1, ma(a2) - 8, "events,<br>heartbeats"),
        lbl(g2, ma(a1) - 8, "queue,<br>decisions"), lbl(g2, ma(a2) - 8, "data task"),
        lbl(g3, ma(a1) - 8, "handoff,<br>case ref only"),
        lbl(g1, (b1 + b2 + rh) // 2 - 8, "scoped<br>export"),
        lbl(g2, mb(b1) - 8, "upsert by<br>external ID"), lbl(g2, mb(b2) - 8, "closed<br>history"),
        lbl(g3, mb(b1) - 8, "sign in"), lbl(g3, mb(b2) - 8, "authorised<br>lookup"),
    ]
    svg = (f'<svg class="arrows" width="{W}" height="{H}"><defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" '
           f'markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#13202b"/></marker></defs>'
           + "".join(lines) + "</svg>")
    body = f"""
    <div class="lane" style="left:96px;right:96px;top:262px;height:310px"></div>
    <div class="lanelbl" style="left:120px;top:250px">PromiseOps pilot · one Swedish DC · all 12 weeks</div>
    <div class="lane" style="left:96px;right:96px;top:626px;height:310px"></div>
    <div class="lanelbl" style="left:120px;top:614px">CRM migration · Denmark · cutover in week 9</div>
    <div style="position:absolute;left:96px;right:96px;top:584px;text-align:center;font-size:19px;color:#536371">
      Shared: budget, integration staff and the steering group. <b style="color:#13202b">No runtime connection between the two paths.</b></div>
    {"".join(boxes)}{svg}{"".join(labels)}
    <div class="legend" style="left:96px;top:956px">
      <span><svg width="44" height="10"><line x1="0" y1="5" x2="44" y2="5" stroke="#13202b" stroke-width="2.5"/></svg> data flow</span>
      <span><svg width="44" height="10"><line x1="0" y1="5" x2="44" y2="5" stroke="#13202b" stroke-width="2.5" stroke-dasharray="10 7"/></svg> manual handoff</span>
      <span><svg width="44" height="10"><line x1="0" y1="5" x2="44" y2="5" stroke="#13202b" stroke-width="2.5" stroke-dasharray="3 6"/></svg> on request</span>
      <span><s style="background:#0f3b5f"></s>in scope</span><span><s style="background:#e9ecef;border:1.5px solid #9aa4ae"></s>existing, outside</span>
      <span><s style="background:#fff;border:2px dashed #9aa4ae"></s>being retired</span>
    </div>"""
    return slide(7, body, "System diagram", "Two independent paths, so neither can break the other")


# ---------- 7. User journeys ----------
def s7() -> str:
    lanes = [
        ("DC coordinator and shift lead · Sweden · shadow pilot", [
            ("09:30", "Detect", "Pick missing after a fresh warehouse read. One case, owner Anna, 15-minute timer.", False),
            ("09:31", "Own, escalate", "Anna checks the floor. An expedite is the shift lead's call, so she escalates.", False),
            ("09:32", "Decide in shadow", "Erik records what he would do and its cost. The usual floor call makes the real decision.", True),
            ("10:05", "Hand off", "SE-1077 cannot make it. Customer service takes the case; PromiseOps keeps only its reference.", True),
            ("15:30", "Measure", "Alert precision and response time count. Prevented lateness is not claimed.", True),
        ]),
        ("CRM operator · Denmark · migration", [
            ("Week 7-8", "Rehearse", "Tests own customers and an active case in the Salesforce sandbox: owner, contacts, access.", True),
            ("Week 9", "Freeze", "Dynamics goes read-only. Urgent work goes into a controlled queue, entered once after go-live.", True),
            ("Week 9", "Go live", "Signs in to Salesforce and continues the case with the same business reference.", True),
            ("Week 10", "Find history", "Closed history sits in a restricted archive. Access on request, logged.", True),
            ("Week 10-12", "Hypercare", "Daily issue review until the country lead accepts the support handover.", True),
        ]),
    ]
    out = []
    for i, (name, steps) in enumerate(lanes):
        top = 280 + i * 330
        cards = "".join(
            f'<div class="card" style="height:228px;padding:20px 22px;background:{"#f6e9f6" if changed and i == 0 else "#f5f6f3"}">'
            f'<div style="font-size:19px;font-weight:700;color:#a626aa">{esc(t)}</div>'
            f'<div style="font-size:25px;font-weight:700;margin:4px 0 8px">{esc(head)}</div>'
            f'<p style="font-size:20.5px;line-height:1.35">{esc(desc)}</p></div>'
            for t, head, desc, changed in steps)
        out.append(
            f'<div style="position:absolute;left:96px;right:96px;top:{top}px">'
            f'<div style="font-size:21px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:#536371;margin-bottom:12px">{esc(name)}</div>'
            f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:22px">{cards}</div></div>')
    legend = ('<div class="legend" style="left:96px;top:930px"><span><s style="background:#f6e9f6"></s>changed from the Round 2 journey</span>'
              '<span>Every Danish CRM step is new in Round 3</span></div>')
    return slide(8, "".join(out) + legend, "User journeys", "Same morning in Sweden, a new cutover in Denmark")


# ---------- 8. MVP, adjusted ----------
def s8() -> str:
    points = [
        ("Shadow mode", "One switch, PROMISEOPS_SHADOW=1. A banner on every screen, every decision marked, and Outcomes never claim a prevented late delivery."),
        ("Handoff by reference", "The customer-service case number is stored with the decision. No CRM integration, during or after the cutover."),
        ("Already there from Round 2", "Pilot mode on the wall clock, API key, feed heartbeats, read-only adapter."),
    ]
    pts = "".join(
        f'<div style="display:flex;gap:20px;margin-bottom:28px"><span class="num">{i + 1}</span>'
        f'<div><div style="font-size:27px;font-weight:700;margin-bottom:6px">{esc(t)}</div>'
        f'<div style="font-size:22px;line-height:1.38;color:#26343f">{esc(d)}</div></div></div>'
        for i, (t, d) in enumerate(points))
    def frame(name: str, caption: str, x: int, y: int, w: int, h: int) -> str:
        return (f'<figure style="position:absolute;left:{x}px;top:{y}px;width:{w}px;margin:0">'
                f'<div style="height:{h}px;background:#f5f6f3;border:1.5px solid #dfe2dc;border-radius:12px;display:flex;'
                f'align-items:center;justify-content:center;overflow:hidden;padding:10px">'
                f'<img src="{shot(name)}" style="max-width:100%;max-height:100%;object-fit:contain"></div>'
                f'<figcaption style="font-size:19px;color:#536371;margin-top:8px">{esc(caption)}</figcaption></figure>')

    shots = (frame("1-banner.png", "1 · The banner on every screen", 712, 276, 1112, 112)
             + frame("3-log-shadow.png", "1 + 2 · The activity log keeps the handoff, its reference and the shadow mark", 712, 450, 1112, 214)
             + frame("2-case-ref.png", "2 · The case reference on the decision form", 712, 726, 540, 214)
             + frame("4-prevented.png", "Outcomes refuse to claim a prevented late delivery", 1284, 726, 540, 214))
    body = f"""
    <div style="position:absolute;left:96px;top:290px;width:570px">{pts}
      <p class="note" style="margin:6px 0 0">Two small changes, about one day of work, all automated tests pass. Shown live in the demo.</p>
    </div>{shots}"""
    return slide(9, body, "MVP, adjusted", "Two small changes make the MVP ready for a shadow pilot")


# ---------- 9. 12 weeks and the cutover ----------
def s9() -> str:
    x0, wk = 430, 80          # first week column x, week width (16 weeks)
    rows = [
        ("CRM · Denmark", None),
        ("Discover", (1, 2, "#a626aa", "")), ("Configure and map", (3, 6, "#a626aa", "")),
        ("Rehearse and UAT", (7, 8, "#a626aa", "")), ("Cutover", (9, 9, "#7c1c80", "")), ("Hypercare", (10, 12, "#d59ad7", "")),
        ("PromiseOps · Sweden", None),
        ("Validate the DC", (1, 2, "#174c76", "")), ("Connect feeds, SSO", (3, 6, "#174c76", "")),
        ("Shadow pilot, quiet in W9", (7, 12, "#7fa4c2", "")), ("Live phase, if funded", (13, 16, "#fff", "border:3px dashed #174c76")),
    ]
    out, y = [], 300
    for name, span in rows:
        if span is None:
            out.append(f'<div style="position:absolute;left:96px;top:{y + 6}px;font-size:19px;font-weight:700;letter-spacing:.06em;'
                       f'text-transform:uppercase;color:#536371">{esc(name)}</div>')
            y += 40
            continue
        a, b, color, extra = span
        out.append(f'<div style="position:absolute;left:96px;top:{y}px;width:320px;font-size:21px;line-height:34px">{esc(name)}</div>'
                   f'<div style="position:absolute;left:{x0 + (a - 1) * wk + 3}px;top:{y + 3}px;width:{(b - a + 1) * wk - 6}px;height:30px;'
                   f'border-radius:7px;background:{color};{extra}"></div>')
        y += 44
    weeks = "".join(
        f'<div style="position:absolute;left:{x0 + (i - 1) * wk}px;top:262px;width:{wk}px;text-align:center;font-size:18px;'
        f'color:{"#536371" if i <= 12 else "#9aa4ae"}">W{i}</div>' for i in range(1, 17))
    grid = "".join(f'<div style="position:absolute;left:{x0 + i * wk}px;top:292px;width:1px;height:{y - 292}px;background:#eceee9"></div>'
                   for i in range(17))
    gates = "".join(
        f'<div style="position:absolute;left:{x0 + w * wk - 2}px;top:286px;width:4px;height:{y - 280}px;background:#13202b"></div>'
        f'<div style="position:absolute;left:{x0 + w * wk - 60}px;top:{y + 4}px;width:120px;text-align:center;font-size:19px;font-weight:700">{g}</div>'
        for w, g in ((2, "Gate 1"), (12, "Gate 2")))
    shadow_y = y - 2 * 44  # the shadow pilot row, one above the live phase
    pause = (f'<div title="no onboarding work in the cutover week" style="position:absolute;left:{x0 + 8 * wk + 3}px;top:{shadow_y + 3}px;'
             f'width:{wk - 6}px;height:30px;border-radius:7px;background:repeating-linear-gradient(135deg,#7fa4c2 0 6px,#ffffff 6px 12px)"></div>')
    panels = f"""
    <div class="card" style="position:absolute;left:96px;width:840px;top:{y + 44}px;padding:20px 26px">
      <h3 style="font-size:24px">Go / no-go for the CRM switch</h3>
      <p style="font-size:20.5px">Zero unexplained gaps in reconciliation, every critical UAT scenario passes, and the Danish country
      lead and the migration owner sign off before Salesforce takes writes.</p></div>
    <div class="card" style="position:absolute;left:984px;right:96px;top:{y + 44}px;padding:20px 26px">
      <h3 style="font-size:24px">If it fails</h3>
      <p style="font-size:20.5px">Before release: keep Salesforce closed and reopen Dynamics inside the written overlap. If Dynamics
      is already gone: run the rehearsed work queue and recover forward from the verified snapshot.</p></div>"""
    return slide(10, weeks + grid + "".join(out) + gates + pause + panels, "Plan",
                 "The Round 1 frame: 12 weeks, Gate 1 in week 2, Gate 2 in week 12")


# ---------- 10. Risks and the fallback ladder ----------
def s10() -> str:
    ladder = ["Use the EUR 14.4k contingency", "Trim optional CRM scope: reports, full history import",
              "PromiseOps drops to a historical replay", "Take the gap to the sponsor"]
    steps = "".join(
        f'<div style="display:flex;gap:18px;align-items:center;margin-left:{i * 34}px;margin-bottom:30px">'
        f'<span class="num">{i + 1}</span><div style="font-size:25px;line-height:1.3">{esc(t)}</div></div>'
        for i, t in enumerate(ladder))
    risks = [
        ("Dynamics switched off before week 10", "Written date at Gate 1. Otherwise only CRM goes ahead, and we recover forward", "CRM owner"),
        ("CRM data or licences exceed the envelope", "Inventory in weeks 1-2, then the fallback order on the left", "Migration lead"),
        ("Shared staff pulled into the cutover", "CRM milestones first; no PromiseOps onboarding in week 9", "Delivery lead"),
        ("Shadow cannot prove savings; the EUR 354k/year case starts later", "Claim nothing until the live phase; report denominators", "Pilot owner"),
    ]
    tr = "".join(f"<tr><td><b>{esc(a)}</b></td><td>{esc(b)}</td><td>{esc(c)}</td></tr>" for a, b, c in risks)
    body = f"""
    <div style="position:absolute;left:96px;top:290px;width:700px">
      <div style="font-size:21px;font-weight:600;letter-spacing:.1em;color:#536371;margin-bottom:22px">IF MONEY RUNS SHORT, WE GIVE UP IN THIS ORDER</div>
      {steps}
      <div style="margin-top:26px;background:#0f3b5f;color:#fff;border-radius:14px;padding:22px 28px;font-size:25px;font-weight:600">
        CRM continuity is never the item we cut.</div>
    </div>
    <div style="position:absolute;left:880px;right:96px;top:290px">
      <table class="big"><thead><tr><th>Risk</th><th>Response</th><th style="width:200px">Owner</th></tr></thead><tbody>{tr}</tbody></table>
    </div>"""
    return slide(11, body, "Risks", "We know what to give up first, and it is never the CRM")


# ---------- 11. The ask ----------
def s11() -> str:
    asks = [
        "Approve EUR 126k as a ceiling with two gates. Release CRM discovery (EUR 16.2k) and the DC validation now.",
        "Name three owners: the Danish country lead, the migration owner and the Swedish DC owner.",
        "Confirm the Dynamics 365 switch-off date in writing before Gate 1.",
        "Agree the shadow thresholds before week 7: 95% usable orders, 70% actionable alerts, 90% owned within 15 minutes.",
    ]
    items = "".join(
        f'<div style="display:flex;gap:24px;align-items:flex-start;margin-bottom:30px"><span class="num">{i + 1}</span>'
        f'<div style="font-size:30px;line-height:1.35">{esc(a)}</div></div>' for i, a in enumerate(asks))
    body = f"""
    <div style="position:absolute;left:96px;top:96px;font-size:22px;letter-spacing:.14em;color:#e7b8e8;font-weight:600">THE DECISION</div>
    <div style="position:absolute;left:96px;top:140px;font-size:72px;font-weight:700;letter-spacing:-.01em">What we ask today</div>
    <div style="position:absolute;left:96px;top:300px;width:1500px">{items}</div>
    <div style="position:absolute;left:96px;top:880px;font-size:36px;font-weight:600;color:#e7b8e8">Continuity now. Proof next. Scale when it is earned.</div>"""
    return slide(12, body, dark=True)


CHECK = """() => {
  const problems = [];
  document.querySelectorAll('.slide').forEach(s => {
    const sr = s.getBoundingClientRect();
    s.querySelectorAll('*').forEach(e => {
      if (e.closest('svg') && e.tagName !== 'svg') return;
      const r = e.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return;
      if (r.right > sr.right + 1 || r.bottom > sr.bottom + 1 || r.left < sr.left - 1 || r.top < sr.top - 1)
        problems.push(s.id + ': outside the slide: ' + (e.textContent || e.tagName).trim().slice(0, 60));
      const style = getComputedStyle(e);
      const clips = style.overflow !== 'visible';
      if ((clips || e.classList.contains('card') || e.classList.contains('box')) &&
          (e.scrollHeight > e.clientHeight + 2 || e.scrollWidth > e.clientWidth + 2) && e.tagName !== 'BODY')
        problems.push(s.id + ': text overflows its box: ' + (e.textContent || '').trim().slice(0, 60));
    });
  });
  return problems;
}"""


def main() -> None:
    slides = [problem_statement(), s1(), s2(), s3(), s4(), s5(), s6(), s7(), s8(), s9(), s10(), s11()]
    doc = (f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><title>PromiseOps Round 3</title>"
           f"<style>{CSS}@page{{size:{W}px {H}px;margin:0}}</style></head><body>{''.join(slides)}</body></html>")
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H})
        pg.set_content(doc)
        pg.evaluate("document.fonts.ready")
        problems = pg.evaluate(CHECK)
        for i in range(1, TOTAL + 1):
            pg.locator(f"#s{i}").screenshot(path=str(PREVIEWS / f"{i:02d}.png"))
        pg.pdf(path=str(OUT), width=f"{W}px", height=f"{H}px", print_background=True)
        b.close()
    print(OUT)
    if problems:
        raise SystemExit("Layout problems:\n" + "\n".join(problems))


if __name__ == "__main__":
    main()

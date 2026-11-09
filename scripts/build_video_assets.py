"""Builds the assets for the MVP video from docs/video/video-script.md.

- docs/video/slides/*.png (1920x1080): title, changes since Round 1, architecture, close
- docs/video/MVP.srt: English subtitles, timed inside each scene of the script

Run: python scripts/build_video_assets.py
"""

from __future__ import annotations

import base64
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "docs" / "video"
SLIDES = VIDEO / "slides"

BASE_CSS = """
*{box-sizing:border-box}html,body{margin:0}
body{width:1920px;height:1080px;font-family:"Segoe UI",system-ui,sans-serif;color:#13202b;background:#f5f6f3;overflow:hidden}
.wrap{position:absolute;inset:0;padding:90px 120px}
.kicker{font-size:24px;letter-spacing:.14em;text-transform:uppercase;color:#536371;font-weight:600}
h1{font-size:64px;line-height:1.1;margin:14px 0 18px;font-weight:700;letter-spacing:-.01em}
h2{font-size:44px;margin:10px 0 30px;font-weight:650}
p{font-size:28px;line-height:1.45;margin:0 0 14px;color:#26343f}
.foot{position:absolute;left:120px;right:120px;bottom:56px;display:flex;justify-content:space-between;font-size:22px;color:#536371}
.course{display:flex;align-items:center;margin:40px 0}
.course i{width:34px;height:34px;border-radius:50%;border:6px solid #a626aa;background:#fff;flex:none}
.course i.p{background:#a626aa}.course i.m{border-color:#c0392b}
.course s{height:7px;background:#a626aa;flex:1}
table{border-collapse:collapse;width:100%;font-size:24px;background:#fff}
th,td{text-align:left;vertical-align:top;padding:16px 20px;border-bottom:1px solid #dfe2dc}
th{font-size:20px;letter-spacing:.06em;text-transform:uppercase;color:#536371;border-bottom:2px solid #13202b}
td b{color:#0f3b5f}
.dark{background:#0f3b5f;color:#fff}.dark p,.dark .kicker,.dark .foot{color:#cfe0ee}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:28px;margin:46px 0}
.stat{background:#174c76;border-radius:12px;padding:26px 28px}
.stat b{display:block;font-size:58px;color:#fff;line-height:1.1}.stat span{font-size:24px;color:#cfe0ee}
"""


def page(body: str, dark: bool = False) -> str:
    return (f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{BASE_CSS}</style></head>"
            f"<body class='{'dark' if dark else ''}'>{body}</body></html>")


def slide_title() -> str:
    return page("""<div class="wrap">
      <div class="kicker">IT Consultant Challenge 2026 · Round 2 · team NgaChainAILayer2</div>
      <h1 style="font-size:110px;margin-top:120px">PromiseOps</h1>
      <p style="font-size:40px;font-style:italic;color:#cfe0ee">Protecting every delivery promise</p>
      <div class="course"><i class="p"></i><s></s><i class="m"></i><s></s><i></i><s></s><i></i></div>
      <p>Functional MVP: detect orders at risk before the cutoff, give each one owner and a deadline,<br>
      record the decision and its cost, and measure the outcome against the original promise.</p>
      <div class="foot"><span>One Swedish DC · two exception rules · fictional data, no Company A data</span><span>Runs locally</span></div>
    </div>""", dark=True)


def slide_changes() -> str:
    rows = [
        ("Alert at pick + 15 min grace",
         "Alert at the milestone, only if the warehouse feed was read after it; the grace is a market setting",
         "The read-after-milestone rule prevents the false alarms the grace was for, and leaves more time to act"),
        ("30-minute stale-feed limit",
         "Same limit, plus the read-after-milestone rule",
         "With the limit alone, a feed outage produced 9 false alarms at minute 30"),
        ("Real order and warehouse feeds",
         "Demo harness: simulated clock and scripted feeds; JSON API for real feeds",
         "No Company A systems or data; the harness replaces only feeds and time, not the engine"),
        ("SSO with role and site access",
         "Demo role switch; API key for integrations",
         "SSO needs Company A's identity provider; planned for the pilot"),
        ("PROVE: action cost logged, cost per outcome",
         "Cost on every expedite; Round 1 scorecard and EUR 25 value, shown as an assumption",
         "Closes the loop to the business case without claiming a measured saving"),
        ("(new)",
         "Timetable view, Vietnamese interface, labelled outcomes API",
         "Time left must be visible at a glance; the team works in Vietnamese; data for the planned risk model"),
    ]
    body = "".join(f"<tr><td>{a}</td><td><b>{b}</b></td><td>{c}</td></tr>" for a, b, c in rows)
    return page(f"""<div class="wrap">
      <div class="kicker">What changed since Round 1, and why</div>
      <h2>Same scope: 1 DC, 2 rules, one owner, escalation, outcome against the original promise, read only, no AI inside</h2>
      <table><tr><th style="width:23%">Round 1 proposal</th><th style="width:40%">In the MVP</th><th>Why</th></tr>{body}</table>
      <div class="foot"><span>PromiseOps MVP · team NgaChainAILayer2</span><span>Round 1 slides 4, 5, 8</span></div>
    </div>""")


def slide_architecture() -> str:
    data = base64.b64encode((ROOT / "docs" / "architecture" / "system-diagram-p2.png").read_bytes()).decode()
    return page(f"""<div class="wrap" style="padding:56px 120px">
      <div class="kicker">Under the hood</div>
      <div style="display:grid;grid-template-columns:1.55fr 1fr;gap:48px;margin-top:22px;align-items:start">
        <img src="data:image/png;base64,{data}" style="width:100%;border:1px solid #dfe2dc;border-radius:10px;background:#fff">
        <div>
          <p><b>One FastAPI service</b>, three layers: web routes, core rules and read models, source integration.</p>
          <p><b>SQLite</b> for zero setup; PostgreSQL in the pilot.</p>
          <p><b>Read only:</b> nothing is written back to order or warehouse systems.</p>
          <p><b>Idempotent ingestion</b> on source + event id, for polled and pushed records alike.</p>
          <p><b>API key</b> for integrations; demo role switch instead of SSO.</p>
          <p><b>46 automated tests</b>: rules, escalation, stale feed, KPIs, HTTP, translations and a real-browser run of this journey.</p>
        </div>
      </div>
    </div>""")


def slide_close() -> str:
    return page("""<div class="wrap">
      <div class="kicker">The closed loop, measured</div>
      <h1 style="color:#fff">Detect early · one owner · explicit decision rights · evidence and cost · outcome against the promise</h1>
      <div class="stats">
        <div class="stat"><b>93.3%</b><span>on time with PromiseOps (demo morning)</span></div>
        <div class="stat"><b>86.7%</b><span>on time when nobody acts (same morning)</span></div>
        <div class="stat"><b>1</b><span>late delivery prevented: SE-1042</span></div>
        <div class="stat"><b>0</b><span>false alarms from the feed outage</span></div>
      </div>
      <p>Next: the 2-week validation (EUR 10k), then the 12-week pilot against control stores, as proposed in Round 1.</p>
      <div class="foot"><span>Thank you · team NgaChainAILayer2</span><span>github.com/HuyVu12/promiseops</span></div>
    </div>""", dark=True)


def build_slides() -> None:
    SLIDES.mkdir(parents=True, exist_ok=True)
    slides = {"1-title": slide_title(), "2-changes": slide_changes(), "3-architecture": slide_architecture(),
              "4-close": slide_close()}
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        for name, html_doc in slides.items():
            pg.set_content(html_doc)
            pg.screenshot(path=str(SLIDES / f"{name}.png"))
        b.close()


def _secs(mmss: str) -> int:
    m, s = mmss.split(":")
    return int(m) * 60 + int(s)


def _stamp(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _chunks(text: str, limit: int = 84) -> list[str]:
    out = []
    for sentence in re.split(r"(?<=[.!?:])\s+", text.strip()):
        words, line = sentence.split(), ""
        for w in words:
            if len(line) + len(w) + 1 > limit and line:
                out.append(line)
                line = w
            else:
                line = f"{line} {w}".strip()
        if line:
            out.append(line)
    return out


def build_srt() -> None:
    script = (VIDEO / "video-script.md").read_text(encoding="utf8")
    cues = []
    for row in re.finditer(r"^\| (\d+) \| (\d+:\d\d)-(\d+:\d\d) \| [^|]+\| (.+?) \|$", script, re.M):
        start, end, narration = _secs(row.group(2)), _secs(row.group(3)), row.group(4)
        parts = _chunks(narration)
        total = sum(len(x) for x in parts)
        t = float(start)
        for part in parts:
            dur = (end - start - 0.05 * len(parts)) * len(part) / total
            cues.append((t, t + dur, part))
            t += dur + 0.05
    lines = []
    for i, (a, b, text) in enumerate(cues, 1):
        lines += [str(i), f"{_stamp(a)} --> {_stamp(b)}", text, ""]
    (VIDEO / "MVP.srt").write_text("\n".join(lines), encoding="utf8")
    print(f"MVP.srt: {len(cues)} cues, ends {_stamp(cues[-1][1])}")


if __name__ == "__main__":
    build_slides()
    build_srt()
    print(SLIDES)

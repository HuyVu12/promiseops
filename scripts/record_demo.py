"""Records an annotated walkthrough of the PromiseOps demo for the landing page.

Drives the real app with Playwright, shows a caption card ("what is happening now") and highlights
each control before it is used. Writes src/promiseops/web/static/landing/demo-<lang>.webm and a poster image.

Run against a separate server so nobody's session is disturbed:
  PROMISEOPS_DB=/tmp/demo.db python -m uvicorn --app-dir src promiseops.web.app:app --port 8766
  python scripts/record_demo.py en http://127.0.0.1:8766
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

LANG = sys.argv[1] if len(sys.argv) > 1 else "en"
BASE = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8766"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "promiseops" / "web" / "static" / "landing"
W, H = 1440, 900

T = {
    "en": {
        "s1": ("09:00 · The timetable", "Every order is a purple course of four controls: pick, cutoff, last viable dispatch, promise. The red line is now."),
        "s2": ("09:30 · Two exceptions", "SE-1042 and SE-1051 passed their pick with no confirmation. 30 minutes before the 10:00 route; the B2B site delivery goes first."),
        "s3": ("Take ownership", "Anna, the DC coordinator, opens SE-1042 and takes it. The 15-minute escalation timer stops."),
        "s4": ("Not her call", "Goods not picked. An expedite spends warehouse capacity, so it is locked for a coordinator."),
        "s5": ("Escalate with the reason", "Anna hands the decision to the shift lead and says what is needed."),
        "s6": ("The shift lead decides", "Erik records the expedite with evidence and its cost. Finance checks the Round 1 assumption against these costs."),
        "s7": ("Everything is attributed", "Who took it, who escalated, who decided, why, and what it cost. Nothing is written back to the warehouse system."),
        "s8": ("A false alarm, with evidence", "SE-1051 was packed at 09:20; the scanner synced late. Recording it tells us how precise the rules are."),
        "s9": ("What if the data goes quiet?", "We simulate a warehouse feed outage and move the clock 45 minutes."),
        "s10": ("Silence proves nothing", "The feed turns red, a data task opens, passed controls show as unknown, and no false alarms are raised."),
        "s11": ("Feed back, real problem found", "The backlog arrives first, then the rules run: SE-1077 is picked but has no vehicle."),
        "s12": ("Handed to customer service", "The promise cannot be kept, so the customer gets a new ETA. The order will still count as late."),
        "s13": ("The afternoon", "SE-1042 was delivered before its 14:00 promise. SE-1077 arrived late and is counted late."),
        "s14": ("Measured against the promise", "On time against the original promise, late deliveries prevented, response time and the Round 1 pilot scorecard."),
        "s15": ("Also in Vietnamese", "The whole interface, including system messages, switches language in one click."),
        "s16": ("That is the closed loop", "Detect early, one owner, explicit decision rights, evidence and cost, outcome against the promise."),
        "esc_note": "Not picked: picker on break. Need a priority pick to make the 10:00 route.",
        "exp_note": "Moved a picker from aisle 3; priority pick, loaded on the 10:30 shuttle.",
        "fa_note": "Picker Jonas: tote packed 09:20, handheld was offline. Scanner ticket raised.",
        "cs_note": "No vehicle until 11:50. Customer service called the site manager with a 14:35 ETA.",
        "step": "Step",
    },
    "vi": {
        "s1": ("09:00 · Lịch trình", "Mỗi đơn là một tuyến tím gồm bốn trạm: lấy hàng, hạn xuất, xuất muộn nhất, cam kết. Vạch đỏ là hiện tại."),
        "s2": ("09:30 · Hai ngoại lệ", "SE-1042 và SE-1051 đã qua mốc lấy hàng mà chưa có xác nhận. Còn 30 phút trước chuyến 10:00; đơn B2B công trình lên trước."),
        "s3": ("Nhận xử lý", "Anna, điều phối viên DC, mở SE-1042 và nhận xử lý. Bộ đếm chuyển cấp 15 phút dừng lại."),
        "s4": ("Không thuộc quyền của cô", "Hàng chưa được lấy. Xử lý gấp tốn năng lực kho nên bị khóa với điều phối viên."),
        "s5": ("Chuyển cấp kèm lý do", "Anna chuyển quyết định cho trưởng ca và ghi rõ cần gì."),
        "s6": ("Trưởng ca quyết định", "Erik ghi nhận xử lý gấp kèm bằng chứng và chi phí. Tài chính đối chiếu giả định Round 1 với các chi phí này."),
        "s7": ("Mọi thao tác đều có người chịu trách nhiệm", "Ai nhận, ai chuyển cấp, ai quyết định, vì sao và tốn bao nhiêu. Không ghi ngược vào hệ thống kho."),
        "s8": ("Cảnh báo sai, có bằng chứng", "SE-1051 đã đóng thùng lúc 09:20, máy quét đồng bộ trễ. Ghi lại giúp đo độ chính xác của quy tắc."),
        "s9": ("Nếu dữ liệu im lặng?", "Giả lập mất nguồn dữ liệu kho và tua đồng hồ 45 phút."),
        "s10": ("Im lặng không chứng minh gì", "Nguồn chuyển đỏ, mở việc dữ liệu, các trạm đã qua hiện là chưa biết, và không có cảnh báo sai."),
        "s11": ("Nguồn trở lại, phát hiện vấn đề thật", "Dữ liệu tồn đọng về trước, rồi quy tắc mới chạy: SE-1077 đã lấy hàng nhưng không có xe."),
        "s12": ("Chuyển cho chăm sóc khách hàng", "Không giữ được cam kết nên khách được báo giờ giao mới. Đơn vẫn bị tính là trễ."),
        "s13": ("Buổi chiều", "SE-1042 giao trước cam kết 14:00. SE-1077 giao trễ và bị tính là trễ."),
        "s14": ("Đo so với cam kết", "Đúng hạn so với cam kết gốc, số đơn trễ đã ngăn được, thời gian phản hồi và bảng điểm pilot Round 1."),
        "s15": ("Có cả tiếng Anh", "Toàn bộ giao diện, kể cả thông báo hệ thống, đổi ngôn ngữ chỉ với một lần bấm."),
        "s16": ("Đó là vòng xử lý khép kín", "Phát hiện sớm, một người phụ trách, quyền quyết định rõ ràng, có bằng chứng và chi phí, đo so với cam kết."),
        "esc_note": "Chưa lấy hàng: nhân viên đang nghỉ. Cần lấy gấp cho kịp chuyến 10:00.",
        "exp_note": "Điều một nhân viên từ dãy 3 sang; lấy gấp, xếp lên chuyến 10:30.",
        "fa_note": "Nhân viên Jonas: đã đóng thùng 09:20, máy quét mất kết nối. Đã báo lỗi máy quét.",
        "cs_note": "Không có xe tới 11:50. Chăm sóc khách hàng đã báo quản lý công trình giờ giao mới 14:35.",
        "step": "Bước",
    },
}[LANG]

OVERLAY = """
(() => {
  const css = `#demo-cap{position:fixed;left:12px;top:548px;width:228px;z-index:9999;
    background:#ffd27a;color:#13202b;border-radius:10px;padding:12px 14px 14px;box-shadow:0 8px 24px rgba(0,0,0,.28);
    font:13.5px/1.45 "Segoe UI",system-ui,sans-serif;transition:opacity .25s ease-out}
  #demo-cap .k{font-size:11.5px;letter-spacing:.06em;text-transform:uppercase;color:#0f3b5f;font-weight:700}
  #demo-cap b{display:block;font-size:16.5px;line-height:1.25;margin:3px 0 5px}
  .demo-hl{outline:3px solid #f0a500!important;outline-offset:3px!important;border-radius:6px;transition:outline-color .2s}`;
  function render(){
    const d = sessionStorage.getItem('demoCap'); if(!d) return;
    const c = JSON.parse(d);
    let el = document.getElementById('demo-cap');
    if(!el){ const s=document.createElement('style'); s.textContent=css; document.head.appendChild(s);
      el=document.createElement('div'); el.id='demo-cap'; document.body.appendChild(el); }
    el.innerHTML = `<div class="k">${c.k}</div><b>${c.t}</b><div>${c.d}</div>`;
  }
  window.__demoRender = render;
  if (document.readyState !== 'loading') render(); else document.addEventListener('DOMContentLoaded', render);
})();
"""


def caption(pg: Page, n: int, key: str, total: int = 16, wait: float = 3.2) -> None:
    title, desc = T[key]
    pg.evaluate("([k,t,d]) => { sessionStorage.setItem('demoCap', JSON.stringify({k,t,d})); window.__demoRender && window.__demoRender(); }",
                [f"{T['step']} {n}/{total}", title, desc])
    pg.wait_for_timeout(int(wait * 1000))


def hl(pg: Page, sel: str, ms: int = 900) -> None:
    pg.locator(sel).first.scroll_into_view_if_needed()
    pg.eval_on_selector(sel, "e => e.classList.add('demo-hl')")
    pg.wait_for_timeout(ms)


def click(pg: Page, sel: str, ms: int = 900) -> None:
    hl(pg, sel, ms)
    with pg.expect_navigation():
        pg.click(sel)
    pg.wait_for_timeout(500)


def type_into(pg: Page, sel: str, text: str) -> None:
    hl(pg, sel, 500)
    pg.click(sel)
    pg.keyboard.type(text, delay=22)
    pg.wait_for_timeout(400)


def main() -> None:
    tmp = Path(tempfile.mkdtemp())
    total = 16
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": W, "height": H}, record_video_dir=str(tmp), record_video_size={"width": W, "height": H})
        ctx.add_init_script(OVERLAY)
        pg = ctx.new_page()
        pg.on("dialog", lambda d: d.accept())
        other = "vi" if LANG == "en" else "en"
        # Prepare: reset scenario and role before the visible part starts.
        pg.goto(f"{BASE}/app?lang={LANG}")
        with pg.expect_navigation():
            pg.click("[data-testid=reset]")
        with pg.expect_navigation():
            pg.select_option("[data-testid=role]", "coordinator")
        pg.goto(f"{BASE}/app")
        caption(pg, 1, "s1", total, wait=4.5)
        click(pg, "[data-testid=adv-30]")
        caption(pg, 2, "s2", total, wait=4.5)
        # SE-1042: own, escalate, expedite with cost.
        click(pg, "[data-testid=row-SE-1042] a.order-link")
        click(pg, "[data-testid=ack]")
        caption(pg, 3, "s3", total, wait=3.0)
        hl(pg, "label.choice.disabled", 600)
        caption(pg, 4, "s4", total, wait=3.5)
        type_into(pg, "[data-testid=esc-note]", T["esc_note"])
        caption(pg, 5, "s5", total, wait=2.0)
        click(pg, "[data-testid=escalate]")
        hl(pg, "[data-testid=role]", 700)
        with pg.expect_navigation():
            pg.select_option("[data-testid=role]", "shift_lead")
        hl(pg, "[data-testid=res-expedited]", 600)
        pg.check("[data-testid=res-expedited]")
        type_into(pg, "[data-testid=resolve-note]", T["exp_note"])
        type_into(pg, "[data-testid=resolve-cost]", "10")
        caption(pg, 6, "s6", total, wait=3.5)
        click(pg, "[data-testid=resolve]")
        pg.locator("[data-testid=log]").scroll_into_view_if_needed()
        caption(pg, 7, "s7", total, wait=4.5)
        with pg.expect_navigation():
            pg.select_option("[data-testid=role]", "coordinator")
        # SE-1051: false alarm.
        pg.goto(f"{BASE}/app")
        click(pg, "[data-testid=row-SE-1051] a.order-link")
        click(pg, "[data-testid=ack]")
        hl(pg, "[data-testid=res-false_alarm]", 500)
        pg.check("[data-testid=res-false_alarm]")
        type_into(pg, "[data-testid=resolve-note]", T["fa_note"])
        caption(pg, 8, "s8", total, wait=3.0)
        click(pg, "[data-testid=resolve]")
        # Feed outage and recovery.
        pg.goto(f"{BASE}/app")
        caption(pg, 9, "s9", total, wait=2.5)
        click(pg, "[data-testid=feed-pause]")
        click(pg, "[data-testid=adv-30]", 500)
        click(pg, "[data-testid=adv-15]", 500)
        hl(pg, "[data-testid=stale-banner]", 300)
        caption(pg, 10, "s10", total, wait=5.0)
        click(pg, "[data-testid=feed-resume]")
        click(pg, "[data-testid=adv-5]", 500)
        hl(pg, "[data-testid=row-SE-1077]", 300)
        caption(pg, 11, "s11", total, wait=4.0)
        # SE-1077: handed to customer service.
        click(pg, "[data-testid=row-SE-1077] a.order-link")
        click(pg, "[data-testid=ack]")
        pg.check("[data-testid=res-customer_notified]")
        type_into(pg, "[data-testid=resolve-note]", T["cs_note"])
        caption(pg, 12, "s12", total, wait=2.5)
        click(pg, "[data-testid=resolve]")
        # Afternoon and outcomes.
        pg.goto(f"{BASE}/orders")
        click(pg, "[data-testid=adv-300]")
        hl(pg, "[data-testid=order-SE-1042]", 400)
        caption(pg, 13, "s13", total, wait=5.0)
        pg.goto(f"{BASE}/kpi")
        caption(pg, 14, "s14", total, wait=5.5)
        hl(pg, "[data-testid=lang]", 600)
        with pg.expect_navigation():
            pg.select_option("[data-testid=lang]", other)
        caption(pg, 15, "s15", total, wait=3.0)
        with pg.expect_navigation():
            pg.select_option("[data-testid=lang]", LANG)
        pg.goto(f"{BASE}/app")
        caption(pg, 16, "s16", total, wait=4.5)
        pg.screenshot(path=str(OUT / f"demo-{LANG}-poster.png"))
        video = pg.video.path()
        ctx.close()
        b.close()
    shutil.move(str(video), OUT / f"demo-{LANG}.webm")
    shutil.rmtree(tmp, ignore_errors=True)
    print(OUT / f"demo-{LANG}.webm")


if __name__ == "__main__":
    main()

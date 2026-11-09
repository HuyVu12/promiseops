"""PromiseOps web application: exception queue for protecting delivery promises."""

from __future__ import annotations

import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Iterator
from urllib.parse import quote

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from promiseops.core import engine, kpi, timetable, workflow
from promiseops.integration import ingest, simulation
from promiseops.storage import db, seed
from promiseops.web import i18n
from promiseops import timeutil as tu
from promiseops.config import EXCEPTION_TYPES, FULFILMENT_SOURCE, MARKETS, RESOLUTION_ROLES, RESOLUTIONS, ROLES

BASE = Path(__file__).resolve().parent
PROJECT_ROOT = BASE.parents[2]
DB_PATH = Path(os.environ.get("PROMISEOPS_DB", PROJECT_ROOT / "var" / "promiseops.db"))
CFG = MARKETS["SE"]


def _ensure_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = db.connect(DB_PATH)
    try:
        db.init(conn)
        if db.get_meta(conn, simulation.CLOCK_KEY) is None:
            seed.seed(conn)
    finally:
        conn.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    _ensure_db()
    yield


app = FastAPI(title="PromiseOps", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")
templates.env.filters["local"] = lambda v, fmt="%H:%M": tu.local(v, CFG.tz, fmt)
templates.env.filters["mins"] = tu.fmt_minutes
templates.env.globals.update(
    EXCEPTION_TYPES=EXCEPTION_TYPES, RESOLUTIONS=RESOLUTIONS, ROLES=ROLES, CFG=CFG,
)


def get_conn() -> Iterator[sqlite3.Connection]:
    conn = db.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def get_role(request: Request) -> str:
    role = request.cookies.get("role", "coordinator")
    return role if role in ROLES else "coordinator"


def back(path: str, *, msg: str | None = None, error: str | None = None) -> RedirectResponse:
    sep = "&" if "?" in path else "?"
    if error:
        path += f"{sep}error={quote(error)}"
    elif msg:
        path += f"{sep}msg={quote(msg)}"
    return RedirectResponse(path, status_code=303)


def _freshness(conn: sqlite3.Connection, now) -> list[dict]:
    out = []
    for s in conn.execute("SELECT * FROM sources ORDER BY id").fetchall():
        age = engine.source_age_min(conn, s["id"], now)
        out.append({
            "id": s["id"], "name": s["name"], "age": age, "paused": bool(s["paused"]),
            "stale": age is None or age > CFG.stale_after_min,
        })
    return out


def _lang(request: Request) -> str:
    return i18n.pick(request.query_params.get("lang") or request.cookies.get("lang"))


def _page(request: Request, template: str, ctx: dict) -> HTMLResponse:
    """Render with the reader's language; a ?lang= choice is remembered in a cookie."""
    lang = _lang(request)
    tr = lambda text, **kw: i18n.translate(text, lang, **kw)  # noqa: E731
    resp = templates.TemplateResponse(request, template, {**ctx, "_": tr, "lang": lang, "LANGS": i18n.LANGS})
    if request.query_params.get("lang") == lang:
        resp.set_cookie("lang", lang, httponly=True, samesite="lax", max_age=365 * 24 * 3600)
    return resp


def render(request: Request, conn: sqlite3.Connection, template: str, active: str, **ctx) -> HTMLResponse:
    now = simulation.now(conn)
    role = get_role(request)
    open_count = conn.execute("SELECT COUNT(*) AS n FROM exceptions WHERE status != 'RESOLVED'").fetchone()["n"]
    mine = conn.execute(
        "SELECT COUNT(*) AS n FROM exceptions WHERE status != 'RESOLVED' AND owner_role = ?", (role,)
    ).fetchone()["n"]
    base = {
        "now": now, "now_iso": tu.iso(now), "role": role, "actor": workflow.actor_name(role),
        "active": active, "freshness": _freshness(conn, now), "open_count": open_count, "mine": mine,
        "msg": request.query_params.get("msg"), "error": request.query_params.get("error"),
        "stale_task": conn.execute(
            "SELECT * FROM data_tasks WHERE source = ? AND closed_at IS NULL", (FULFILMENT_SOURCE,)
        ).fetchone(),
    }
    base["day"] = i18n.day_label(now, CFG.tz, _lang(request))
    return _page(request, template, {**base, **ctx})


def _queue_rows(conn: sqlite3.Connection, now, where: str, params: tuple = ()) -> list[dict]:
    rows = conn.execute(
        "SELECT x.*, o.store, o.customer_type, o.promised_at FROM exceptions x JOIN orders o ON o.id = x.order_id "
        f"WHERE {where}", params,
    ).fetchall()
    out = []
    for r in rows:
        remaining = tu.minutes_between(now, tu.parse(r["intervention_deadline"]))
        ack_left = tu.minutes_between(now, tu.parse(r["ack_due_at"]))
        out.append({**dict(r), "remaining": remaining, "ack_left": ack_left})
    # Priority: least time left to intervene first; ties go to B2B (agreed service impact).
    out.sort(key=lambda r: (r["remaining"], 0 if r["customer_type"] == "B2B" else 1, r["id"]))
    return out


def _board(conn: sqlite3.Connection, now) -> tuple[timetable.Axis, dict]:
    orders = conn.execute("SELECT * FROM orders").fetchall()
    axis = timetable.build_axis(orders, now, CFG.tz)
    escalated = {
        r["order_id"] for r in conn.execute("SELECT order_id FROM exceptions WHERE status != 'RESOLVED' AND escalated = 1")
    }
    courses = {
        o["id"]: timetable.course(o, timetable.events_by_type(conn, o["id"]), now, axis, o["id"] in escalated)
        for o in orders
    }
    return axis, courses


# ---------- Pages ----------

@app.get("/", response_class=HTMLResponse)
def landing(request: Request):
    return _page(request, "landing.html", {})


@app.get("/app", response_class=HTMLResponse)
def queue(request: Request, view: str = "all", conn: sqlite3.Connection = Depends(get_conn)):
    now = simulation.now(conn)
    role = get_role(request)
    if view == "mine":
        rows = _queue_rows(conn, now, "x.status != 'RESOLVED' AND x.owner_role = ?", (role,))
    else:
        view = "all"
        rows = _queue_rows(conn, now, "x.status != 'RESOLVED'")
    recent = conn.execute(
        "SELECT x.*, o.store FROM exceptions x JOIN orders o ON o.id = x.order_id "
        "WHERE x.status = 'RESOLVED' ORDER BY x.resolved_at DESC LIMIT 6"
    ).fetchall()
    axis, courses = _board(conn, now)
    open_ids = {r["order_id"] for r in _queue_rows(conn, now, "x.status != 'RESOLVED'")}
    others = conn.execute("SELECT * FROM orders ORDER BY dispatch_cutoff_at, id").fetchall()
    on_course = [o for o in others if o["id"] not in open_ids]
    # Still running first (next control soonest), delivered orders last.
    on_course.sort(key=lambda o: (courses[o["id"]]["delivered"] is not None, (courses[o["id"]]["next"] or {}).get("due", "")))
    return render(
        request, conn, "queue.html", "queue", rows=rows, recent=recent, view=view,
        axis=axis, courses=courses, on_course=on_course, now_pct=axis.pct(now),
    )


@app.get("/exceptions/{exception_id}", response_class=HTMLResponse)
def exception_detail(request: Request, exception_id: int, conn: sqlite3.Connection = Depends(get_conn)):
    now = simulation.now(conn)
    x = conn.execute("SELECT * FROM exceptions WHERE id = ?", (exception_id,)).fetchone()
    if not x:
        raise HTTPException(404, "Exception not found")
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (x["order_id"],)).fetchone()
    events = conn.execute(
        "SELECT * FROM events WHERE order_id = ? ORDER BY occurred_at", (x["order_id"],)
    ).fetchall()
    log = conn.execute("SELECT * FROM audit_log WHERE exception_id = ? ORDER BY id", (exception_id,)).fetchall()
    others = conn.execute(
        "SELECT * FROM exceptions WHERE order_id = ? AND id != ?", (x["order_id"], exception_id)
    ).fetchall()
    role = get_role(request)
    allowed = [k for k, roles in RESOLUTION_ROLES.items() if role in roles]
    milestones = [
        ("Pick due", order["pick_due_at"], "PICK_CONFIRMED"),
        ("Dispatch cutoff", order["dispatch_cutoff_at"], "DISPATCHED"),
        ("Last viable dispatch", order["latest_dispatch_at"], None),
        ("Promised delivery", order["promised_at"], "DELIVERED"),
    ]
    done = {e["type"]: e["occurred_at"] for e in events}
    axis = timetable.build_axis([order], now, CFG.tz)
    crs = timetable.course(order, timetable.events_by_type(conn, order["id"]), now, axis,
                           escalated=bool(x["escalated"]) and x["status"] != "RESOLVED")
    return render(
        request, conn, "exception.html", "queue", x=x, order=order, events=events, log=log, others=others,
        axis=axis, crs=crs, now_pct=axis.pct(now),
        remaining=tu.minutes_between(now, tu.parse(x["intervention_deadline"])),
        ack_left=tu.minutes_between(now, tu.parse(x["ack_due_at"])),
        allowed=allowed, milestones=milestones, done=done,
    )


@app.get("/orders", response_class=HTMLResponse)
def orders(request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    rows = conn.execute(
        "SELECT o.*, "
        "(SELECT MIN(occurred_at) FROM events e WHERE e.order_id = o.id AND e.type = 'PICK_CONFIRMED') AS picked_at, "
        "(SELECT MIN(occurred_at) FROM events e WHERE e.order_id = o.id AND e.type = 'DISPATCHED') AS dispatched_at, "
        "(SELECT MIN(occurred_at) FROM events e WHERE e.order_id = o.id AND e.type = 'DELIVERED') AS delivered_at, "
        "(SELECT GROUP_CONCAT(id || ':' || type || ':' || status) FROM exceptions x WHERE x.order_id = o.id) AS exc "
        "FROM orders o ORDER BY o.dispatch_cutoff_at, o.id"
    ).fetchall()
    parsed = []
    for r in rows:
        excs = []
        for item in (r["exc"] or "").split(","):
            if item:
                xid, xtype, xstatus = item.split(":")
                excs.append({"id": int(xid), "type": xtype, "status": xstatus})
        parsed.append({**dict(r), "excs": excs})
    axis, courses = _board(conn, simulation.now(conn))
    return render(request, conn, "orders.html", "orders", rows=parsed, axis=axis, courses=courses,
                  now_pct=axis.pct(simulation.now(conn)))


@app.get("/kpi", response_class=HTMLResponse)
def kpi_page(request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    k = kpi.compute(conn, simulation.now(conn))
    margins = []
    for o in conn.execute(
        "SELECT o.id, o.customer_type, o.promised_at, MIN(e.occurred_at) AS delivered_at FROM orders o "
        "JOIN events e ON e.order_id = o.id AND e.type = 'DELIVERED' GROUP BY o.id"
    ):
        margins.append({
            "id": o["id"], "type": o["customer_type"],
            "min": tu.minutes_between(tu.parse(o["delivered_at"]), tu.parse(o["promised_at"])),
        })
    lo = min([-60] + [m["min"] for m in margins])
    hi = max([120] + [m["min"] for m in margins])
    for m in margins:
        m["pct"] = round((m["min"] - lo) / (hi - lo) * 100, 2)
    zero_pct = round((0 - lo) / (hi - lo) * 100, 2)
    return render(request, conn, "kpi.html", "kpi", k=k, margins=margins, zero_pct=zero_pct, lo=lo, hi=hi)


@app.get("/data", response_class=HTMLResponse)
def data_page(request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    tasks = conn.execute("SELECT * FROM data_tasks ORDER BY id DESC").fetchall()
    log = conn.execute("SELECT * FROM ingest_log ORDER BY id DESC LIMIT 40").fetchall()
    counts = {
        r["outcome"]: r["n"]
        for r in conn.execute("SELECT outcome, COUNT(*) AS n FROM ingest_log GROUP BY outcome")
    }
    system = conn.execute(
        "SELECT * FROM audit_log WHERE exception_id IS NULL ORDER BY id DESC LIMIT 12"
    ).fetchall()
    return render(request, conn, "data.html", "data", tasks=tasks, log=log, counts=counts, system=system)


# ---------- Human actions ----------

def _act(path: str, fn) -> RedirectResponse:
    try:
        fn()
    except workflow.ActionError as exc:
        return back(path, error=str(exc))
    return back(path, msg="Saved")


@app.post("/exceptions/{exception_id}/ack")
def ack(request: Request, exception_id: int, conn: sqlite3.Connection = Depends(get_conn)):
    now = simulation.now(conn)
    return _act(f"/exceptions/{exception_id}", lambda: workflow.acknowledge(conn, exception_id, get_role(request), now))


@app.post("/exceptions/{exception_id}/escalate")
def escalate(request: Request, exception_id: int, note: str = Form(""), conn: sqlite3.Connection = Depends(get_conn)):
    now = simulation.now(conn)
    return _act(f"/exceptions/{exception_id}", lambda: workflow.escalate(conn, exception_id, get_role(request), note, now))


@app.post("/exceptions/{exception_id}/note")
def note(request: Request, exception_id: int, note: str = Form(""), conn: sqlite3.Connection = Depends(get_conn)):
    now = simulation.now(conn)
    return _act(f"/exceptions/{exception_id}", lambda: workflow.add_note(conn, exception_id, get_role(request), note, now))


@app.post("/exceptions/{exception_id}/resolve")
def resolve(
    request: Request, exception_id: int, resolution: str = Form(""), note: str = Form(""),
    conn: sqlite3.Connection = Depends(get_conn),
):
    now = simulation.now(conn)
    return _act(
        f"/exceptions/{exception_id}",
        lambda: workflow.resolve(conn, exception_id, get_role(request), resolution, note, now),
    )


@app.post("/role")
def set_role(role: str = Form(...), next: str = Form("/app")):
    if role not in ROLES:
        raise HTTPException(400, "Unknown role")
    target = next if next.startswith("/") and not next.startswith("//") else "/app"
    resp = RedirectResponse(target.split("?")[0], status_code=303)
    resp.set_cookie("role", role, httponly=True, samesite="lax")
    return resp


# ---------- Demo controls (simulation only) ----------

def _safe_next(next: str) -> str:
    return next.split("?")[0] if next.startswith("/") and not next.startswith("//") else "/app"


@app.post("/sim/advance")
def sim_advance(minutes: int = Form(...), next: str = Form("/app"), conn: sqlite3.Connection = Depends(get_conn)):
    try:
        t = simulation.advance(conn, minutes)
    except ValueError as exc:
        return back(_safe_next(next), error=str(exc))
    return back(_safe_next(next), msg=f"Clock moved to {tu.local(t, CFG.tz)}")


@app.post("/sim/feed")
def sim_feed(action: str = Form(...), next: str = Form("/app"), conn: sqlite3.Connection = Depends(get_conn)):
    simulation.set_paused(conn, FULFILMENT_SOURCE, action == "pause")
    return back(_safe_next(next), msg="Fulfilment feed paused" if action == "pause" else "Fulfilment feed resumed")


@app.post("/sim/reset")
def sim_reset(conn: sqlite3.Connection = Depends(get_conn)):
    seed.seed(conn)
    return back("/app", msg="Scenario reset to 09:00")


# ---------- JSON API for source integrations ----------

class EventIn(BaseModel):
    source: str
    event_id: str
    order_id: str
    type: str
    occurred_at: str


class OrderIn(BaseModel):
    id: str
    market: str
    dc: str
    store: str
    customer_type: str
    customer_ref: str
    promised_at: str
    pick_due_at: str
    dispatch_cutoff_at: str
    latest_dispatch_at: str


@app.post("/api/events")
def api_event(event: EventIn, conn: sqlite3.Connection = Depends(get_conn)):
    now = simulation.now(conn)
    result = ingest.ingest_event(conn, now=now, **event.model_dump())
    conn.commit()
    if result.outcome == "accepted":
        engine.run(conn, now)
    status = 422 if result.outcome == "rejected" else 200
    if status != 200:
        raise HTTPException(status, result.detail)
    return {"outcome": result.outcome, "detail": result.detail}


@app.post("/api/orders")
def api_order(order: OrderIn, conn: sqlite3.Connection = Depends(get_conn)):
    now = simulation.now(conn)
    result = ingest.ingest_order(conn, order.model_dump(), now)
    conn.commit()
    if result.outcome == "rejected":
        raise HTTPException(422, result.detail)
    engine.run(conn, now)
    return {"outcome": result.outcome, "detail": result.detail}


@app.get("/api/exceptions")
def api_exceptions(conn: sqlite3.Connection = Depends(get_conn)):
    now = simulation.now(conn)
    return {"now": tu.iso(now), "open": _queue_rows(conn, now, "x.status != 'RESOLVED'")}


@app.get("/api/health")
def health(conn: sqlite3.Connection = Depends(get_conn)):
    now = simulation.now(conn)
    return {"status": "ok", "now": tu.iso(now), "sources": _freshness(conn, now)}

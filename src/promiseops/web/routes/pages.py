"""Read-only pages: landing, exception queue, exception detail, orders, outcomes, data health."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from promiseops.config import RESOLUTION_ROLES
from promiseops.core import kpi, queries
from promiseops.integration import simulation
from promiseops.web.deps import CFG, get_conn, get_role, page, render

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def landing(request: Request):
    return page(request, "landing.html", {})


@router.get("/app", response_class=HTMLResponse)
def queue(request: Request, view: str = "all", conn: sqlite3.Connection = Depends(get_conn)):
    now = simulation.now(conn)
    role = get_role(request)
    view = "mine" if view == "mine" else "all"
    all_open = queries.queue_rows(conn, now)
    rows = queries.queue_rows(conn, now, role) if view == "mine" else all_open
    axis, courses, orders = queries.board(conn, now, CFG)
    on_course = queries.on_course(orders, courses, {r["order_id"] for r in all_open})
    return render(
        request, conn, "queue.html", "queue", rows=rows, view=view, recent=queries.recently_closed(conn),
        axis=axis, courses=courses, on_course=on_course, now_pct=axis.pct(now),
    )


@router.get("/exceptions/{exception_id}", response_class=HTMLResponse)
def exception_detail(request: Request, exception_id: int, conn: sqlite3.Connection = Depends(get_conn)):
    detail = queries.exception_detail(conn, exception_id, simulation.now(conn), CFG)
    if detail is None:
        raise HTTPException(404, "Exception not found")
    role = get_role(request)
    allowed = [k for k, roles in RESOLUTION_ROLES.items() if role in roles]
    return render(request, conn, "exception.html", "queue", allowed=allowed, **detail)


@router.get("/orders", response_class=HTMLResponse)
def orders(request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    now = simulation.now(conn)
    axis, courses, _ = queries.board(conn, now, CFG)
    results = {o["id"]: o["result"] for o in kpi.order_results(conn, now)}
    return render(
        request, conn, "orders.html", "orders", rows=queries.orders_listing(conn), axis=axis, courses=courses,
        results=results, now_pct=axis.pct(now),
    )


@router.get("/kpi", response_class=HTMLResponse)
def outcomes(request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    now = simulation.now(conn)
    return render(request, conn, "kpi.html", "kpi", k=kpi.compute(conn, now), m=kpi.margins(conn, now))


@router.get("/data", response_class=HTMLResponse)
def data_health(request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    return render(request, conn, "data.html", "data", **queries.data_health(conn))

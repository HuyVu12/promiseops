"""Read models for the screens and the JSON API. Pure reads; no rule or workflow logic lives here."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from promiseops import timeutil as tu
from promiseops.config import FULFILMENT_SOURCE, MarketConfig
from promiseops.core import engine, timetable


def freshness(conn: sqlite3.Connection, now: datetime, cfg: MarketConfig) -> list[dict]:
    out = []
    for s in conn.execute("SELECT * FROM sources ORDER BY id").fetchall():
        age = engine.source_age_min(conn, s["id"], now)
        out.append({
            "id": s["id"], "name": s["name"], "age": age, "paused": bool(s["paused"]),
            "stale": age is None or age > cfg.stale_after_min,
        })
    return out


def open_stale_task(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM data_tasks WHERE source = ? AND closed_at IS NULL", (FULFILMENT_SOURCE,)
    ).fetchone()


def counts(conn: sqlite3.Connection, role: str) -> tuple[int, int]:
    """Open exceptions in total, and those owned by the given role."""
    row = conn.execute(
        "SELECT COUNT(*) AS n, SUM(CASE WHEN owner_role = ? THEN 1 ELSE 0 END) AS mine "
        "FROM exceptions WHERE status != 'RESOLVED'", (role,),
    ).fetchone()
    return row["n"], row["mine"] or 0


def queue_rows(conn: sqlite3.Connection, now: datetime, role: str | None = None) -> list[dict]:
    """Open exceptions in priority order: least time left to intervene first, ties to B2B (Round 1 rule)."""
    sql = (
        "SELECT x.*, o.store, o.customer_type, o.promised_at FROM exceptions x JOIN orders o ON o.id = x.order_id "
        "WHERE x.status != 'RESOLVED'"
    )
    params: tuple = ()
    if role:
        sql += " AND x.owner_role = ?"
        params = (role,)
    out = []
    for r in conn.execute(sql, params).fetchall():
        out.append({
            **dict(r),
            "remaining": tu.minutes_between(now, tu.parse(r["intervention_deadline"])),
            "ack_left": tu.minutes_between(now, tu.parse(r["ack_due_at"])),
        })
    out.sort(key=lambda r: (r["remaining"], 0 if r["customer_type"] == "B2B" else 1, r["order_id"]))
    return out


def recently_closed(conn: sqlite3.Connection, limit: int = 6) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT x.*, o.store FROM exceptions x JOIN orders o ON o.id = x.order_id "
        "WHERE x.status = 'RESOLVED' ORDER BY x.resolved_at DESC, x.id DESC LIMIT ?", (limit,),
    ).fetchall()


def board(conn: sqlite3.Connection, now: datetime, cfg: MarketConfig) -> tuple[timetable.Axis, dict, list[sqlite3.Row]]:
    """The shared time axis and every order's course."""
    orders = conn.execute("SELECT * FROM orders ORDER BY dispatch_cutoff_at, id").fetchall()
    axis = timetable.build_axis(orders, now, cfg.tz)
    escalated = {
        r["order_id"] for r in conn.execute(
            "SELECT order_id FROM exceptions WHERE status != 'RESOLVED' AND escalated = 1"
        )
    }
    read_until = engine.source_read_at(conn, FULFILMENT_SOURCE)
    courses = {
        o["id"]: timetable.course(o, timetable.events_by_type(conn, o["id"]), now, axis, o["id"] in escalated,
                                  read_until=read_until)
        for o in orders
    }
    return axis, courses, orders


def on_course(orders: list[sqlite3.Row], courses: dict, open_order_ids: set[str]) -> list[sqlite3.Row]:
    """Orders without an open exception: still running first (next control soonest), delivered last."""
    rows = [o for o in orders if o["id"] not in open_order_ids]
    rows.sort(key=lambda o: (courses[o["id"]]["delivered"] is not None, (courses[o["id"]]["next"] or {}).get("due", "")))
    return rows


def orders_listing(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT o.*, "
        "(SELECT MIN(occurred_at) FROM events e WHERE e.order_id = o.id AND e.type = 'DISPATCHED') AS dispatched_at "
        "FROM orders o ORDER BY o.dispatch_cutoff_at, o.id"
    ).fetchall()
    excs: dict[str, list[dict]] = {}
    for x in conn.execute("SELECT id, order_id, type, status, resolution FROM exceptions ORDER BY id"):
        excs.setdefault(x["order_id"], []).append(dict(x))
    return [{**dict(r), "excs": excs.get(r["id"], [])} for r in rows]


def exception_detail(conn: sqlite3.Connection, exception_id: int, now: datetime, cfg: MarketConfig) -> dict | None:
    x = conn.execute("SELECT * FROM exceptions WHERE id = ?", (exception_id,)).fetchone()
    if not x:
        return None
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (x["order_id"],)).fetchone()
    events = conn.execute("SELECT * FROM events WHERE order_id = ? ORDER BY occurred_at", (x["order_id"],)).fetchall()
    log = conn.execute("SELECT * FROM audit_log WHERE exception_id = ? ORDER BY id", (exception_id,)).fetchall()
    others = conn.execute("SELECT * FROM exceptions WHERE order_id = ? AND id != ?", (x["order_id"], exception_id)).fetchall()
    axis = timetable.build_axis([order], now, cfg.tz)
    crs = timetable.course(order, timetable.events_by_type(conn, order["id"]), now, axis,
                           escalated=bool(x["escalated"]) and x["status"] != "RESOLVED",
                           read_until=engine.source_read_at(conn, FULFILMENT_SOURCE))
    return {
        "x": x, "order": order, "events": events, "log": log, "others": others,
        "axis": axis, "crs": crs, "now_pct": axis.pct(now),
        "remaining": tu.minutes_between(now, tu.parse(x["intervention_deadline"])),
        "ack_left": tu.minutes_between(now, tu.parse(x["ack_due_at"])),
    }


def data_health(conn: sqlite3.Connection) -> dict:
    return {
        "tasks": conn.execute("SELECT * FROM data_tasks ORDER BY id DESC").fetchall(),
        "log": conn.execute("SELECT * FROM ingest_log ORDER BY id DESC LIMIT 40").fetchall(),
        "counts": {
            r["outcome"]: r["n"]
            for r in conn.execute("SELECT outcome, COUNT(*) AS n FROM ingest_log GROUP BY outcome")
        },
        "system": conn.execute(
            "SELECT * FROM audit_log WHERE exception_id IS NULL ORDER BY id DESC LIMIT 12"
        ).fetchall(),
    }

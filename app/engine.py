"""Exception rules, data-freshness guard and escalation. Deterministic and explainable by design."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from . import timeutil as tu
from .config import EXCEPTION_TYPES, FULFILMENT_SOURCE, MARKETS, MarketConfig

SYSTEM = "PromiseOps"


def audit(conn: sqlite3.Connection, exception_id: int | None, now: datetime, actor: str, action: str, note: str = "") -> None:
    conn.execute(
        "INSERT INTO audit_log(exception_id, at, actor, action, note) VALUES (?, ?, ?, ?, ?)",
        (exception_id, tu.iso(now), actor, action, note),
    )


def source_age_min(conn: sqlite3.Connection, source: str, now: datetime) -> int | None:
    row = conn.execute("SELECT last_received_at FROM sources WHERE id = ?", (source,)).fetchone()
    if not row or not row["last_received_at"]:
        return None
    return tu.minutes_between(tu.parse(row["last_received_at"]), now)


def is_stale(conn: sqlite3.Connection, source: str, now: datetime, cfg: MarketConfig) -> bool:
    age = source_age_min(conn, source, now)
    return age is None or age > cfg.stale_after_min


def _has_event(conn: sqlite3.Connection, order_id: str, type_: str) -> str | None:
    row = conn.execute(
        "SELECT MIN(occurred_at) AS t FROM events WHERE order_id = ? AND type = ?", (order_id, type_)
    ).fetchone()
    return row["t"]


def _guard_freshness(conn: sqlite3.Connection, now: datetime, cfg: MarketConfig) -> bool:
    """Returns True when absence-based rules may run. Opens or closes a data task as needed."""
    stale = is_stale(conn, FULFILMENT_SOURCE, now, cfg)
    open_task = conn.execute(
        "SELECT id FROM data_tasks WHERE source = ? AND closed_at IS NULL", (FULFILMENT_SOURCE,)
    ).fetchone()
    if stale and not open_task:
        age = source_age_min(conn, FULFILMENT_SOURCE, now)
        conn.execute(
            "INSERT INTO data_tasks(source, owner, opened_at, note) VALUES (?, ?, ?, ?)",
            (
                FULFILMENT_SOURCE, cfg.data_owner, tu.iso(now),
                f"No fulfilment data for {age} min (limit {cfg.stale_after_min}). "
                "Missing-event alerts paused to avoid false alarms.",
            ),
        )
        audit(conn, None, now, SYSTEM, "DATA_STALE", "Fulfilment feed stale, absence-based alerts paused")
    elif not stale and open_task:
        conn.execute("UPDATE data_tasks SET closed_at = ? WHERE id = ?", (tu.iso(now), open_task["id"]))
        audit(conn, None, now, SYSTEM, "DATA_RECOVERED", "Fulfilment feed fresh again, alerts resumed")
    return not stale


def _create_exception(
    conn: sqlite3.Connection, order: sqlite3.Row, type_: str, reason: str, deadline: str, now: datetime, cfg: MarketConfig
) -> None:
    cur = conn.execute(
        "INSERT OR IGNORE INTO exceptions(order_id, type, reason, status, owner, owner_role, created_at, "
        "intervention_deadline, ack_due_at) VALUES (?, ?, ?, 'OPEN', ?, 'coordinator', ?, ?, ?)",
        (
            order["id"], type_, reason, cfg.coordinator, tu.iso(now), deadline,
            tu.iso(now + timedelta(minutes=cfg.ack_sla_min)),
        ),
    )
    if cur.rowcount:
        audit(conn, cur.lastrowid, now, SYSTEM, "CREATED", f"{reason} Assigned to {cfg.coordinator}.")


def _detect(conn: sqlite3.Connection, now: datetime, cfg: MarketConfig) -> None:
    orders = conn.execute(
        "SELECT * FROM orders o WHERE market = ? AND NOT EXISTS "
        "(SELECT 1 FROM events e WHERE e.order_id = o.id AND e.type IN ('DISPATCHED', 'DELIVERED'))",
        (cfg.code,),
    ).fetchall()
    # "No event" only means "not done" if we actually read the source after the milestone passed.
    row = conn.execute("SELECT last_received_at FROM sources WHERE id = ?", (FULFILMENT_SOURCE,)).fetchone()
    read_until = tu.parse(row["last_received_at"]) if row and row["last_received_at"] else None
    if read_until is None:
        return
    for o in orders:
        picked = _has_event(conn, o["id"], "PICK_CONFIRMED")
        if not picked and read_until >= tu.parse(o["pick_due_at"]):
            _create_exception(
                conn, o, "MISSING_PICK",
                f"No pick confirmation by {tu.local(o['pick_due_at'], cfg.tz)}; "
                f"route dispatches at {tu.local(o['dispatch_cutoff_at'], cfg.tz)}.",
                o["dispatch_cutoff_at"], now, cfg,
            )
        # Only raise a dispatch alert once picked; otherwise the pick alert already covers the root cause.
        # After a shift lead expedites, the plan is the latest viable dispatch, not the normal cutoff.
        expedited = conn.execute(
            "SELECT 1 FROM exceptions WHERE order_id = ? AND resolution = 'EXPEDITED'", (o["id"],)
        ).fetchone()
        dispatch_due = o["latest_dispatch_at"] if expedited else o["dispatch_cutoff_at"]
        if picked and read_until >= tu.parse(dispatch_due):
            _create_exception(
                conn, o, "MISSING_DISPATCH",
                f"Picked but not dispatched by {tu.local(dispatch_due, cfg.tz)}; "
                f"last dispatch that keeps the promise is {tu.local(o['latest_dispatch_at'], cfg.tz)}.",
                o["latest_dispatch_at"], now, cfg,
            )


def _reconcile_events(conn: sqlite3.Connection, now: datetime) -> None:
    """When the missing event arrives: auto-clear untouched alerts, inform owners of worked ones."""
    awaited = {"MISSING_PICK": ("PICK_CONFIRMED",), "MISSING_DISPATCH": ("DISPATCHED", "DELIVERED")}
    rows = conn.execute("SELECT * FROM exceptions WHERE event_arrived_at IS NULL").fetchall()
    for x in rows:
        types = awaited[x["type"]]
        marks = ",".join("?" * len(types))
        ev = conn.execute(
            f"SELECT type, occurred_at FROM events WHERE order_id = ? AND type IN ({marks}) ORDER BY occurred_at LIMIT 1",
            (x["order_id"], *types),
        ).fetchone()
        if not ev:
            continue
        conn.execute("UPDATE exceptions SET event_arrived_at = ? WHERE id = ?", (tu.iso(now), x["id"]))
        note = f"{ev['type']} received (source time {ev['occurred_at']})."
        if x["status"] == "OPEN":
            conn.execute(
                "UPDATE exceptions SET status = 'RESOLVED', resolution = 'AUTO_CLEARED', resolved_at = ? WHERE id = ?",
                (tu.iso(now), x["id"]),
            )
            audit(conn, x["id"], now, SYSTEM, "AUTO_CLEARED", note + " Nobody had started work, so the alert was closed.")
        else:
            audit(conn, x["id"], now, SYSTEM, "EVENT_ARRIVED", note)


def _escalate_overdue(conn: sqlite3.Connection, now: datetime, cfg: MarketConfig) -> None:
    rows = conn.execute(
        "SELECT x.* FROM exceptions x JOIN orders o ON o.id = x.order_id "
        "WHERE o.market = ? AND x.status = 'OPEN' AND x.escalated = 0 AND x.ack_due_at < ?",
        (cfg.code, tu.iso(now)),
    ).fetchall()
    for x in rows:
        conn.execute(
            "UPDATE exceptions SET escalated = 1, owner = ?, owner_role = 'shift_lead', ack_due_at = ? WHERE id = ?",
            (cfg.shift_lead, tu.iso(now + timedelta(minutes=cfg.ack_sla_min)), x["id"]),
        )
        audit(
            conn, x["id"], now, SYSTEM, "ESCALATED",
            f"Not acknowledged within {cfg.ack_sla_min} min. Moved from {x['owner']} to {cfg.shift_lead}.",
        )


def run(conn: sqlite3.Connection, now: datetime) -> None:
    """One evaluation cycle. In production this runs as a background job after each adapter poll."""
    for cfg in MARKETS.values():
        _reconcile_events(conn, now)
        if _guard_freshness(conn, now, cfg):
            _detect(conn, now, cfg)
        _escalate_overdue(conn, now, cfg)
    conn.commit()


def exception_label(type_: str) -> str:
    return EXCEPTION_TYPES.get(type_, type_)

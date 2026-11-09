"""Exception rules, data-freshness guard and escalation. Deterministic and explainable by design.

One evaluation cycle (``run``) does four things per market, in this order:

1. reconcile: a missing event that finally arrived closes untouched alerts and informs owners;
2. guard: if the fulfilment feed is stale, absence-based rules pause and a data task opens;
3. detect: the two Round 1 rules raise at most one exception per order and cause;
4. escalate: an alert nobody took within the response time moves to the shift lead.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from promiseops import timeutil as tu
from promiseops.config import EXCEPTION_TYPES, FULFILMENT_SOURCE, MARKETS, MarketConfig

SYSTEM = "PromiseOps"

# The event that settles each exception type.
AWAITED_EVENTS = {
    "MISSING_PICK": ("PICK_CONFIRMED",),
    "MISSING_DISPATCH": ("DISPATCHED", "DELIVERED"),
    "PICK_STILL_MISSING": ("PICK_CONFIRMED",),
    "DISPATCH_STILL_MISSING": ("DISPATCHED", "DELIVERED"),
}


def audit(conn: sqlite3.Connection, exception_id: int | None, now: datetime, actor: str, action: str, note: str = "") -> None:
    conn.execute(
        "INSERT INTO audit_log(exception_id, at, actor, action, note) VALUES (?, ?, ?, ?, ?)",
        (exception_id, tu.iso(now), actor, action, note),
    )


def source_read_at(conn: sqlite3.Connection, source: str) -> datetime | None:
    """When the adapter last read the source successfully (with or without new records)."""
    row = conn.execute("SELECT last_received_at FROM sources WHERE id = ?", (source,)).fetchone()
    return tu.parse(row["last_received_at"]) if row and row["last_received_at"] else None


def source_age_min(conn: sqlite3.Connection, source: str, now: datetime) -> int | None:
    read_at = source_read_at(conn, source)
    return None if read_at is None else tu.minutes_between(read_at, now)


def is_stale(conn: sqlite3.Connection, source: str, now: datetime, cfg: MarketConfig) -> bool:
    age = source_age_min(conn, source, now)
    return age is None or age > cfg.stale_after_min


def _first_event(conn: sqlite3.Connection, order_id: str, types: tuple[str, ...]) -> sqlite3.Row | None:
    marks = ",".join("?" * len(types))
    return conn.execute(
        f"SELECT type, occurred_at FROM events WHERE order_id = ? AND type IN ({marks}) ORDER BY occurred_at LIMIT 1",
        (order_id, *types),
    ).fetchone()


def _guard_freshness(conn: sqlite3.Connection, now: datetime, cfg: MarketConfig) -> bool:
    """Returns True when absence-based rules may run. Opens or closes a data task as needed."""
    stale = is_stale(conn, FULFILMENT_SOURCE, now, cfg)
    open_task = conn.execute(
        "SELECT id FROM data_tasks WHERE source = ? AND closed_at IS NULL", (FULFILMENT_SOURCE,)
    ).fetchone()
    if stale and not open_task:
        age = source_age_min(conn, FULFILMENT_SOURCE, now)
        note = (
            f"No fulfilment data for {age} min (limit {cfg.stale_after_min}). "
            "Missing-event alerts paused to avoid false alarms."
            if age is not None else
            "No fulfilment data received yet. Missing-event alerts paused to avoid false alarms."
        )
        conn.execute(
            "INSERT INTO data_tasks(source, owner, opened_at, note) VALUES (?, ?, ?, ?)",
            (FULFILMENT_SOURCE, cfg.data_owner, tu.iso(now), note),
        )
        audit(conn, None, now, SYSTEM, "DATA_STALE", "Fulfilment feed stale, absence-based alerts paused")
    elif not stale and open_task:
        conn.execute("UPDATE data_tasks SET closed_at = ? WHERE id = ?", (tu.iso(now), open_task["id"]))
        audit(conn, None, now, SYSTEM, "DATA_RECOVERED", "Fulfilment feed fresh again, alerts resumed")
    return not stale


def _dismissed(conn: sqlite3.Connection, order_id: str, type_: str) -> bool:
    """True when a person closed this order's alert of the given type as a false alarm."""
    return conn.execute(
        "SELECT 1 FROM exceptions WHERE order_id = ? AND type = ? AND resolution = 'FALSE_ALARM'", (order_id, type_)
    ).fetchone() is not None


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
    if cur.rowcount:  # UNIQUE(order_id, type): one exception per order and cause
        audit(conn, cur.lastrowid, now, SYSTEM, "CREATED", f"{reason} Assigned to {cfg.coordinator}.")


def _detect(conn: sqlite3.Connection, now: datetime, cfg: MarketConfig) -> None:
    # "No event" only means "not done" if the source was actually read after the milestone passed.
    read_until = source_read_at(conn, FULFILMENT_SOURCE)
    if read_until is None:
        return
    orders = conn.execute(
        "SELECT * FROM orders o WHERE market = ? AND NOT EXISTS "
        "(SELECT 1 FROM events e WHERE e.order_id = o.id AND e.type IN ('DISPATCHED', 'DELIVERED'))",
        (cfg.code,),
    ).fetchall()
    grace = timedelta(minutes=cfg.pick_grace_min)
    for o in orders:
        picked = _first_event(conn, o["id"], AWAITED_EVENTS["MISSING_PICK"]) is not None
        if not picked and read_until >= tu.parse(o["pick_due_at"]) + grace:
            _create_exception(
                conn, o, "MISSING_PICK",
                f"No pick confirmation by {tu.local(o['pick_due_at'], cfg.tz)}; "
                f"route dispatches at {tu.local(o['dispatch_cutoff_at'], cfg.tz)}.",
                o["dispatch_cutoff_at"], now, cfg,
            )
        if not picked:
            # A pick alert closed as a false alarm must not silence the order: if the pick is still
            # missing when the route leaves, the case comes back while the last viable dispatch is ahead.
            if read_until >= tu.parse(o["dispatch_cutoff_at"]) and _dismissed(conn, o["id"], "MISSING_PICK"):
                _create_exception(
                    conn, o, "PICK_STILL_MISSING",
                    f"Closed as a false alarm, but still no pick confirmation at the {tu.local(o['dispatch_cutoff_at'], cfg.tz)} "
                    f"cutoff; last dispatch that keeps the promise is {tu.local(o['latest_dispatch_at'], cfg.tz)}.",
                    o["latest_dispatch_at"], now, cfg,
                )
            continue  # the pick alert already covers the root cause; no second alert for it
        # After a shift lead expedites, the plan is the latest viable dispatch, not the normal cutoff.
        expedited = conn.execute(
            "SELECT 1 FROM exceptions WHERE order_id = ? AND resolution = 'EXPEDITED'", (o["id"],)
        ).fetchone()
        dispatch_due = o["latest_dispatch_at"] if expedited else o["dispatch_cutoff_at"]
        if read_until >= tu.parse(dispatch_due):
            _create_exception(
                conn, o, "MISSING_DISPATCH",
                f"Picked but not dispatched by {tu.local(dispatch_due, cfg.tz)}; "
                f"last dispatch that keeps the promise is {tu.local(o['latest_dispatch_at'], cfg.tz)}.",
                o["latest_dispatch_at"], now, cfg,
            )
        # Same for a dispatch alert closed as a false alarm: no dispatch by the last viable time means
        # the promise is at risk, and someone has to decide what the customer is told.
        if read_until >= tu.parse(o["latest_dispatch_at"]) and _dismissed(conn, o["id"], "MISSING_DISPATCH"):
            _create_exception(
                conn, o, "DISPATCH_STILL_MISSING",
                f"Closed as a false alarm, but still not dispatched by {tu.local(o['latest_dispatch_at'], cfg.tz)}; "
                f"the promise of {tu.local(o['promised_at'], cfg.tz)} is at risk.",
                o["promised_at"], now, cfg,
            )


def _reconcile_events(conn: sqlite3.Connection, now: datetime, cfg: MarketConfig) -> None:
    """When the missing event arrives: auto-clear untouched alerts, inform owners of worked ones."""
    rows = conn.execute(
        "SELECT x.* FROM exceptions x JOIN orders o ON o.id = x.order_id "
        "WHERE o.market = ? AND x.event_arrived_at IS NULL",
        (cfg.code,),
    ).fetchall()
    for x in rows:
        ev = _first_event(conn, x["order_id"], AWAITED_EVENTS[x["type"]])
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
    """One evaluation cycle. Runs after every adapter poll and after every record pushed to the API."""
    for cfg in MARKETS.values():
        _reconcile_events(conn, now, cfg)
        if _guard_freshness(conn, now, cfg):
            _detect(conn, now, cfg)
        _escalate_overdue(conn, now, cfg)
    conn.commit()


def exception_label(type_: str) -> str:
    return EXCEPTION_TYPES.get(type_, type_)

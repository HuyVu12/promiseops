"""Timetable geometry: every order as a course of four controls on one shared time axis.

Pure functions over rows already read from the database, so the board, the detail page and the
orders page draw the same course the same way.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from . import timeutil as tu

# Planned control, the event that punches it (None: a planning limit, punched by dispatch).
CONTROLS = (
    ("Pick", "pick_due_at", "PICK_CONFIRMED"),
    ("Cutoff", "dispatch_cutoff_at", "DISPATCHED"),
    ("Last viable", "latest_dispatch_at", None),
    ("Promise", "promised_at", "DELIVERED"),
)


@dataclass
class Axis:
    start: datetime
    end: datetime
    tz: str
    hours: list[dict] = field(default_factory=list)
    quarters: int = 0

    def pct(self, t: datetime | str | None) -> float:
        if isinstance(t, str):
            t = tu.parse(t)
        if t is None:
            return 0.0
        span = (self.end - self.start).total_seconds()
        value = (t - self.start).total_seconds() / span * 100
        return round(min(100.0, max(0.0, value)), 3)


def build_axis(orders: list[sqlite3.Row], now: datetime, tz: str) -> Axis:
    """Whole hours from the earliest pick milestone to the latest promise, always containing now."""
    times = [tu.parse(o["pick_due_at"]) for o in orders] + [tu.parse(o["promised_at"]) for o in orders] + [now]
    first, last = min(times), max(times)
    start = first.replace(minute=0, second=0, microsecond=0)
    end = last.replace(minute=0, second=0, microsecond=0)
    if end <= last:
        end += timedelta(hours=1)
    axis = Axis(start=start, end=end, tz=tz)
    t = start
    while t <= end:
        axis.hours.append({"label": tu.local(t, tz), "pct": axis.pct(t)})
        t += timedelta(hours=1)
    axis.quarters = int((end - start) / timedelta(minutes=15))
    return axis


def events_by_type(conn: sqlite3.Connection, order_id: str) -> dict[str, str]:
    rows = conn.execute(
        "SELECT type, MIN(occurred_at) AS t FROM events WHERE order_id = ? GROUP BY type", (order_id,)
    ).fetchall()
    return {r["type"]: r["t"] for r in rows}


def course(order: sqlite3.Row, events: dict[str, str], now: datetime, axis: Axis, escalated: bool = False) -> dict:
    now_iso = tu.iso(now)
    dispatched = events.get("DISPATCHED") or events.get("DELIVERED")
    stops = []
    for label, column, event_type in CONTROLS:
        due = order[column]
        actual = events.get(event_type) if event_type else dispatched
        if actual and event_type:
            state = "late" if actual > due else "punched"
        elif event_type is None and actual:
            state = "passed" if actual <= due else "missed"
        elif due <= now_iso:
            state = "missed"
        else:
            state = "ahead"
        stops.append({
            "label": label, "due": due, "time": tu.local(due, axis.tz), "pct": axis.pct(due),
            "state": state, "actual": tu.local(actual, axis.tz) if actual and event_type else None,
            "actual_pct": axis.pct(actual) if actual and event_type else None,
        })
    first_missed = next((s for s in stops if s["state"] == "missed"), None)
    if escalated and first_missed:
        first_missed["escalated"] = True
    delivered = events.get("DELIVERED")
    outcome = None
    if delivered:
        outcome = "on time" if delivered <= order["promised_at"] else "late"
    nxt = next((s for s in stops if s["state"] == "ahead"), None)
    return {
        "stops": stops,
        "start_pct": stops[0]["pct"],
        "end_pct": stops[-1]["pct"],
        "delivered": tu.local(delivered, axis.tz) if delivered else None,
        "outcome": outcome,
        "next": nxt,
        "at_risk": first_missed is not None and not delivered,
    }

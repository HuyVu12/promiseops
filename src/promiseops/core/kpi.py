"""Outcome measurement against the ORIGINAL promise, using the Round 1 pilot metric definitions (slide 8).

Rules that keep the numbers honest:

- An order counts once its result is known: delivered, or past its promise without a delivery
  ("overdue"). An overdue order is late, even before it arrives; silence is never success.
- "Late deliveries prevented" only counts orders where a person intervened (expedite) and the
  original promise was still kept. False alarms and alerts that cleared on their own are excluded.
- Money is shown as a Round 1 planning assumption, next to the costs people actually logged.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from statistics import median

from promiseops import timeutil as tu
from promiseops.config import AVOIDED_COST_PER_LATE_EUR, PILOT_TARGETS


def _pct(part: int, whole: int) -> float | None:
    return round(100 * part / whole, 1) if whole else None


def order_results(conn: sqlite3.Connection, now: datetime) -> list[dict]:
    """Every order with its delivery time and result: on_time | late | overdue | open."""
    now_iso = tu.iso(now)
    rows = conn.execute(
        "SELECT o.*, (SELECT MIN(occurred_at) FROM events e WHERE e.order_id = o.id AND e.type = 'DELIVERED') "
        "AS delivered_at FROM orders o ORDER BY o.id"
    ).fetchall()
    out = []
    for o in rows:
        if o["delivered_at"]:
            result = "on_time" if o["delivered_at"] <= o["promised_at"] else "late"
        elif o["promised_at"] < now_iso:
            result = "overdue"
        else:
            result = "open"
        out.append({**dict(o), "result": result})
    return out


def _segment(rows: list[dict]) -> dict:
    on_time = sum(1 for o in rows if o["result"] == "on_time")
    late = sum(1 for o in rows if o["result"] == "late")
    overdue = sum(1 for o in rows if o["result"] == "overdue")
    decided = on_time + late + overdue
    return {
        "orders": len(rows),
        "delivered": on_time + late,
        "on_time": on_time,
        "late": late,
        "overdue": overdue,
        "missed": late + overdue,
        "decided": decided,
        "open": len(rows) - decided,
        "on_time_pct": _pct(on_time, decided),
    }


def compute(conn: sqlite3.Connection, now: datetime) -> dict:
    orders = order_results(conn, now)
    by_id = {o["id"]: o for o in orders}
    segments = {
        "All": _segment(orders),
        "B2B": _segment([o for o in orders if o["customer_type"] == "B2B"]),
        "B2C": _segment([o for o in orders if o["customer_type"] == "B2C"]),
    }

    exc = conn.execute("SELECT * FROM exceptions").fetchall()
    resolved = [x for x in exc if x["status"] == "RESOLVED"]
    by_resolution: dict[str, int] = {}
    for x in resolved:
        by_resolution[x["resolution"]] = by_resolution.get(x["resolution"], 0) + 1

    # Alerts a person worked to a verdict. Auto-cleared ones cost nobody time and are not judged.
    worked = [x for x in resolved if x["resolution"] != "AUTO_CLEARED"]
    actionable = [x for x in worked if x["resolution"] != "FALSE_ALARM"]

    # Response time: every alert that needed a person, i.e. not cleared by data before its timer ran out.
    needed_person = [
        x for x in exc
        if x["acknowledged_at"] or x["escalated"]
        or (x["status"] != "RESOLVED" and x["ack_due_at"] <= tu.iso(now))
    ]
    ack_minutes = [
        tu.minutes_between(tu.parse(x["created_at"]), tu.parse(x["acknowledged_at"]))
        for x in exc if x["acknowledged_at"]
    ]
    in_sla = [
        x for x in needed_person
        if x["acknowledged_at"] and x["acknowledged_at"] <= x["ack_due_at"] and not _auto_escalated(conn, x["id"])
    ]

    # Interventions: expedites, and whether the original promise was kept afterwards.
    expedited_orders = sorted({x["order_id"] for x in resolved if x["resolution"] == "EXPEDITED"})
    expedite_results = [by_id[oid]["result"] for oid in expedited_orders]
    prevented = sum(1 for r in expedite_results if r == "on_time")
    expedite_decided = sum(1 for r in expedite_results if r != "open")
    logged_cost = round(sum(x["action_cost_eur"] or 0 for x in resolved), 2)

    order_log = conn.execute("SELECT outcome, COUNT(*) AS n FROM ingest_log WHERE source = 'oms' GROUP BY outcome")
    order_counts = {r["outcome"]: r["n"] for r in order_log}
    usable = order_counts.get("accepted", 0)
    received = usable + order_counts.get("rejected", 0)

    return {
        "segments": segments,
        "exceptions_total": len(exc),
        "exceptions_open": sum(1 for x in exc if x["status"] != "RESOLVED"),
        "escalated": sum(1 for x in exc if x["escalated"]),
        "by_resolution": by_resolution,
        "median_ack_min": median(ack_minutes) if ack_minutes else None,
        "worked": len(worked),
        "actionable": len(actionable),
        "actionable_pct": _pct(len(actionable), len(worked)),
        "false_alarm_pct": _pct(by_resolution.get("FALSE_ALARM", 0), len(worked)),
        "needed_person": len(needed_person),
        "ack_in_sla": len(in_sla),
        "ack_in_sla_pct": _pct(len(in_sla), len(needed_person)),
        "expedited": len(expedited_orders),
        "expedite_decided": expedite_decided,
        "prevented": prevented,
        "prevented_ids": [oid for oid in expedited_orders if by_id[oid]["result"] == "on_time"],
        "logged_cost_eur": logged_cost,
        "avoided_eur": prevented * AVOIDED_COST_PER_LATE_EUR,
        "avoided_per_late_eur": AVOIDED_COST_PER_LATE_EUR,
        "coverage_pct": _pct(usable, received),
        "orders_usable": usable,
        "orders_received": received,
        "overdue_ids": [o["id"] for o in orders if o["result"] == "overdue"],
        "targets": PILOT_TARGETS,
        "data_incidents": conn.execute("SELECT COUNT(*) AS n FROM data_tasks").fetchone()["n"],
    }


def _auto_escalated(conn: sqlite3.Connection, exception_id: int) -> bool:
    """True when the response timer ran out and the system moved the case (a missed response)."""
    return conn.execute(
        "SELECT 1 FROM audit_log WHERE exception_id = ? AND action = 'ESCALATED' AND actor = 'PromiseOps'",
        (exception_id,),
    ).fetchone() is not None


def margins(conn: sqlite3.Connection, now: datetime) -> dict:
    """Delivery margin against the promise for the strip chart; overdue orders sit at their delay so far."""
    marks = []
    for o in order_results(conn, now):
        if o["result"] in ("on_time", "late"):
            minutes = tu.minutes_between(tu.parse(o["delivered_at"]), tu.parse(o["promised_at"]))
        elif o["result"] == "overdue":
            minutes = tu.minutes_between(now, tu.parse(o["promised_at"]))
        else:
            continue
        marks.append({"id": o["id"], "type": o["customer_type"], "min": minutes, "result": o["result"]})
    lo = min([-60] + [m["min"] for m in marks])
    hi = max([120] + [m["min"] for m in marks])
    for m in marks:
        m["pct"] = round((m["min"] - lo) / (hi - lo) * 100, 2)
    marks.sort(key=lambda m: m["min"])
    # Stack marks that would overlap so every order stays visible.
    lanes: list[float] = []
    for m in marks:
        lane = next((i for i, last in enumerate(lanes) if m["pct"] - last > 2.2), None)
        if lane is None:
            lanes.append(m["pct"])
            lane = len(lanes) - 1
        else:
            lanes[lane] = m["pct"]
        m["lane"] = lane
    return {"marks": marks, "lo": lo, "hi": hi, "zero_pct": round((0 - lo) / (hi - lo) * 100, 2),
            "lanes": max(1, len(lanes))}

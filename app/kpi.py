"""Outcome measurement against the ORIGINAL promise, matching the pilot metric definitions."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from statistics import median

from . import timeutil as tu


def _pct(part: int, whole: int) -> float | None:
    return round(100 * part / whole, 1) if whole else None


def compute(conn: sqlite3.Connection, now: datetime) -> dict:
    orders = conn.execute(
        "SELECT o.*, (SELECT MIN(occurred_at) FROM events e WHERE e.order_id = o.id AND e.type = 'DELIVERED') AS delivered_at "
        "FROM orders o"
    ).fetchall()
    exc_orders = {r["order_id"] for r in conn.execute("SELECT DISTINCT order_id FROM exceptions")}

    segments: dict[str, dict] = {}
    for seg in ("All", "B2B", "B2C"):
        rows = [o for o in orders if seg == "All" or o["customer_type"] == seg]
        delivered = [o for o in rows if o["delivered_at"]]
        on_time = [o for o in delivered if o["delivered_at"] <= o["promised_at"]]
        segments[seg] = {
            "orders": len(rows),
            "delivered": len(delivered),
            "on_time": len(on_time),
            "late": len(delivered) - len(on_time),
            "on_time_pct": _pct(len(on_time), len(delivered)),
        }

    exc = conn.execute("SELECT * FROM exceptions").fetchall()
    resolved = [x for x in exc if x["status"] == "RESOLVED"]
    human = [x for x in resolved if x["resolution"] != "AUTO_CLEARED"]
    ack_minutes = [
        tu.minutes_between(tu.parse(x["created_at"]), tu.parse(x["acknowledged_at"]))
        for x in exc if x["acknowledged_at"]
    ]
    by_resolution: dict[str, int] = {}
    for x in resolved:
        by_resolution[x["resolution"]] = by_resolution.get(x["resolution"], 0) + 1

    flagged_delivered = [o for o in orders if o["id"] in exc_orders and o["delivered_at"]]
    recovered = [o for o in flagged_delivered if o["delivered_at"] <= o["promised_at"]]
    # Precision is judged only on alerts a person actually worked; auto-cleared ones cost nobody time.
    false_alarms = by_resolution.get("FALSE_ALARM", 0)

    return {
        "segments": segments,
        "exceptions_total": len(exc),
        "exceptions_open": sum(1 for x in exc if x["status"] != "RESOLVED"),
        "escalated": sum(1 for x in exc if x["escalated"]),
        "by_resolution": by_resolution,
        "median_ack_min": median(ack_minutes) if ack_minutes else None,
        "flagged_delivered": len(flagged_delivered),
        "recovered": len(recovered),
        "recovered_pct": _pct(len(recovered), len(flagged_delivered)),
        "false_alarm_pct": _pct(false_alarms, len(human)),
        "data_incidents": conn.execute("SELECT COUNT(*) AS n FROM data_tasks").fetchone()["n"],
    }

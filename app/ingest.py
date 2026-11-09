"""Source adapter: validates and stores records from existing systems. Read-only towards those systems."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta

from . import timeutil as tu
from .config import EVENT_TYPES, MARKETS

MAX_CLOCK_SKEW = timedelta(minutes=5)


@dataclass
class IngestResult:
    outcome: str  # accepted | duplicate | rejected
    detail: str = ""


def _log(conn: sqlite3.Connection, now: datetime, source: str, ref: str | None, result: IngestResult) -> IngestResult:
    conn.execute(
        "INSERT INTO ingest_log(at, source, ref, outcome, detail) VALUES (?, ?, ?, ?, ?)",
        (tu.iso(now), source, ref, result.outcome, result.detail),
    )
    return result


def mark_read(conn: sqlite3.Connection, source: str, now: datetime) -> None:
    """A successful read of a source, even with no new records, proves the feed is alive."""
    conn.execute("UPDATE sources SET last_received_at = ? WHERE id = ?", (tu.iso(now), source))


def ingest_event(
    conn: sqlite3.Connection,
    *,
    source: str,
    event_id: str,
    order_id: str,
    type: str,
    occurred_at: str,
    now: datetime,
) -> IngestResult:
    ref = f"{event_id} {type} {order_id}"
    if not conn.execute("SELECT 1 FROM sources WHERE id = ?", (source,)).fetchone():
        return _log(conn, now, source, ref, IngestResult("rejected", "unknown source"))
    if type not in EVENT_TYPES:
        return _log(conn, now, source, ref, IngestResult("rejected", f"unknown event type {type!r}"))
    try:
        occurred = tu.parse(occurred_at)
    except ValueError as exc:
        return _log(conn, now, source, ref, IngestResult("rejected", str(exc)))
    if occurred is None:
        return _log(conn, now, source, ref, IngestResult("rejected", "missing timestamp"))
    if occurred > now + MAX_CLOCK_SKEW:
        return _log(conn, now, source, ref, IngestResult("rejected", "timestamp is in the future"))
    if not conn.execute("SELECT 1 FROM orders WHERE id = ?", (order_id,)).fetchone():
        return _log(conn, now, source, ref, IngestResult("rejected", "unknown order"))

    # Idempotency: (source, event_id) is unique, so a re-delivered record never creates new work.
    cur = conn.execute(
        "INSERT OR IGNORE INTO events(source, event_id, order_id, type, occurred_at, received_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (source, event_id, order_id, type, tu.iso(occurred), tu.iso(now)),
    )
    if cur.rowcount == 0:
        return _log(conn, now, source, ref, IngestResult("duplicate", "already received"))

    # Late events never move the source clock backwards.
    conn.execute(
        "UPDATE sources SET last_event_at = ? WHERE id = ? AND (last_event_at IS NULL OR last_event_at < ?)",
        (tu.iso(occurred), source, tu.iso(occurred)),
    )
    mark_read(conn, source, now)
    return _log(conn, now, source, ref, IngestResult("accepted"))


def ingest_order(conn: sqlite3.Connection, order: dict, now: datetime, source: str = "oms") -> IngestResult:
    ref = order.get("id")
    required = [
        "id", "market", "dc", "store", "customer_type", "customer_ref",
        "promised_at", "pick_due_at", "dispatch_cutoff_at", "latest_dispatch_at",
    ]
    missing = [f for f in required if not order.get(f)]
    if missing:
        return _log(conn, now, source, ref, IngestResult("rejected", f"missing {', '.join(missing)}"))
    if order["market"] not in MARKETS:
        return _log(conn, now, source, ref, IngestResult("rejected", "unknown market"))
    if order["customer_type"] not in ("B2B", "B2C"):
        return _log(conn, now, source, ref, IngestResult("rejected", "customer_type must be B2B or B2C"))
    try:
        times = {k: tu.parse(order[k]) for k in ("promised_at", "pick_due_at", "dispatch_cutoff_at", "latest_dispatch_at")}
    except ValueError as exc:
        return _log(conn, now, source, ref, IngestResult("rejected", str(exc)))
    if not (times["pick_due_at"] <= times["dispatch_cutoff_at"] <= times["latest_dispatch_at"] < times["promised_at"]):
        return _log(conn, now, source, ref, IngestResult("rejected", "milestones must precede the promise in order"))

    cur = conn.execute(
        "INSERT OR IGNORE INTO orders(id, market, dc, store, customer_type, customer_ref, promised_at, "
        "pick_due_at, dispatch_cutoff_at, latest_dispatch_at, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            order["id"], order["market"], order["dc"], order["store"], order["customer_type"],
            order["customer_ref"], tu.iso(times["promised_at"]), tu.iso(times["pick_due_at"]),
            tu.iso(times["dispatch_cutoff_at"]), tu.iso(times["latest_dispatch_at"]), tu.iso(now),
        ),
    )
    if cur.rowcount == 0:
        # The original promise is immutable: a re-sent order never overwrites it.
        return _log(conn, now, source, ref, IngestResult("duplicate", "order exists, promise kept unchanged"))
    mark_read(conn, source, now)
    return _log(conn, now, source, ref, IngestResult("accepted"))

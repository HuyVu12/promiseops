"""Demo harness: a simulated clock and scripted source feeds standing in for the real OMS/WMS.

Production replaces this module with scheduled adapter polls; the engine and workflow are unchanged.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from promiseops.core import engine
from promiseops.integration import ingest
from promiseops.storage import db
from promiseops import timeutil as tu
from promiseops.config import MARKETS

CLOCK_KEY = "sim_now"
# Each recorded human action takes one simulated minute, so the audit log and the response-time KPI
# read like a real shift instead of everything happening at the same instant.
ACTION_MINUTES = 1
MAX_ADVANCE_MIN = 12 * 60


def now(conn: sqlite3.Connection) -> datetime:
    value = db.get_meta(conn, CLOCK_KEY)
    if value is None:
        raise RuntimeError("Simulation clock not initialised; run the seed first")
    return tu.parse(value)


def _expedite_time(conn: sqlite3.Connection, order_id: str) -> datetime | None:
    row = conn.execute(
        "SELECT resolved_at FROM exceptions WHERE order_id = ? AND resolution = 'EXPEDITED'", (order_id,)
    ).fetchone()
    return tu.parse(row["resolved_at"]) if row else None


def _due_records(conn: sqlite3.Connection, source: str, t: datetime) -> list[tuple[sqlite3.Row, datetime]]:
    due = []
    rows = conn.execute("SELECT * FROM sim_feed WHERE source = ? AND released = 0 ORDER BY id", (source,)).fetchall()
    for r in rows:
        expedited_at = _expedite_time(conn, r["order_id"])
        if r["branch"] == "expedited":
            if expedited_at is None:
                continue
            occurred = expedited_at + timedelta(minutes=r["offset_min"])
            release = occurred
        else:
            occurred = tu.parse(r["occurred_at"])
            release = tu.parse(r["release_at"]) if r["release_at"] else occurred
            if r["branch"] == "not_expedited" and expedited_at is not None and expedited_at <= release:
                continue  # the shift lead's decision replaced this outcome
        if release <= t:
            due.append((r, occurred))
    return due


def poll(conn: sqlite3.Connection, t: datetime) -> None:
    """One adapter cycle: read every live source, ingest new records, record that the read succeeded."""
    for src in conn.execute("SELECT * FROM sources").fetchall():
        if src["paused"]:
            continue
        for r, occurred in _due_records(conn, src["id"], t):
            ingest.ingest_event(
                conn, source=r["source"], event_id=r["event_id"], order_id=r["order_id"],
                type=r["type"], occurred_at=tu.iso(occurred), now=t,
            )
            conn.execute("UPDATE sim_feed SET released = 1 WHERE id = ?", (r["id"],))
        ingest.mark_read(conn, src["id"], t)
    conn.commit()


def _poll_times(start: datetime, end: datetime, every_min: int) -> list[datetime]:
    """Adapter polls happen on a fixed clock grid (every N minutes on the hour), not relative to the last click."""
    step = timedelta(minutes=every_min)
    first = start.replace(second=0, microsecond=0)
    first += timedelta(minutes=(-first.minute) % every_min)
    if first <= start:
        first += step
    times = []
    t = first
    while t <= end:
        times.append(t)
        t += step
    return times


def advance(conn: sqlite3.Connection, minutes: int) -> datetime:
    """Move the demo clock forward: poll the feeds and run the rules at every poll, then run the rules at the end."""
    if minutes <= 0 or minutes > MAX_ADVANCE_MIN:
        raise ValueError("Advance between 1 minute and 12 hours")
    start = now(conn)
    end = start + timedelta(minutes=minutes)
    for t in _poll_times(start, end, MARKETS["SE"].poll_interval_min):
        db.set_meta(conn, CLOCK_KEY, tu.iso(t))
        poll(conn, t)
        engine.run(conn, t)
    db.set_meta(conn, CLOCK_KEY, tu.iso(end))
    engine.run(conn, end)  # timers (escalation, staleness) move even between polls
    return end


def after_human_action(conn: sqlite3.Connection) -> datetime:
    """Let simulated time pass for the action a person just recorded."""
    return advance(conn, ACTION_MINUTES)


def set_paused(conn: sqlite3.Connection, source: str, paused: bool) -> None:
    conn.execute("UPDATE sources SET paused = ? WHERE id = ?", (1 if paused else 0, source))
    engine.audit(
        conn, None, now(conn), "Demo control",
        "FEED_PAUSED" if paused else "FEED_RESUMED", f"Source {source} {'paused' if paused else 'resumed'}",
    )
    conn.commit()

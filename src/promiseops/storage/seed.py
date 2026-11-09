"""Fully fictional demo scenario: one Swedish DC, 12 stores, one morning of timed deliveries.

No Company A data is used. Numbers are illustrative. The hero order SE-1042 is the Round 1 example
(slide 4): a B2B site delivery of plasterboard, promised for 14:00, on the 10:00 route.
"""

from __future__ import annotations

import sqlite3

from promiseops.core import engine
from promiseops.integration import ingest, simulation
from promiseops.storage import db
from promiseops import timeutil as tu
from promiseops.config import DEFAULT_MARKET, FULFILMENT_SOURCE, MARKETS, ORDER_SOURCE

DAY = "2026-11-10"
TZ = MARKETS[DEFAULT_MARKET].tz
START = "09:00"
DC = MARKETS[DEFAULT_MARKET].dc

STORES = [
    "S01 Sodermalm", "S02 Kungsholmen", "S03 Solna", "S04 Nacka", "S05 Huddinge", "S06 Taby",
    "S07 Sundbyberg", "S08 Haninge", "S09 Lidingo", "S10 Sollentuna", "S11 Bromma", "S12 Farsta",
]

# Route milestones: pick due, dispatch cutoff, latest dispatch that keeps the promise, promise.
ROUTES = {
    "A": ("09:30", "10:00", "11:30", "14:00"),
    "B": ("10:00", "10:30", "12:00", "15:00"),
    "C": ("10:30", "11:00", "12:30", "16:00"),
}

# id, store index, customer type, route, normal timeline (pick, dispatch, delivered) or None for special cases
NORMAL = [
    ("SE-1031", 0, "B2C", "A", ("08:40", "09:50", "12:40")),
    ("SE-1033", 2, "B2B", "A", ("08:55", "09:45", "11:55")),
    ("SE-1036", 4, "B2C", "A", ("09:10", "09:55", "13:20")),
    ("SE-1039", 5, "B2C", "B", ("09:35", "10:20", "13:50")),
    ("SE-1044", 7, "B2B", "B", ("09:40", "10:25", "14:05")),
    ("SE-1047", 8, "B2C", "B", ("09:50", "10:15", "14:40")),
    ("SE-1053", 9, "B2C", "C", ("10:05", "10:50", "15:10")),
    ("SE-1056", 11, "B2B", "C", ("10:20", "10:55", "14:30")),
    ("SE-1058", 1, "B2C", "C", ("10:10", "10:45", "15:35")),
    ("SE-1063", 3, "B2C", "A", ("09:20", "09:58", "13:45")),
    ("SE-1066", 6, "B2B", "C", ("10:25", "10:58", "15:20")),
    ("SE-1069", 10, "B2C", "B", ("09:30", "10:10", "14:15")),
]

SPECIAL = [
    # SE-1042: B2B site delivery, goods genuinely not picked. On time only if the shift lead expedites in time.
    ("SE-1042", 3, "B2B", "A"),
    # SE-1051: picked on time, but the handheld synced 35 minutes late. A false alarm worth recording.
    ("SE-1051", 6, "B2C", "A"),
    # SE-1060: nobody acknowledges; the alert escalates, then clears when the pick arrives.
    ("SE-1060", 1, "B2C", "B"),
    # SE-1077: picked, but the vehicle is short. Promise cannot be kept; customer service informs the customer.
    ("SE-1077", 10, "B2B", "A"),
]


def _t(hhmm: str) -> str:
    return tu.iso(tu.local_dt(DAY, hhmm, TZ))


# What the order is, where the story needs it; otherwise a neutral reference.
CUSTOMER_REFS = {
    "SE-1042": "Trade customer 1042 · site delivery, plasterboard",
    "SE-1077": "Trade customer 1077 · site delivery, insulation",
}


def _order(order_id: str, store: int, ctype: str, route: str) -> dict:
    pick, cutoff, latest, promise = ROUTES[route]
    default_ref = f"{'Trade' if ctype == 'B2B' else 'Household'} customer {order_id[-4:]}"
    return {
        "id": order_id, "market": DEFAULT_MARKET, "dc": DC, "store": STORES[store], "customer_type": ctype,
        "customer_ref": CUSTOMER_REFS.get(order_id, default_ref),
        "promised_at": _t(promise), "pick_due_at": _t(pick),
        "dispatch_cutoff_at": _t(cutoff), "latest_dispatch_at": _t(latest),
    }


def _feed(conn: sqlite3.Connection, order_id: str, type_: str, occurred: str | None, *,
          release: str | None = None, branch: str = "always", offset: int | None = None) -> None:
    n = conn.execute("SELECT COUNT(*) AS n FROM sim_feed").fetchone()["n"] + 1
    conn.execute(
        "INSERT INTO sim_feed(source, event_id, order_id, type, occurred_at, release_at, branch, offset_min) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (FULFILMENT_SOURCE, f"WMS-{n:05d}", order_id, type_,
         _t(occurred) if occurred else None, _t(release) if release else None, branch, offset),
    )


def seed(conn: sqlite3.Connection) -> None:
    db.reset(conn)
    start = tu.local_dt(DAY, START, TZ)
    conn.executemany(
        "INSERT INTO sources(id, name, kind) VALUES (?, ?, ?)",
        [
            (ORDER_SOURCE, "Order management system (existing)", "orders"),
            (FULFILMENT_SOURCE, "Warehouse fulfilment status (existing)", "fulfilment"),
        ],
    )
    db.set_meta(conn, simulation.CLOCK_KEY, tu.iso(start))
    db.set_meta(conn, "schema_version", db.SCHEMA_VERSION)

    for oid, store, ctype, route, _ in NORMAL:
        ingest.ingest_order(conn, _order(oid, store, ctype, route), start)
    for oid, store, ctype, route in SPECIAL:
        ingest.ingest_order(conn, _order(oid, store, ctype, route), start)

    for oid, _, _, _, (pick, dispatch, delivered) in NORMAL:
        _feed(conn, oid, "PICK_CONFIRMED", pick)
        _feed(conn, oid, "DISPATCHED", dispatch)
        _feed(conn, oid, "DELIVERED", delivered)

    # SE-1042: two possible futures, decided by the shift lead's action.
    _feed(conn, "SE-1042", "PICK_CONFIRMED", None, branch="expedited", offset=20)
    _feed(conn, "SE-1042", "DISPATCHED", None, branch="expedited", offset=45)
    _feed(conn, "SE-1042", "DELIVERED", None, branch="expedited", offset=180)
    _feed(conn, "SE-1042", "PICK_CONFIRMED", "11:20", branch="not_expedited")
    _feed(conn, "SE-1042", "DISPATCHED", "11:55", branch="not_expedited")
    _feed(conn, "SE-1042", "DELIVERED", "14:25", branch="not_expedited")

    # SE-1051: the pick happened at 09:20 but reaches the adapter at 09:55.
    _feed(conn, "SE-1051", "PICK_CONFIRMED", "09:20", release="09:55")
    _feed(conn, "SE-1051", "DISPATCHED", "09:58")
    _feed(conn, "SE-1051", "DELIVERED", "12:50")

    # SE-1060: late pick at 10:25, still makes the 10:30 cutoff.
    _feed(conn, "SE-1060", "PICK_CONFIRMED", "10:25")
    _feed(conn, "SE-1060", "DISPATCHED", "10:29")
    _feed(conn, "SE-1060", "DELIVERED", "14:30")

    # SE-1077: picked early, no vehicle until 11:50 unless the shift lead finds capacity.
    _feed(conn, "SE-1077", "PICK_CONFIRMED", "09:05")
    _feed(conn, "SE-1077", "DISPATCHED", "11:50", branch="not_expedited")
    _feed(conn, "SE-1077", "DELIVERED", "14:35", branch="not_expedited")
    _feed(conn, "SE-1077", "DISPATCHED", None, branch="expedited", offset=30)
    _feed(conn, "SE-1077", "DELIVERED", None, branch="expedited", offset=170)

    engine.audit(conn, None, start, "Demo control", "SEEDED", f"Fictional scenario loaded for {DAY}")
    conn.commit()
    simulation.poll(conn, start)
    engine.run(conn, start)

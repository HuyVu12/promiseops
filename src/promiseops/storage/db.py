"""SQLite storage. One relational database, as proposed for the pilot."""

from __future__ import annotations

import sqlite3
from pathlib import Path

# Bump when the schema changes; a database with another version is rebuilt from the demo seed.
SCHEMA_VERSION = "2"

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,              -- orders | fulfilment
    last_received_at TEXT,           -- last successful read by the adapter
    last_event_at TEXT,              -- newest source timestamp seen
    paused INTEGER NOT NULL DEFAULT 0 -- demo only: simulate a feed outage
);

CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    market TEXT NOT NULL,
    dc TEXT NOT NULL,
    store TEXT NOT NULL,
    customer_type TEXT NOT NULL CHECK (customer_type IN ('B2B', 'B2C')),
    customer_ref TEXT NOT NULL,
    promised_at TEXT NOT NULL,        -- original delivery promise, never edited
    pick_due_at TEXT NOT NULL,        -- process milestone: pick confirmed by
    dispatch_cutoff_at TEXT NOT NULL, -- process milestone: dispatched by
    latest_dispatch_at TEXT NOT NULL, -- last dispatch that can still meet the promise
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    event_id TEXT NOT NULL,
    order_id TEXT NOT NULL REFERENCES orders(id),
    type TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    received_at TEXT NOT NULL,
    UNIQUE (source, event_id)
);
CREATE INDEX IF NOT EXISTS idx_events_order ON events(order_id, type);

CREATE TABLE IF NOT EXISTS ingest_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    source TEXT NOT NULL,
    ref TEXT,
    outcome TEXT NOT NULL,           -- accepted | duplicate | rejected
    detail TEXT
);

CREATE TABLE IF NOT EXISTS exceptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL REFERENCES orders(id),
    type TEXT NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('OPEN', 'ACKNOWLEDGED', 'RESOLVED')),
    owner TEXT NOT NULL,
    owner_role TEXT NOT NULL,
    escalated INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    intervention_deadline TEXT NOT NULL,
    ack_due_at TEXT NOT NULL,
    acknowledged_at TEXT,
    resolved_at TEXT,
    resolution TEXT,
    action_cost_eur REAL,            -- cost of the intervention, logged with the outcome (Round 1: PROVE)
    event_arrived_at TEXT,           -- when the missing event finally showed up
    UNIQUE (order_id, type)          -- one exception per order and cause
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exception_id INTEGER REFERENCES exceptions(id),
    at TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    note TEXT
);

CREATE TABLE IF NOT EXISTS data_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL REFERENCES sources(id),
    owner TEXT NOT NULL,
    opened_at TEXT NOT NULL,
    closed_at TEXT,
    note TEXT NOT NULL
);

-- Demo only: scripted source records the feed simulator releases as the clock moves.
CREATE TABLE IF NOT EXISTS sim_feed (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    event_id TEXT NOT NULL,
    order_id TEXT NOT NULL,
    type TEXT NOT NULL,
    occurred_at TEXT,                -- absolute time, or NULL when relative to a decision
    release_at TEXT,                 -- when the record reaches the adapter (sync delay)
    branch TEXT NOT NULL DEFAULT 'always', -- always | expedited | not_expedited
    offset_min INTEGER,              -- for branch=expedited: minutes after the decision
    released INTEGER NOT NULL DEFAULT 0
);
"""


def connect(path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def is_current(conn: sqlite3.Connection) -> bool:
    """True when the database was built with this code's schema (and has been seeded)."""
    try:
        return get_meta(conn, "schema_version") == SCHEMA_VERSION
    except sqlite3.OperationalError:
        return False


def reset(conn: sqlite3.Connection) -> None:
    tables = [
        "audit_log", "data_tasks", "exceptions", "events", "ingest_log",
        "sim_feed", "orders", "sources", "meta",
    ]
    for t in tables:
        conn.execute(f"DROP TABLE IF EXISTS {t}")
    init(conn)


def get_meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )

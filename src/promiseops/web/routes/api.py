"""JSON API for source integrations and monitoring.

Writes go through the same source adapter as the polled feeds (validation, idempotency, freshness),
and every accepted record triggers a rules cycle. When PROMISEOPS_API_KEY is set, every endpoint
except /api/health requires the X-API-Key header. Sources that have nothing new send a heartbeat.
"""

from __future__ import annotations

import hmac
import sqlite3

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from promiseops import clock
from promiseops import timeutil as tu
from promiseops.core import engine, kpi, queries
from promiseops.integration import ingest
from promiseops.web.deps import CFG, get_conn, settings

router = APIRouter(prefix="/api")


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if settings.api_key is None:
        return  # local demo: open, and /api/health says so
    if not x_api_key or not hmac.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(401, "Missing or wrong X-API-Key")


class EventIn(BaseModel):
    source: str
    event_id: str
    order_id: str
    type: str
    occurred_at: str


class OrderIn(BaseModel):
    id: str
    market: str
    dc: str
    store: str
    customer_type: str
    customer_ref: str
    promised_at: str
    pick_due_at: str
    dispatch_cutoff_at: str
    latest_dispatch_at: str


def _result(result: ingest.IngestResult, conn: sqlite3.Connection, now) -> dict:
    conn.commit()
    if result.outcome == "rejected":
        raise HTTPException(422, result.detail)
    if result.outcome == "accepted":
        engine.run(conn, now)
    return {"outcome": result.outcome, "detail": result.detail}


@router.post("/events", dependencies=[Depends(require_api_key)])
def receive_event(event: EventIn, conn: sqlite3.Connection = Depends(get_conn)):
    now = clock.now(conn)
    return _result(ingest.ingest_event(conn, now=now, **event.model_dump()), conn, now)


@router.post("/orders", dependencies=[Depends(require_api_key)])
def receive_order(order: OrderIn, conn: sqlite3.Connection = Depends(get_conn)):
    now = clock.now(conn)
    return _result(ingest.ingest_order(conn, order.model_dump(), now), conn, now)


@router.post("/sources/{source_id}/heartbeat", dependencies=[Depends(require_api_key)])
def heartbeat(source_id: str, conn: sqlite3.Connection = Depends(get_conn)):
    """A source that is alive but has nothing new says so. Without this, a quiet but healthy feed would
    look stale after 30 minutes and pause the alerts."""
    now = clock.now(conn)
    if not conn.execute("SELECT 1 FROM sources WHERE id = ?", (source_id,)).fetchone():
        raise HTTPException(404, "Unknown source")
    ingest.mark_read(conn, source_id, now)
    conn.commit()
    engine.run(conn, now)
    return {"outcome": "read recorded", "source": source_id, "at": tu.iso(now)}


@router.get("/exceptions", dependencies=[Depends(require_api_key)])
def open_exceptions(conn: sqlite3.Connection = Depends(get_conn)):
    now = clock.now(conn)
    return {"now": tu.iso(now), "open": queries.queue_rows(conn, now)}


@router.get("/outcomes", dependencies=[Depends(require_api_key)])
def outcomes(conn: sqlite3.Connection = Depends(get_conn)):
    """Labelled outcomes: one row per exception with how it ended. The training data for a later risk model."""
    now = clock.now(conn)
    rows = conn.execute(
        "SELECT x.id, x.order_id, x.type, x.created_at, x.acknowledged_at, x.resolved_at, x.resolution, "
        "x.escalated, x.action_cost_eur, o.customer_type, o.promised_at FROM exceptions x "
        "JOIN orders o ON o.id = x.order_id ORDER BY x.id"
    ).fetchall()
    results = {o["id"]: o["result"] for o in kpi.order_results(conn, now)}
    return {"now": tu.iso(now), "rows": [{**dict(r), "order_result": results[r["order_id"]]} for r in rows]}


@router.get("/health")
def health(conn: sqlite3.Connection = Depends(get_conn)):
    now = clock.now(conn)
    return {
        "status": "ok", "mode": clock.mode(), "now": tu.iso(now),
        "auth": "api-key" if settings.api_key else "open (local demo)",
        "sources": queries.freshness(conn, now, CFG),
    }
